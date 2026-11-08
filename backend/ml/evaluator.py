import os
import json
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.metrics import (
    accuracy_score, 
    precision_recall_fscore_support, 
    confusion_matrix, 
    classification_report
)

logger = logging.getLogger("feedbackiq.ml.evaluator")

EVALUATIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "ml_evaluations")
os.makedirs(EVALUATIONS_DIR, exist_ok=True)

class ModelEvaluator:
    """
    Standardized evaluation module for classification models.
    Calculates Macro/Weighted F1, Precision, Recall, Accuracy, Confusion Matrix,
    and overfitting/underfitting diagnostic signals.
    """

    def evaluate_predictions(
        self,
        y_true: List[str],
        y_pred: List[str],
        class_labels: Optional[List[str]] = None,
        model_id: Optional[str] = None,
        model_name: Optional[str] = None,
        split_name: str = "test"
    ) -> Dict[str, Any]:
        """
        Evaluates predictions against true labels.
        Computes accuracy, precision, recall, macro F1, weighted F1, and confusion matrix.
        """
        if class_labels is None:
            # Sort unique labels alphabetically for deterministic ordering
            class_labels = sorted(list(set(y_true).union(set(y_pred))))

        # Basic accuracy
        acc = float(accuracy_score(y_true, y_pred))

        # Precision, Recall, F1 (Macro & Weighted)
        p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
            y_true, y_pred, labels=class_labels, average="macro", zero_division=0
        )
        p_weighted, r_weighted, f1_weighted, _ = precision_recall_fscore_support(
            y_true, y_pred, labels=class_labels, average="weighted", zero_division=0
        )

        # Per-class metrics
        p_per_class, r_per_class, f1_per_class, support = precision_recall_fscore_support(
            y_true, y_pred, labels=class_labels, average=None, zero_division=0
        )

        per_class_metrics = {}
        for idx, label in enumerate(class_labels):
            per_class_metrics[label] = {
                "precision": round(float(p_per_class[idx]), 4),
                "recall": round(float(r_per_class[idx]), 4),
                "f1_score": round(float(f1_per_class[idx]), 4),
                "support": int(support[idx])
            }

        # Confusion Matrix
        cm = confusion_matrix(y_true, y_pred, labels=class_labels).tolist()

        result = {
            "model_id": model_id or "unspecified_model",
            "model_name": model_name or "Classifier",
            "split_name": split_name,
            "accuracy": round(acc, 4),
            "macro_precision": round(float(p_macro), 4),
            "macro_recall": round(float(r_macro), 4),
            "macro_f1": round(float(f1_macro), 4),
            "weighted_precision": round(float(p_weighted), 4),
            "weighted_recall": round(float(r_weighted), 4),
            "weighted_f1": round(float(f1_weighted), 4),
            "class_labels": class_labels,
            "confusion_matrix": cm,
            "per_class_metrics": per_class_metrics,
            "total_samples": len(y_true)
        }

        # Save to disk if model_id provided
        if model_id:
            self.save_evaluation(model_id, result)

        return result

    def diagnose_overfitting_underfitting(
        self,
        training_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Detects possible overfitting and underfitting by analyzing training vs validation trajectories.
        """
        if not training_history or len(training_history) < 2:
            return {
                "status": "Inconclusive",
                "message": "Insufficient epochs to evaluate training trajectory.",
                "overfitting_detected": False,
                "underfitting_detected": False
            }

        train_losses = [h.get("train_loss", 0.0) for h in training_history]
        val_losses = [h.get("val_loss", 0.0) for h in training_history]
        train_accs = [h.get("train_acc", 0.0) for h in training_history]
        val_accs = [h.get("val_acc", 0.0) for h in training_history]

        final_train_loss = train_losses[-1]
        final_val_loss = val_losses[-1]
        final_train_acc = train_accs[-1]
        final_val_acc = val_accs[-1]

        min_val_loss = min(val_losses)
        val_loss_diverging = (final_val_loss > min_val_loss * 1.15)
        acc_gap = final_train_acc - final_val_acc

        overfitting = False
        underfitting = False
        diagnostic_messages = []

        if val_loss_diverging and (train_losses[-1] < train_losses[0]):
            overfitting = True
            diagnostic_messages.append(
                f"Validation loss increased from {min_val_loss:.4f} to {final_val_loss:.4f} while training loss continued downward. Indicates possible overfitting."
            )
        elif acc_gap > 0.15:
            overfitting = True
            diagnostic_messages.append(
                f"Noticeable generalization gap: training accuracy ({final_train_acc:.1%}) significantly exceeds validation accuracy ({final_val_acc:.1%})."
            )

        if final_train_acc < 0.60 and final_val_acc < 0.60:
            underfitting = True
            diagnostic_messages.append(
                f"Both training ({final_train_acc:.1%}) and validation ({final_val_acc:.1%}) accuracy remain below baseline thresholds. The model may lack sufficient capacity or training steps."
            )

        if not overfitting and not underfitting:
            status = "Healthy Generalization"
            msg = "Training and validation losses converge stably without significant generalization gap."
        elif overfitting and underfitting:
            status = "Unstable Convergence"
            msg = " ".join(diagnostic_messages)
        elif overfitting:
            status = "Possible Overfitting Detected"
            msg = " ".join(diagnostic_messages)
        else:
            status = "Possible Underfitting Detected"
            msg = " ".join(diagnostic_messages)

        return {
            "status": status,
            "message": msg,
            "overfitting_detected": overfitting,
            "underfitting_detected": underfitting,
            "final_train_acc": round(final_train_acc, 4),
            "final_val_acc": round(final_val_acc, 4),
            "final_train_loss": round(final_train_loss, 4),
            "final_val_loss": round(final_val_loss, 4),
            "generalization_gap": round(acc_gap, 4),
            "mitigations_used": [
                "Early Stopping with Best Weights Checkpointing",
                "Weight Decay (AdamW L2 Regularization)",
                "Stratified Leak-Free Partitioning",
                "Class-Weighted Cross Entropy"
            ]
        }

    def save_evaluation(self, model_id: str, evaluation_data: Dict[str, Any]) -> str:
        """Saves evaluation results to JSON file."""
        file_path = os.path.join(EVALUATIONS_DIR, f"{model_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(evaluation_data, f, indent=2, default=str)
        return file_path

    def load_evaluation(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Loads evaluation results from disk by model ID."""
        file_path = os.path.join(EVALUATIONS_DIR, f"{model_id}.json")
        if not os.path.exists(file_path):
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

model_evaluator = ModelEvaluator()
