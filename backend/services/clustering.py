import os
import re
import logging
import numpy as np
from typing import List, Dict, Any, Tuple, Optional, Callable
from collections import Counter
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger("feedbackiq.clustering")

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "is", "are", "was", "were", "it", "its", "i", "we", "my", "our", "you", "your",
    "this", "that", "these", "those", "have", "has", "had", "do", "does", "did", "be",
    "been", "being", "so", "than", "too", "very", "can", "will", "just", "app", "page",
    "feedback", "when", "after", "every", "takes", "getting", "keep", "keeps"
}

# Domain heuristic mapping to enhance auto-generated titles
THEME_KEYWORD_MAP = {
    ("reminder", "reminders", "notification", "notifications", "alarm", "alarms", "alert", "ring", "notify"): "Notifications & Task Reminders",
    ("calendar", "events", "google", "schedule", "agenda", "month", "outlook", "dates"): "Calendar Sync & Scheduling",
    ("version", "premium", "pro", "subscription", "pay", "paid", "refund", "price", "charge", "free", "buy", "cost", "money"): "Pricing, Subscriptions & Pro Tier",
    ("backup", "restore", "lost", "delete", "deleted", "account", "phone", "transfer", "device", "data", "disappeared"): "Account Data, Backup & Cloud Restore",
    ("task", "tasks", "list", "lists", "subtask", "subtasks", "project", "sort", "filter", "category", "categories"): "Task Management & List Organization",
    ("habit", "habits", "tree", "forest", "focus", "timer", "gamification", "rpg", "pomodoro", "streak", "coins"): "Focus Timers, Habits & Gamification",
    ("widget", "widgets", "homescreen", "screen", "shortcut", "badge"): "Widgets & Home Screen Access",
    ("dark", "theme", "contrast", "ui", "font", "typography", "design", "color", "layout", "view", "interface"): "UI Design, Layout & Navigation",
    ("slow", "lag", "latency", "freeze", "freezes", "crash", "crashes", "bug", "bugs", "glitch", "error", "broken"): "App Stability, Crashes & Bug Reports",
    ("login", "auth", "sign", "signin", "password", "sso", "oauth", "credential"): "Authentication & Login Stability",
    ("export", "csv", "json", "slack", "webhook", "zapier", "jira", "integration", "integrate"): "Integrations & Data Export",
    ("love", "loved", "best", "great", "awesome", "excellent", "amazing", "favorite", "helpful", "delight", "super", "praise"): "Customer Praise & User Satisfaction"
}

class SemanticClusterer:
    def __init__(self):
        self._model = None
        self._initialized = False

    def preload_models(self):
        """Eagerly loads SentenceTransformer at server startup."""
        self._init_sentence_transformer()

    def _init_sentence_transformer(self):
        if self._initialized:
            return
        try:
            import torch
            threads = min(8, os.cpu_count() or 4)
            torch.set_num_threads(threads)

            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("SentenceTransformer 'all-MiniLM-L6-v2' loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformer ({e}). Using TF-IDF semantic embeddings fallback.")
            self._model = None
        finally:
            self._initialized = True

    def get_embeddings(
        self, 
        texts: List[str], 
        batch_size: int = 128, 
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> np.ndarray:
        """
        Computes dense semantic embeddings with batching and progress reporting.
        """
        if not self._initialized:
            self._init_sentence_transformer()

        total = len(texts)
        if total == 0:
            return np.empty((0, 384), dtype=np.float32)

        if self._model:
            try:
                # If large dataset, process in chunks to report incremental progress
                if total > batch_size and progress_callback:
                    all_chunks = []
                    for i in range(0, total, batch_size):
                        chunk = texts[i : i + batch_size]
                        # Truncate texts to 256 characters for ultra-fast embedding inference
                        chunk_clean = [t[:256] for t in chunk]
                        chunk_embs = self._model.encode(
                            chunk_clean, 
                            batch_size=len(chunk_clean), 
                            show_progress_bar=False, 
                            normalize_embeddings=True
                        )
                        all_chunks.append(chunk_embs)
                        processed = min(total, i + len(chunk))
                        progress_callback(processed, total)
                    return np.vstack(all_chunks)
                else:
                    clean_texts = [t[:256] for t in texts]
                    embeddings = self._model.encode(
                        clean_texts, 
                        batch_size=batch_size, 
                        show_progress_bar=False, 
                        normalize_embeddings=True
                    )
                    if progress_callback:
                        progress_callback(total, total)
                    return np.array(embeddings, dtype=np.float32)
            except Exception as e:
                logger.warning(f"SentenceTransformer encoding error ({e}), falling back to TF-IDF.")

        # Fallback TF-IDF embeddings
        vectorizer = TfidfVectorizer(max_features=64, stop_words="english")
        try:
            tfidf_matrix = vectorizer.fit_transform(texts).toarray()
            norms = np.linalg.norm(tfidf_matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            if progress_callback:
                progress_callback(total, total)
            return (tfidf_matrix / norms).astype(np.float32)
        except Exception:
            if progress_callback:
                progress_callback(total, total)
            return np.ones((len(texts), 32), dtype=np.float32) / np.sqrt(32)

    def _detect_feature_intent(self, sample_texts: List[str], negative_ratio: float = 0.0) -> bool:
        """
        Determines whether a cluster represents a genuine feature request.
        A theme is ONLY a feature request if:
        1. Negative sentiment ratio is low (< 45%). High negative ratio denotes user complaints/bugs.
        2. Feature request indicator phrases clearly exceed complaint indicators.
        """
        if negative_ratio >= 0.45:
            return False

        combined = " ".join(sample_texts).lower()

        feature_patterns = [
            r"\bplease add\b", r"\bwould love\b", r"\bwould be great\b", r"\bwish (?:there was|it had|you could)\b",
            r"\bcan you add\b", r"\bcould you add\b", r"\bhope you add\b", r"\bfeature request\b",
            r"\badd support for\b", r"\bintegrate with\b", r"\bwould like to see\b"
        ]
        complaint_patterns = [
            r"\bcannot\b", r"\bcan't\b", r"\bbroken\b", r"\bbug\b", r"\bcrash\b", r"\bcrashes\b",
            r"\bfreeze\b", r"\bfreezes\b", r"\bstopped working\b", r"\bnot working\b", r"\bterrible\b",
            r"\bhorrible\b", r"\bworst\b", r"\brefund\b", r"\bcharged\b", r"\bfailed\b", r"\bfails\b",
            r"\bunresponsive\b", r"\buseless\b", r"\blost data\b", r"\bdeleted\b"
        ]

        feature_hits = sum(len(re.findall(p, combined)) for p in feature_patterns)
        complaint_hits = sum(len(re.findall(p, combined)) for p in complaint_patterns)

        return feature_hits >= 2 and feature_hits > complaint_hits

    def _generate_theme_title(
        self, 
        cluster_texts: List[str], 
        cluster_id: int, 
        used_titles: Optional[set] = None,
        negative_ratio: float = 0.0
    ) -> Tuple[str, bool]:
        """Generates an intuitive, unique, professional theme title using semantic n-grams & keyword mapping."""
        if used_titles is None:
            used_titles = set()

        # Sample up to 150 texts to quickly derive keywords for large clusters
        sample_texts = cluster_texts[:150]
        combined_text = " ".join(sample_texts).lower()
        words = re.findall(r"\b[a-z]{3,}\b", combined_text)
        meaningful_words = [w for w in words if w not in STOPWORDS]
        word_counts = Counter(meaningful_words)
        
        # Rank domain map candidates
        candidates = []
        for keys, label in THEME_KEYWORD_MAP.items():
            score = sum(word_counts.get(k, 0) for k in keys)
            if score > 0:
                candidates.append((score, label))
        
        candidates.sort(key=lambda x: x[0], reverse=True)
        
        best_match = None
        for score, label in candidates:
            if score >= 3 and label not in used_titles:
                best_match = label
                break
                
        is_feature = self._detect_feature_intent(sample_texts, negative_ratio=negative_ratio)
        
        if best_match:
            return best_match, is_feature
            
        # Fallback: Top bigrams or top words
        bigrams = []
        for i in range(len(meaningful_words) - 1):
            bigrams.append(f"{meaningful_words[i]} {meaningful_words[i+1]}")
        top_bigrams = Counter(bigrams).most_common(5)
        
        chosen_title = None
        for bg, count in top_bigrams:
            bg_title = bg.title()
            if count >= 2 and bg_title not in used_titles:
                chosen_title = f"{bg_title} Experience"
                break
                
        if not chosen_title:
            top_words = [w.capitalize() for w, _ in word_counts.most_common(4)]
            top_words = [w for w in top_words if w.lower() not in {"app", "time", "just", "like"}]
            if len(top_words) >= 2:
                pair = f"{top_words[0]} & {top_words[1]}"
                chosen_title = pair if pair not in used_titles else f"{pair} (Group {cluster_id + 1})"
            else:
                chosen_title = f"Topic Group #{cluster_id + 1}"
                
        # Ensure total uniqueness
        final_title = chosen_title
        counter = 2
        while final_title in used_titles:
            final_title = f"{chosen_title} #{counter}"
            counter += 1

        return final_title, is_feature

    def cluster_feedback(
        self, 
        feedback_items: List[Dict[str, Any]], 
        embeddings: Optional[np.ndarray] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Clusters feedback items into themes using embeddings and K-Means."""
        n_items = len(feedback_items)
        if n_items == 0:
            return [], []

        if embeddings is None:
            texts = [item.get("feedback_text", "") for item in feedback_items]
            embeddings = self.get_embeddings(texts, progress_callback=progress_callback)

        # Dynamic number of clusters: 2 to 6
        if n_items <= 3:
            k = 1
        elif n_items <= 7:
            k = 2
        elif n_items <= 15:
            k = 3
        elif n_items <= 25:
            k = 4
        elif n_items <= 50:
            k = 5
        else:
            k = 6

        if k == 1:
            labels = [0] * n_items
        else:
            n_init_val = 3 if n_items > 2000 else 10
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=n_init_val)
            labels = kmeans.fit_predict(embeddings)

        # Group feedback items by cluster
        clusters: Dict[int, List[Dict[str, Any]]] = {}
        for idx, (label, item) in enumerate(zip(labels, feedback_items)):
            c_id = int(label)
            if c_id not in clusters:
                clusters[c_id] = []
            item["_emb_idx"] = idx
            clusters[c_id].append(item)

        themes_list = []
        labeled_feedback = []
        used_titles = set()

        for c_id, items in clusters.items():
            cluster_texts = [it["feedback_text"] for it in items]
            total_items = len(items)
            neg_items = sum(1 for it in items if it.get("sentiment") == "Negative")
            neg_ratio = (neg_items / total_items) if total_items > 0 else 0.0

            title, is_feature = self._generate_theme_title(
                cluster_texts, 
                c_id, 
                used_titles=used_titles,
                negative_ratio=neg_ratio
            )
            used_titles.add(title)
            theme_key = f"theme_{c_id + 1}"

            # Calculate centroid and representative comments closest to centroid
            c_indices = [it["_emb_idx"] for it in items]
            c_embeddings = embeddings[c_indices]
            centroid = np.mean(c_embeddings, axis=0, keepdims=True)
            dists = np.linalg.norm(c_embeddings - centroid, axis=1)
            sorted_indices = np.argsort(dists)
            
            # Top 3 most representative comments
            rep_comments = [items[i]["feedback_text"] for i in sorted_indices[:3]]

            # Update each item with theme metadata
            for it in items:
                it.pop("_emb_idx", None)
                it["theme_id"] = theme_key
                it["theme_name"] = title
                labeled_feedback.append(it)

            themes_list.append({
                "id": theme_key,
                "name": title,
                "items": items,
                "representative_comments": rep_comments,
                "is_feature_request": is_feature
            })

        return themes_list, labeled_feedback

semantic_clusterer = SemanticClusterer()
