import os
import io
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from backend.ml.dataset_manager import dataset_manager
from backend.ml.sentiment_trainer import sentiment_trainer
from backend.ml.category_classifier import category_classifier_suite
from backend.ml.evaluator import model_evaluator
from backend.ml.model_registry import model_registry
from backend.ml.drift_monitor import data_drift_monitor
from backend.services.jobs import job_manager
from backend.database.db import db

logger = logging.getLogger("feedbackiq.ml.api")

ml_router = APIRouter(prefix="/ml", tags=["Machine Learning Pipeline"])

# Thread pool for asynchronous background model training
training_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ml-train-worker")

# ==========================================================
# PYDANTIC SCHEMAS
# ==========================================================
class TrainModelRequest(BaseModel):
    dataset_id: Optional[str] = None
    model_type: str = Field("sentiment", description="'sentiment' for DistilBERT, 'category' for Issue Classifier")
    epochs: int = Field(3, ge=1, le=10)
    batch_size: int = Field(16, ge=4, le=64)
    learning_rate: float = Field(3e-5, gt=0)
    early_stopping_patience: int = Field(2, ge=1, le=5)
    split_strategy: str = Field("stratified", description="'stratified' or 'temporal'")

class PromoteModelRequest(BaseModel):
    candidate_model_id: str
    force: bool = False

class LabelCorrectionRequest(BaseModel):
    feedback_id: str
    feedback_text: str
    corrected_sentiment: Optional[str] = None
    corrected_category: Optional[str] = None
    original_sentiment: Optional[str] = None
    original_category: Optional[str] = None
    corrected_by: Optional[str] = "ML Engineer"

# ==========================================================
# 1. DATASET MANAGEMENT ENDPOINTS
# ==========================================================
@ml_router.post("/datasets/upload")
async def upload_and_process_dataset(
    file: UploadFile = File(...),
    train_ratio: float = Form(0.70),
    val_ratio: float = Form(0.15),
    test_ratio: float = Form(0.15),
    split_strategy: str = Form("stratified")
):
    """
    Ingests and validates CSV dataset, detects & removes duplicates,
    computes class balance, and creates leak-free stratified or temporal splits.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV format is supported for training datasets.")

    content = await file.read()
    try:
        buffer = io.BytesIO(content)
        prep_res = dataset_manager.load_and_validate_csv(buffer, dataset_name=file.filename)
        clean_df = prep_res["df"]
        stats = prep_res["stats"]

        splits_res = dataset_manager.create_splits(
            clean_df,
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            split_strategy=split_strategy
        )

        dataset_id = f"ds_{uuid.uuid4().hex[:8]}"
        saved_path = dataset_manager.save_dataset_package(
            dataset_id=dataset_id,
            dataset_name=file.filename,
            train_df=splits_res["train_df"],
            val_df=splits_res["val_df"],
            test_df=splits_res["test_df"],
            stats=stats,
            split_summary=splits_res["summary"]
        )

        return {
            "status": "success",
            "dataset_id": dataset_id,
            "dataset_name": file.filename,
            "statistics": stats,
            "split_summary": splits_res["summary"],
            "leakage_verification": splits_res["summary"]["leakage_verification"]
        }
    except Exception as e:
        logger.error(f"Error processing dataset {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=422, detail=f"Dataset validation failed: {str(e)}")

@ml_router.get("/datasets")
async def list_datasets():
    """Lists all ingested datasets available for training."""
    return {"datasets": dataset_manager.list_datasets()}

# ==========================================================
# 2. MODEL TRAINING WORKFLOWS
# ==========================================================
def _run_sentiment_training_worker(job_id: str, dataset_id: str, params: Dict[str, Any]):
    try:
        job_manager.update_job(
            job_id,
            status="processing",
            current_stage="Loading dataset package",
            stage_index=1,
            progress_percentage=10,
            message="Validating dataset partitions and verifying zero data leakage..."
        )

        pkg = dataset_manager.load_dataset_package(dataset_id)
        if not pkg:
            raise ValueError(f"Dataset {dataset_id} not found.")

        train_data = pkg["train_data"]
        val_data = pkg["val_data"]
        test_data = pkg["test_data"]

        def on_batch_progress(progress_info: Dict[str, Any]):
            job_manager.update_job(
                job_id,
                current_stage=f"Training Epoch {progress_info['epoch']}/{progress_info['total_epochs']}",
                stage_index=2,
                progress_percentage=int(15 + progress_info["progress_percent"] * 0.7),
                message=f"Epoch {progress_info['epoch']} step {progress_info['step']}/{progress_info['total_steps']} - loss: {progress_info['current_batch_loss']}"
            )

        job_manager.update_job(
            job_id,
            current_stage="Fine-tuning DistilBERT",
            stage_index=2,
            progress_percentage=20,
            message=f"Initializing DistilBERT with balanced class weights for {params['epochs']} epochs..."
        )

        model_id = f"sentiment_distilbert_{uuid.uuid4().hex[:6]}"
        metadata = sentiment_trainer.train(
            train_data=train_data,
            val_data=val_data,
            test_data=test_data,
            model_id=model_id,
            epochs=params["epochs"],
            batch_size=params["batch_size"],
            learning_rate=params["learning_rate"],
            early_stopping_patience=params["early_stopping_patience"],
            progress_callback=on_batch_progress
        )

        job_manager.update_job(
            job_id,
            current_stage="Registering candidate model",
            stage_index=3,
            progress_percentage=95,
            message="Registering fine-tuned model in model registry..."
        )

        registered = model_registry.register_trained_model(
            model_id=model_id,
            model_name="DistilBERT Fine-Tuned Sentiment",
            model_type="sentiment_transformer",
            metrics=metadata.get("test_evaluation") or {
                "macro_f1": metadata.get("best_val_macro_f1", 0.0),
                "val_loss": metadata.get("best_val_loss", 0.0)
            },
            hyperparameters=metadata["hyperparameters"],
            dataset_id=dataset_id
        )

        job_manager.update_job(
            job_id,
            status="completed",
            current_stage="Training Complete",
            stage_index=3,
            progress_percentage=100,
            message=f"Model {model_id} fine-tuned successfully with test Macro F1: {metadata.get('test_evaluation', {}).get('macro_f1', 0.0)}",
            result={
                "model_id": model_id,
                "model_name": "DistilBERT Fine-Tuned Sentiment",
                "training_history": metadata["training_history"],
                "diagnostics": metadata["diagnostics"],
                "test_evaluation": metadata["test_evaluation"],
                "registered_model": registered
            }
        )
    except Exception as e:
        logger.error(f"Training job {job_id} failed: {e}", exc_info=True)
        job_manager.update_job(
            job_id,
            status="failed",
            error=str(e),
            message=f"Training halted: {str(e)}"
        )

def _run_category_training_worker(job_id: str, dataset_id: str):
    try:
        job_manager.update_job(
            job_id,
            status="processing",
            current_stage="Loading dataset partitions",
            stage_index=1,
            progress_percentage=15,
            message="Preparing category train and held-out test splits..."
        )

        pkg = dataset_manager.load_dataset_package(dataset_id)
        if not pkg:
            raise ValueError(f"Dataset {dataset_id} not found.")

        train_data = pkg["train_data"]
        test_data = pkg["test_data"]

        job_manager.update_job(
            job_id,
            current_stage="Training Baseline vs Transformer",
            stage_index=2,
            progress_percentage=40,
            message="Fitting TF-IDF + Logistic Regression baseline & Semantic Neural classifier..."
        )

        model_id = f"category_{uuid.uuid4().hex[:6]}"
        comparison_res = category_classifier_suite.train_and_compare(
            train_data=train_data,
            test_data=test_data,
            model_id=model_id
        )

        job_manager.update_job(
            job_id,
            current_stage="Registering champion model",
            stage_index=3,
            progress_percentage=90,
            message=f"Selecting champion model ({comparison_res['champion_model']})..."
        )

        champ_metrics = (
            comparison_res["comparison"]["transformer"]
            if comparison_res["champion_type"] == "transformer_neural"
            else comparison_res["comparison"]["baseline"]
        )

        registered = model_registry.register_trained_model(
            model_id=model_id,
            model_name=comparison_res["champion_model"],
            model_type="category_classifier",
            metrics=champ_metrics,
            hyperparameters={"champion_type": comparison_res["champion_type"]},
            dataset_id=dataset_id
        )

        job_manager.update_job(
            job_id,
            status="completed",
            current_stage="Training Complete",
            stage_index=3,
            progress_percentage=100,
            message=f"Champion selected: {comparison_res['champion_model']}",
            result={
                "model_id": model_id,
                "comparison": comparison_res,
                "registered_model": registered
            }
        )
    except Exception as e:
        logger.error(f"Category training job {job_id} failed: {e}", exc_info=True)
        job_manager.update_job(
            job_id,
            status="failed",
            error=str(e),
            message=f"Category training halted: {str(e)}"
        )

@ml_router.post("/train")
async def start_model_training(request: TrainModelRequest):
    """
    Launches non-blocking supervised model training in the background.
    Supports DistilBERT 3-class sentiment fine-tuning and Category classifier comparison.
    """
    dataset_id = request.dataset_id
    if not dataset_id:
        # Find latest available dataset
        datasets = dataset_manager.list_datasets()
        if not datasets:
            raise HTTPException(status_code=400, detail="No datasets found. Please upload a training CSV first.")
        dataset_id = datasets[0]["dataset_id"]

    job_id = job_manager.create_job(
        total_items=100, 
        dataset_name=f"Training: {request.model_type.capitalize()}"
    )

    if request.model_type.lower() == "sentiment":
        training_executor.submit(
            _run_sentiment_training_worker,
            job_id,
            dataset_id,
            {
                "epochs": request.epochs,
                "batch_size": request.batch_size,
                "learning_rate": request.learning_rate,
                "early_stopping_patience": request.early_stopping_patience
            }
        )
    elif request.model_type.lower() == "category":
        training_executor.submit(_run_category_training_worker, job_id, dataset_id)
    else:
        raise HTTPException(status_code=400, detail="model_type must be either 'sentiment' or 'category'")

    return {
        "job_id": job_id,
        "status": "processing",
        "dataset_id": dataset_id,
        "model_type": request.model_type,
        "message": f"Supervised {request.model_type} training initiated in background."
    }

@ml_router.get("/training-status/{job_id}")
async def get_training_status(job_id: str):
    """Polls training status, real-time epoch progress, loss/acc curves, and evaluation results."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Training job {job_id} not found.")
    return job

# ==========================================================
# 3. EVALUATION & MODEL REGISTRY ENDPOINTS
# ==========================================================
@ml_router.get("/evaluation/{model_id}")
async def get_model_evaluation(model_id: str):
    """Returns detailed evaluation report, confusion matrix, and per-class metrics."""
    res = model_evaluator.load_evaluation(model_id)
    if not res:
        # Check model metadata file
        meta_file = os.path.join(os.path.dirname(__file__), "..", "data", "ml_models", model_id, "model_metadata.json")
        comp_file = os.path.join(os.path.dirname(__file__), "..", "data", "ml_models", model_id, "comparison_metadata.json")
        if os.path.exists(meta_file):
            import json
            with open(meta_file, "r", encoding="utf-8") as f:
                return json.load(f).get("test_evaluation") or {}
        elif os.path.exists(comp_file):
            import json
            with open(comp_file, "r", encoding="utf-8") as f:
                return json.load(f)
        raise HTTPException(status_code=404, detail=f"Evaluation metrics for model {model_id} not found.")
    return res

@ml_router.get("/models")
async def list_models():
    """Returns registered models, active production model, and candidate model."""
    return {
        "models": model_registry.list_models(),
        "production_model": model_registry.get_production_model(),
        "candidate_model": model_registry.get_candidate_model()
    }

@ml_router.get("/models/candidate-evaluation")
async def evaluate_candidate():
    """Compares candidate model against production model on benchmark evaluation metrics."""
    cand = model_registry.get_candidate_model()
    if not cand:
        raise HTTPException(status_code=404, detail="No candidate model currently pending evaluation.")
    return model_registry.evaluate_candidate_against_production(cand["model_id"])

@ml_router.post("/models/promote")
async def promote_candidate_model(request: PromoteModelRequest):
    """Promotes candidate model to active production status if evaluation criteria are satisfied."""
    try:
        from backend.services.sentiment import sentiment_analyzer
        res = model_registry.promote_candidate(request.candidate_model_id, force=request.force)
        sentiment_analyzer.reload_production_model()
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@ml_router.post("/models/rollback")
async def rollback_model():
    """Rolls back the active production model to the designated rollback target."""
    try:
        from backend.services.sentiment import sentiment_analyzer
        res = model_registry.rollback_production()
        sentiment_analyzer.reload_production_model()
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==========================================================
# 4. DATA DRIFT & HUMAN-IN-THE-LOOP CORRECTIONS
# ==========================================================
@ml_router.get("/drift")
async def get_data_drift():
    """
    Computes multidimensional data drift (sentiment, category, embedding centroid, and vocabulary)
    between the training baseline and active feedback records.
    """
    active_fb = db.get_all_feedback()
    
    # Retrieve baseline feedback from latest ingested dataset package
    datasets = dataset_manager.list_datasets()
    baseline_fb = []
    if datasets:
        pkg = dataset_manager.load_dataset_package(datasets[0]["dataset_id"])
        if pkg:
            baseline_fb = pkg.get("train_data", [])

    if not baseline_fb:
        # Fallback to early feedback records
        baseline_fb = active_fb[:300] if len(active_fb) > 300 else active_fb

    current_fb = active_fb[-500:] if len(active_fb) > 500 else active_fb
    report = data_drift_monitor.compute_drift_report(baseline_fb, current_fb)
    return report

@ml_router.post("/feedback/correct-label")
async def correct_feedback_label(request: LabelCorrectionRequest):
    """
    Submits human-verified ground-truth label correction for a feedback item.
    Enriches candidate pool for controlled retraining without unsupervised self-training drift.
    """
    res = model_registry.add_label_correction(
        feedback_id=request.feedback_id,
        feedback_text=request.feedback_text,
        corrected_sentiment=request.corrected_sentiment,
        corrected_category=request.corrected_category,
        original_sentiment=request.original_sentiment,
        original_category=request.original_category,
        corrected_by=request.corrected_by or "ML Engineer"
    )
    return res

@ml_router.get("/retraining-status")
async def get_retraining_status():
    """Returns human-in-the-loop candidate pool progress toward retraining threshold."""
    return model_registry.get_candidate_pool_status()
