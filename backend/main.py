import os
import csv
import logging
from contextlib import asynccontextmanager

# Ensure Python trusts Windows system certificates (e.g. for antivirus shields/proxies)
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import router, run_nlp_pipeline_sync
from backend.api.ml_routes import ml_router
from backend.database.db import db
from backend.services.sentiment import sentiment_analyzer
from backend.services.clustering import semantic_clusterer

# Optimize CPU thread allocation for Windows multi-core processors
try:
    import torch
    threads = min(8, os.cpu_count() or 4)
    torch.set_num_threads(threads)
except Exception:
    pass

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("feedbackiq.main")

SAMPLE_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "dataset", "sample_feedback.csv")

def preload_models_and_sample_data():
    """Eagerly preloads and warms up ML models once at startup and seeds database if empty."""
    logger.info("Pre-warming NLP models (DistilBERT & SentenceTransformers)...")
    try:
        sentiment_analyzer.preload_models()
        semantic_clusterer.preload_models()
        # Warmup with single dummy string
        _ = sentiment_analyzer.analyze("Model warmup test")
        _ = semantic_clusterer.get_embeddings(["Model warmup test"])
        logger.info("All ML models pre-warmed and ready for high-throughput batch inference.")
    except Exception as e:
        logger.warning(f"Model pre-warm warning: {e}")

    existing = db.get_all_feedback()
    if existing:
        logger.info(f"Database already populated with {len(existing)} feedback records.")
        return

    if not os.path.exists(SAMPLE_CSV_PATH):
        logger.warning(f"Sample CSV not found at {SAMPLE_CSV_PATH}.")
        return

    try:
        logger.info("Initializing database with sample customer feedback dataset...")
        rows = []
        with open(SAMPLE_CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append({
                    "feedback": r.get("feedback", ""),
                    "rating": r.get("rating"),
                    "date": r.get("date"),
                    "source": r.get("source", "Web App")
                })
        if rows:
            run_nlp_pipeline_sync(rows, dataset_name="Production Customer Feedback (Sample)")
            logger.info(f"Successfully processed and seeded {len(rows)} sample feedback records.")
    except Exception as e:
        logger.error(f"Error seeding sample feedback: {e}", exc_info=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting FeedbackIQ API...")
    preload_models_and_sample_data()
    yield
    # Shutdown
    logger.info("Shutting down FeedbackIQ API...")

app = FastAPI(
    title="FeedbackIQ — User Feedback Synthesizer API",
    description="Transforms raw customer feedback into actionable intelligence using NLP and Generative AI",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend Vite dev server, preview, and production domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(ml_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
