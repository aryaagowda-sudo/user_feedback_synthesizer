import os
import time
import json
import logging
import pickle
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from backend.ml.dataset_manager import STANDARD_CATEGORIES
from backend.ml.evaluator import model_evaluator

logger = logging.getLogger("feedbackiq.ml.category_classifier")

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "ml_models")
os.makedirs(MODELS_DIR, exist_ok=True)

class CategoryClassifierSuite:
    """
    Trains and compares:
    1. Baseline Model: TF-IDF (n-grams 1-2, sublinear TF) + Logistic Regression (balanced class weights)
    2. Transformer / Semantic Embedding Neural Classifier
    Evaluates both on the identical held-out test set and performs data-driven champion selection.
    """

    def __init__(self):
        self.categories = STANDARD_CATEGORIES

    def train_baseline_tfidf(
        self,
        train_texts: List[str],
        train_labels: List[str],
        test_texts: List[str],
        test_labels: List[str]
    ) -> Dict[str, Any]:
        """Trains TF-IDF + Logistic Regression baseline model."""
        start_time = time.time()
        pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(
                max_features=5000, 
                ngram_range=(1, 2), 
                sublinear_tf=True,
                stop_words="english"
            )),
            ("clf", LogisticRegression(
                class_weight="balanced", 
                max_iter=1000, 
                C=1.0, 
                random_state=42
            ))
        ])

        pipeline.fit(train_texts, train_labels)
        train_time = round(time.time() - start_time, 3)

        # Measure inference latency on test set
        infer_start = time.time()
        test_preds = pipeline.predict(test_texts)
        infer_latency_ms = round(((time.time() - infer_start) / max(1, len(test_texts))) * 1000, 3)

        # Evaluation metrics
        eval_metrics = model_evaluator.evaluate_predictions(
            test_labels,
            list(test_preds),
            class_labels=self.categories,
            model_name="TF-IDF + Logistic Regression Baseline",
            split_name="test"
        )

        return {
            "model_type": "tfidf_logistic_regression",
            "model_name": "TF-IDF + Logistic Regression (Baseline)",
            "pipeline": pipeline,
            "train_time_sec": train_time,
            "infer_latency_ms": infer_latency_ms,
            "metrics": eval_metrics
        }

    def train_semantic_neural(
        self,
        train_texts: List[str],
        train_labels: List[str],
        test_texts: List[str],
        test_labels: List[str]
    ) -> Dict[str, Any]:
        """Trains Semantic Embedding Neural Classifier (Transformer features + MLP head)."""
        start_time = time.time()

        from backend.services.clustering import semantic_clusterer
        semantic_clusterer.preload_models()

        # Compute embeddings for train and test
        X_train_emb = semantic_clusterer.get_embeddings(train_texts)
        X_test_emb = semantic_clusterer.get_embeddings(test_texts)

        use_early_stopping = len(train_texts) >= 50
        mlp = MLPClassifier(
            hidden_layer_sizes=(128, 64),
            activation="relu",
            max_iter=200,
            early_stopping=use_early_stopping,
            n_iter_no_change=10,
            random_state=42
        )
        mlp.fit(X_train_emb, train_labels)
        train_time = round(time.time() - start_time, 3)

        infer_start = time.time()
        test_preds = mlp.predict(X_test_emb)
        infer_latency_ms = round(((time.time() - infer_start) / max(1, len(test_texts))) * 1000, 3)

        eval_metrics = model_evaluator.evaluate_predictions(
            test_labels,
            list(test_preds),
            class_labels=self.categories,
            model_name="Transformer Embeddings + Neural Classifier",
            split_name="test"
        )

        return {
            "model_type": "transformer_neural",
            "model_name": "Transformer Embeddings + MLP (Neural)",
            "model": mlp,
            "train_time_sec": train_time,
            "infer_latency_ms": infer_latency_ms,
            "metrics": eval_metrics
        }

    def train_and_compare(
        self,
        train_data: List[Dict[str, Any]],
        test_data: List[Dict[str, Any]],
        model_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Trains both Baseline and Transformer architectures, compares them on held-out test data,
        selects the superior model based on Macro F1, and saves artifacts.
        """
        if model_id is None:
            model_id = f"category_classifier_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        save_path = os.path.join(MODELS_DIR, model_id)
        os.makedirs(save_path, exist_ok=True)

        train_texts = [d["feedback"] for d in train_data]
        train_labels = [d.get("category", "Other") for d in train_data]

        test_texts = [d["feedback"] for d in test_data]
        test_labels = [d.get("category", "Other") for d in test_data]

        logger.info(f"Training Category Baseline Model (TF-IDF + Logistic Regression) on {len(train_texts)} samples...")
        baseline_res = self.train_baseline_tfidf(train_texts, train_labels, test_texts, test_labels)

        logger.info(f"Training Category Neural Model (Transformer + MLP) on {len(train_texts)} samples...")
        transformer_res = self.train_semantic_neural(train_texts, train_labels, test_texts, test_labels)

        # Comparative Selection: evaluate macro F1 and latency
        b_f1 = baseline_res["metrics"]["macro_f1"]
        t_f1 = transformer_res["metrics"]["macro_f1"]

        # Selection criteria: choose based on highest Macro F1; if tie within 0.015, prefer faster baseline
        if t_f1 > b_f1 + 0.015:
            champion_type = "transformer_neural"
            champion_name = transformer_res["model_name"]
            champion_reason = f"Transformer Neural achieved superior Macro F1 ({t_f1:.4f} vs {b_f1:.4f})."
            winning_obj = transformer_res["model"]
        else:
            champion_type = "tfidf_logistic_regression"
            champion_name = baseline_res["model_name"]
            champion_reason = (
                f"Baseline TF-IDF + Logistic Regression selected: competitive Macro F1 ({b_f1:.4f} vs {t_f1:.4f}) "
                f"with {baseline_res['infer_latency_ms']:.2f}ms latency ({transformer_res['infer_latency_ms']:.2f}ms for Transformer)."
            )
            winning_obj = baseline_res["pipeline"]

        # Save champion model binary
        champion_file = os.path.join(save_path, "champion_model.pkl")
        with open(champion_file, "wb") as f:
            pickle.dump({
                "type": champion_type,
                "model": winning_obj,
                "categories": self.categories
            }, f)

        comparison_data = {
            "model_id": model_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "champion_model": champion_name,
            "champion_type": champion_type,
            "champion_selection_reason": champion_reason,
            "comparison": {
                "baseline": {
                    "model_name": baseline_res["model_name"],
                    "accuracy": baseline_res["metrics"]["accuracy"],
                    "macro_f1": baseline_res["metrics"]["macro_f1"],
                    "weighted_f1": baseline_res["metrics"]["weighted_f1"],
                    "train_time_sec": baseline_res["train_time_sec"],
                    "infer_latency_ms": baseline_res["infer_latency_ms"],
                    "confusion_matrix": baseline_res["metrics"]["confusion_matrix"]
                },
                "transformer": {
                    "model_name": transformer_res["model_name"],
                    "accuracy": transformer_res["metrics"]["accuracy"],
                    "macro_f1": transformer_res["metrics"]["macro_f1"],
                    "weighted_f1": transformer_res["metrics"]["weighted_f1"],
                    "train_time_sec": transformer_res["train_time_sec"],
                    "infer_latency_ms": transformer_res["infer_latency_ms"],
                    "confusion_matrix": transformer_res["metrics"]["confusion_matrix"]
                }
            },
            "class_labels": self.categories,
            "test_samples_count": len(test_texts)
        }

        # Save metadata JSON
        with open(os.path.join(save_path, "comparison_metadata.json"), "w", encoding="utf-8") as f:
            json.dump(comparison_data, f, indent=2, default=str)

        logger.info(f"Category classifier comparison complete. Winner: {champion_name}. Reason: {champion_reason}")
        return comparison_data

    def predict(self, model_id: str, texts: List[str]) -> List[str]:
        """Loads champion model and generates category predictions for unseen texts."""
        safe_dir = os.path.abspath(MODELS_DIR)
        model_file = os.path.abspath(os.path.join(MODELS_DIR, model_id, "champion_model.pkl"))
        if not model_file.startswith(safe_dir) or not os.path.exists(model_file):
            raise FileNotFoundError(f"Champion model not found at {model_file}")

        with open(model_file, "rb") as f:
            bundle = pickle.load(f)  # nosec B301

        m_type = bundle["type"]
        model = bundle["model"]

        if m_type == "tfidf_logistic_regression":
            return list(model.predict(texts))
        else:
            from backend.services.clustering import semantic_clusterer
            embs = semantic_clusterer.get_embeddings(texts)
            return list(model.predict(embs))

category_classifier_suite = CategoryClassifierSuite()
