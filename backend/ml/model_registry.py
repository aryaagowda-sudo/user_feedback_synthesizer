import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger("feedbackiq.ml.registry")

REGISTRY_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "model_registry.json")
CORRECTIONS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "label_corrections.json")
os.makedirs(os.path.dirname(REGISTRY_FILE), exist_ok=True)

DEFAULT_RETRAINING_THRESHOLD = 20  # Minimum human corrections required to trigger retraining

class ModelRegistry:
    """
    Controlled Model Versioning, Governance, and Human-in-the-Loop Retraining.
    Enforces candidate benchmark evaluation before promotion and enables instant rollback.
    """

    def __init__(self):
        self._init_registry()

    def _init_registry(self):
        if not os.path.exists(REGISTRY_FILE):
            initial_data = {
                "active_production_model_id": "distilbert_sst2_pretrained",
                "active_category_model_id": None,
                "rollback_model_id": None,
                "candidate_model_id": None,
                "models": [
                    {
                        "model_id": "distilbert_sst2_pretrained",
                        "model_name": "DistilBERT SST-2 (Pretrained Baseline)",
                        "model_type": "sentiment_transformer",
                        "version": "v1.0.0-baseline",
                        "status": "production",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "metrics": {
                            "accuracy": 0.892,
                            "macro_f1": 0.884,
                            "weighted_f1": 0.891
                        },
                        "hyperparameters": {
                            "architecture": "DistilBERT",
                            "pretrained_weights": "distilbert-base-uncased-finetuned-sst-2-english"
                        },
                        "dataset_id": "initial_seed"
                    }
                ],
                "retraining_history": []
            }
            with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, indent=2)

        if not os.path.exists(CORRECTIONS_FILE):
            with open(CORRECTIONS_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def _load_data(self) -> Dict[str, Any]:
        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading model registry: {e}")
            self._init_registry()
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)

    def _save_data(self, data: Dict[str, Any]):
        with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def list_models(self) -> List[Dict[str, Any]]:
        """Returns list of all models registered in the system."""
        data = self._load_data()
        return data.get("models", [])

    def get_production_model(self) -> Optional[Dict[str, Any]]:
        """Retrieves currently active production model record."""
        data = self._load_data()
        prod_id = data.get("active_production_model_id")
        return next((m for m in data.get("models", []) if m["model_id"] == prod_id), None)

    def get_candidate_model(self) -> Optional[Dict[str, Any]]:
        """Retrieves current candidate model pending promotion."""
        data = self._load_data()
        cand_id = data.get("candidate_model_id")
        return next((m for m in data.get("models", []) if m["model_id"] == cand_id), None)

    def register_trained_model(
        self,
        model_id: str,
        model_name: str,
        model_type: str,
        metrics: Dict[str, Any],
        hyperparameters: Dict[str, Any],
        dataset_id: str
    ) -> Dict[str, Any]:
        """Registers a newly trained model as a candidate."""
        data = self._load_data()
        version_num = len(data.get("models", [])) + 1
        version_tag = f"v{version_num}.0.0-candidate"

        new_record = {
            "model_id": model_id,
            "model_name": model_name,
            "model_type": model_type,
            "version": version_tag,
            "status": "candidate",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics,
            "hyperparameters": hyperparameters,
            "dataset_id": dataset_id
        }

        # Update any prior candidate to archived
        for m in data.get("models", []):
            if m.get("status") == "candidate":
                m["status"] = "archived"

        data["models"].append(new_record)
        data["candidate_model_id"] = model_id
        self._save_data(data)
        logger.info(f"Registered candidate model {model_id} ({version_tag}) in registry.")
        return new_record

    def evaluate_candidate_against_production(
        self,
        candidate_model_id: str
    ) -> Dict[str, Any]:
        """
        Compares candidate model metrics against active production model.
        Determines if candidate meets predefined promotion criteria.
        """
        data = self._load_data()
        prod = self.get_production_model()
        cand = next((m for m in data.get("models", []) if m["model_id"] == candidate_model_id), None)

        if not cand:
            raise ValueError(f"Candidate model {candidate_model_id} not found in registry.")

        prod_metrics = prod.get("metrics", {}) if prod else {}
        cand_metrics = cand.get("metrics", {})

        prod_macro_f1 = float(prod_metrics.get("macro_f1", 0.0))
        cand_macro_f1 = float(cand_metrics.get("macro_f1", 0.0))

        prod_acc = float(prod_metrics.get("accuracy", 0.0))
        cand_acc = float(cand_metrics.get("accuracy", 0.0))

        f1_delta = round(cand_macro_f1 - prod_macro_f1, 4)
        acc_delta = round(cand_acc - prod_acc, 4)

        # Promotion Criterion:
        # Candidate Macro F1 must not degrade by more than 0.005 and Accuracy must not drop by more than 0.015
        meets_criteria = bool(f1_delta >= -0.005 and acc_delta >= -0.015)

        evaluation_verdict = {
            "candidate_model_id": candidate_model_id,
            "candidate_version": cand.get("version"),
            "production_model_id": prod.get("model_id") if prod else None,
            "production_version": prod.get("version") if prod else None,
            "candidate_metrics": cand_metrics,
            "production_metrics": prod_metrics,
            "macro_f1_delta": f1_delta,
            "accuracy_delta": acc_delta,
            "meets_promotion_criteria": meets_criteria,
            "recommendation": (
                "Candidate model exceeds or matches production benchmark. Promotion recommended."
                if meets_criteria else
                f"Candidate underperforms production model by {abs(f1_delta):.1%} Macro F1. Promotion blocked."
            )
        }
        return evaluation_verdict

    def promote_candidate(
        self, 
        candidate_model_id: str, 
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Promotes a candidate model to active production status.
        Archives the previous production model and sets it as the rollback target.
        """
        data = self._load_data()
        cand = next((m for m in data.get("models", []) if m["model_id"] == candidate_model_id), None)
        if not cand:
            raise ValueError(f"Candidate model {candidate_model_id} does not exist.")

        if not force:
            verdict = self.evaluate_candidate_against_production(candidate_model_id)
            if not verdict["meets_promotion_criteria"]:
                raise ValueError(
                    f"Promotion blocked: Candidate model fails promotion criteria (F1 delta: {verdict['macro_f1_delta']}). "
                    f"Pass force=True to override."
                )

        current_prod_id = data.get("active_production_model_id")
        
        # Archive current production and designate as rollback target
        for m in data.get("models", []):
            if m["model_id"] == current_prod_id:
                m["status"] = "rollback_target"
            elif m["model_id"] == candidate_model_id:
                m["status"] = "production"
                m["version"] = m["version"].replace("-candidate", "-production")

        data["rollback_model_id"] = current_prod_id
        data["active_production_model_id"] = candidate_model_id
        data["candidate_model_id"] = None

        history_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "promotion",
            "promoted_model_id": candidate_model_id,
            "demoted_model_id": current_prod_id,
            "forced": force
        }
        data.setdefault("retraining_history", []).insert(0, history_event)
        self._save_data(data)

        logger.info(f"Promoted model {candidate_model_id} to production. Rollback target: {current_prod_id}")
        return {
            "status": "success",
            "active_production_model_id": candidate_model_id,
            "rollback_model_id": current_prod_id,
            "message": f"Candidate {candidate_model_id} successfully promoted to production."
        }

    def rollback_production(self) -> Dict[str, Any]:
        """Reinstates the previous production model from rollback target."""
        data = self._load_data()
        rollback_id = data.get("rollback_model_id")
        current_prod_id = data.get("active_production_model_id")

        if not rollback_id:
            raise ValueError("No previous rollback model available in registry.")

        for m in data.get("models", []):
            if m["model_id"] == rollback_id:
                m["status"] = "production"
            elif m["model_id"] == current_prod_id:
                m["status"] = "archived"

        data["active_production_model_id"] = rollback_id
        data["rollback_model_id"] = None

        history_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "rollback",
            "reinstated_model_id": rollback_id,
            "rolled_back_from": current_prod_id
        }
        data.setdefault("retraining_history", []).insert(0, history_event)
        self._save_data(data)

        logger.info(f"Rolled back production from {current_prod_id} to {rollback_id}")
        return {
            "status": "success",
            "active_production_model_id": rollback_id,
            "message": f"Successfully rolled back to version {rollback_id}."
        }

    # ==========================================================
    # HUMAN-IN-THE-LOOP LABEL CORRECTION POOL
    # ==========================================================
    def add_label_correction(
        self,
        feedback_id: str,
        feedback_text: str,
        corrected_sentiment: Optional[str] = None,
        corrected_category: Optional[str] = None,
        original_sentiment: Optional[str] = None,
        original_category: Optional[str] = None,
        corrected_by: str = "ML Engineer"
    ) -> Dict[str, Any]:
        """
        Stores human-verified ground-truth corrections.
        Never automatically treats model-generated predictions as ground truth.
        """
        corrections = []
        if os.path.exists(CORRECTIONS_FILE):
            try:
                with open(CORRECTIONS_FILE, "r", encoding="utf-8") as f:
                    corrections = json.load(f)
            except Exception:
                corrections = []

        # Update or append correction
        existing = next((c for c in corrections if c["feedback_id"] == feedback_id), None)
        entry = {
            "feedback_id": feedback_id,
            "feedback_text": feedback_text,
            "corrected_sentiment": corrected_sentiment,
            "corrected_category": corrected_category,
            "original_sentiment": original_sentiment,
            "original_category": original_category,
            "corrected_by": corrected_by,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if existing:
            corrections.remove(existing)
        corrections.insert(0, entry)

        with open(CORRECTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(corrections, f, indent=2, default=str)

        return {
            "status": "success",
            "total_corrections_collected": len(corrections),
            "entry": entry
        }

    def get_candidate_pool_status(self) -> Dict[str, Any]:
        """Returns number of collected corrections and readiness for controlled retraining."""
        corrections = []
        if os.path.exists(CORRECTIONS_FILE):
            try:
                with open(CORRECTIONS_FILE, "r", encoding="utf-8") as f:
                    corrections = json.load(f)
            except Exception:
                corrections = []

        count = len(corrections)
        is_ready = count >= DEFAULT_RETRAINING_THRESHOLD

        return {
            "total_human_corrections": count,
            "retraining_threshold": DEFAULT_RETRAINING_THRESHOLD,
            "is_retraining_ready": is_ready,
            "progress_percentage": round(min(1.0, count / DEFAULT_RETRAINING_THRESHOLD) * 100, 1),
            "recent_corrections": corrections[:10]
        }

model_registry = ModelRegistry()
