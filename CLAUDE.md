# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Foresto Compass (KingoPortfolio) — Investment portfolio simulation and educational platform for Korean markets. This is an educational tool, NOT investment advice. Regulatory compliance (forbidden terms, disclaimers) is enforced throughout.

## Commands

### Backend (Python/FastAPI)

```bash
cd backend

# Development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Install dependencies
pip install -r requirements.txt

# Tests
pytest                                    # All tests (with coverage)
pytest -m unit -v                         # By category: unit, integration, e2e, smoke
pytest tests/unit/test_auth.py -v         # Single file
pytest tests/unit/test_auth.py::TestProfileEndpoints::test_get_profile -v  # Single test
```

### Frontend (React/Vite)

```bash
cd frontend
npm install      # Install dependencies
npm run dev      # Dev server (port 5173)
npm run build    # Production build
npm run lint     # ESLint
```

### Database

PostgreSQL required. No Alembic — schema is managed manually via SQL or `create_all` (SQLite only for local dev).

```bash
# Ensure PostgreSQL is running with database 'kingo'
createdb kingo   # if not exists
```

## Architecture

```
backend/app/
├── main.py          # FastAPI entry, lifespan, survey questions, health check
├── auth.py          # JWT authentication (get_current_user)
├── database.py      # SQLAlchemy engine, SessionLocal, Base, get_db dependency
├── config.py        # Pydantic settings from .env
├── schemas.py       # Pydantic request/response schemas
├── progress_tracker.py  # Real-time task progress system
├── routes/          # API route modules (admin, auth, diagnosis, securities, etc.)
├── services/        # Business logic (data loading, simulation, analytics)
│   └── fetchers/    # External API clients (DART, FSC, etc.)
└── models/          # SQLAlchemy ORM models

frontend/src/
├── pages/           # Page components
├── components/      # Reusable components (ProgressModal, etc.)
├── services/api.js  # Axios client with JWT injection
└── styles/          # CSS and Tailwind
```

### Request Flow

Routes → Services → Models (SQLAlchemy) → PostgreSQL. Pydantic schemas validate request/response. JWT tokens for auth, rate limiting via slowapi (disabled in tests).

### Key Files

| Area | File | Purpose |
|------|------|---------|
| Data loading | `services/real_data_loader.py` | Master loader (stocks, pykrx, DART, dividends) |
| Data loading | `services/pykrx_loader.py` | pykrx parallel & batch optimization |
| Data loading | `services/fetchers/dart_fetcher.py` | DART API client with rate limiting |
| Data loading | `services/fetchers/bond_basic_info_fetcher.py` | FSC bond data fetcher |
| Models | `models/real_data.py` | FinancialStatement, FdrStockListing, StockPriceDaily |
| Models | `models/securities.py` | Stock, Bond, ETF |
| Admin API | `routes/admin.py` | Data loading endpoints |
| Frontend | `pages/DataManagementPage.jsx` | Admin panel UI |
| Frontend | `components/ProgressModal.jsx` | Real-time progress display |
| Tests | `tests/conftest.py` | Fixtures: db, client, test_user, test_admin |

## Data Pipeline

### Sources & Endpoints

| Data | Source | Endpoint | Notes |
|------|--------|----------|-------|
| Korean stocks | FDR → yfinance → FSC CRNO | `POST /admin/stocks/load-stocks-from-fdr` | 2885+ stocks |
| Daily prices | pykrx | `POST /admin/pykrx/load-daily-prices` | ThreadPoolExecutor + batch upsert |
| Financials | DART API | `POST /admin/dart/load-financials` | PER/PBR calculated; 1 req/sec rate limit |
| Bonds | FSC | `POST /admin/bonds/load-full-query` | 19,875+ corporate bonds |
| US stocks | Alpha Vantage | — | OVERVIEW endpoint; Korean stocks NOT supported |

### Valuation Calculation

- PER = market_cap / net_income (NULL if negative earnings)
- PBR = market_cap / total_equity (NULL if negative equity)
- Fiscal year default: 2024 (2026 reports not yet available)

## Background Task Pattern

All data loading runs as FastAPI `BackgroundTasks`:

```python
task_id = f"prefix_{uuid.uuid4().hex[:8]}"
operator_id = str(current_user.id)  # capture outside closure

def background_fn():
    db = SessionLocal()
    try:
        progress_tracker.start_task(task_id, total=0)  # dynamic total
        # ... work ...
        progress_tracker.update_progress(task_id, success=True, message="...")
        progress_tracker.complete_task(task_id, status='completed')
    finally:
        db.close()
```

**Two-Phase execution:**
- **Phase 1**: Parallel data collection (ThreadPoolExecutor, no per-item progress)
- **Phase 2**: Sequential DB upsert with per-item `update_progress` calls

**Frontend polling**: ProgressModal polls every 1 second, shows Phase 1/2 badges, auto-closes on completion.

## Critical Implementation Notes

### DART API Parsing
- `account_nm` appears multiple times across financial statements (income, cashflow, equity change). **Use first occurrence only** to avoid overwrites.
- Some stocks (e.g., NAVER) may have missing DART data for certain fiscal years.
- corpCode.xml is cached in memory (ticker → corp_code mapping).

### pykrx Limitations
- `get_market_fundamental`: **Broken** — KRX endpoint returns HTTP 404
- `get_market_cap`: Works reliably
- `@dataframe_empty_handler` silently returns empty DataFrame on errors

### Progress Tracker Gotchas
- Must call `update_progress(success=True)` to populate `items_history` (required for Phase 2 detection in frontend)
- `complete_task(status='completed')` takes status as param, not dict
- Set total to 0 initially, update dynamically after API response

### React ProgressModal
- Hooks must appear before any conditional returns
- Use `useRef` for polling intervals to prevent multiple concurrent polls
- 3-retry 404 handling before giving up

## Environment Variables

Backend `.env`:
```
DATABASE_URL=postgresql://changrim@localhost:5432/kingo
SECRET_KEY=your-secret-key-min-32-chars
ANTHROPIC_API_KEY=your-api-key  # optional
ALPHA_VANTAGE_API_KEY=your-api-key
DART_API_KEY=your-api-key
FSS_API_KEY=your-api-key
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

Frontend `.env.development`:
```
VITE_API_URL=http://localhost:8000
```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development Phases

Phased development (Phase 0–9). Currently on **Phase 3-C** (Real data loading). Phase docs in `docs/phase*/`. Backend docs index at `backend/docs/README.md`.

## Tech Stack

- **Backend**: FastAPI, Python 3.11, SQLAlchemy 2.0, PostgreSQL
- **Frontend**: React 18, Vite 5, Tailwind CSS 4, React Router 6, Chart.js
- **Testing**: pytest with pytest-asyncio, pytest-cov (markers: unit, integration, e2e, smoke, auth, admin, financial, quant, valuation, slow)
- **Financial Data**: yfinance, pykrx, DART API, FSC API, Alpha Vantage
