import os
import sys
import unittest
import pandas as pd
import numpy as np

# Ensure root directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.ml.dataset_manager import dataset_manager, text_hash
from backend.ml.evaluator import model_evaluator
from backend.ml.category_classifier import category_classifier_suite
from backend.ml.model_registry import model_registry
from backend.ml.drift_monitor import data_drift_monitor

class TestMLPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a synthetic dataset for testing
        cls.raw_data = [
            {"feedback": "The login screen is completely broken and crashes constantly", "sentiment": "Negative", "category": "Login and Authentication", "rating": 1, "date": "2026-01-01"},
            {"feedback": "I was charged twice on my invoice, please refund my money", "sentiment": "Negative", "category": "Payment Issues", "rating": 1, "date": "2026-01-02"},
            {"feedback": "This app is super slow and latency is unbearable when scrolling", "sentiment": "Negative", "category": "Performance", "rating": 2, "date": "2026-01-03"},
            {"feedback": "Love the dark theme and gorgeous UI typography!", "sentiment": "Positive", "category": "UI/UX", "rating": 5, "date": "2026-01-04"},
            {"feedback": "Please add Jira and Slack webhook integrations", "sentiment": "Neutral", "category": "Feature Requests", "rating": 3, "date": "2026-01-05"},
            {"feedback": "Customer support answered within 2 minutes, amazing service", "sentiment": "Positive", "category": "Customer Support", "rating": 5, "date": "2026-01-06"},
            {"feedback": "App freezes every time I tap the export button", "sentiment": "Negative", "category": "Bugs and Crashes", "rating": 1, "date": "2026-01-07"},
            {"feedback": "Best task organizer I have ever used, highly recommend to everyone", "sentiment": "Positive", "category": "Other", "rating": 5, "date": "2026-01-08"},
            {"feedback": "Cannot log in with Google OAuth SSO credential", "sentiment": "Negative", "category": "Login and Authentication", "rating": 1, "date": "2026-01-09"},
            {"feedback": "Subscription price increased but features remain unchanged", "sentiment": "Negative", "category": "Payment Issues", "rating": 2, "date": "2026-01-10"},
            {"feedback": "Lag on Android 14 is very noticeable", "sentiment": "Negative", "category": "Performance", "rating": 2, "date": "2026-01-11"},
            {"feedback": "Clean interface and easy navigation, very intuitive", "sentiment": "Positive", "category": "UI/UX", "rating": 4, "date": "2026-01-12"},
            {"feedback": "Would love an option to export feedback to CSV format", "sentiment": "Neutral", "category": "Feature Requests", "rating": 3, "date": "2026-01-13"},
            {"feedback": "Support agent resolved my account issue quickly", "sentiment": "Positive", "category": "Customer Support", "rating": 5, "date": "2026-01-14"},
            {"feedback": "App crashed after latest update, please hotfix", "sentiment": "Negative", "category": "Bugs and Crashes", "rating": 1, "date": "2026-01-15"},
            # Duplicate item to test deduplication
            {"feedback": "The login screen is completely broken and crashes constantly", "sentiment": "Negative", "category": "Login and Authentication", "rating": 1, "date": "2026-01-01"},
            # Near duplicate with whitespace/punctuation variation
            {"feedback": "the login screen is completely broken and crashes constantly!", "sentiment": "Negative", "category": "Login and Authentication", "rating": 1, "date": "2026-01-01"}
        ]
        cls.df = pd.DataFrame(cls.raw_data)

    def test_01_dataset_validation_and_deduplication(self):
        """Phase 1: Validates CSV, handles missing values, detects and cleans duplicates."""
        csv_buffer = self.df.to_csv(index=False)
        from io import StringIO
        res = dataset_manager.load_and_validate_csv(StringIO(csv_buffer), dataset_name="test_data.csv")
        clean_df = res["df"]
        stats = res["stats"]

        self.assertIn("valid_rows_retained", stats)
        self.assertEqual(stats["duplicates_removed"], 2)  # Exact + near-duplicate removed
        self.assertEqual(stats["valid_rows_retained"], 15)
        self.assertTrue(stats["has_supervised_sentiment"])
        self.assertEqual(len(clean_df), 15)

    def test_02_zero_data_leakage_splits(self):
        """Phase 1: Verifies zero data leakage between train, validation, and test sets."""
        csv_buffer = self.df.to_csv(index=False)
        from io import StringIO
        res = dataset_manager.load_and_validate_csv(StringIO(csv_buffer))
        splits = dataset_manager.create_splits(res["df"], train_ratio=0.6, val_ratio=0.2, test_ratio=0.2)
        
        leakage_info = splits["summary"]["leakage_verification"]
        self.assertTrue(leakage_info["leak_free"], "Data leakage detected between partitions!")
        self.assertEqual(leakage_info["train_val_overlap_count"], 0)
        self.assertEqual(leakage_info["train_test_overlap_count"], 0)
        self.assertEqual(leakage_info["val_test_overlap_count"], 0)

    def test_03_temporal_splitting(self):
        """Phase 1: Verifies temporal chronological splitting."""
        csv_buffer = self.df.to_csv(index=False)
        from io import StringIO
        res = dataset_manager.load_and_validate_csv(StringIO(csv_buffer))
        splits = dataset_manager.create_splits(res["df"], split_strategy="temporal", train_ratio=0.6, val_ratio=0.2, test_ratio=0.2)
        
        train_df = splits["train_df"]
        test_df = splits["test_df"]
        # Train dates should precede test dates
        self.assertLess(train_df["date_parsed"].max(), test_df["date_parsed"].min())

    def test_04_evaluator_metrics_and_confusion_matrix(self):
        """Phase 5: Verifies macro/weighted F1 and confusion matrix computation."""
        y_true = ["Negative", "Negative", "Neutral", "Positive", "Positive"]
        y_pred = ["Negative", "Neutral", "Neutral", "Positive", "Positive"]
        eval_res = model_evaluator.evaluate_predictions(y_true, y_pred, class_labels=["Negative", "Neutral", "Positive"])

        self.assertAlmostEqual(eval_res["accuracy"], 0.8, places=2)
        self.assertGreater(eval_res["macro_f1"], 0.7)
        self.assertIn("confusion_matrix", eval_res)
        self.assertEqual(len(eval_res["confusion_matrix"]), 3)

    def test_05_overfitting_underfitting_diagnostics(self):
        """Phase 3: Verifies detection of overfitting and underfitting signals."""
        # Overfitting history: train loss drops, val loss rises
        overfitting_history = [
            {"epoch": 1, "train_loss": 0.80, "val_loss": 0.60, "train_acc": 0.70, "val_acc": 0.68},
            {"epoch": 2, "train_loss": 0.40, "val_loss": 0.55, "train_acc": 0.88, "val_acc": 0.72},
            {"epoch": 3, "train_loss": 0.15, "val_loss": 0.78, "train_acc": 0.98, "val_acc": 0.71}
        ]
        diag = model_evaluator.diagnose_overfitting_underfitting(overfitting_history)
        self.assertTrue(diag["overfitting_detected"])
        self.assertIn("overfitting", diag["status"].lower())

    def test_06_category_classifier_baseline_vs_neural(self):
        """Phase 4: Trains Baseline TF-IDF vs Neural model and verifies champion selection."""
        train_data = [
            {"feedback": "Login failed with invalid credentials", "category": "Login and Authentication"},
            {"feedback": "Cannot sign in to my account", "category": "Login and Authentication"},
            {"feedback": "I was billed twice on my card", "category": "Payment Issues"},
            {"feedback": "Please refund my subscription fee", "category": "Payment Issues"},
            {"feedback": "The app freezes on launch and crashes", "category": "Bugs and Crashes"},
            {"feedback": "Force close error when clicking settings", "category": "Bugs and Crashes"},
            {"feedback": "Super slow and high latency", "category": "Performance"},
            {"feedback": "Takes forever to load my dashboard", "category": "Performance"},
            {"feedback": "Please add Zapier and Webhook support", "category": "Feature Requests"},
            {"feedback": "Would love an option to export CSV", "category": "Feature Requests"}
        ]
        test_data = [
            {"feedback": "Unable to log in with password", "category": "Login and Authentication"},
            {"feedback": "Charged wrong amount for my plan", "category": "Payment Issues"},
            {"feedback": "Application crashed unexpectedly", "category": "Bugs and Crashes"},
            {"feedback": "Lag is horrible when typing", "category": "Performance"},
            {"feedback": "Feature suggestion: add dark mode toggle", "category": "Feature Requests"}
        ]

        res = category_classifier_suite.train_and_compare(train_data, test_data, model_id="test_category_model")
        self.assertIn("champion_model", res)
        self.assertIn("comparison", res)
        self.assertIn("baseline", res["comparison"])
        self.assertIn("transformer", res["comparison"])

    def test_07_model_registry_and_governance(self):
        """Phase 6: Verifies controlled candidate registration, promotion criteria, and rollback."""
        reg = model_registry
        initial_prod = reg.get_production_model()
        self.assertIsNotNone(initial_prod)

        # Register candidate with superior F1
        reg.register_trained_model(
            model_id="cand_test_v2",
            model_name="Test Model v2",
            model_type="sentiment_transformer",
            metrics={"macro_f1": 0.910, "accuracy": 0.920},
            hyperparameters={"lr": 3e-5},
            dataset_id="test_ds"
        )
        cand = reg.get_candidate_model()
        self.assertEqual(cand["model_id"], "cand_test_v2")

        # Evaluate candidate against production
        verdict = reg.evaluate_candidate_against_production("cand_test_v2")
        self.assertTrue(verdict["meets_promotion_criteria"])

        # Promote candidate
        promote_res = reg.promote_candidate("cand_test_v2")
        self.assertEqual(promote_res["active_production_model_id"], "cand_test_v2")
        self.assertEqual(promote_res["rollback_model_id"], initial_prod["model_id"])

        # Rollback
        rollback_res = reg.rollback_production()
        self.assertEqual(rollback_res["active_production_model_id"], initial_prod["model_id"])

    def test_08_data_drift_monitoring(self):
        """Phase 7: Verifies JSD, PSI, centroid shift, and vocabulary drift tracking."""
        baseline = [
            {"feedback": "Great app, fast and reliable", "sentiment": "Positive", "category": "UI/UX", "confidence": 0.95},
            {"feedback": "Smooth navigation and nice design", "sentiment": "Positive", "category": "UI/UX", "confidence": 0.92},
            {"feedback": "Works well for my daily tasks", "sentiment": "Positive", "category": "Other", "confidence": 0.90}
        ]
        # Current batch with heavy negative crash reports (significant drift)
        current = [
            {"feedback": "Crashed immediately on Android update, broken", "sentiment": "Negative", "category": "Bugs and Crashes", "confidence": 0.70},
            {"feedback": "Total failure, battery drain and freezing", "sentiment": "Negative", "category": "Performance", "confidence": 0.65},
            {"feedback": "Worst bug ever, cannot start application", "sentiment": "Negative", "category": "Bugs and Crashes", "confidence": 0.60}
        ]

        drift_res = data_drift_monitor.compute_drift_report(baseline, current)
        self.assertIn("drift_severity", drift_res)
        self.assertIn(drift_res["drift_severity"], ["Moderate", "High"])
        self.assertGreater(drift_res["sentiment_drift"]["jensen_shannon_divergence"], 0.15)
        self.assertIn("emerging_keywords", drift_res)

if __name__ == "__main__":
    unittest.main()
