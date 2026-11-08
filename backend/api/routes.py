import io
import csv
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, BackgroundTasks, Header, Depends
from backend.models.schemas import (
    FeedbackInput, BatchAnalyzeRequest, AnalyticsResponse, 
    InsightsResponse, ChatRequest, ChatResponse, SummarizeRequest,
    HistoricalIntelligenceRequest
)
from backend.database.db import db, is_valid_uuid

def get_current_user_id(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None)
) -> Optional[str]:
    """
    Extracts authenticated user ID from Supabase JWT Bearer token or X-User-Id header.
    Enforces security while gracefully allowing guest access in local development mode.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1].strip()
        if token:
            # 1. Verify via Supabase Auth client if remote connection is live
            if db.use_supabase and db.supabase:
                try:
                    res = db.supabase.auth.get_user(token)
                    if res and res.user and res.user.id:
                        return str(res.user.id)
                except Exception:
                    pass

            # 2. Extract from standard JWT payload
            try:
                import base64
                import json
                parts = token.split(".")
                if len(parts) >= 2:
                    padded = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
                    payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
                    sub = payload.get("sub") or payload.get("id")
                    if sub and is_valid_uuid(str(sub)):
                        return str(sub)
            except Exception:
                pass

    if x_user_id and is_valid_uuid(x_user_id):
        return x_user_id

    return None
from backend.services.sentiment import sentiment_analyzer
from backend.services.clustering import semantic_clusterer
from backend.services.summarization import theme_summarizer
from backend.services.prioritization import issue_prioritizer
from backend.services.insights import insights_engine
from backend.services.copilot import feedback_copilot
from backend.services.jobs import job_manager

logger = logging.getLogger("feedbackiq.routes")

router = APIRouter()

# Thread pool for non-blocking background analysis tasks
executor = ThreadPoolExecutor(max_workers=2)

def clean_feedback_items(raw_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Cleans and deduplicates raw feedback dictionaries, sanitizing ratings and dates.
    """
    cleaned_items = []
    seen_texts = set()

    for it in raw_items:
        text = str(it.get("feedback") or it.get("feedback_text") or "").strip()
        if not text:
            continue
        norm_key = text.lower()
        if norm_key in seen_texts:
            continue
        seen_texts.add(norm_key)

        rating = it.get("rating")
        try:
            if rating is not None and str(rating).strip() != "":
                parsed_r = int(float(str(rating).strip()))
                rating = max(1, min(5, parsed_r))
            else:
                rating = 3
        except Exception:
            rating = 3

        d_str = str(it.get("date") or date.today().isoformat()).strip()
        src = str(it.get("source") or "Web App").strip()

        cleaned_items.append({
            "id": it.get("id") or f"fb_{uuid.uuid4().hex[:8]}",
            "feedback_text": text,
            "rating": rating,
            "date": d_str,
            "source": src,
            "created_at": datetime.now(timezone.utc).isoformat()
        })

    return cleaned_items

def run_nlp_pipeline_sync(
    raw_items: List[Dict[str, Any]], 
    dataset_name: str = "Uploaded Dataset", 
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """Synchronous pipeline execution (used during server startup seeding)."""
    return run_pipeline_with_progress(
        job_id=None,
        raw_items=raw_items,
        dataset_name=dataset_name,
        user_id=user_id
    )

def run_pipeline_with_progress(
    job_id: Optional[str],
    raw_items: List[Dict[str, Any]], 
    dataset_name: str = "Uploaded Dataset", 
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes the optimized 6-stage AI NLP & Intelligence Pipeline with real-time stage progress:
    Stage 1: Data preprocessing (empty check, deduplication, whitespace cleaning)
    Stage 2: Sentiment classification (high-throughput batch inference with DistilBERT)
    Stage 3: Semantic embeddings (batch vector encoding with all-MiniLM-L6-v2)
    Stage 4: Semantic clustering (K-Means)
    Stage 5: Theme identification (Dynamic cluster titling & prioritization)
    Stage 6: Theme summarization (AI summary generation & database persistence)
    """
    stage_name = "Data preprocessing"
    try:
        # ==========================================================
        # STAGE 1: DATA PREPROCESSING
        # ==========================================================
        stage_name = "Data preprocessing"
        if job_id:
            job_manager.update_job(
                job_id,
                status="processing",
                current_stage="Data preprocessing",
                stage_index=1,
                progress_percentage=5,
                message="Cleaning whitespace, deduplicating, and validating records..."
            )

        cleaned_items = clean_feedback_items(raw_items)

        if not cleaned_items:
            raise ValueError("No valid feedback items provided after data cleaning.")

        total_cleaned = len(cleaned_items)
        if job_id:
            job_manager.update_job(
                job_id,
                progress_percentage=15,
                processed_items=total_cleaned,
                total_items=total_cleaned,
                message=f"Cleaned {total_cleaned} unique feedback items."
            )

        # ==========================================================
        # STAGE 2: SENTIMENT CLASSIFICATION (BATCH INFERENCE)
        # ==========================================================
        stage_name = "Sentiment classification"
        if job_id:
            job_manager.update_job(
                job_id,
                current_stage="Sentiment classification",
                stage_index=2,
                progress_percentage=15,
                message=f"Classifying sentiment with DistilBERT batch inference (0/{total_cleaned})..."
            )

        all_texts = [it["feedback_text"] for it in cleaned_items]

        def sentiment_progress_cb(done: int, total: int):
            if job_id:
                # Stage 2 maps from 15% to 50%
                pct = 15 + int((done / max(1, total)) * 35)
                job_manager.update_job(
                    job_id,
                    progress_percentage=pct,
                    processed_items=done,
                    message=f"Classifying sentiment with DistilBERT ({done}/{total})..."
                )

        sentiment_results = sentiment_analyzer.analyze_batch(
            all_texts, 
            batch_size=128, 
            progress_callback=sentiment_progress_cb if job_id else None
        )

        for item, s_res in zip(cleaned_items, sentiment_results):
            item["sentiment"] = s_res["sentiment"]
            item["confidence"] = s_res["confidence"]
            item["sentiment_confidence"] = s_res["confidence"]

        # ==========================================================
        # STAGE 3: SEMANTIC EMBEDDINGS (BATCH ENCODING)
        # ==========================================================
        stage_name = "Semantic embeddings"
        if job_id:
            job_manager.update_job(
                job_id,
                current_stage="Semantic embeddings",
                stage_index=3,
                progress_percentage=50,
                message=f"Encoding 384-d semantic vectors with all-MiniLM-L6-v2 (0/{total_cleaned})..."
            )

        def emb_progress_cb(done: int, total: int):
            if job_id:
                # Stage 3 maps from 50% to 75%
                pct = 50 + int((done / max(1, total)) * 25)
                job_manager.update_job(
                    job_id,
                    progress_percentage=pct,
                    processed_items=done,
                    message=f"Encoding semantic vectors with all-MiniLM-L6-v2 ({done}/{total})..."
                )

        # Precompute embeddings
        embeddings = semantic_clusterer.get_embeddings(
            all_texts, 
            batch_size=128, 
            progress_callback=emb_progress_cb if job_id else None
        )

        # ==========================================================
        # STAGE 4: SEMANTIC CLUSTERING (K-MEANS)
        # ==========================================================
        stage_name = "Semantic clustering"
        if job_id:
            job_manager.update_job(
                job_id,
                current_stage="Semantic clustering",
                stage_index=4,
                progress_percentage=75,
                message="Partitioning high-dimensional embeddings with K-Means..."
            )

        raw_themes, labeled_items = semantic_clusterer.cluster_feedback(cleaned_items)

        # ==========================================================
        # STAGE 5: THEME IDENTIFICATION & PRIORITIZATION
        # ==========================================================
        stage_name = "Theme identification"
        if job_id:
            job_manager.update_job(
                job_id,
                current_stage="Theme identification",
                stage_index=5,
                progress_percentage=85,
                message="Assigning theme titles, severity weights, and priority scores..."
            )

        prioritized_themes = issue_prioritizer.rank_themes(raw_themes)

        # ==========================================================
        # STAGE 6: THEME SUMMARIZATION & PERSISTENCE
        # ==========================================================
        stage_name = "Theme summarization"
        if job_id:
            job_manager.update_job(
                job_id,
                current_stage="Theme summarization",
                stage_index=6,
                progress_percentage=90,
                message="Synthesizing AI theme summaries and recommended actions..."
            )

        final_themes = []
        for t in prioritized_themes:
            name = t.get("name") or t.get("theme_name", "General")
            severity = t.get("severity", "Medium")
            theme_summary_data = theme_summarizer.summarize_theme(name, t["items"], severity=severity)
            t.update(theme_summary_data)
            final_themes.append(t)

        final_themes = issue_prioritizer.rank_themes(final_themes)

        # Strip circular items before database save
        clean_save_themes = []
        for t in final_themes:
            t_copy = dict(t)
            t_copy.pop("items", None)
            clean_save_themes.append(t_copy)

        # Persist in Supabase and local storage
        analysis_id = db.create_analysis_session(
            analysis_name=dataset_name,
            feedback_records=labeled_items,
            themes=clean_save_themes,
            user_id=user_id
        )

        # Single compact memory retention in Hindsight (strictly guarded for credit conservation)
        try:
            from backend.services.hindsight_service import hindsight_service
            if hindsight_service.is_configured():
                analysis_detail = db.get_analysis_by_id(analysis_id)
                if analysis_detail:
                    hindsight_service.retain_analysis_memory(analysis_detail)
        except Exception as he:
            logger.warning(f"Hindsight background retention skipped/notice: {he}")

        result_payload = {
            "status": "success",
            "analysis_id": analysis_id,
            "processed_count": len(labeled_items),
            "themes_count": len(clean_save_themes),
            "dataset_name": dataset_name
        }

        if job_id:
            job_manager.update_job(
                job_id,
                status="completed",
                current_stage="Completed",
                stage_index=6,
                progress_percentage=100,
                processed_items=len(labeled_items),
                message=f"Analysis completed successfully! Synthesized {len(labeled_items)} records across {len(clean_save_themes)} themes.",
                result=result_payload
            )

        return result_payload

    except Exception as e:
        logger.error(f"Error during {stage_name}: {e}", exc_info=True)
        if job_id:
            job_manager.update_job(
                job_id,
                status="failed",
                error=f"Failure during {stage_name}: {str(e)}",
                message=f"Pipeline error at stage '{stage_name}': {str(e)}"
            )
        raise e

# ==========================================================
# PUBLIC API ROUTES
# ==========================================================

@router.get("/")
@router.get("/system/status")
def health_check():
    """Returns database connectivity mode, health status, and active dataset metrics."""
    return db.get_system_status()

@router.get("/analysis-status/{job_id}")
def get_analysis_status(job_id: str):
    """
    GET /analysis-status/{job_id}
    Returns real-time progress and stage metrics for a running background analysis job.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Analysis job '{job_id}' not found.")
    return job

@router.post("/upload")
async def upload_feedback_csv(
    file: UploadFile = File(...), 
    user_id: Optional[str] = Form(None),
    auth_user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Upload CSV feedback file.
    Validates CSV headers, registers a background job, and returns the job_id immediately.
    """
    effective_user_id = user_id or auth_user_id
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload a .csv file.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded CSV file is empty.")

    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            decoded = content.decode("latin-1")
        except Exception:
            raise HTTPException(status_code=400, detail="Failed to decode CSV file. Ensure valid UTF-8 encoding.")

    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file contains no headers.")

    # Match feedback column (case-insensitive)
    col_map = {col.strip().lower(): col for col in reader.fieldnames}
    feedback_col = None
    for cand in ["feedback", "content", "text", "comment", "review", "feedback_text", "message", "body"]:
        if cand in col_map:
            feedback_col = col_map[cand]
            break

    if not feedback_col:
        raise HTTPException(
            status_code=400, 
            detail=f"Required feedback column not found. Available columns: {', '.join(reader.fieldnames)}"
        )

    rating_col = None
    for cand in ["rating", "score", "stars"]:
        if cand in col_map:
            rating_col = col_map[cand]
            break

    date_col = None
    for cand in ["date", "created_at", "timestamp", "time", "at"]:
        if cand in col_map:
            date_col = col_map[cand]
            break

    source_col = None
    for cand in ["source", "channel", "platform", "origin", "appid"]:
        if cand in col_map:
            source_col = col_map[cand]
            break

    parsed_rows = []
    for row in reader:
        text = row.get(feedback_col, "").strip()
        if not text:
            continue
        parsed_rows.append({
            "feedback": text,
            "rating": row.get(rating_col) if rating_col else None,
            "date": row.get(date_col) if date_col else date.today().isoformat(),
            "source": row.get(source_col) if source_col else "Web App"
        })

    if not parsed_rows:
        raise HTTPException(status_code=400, detail="No valid feedback rows found in the CSV file.")

    # Create background job and return immediately to avoid blocking client
    job_id = job_manager.create_job(total_items=len(parsed_rows), dataset_name=file.filename)
    
    # Submit to worker pool
    executor.submit(
        run_pipeline_with_progress,
        job_id,
        parsed_rows,
        file.filename,
        effective_user_id
    )

    return {
        "job_id": job_id,
        "status": "processing",
        "message": f"Successfully queued {len(parsed_rows)} feedback entries for background analysis.",
        "total_items": len(parsed_rows),
        "dataset_name": file.filename
    }

@router.post("/analyze")
def analyze_feedback(
    payload: BatchAnalyzeRequest,
    auth_user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Analyze manually inputted feedback (JSON array or raw multiline text).
    Returns job_id immediately so frontend polls progress smoothly.
    """
    effective_user_id = payload.user_id or auth_user_id
    items = []
    if payload.items:
        for it in payload.items:
            items.append(it.model_dump())
    elif payload.raw_text:
        lines = [line.strip() for line in payload.raw_text.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            items.append({
                "feedback": line,
                "date": date.today().isoformat(),
                "source": "Manual Input"
            })
    else:
        raise HTTPException(status_code=400, detail="Please provide either 'items' list or 'raw_text'.")

    dataset_name = payload.dataset_name or "Manual Ingestion"
    job_id = job_manager.create_job(total_items=len(items), dataset_name=dataset_name)

    executor.submit(
        run_pipeline_with_progress,
        job_id,
        items,
        dataset_name,
        effective_user_id
    )

    return {
        "job_id": job_id,
        "status": "processing",
        "message": f"Queued {len(items)} feedback items for analysis.",
        "total_items": len(items),
        "dataset_name": dataset_name
    }

@router.post("/summarize")
def summarize_themes(payload: Optional[SummarizeRequest] = None):
    """
    POST /summarize
    Return structured JSON containing summaries and recommendations for each theme.
    """
    themes = db.get_themes()
    if not themes:
        return {"themes": []}

    target_themes = themes
    if payload and payload.theme_ids:
        target_themes = [t for t in themes if t.get("id") in payload.theme_ids]

    summarized_output = []
    for t in target_themes:
        summarized_output.append({
            "id": t.get("id"),
            "theme_name": t.get("theme_name") or t.get("name"),
            "mention_count": t.get("mention_count", 0),
            "positive_percentage": t.get("positive_percentage", 0.0),
            "negative_percentage": t.get("negative_percentage", 0.0),
            "neutral_percentage": t.get("neutral_percentage", 0.0),
            "main_complaint": t.get("main_complaint", ""),
            "key_observations": t.get("key_observations", []),
            "representative_feedback": t.get("representative_feedback") or t.get("representative_comments", []),
            "severity": t.get("severity", "Medium"),
            "priority": t.get("priority") or t.get("priority_level", "Medium"),
            "ai_summary": t.get("ai_summary") or t.get("summary", ""),
            "recommendation": t.get("recommendation") or t.get("suggested_action", "")
        })

    return {"themes": summarized_output}

@router.get("/feedback")
def get_feedback_records(
    sentiment: Optional[str] = Query(None, description="Filter by sentiment: Positive, Negative, Neutral, All"),
    theme_id: Optional[str] = Query(None, description="Filter by theme ID or name"),
    search: Optional[str] = Query(None, description="Search term in feedback text"),
    sort_by: str = Query("date", description="Field to sort by: date, rating, confidence, sentiment"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=200)
):
    offset = (page - 1) * limit
    res = db.get_feedback(
        sentiment=sentiment, 
        theme_id=theme_id, 
        search=search, 
        sort_by=sort_by, 
        sort_order=sort_order, 
        limit=limit, 
        offset=offset
    )
    return {
        "page": page,
        "limit": limit,
        "total": res["total"],
        "items": res["items"]
    }

@router.get("/themes")
def get_themes():
    themes = db.get_themes()
    return {"themes": themes}

@router.get("/insights")
def get_insights():
    themes = db.get_themes()
    feedback = db.get_all_feedback()
    return insights_engine.generate_insights(themes, feedback)

@router.post("/chat")
def chat_feedback(request: ChatRequest):
    """
    AI Feedback Copilot: RAG chatbot that answers questions based on analyzed feedback records.
    """
    themes = db.get_themes()
    feedback = db.get_all_feedback()
    copilot_res = feedback_copilot.answer_query(
        query=request.message,
        feedback_records=feedback,
        themes=themes,
        analysis_id=request.analysis_id
    )
    return copilot_res

@router.get("/analytics")
def get_analytics():
    all_fb = db.get_all_feedback()
    themes = db.get_themes()
    total = len(all_fb)

    pos_count = sum(1 for f in all_fb if f.get("sentiment") == "Positive")
    neg_count = sum(1 for f in all_fb if f.get("sentiment") == "Negative")
    neu_count = sum(1 for f in all_fb if f.get("sentiment") == "Neutral")

    pos_pct = round((pos_count / total) * 100, 1) if total > 0 else 0.0
    neg_pct = round((neg_count / total) * 100, 1) if total > 0 else 0.0
    neu_pct = round((neu_count / total) * 100, 1) if total > 0 else 0.0

    total_issues = neg_count

    # Sentiment Donut Chart Data
    sentiment_donut = [
        {"name": "Positive", "value": pos_count, "color": "#10B981"}, # Emerald
        {"name": "Neutral", "value": neu_count, "color": "#6366F1"},  # Indigo
        {"name": "Negative", "value": neg_count, "color": "#F43F5E"}  # Rose
    ]

    # Feedback Sentiment Trend (group by date)
    date_map: Dict[str, Dict[str, int]] = {}
    for it in all_fb:
        d = it.get("date", "2026-11-01")[:10]
        date_map.setdefault(d, {"positive": 0, "negative": 0, "neutral": 0, "total": 0})
        s = it.get("sentiment", "Neutral").lower()
        if s in date_map[d]:
            date_map[d][s] += 1
        date_map[d]["total"] += 1

    sorted_dates = sorted(date_map.keys())
    sentiment_trend = [
        {
            "date": d,
            "positive": date_map[d]["positive"],
            "negative": date_map[d]["negative"],
            "neutral": date_map[d]["neutral"],
            "total": date_map[d]["total"]
        }
        for d in sorted_dates
    ]

    # Top Themes Bar Chart
    top_themes = [
        {
            "name": t.get("theme_name") or t.get("name"),
            "count": t.get("mention_count", 0),
            "priority": t.get("priority") or t.get("priority_level", "Medium"),
            "priority_score": t.get("priority_score", 0),
            "negative_count": t.get("negative_count", 0)
        }
        for t in themes[:6]
    ]

    # Severity weight mapping for deterministic ranking
    SEVERITY_WEIGHTS = {
        "Critical": 4,
        "High": 3,
        "Medium": 2,
        "Low": 1
    }

    # Top user complaints (qualifies: predominantly negative user issues & bugs)
    top_complaints = []
    complaint_theme_ids = set()

    for idx, t in enumerate(themes):
        neg_c = t.get("negative_count", 0)
        mention_c = t.get("mention_count", 0)
        neg_pct_val = float(t.get("negative_percentage", 0.0))
        is_feat = bool(t.get("is_feature_request", False))

        t_name = t.get("theme_name") or t.get("name") or f"Theme #{idx + 1}"
        pos_pct_val = float(t.get("positive_percentage", 0.0))
        is_praise_theme = any(p in t_name.lower() for p in ["praise", "satisfaction", "delight", "appreciation"])

        # A theme qualifies as a user complaint when:
        # 1. Its aggregated sentiment is predominantly negative (neg_pct >= 50% and neg_pct > pos_pct)
        # 2. It contains actual user problems, friction, or dissatisfaction (neg_c >= 5)
        # 3. Excludes positive-only / praise themes and genuine feature requests
        qualifies_as_complaint = (
            neg_c >= 5 and 
            neg_pct_val >= 50.0 and 
            neg_pct_val > pos_pct_val and 
            not is_praise_theme
        )

        if qualifies_as_complaint:
            reps = t.get("representative_feedback") or t.get("representative_comments") or []
            if not reps and t.get("sample"):
                reps = [t.get("sample")]

            summary_text = (
                t.get("main_complaint") or 
                t.get("ai_summary") or 
                t.get("summary") or 
                f"Users report recurring friction regarding {t_name.lower()}."
            )

            severity_val = t.get("severity") or ("High" if neg_pct_val >= 70.0 else "Medium")
            priority_val = t.get("priority") or t.get("priority_level") or severity_val

            theme_id = t.get("id") or t.get("theme_id") or f"theme_{idx + 1}"
            complaint_theme_ids.add(theme_id)

            top_complaints.append({
                "theme_id": theme_id,
                "theme_name": t_name,
                "theme": t_name,  # Backward compatibility alias
                "mention_count": mention_c,
                "count": neg_c,   # Backward compatibility alias (negative mentions)
                "negative_count": neg_c,
                "positive_count": t.get("positive_count", 0),
                "neutral_count": t.get("neutral_count", 0),
                "negative_percentage": round(neg_pct_val, 1),
                "negative_pct": round(neg_pct_val, 1),  # Backward compatibility alias
                "positive_percentage": round(float(t.get("positive_percentage", 0.0)), 1),
                "severity": severity_val,
                "priority": priority_val,
                "representative_feedback": reps[:4] if reps else ([summary_text] if summary_text else []),
                "sample": reps[0] if reps else summary_text,  # Backward compatibility alias
                "summary": summary_text,
                "main_complaint": t.get("main_complaint") or summary_text,
                "suggested_action": t.get("recommendation") or t.get("suggested_action") or "Audit and resolve friction."
            })

    # Rank complaints by: 1) Negative mentions desc, 2) Severity desc, 3) Negative % desc
    top_complaints.sort(
        key=lambda c: (
            c["negative_count"],
            SEVERITY_WEIGHTS.get(c["severity"], 0),
            c["negative_percentage"]
        ),
        reverse=True
    )

    # Most requested features (strictly exclude themes categorized as complaints or >50% negative)
    most_requested_features = []
    for t in themes:
        t_id = t.get("id") or t.get("theme_id")
        neg_pct_val = float(t.get("negative_percentage", 0.0))
        is_feat = bool(t.get("is_feature_request", False))

        if is_feat and t_id not in complaint_theme_ids and neg_pct_val < 50.0:
            reps = t.get("representative_feedback") or t.get("representative_comments") or []
            most_requested_features.append({
                "theme_id": t_id,
                "theme_name": t.get("theme_name") or t.get("name"),
                "theme": t.get("theme_name") or t.get("name"),
                "mentions": t.get("mention_count", 0),
                "negative_percentage": round(neg_pct_val, 1),
                "summary": t.get("ai_summary") or t.get("summary"),
                "sample": reps[0] if reps else ""
            })

    most_requested_features.sort(key=lambda f: f["mentions"], reverse=True)

    # Priority issues (ranked themes)
    priority_issues = [
        {
            "rank": t.get("priority_rank", idx + 1),
            "name": t.get("theme_name") or t.get("name"),
            "level": t.get("priority") or t.get("priority_level", "Medium"),
            "score": t.get("priority_score", 0),
            "mentions": t.get("mention_count", 0),
            "negative_pct": t.get("negative_percentage", 0.0),
            "action": t.get("recommendation") or t.get("suggested_action")
        }
        for idx, t in enumerate(themes[:5])
    ]

    # Recent feedback (last 6 items)
    recent_feedback = sorted(all_fb, key=lambda x: str(x.get("date", "")), reverse=True)[:6]

    return {
        "total_feedback": total,
        "positive_percentage": pos_pct,
        "neutral_percentage": neu_pct,
        "negative_percentage": neg_pct,
        "total_issues_identified": total_issues,
        "sentiment_donut": sentiment_donut,
        "sentiment_trend": sentiment_trend,
        "top_themes": top_themes,
        "top_complaints": top_complaints,
        "most_requested_features": most_requested_features,
        "priority_issues": priority_issues,
        "recent_feedback": recent_feedback
    }

# ==========================================================
# ANALYSIS HISTORY & LIFECYCLE MANAGEMENT ENDPOINTS
# ==========================================================

@router.get("/history")
def get_analysis_history(
    user_id: Optional[str] = Query(None),
    auth_user_id: Optional[str] = Depends(get_current_user_id)
):
    """Retrieve list of previous analysis sessions (filtered by authenticated user when signed in)."""
    effective_user_id = user_id or auth_user_id
    return {
        "history": db.get_history(user_id=effective_user_id),
        "status": db.get_system_status()
    }

@router.get("/analysis/{analysis_id}")
def get_analysis_details(analysis_id: str):
    """Retrieve full themes and feedback for a specific analysis session."""
    data = db.get_analysis_by_id(analysis_id)
    if not data:
        raise HTTPException(status_code=404, detail="Analysis session not found.")
    return data

@router.post("/analysis/{analysis_id}/activate")
def activate_analysis_session(analysis_id: str):
    """Switch the active session to this analysis ID."""
    success = db.activate_analysis(analysis_id)
    if not success:
        raise HTTPException(status_code=404, detail="Analysis session not found.")
    return {"message": f"Activated analysis session {analysis_id}", "active_id": analysis_id}

@router.delete("/analysis/{analysis_id}")
def delete_analysis_session(
    analysis_id: str, 
    user_id: Optional[str] = Query(None),
    auth_user_id: Optional[str] = Depends(get_current_user_id)
):
    """Delete an analysis session and its associated feedback records and themes safely."""
    effective_user_id = user_id or auth_user_id
    success = db.delete_analysis(analysis_id, user_id=effective_user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Analysis session not found or deletion failed.")
    return {"message": f"Successfully deleted analysis session {analysis_id}"}


# ==========================================================
# HISTORICAL INTELLIGENCE & HINDSIGHT AI ENDPOINTS
# ==========================================================

@router.get("/hindsight/status")
def get_hindsight_status():
    """Returns Hindsight memory operational status, budget guardrails, and call counters."""
    from backend.services.hindsight_service import hindsight_service
    return hindsight_service.get_status()


@router.post("/hindsight/retain/{analysis_id}")
def retain_hindsight_memory(
    analysis_id: str,
    force: bool = False,
    auth_user_id: Optional[str] = Depends(get_current_user_id)
):
    """Retains a single compact analysis memory in Hindsight with idempotency protection."""
    from backend.services.hindsight_service import hindsight_service
    data = db.get_analysis_by_id(analysis_id)
    if not data:
        raise HTTPException(status_code=404, detail="Analysis session not found.")
    res = hindsight_service.retain_analysis_memory(data, force=force)
    return res


@router.post("/historical-intelligence")
def get_historical_intelligence(
    req: HistoricalIntelligenceRequest,
    auth_user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    On-demand historical intelligence endpoint.
    Compares current analysis with historical sessions using exact Supabase metrics,
    and performs at most ONE recall against Hindsight long-term contextual memory.
    """
    from backend.services.hindsight_service import hindsight_service
    
    # Resolve target analysis ID
    target_id = req.analysis_id or db._local_data.get("active_analysis_id")
    if not target_id:
        history = db.get_history(user_id=auth_user_id)
        if history:
            target_id = history[0].get("id") or history[0].get("analysis_id")
            
    if not target_id:
        return {
            "status": "success",
            "has_sufficient_history": False,
            "answer": "Not enough historical analysis data available yet.",
            "message": "No analysis sessions available. Ingest a dataset to begin."
        }

    question = req.question or "Which complaints have worsened over time?"
    result = hindsight_service.query_historical_intelligence(
        current_analysis_id=target_id,
        question=question,
        user_id=auth_user_id
    )
    return result


@router.get("/historical-intelligence/overview")
def get_historical_intelligence_overview(
    analysis_id: Optional[str] = Query(None),
    auth_user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Returns full historical trends, sentiment drift, and theme matrices
    for the Historical Intelligence dashboard.
    """
    from backend.services.hindsight_service import hindsight_service
    
    target_id = analysis_id or db._local_data.get("active_analysis_id")
    if not target_id:
        history = db.get_history(user_id=auth_user_id)
        if history:
            target_id = history[0].get("id") or history[0].get("analysis_id")
            
    if not target_id:
        return {
            "status": "success",
            "has_sufficient_history": False,
            "message": "Not enough historical analysis data available yet."
        }
        
    return hindsight_service.query_historical_intelligence(
        current_analysis_id=target_id,
        question="Historical overview of trends, improvements, and recurring issues",
        user_id=auth_user_id
    )
