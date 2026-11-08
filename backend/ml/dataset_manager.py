import os
import re
import json
import hashlib
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from sklearn.model_selection import StratifiedShuffleSplit

logger = logging.getLogger("feedbackiq.ml.dataset")

DATASETS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "ml_datasets")
os.makedirs(DATASETS_DIR, exist_ok=True)

# Standard category taxonomy
STANDARD_CATEGORIES = [
    "Login and Authentication",
    "Payment Issues",
    "Performance",
    "UI/UX",
    "Feature Requests",
    "Bugs and Crashes",
    "Customer Support",
    "Other"
]

CATEGORY_ALIASES = {
    "login": "Login and Authentication",
    "auth": "Login and Authentication",
    "authentication": "Login and Authentication",
    "signin": "Login and Authentication",
    "sign-in": "Login and Authentication",
    "payment": "Payment Issues",
    "payments": "Payment Issues",
    "billing": "Payment Issues",
    "invoice": "Payment Issues",
    "subscription": "Payment Issues",
    "refund": "Payment Issues",
    "price": "Payment Issues",
    "pricing": "Payment Issues",
    "slow": "Performance",
    "speed": "Performance",
    "lag": "Performance",
    "latency": "Performance",
    "freeze": "Performance",
    "ui": "UI/UX",
    "ux": "UI/UX",
    "design": "UI/UX",
    "layout": "UI/UX",
    "interface": "UI/UX",
    "theme": "UI/UX",
    "feature": "Feature Requests",
    "feature request": "Feature Requests",
    "suggestion": "Feature Requests",
    "request": "Feature Requests",
    "bug": "Bugs and Crashes",
    "bugs": "Bugs and Crashes",
    "crash": "Bugs and Crashes",
    "crashes": "Bugs and Crashes",
    "broken": "Bugs and Crashes",
    "error": "Bugs and Crashes",
    "glitch": "Bugs and Crashes",
    "support": "Customer Support",
    "help": "Customer Support",
    "service": "Customer Support",
    "agent": "Customer Support"
}

def normalize_text_for_dedup(text: str) -> str:
    """Normalizes text for hash-based exact and near-duplicate detection."""
    if not isinstance(text, str):
        return ""
    clean = text.lower().strip()
    clean = re.sub(r"[^\w\s]", "", clean)
    clean = re.sub(r"\s+", " ", clean)
    return clean

def text_hash(text: str) -> str:
    """Computes SHA-256 hash of normalized text."""
    norm = normalize_text_for_dedup(text)
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()

class DatasetManager:
    """
    Manages dataset ingestion, cleaning, label normalization, deduplication,
    statistics calculation, and leak-free stratified or temporal train/val/test splitting.
    """

    def normalize_sentiment(self, val: Any) -> Optional[str]:
        """Normalizes sentiment label into Positive, Negative, or Neutral."""
        if val is None or pd.isna(val):
            return None
        
        # Numeric scores
        if isinstance(val, (int, float)):
            if val in (1, 2):
                return "Negative"
            elif val == 3:
                return "Neutral"
            elif val in (4, 5):
                return "Positive"
        
        val_str = str(val).strip().lower()
        if val_str in ("positive", "pos", "1", "good", "happy"):
            return "Positive"
        elif val_str in ("negative", "neg", "-1", "bad", "unhappy"):
            return "Negative"
        elif val_str in ("neutral", "neu", "0", "mixed"):
            return "Neutral"
        return None

    def normalize_category(self, val: Any, fallback_text: str = "") -> str:
        """Normalizes category into one of the 8 canonical classes."""
        if val is not None and not pd.isna(val):
            val_clean = str(val).strip().lower()
            if val_clean in CATEGORY_ALIASES:
                return CATEGORY_ALIASES[val_clean]
            for cat in STANDARD_CATEGORIES:
                if cat.lower() in val_clean:
                    return cat

        # Text-based heuristic inference fallback if category is absent or unmapped
        if fallback_text:
            text_lower = fallback_text.lower()
            if any(k in text_lower for k in ["login", "sign in", "password", "auth", "credential", "logout", "account access"]):
                return "Login and Authentication"
            if any(k in text_lower for k in ["payment", "charge", "refund", "billing", "subscription", "price", "pro tier"]):
                return "Payment Issues"
            if any(k in text_lower for k in ["crash", "freeze", "bug", "broken", "glitch", "force close", "stopped working"]):
                return "Bugs and Crashes"
            if any(k in text_lower for k in ["slow", "lag", "latency", "hang", "takes forever", "stuck"]):
                return "Performance"
            if any(k in text_lower for k in ["ui", "button", "dark mode", "font", "color", "layout", "screen", "theme", "look"]):
                return "UI/UX"
            if any(k in text_lower for k in ["please add", "would love", "feature", "wish", "add option", "integration"]):
                return "Feature Requests"
            if any(k in text_lower for k in ["support", "email", "customer service", "agent", "ticket", "reply", "response"]):
                return "Customer Support"

        return "Other"

    def load_and_validate_csv(
        self, 
        file_path_or_buffer: Any, 
        dataset_name: str = "custom_dataset.csv"
    ) -> Dict[str, Any]:
        """
        Loads CSV, inspects columns, cleans missing values, validates labels,
        identifies duplicates, and compiles dataset statistics.
        """
        df = pd.read_csv(file_path_or_buffer)
        total_raw_rows = len(df)

        # Standardize column names
        col_map = {}
        for col in df.columns:
            c_low = col.strip().lower()
            if c_low in ("feedback", "content", "review", "text", "feedback_text", "comment"):
                col_map[col] = "feedback"
            elif c_low in ("sentiment", "label", "sentiment_label", "polarity"):
                col_map[col] = "sentiment"
            elif c_low in ("category", "issue_type", "type", "topic"):
                col_map[col] = "category"
            elif c_low in ("rating", "score", "stars"):
                col_map[col] = "rating"
            elif c_low in ("date", "timestamp", "created_at", "at", "time"):
                col_map[col] = "date"
            elif c_low in ("source", "app", "appid", "origin", "channel"):
                col_map[col] = "source"

        df = df.rename(columns=col_map)

        if "feedback" not in df.columns:
            raise ValueError(f"CSV must contain a feedback text column (found: {list(df.columns)})")

        # 1. Missing text handling
        df = df[df["feedback"].notna()]
        df["feedback"] = df["feedback"].astype(str).str.strip()
        df = df[df["feedback"].str.len() > 1]
        valid_after_empty_drop = len(df)

        # 2. Rating handling
        if "rating" in df.columns:
            df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
        else:
            df["rating"] = None

        # 3. Sentiment normalization & rating fallback
        if "sentiment" in df.columns:
            df["sentiment"] = df["sentiment"].apply(self.normalize_sentiment)
            # Fallback to rating if sentiment label is missing
            missing_sent = df["sentiment"].isna()
            if missing_sent.any() and "rating" in df.columns:
                df.loc[missing_sent, "sentiment"] = df.loc[missing_sent, "rating"].apply(self.normalize_sentiment)
        else:
            if "rating" in df.columns:
                df["sentiment"] = df["rating"].apply(self.normalize_sentiment)
            else:
                df["sentiment"] = None

        # 4. Category normalization
        if "category" in df.columns:
            df["category"] = [
                self.normalize_category(cat, fallback_text=fb)
                for cat, fb in zip(df["category"], df["feedback"])
            ]
        else:
            df["category"] = [
                self.normalize_category(None, fallback_text=fb)
                for fb in df["feedback"]
            ]

        # 5. Date parsing
        if "date" in df.columns:
            df["date_parsed"] = pd.to_datetime(df["date"], errors="coerce")
        else:
            df["date"] = datetime.utcnow().strftime("%Y-%m-%d")
            df["date_parsed"] = pd.to_datetime(df["date"])

        # 6. Source
        if "source" not in df.columns:
            df["source"] = "Customer Upload"

        # 7. Deduplication & Hash Computation (Strictly done BEFORE train/test split to prevent leakage)
        df["norm_hash"] = df["feedback"].apply(text_hash)
        duplicates_mask = df.duplicated(subset=["norm_hash"], keep="first")
        duplicate_count = int(duplicates_mask.sum())
        
        # Deduplicated dataset for supervised learning
        clean_df = df[~duplicates_mask].copy().reset_index(drop=True)
        final_clean_count = len(clean_df)

        # Compute Statistics
        lengths = clean_df["feedback"].str.split().apply(len)
        stats = {
            "dataset_name": dataset_name,
            "total_raw_rows": total_raw_rows,
            "valid_rows_retained": final_clean_count,
            "empty_rows_dropped": total_raw_rows - valid_after_empty_drop,
            "duplicates_removed": duplicate_count,
            "has_supervised_sentiment": bool(clean_df["sentiment"].notna().sum() > 0),
            "supervised_sentiment_count": int(clean_df["sentiment"].notna().sum()),
            "token_length": {
                "min": int(lengths.min()) if not lengths.empty else 0,
                "max": int(lengths.max()) if not lengths.empty else 0,
                "mean": round(float(lengths.mean()), 1) if not lengths.empty else 0.0,
                "median": int(lengths.median()) if not lengths.empty else 0
            },
            "sentiment_distribution": clean_df["sentiment"].value_counts(dropna=False).to_dict(),
            "category_distribution": clean_df["category"].value_counts(dropna=False).to_dict(),
            "has_timestamps": bool(clean_df["date_parsed"].notna().sum() > 0)
        }

        # Calculate imbalance ratio (max / min class count)
        sent_counts = [v for k, v in stats["sentiment_distribution"].items() if pd.notna(k) and v > 0]
        if sent_counts and min(sent_counts) > 0:
            stats["sentiment_imbalance_ratio"] = round(max(sent_counts) / min(sent_counts), 2)
        else:
            stats["sentiment_imbalance_ratio"] = 1.0

        return {
            "df": clean_df,
            "stats": stats
        }

    def create_splits(
        self,
        df: pd.DataFrame,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        split_strategy: str = "stratified",  # "stratified" or "temporal"
        random_seed: int = 42
    ) -> Dict[str, Any]:
        """
        Creates train/validation/test splits with zero data leakage guarantees.
        Supports Stratified splitting and Chronological Temporal splitting.
        """
        # Ensure ratios sum to 1.0
        total_ratio = train_ratio + val_ratio + test_ratio
        train_ratio = train_ratio / total_ratio
        val_ratio = val_ratio / total_ratio
        test_ratio = test_ratio / total_ratio

        n = len(df)
        if n < 10:
            raise ValueError(f"Dataset too small to split meaningfully ({n} records, minimum 10 required)")

        # Filter records that have valid sentiment labels for supervised training
        labeled_df = df[df["sentiment"].notna()].copy().reset_index(drop=True)
        if len(labeled_df) < 10:
            labeled_df = df.copy().reset_index(drop=True)
            labeled_df["sentiment"] = labeled_df["sentiment"].fillna("Neutral")

        if split_strategy == "temporal" and "date_parsed" in labeled_df.columns and labeled_df["date_parsed"].notna().any():
            # Temporal Chronological Split
            sorted_df = labeled_df.sort_values(by="date_parsed", ascending=True).reset_index(drop=True)
            train_end = int(n * train_ratio)
            val_end = int(n * (train_ratio + val_ratio))

            train_df = sorted_df.iloc[:train_end].copy()
            val_df = sorted_df.iloc[train_end:val_end].copy()
            test_df = sorted_df.iloc[val_end:].copy()
        else:
            # Stratified Split on Sentiment
            y = labeled_df["sentiment"].values
            
            # Step 1: Split into train and temp (val + test)
            temp_ratio = val_ratio + test_ratio
            sss1 = StratifiedShuffleSplit(n_splits=1, test_size=temp_ratio, random_state=random_seed)
            try:
                train_idx, temp_idx = next(sss1.split(labeled_df, y))
            except Exception:
                # Fallback to random shuffle if a class has fewer than 2 members
                np.random.seed(random_seed)
                perm = np.random.permutation(len(labeled_df))
                split_pt = int(len(labeled_df) * train_ratio)
                train_idx, temp_idx = perm[:split_pt], perm[split_pt:]

            train_df = labeled_df.iloc[train_idx].copy().reset_index(drop=True)
            temp_df = labeled_df.iloc[temp_idx].copy().reset_index(drop=True)

            # Step 2: Split temp into val and test
            rel_test_ratio = test_ratio / temp_ratio
            sss2 = StratifiedShuffleSplit(n_splits=1, test_size=rel_test_ratio, random_state=random_seed)
            try:
                val_idx, test_idx = next(sss2.split(temp_df, temp_df["sentiment"].values))
            except Exception:
                perm_temp = np.random.permutation(len(temp_df))
                val_pt = int(len(temp_df) * (1 - rel_test_ratio))
                val_idx, test_idx = perm_temp[:val_pt], perm_temp[val_pt:]

            val_df = temp_df.iloc[val_idx].copy().reset_index(drop=True)
            test_df = temp_df.iloc[test_idx].copy().reset_index(drop=True)

        # Leakage Verification: confirm 0% normalized hash overlap across splits
        leakage_report = self.verify_no_leakage(train_df, val_df, test_df)

        split_summary = {
            "strategy": split_strategy,
            "train_count": len(train_df),
            "val_count": len(val_df),
            "test_count": len(test_df),
            "train_sentiment": train_df["sentiment"].value_counts().to_dict(),
            "val_sentiment": val_df["sentiment"].value_counts().to_dict(),
            "test_sentiment": test_df["sentiment"].value_counts().to_dict(),
            "train_categories": train_df["category"].value_counts().to_dict(),
            "val_categories": val_df["category"].value_counts().to_dict(),
            "test_categories": test_df["category"].value_counts().to_dict(),
            "leakage_verification": leakage_report
        }

        return {
            "train_df": train_df,
            "val_df": val_df,
            "test_df": test_df,
            "summary": split_summary
        }

    def verify_no_leakage(
        self, 
        train_df: pd.DataFrame, 
        val_df: pd.DataFrame, 
        test_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Guarantees zero data leakage by checking text hash intersections between all partition pairs.
        """
        train_hashes = set(train_df["norm_hash"].tolist()) if "norm_hash" in train_df.columns else set(train_df["feedback"].apply(text_hash))
        val_hashes = set(val_df["norm_hash"].tolist()) if "norm_hash" in val_df.columns else set(val_df["feedback"].apply(text_hash))
        test_hashes = set(test_df["norm_hash"].tolist()) if "norm_hash" in test_df.columns else set(test_df["feedback"].apply(text_hash))

        train_val_overlap = len(train_hashes.intersection(val_hashes))
        train_test_overlap = len(train_hashes.intersection(test_hashes))
        val_test_overlap = len(val_hashes.intersection(test_hashes))

        is_leak_free = (train_val_overlap == 0 and train_test_overlap == 0 and val_test_overlap == 0)

        return {
            "leak_free": is_leak_free,
            "train_val_overlap_count": train_val_overlap,
            "train_test_overlap_count": train_test_overlap,
            "val_test_overlap_count": val_test_overlap,
            "train_unique_hashes": len(train_hashes),
            "val_unique_hashes": len(val_hashes),
            "test_unique_hashes": len(test_hashes)
        }

    def save_dataset_package(
        self, 
        dataset_id: str, 
        dataset_name: str, 
        train_df: pd.DataFrame, 
        val_df: pd.DataFrame, 
        test_df: pd.DataFrame, 
        stats: Dict[str, Any],
        split_summary: Dict[str, Any]
    ) -> str:
        """Saves processed dataset and splits to disk as serialized JSON package."""
        package = {
            "dataset_id": dataset_id,
            "dataset_name": dataset_name,
            "created_at": datetime.utcnow().isoformat(),
            "stats": stats,
            "split_summary": split_summary,
            "train_data": train_df[["feedback", "sentiment", "category", "rating", "source", "date"]].to_dict(orient="records"),
            "val_data": val_df[["feedback", "sentiment", "category", "rating", "source", "date"]].to_dict(orient="records"),
            "test_data": test_df[["feedback", "sentiment", "category", "rating", "source", "date"]].to_dict(orient="records")
        }
        
        file_path = os.path.join(DATASETS_DIR, f"{dataset_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(package, f, indent=2, default=str)
        logger.info(f"Saved dataset package {dataset_id} to {file_path}")
        return file_path

    def load_dataset_package(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """Loads serialized dataset package by ID."""
        file_path = os.path.join(DATASETS_DIR, f"{dataset_id}.json")
        if not os.path.exists(file_path):
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_datasets(self) -> List[Dict[str, Any]]:
        """Lists all ingested datasets with high-level statistics."""
        datasets = []
        if not os.path.exists(DATASETS_DIR):
            return []
        for fn in os.listdir(DATASETS_DIR):
            if fn.endswith(".json"):
                fp = os.path.join(DATASETS_DIR, fn)
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    datasets.append({
                        "dataset_id": data.get("dataset_id"),
                        "dataset_name": data.get("dataset_name"),
                        "created_at": data.get("created_at"),
                        "total_rows": data.get("stats", {}).get("valid_rows_retained", 0),
                        "train_count": data.get("split_summary", {}).get("train_count", 0),
                        "val_count": data.get("split_summary", {}).get("val_count", 0),
                        "test_count": data.get("split_summary", {}).get("test_count", 0),
                        "sentiment_distribution": data.get("stats", {}).get("sentiment_distribution", {}),
                        "category_distribution": data.get("stats", {}).get("category_distribution", {})
                    })
                except Exception as e:
                    logger.warning(f"Error reading dataset file {fn}: {e}")
        return sorted(datasets, key=lambda d: d.get("created_at", ""), reverse=True)

dataset_manager = DatasetManager()
