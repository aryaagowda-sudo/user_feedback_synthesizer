"""
FeedbackIQ — Hindsight AI Integration Service
Strict $5 Credit Conservation Mode

Architecture:
- Supabase PostgreSQL: Structured records, sentiment metrics, theme statistics, history, numerical comparisons.
- Hindsight AI: Long-term contextual memory, compact cross-session summaries, on-demand historical recall.

Cost Control Safeguards:
1. Strict call minimization: max 1 retain per completed analysis; max 1 recall per on-demand query.
2. Zero API calls during CSV ingestion, preprocessing, sentiment inference, clustering, or navigation.
3. Idempotency protection: analyses already retained are never re-sent to Hindsight.
4. Response caching: TTL-based in-memory cache prevents duplicate recall queries.
5. Exact numerical analytics calculated 100% locally from Supabase; Hindsight used only for contextual memory.
6. Configurable circuit breaker and call counter to protect user credits.
7. Graceful degradation: FeedbackIQ functions seamlessly via local/Supabase storage when Hindsight is disabled.
"""

import os
import time
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from dotenv import load_dotenv

# Ensure Python trusts Windows system certificates for HTTPS
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

logger = logging.getLogger("feedbackiq.hindsight")

# ----------------------------------------------------------------------
# Configuration & Guardrails
# ----------------------------------------------------------------------
HINDSIGHT_ENABLED = os.getenv("HINDSIGHT_ENABLED", "true").lower() in ("true", "1", "yes")
HINDSIGHT_API_KEY = os.getenv("HINDSIGHT_API_KEY", "").strip()
HINDSIGHT_BASE_URL = os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io").strip()
HINDSIGHT_BANK_ID = os.getenv("HINDSIGHT_BANK_ID", "feedbackiq_memory").strip()

# Limits & Quotas (Strict credit conservation)
HINDSIGHT_MAX_RETAINS_PER_ANALYSIS = int(os.getenv("HINDSIGHT_MAX_RETAINS_PER_ANALYSIS", "1"))
HINDSIGHT_MAX_RECALLS_PER_REQUEST = int(os.getenv("HINDSIGHT_MAX_RECALLS_PER_REQUEST", "1"))
HINDSIGHT_CACHE_ENABLED = os.getenv("HINDSIGHT_CACHE_ENABLED", "true").lower() in ("true", "1", "yes")
HINDSIGHT_MAX_CALLS_PER_SESSION = int(os.getenv("HINDSIGHT_MAX_CALLS_PER_SESSION", "50"))
HINDSIGHT_CACHE_TTL = int(os.getenv("HINDSIGHT_CACHE_TTL", "3600"))  # 1 hour in-memory cache


class HindsightService:
    def __init__(self):
        self.enabled = HINDSIGHT_ENABLED
        self.api_key = HINDSIGHT_API_KEY
        self.base_url = HINDSIGHT_BASE_URL
        self.bank_id = HINDSIGHT_BANK_ID
        self.client = None
        
        # Operational Metrics & Cost Tracking
        self.total_calls = 0
        self.retains_count = 0
        self.recalls_count = 0
        self.cache_hits = 0
        self.errors_count = 0
        self.last_call_at: Optional[str] = None
        
        # In-memory TTL Response Cache: { cache_key: { "timestamp": float, "data": Any } }
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        self._init_client()

    def _init_client(self):
        """Initializes official Hindsight client if credentials are configured."""
        self.enabled = os.getenv("HINDSIGHT_ENABLED", "true").lower() in ("true", "1", "yes")
        self.api_key = os.getenv("HINDSIGHT_API_KEY", "").strip()
        self.base_url = os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io").strip()
        self.bank_id = os.getenv("HINDSIGHT_BANK_ID", "feedbackiq_memory").strip()

        if self.is_configured():
            try:
                from hindsight_client import Hindsight
                self.client = Hindsight(
                    base_url=self.base_url,
                    api_key=self.api_key,
                    timeout=15.0,  # Strict timeout to avoid hanging
                    max_attempts=2  # Max 1 retry for transient errors
                )
                logger.info(f"Hindsight AI client initialized successfully for bank '{self.bank_id}'.")
            except Exception as e:
                logger.warning(f"Failed to initialize Hindsight client ({e}). Running in local fallback mode.")
                self.client = None
        else:
            self.client = None
            if not self.enabled:
                logger.info("Hindsight AI is explicitly disabled (HINDSIGHT_ENABLED=false).")
            else:
                logger.info("Hindsight AI API key is not configured. Historical Intelligence running in Supabase local mode.")

    def is_configured(self) -> bool:
        """Checks if Hindsight AI is enabled and valid credentials are present."""
        if not self.enabled:
            return False
        if not self.api_key:
            return False
        if self.api_key.startswith("your-") or self.api_key.startswith("dummy"):
            return False
        return True

    def get_status(self) -> Dict[str, Any]:
        """Returns safe operational status and call counters without exposing API secrets."""
        # Clean expired cache entries
        self._cleanup_cache()

        return {
            "enabled": self.enabled,
            "configured": self.is_configured(),
            "bank_id": self.bank_id,
            "base_url": self.base_url,
            "cache_enabled": HINDSIGHT_CACHE_ENABLED,
            "cached_entries": len(self._cache),
            "circuit_breaker_active": self.total_calls >= HINDSIGHT_MAX_CALLS_PER_SESSION,
            "usage": {
                "total_calls": self.total_calls,
                "retains_count": self.retains_count,
                "recalls_count": self.recalls_count,
                "cache_hits": self.cache_hits,
                "errors_count": self.errors_count,
                "last_call_at": self.last_call_at,
                "session_call_budget": HINDSIGHT_MAX_CALLS_PER_SESSION,
                "remaining_calls": max(0, HINDSIGHT_MAX_CALLS_PER_SESSION - self.total_calls)
            },
            "guardrails": {
                "max_retains_per_analysis": HINDSIGHT_MAX_RETAINS_PER_ANALYSIS,
                "max_recalls_per_request": HINDSIGHT_MAX_RECALLS_PER_REQUEST,
                "max_memory_tokens": 800,
                "cost_conservation_mode": True
            }
        }

    def reset_usage_metrics(self):
        """Resets call counters and memory cache (useful for testing)."""
        self.total_calls = 0
        self.retains_count = 0
        self.recalls_count = 0
        self.cache_hits = 0
        self.errors_count = 0
        self.last_call_at = None
        self._cache.clear()

    # ------------------------------------------------------------------
    # Cache Helpers
    # ------------------------------------------------------------------
    def _get_cache_key(self, query: str, analysis_id: Optional[str]) -> str:
        clean_q = query.strip().lower()
        a_id = analysis_id or "all"
        return f"{self.bank_id}:{a_id}:{clean_q}"

    def _cleanup_cache(self):
        now = time.time()
        expired_keys = [k for k, v in self._cache.items() if (now - v["timestamp"]) > HINDSIGHT_CACHE_TTL]
        for k in expired_keys:
            self._cache.pop(k, None)

    # ------------------------------------------------------------------
    # Phase 2: Compact Memory Generation
    # ------------------------------------------------------------------
    def create_compact_memory_text(self, analysis_data: Dict[str, Any]) -> str:
        """
        Creates a single compact, high-signal memory for Hindsight retention.
        Strictly limited to 500-800 tokens maximum (~2000-3000 chars).
        Excludes raw individual feedback, CSVs, or customer PII.
        """
        session = analysis_data.get("session") or analysis_data
        themes = analysis_data.get("themes") or []
        
        analysis_id = session.get("id") or session.get("analysis_id", "unknown")
        analysis_name = session.get("analysis_name", "User Feedback Analysis")
        created_at = str(session.get("created_at", datetime.now(timezone.utc).isoformat()))[:10]
        total_feedback = session.get("total_feedback", 0)
        pos_pct = float(session.get("positive_percentage", 0.0))
        neg_pct = float(session.get("negative_percentage", 0.0))
        neu_pct = float(session.get("neutral_percentage", 0.0))

        # Top 5 themes sorted by volume/mentions
        sorted_themes = sorted(themes, key=lambda t: t.get("mention_count", 0), reverse=True)[:5]

        theme_lines = []
        recurring_complaints = []
        feature_requests = []
        syntheses = []

        for idx, t in enumerate(sorted_themes, 1):
            name = t.get("theme_name") or t.get("name", f"Theme {idx}")
            mentions = t.get("mention_count", 0)
            neg = float(t.get("negative_percentage", 0.0))
            pos = float(t.get("positive_percentage", 0.0))
            complaint = t.get("main_complaint") or ""
            
            theme_line = f"{idx}. {name}: {mentions} mentions ({neg:.1f}% negative, {pos:.1f}% positive)"
            if complaint:
                theme_line += f" | Main complaint: {complaint[:90]}"
            theme_lines.append(theme_line)

            if complaint and complaint not in recurring_complaints:
                recurring_complaints.append(complaint[:100])

            if t.get("is_feature_request") and name not in feature_requests:
                feature_requests.append(name)

            summary = t.get("summary") or t.get("ai_summary") or ""
            if summary and len(syntheses) < 3:
                syntheses.append(f"- {name}: {summary[:120]}")

        # Assemble compact text payload
        sections = [
            f"FeedbackIQ Analysis Memory: {analysis_name}",
            f"Session ID: {analysis_id} | Ingest Date: {created_at}",
            f"Total Volume: {total_feedback} feedback items",
            f"Aggregate Sentiment: {pos_pct:.1f}% Positive, {neg_pct:.1f}% Negative, {neu_pct:.1f}% Neutral",
            "",
            "Top Themes:"
        ]
        sections.extend(theme_lines if theme_lines else ["No themes identified."])

        if recurring_complaints:
            sections.append("\nKey Reported Complaints:")
            sections.extend([f"- {c}" for c in recurring_complaints[:4]])

        if feature_requests:
            sections.append("\nTop Feature Requests:")
            sections.extend([f"- {f}" for f in feature_requests[:3]])

        if syntheses:
            sections.append("\nTheme Syntheses:")
            sections.extend(syntheses)

        memory_text = "\n".join(sections)

        # Enforce strict 800 token boundary (~3000 chars)
        if len(memory_text) > 2800:
            memory_text = memory_text[:2750] + "\n[Truncated to conserve token budget]"

        return memory_text

    # ------------------------------------------------------------------
    # Phase 3: Idempotent Single Retain Operation
    # ------------------------------------------------------------------
    def retain_analysis_memory(
        self,
        analysis_data: Dict[str, Any],
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Retains a single compact analysis summary in Hindsight.
        Enforces idempotency: never retains the same analysis twice unless force=True.
        Stores retention status ('pending', 'retained', 'failed') in database.
        """
        from backend.database.db import db

        session = analysis_data.get("session") or analysis_data
        analysis_id = session.get("id") or session.get("analysis_id")

        if not analysis_id:
            return {"success": False, "status": "failed", "error": "Missing analysis_id."}

        # 1. Idempotency Check
        current_status = session.get("hindsight_status")
        if current_status == "retained" and not force:
            logger.info(f"Analysis {analysis_id} has already been retained in Hindsight. Skipping retain (idempotent).")
            return {
                "success": True,
                "status": "already_retained",
                "analysis_id": analysis_id,
                "memory_id": session.get("hindsight_memory_id"),
                "message": "Analysis summary was already retained in Hindsight."
            }

        # 2. Configuration & Circuit Breaker Check
        if not self.is_configured() or not self.client:
            logger.info(f"Hindsight not configured. Marking analysis {analysis_id} retention as pending.")
            db.update_analysis_hindsight_status(analysis_id, "pending")
            return {
                "success": False,
                "status": "unconfigured",
                "analysis_id": analysis_id,
                "message": "Hindsight AI is not configured or disabled. Retention skipped to save credits."
            }

        if self.total_calls >= HINDSIGHT_MAX_CALLS_PER_SESSION:
            logger.warning("Hindsight session call limit reached. Blocking retain to conserve credits.")
            db.update_analysis_hindsight_status(analysis_id, "pending")
            return {
                "success": False,
                "status": "quota_exceeded",
                "analysis_id": analysis_id,
                "message": "Session call budget reached. Retain operation skipped to preserve $5 credits."
            }

        # 3. Create Compact Memory Text (500-800 tokens max)
        memory_content = self.create_compact_memory_text(analysis_data)
        created_at_iso = str(session.get("created_at", datetime.now(timezone.utc).isoformat()))

        # 4. Perform Single Retain with max 1 retry
        retries = 1
        last_error = None
        memory_id = None

        for attempt in range(retries + 1):
            try:
                self.total_calls += 1
                self.retains_count += 1
                self.last_call_at = datetime.now(timezone.utc).isoformat()

                logger.info(f"Calling Hindsight retain for analysis {analysis_id} (attempt {attempt + 1})...")
                res = self.client.retain(
                    bank_id=self.bank_id,
                    content=memory_content,
                    context="analysis_session",
                    document_id=analysis_id,
                    metadata={
                        "analysis_id": analysis_id,
                        "analysis_name": session.get("analysis_name", "Analysis"),
                        "source": "feedbackiq"
                    }
                )
                memory_id = getattr(res, "operation_id", None) or getattr(res, "id", None) or f"mem_{analysis_id[:8]}"
                logger.info(f"Hindsight retain succeeded for {analysis_id}. Operation ID: {memory_id}")
                break
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Hindsight retain attempt {attempt + 1} failed: {e}")
                if attempt < retries:
                    time.sleep(1.0)

        # 5. Update Database Status
        if memory_id:
            db.update_analysis_hindsight_status(analysis_id, "retained", memory_id)
            return {
                "success": True,
                "status": "retained",
                "analysis_id": analysis_id,
                "memory_id": memory_id,
                "tokens_estimated": int(len(memory_content.split()) * 1.3),
                "message": "Successfully retained compact analysis memory in Hindsight."
            }
        else:
            self.errors_count += 1
            db.update_analysis_hindsight_status(analysis_id, "failed")
            return {
                "success": False,
                "status": "failed",
                "analysis_id": analysis_id,
                "error": last_error,
                "message": "Failed to retain memory in Hindsight after retry. Saved in local fallback mode."
            }

    # ------------------------------------------------------------------
    # Phase 4: Local Statistical Engine (100% Deterministic & Local)
    # ------------------------------------------------------------------
    def calculate_historical_statistics(
        self,
        current_analysis: Dict[str, Any],
        previous_analyses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculates all numerical metrics locally using Supabase/local data.
        Never calls Hindsight for numerical calculations.
        Returns sentiment drift, volume velocity, worsened/improving issues,
        emerging issues, and recurring complaints.
        """
        curr_session = current_analysis.get("session") or current_analysis
        curr_themes = current_analysis.get("themes") or []

        if not previous_analyses:
            return {
                "has_sufficient_history": False,
                "message": "Not enough historical analysis data available yet.",
                "total_historical_sessions": 1
            }

        # Baseline is the most recent preceding analysis
        prev_session = previous_analyses[0].get("session") or previous_analyses[0]
        prev_themes = previous_analyses[0].get("themes") or []

        # 1. Volume Delta
        curr_vol = int(curr_session.get("total_feedback", 0))
        prev_vol = int(prev_session.get("total_feedback", 0))
        vol_diff = curr_vol - prev_vol
        vol_pct_change = round((vol_diff / max(1, prev_vol)) * 100, 1)

        # 2. Sentiment Drift
        curr_pos = float(curr_session.get("positive_percentage", 0.0))
        curr_neg = float(curr_session.get("negative_percentage", 0.0))
        curr_neu = float(curr_session.get("neutral_percentage", 0.0))

        prev_pos = float(prev_session.get("positive_percentage", 0.0))
        prev_neg = float(prev_session.get("negative_percentage", 0.0))
        prev_neu = float(prev_session.get("neutral_percentage", 0.0))

        pos_drift = round(curr_pos - prev_pos, 1)
        neg_drift = round(curr_neg - prev_neg, 1)
        neu_drift = round(curr_neu - prev_neu, 1)

        # 3. Theme Maps for Comparative Analysis
        curr_theme_map = {
            (t.get("theme_name") or t.get("name", "")).strip().lower(): t 
            for t in curr_themes if (t.get("theme_name") or t.get("name"))
        }
        prev_theme_map = {
            (t.get("theme_name") or t.get("name", "")).strip().lower(): t 
            for t in prev_themes if (t.get("theme_name") or t.get("name"))
        }

        worsened_issues = []
        improving_issues = []
        emerging_issues = []
        recurring_complaints = []
        theme_matrix = []

        # Compare matching themes
        for name_key, c_t in curr_theme_map.items():
            disp_name = c_t.get("theme_name") or c_t.get("name", name_key.title())
            c_mentions = int(c_t.get("mention_count", 0))
            c_neg = float(c_t.get("negative_percentage", 0.0))
            c_pos = float(c_t.get("positive_percentage", 0.0))
            complaint = c_t.get("main_complaint") or ""

            if name_key in prev_theme_map:
                p_t = prev_theme_map[name_key]
                p_mentions = int(p_t.get("mention_count", 0))
                p_neg = float(p_t.get("negative_percentage", 0.0))
                p_pos = float(p_t.get("positive_percentage", 0.0))

                mentions_diff = c_mentions - p_mentions
                neg_diff = round(c_neg - p_neg, 1)
                pos_diff = round(c_pos - p_pos, 1)

                theme_matrix.append({
                    "theme_name": disp_name,
                    "current_mentions": c_mentions,
                    "previous_mentions": p_mentions,
                    "mentions_change": mentions_diff,
                    "current_negative_pct": c_neg,
                    "previous_negative_pct": p_neg,
                    "negative_pct_change": neg_diff,
                    "current_positive_pct": c_pos,
                    "previous_positive_pct": p_pos,
                    "status": "worsened" if neg_diff >= 5.0 else ("improved" if neg_diff <= -5.0 else "stable")
                })

                # Check if worsened (neg % increased by >= 5% or complaint volume spiked)
                if neg_diff >= 5.0 or (mentions_diff > 0 and c_neg > 60.0):
                    worsened_issues.append({
                        "theme_name": disp_name,
                        "current_mentions": c_mentions,
                        "previous_mentions": p_mentions,
                        "negative_percentage": c_neg,
                        "negative_drift": neg_diff,
                        "main_complaint": complaint or "Elevated negative sentiment detected."
                    })

                # Check if improving (neg % decreased by >= 5% or pos % grew >= 5%)
                if neg_diff <= -5.0 or pos_diff >= 5.0:
                    improving_issues.append({
                        "theme_name": disp_name,
                        "current_mentions": c_mentions,
                        "positive_percentage": c_pos,
                        "positive_gain": pos_diff,
                        "negative_reduction": abs(neg_diff)
                    })

                # Recurring complaints across multiple analyses
                if c_neg >= 40.0 and p_neg >= 40.0:
                    recurring_complaints.append({
                        "theme_name": disp_name,
                        "current_mentions": c_mentions,
                        "previous_mentions": p_mentions,
                        "complaint": complaint or f"Recurring negative issue in {disp_name}.",
                        "average_negative_pct": round((c_neg + p_neg) / 2, 1)
                    })
            else:
                # Emerging issue: theme appears in current analysis but was not in baseline
                emerging_issues.append({
                    "theme_name": disp_name,
                    "mentions": c_mentions,
                    "negative_percentage": c_neg,
                    "positive_percentage": c_pos,
                    "main_complaint": complaint or "New topic emerging in latest feedback."
                })
                theme_matrix.append({
                    "theme_name": disp_name,
                    "current_mentions": c_mentions,
                    "previous_mentions": 0,
                    "mentions_change": c_mentions,
                    "current_negative_pct": c_neg,
                    "previous_negative_pct": 0.0,
                    "negative_pct_change": c_neg,
                    "current_positive_pct": c_pos,
                    "previous_positive_pct": 0.0,
                    "status": "emerging"
                })

        # Multi-session timeline points for charting (up to 8 historical sessions)
        all_sessions = [curr_session] + [p.get("session") or p for p in previous_analyses[:7]]
        timeline = []
        for s in reversed(all_sessions):
            timeline.append({
                "id": s.get("id") or s.get("analysis_id"),
                "name": s.get("analysis_name", "Analysis"),
                "date": str(s.get("created_at", ""))[:10],
                "total": s.get("total_feedback", 0),
                "positive": float(s.get("positive_percentage", 0.0)),
                "negative": float(s.get("negative_percentage", 0.0)),
                "neutral": float(s.get("neutral_percentage", 0.0))
            })

        return {
            "has_sufficient_history": True,
            "baseline_session": {
                "id": prev_session.get("id"),
                "name": prev_session.get("analysis_name", "Baseline Session"),
                "date": str(prev_session.get("created_at", ""))[:10]
            },
            "volume_metrics": {
                "current": curr_vol,
                "previous": prev_vol,
                "change": vol_diff,
                "percentage_change": vol_pct_change
            },
            "sentiment_drift": {
                "positive_drift": pos_drift,
                "negative_drift": neg_drift,
                "neutral_drift": neu_drift
            },
            "worsened_issues": worsened_issues,
            "improving_issues": improving_issues,
            "emerging_issues": emerging_issues,
            "recurring_complaints": recurring_complaints,
            "theme_matrix": theme_matrix,
            "timeline": timeline,
            "total_historical_sessions": len(previous_analyses) + 1
        }

    # ------------------------------------------------------------------
    # Phase 5: On-Demand Memory Recall & Intelligence Synthesis
    # ------------------------------------------------------------------
    def query_historical_intelligence(
        self,
        current_analysis_id: str,
        question: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes on-demand historical intelligence workflow.
        Rule: Performs at most ONE recall call if contextual memory is required.
        Caches results to eliminate redundant API credit usage.
        Validates all numerical statistics against Supabase local calculations.
        """
        from backend.database.db import db

        # 1. Fetch current analysis
        current_analysis = db.get_analysis_by_id(current_analysis_id)
        if not current_analysis:
            return {
                "status": "error",
                "error": f"Analysis with ID '{current_analysis_id}' was not found.",
                "has_sufficient_history": False
            }

        # 2. Fetch past analyses
        history = db.get_history(user_id=user_id)
        previous_history = [
            h for h in history 
            if (h.get("id") != current_analysis_id and h.get("analysis_id") != current_analysis_id)
        ]

        # Hydrate previous analyses details
        previous_analyses = []
        for h in previous_history[:5]:  # Compare against up to 5 preceding analyses
            h_id = h.get("id") or h.get("analysis_id")
            if h_id:
                detail = db.get_analysis_by_id(h_id)
                if detail:
                    previous_analyses.append(detail)

        # 3. Calculate Local Deterministic Statistics
        local_stats = self.calculate_historical_statistics(current_analysis, previous_analyses)

        if not local_stats.get("has_sufficient_history"):
            return {
                "status": "success",
                "question": question,
                "has_sufficient_history": False,
                "answer": "Not enough historical analysis data available yet. Run or import at least two feedback analyses to identify recurring issues and observe trends.",
                "local_metrics": local_stats,
                "hindsight_used": False,
                "cache_hit": False,
                "usage": self.get_status()["usage"]
            }

        # 4. Check if Hindsight Contextual Memory Recall is needed & allowed
        hindsight_used = False
        cache_hit = False
        recalled_memories: List[Dict[str, Any]] = []
        cache_key = self._get_cache_key(question, current_analysis_id)

        # Check in-memory cache first (Zero Credits consumed)
        if HINDSIGHT_CACHE_ENABLED and cache_key in self._cache:
            entry = self._cache[cache_key]
            if (time.time() - entry["timestamp"]) <= HINDSIGHT_CACHE_TTL:
                recalled_memories = entry["data"]
                cache_hit = True
                self.cache_hits += 1
                logger.info(f"Hindsight recall cache hit for query: '{question}' (0 API calls).")

        # If not cached, perform ONE recall if configured and within budget
        if not cache_hit and self.is_configured() and self.client:
            if self.total_calls < HINDSIGHT_MAX_CALLS_PER_SESSION:
                try:
                    self.total_calls += 1
                    self.recalls_count += 1
                    self.last_call_at = datetime.now(timezone.utc).isoformat()
                    hindsight_used = True

                    logger.info(f"Executing single Hindsight recall for question: '{question}'...")
                    recall_res = self.client.recall(
                        bank_id=self.bank_id,
                        query=question,
                        max_tokens=400,  # Compact token limit to conserve memory bandwidth
                        budget="low"     # Low budget traversal to strictly conserve credits
                    )

                    raw_results = getattr(recall_res, "results", []) or []
                    for r in raw_results[:3]:  # Top 3 most relevant memory facts
                        recalled_memories.append({
                            "text": getattr(r, "text", str(r)),
                            "type": getattr(r, "type", "experience"),
                            "context": getattr(r, "context", "analysis_session")
                        })

                    # Store in cache
                    if HINDSIGHT_CACHE_ENABLED:
                        self._cache[cache_key] = {
                            "timestamp": time.time(),
                            "data": recalled_memories
                        }
                except Exception as e:
                    self.errors_count += 1
                    logger.warning(f"Hindsight recall failed ({e}). Falling back to pure local historical synthesis.")
            else:
                logger.warning("Session call budget reached. Using local historical statistics without Hindsight.")

        # 5. Synthesize Evidence-Based Answer
        answer = self._synthesize_historical_answer(
            question=question,
            local_stats=local_stats,
            recalled_memories=recalled_memories,
            hindsight_used=hindsight_used or cache_hit
        )

        return {
            "status": "success",
            "question": question,
            "has_sufficient_history": True,
            "answer": answer,
            "local_metrics": local_stats,
            "worsened_issues": local_stats.get("worsened_issues", []),
            "improving_issues": local_stats.get("improving_issues", []),
            "emerging_issues": local_stats.get("emerging_issues", []),
            "recurring_complaints": local_stats.get("recurring_complaints", []),
            "theme_matrix": local_stats.get("theme_matrix", []),
            "timeline": local_stats.get("timeline", []),
            "recalled_memories": recalled_memories,
            "hindsight_used": hindsight_used,
            "cache_hit": cache_hit,
            "usage": self.get_status()["usage"]
        }

    def _synthesize_historical_answer(
        self,
        question: str,
        local_stats: Dict[str, Any],
        recalled_memories: List[Dict[str, Any]],
        hindsight_used: bool
    ) -> str:
        """
        Synthesizes a cohesive, factual answer combining exact Supabase calculations
        with Hindsight contextual memory. Never invents numerical values.
        """
        q_lower = question.lower()
        drift = local_stats.get("sentiment_drift", {})
        vol = local_stats.get("volume_metrics", {})
        worsened = local_stats.get("worsened_issues", [])
        improving = local_stats.get("improving_issues", [])
        emerging = local_stats.get("emerging_issues", [])
        recurring = local_stats.get("recurring_complaints", [])
        baseline_name = local_stats.get("baseline_session", {}).get("name", "previous analysis")

        lines = []

        if "worsen" in q_lower or "negative" in q_lower or "bad" in q_lower:
            if worsened:
                lines.append(f"Based on historical comparison with {baseline_name}, {len(worsened)} issue(s) have intensified:")
                for w in worsened[:3]:
                    drift_str = f"+{w['negative_drift']:.1f}%" if w.get("negative_drift", 0) > 0 else f"{w.get('negative_drift', 0):.1f}%"
                    lines.append(f"• **{w['theme_name']}**: Negative sentiment grew by {drift_str} (now {w['negative_percentage']:.1f}% negative across {w['current_mentions']} mentions). Issue: {w['main_complaint']}")
            else:
                lines.append(f"No existing themes experienced a significant rise in negative sentiment compared with {baseline_name}. Overall negative sentiment changed by {drift.get('negative_drift', 0.0):+.1f}%.")

        elif "recur" in q_lower or "chronic" in q_lower or "keep" in q_lower:
            if recurring:
                lines.append(f"Identified {len(recurring)} chronic recurring complaint(s) persisting across analysis cycles:")
                for r in recurring[:4]:
                    lines.append(f"• **{r['theme_name']}**: Logged {r['current_mentions']} times in the latest session and {r['previous_mentions']} times previously (average negative sentiment: {r['average_negative_pct']}%. Concern: {r['complaint']}).")
            else:
                lines.append(f"No complaints crossed the chronic recurrence threshold between the current session and {baseline_name}.")

        elif "improv" in q_lower or "better" in q_lower or "positive" in q_lower:
            if improving:
                lines.append(f"Positive progress observed across {len(improving)} theme(s) compared with {baseline_name}:")
                for imp in improving[:3]:
                    lines.append(f"• **{imp['theme_name']}**: Negative feedback decreased by {imp['negative_reduction']:.1f}% while positive sentiment reached {imp['positive_percentage']:.1f}%.")
            else:
                lines.append(f"No themes demonstrated a >= 5.0% reduction in negative sentiment compared with {baseline_name}.")

        elif "emerg" in q_lower or "new" in q_lower:
            if emerging:
                lines.append(f"Detected {len(emerging)} newly emerging topic(s) not reported in {baseline_name}:")
                for e in emerging[:3]:
                    lines.append(f"• **{e['theme_name']}**: {e['mentions']} mentions ({e['negative_percentage']:.1f}% negative). Note: {e['main_complaint']}")
            else:
                lines.append(f"No completely new themes emerged; feedback remained concentrated within existing topic categories.")

        else:
            # General overview query
            lines.append(f"Cross-Session Historical Intelligence Summary vs. {baseline_name}:")
            lines.append(f"• **Feedback Volume**: {vol.get('current', 0)} records ({vol.get('change', 0):+d} vs. previous, {vol.get('percentage_change', 0.0):+.1f}%).")
            lines.append(f"• **Sentiment Drift**: Positive {drift.get('positive_drift', 0.0):+.1f}%, Negative {drift.get('negative_drift', 0.0):+.1f}%, Neutral {drift.get('neutral_drift', 0.0):+.1f}%.")
            if worsened:
                lines.append(f"• **Worsening Focus**: {worsened[0]['theme_name']} (+{worsened[0]['negative_drift']:.1f}% negative).")
            if recurring:
                lines.append(f"• **Chronic Complaint**: {recurring[0]['theme_name']} ({recurring[0]['complaint']}).")
            if emerging:
                lines.append(f"• **Emerging Topic**: {emerging[0]['theme_name']} ({emerging[0]['mentions']} mentions).")

        # Incorporate long-term context from Hindsight if memories were recalled
        if recalled_memories:
            lines.append("\n**Historical Context from Long-Term Memory:**")
            for m in recalled_memories[:2]:
                text = m.get("text", "").strip()
                if text:
                    lines.append(f"> \"{text[:200]}\"")

        return "\n".join(lines)


# Singleton Service Instance
hindsight_service = HindsightService()
