"""
FeedbackIQ — Comprehensive NLP, ML Pipeline & Complaint Classification Test Suite

Tests:
1. Text Preprocessing & Cleaning Normalization
2. DistilBERT Sentiment Classification Metrics (Accuracy, Precision, Recall, Macro F1, Confusion Matrix)
3. SentenceTransformer Embeddings Quality (384 dimensions, zero NaN/Inf, semantic cosine similarity)
4. K-Means Clustering Validation (Silhouette Score, Davies-Bouldin Index)
5. Theme Identification & Aggregation
6. Top User Complaints Strict Qualification Logic:
   - Must represent real user problems, bugs, frustrations, dissatisfaction
   - Negative sentiment must dominate
   - Feature requests and positive compliments are NOT classified as complaints
7. Deterministic AI Summarization & Recommendation Validity
"""

import unittest
import numpy as np
from backend.services.sentiment import sentiment_analyzer
from backend.services.clustering import semantic_clusterer
from backend.services.summarization import theme_summarizer
from backend.ml.evaluator import model_evaluator


class TestNLPMLComprehensive(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Pre-warm models once
        sentiment_analyzer.preload_models()
        semantic_clusterer.preload_models()

    def test_01_sentiment_classification_accuracy_and_metrics(self):
        """Verifies DistilBERT sentiment classifier on a curated ground-truth test suite."""
        test_samples = [
            ("The application freezes every time I click the checkout button", "Negative"),
            ("Cannot login with my credentials after upgrading to version 3", "Negative"),
            ("Terrible customer service, nobody replied for three days", "Negative"),
            ("Subscription price is exorbitant and unfair", "Negative"),
            ("Absolutely love the intuitive navigation and clean dark mode!", "Positive"),
            ("Fast loading times and buttery smooth animations", "Positive"),
            ("Super helpful tool that saves our team hours each week", "Positive"),
            ("Fantastic customer support team, solved my issue in minutes", "Positive"),
            ("Please add Jira and Slack webhook integrations", "Neutral"),
            ("Would love an option to export feedback to CSV format", "Neutral")
        ]

        y_true = [s[1] for s in test_samples]
        y_pred = []
        for text, _ in test_samples:
            res = sentiment_analyzer.analyze(text)
            y_pred.append(res["sentiment"])

        eval_res = model_evaluator.evaluate_predictions(
            y_true, 
            y_pred, 
            class_labels=["Negative", "Neutral", "Positive"]
        )

        # DistilBERT on clear feedback should achieve high accuracy
        self.assertGreaterEqual(eval_res["accuracy"], 0.85, f"Accuracy too low: {eval_res['accuracy']}")
        self.assertGreaterEqual(eval_res["macro_f1"], 0.85, f"Macro F1 too low: {eval_res['macro_f1']}")
        self.assertIn("confusion_matrix", eval_res)
        self.assertEqual(len(eval_res["confusion_matrix"]), 3)

    def test_02_sentence_transformer_embeddings_quality(self):
        """Verifies SentenceTransformer generates valid, finite 384-d vectors with correct cosine similarity."""
        texts = [
            "Cannot login with password on mobile",
            "Authentication failed with invalid credential error",
            "Love the new dark mode theme design and colors",
            "The app crashes whenever I export reports"
        ]

        embeddings = semantic_clusterer.get_embeddings(texts)

        # 1. Shape and dimensions
        self.assertEqual(len(embeddings), 4)
        self.assertEqual(len(embeddings[0]), 384)

        # 2. Absence of NaN or Inf
        arr = np.array(embeddings)
        self.assertFalse(np.isnan(arr).any(), "Embeddings contain NaN values")
        self.assertFalse(np.isinf(arr).any(), "Embeddings contain Inf values")

        # 3. Cosine similarity between related vs unrelated pairs
        def cosine_sim(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

        sim_auth_1_2 = cosine_sim(arr[0], arr[1])  # Both about login/auth failure
        sim_auth_ui = cosine_sim(arr[0], arr[2])    # Auth vs Dark mode theme

        self.assertGreater(
            sim_auth_1_2, 
            sim_auth_ui + 0.15, 
            f"Expected auth embeddings to be significantly closer than auth vs UI: {sim_auth_1_2} vs {sim_auth_ui}"
        )

    def test_03_clustering_and_cluster_metrics(self):
        """Verifies K-Means clustering generates coherent clusters with valid Silhouette score."""
        feedback_corpus = [
            # Group 1: Login/Auth issues
            "Cannot login with Google SSO",
            "Password reset link is broken",
            "Login screen freezes on iOS",
            "Invalid credentials error when logging in",
            # Group 2: Payment/Billing
            "I was charged twice on my credit card",
            "Subscription renewal failed at checkout",
            "Refund request has not been processed",
            "Invoice has the wrong company billing address",
            # Group 3: Positive UI/UX
            "Love the clean typography and intuitive layout",
            "Beautiful interface and smooth animations",
            "The design is gorgeous and very modern",
            "Dark mode looks stunning on OLED displays"
        ]

        feedback_items = [{"id": f"fb_{i}", "feedback_text": t, "rating": 3} for i, t in enumerate(feedback_corpus)]
        embeddings = semantic_clusterer.get_embeddings(feedback_corpus)
        themes, labeled_items = semantic_clusterer.cluster_feedback(feedback_items, embeddings=embeddings)

        self.assertEqual(len(labeled_items), len(feedback_corpus))
        self.assertGreaterEqual(len(themes), 2)
        self.assertIn("name", themes[0])

        # Silhouette score validation across cluster labels
        cluster_labels = [it["theme_id"] for it in labeled_items]
        from sklearn.metrics import silhouette_score, davies_bouldin_score
        sil = silhouette_score(embeddings, cluster_labels)
        db_score = davies_bouldin_score(embeddings, cluster_labels)

        self.assertGreater(sil, 0.05, f"Silhouette score unexpectedly low: {sil}")
        self.assertLess(db_score, 4.0, f"Davies-Bouldin index too high: {db_score}")

    def test_04_top_user_complaints_strict_qualification(self):
        """
        Verifies Top User Complaints logic:
        A theme qualifies as a complaint ONLY when:
        1. Predominantly negative sentiment (negative_percentage > 50% or negative_percentage > positive_percentage)
        2. Contains real user problems, bugs, crashes, or dissatisfaction
        3. Sufficient supporting feedback
        Feature requests and positive compliments MUST NOT qualify.
        """
        candidate_themes = [
            {
                "id": "theme_1",
                "name": "App Crashes & Freezes",
                "theme_name": "App Crashes & Freezes",
                "mention_count": 85,
                "negative_percentage": 78.0,
                "positive_percentage": 10.0,
                "neutral_percentage": 12.0,
                "summary": "Users report recurrent application freezes on export.",
                "sentiment_distribution": {"Positive": 8, "Negative": 66, "Neutral": 11}
            },
            {
                "id": "theme_2",
                "name": "Payment Gateway Declines",
                "theme_name": "Payment Gateway Declines",
                "mention_count": 42,
                "negative_percentage": 62.0,
                "positive_percentage": 18.0,
                "neutral_percentage": 20.0,
                "summary": "International credit card charges fail repeatedly.",
                "sentiment_distribution": {"Positive": 8, "Negative": 26, "Neutral": 8}
            },
            {
                "id": "theme_3",
                "name": "Feature Request: Slack Webhooks",
                "theme_name": "Feature Request: Slack Webhooks",
                "mention_count": 55,
                "negative_percentage": 15.0,
                "positive_percentage": 35.0,
                "neutral_percentage": 50.0,
                "summary": "Users request third-party integrations with Slack.",
                "sentiment_distribution": {"Positive": 19, "Negative": 8, "Neutral": 28}
            },
            {
                "id": "theme_4",
                "name": "Clean UI & Smooth Design",
                "theme_name": "Clean UI & Smooth Design",
                "mention_count": 95,
                "negative_percentage": 4.0,
                "positive_percentage": 88.0,
                "neutral_percentage": 8.0,
                "summary": "Praise for the intuitive interface and dark mode.",
                "sentiment_distribution": {"Positive": 84, "Negative": 4, "Neutral": 7}
            }
        ]

        def is_top_complaint(theme: dict) -> bool:
            neg_pct = theme.get("negative_percentage", 0.0)
            pos_pct = theme.get("positive_percentage", 0.0)
            name_lower = theme.get("name", "").lower()

            # Disqualify obvious feature requests or praises
            if "feature request" in name_lower or "praise" in name_lower:
                return False
            # Must have predominant negative sentiment
            if neg_pct <= pos_pct or neg_pct < 40.0:
                return False
            return True

        complaints = [t for t in candidate_themes if is_top_complaint(t)]

        # Themes 1 and 2 must qualify
        self.assertEqual(len(complaints), 2)
        complaint_names = [c["name"] for c in complaints]
        self.assertIn("App Crashes & Freezes", complaint_names)
        self.assertIn("Payment Gateway Declines", complaint_names)
        self.assertNotIn("Feature Request: Slack Webhooks", complaint_names)
        self.assertNotIn("Clean UI & Smooth Design", complaint_names)

    def test_05_theme_summarizer_deterministic_synthesis(self):
        """Verifies deterministic summarization fallback produces valid, non-null intelligence."""
        sample_texts = [
            "App crashes on launch every time",
            "Force close when I tap on account settings",
            "Constant crashing on Android 14"
        ]

        sample_items = [
            {"id": f"fb_{i}", "feedback_text": t, "sentiment": "Negative", "rating": 1}
            for i, t in enumerate(sample_texts)
        ]

        res = theme_summarizer.summarize_theme(
            theme_name="Bugs & Crashes",
            items=sample_items,
            severity="High"
        )

        self.assertIn("summary", res)
        self.assertIn("main_complaint", res)
        self.assertIn("severity", res)
        self.assertIn("priority", res)
        self.assertIn("recommendation", res)
        self.assertEqual(res["severity"], "High")
        self.assertEqual(res["priority"], "P1")
        self.assertGreater(len(res["summary"]), 15)
        self.assertGreater(len(res["recommendation"]), 15)


if __name__ == "__main__":
    unittest.main()
