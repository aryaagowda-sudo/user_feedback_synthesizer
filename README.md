# FeedbackIQ — AI-Powered Customer Feedback Intelligence Platform

> Transform raw, unstructured customer feedback into actionable engineering and product intelligence using Natural Language Processing, Machine Learning, and Generative AI.

---

## 🌟 Overview

**FeedbackIQ** is a modern, full-stack intelligence SaaS platform designed for product teams, engineering leads, and customer experience operations. It transforms chaotic customer feedback streams (app store reviews, Zendesk tickets, community Discord messages, in-app surveys) into structured, evidence-based prioritization.

The platform includes:
1. **AI Feedback Summarization Engine**: Groups semantically similar feedback into themes, calculates exact sentiment distributions programmatically, and generates structured executive summaries, main user complaints, key observations, and recommended actions.
2. **Supabase PostgreSQL Persistence & History**: Enterprise relational database with Row Level Security (RLS) policies, authentication, and session history management—with a zero-config local JSON fallback for offline development.
3. **AI Feedback Copilot (RAG Chatbot)**: Intelligent conversational agent grounded strictly in your feedback records and themes, answering questions with exact customer quotes as supporting evidence and recommending relevant follow-up prompts.
4. **ML Model Lab & Retraining Pipeline**: Complete machine learning lifecycle for supervised fine-tuning (DistilBERT), issue category classification (Baseline vs Transformer), overfitting/underfitting prevention, empirical evaluation, data drift tracking, and controlled human-in-the-loop retraining with automated rollback.

---

## 🛠️ Architecture & Tech Stack

### Frontend
- **React.js 18** & **Vite** — High-performance modern web SPA
- **Tailwind CSS** — Bespoke dark-theme UI system inspired by Linear and Stripe
- **Recharts** — Interactive data visualization (Sentiment Donut, Trend Lines, Theme Volume, Stacked Velocity)
- **Lucide React** — Crisp modern iconography
- **Axios** — Interceptor-wrapped API client
- **Supabase JS Client** (`@supabase/supabase-js`) — Authentication and session management

### Backend & AI Pipeline
- **Python 3.10 - 3.13** & **FastAPI** — High-throughput asynchronous REST API
- **Sentence Transformers** (`all-MiniLM-L6-v2`) — 384-dimensional dense semantic vector embeddings for clustering and cosine similarity retrieval
- **Hugging Face Transformers** (`distilbert-base-uncased-finetuned-sst-2-english`) — Calibrated sentiment classification
- **Scikit-learn** — K-Means clustering and feature extraction
- **Generative AI LLM** — Gemini (via official API) / OpenAI (via GPT-4o-mini) with robust, deterministic extractive fallback
- **Supabase Python Client** (`supabase-py`) — PostgreSQL connection with connection resilience
- **Pandas** — Tabular data validation and preprocessing
- **Uvicorn** — Production ASGI server

---

## 📁 Project Structure

```
user_feedback/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── AuthModal.jsx        # Supabase Sign In / Sign Up / Forgot Password
│   │   ├── context/
│   │   │   └── AuthContext.jsx      # Authentication state and hooks
│   │   ├── layouts/
│   │   │   └── MainLayout.jsx       # Linear-style sidebar & navigation
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx        # Executive Overview & Recharts
│   │   │   ├── AnalyzeFeedback.jsx  # CSV / Manual upload & AI Stepper
│   │   │   ├── FeedbackExplorer.jsx # Filterable table & detail drawer
│   │   │   ├── AIInsights.jsx       # AI Theme Summaries & Recommendations
│   │   │   ├── AICopilot.jsx        # Dedicated RAG conversational chat page
│   │   │   ├── AnalysisHistory.jsx  # Past sessions, session switcher & deletion
│   │   │   ├── Trends.jsx           # Temporal velocity & channel charts
│   │   │   └── Settings.jsx         # Supabase status, keys, SQL schema
│   │   ├── services/
│   │   │   ├── api.js               # Backend API client
│   │   │   └── supabase.js          # Supabase client initializer
│   │   ├── App.jsx                  # Application router
│   │   ├── main.jsx                 # React DOM entrypoint
│   │   └── index.css                # Tailwind styling
│   ├── package.json
│   ├── .env.example
│   └── vite.config.js
│
├── backend/
│   ├── main.py                      # FastAPI entrypoint & data preloader
│   ├── api/
│   │   └── routes.py                # REST endpoints (/analytics, /upload, /summarize, /chat, etc.)
│   ├── services/
│   │   ├── sentiment.py             # Hugging Face & heuristic sentiment analyzer
│   │   ├── clustering.py            # SentenceTransformers & K-Means clustering
│   │   ├── summarization.py         # AI theme summarizer (LLM + extractive fallback)
│   │   ├── prioritization.py        # Multi-factor severity & priority ranker
│   │   ├── copilot.py               # RAG Copilot retrieval & conversational engine
│   │   └── insights.py              # Categorized insight synthesis
│   ├── models/
│   │   └── schemas.py               # Pydantic request & response schemas
│   ├── database/
│   │   ├── db.py                    # Supabase client & local JSON database adapter
│   │   └── schema.sql               # Supabase PostgreSQL schema with RLS
│   ├── data/
│   │   └── local_db.json            # Local persistent database
│   ├── requirements.txt             # Python dependencies
│   └── .env.example                 # Backend environment template
│
├── dataset/
│   └── sample_feedback.csv          # 30 realistic feedback records across 5 themes
├── README.md
└── design-system.md
```

---

## ⚙️ Environment Variables Configuration

### Backend (`backend/.env`)
Copy `backend/.env.example` to `backend/.env`:
```env
# Supabase PostgreSQL Integration
# (Leave empty to use automatic zero-config local JSON storage in backend/data/local_db.json)
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key

# Generative AI / LLM Configuration
# (Leave empty to use built-in offline deterministic NLP synthesis and SentenceTransformers)
LLM_API_KEY=your-gemini-or-openai-api-key
LLM_MODEL=gemini-1.5-flash

# Optional individual provider keys
GEMINI_API_KEY=
OPENAI_API_KEY=

# Server Configuration
PORT=8000
HOST=0.0.0.0
```

### Frontend (`frontend/.env`)
Copy `frontend/.env.example` to `frontend/.env`:
```env
# Supabase Authentication & Client
# (Never expose your SUPABASE_SERVICE_ROLE_KEY or LLM_API_KEY in the frontend!)
VITE_SUPABASE_URL=https://your-project-id.supabase.co
VITE_SUPABASE_ANON_KEY=your-supabase-anon-key

# Backend API Endpoint
VITE_API_URL=http://localhost:8000
```

---

## ⚡ Quick Start on Windows

### 1. Start the Backend API

Open a PowerShell terminal in the repository root:

```powershell
# Navigate to the workspace root
cd C:\Users\aryaa\OneDrive\Desktop\user_feedback

# Run the FastAPI server using Python 3.13 (or python)
py -3.13 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

The API will start on **`http://127.0.0.1:8000`**. Interactive Swagger docs are available at **`http://127.0.0.1:8000/docs`**.

### 2. Start the Frontend Development Server

Open a second PowerShell terminal:

```powershell
# Navigate to the frontend directory
cd C:\Users\aryaa\OneDrive\Desktop\user_feedback\frontend

# Start the Vite development server
npm run dev
```

Open your browser to:
👉 **`http://localhost:5173`**

---

## 🧠 ML Training, Evaluation & Controlled Retraining Pipeline

FeedbackIQ features an enterprise-grade supervised Machine Learning training and evaluation lifecycle located in `backend/ml/`. It elevates the platform from relying exclusively on pretrained models to a fully controlled, auditable, and retrainable ML system.

```
backend/ml/
├── dataset_manager.py     # Cleaning, label normalization, deduplication, leak-free stratified & temporal splitting
├── sentiment_trainer.py   # DistilBERT 3-class fine-tuning, balanced class weighting, early stopping, LR scheduling
├── category_classifier.py # TF-IDF + Logistic Regression baseline vs Semantic Transformer Neural comparison
├── evaluator.py           # Standardized evaluation: Macro/Weighted F1, Precision, Recall, Confusion Matrix
├── drift_monitor.py       # Covariate drift tracking (JSD, PSI, Embedding centroid shift, OOV vocabulary)
└── model_registry.py      # Version management, candidate benchmark evaluation, rollback, human correction pool
```

### 1. Dataset Format & Validation
The dataset module supports CSV datasets containing:
- `feedback`: Raw customer review / text (required)
- `sentiment`: `Positive`, `Negative`, or `Neutral` (optional for inference, required for training)
- `category`: Canonical issue taxonomy (`Login and Authentication`, `Payment Issues`, `Performance`, `UI/UX`, `Feature Requests`, `Bugs and Crashes`, `Customer Support`, `Other`)
- `rating`: Optional 1–5 numerical score
- `date`: Timestamp / ISO string for temporal ordering
- `source`: App identifier or ingestion channel

**Data Leakage Prevention:**
- Exact and near-duplicates (normalized lowercase, stripped punctuation, collapsed whitespace SHA-256 hash) are detected and removed strictly **prior to partitioning**.
- `verify_no_leakage()` validates that intersection of train, validation, and test hash sets is strictly zero.
- **Stratified Split:** Partitions data 70% train, 15% validation, and 15% test while preserving class proportions.
- **Temporal Split:** If chronological dates exist, partitions by time (earliest 70% train, subsequent 15% val, latest 15% test) to test forward-looking generalization on future feedback.

### 2. Sentiment Model Fine-Tuning (DistilBERT)
- **Base Architecture:** `distilbert-base-uncased` with sequence classification head (3 classes: Negative, Neutral, Positive).
- **Imbalance Handling:** Scikit-learn `compute_class_weight('balanced')` dynamically weights the PyTorch `CrossEntropyLoss` to prevent dominant classes from overpowering minority classes.
- **Optimization:** AdamW optimizer with weight decay (`0.01`), linear warmup schedule (`0.10` total steps), and gradient clipping (`max_norm=1.0`).
- **Device Support:** Auto-detects NVIDIA CUDA GPU with automatic, thread-optimized CPU fallback on Windows.

### 3. Overfitting & Underfitting Prevention
FeedbackIQ implements systematic safeguards:
- **Early Stopping with Checkpointing:** Monitors validation loss; if validation loss fails to decrease for `patience` consecutive epochs (default 2), training halts and the checkpoint with the highest validation Macro F1 is restored.
- **Loss & Accuracy Trajectory Monitoring:** Epoch curves for Train Loss vs Val Loss and Train Acc vs Val Acc are visualized live in the frontend.
- **Diagnostic Heuristics:**
  - *Overfitting Detected:* Validation loss increases while training loss continues decreasing, or `train_acc - val_acc > 0.15`.
  - *Underfitting Detected:* Both train and validation accuracy fail to surpass baseline thresholds (`<60%`).
  - *Engineering Note:* While early stopping and weight decay substantially mitigate overfitting, no single method eliminates it entirely.

### 4. Feedback Category Classifier (Baseline vs Transformer)
FeedbackIQ builds two distinct supervised architectures on the identical training set and evaluates both on the identical held-out test set:
1. **Linear Baseline:** `TfidfVectorizer(max_features=5000, ngram_range=(1,2), sublinear_tf=True)` + `LogisticRegression(class_weight='balanced', C=1.0)`.
2. **Transformer Neural Classifier:** SentenceTransformers dense embeddings (`all-MiniLM-L6-v2`) + Multi-Layer Perceptron (`128 -> 64 -> 8 classes`) with ReLU activation.
3. **Data-Driven Champion Selection:** Evaluates test Macro F1 and inference latency. If the baseline achieves comparable Macro F1 with 10x lower latency, it is selected as the production champion without assuming the Transformer will always perform best.

### 5. Evaluation Methodology
- Held-out test set is evaluated strictly once after training is finalized (never used for early stopping or hyperparameter search).
- Metrics computed: **Accuracy, Macro Precision, Macro Recall, Macro F1, Weighted F1, and Confusion Matrix**.
- Macro F1 is treated as the primary governance metric because customer feedback datasets exhibit strong class imbalances.

### 6. Controlled Retraining & Model Registry
FeedbackIQ enforces strict retraining governance:
1. Production runs inference on active models.
2. Users can correct sentiment or category predictions in Feedback Explorer.
3. Corrections accumulate in a **Human-in-the-Loop Ground Truth Pool**.
4. Model-generated predictions are **never** treated as ground-truth labels.
5. Retraining is permitted only when the pool reaches a controlled threshold (e.g., $\ge 20$ human annotations).
6. Newly trained models are staged as **Candidates**.
7. Candidate models must pass a benchmark evaluation against the active production model ($\Delta \text{Macro F1} \ge -0.005$).
8. If approved, candidate is promoted; previous production model becomes the **Rollback Target** for one-click reversion.

### 7. Data Drift & Stability Monitoring
The Drift Monitor tracks multidimensional covariate shift between the training baseline and live feedback:
- **Sentiment & Category Shift:** Computes Jensen-Shannon Divergence (JSD) and Population Stability Index (PSI).
- **Embedding Centroid Shift:** Computes cosine distance between average baseline embedding and live feedback centroid.
- **Prediction Confidence Drift:** Monitors average softmax confidence and entropy drops.
- **Vocabulary Drift:** Surfaces emerging out-of-vocabulary keywords gaining statistically significant frequency.
- **Drift Severity:** Categorized as `Low` ($<0.12$), `Moderate` ($0.12 - 0.25$), or `High` ($>0.25$).

---

## 🔌 API Endpoints Reference

### Core Feedback & Analytics
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check, record counts, active mode (Supabase / Local) |
| `GET` | `/analytics` | Dashboard analytics (KPI cards, Donut chart, Trend line, Priority issues) |
| `POST` | `/upload` | Non-blocking background CSV upload returning `job_id` |
| `GET` | `/analysis-status/{job_id}` | Real-time 6-stage NLP analysis progress tracker |
| `POST` | `/analyze` | Analyze JSON batch or multiline raw text input |
| `POST` | `/summarize` | Generate structured AI summaries, main complaints, observations, and recommendations |
| `POST` | `/chat` | AI Feedback Copilot RAG chat with sub-second candidate re-ranking & citations |
| `GET` | `/feedback` | Paginated feedback table with search, sentiment, theme, and date sorting |
| `GET` | `/themes` | Clustered themes sorted by priority rank |
| `GET` | `/insights` | Structured AI insights (Common complaints, Emerging problems, Sprint recommendations) |
| `GET` | `/history` | List of all historical analysis sessions |
| `GET` | `/analysis/{id}` | Full themes and feedback records for a specific historical session |
| `POST` | `/analysis/{id}/activate` | Switch active workspace to a past analysis session |
| `DELETE` | `/analysis/{id}` | Permanently delete an analysis session and its associated data |

### Machine Learning Model Lab
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/ml/datasets/upload` | Upload CSV, validate schema, remove duplicates, compute stats, and create leak-free splits |
| `GET` | `/ml/datasets` | List all ingested datasets with token length & class distribution statistics |
| `POST` | `/ml/train` | Launch asynchronous supervised model training (DistilBERT or Category Classifier) |
| `GET` | `/ml/training-status/{job_id}` | Poll training progress, epoch loss curves, accuracy, and diagnostics |
| `GET` | `/ml/evaluation/{model_id}` | Get evaluation metrics, per-class breakdown, and confusion matrix |
| `GET` | `/ml/models` | List all registered model versions, active production model, and candidate model |
| `GET` | `/ml/models/candidate-evaluation` | Evaluate candidate model against production benchmark metrics |
| `POST` | `/ml/models/promote` | Promote candidate model to active production status if criteria are satisfied |
| `POST` | `/ml/models/rollback` | Instantly roll back production to previous version target |
| `GET` | `/ml/drift` | Compute sentiment, category, embedding, and vocabulary drift report |
| `POST` | `/ml/feedback/correct-label` | Submit human ground-truth label correction for retraining pool |
| `GET` | `/ml/retraining-status` | Get human-in-the-loop candidate pool count and retraining readiness |

---

## 🧪 Running ML Pipeline Tests

Execute the comprehensive automated test suite verifying dataset validation, leakage prevention, early stopping, evaluation metrics, model comparison, registry governance, and drift tracking:

```powershell
py -3.13 backend\tests\test_ml_pipeline.py
```

All 8 test suites execute in ~10 seconds.

---

## 🚢 Deployment Guide

FeedbackIQ includes a production-grade PostgreSQL database schema with Row Level Security (RLS) in `backend/database/schema.sql`.

### The 4 Core Tables:
1. `profiles`: User accounts linked directly to Supabase Auth (`id`, `email`, `full_name`, `created_at`).
2. `analysis_history`: Historical analysis runs (`id`, `user_id`, `analysis_name`, `total_feedback`, `positive_count`, `negative_count`, `neutral_count`, `created_at`).
3. `themes`: Clustered feedback groups with AI summaries (`id`, `analysis_id`, `user_id`, `theme_name`, `summary`, `mention_count`, `positive_percentage`, `negative_percentage`, `neutral_percentage`, `severity`, `priority`, `recommendation`, `main_complaint`, `key_observations`, `representative_feedback`, `created_at`).
4. `feedback`: Granular customer feedback submissions (`id`, `user_id`, `analysis_id`, `feedback_text`, `sentiment`, `sentiment_confidence`, `theme_id`, `source`, `rating`, `created_at`).

To run the schema:
1. Open your Supabase project dashboard at [supabase.com](https://supabase.com).
2. Go to the **SQL Editor**.
3. Paste the contents of `backend/database/schema.sql` and click **Run**.
4. Set the `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in `backend/.env`, and `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` in `frontend/.env`.

---

## 🤖 AI Feedback Copilot Sample Questions

The Copilot chatbot is accessible via the **AI Copilot** navigation tab or top header shortcut:

1. *"What should we fix first?"* — Evaluates critical crashes, high failure rates, and provides root cause recommendations.
2. *"What are the biggest user complaints?"* — Summarizes top negative clusters with supporting customer quotes.
3. *"What features are users requesting?"* — Identifies enhancement requests (e.g. integrations, export formats, dark mode).
4. *"Why is negative sentiment increasing?"* — Breaks down the main drivers of customer dissatisfaction.
5. *"Summarize the feedback about payment issues."* — Aggregates duplicate charges, billing errors, and receipt delivery friction.
6. *"What are the most common login problems?"* — Pinpoints authentication crashes, OAuth timeouts, and session expirations.
7. *"Which issue has the highest priority?"* — Outlines P0/P1 issues based on multi-factor operational urgency.

---

## 🚢 Deployment Guide

### Frontend on Vercel
1. Push code to your GitHub repository.
2. Import the project in Vercel and select `frontend` as the **Root Directory**.
3. Framework Preset: **Vite**.
4. Environment Variables:
   - `VITE_API_URL`: Your Render backend URL (e.g. `https://feedbackiq-api.onrender.com`).
   - `VITE_SUPABASE_URL`: Your Supabase URL.
   - `VITE_SUPABASE_ANON_KEY`: Your Supabase Anon Key.
5. Click **Deploy**.

### Backend on Render
1. Create a new **Web Service** on Render connected to the repository.
2. Environment: **Python 3**.
3. Build Command: `pip install -r backend/requirements.txt`.
4. Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
5. Environment Variables: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `LLM_API_KEY`.
6. Click **Create Web Service**.

---

## 🛡️ License

MIT License © 2026 FeedbackIQ. Built with passion for human product teams powered by genuine AI intelligence.
