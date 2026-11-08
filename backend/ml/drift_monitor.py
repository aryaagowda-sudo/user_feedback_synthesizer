import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
from collections import Counter
import numpy as np
from scipy.spatial.distance import jensenshannon

logger = logging.getLogger("feedbackiq.ml.drift")

DRIFT_LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "drift_logs")
os.makedirs(DRIFT_LOGS_DIR, exist_ok=True)

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "is", "are", "was", "were", "it", "its", "i", "we", "my", "our", "you", "your",
    "this", "that", "have", "has", "had", "do", "does", "did", "be", "been", "app"
}

def compute_distribution_psi(baseline_probs: np.ndarray, current_probs: np.ndarray, epsilon: float = 1e-4) -> float:
    """Computes Population Stability Index (PSI) between two discrete probability distributions."""
    bp = np.clip(baseline_probs, epsilon, 1.0)
    cp = np.clip(current_probs, epsilon, 1.0)
    bp = bp / bp.sum()
    cp = cp / cp.sum()
    psi = np.sum((cp - bp) * np.log(cp / bp))
    return float(psi)

class DataDriftMonitor:
    """
    Monitors data drift between the training baseline and live incoming feedback:
    1. Sentiment Distribution Drift (Jensen-Shannon Divergence & PSI)
    2. Category Distribution Drift
    3. Semantic Embedding Centroid Shift (Cosine Distance)
    4. Prediction Confidence Drift (Average Confidence Drop)
    5. Vocabulary Drift (Emerging Out-of-Vocabulary Keywords)
    """

    def compute_drift_report(
        self,
        baseline_feedback: List[Dict[str, Any]],
        current_feedback: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculates multidimensional data drift metrics and assigns an overall drift severity level.
        """
        if not baseline_feedback or not current_feedback:
            return {
                "status": "Insufficient Data",
                "drift_severity": "Low",
                "message": "Both baseline and current feedback batches are required to compute drift.",
                "sentiment_jsd": 0.0,
                "category_jsd": 0.0,
                "embedding_drift": 0.0,
                "confidence_drop": 0.0,
                "emerging_keywords": []
            }

        # 1. Sentiment Distribution Drift
        sent_classes = ["Positive", "Negative", "Neutral"]
        b_sent_counts = Counter(f.get("sentiment", "Neutral") for f in baseline_feedback)
        c_sent_counts = Counter(f.get("sentiment", "Neutral") for f in current_feedback)

        b_sent_probs = np.array([b_sent_counts.get(c, 0) + 1 for c in sent_classes], dtype=float)
        c_sent_probs = np.array([c_sent_counts.get(c, 0) + 1 for c in sent_classes], dtype=float)
        b_sent_probs /= b_sent_probs.sum()
        c_sent_probs /= c_sent_probs.sum()

        sentiment_jsd = float(jensenshannon(b_sent_probs, c_sent_probs))
        sentiment_psi = compute_distribution_psi(b_sent_probs, c_sent_probs)

        # 2. Category Distribution Drift
        from backend.ml.dataset_manager import STANDARD_CATEGORIES
        b_cat_counts = Counter(f.get("category", "Other") for f in baseline_feedback)
        c_cat_counts = Counter(f.get("category", "Other") for f in current_feedback)

        b_cat_probs = np.array([b_cat_counts.get(c, 0) + 1 for c in STANDARD_CATEGORIES], dtype=float)
        c_cat_probs = np.array([c_cat_counts.get(c, 0) + 1 for c in STANDARD_CATEGORIES], dtype=float)
        b_cat_probs /= b_cat_probs.sum()
        c_cat_probs /= c_cat_probs.sum()

        category_jsd = float(jensenshannon(b_cat_probs, c_cat_probs))
        category_psi = compute_distribution_psi(b_cat_probs, c_cat_probs)

        # 3. Embedding Centroid Shift
        from backend.services.clustering import semantic_clusterer
        semantic_clusterer.preload_models()

        b_sample = [f.get("feedback_text") or f.get("feedback", "") for f in baseline_feedback[:200]]
        c_sample = [f.get("feedback_text") or f.get("feedback", "") for f in current_feedback[:200]]

        b_embs = semantic_clusterer.get_embeddings(b_sample)
        c_embs = semantic_clusterer.get_embeddings(c_sample)

        b_centroid = np.mean(b_embs, axis=0)
        c_centroid = np.mean(c_embs, axis=0)

        # Cosine distance = 1 - cosine_similarity
        norm_b = b_centroid / (np.linalg.norm(b_centroid) + 1e-9)
        norm_c = c_centroid / (np.linalg.norm(c_centroid) + 1e-9)
        embedding_cosine_distance = float(1.0 - np.dot(norm_b, norm_c))

        # 4. Model Prediction Confidence Drift
        b_conf = [float(f.get("confidence") or f.get("sentiment_confidence") or 0.85) for f in baseline_feedback]
        c_conf = [float(f.get("confidence") or f.get("sentiment_confidence") or 0.85) for f in current_feedback]

        avg_b_conf = float(np.mean(b_conf)) if b_conf else 0.85
        avg_c_conf = float(np.mean(c_conf)) if c_conf else 0.85
        confidence_delta = round(avg_c_conf - avg_b_conf, 4)

        # 5. Vocabulary Drift (Emerging Keywords in Current Batch)
        def get_vocab(texts: List[str]) -> Counter:
            words = []
            for t in texts:
                w_list = [w for w in re.findall(r"\b[a-z]{4,}\b", t.lower()) if w not in STOPWORDS]
                words.extend(w_list)
            return Counter(words)

        b_vocab = get_vocab(b_sample)
        c_vocab = get_vocab(c_sample)

        total_b = max(1, sum(b_vocab.values()))
        total_c = max(1, sum(c_vocab.values()))

        emerging_words = []
        for word, count in c_vocab.most_common(50):
            freq_c = count / total_c
            freq_b = b_vocab.get(word, 0) / total_b
            if freq_c > 0.005 and freq_c > (freq_b * 2.0 + 0.002):
                emerging_words.append({
                    "keyword": word,
                    "current_frequency": round(freq_c * 100, 2),
                    "baseline_frequency": round(freq_b * 100, 2),
                    "frequency_increase": round(freq_c / max(0.0001, freq_b), 1)
                })

        # 6. Overall Drift Severity Synthesis
        severity_score = (
            sentiment_jsd * 0.35 +
            category_jsd * 0.30 +
            min(1.0, embedding_cosine_distance * 4.0) * 0.25 +
            max(0.0, -confidence_delta) * 0.10
        )

        if severity_score > 0.25 or sentiment_jsd > 0.25:
            severity = "High"
            action = "Significant covariate drift detected in user feedback. Consider annotating recent feedback and triggering controlled retraining."
        elif severity_score > 0.12 or sentiment_jsd > 0.12:
            severity = "Moderate"
            action = "Noticeable distribution shift detected in categories/sentiment. Monitor model confidence and gather candidate labels."
        else:
            severity = "Low"
            action = "Feedback distribution aligns stably with the training baseline. No immediate retraining required."

        report = {
            "drift_severity": severity,
            "overall_drift_score": round(float(severity_score), 4),
            "recommended_action": action,
            "sentiment_drift": {
                "jensen_shannon_divergence": round(sentiment_jsd, 4),
                "population_stability_index": round(sentiment_psi, 4),
                "baseline_distribution": {k: round(v, 3) for k, v in zip(sent_classes, b_sent_probs)},
                "current_distribution": {k: round(v, 3) for k, v in zip(sent_classes, c_sent_probs)}
            },
            "category_drift": {
                "jensen_shannon_divergence": round(category_jsd, 4),
                "population_stability_index": round(category_psi, 4),
                "baseline_distribution": {k: round(v, 3) for k, v in zip(STANDARD_CATEGORIES, b_cat_probs)},
                "current_distribution": {k: round(v, 3) for k, v in zip(STANDARD_CATEGORIES, c_cat_probs)}
            },
            "embedding_drift": {
                "centroid_cosine_distance": round(embedding_cosine_distance, 4),
                "semantic_shift_detected": bool(embedding_cosine_distance > 0.08)
            },
            "confidence_drift": {
                "baseline_mean_confidence": round(avg_b_conf, 4),
                "current_mean_confidence": round(avg_c_conf, 4),
                "confidence_drop": round(-confidence_delta, 4) if confidence_delta < 0 else 0.0
            },
            "emerging_keywords": emerging_words[:8],
            "conceptual_distinction": (
                "Data Drift (Covariate Shift) measures changes in input features P(X) — such as new app issues or shifts in user tone. "
                "Model Performance Degradation (Concept Drift) occurs when the true relationship P(Y|X) alters, requiring human ground-truth labels to evaluate."
            )
        }
        return report

data_drift_monitor = DataDriftMonitor()
