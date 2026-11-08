import os
import json
import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Ensure Python trusts Windows system certificates (e.g. for antivirus shields/proxies)
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logger = logging.getLogger("feedbackiq.db")

SUPABASE_URL = os.getenv("SUPABASE_URL", os.getenv("VITE_SUPABASE_URL", "")).strip()
# Use Service Role Key on backend if available for administrative RLS bypass, otherwise Anon Key
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY") or 
    os.getenv("SUPABASE_KEY") or 
    os.getenv("VITE_SUPABASE_ANON_KEY") or 
    os.getenv("SUPABASE_ANON_KEY", "")
).strip()

LOCAL_STORAGE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "local_db.json")


def is_valid_uuid(val: Any) -> bool:
    """Checks whether a string or value is a valid UUID."""
    if not val or not isinstance(val, str):
        return False
    try:
        uuid.UUID(val)
        return True
    except (ValueError, AttributeError):
        return False


class DatabaseClient:
    def __init__(self):
        self.supabase = None
        self.use_supabase = False
        self.mode = "Local Storage (JSON)"
        self._local_data: Dict[str, Any] = {
            "active_analysis_id": None,
            "analysis_history": [],
            "themes": [],
            "feedback": []
        }
        self._init_storage()

    def _init_storage(self):
        """Initializes database connection to Supabase or sets up local JSON store."""
        os.makedirs(os.path.dirname(LOCAL_STORAGE_PATH), exist_ok=True)

        has_creds = bool(
            SUPABASE_URL and 
            SUPABASE_KEY and 
            not SUPABASE_URL.startswith("https://your-") and 
            not SUPABASE_URL.startswith("your_") and
            not SUPABASE_KEY.startswith("your_")
        )

        if has_creds:
            try:
                from supabase import create_client
                client = create_client(SUPABASE_URL, SUPABASE_KEY)
                # Test connection by making a lightweight read
                _ = client.table("analyses").select("id").limit(1).execute()
                self.supabase = client
                self.use_supabase = True
                self.mode = "Supabase PostgreSQL"
                logger.info("Successfully connected to Supabase PostgreSQL.")
            except Exception as e:
                # If table doesn't exist yet or connection fails, log friendly notice
                logger.warning(
                    f"Supabase connection notice: {e}. Falling back to Local Storage mode."
                )
                self.use_supabase = False
                self.mode = "Local Storage (JSON)"
        else:
            logger.info("No remote Supabase credentials supplied; running in Local Storage mode.")
            self.use_supabase = False
            self.mode = "Local Storage (JSON)"

        # Initialize local JSON cache/fallback
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
        """Reloads JSON from disk if another background thread or process updated it."""
        if os.path.exists(LOCAL_STORAGE_PATH):
            try:
                mtime = os.path.getmtime(LOCAL_STORAGE_PATH)
                if getattr(self, "_last_mtime", 0) < mtime:
                    with open(LOCAL_STORAGE_PATH, "r", encoding="utf-8") as f:
                        self._local_data = json.load(f)
                    self._last_mtime = mtime
            except Exception:
                pass

    def _save_local(self):
        """Saves current state to local JSON file."""
        try:
            with open(LOCAL_STORAGE_PATH, "w", encoding="utf-8") as f:
                json.dump(self._local_data, f, indent=2, default=str)
            if os.path.exists(LOCAL_STORAGE_PATH):
                self._last_mtime = os.path.getmtime(LOCAL_STORAGE_PATH)
        except Exception as e:
            logger.error(f"Failed to persist local database: {e}")

    def get_system_status(self) -> Dict[str, Any]:
        """Returns active database operational metadata and record counts."""
        self._sync_local_data()
        return {
            "online": True,
            "mode": self.mode,
            "database_type": "supabase" if self.use_supabase else "local",
            "connected": self.use_supabase,
            "active_analysis_id": self._local_data.get("active_analysis_id"),
            "records_count": len(self.get_all_feedback()),
            "themes_count": len(self.get_themes()),
            "analyses_count": len(self.get_history())
        }

    # ==========================================================
    # ANALYSIS HISTORY & PERSISTENCE OPERATIONS
    # ==========================================================
    def create_analysis_session(
        self, 
        analysis_name: str, 
        feedback_records: List[Dict[str, Any]], 
        themes: List[Dict[str, Any]], 
        user_id: Optional[str] = None
    ) -> str:
        """
        Persists a complete analysis session:
        1. Generates a standard UUID for the analysis session.
        2. Persists to 'analyses' and 'analysis_history' tables.
        3. Persists all themes and AI summaries.
        4. Persists all labeled feedback records.
        5. Synchronizes local storage cache so dashboard and explorer reflect changes instantly.
        """
        analysis_id = str(uuid.uuid4())
        total = len(feedback_records)
        pos = sum(1 for it in feedback_records if it.get("sentiment") == "Positive")
        neg = sum(1 for it in feedback_records if it.get("sentiment") == "Negative")
        neu = sum(1 for it in feedback_records if it.get("sentiment") == "Neutral")

        pos_pct = round((pos / total) * 100, 1) if total > 0 else 0.0
        neg_pct = round((neg / total) * 100, 1) if total > 0 else 0.0
        neu_pct = round((neu / total) * 100, 1) if total > 0 else 0.0
        now_iso = datetime.utcnow().isoformat()

        # Clean user_id (must be valid UUID for Postgres public.profiles foreign key, else None)
        valid_user_id = user_id if is_valid_uuid(user_id) else None

        # Analysis Master Record
        analysis_record = {
            "id": analysis_id,
            "user_id": valid_user_id,
            "analysis_name": analysis_name,
            "total_feedback": total,
            "positive_count": pos,
            "negative_count": neg,
            "neutral_count": neu,
            "positive_percentage": pos_pct,
            "negative_percentage": neg_pct,
            "neutral_percentage": neu_pct,
            "hindsight_status": "pending",
            "hindsight_memory_id": None,
            "hindsight_retained_at": None,
            "created_at": now_iso
        }

        # Analysis History Audit Record
        history_record = {
            "id": str(uuid.uuid4()),
            "analysis_id": analysis_id,
            "user_id": valid_user_id,
            "analysis_name": analysis_name,
            "total_feedback": total,
            "positive_percentage": pos_pct,
            "negative_percentage": neg_pct,
            "neutral_percentage": neu_pct,
            "hindsight_status": "pending",
            "created_at": now_iso
        }

        # Tag feedback records with session IDs
        for it in feedback_records:
            it["analysis_id"] = analysis_id
            if valid_user_id:
                it["user_id"] = valid_user_id

        # Tag themes with session IDs
        for t in themes:
            t["analysis_id"] = analysis_id
            if valid_user_id:
                t["user_id"] = valid_user_id

        # ----------------------------------------------------------
        # Persist to Supabase if connected
        # ----------------------------------------------------------
        if self.use_supabase and self.supabase:
            try:
                # 1. Insert into 'analyses'
                self.supabase.table("analyses").insert(analysis_record).execute()

                # 2. Insert into 'analysis_history'
                self.supabase.table("analysis_history").insert(history_record).execute()

                # 3. Clean and insert themes
                clean_themes = []
                for t in themes:
                    t_id = str(t.get("id") or f"theme_{uuid.uuid4().hex[:6]}")
                    clean_themes.append({
                        "id": t_id,
                        "analysis_id": analysis_id,
                        "user_id": valid_user_id,
                        "theme_name": t.get("theme_name") or t.get("name", "General"),
                        "summary": t.get("ai_summary") or t.get("summary", ""),
                        "mention_count": t.get("mention_count", 0),
                        "positive_percentage": float(t.get("positive_percentage") or (t.get("sentiment_distribution", {}).get("Positive") if isinstance(t.get("sentiment_distribution"), dict) else 0.0)),
                        "negative_percentage": float(t.get("negative_percentage") or (t.get("sentiment_distribution", {}).get("Negative") if isinstance(t.get("sentiment_distribution"), dict) else 0.0)),
                        "neutral_percentage": float(t.get("neutral_percentage") or (t.get("sentiment_distribution", {}).get("Neutral") if isinstance(t.get("sentiment_distribution"), dict) else 0.0)),
                        "severity": t.get("severity", "Medium"),
                        "priority": t.get("priority") or t.get("priority_level", "Medium"),
                        "priority_score": float(t.get("priority_score", 0.0)),
                        "recommendation": t.get("recommendation") or t.get("suggested_action") or t.get("recommended_action", ""),
                        "main_complaint": t.get("main_complaint", ""),
                        "is_feature_request": bool(t.get("is_feature_request", False)),
                        "key_observations": t.get("key_observations", []),
                        "representative_feedback": t.get("representative_feedback") or t.get("representative_comments", [])
                    })
                if clean_themes:
                    self.supabase.table("themes").insert(clean_themes).execute()

                # 4. Clean and insert feedback records in batches
                clean_feedback = []
                for f in feedback_records:
                    f_id = f.get("id")
                    if not is_valid_uuid(f_id):
                        f_id = str(uuid.uuid4())
                        f["id"] = f_id

                    clean_feedback.append({
                        "id": f_id,
                        "analysis_id": analysis_id,
                        "user_id": valid_user_id,
                        "feedback_text": f.get("feedback_text") or f.get("feedback") or f.get("text", ""),
                        "sentiment": f.get("sentiment", "Neutral"),
                        "sentiment_confidence": float(f.get("confidence") or f.get("sentiment_confidence") or 0.85),
                        "theme_id": f.get("theme_id"),
                        "source": f.get("source", "Web App"),
                        "rating": int(f["rating"]) if f.get("rating") is not None and str(f.get("rating")).isdigit() else None,
                        "date": str(f.get("date", "")),
                        "created_at": now_iso
                    })

                # Batch insert feedback (200 records at a time)
                batch_size = 200
                for i in range(0, len(clean_feedback), batch_size):
                    chunk = clean_feedback[i : i + batch_size]
                    self.supabase.table("feedback").insert(chunk).execute()

                logger.info(f"Persisted analysis {analysis_id} with {len(clean_feedback)} feedback items to Supabase.")
            except Exception as e:
                logger.warning(f"Supabase persistence error ({e}), ensuring local JSON persistence.")

        # ----------------------------------------------------------
        # Persist to Local Storage Cache
        # ----------------------------------------------------------
        local_session_entry = dict(analysis_record)
        local_session_entry["themes_count"] = len(themes)
        self._local_data["analysis_history"].insert(0, local_session_entry)
        self._local_data["active_analysis_id"] = analysis_id
        self._local_data["themes"] = themes
        self._local_data["feedback"] = feedback_records
        self._save_local()

        return analysis_id

    def get_history(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns list of past analysis sessions (scoped to user_id if provided)."""
        self._sync_local_data()

        if self.use_supabase and self.supabase:
            try:
                # Query analyses table
                query = self.supabase.table("analyses").select("*").order("created_at", desc=True)
                if user_id and is_valid_uuid(user_id):
                    query = query.or_(f"user_id.eq.{user_id},user_id.is.null")
                res = query.execute()
                if res.data:
                    return res.data
            except Exception as e:
                logger.warning(f"Supabase get_history failed ({e}), loading from local store.")

        hist = self._local_data.get("analysis_history", [])
        if user_id:
            return [h for h in hist if h.get("user_id") == user_id or not h.get("user_id")]
        return hist

    def get_analysis_by_id(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves session metadata, themes, and feedback for a specific analysis ID."""
        if self.use_supabase and self.supabase:
            try:
                hist_res = self.supabase.table("analyses").select("*").eq("id", analysis_id).execute()
                themes_res = self.supabase.table("themes").select("*").eq("analysis_id", analysis_id).execute()
                feedback_res = self.supabase.table("feedback").select("*").eq("analysis_id", analysis_id).execute()
                if hist_res.data:
                    return {
                        "session": hist_res.data[0],
                        "themes": themes_res.data or [],
                        "feedback": feedback_res.data or []
                    }
            except Exception as e:
                logger.warning(f"Supabase get_analysis_by_id failed ({e}), checking local store.")

        # Local fallback
        self._sync_local_data()
        session = next((h for h in self._local_data.get("analysis_history", []) if h["id"] == analysis_id), None)
        if session:
            if self._local_data.get("active_analysis_id") == analysis_id:
                return {
                    "session": session,
                    "themes": self._local_data.get("themes", []),
                    "feedback": self._local_data.get("feedback", [])
                }
            matched_fb = [f for f in self._local_data.get("feedback", []) if f.get("analysis_id") == analysis_id]
            matched_themes = [t for t in self._local_data.get("themes", []) if t.get("analysis_id") == analysis_id]
            return {
                "session": session,
                "themes": matched_themes or self._local_data.get("themes", []),
                "feedback": matched_fb or self._local_data.get("feedback", [])
            }
        return None

    def activate_analysis(self, analysis_id: str) -> bool:
        """Switches the active analysis session in memory and local store."""
        data = self.get_analysis_by_id(analysis_id)
        if not data:
            return False
        self._local_data["active_analysis_id"] = analysis_id
        self._local_data["themes"] = data["themes"]
        self._local_data["feedback"] = data["feedback"]
        self._save_local()
        logger.info(f"Activated analysis session {analysis_id}.")
        return True

    def update_analysis_hindsight_status(
        self,
        analysis_id: str,
        status: str,
        memory_id: Optional[str] = None
    ) -> bool:
        """Updates Hindsight retention status ('pending', 'retained', 'failed') in Supabase and local storage."""
        now_iso = datetime.now().isoformat()
        updated = False

        if self.use_supabase and self.supabase:
            try:
                update_payload: Dict[str, Any] = {
                    "hindsight_status": status,
                    "hindsight_retained_at": now_iso
                }
                if memory_id:
                    update_payload["hindsight_memory_id"] = memory_id
                
                self.supabase.table("analyses").update(update_payload).eq("id", analysis_id).execute()
                updated = True
                logger.info(f"Updated Supabase analysis {analysis_id} hindsight_status='{status}'.")
            except Exception as e:
                logger.warning(f"Failed to update hindsight_status in Supabase: {e}")

        # Update in local storage
        self._sync_local_data()
        for session in self._local_data.get("analysis_history", []):
            if session.get("analysis_id") == analysis_id or session.get("id") == analysis_id:
                session["hindsight_status"] = status
                if memory_id:
                    session["hindsight_memory_id"] = memory_id
                session["hindsight_retained_at"] = now_iso
                updated = True
        self._save_local()
        return updated

    def delete_analysis(self, analysis_id: str, user_id: Optional[str] = None) -> bool:
        """Deletes an analysis session and cascades deletion of its themes and feedback."""
        if self.use_supabase and self.supabase:
            try:
                # In Postgres, ON DELETE CASCADE handles child feedback, themes, and history
                self.supabase.table("analyses").delete().eq("id", analysis_id).execute()
                self.supabase.table("analysis_history").delete().eq("analysis_id", analysis_id).execute()
                logger.info(f"Deleted analysis session {analysis_id} from Supabase.")
            except Exception as e:
                logger.warning(f"Supabase delete_analysis failed ({e}).")

        # Local deletion
        self._sync_local_data()
        self._local_data["analysis_history"] = [
            h for h in self._local_data.get("analysis_history", []) if h["id"] != analysis_id
        ]
        if self._local_data.get("active_analysis_id") == analysis_id:
            if self._local_data["analysis_history"]:
                next_active = self._local_data["analysis_history"][0]["id"]
                self.activate_analysis(next_active)
            else:
                self._local_data["active_analysis_id"] = None
                self._local_data["themes"] = []
                self._local_data["feedback"] = []
        self._save_local()
        return True

    # ==========================================================
    # ACTIVE WORKSPACE DATA ACCESS
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
        """Returns filtered and paginated feedback from the active workspace."""
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
