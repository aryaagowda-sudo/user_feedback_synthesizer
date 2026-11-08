# FeedbackIQ — Complete Testing & QA Guide

This guide provides exact Windows PowerShell commands to run the automated test suite, security audits, performance benchmarks, and local dev servers.

---

## 1. Prerequisites

Ensure Python 3.13 and Node.js are available on your system:
```powershell
py -3.13 --version
node -v
npm -v
```

Install backend dependencies and testing tools:
```powershell
py -3.13 -m pip install -r backend/requirements.txt
py -3.13 -m pip install pytest bandit
```

Install frontend dependencies:
```powershell
cd frontend
npm install
cd ..
```

---

## 2. Automated Test Suite Execution

You can run the entire automated test suite or specific test modules using `npm test` or `pytest`.

### Run All 67 Automated Tests
```powershell
npm test
```
*Or directly via Python:*
```powershell
py -3.13 -m pytest backend/tests -v
```

---

## 3. Individual Test Module Execution

### 1. CSV Ingestion & Edge Cases (20 Cases)
Tests 10, 100, 1k rows, empty file, headers only, null values, exact duplicates, near-duplicates, unescaped quotes, multilingual text, emojis, ultra-long text, XSS/SQL injection payloads, and UTF-8 BOM.
```powershell
py -3.13 -m pytest backend/tests/test_csv_ingestion_edge_cases.py -v
```

### 2. REST API Endpoints & Route Contracts (15 Tests)
Tests system status, pagination, sentiment filters, themes, insights, copilot Q&A, prompt injection handling, history, 404/422 errors, and ML routes.
```powershell
py -3.13 -m pytest backend/tests/test_api_endpoints.py -v
```

### 3. NLP, ML & Complaint Classification (5 Tests)
Tests DistilBERT accuracy/F1/confusion matrix, 384-d sentence embeddings, K-Means silhouette scores, and strict complaint qualification.
```powershell
py -3.13 -m pytest backend/tests/test_nlp_ml_comprehensive.py -v
```

### 4. ML Model Lab & Retraining Pipeline (8 Tests)
Tests leak-free train/val/test splits, temporal splitting, TF-IDF vs Neural comparison, model registry governance, candidate promotion/rollback, and drift monitoring.
```powershell
py -3.13 -m pytest backend/tests/test_ml_pipeline.py -v
```

### 5. Supabase Database & Multi-Tenant RLS (6 Tests)
Tests dual-mode detection, UUID session persistence, cascade deletion, and multi-user data isolation.
```powershell
py -3.13 -m pytest backend/tests/test_supabase_integration.py -v
```

### 6. Hindsight AI Credit Conservation ($5 Protection) (9 Tests)
Tests token limits (<800 tokens), idempotency (0 double retains), TTL cache hits (0 credits consumed), and disabled/offline fallback.
```powershell
py -3.13 -m pytest backend/tests/test_hindsight_service.py -v
```

### 7. Performance & Stress Testing (4 Tests)
Measures inference throughput, embedding generation speed, clustering latency, and memory stability.
```powershell
py -3.13 -m pytest backend/tests/test_performance_stress.py -v
```

---

## 4. Security Audit Execution

### Backend Python Security Scan (Bandit AST)
Scans for hardcoded credentials, insecure bindings, injection flaws, and unsafe libraries:
```powershell
npm run test:security
```
*Or directly via Python:*
```powershell
py -3.13 -m bandit -r backend -ll
```

### Frontend Dependency Vulnerability Audit
```powershell
npm audit --prefix frontend
```

---

## 5. Running the Application Locally

### Start Backend API Server
```powershell
npm run dev:backend
```
*API will be live at:* `http://127.0.0.1:8000`  
*Swagger Documentation:* `http://127.0.0.1:8000/docs`

### Start Frontend Vite Dev Server
```powershell
npm run dev:frontend
```
*Frontend will be live at:* `http://localhost:5173`

---

## 6. Verifying Production Build

Verify the frontend compiles cleanly for production:
```powershell
npm run build
```
Output bundle will be generated in `frontend/dist`.
