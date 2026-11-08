import os
import json
import logging
import copy
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timezone
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification, 
    get_linear_schedule_with_warmup
)
from sklearn.utils.class_weight import compute_class_weight
from backend.ml.evaluator import model_evaluator

logger = logging.getLogger("feedbackiq.ml.sentiment_trainer")

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "ml_models")
os.makedirs(MODELS_DIR, exist_ok=True)

SENTIMENT_LABEL_MAP = {
    "Negative": 0,
    "Neutral": 1,
    "Positive": 2
}
SENTIMENT_INV_MAP = {0: "Negative", 1: "Neutral", 2: "Positive"}

class FeedbackDataset(Dataset):
    def __init__(self, texts: List[str], labels: List[int], tokenizer, max_length: int = 128):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]

        encoding = self.tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_tensors="pt"
        )

        item = {key: val.squeeze(0) for key, val in encoding.items()}
        item["labels"] = torch.tensor(label, dtype=torch.long)
        return item

class SentimentTrainer:
    """
    Fine-tunes a pretrained Transformer (DistilBERT) for 3-class sentiment classification
    with early stopping, learning rate scheduling, class weighting, and model checkpointing.
    """

    def __init__(self, base_model_name: str = "distilbert/distilbert-base-uncased"):
        self.base_model_name = base_model_name
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"SentimentTrainer initialized. Target execution device: {self.device}")

    def train(
        self,
        train_data: List[Dict[str, Any]],
        val_data: List[Dict[str, Any]],
        test_data: Optional[List[Dict[str, Any]]] = None,
        model_id: Optional[str] = None,
        epochs: int = 3,
        batch_size: int = 16,
        learning_rate: float = 3e-5,
        weight_decay: float = 0.01,
        early_stopping_patience: int = 2,
        max_length: int = 128,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes supervised fine-tuning with training/validation monitoring and checkpointing.
        """
        if model_id is None:
            model_id = f"sentiment_distilbert_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        save_path = os.path.join(MODELS_DIR, model_id)
        os.makedirs(save_path, exist_ok=True)

        # 1. Prepare Data
        train_texts = [d["feedback"] for d in train_data if d.get("sentiment") in SENTIMENT_LABEL_MAP]
        train_labels = [SENTIMENT_LABEL_MAP[d["sentiment"]] for d in train_data if d.get("sentiment") in SENTIMENT_LABEL_MAP]

        val_texts = [d["feedback"] for d in val_data if d.get("sentiment") in SENTIMENT_LABEL_MAP]
        val_labels = [SENTIMENT_LABEL_MAP[d["sentiment"]] for d in val_data if d.get("sentiment") in SENTIMENT_LABEL_MAP]

        if not train_texts or not val_texts:
            raise ValueError("Training and validation datasets must contain valid sentiment labels (Positive, Negative, Neutral).")

        # 2. Compute Balanced Class Weights for Imbalanced Sentiment Distributions
        unique_classes = np.unique(train_labels)
        raw_weights = compute_class_weight(
            class_weight="balanced",
            classes=unique_classes,
            y=np.array(train_labels)
        )
        full_weights = np.ones(3, dtype=np.float32)
        for c, w in zip(unique_classes, raw_weights):
            full_weights[c] = float(w)
        class_weights_tensor = torch.tensor(full_weights, dtype=torch.float32).to(self.device)

        # 3. Load Tokenizer & Model
        logger.info(f"Loading pretrained tokenizer & model weights from '{self.base_model_name}'...")
        tokenizer = AutoTokenizer.from_pretrained(self.base_model_name, revision="main")  # nosec B615
        model = AutoModelForSequenceClassification.from_pretrained(  # nosec B615
            self.base_model_name,
            revision="main",
            num_labels=3,
            id2label=SENTIMENT_INV_MAP,
            label2id=SENTIMENT_LABEL_MAP
        )
        model.to(self.device)

        # 4. DataLoaders
        train_ds = FeedbackDataset(train_texts, train_labels, tokenizer, max_length=max_length)
        val_ds = FeedbackDataset(val_texts, val_labels, tokenizer, max_length=max_length)

        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

        # 5. Optimizer & Scheduler with Weight Decay
        no_decay = ["bias", "LayerNorm.weight"]
        optimizer_grouped_parameters = [
            {
                "params": [p for n, p in model.named_parameters() if not any(nd in n for nd in no_decay)],
                "weight_decay": weight_decay,
            },
            {
                "params": [p for n, p in model.named_parameters() if any(nd in n for nd in no_decay)],
                "weight_decay": 0.0,
            },
        ]
        optimizer = torch.optim.AdamW(optimizer_grouped_parameters, lr=learning_rate)

        total_training_steps = len(train_loader) * epochs
        warmup_steps = int(0.1 * total_training_steps)
        scheduler = get_linear_schedule_with_warmup(
            optimizer, 
            num_warmup_steps=warmup_steps, 
            num_training_steps=total_training_steps
        )
        loss_fn = torch.nn.CrossEntropyLoss(weight=class_weights_tensor)

        # 6. Training Loop with Early Stopping & Metrics Tracking
        training_history = []
        best_val_loss = float("inf")
        best_val_macro_f1 = 0.0
        best_model_state = None
        patience_counter = 0

        logger.info(f"Starting fine-tuning for {epochs} epochs (Batch Size={batch_size}, Steps/Epoch={len(train_loader)})...")

        for epoch in range(1, epochs + 1):
            model.train()
            total_train_loss = 0.0
            correct_train = 0
            total_train = 0

            for step, batch in enumerate(train_loader):
                input_ids = batch["input_ids"].to(self.device)
                attention_mask = batch["attention_mask"].to(self.device)
                labels = batch["labels"].to(self.device)

                optimizer.zero_grad()
                outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                logits = outputs.logits
                loss = loss_fn(logits, labels)

                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()

                total_train_loss += loss.item()
                preds = torch.argmax(logits, dim=1)
                correct_train += (preds == labels).sum().item()
                total_train += labels.size(0)

                # Report batch progress to callback
                if progress_callback and (step % 5 == 0 or step == len(train_loader) - 1):
                    progress_callback({
                        "stage": "Training",
                        "epoch": epoch,
                        "total_epochs": epochs,
                        "step": step + 1,
                        "total_steps": len(train_loader),
                        "current_batch_loss": round(loss.item(), 4),
                        "progress_percent": round(((epoch - 1) * len(train_loader) + (step + 1)) / total_training_steps * 100, 1)
                    })

            avg_train_loss = total_train_loss / max(1, len(train_loader))
            train_accuracy = correct_train / max(1, total_train)

            # Validation Pass
            model.eval()
            total_val_loss = 0.0
            val_preds_all = []
            val_labels_all = []

            with torch.no_grad():
                for batch in val_loader:
                    input_ids = batch["input_ids"].to(self.device)
                    attention_mask = batch["attention_mask"].to(self.device)
                    labels = batch["labels"].to(self.device)

                    outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                    logits = outputs.logits
                    loss = loss_fn(logits, labels)
                    total_val_loss += loss.item()

                    preds = torch.argmax(logits, dim=1)
                    val_preds_all.extend(preds.cpu().tolist())
                    val_labels_all.extend(labels.cpu().tolist())

            avg_val_loss = total_val_loss / max(1, len(val_loader))

            # Evaluate epoch validation metrics via ModelEvaluator
            val_y_true = [SENTIMENT_INV_MAP[lbl] for lbl in val_labels_all]
            val_y_pred = [SENTIMENT_INV_MAP[lbl] for lbl in val_preds_all]
            val_eval = model_evaluator.evaluate_predictions(
                val_y_true, 
                val_y_pred, 
                class_labels=["Negative", "Neutral", "Positive"],
                split_name="validation"
            )

            epoch_record = {
                "epoch": epoch,
                "train_loss": round(avg_train_loss, 4),
                "val_loss": round(avg_val_loss, 4),
                "train_acc": round(train_accuracy, 4),
                "val_acc": round(val_eval["accuracy"], 4),
                "val_macro_f1": round(val_eval["macro_f1"], 4),
                "val_weighted_f1": round(val_eval["weighted_f1"], 4),
                "val_precision": round(val_eval["macro_precision"], 4),
                "val_recall": round(val_eval["macro_recall"], 4),
                "val_confusion_matrix": val_eval["confusion_matrix"]
            }
            training_history.append(epoch_record)
            logger.info(f"Epoch {epoch}/{epochs} | Train Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f} | Val Acc: {val_eval['accuracy']:.1%} | Val Macro F1: {val_eval['macro_f1']:.4f}")

            # Checkpoint Best Model (based on validation loss and macro F1)
            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                best_val_macro_f1 = val_eval["macro_f1"]
                best_model_state = copy.deepcopy(model.state_dict())
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= early_stopping_patience:
                    logger.info(f"Early stopping triggered at epoch {epoch} (no val_loss improvement for {patience_counter} consecutive epochs).")
                    break

        # Restore Best Checkpoint
        if best_model_state is not None:
            model.load_state_dict(best_model_state)

        # 7. Diagnose Overfitting & Underfitting
        diagnostics = model_evaluator.diagnose_overfitting_underfitting(training_history)

        # 8. Save Fine-Tuned Model Weights & Tokenizer
        model.save_pretrained(save_path)
        tokenizer.save_pretrained(save_path)

        # 9. Final Test Evaluation if Held-Out Test Set Provided
        test_eval = None
        if test_data:
            test_texts = [d["feedback"] for d in test_data if d.get("sentiment") in SENTIMENT_LABEL_MAP]
            test_labels = [SENTIMENT_LABEL_MAP[d["sentiment"]] for d in test_data if d.get("sentiment") in SENTIMENT_LABEL_MAP]

            if test_texts:
                test_ds = FeedbackDataset(test_texts, test_labels, tokenizer, max_length=max_length)
                test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)

                model.eval()
                test_preds_all = []
                with torch.no_grad():
                    for batch in test_loader:
                        input_ids = batch["input_ids"].to(self.device)
                        attention_mask = batch["attention_mask"].to(self.device)
                        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                        preds = torch.argmax(outputs.logits, dim=1)
                        test_preds_all.extend(preds.cpu().tolist())

                test_y_true = [SENTIMENT_INV_MAP[lbl] for lbl in test_labels]
                test_y_pred = [SENTIMENT_INV_MAP[lbl] for lbl in test_preds_all]
                test_eval = model_evaluator.evaluate_predictions(
                    test_y_true,
                    test_y_pred,
                    class_labels=["Negative", "Neutral", "Positive"],
                    model_id=model_id,
                    model_name="DistilBERT Sentiment Classifier",
                    split_name="test"
                )

        metadata = {
            "model_id": model_id,
            "model_type": "sentiment_transformer",
            "base_model": self.base_model_name,
            "architecture": "DistilBertForSequenceClassification",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "target_classes": ["Negative", "Neutral", "Positive"],
            "hyperparameters": {
                "epochs": epochs,
                "batch_size": batch_size,
                "learning_rate": learning_rate,
                "weight_decay": weight_decay,
                "early_stopping_patience": early_stopping_patience,
                "max_length": max_length,
                "class_weights": full_weights.tolist()
            },
            "best_val_loss": round(best_val_loss, 4),
            "best_val_macro_f1": round(best_val_macro_f1, 4),
            "training_history": training_history,
            "diagnostics": diagnostics,
            "test_evaluation": test_eval,
            "model_path": save_path
        }

        # Save metadata JSON with model artifacts
        with open(os.path.join(save_path, "model_metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, default=str)

        logger.info(f"Successfully trained and saved model '{model_id}' to {save_path}")
        return metadata

sentiment_trainer = SentimentTrainer()
