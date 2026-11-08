import os
import json
import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("feedbackiq.db")

SUPABASE_URL = os.getenv("SUPABASE_URL", os.getenv("VITE_SUPABASE_URL", "")).strip()
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_KEY", os.getenv("SUPABASE_ANON_KEY", ""))).strip()

LOCAL_STORAGE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "local_db.json")

class DatabaseClient:
    def __init__(self):
        self.use_supabase = bool(
            SUPABASE_URL and 
            SUPABASE_KEY and 
            not SUPABASE_URL.startswith("your_") and 
            not SUPABASE_KEY.startswith("your_")
        )
        self.supabase = None
        self._local_data: Dict[str, Any] = {
            "active_analysis_id": None,
            "analysis_history": [],
            "themes": [],
            "feedback": []
        }
        self._init_storage()

    def _init_storage(self):
        os.makedirs(os.path.dirname(LOCAL_STORAGE_PATH), exist_ok=True)
        if self.use_supabase:
            try:
                from supabase import create_client
                self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
                logger.info("Connected successfully to Supabase PostgreSQL.")
            except Exception as e:
                logger.warning(f"Supabase initialization error ({e}), operating in local JSON mode.")
                self.use_supabase = False

        # Load local storage as fallback and cache
        self._last_mtime = 0
        if os.path.exists(LOCAL_STORAGE_PATH):
            try:
                self._last_mtime = os.path.getmtime(LOCAL_STORAGE_PATH)
                with open(LOCAL_STORAGE_PATH, "r", encoding="utf-8") as f:
                    self._local_data = json.load(f)
                    if "active_analysis_id" not in self._local_data:
                        self._local_data["active_analysis_id"] = None
                    if "analysis_history" not in self._local_data:
                        self._local_data["analysis_history"] = []
                    if "themes" not in self._local_data:
                        self._local_data["themes"] = []
                    if "feedback" not in self._local_data:
                        self._local_data["feedback"] = []
            except Exception as e:
                logger.error(f"Error reading local database JSON: {e}")
                self._save_local()
        else:
            self._save_local()

    def _sync_local_data(self):
        """Reloads JSON from disk if another process updated it."""
        if not self.use_supabase and os.path.exists(LOCAL_STORAGE_PATH):
            try:
                mtime = os.path.getmtime(LOCAL_STORAGE_PATH)
                if getattr(self, "_last_mtime", 0) < mtime:
                    with open(LOCAL_STORAGE_PATH, "r", encoding="utf-8") as f:
                        self._local_data = json.load(f)
                    self._last_mtime = mtime
            except Exception:
                pass

    def _save_local(self):
        try:
            with open(LOCAL_STORAGE_PATH, "w", encoding="utf-8") as f:
                json.dump(self._local_data, f, indent=2, default=str)
            if os.path.exists(LOCAL_STORAGE_PATH):
                self._last_mtime = os.path.getmtime(LOCAL_STORAGE_PATH)
        except Exception as e:
            logger.error(f"Failed to persist local database: {e}")

    # ==========================================================
    # ANALYSIS HISTORY OPERATIONS
    # ==========================================================
    def create_analysis_session(
        self, 
        analysis_name: str, 
        feedback_records: List[Dict[str, Any]], 
        themes: List[Dict[str, Any]], 
        user_id: Optional[str] = None
    ) -> str:
        """Saves a new analysis session and links all feedback and themes."""
        analysis_id = f"analysis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        total = len(feedback_records)
        pos = sum(1 for it in feedback_records if it.get("sentiment") == "Positive")
        neg = sum(1 for it in feedback_records if it.get("sentiment") == "Negative")
        neu = sum(1 for it in feedback_records if it.get("sentiment") == "Neutral")

        session_record = {
            "id": analysis_id,
            "user_id": user_id,
            "analysis_name": analysis_name,
            "total_feedback": total,
            "positive_count": pos,
            "negative_count": neg,
            "neutral_count": neu,
            "positive_percentage": round((pos / total) * 100, 1) if total > 0 else 0.0,
            "negative_percentage": round((neg / total) * 100, 1) if total > 0 else 0.0,
            "neutral_percentage": round((neu / total) * 100, 1) if total > 0 else 0.0,
            "themes_count": len(themes),
            "created_at": datetime.utcnow().isoformat()
        }

        # Tag feedback and themes with analysis_id and user_id
        for it in feedback_records:
            it["analysis_id"] = analysis_id
            if user_id:
                it["user_id"] = user_id

        for t in themes:
            t["analysis_id"] = analysis_id
            if user_id:
                t["user_id"] = user_id

        # Supabase Persistence
        if self.use_supabase and self.supabase:
            try:
                self.supabase.table("analysis_history").insert(session_record).execute()
                
                # Insert themes
                clean_themes = []
                for t in themes:
                    ct = {
                        "id": t["id"],
                        "analysis_id": analysis_id,
                        "user_id": user_id,
                        "theme_name": t.get("theme_name") or t.get("name", "Unknown"),
                        "summary": t.get("ai_summary") or t.get("summary", ""),
                        "mention_count": t.get("mention_count", 0),
                        "positive_percentage": t.get("positive_percentage", 0.0),
                        "negative_percentage": t.get("negative_percentage", 0.0),
                        "neutral_percentage": t.get("neutral_percentage", 0.0),
                        "severity": t.get("severity", "Low"),
                        "priority": t.get("priority") or t.get("priority_level", "Medium"),
                        "recommendation": t.get("recommendation") or t.get("suggested_action", ""),
                        "main_complaint": t.get("main_complaint", ""),
                        "key_observations": t.get("key_observations", []),
                        "representative_feedback": t.get("representative_feedback") or t.get("representative_comments", [])
                    }
                    clean_themes.append(ct)
                self.supabase.table("themes").insert(clean_themes).execute()

                # Insert feedback
                clean_feedback = []
                for f in feedback_records:
                    cf = {
                        "id": f["id"],
                        "user_id": user_id,
                        "analysis_id": analysis_id,
                        "feedback_text": f["feedback_text"],
                        "sentiment": f["sentiment"],
                        "sentiment_confidence": float(f.get("confidence") or f.get("sentiment_confidence") or 0.9),
                        "theme_id": f.get("theme_id"),
                        "source": f.get("source", "Web App"),
                        "rating": f.get("rating")
                    }
                    clean_feedback.append(cf)
                self.supabase.table("feedback").insert(clean_feedback).execute()
            except Exception as e:
                logger.warning(f"Failed inserting analysis into Supabase ({e}), persisting locally.")

        # Local storage persistence
        self._local_data["analysis_history"].insert(0, session_record)
        self._local_data["active_analysis_id"] = analysis_id
        self._local_data["themes"] = themes
        self._local_data["feedback"] = feedback_records
        self._save_local()

        return analysis_id

    def get_history(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns list of previous analyses."""
        self._sync_local_data()
        if self.use_supabase and self.supabase:
            try:
                query = self.supabase.table("analysis_history").select("*").order("created_at", desc=True)
                if user_id:
                    query = query.eq("user_id", user_id)
                res = query.execute()
                if res.data:
                    return res.data
            except Exception as e:
                logger.warning(f"Supabase get_history failed ({e}), loading local.")

        hist = self._local_data.get("analysis_history", [])
        if user_id:
            return [h for h in hist if h.get("user_id") == user_id or not h.get("user_id")]
        return hist

    def get_analysis_by_id(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves themes and feedback for a specific analysis session."""
        if self.use_supabase and self.supabase:
            try:
                hist_res = self.supabase.table("analysis_history").select("*").eq("id", analysis_id).execute()
                themes_res = self.supabase.table("themes").select("*").eq("analysis_id", analysis_id).execute()
                feedback_res = self.supabase.table("feedback").select("*").eq("analysis_id", analysis_id).execute()
                if hist_res.data:
                    return {
                        "session": hist_res.data[0],
                        "themes": themes_res.data or [],
                        "feedback": feedback_res.data or []
                    }
            except Exception as e:
                logger.warning(f"Supabase get_analysis_by_id error ({e}), checking local storage.")

        # Check local storage
        session = next((h for h in self._local_data.get("analysis_history", []) if h["id"] == analysis_id), None)
        if session:
            # If active, get directly
            if self._local_data.get("active_analysis_id") == analysis_id:
                return {
                    "session": session,
                    "themes": self._local_data.get("themes", []),
                    "feedback": self._local_data.get("feedback", [])
                }
            # Or filter from feedback/themes
            matched_fb = [f for f in self._local_data.get("feedback", []) if f.get("analysis_id") == analysis_id]
            matched_themes = [t for t in self._local_data.get("themes", []) if t.get("analysis_id") == analysis_id]
            return {
                "session": session,
                "themes": matched_themes or self._local_data.get("themes", []),
                "feedback": matched_fb or self._local_data.get("feedback", [])
            }
        return None

    def activate_analysis(self, analysis_id: str) -> bool:
        """Switches active analysis session to the specified ID."""
        data = self.get_analysis_by_id(analysis_id)
        if not data:
            return False
        self._local_data["active_analysis_id"] = analysis_id
        self._local_data["themes"] = data["themes"]
        self._local_data["feedback"] = data["feedback"]
        self._save_local()
        return True

    def delete_analysis(self, analysis_id: str, user_id: Optional[str] = None) -> bool:
        """Deletes an analysis session and associated themes and feedback."""
        if self.use_supabase and self.supabase:
            try:
                self.supabase.table("analysis_history").delete().eq("id", analysis_id).execute()
            except Exception as e:
                logger.warning(f"Supabase delete_analysis failed ({e}).")

        # Local deletion
        self._local_data["analysis_history"] = [
            h for h in self._local_data.get("analysis_history", []) if h["id"] != analysis_id
        ]
        if self._local_data.get("active_analysis_id") == analysis_id:
            # Revert to latest remaining analysis or clear
            if self._local_data["analysis_history"]:
                latest = self._local_data["analysis_history"][0]["id"]
                self.activate_analysis(latest)
            else:
                self._local_data["active_analysis_id"] = None
                self._local_data["themes"] = []
                self._local_data["feedback"] = []
        self._save_local()
        return True

    # ==========================================================
    # FEEDBACK & THEMES RETRIEVAL (ACTIVE SESSION)
    # ==========================================================
    def get_feedback(
        self, 
        sentiment: Optional[str] = None, 
        theme_id: Optional[str] = None, 
        search: Optional[str] = None,
        sort_by: str = "date",
        sort_order: str = "desc",
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        self._sync_local_data()
        all_items = self._local_data.get("feedback", [])

        filtered = all_items
        if sentiment and sentiment.lower() != "all":
            filtered = [f for f in filtered if f.get("sentiment", "").lower() == sentiment.lower()]
        if theme_id and theme_id.lower() != "all":
            filtered = [
                f for f in filtered 
                if f.get("theme_id") == theme_id or 
                   f.get("theme_name") == theme_id or 
                   (theme_id.lower() in (f.get("theme_name") or "").lower())
            ]
        if search:
            s = search.lower()
            filtered = [
                f for f in filtered 
                if s in f.get("feedback_text", "").lower() or s in f.get("source", "").lower()
            ]

        # Sort
        reverse = (sort_order.lower() == "desc")
        def sort_key(item):
            val = item.get(sort_by, "")
            return val if val is not None else ""

        filtered.sort(key=sort_key, reverse=reverse)
        total = len(filtered)
        paginated = filtered[offset : offset + limit]

        return {
            "total": total,
            "items": paginated
        }

    def save_themes(self, themes: List[Dict[str, Any]]):
        self._local_data["themes"] = themes
        self._save_local()

    def save_feedback(self, records: List[Dict[str, Any]]):
        self._local_data["feedback"] = records
        self._save_local()

    def get_themes(self) -> List[Dict[str, Any]]:
        self._sync_local_data()
        return sorted(
            self._local_data.get("themes", []), 
            key=lambda t: t.get("priority_rank", 99)
        )

    def get_all_feedback(self) -> List[Dict[str, Any]]:
        self._sync_local_data()
        return self._local_data.get("feedback", [])

    def clear_all(self):
        self._local_data = {
            "active_analysis_id": None,
            "analysis_history": [],
            "themes": [],
            "feedback": []
        }
        self._save_local()

db = DatabaseClient()
