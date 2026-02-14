# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Foresto Compass (KingoPortfolio) — Investment portfolio simulation and educational platform for Korean markets. This is an educational tool, NOT investment advice. Regulatory compliance (forbidden terms, disclaimers) is enforced throughout.

### Regulatory Compliance (Critical)
- All user-facing analysis must include disclaimer: "교육 목적 참고 정보이며 투자 권유가 아닙니다"
- Forbidden terms: "투자 추천", "매수 추천", "수익 보장" — use "학습 도구", "시뮬레이션", "교육 목적" instead
- Three permission levels: user (default), premium, admin
- Email templates must include full legal notice referencing 자본시장법 제6조

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
├── main.py              # FastAPI entry, lifespan, APScheduler, health check
├── auth.py              # JWT auth (get_current_user), unsubscribe tokens
├── database.py          # SQLAlchemy engine, SessionLocal, Base, get_db
├── config.py            # Settings from .env
├── schemas.py           # Pydantic request/response schemas
├── progress_tracker.py  # Real-time task progress system
├── routes/              # API route modules
├── services/            # Business logic (scoring, data loading, analytics)
│   ├── scoring_engine.py     # Compass Score (4-axis integrated scoring)
│   ├── market_email_service.py  # Daily market email + Compass Score cards
│   ├── watchlist_alert_service.py  # Score change alert emails
│   └── fetchers/        # External API clients (DART, FSC, etc.)
├── models/              # SQLAlchemy ORM models
├── templates/           # Jinja2 email templates (inline CSS only)
└── utils/email.py       # Async SMTP via aiosmtplib

frontend/src/
├── pages/           # Page components
├── components/      # Reusable components (ProgressModal, ProfileCompletionModal, etc.)
├── services/api.js  # Axios client with JWT injection
└── styles/          # CSS and Tailwind
```

### Request Flow

Routes → Services → Models (SQLAlchemy) → PostgreSQL. Pydantic schemas validate request/response. JWT tokens for auth, rate limiting via slowapi (disabled in tests).

### Core Feature Areas

1. **Investment profile diagnosis** — SurveyPage → DiagnosisResultPage (survey → profile → portfolio)
2. **Compass Score** — 4-axis integrated scoring: financial(30%) + valuation(20%) + technical(30%) + risk(20%) → `services/scoring_engine.py`
3. **Financial statement analysis** — DART → ROE, ROA, margins, CAGR, FCF → `services/financial_analyzer.py`
4. **Valuation** — PER/PBR multiples + DCF + DDM → `services/valuation.py`
5. **Technical analysis** — 11 indicators (SMA, RSI, BB, MACD, Stochastic, ATR, ADX, OBV, MA alignment, 52-week, Golden Cross) → `services/quant_analyzer.py`
6. **Portfolio construction & optimization** — MVO, Risk Parity → `services/portfolio_engine.py`
7. **Backtesting** — Historical performance with rebalancing → `services/backtesting.py`
8. **Scenario simulation** — Macro variable impact → `services/scenario_simulation.py`
9. **Stock screener & watchlist** — Filter by Compass Score, track score changes → `routes/screener.py`, `routes/watchlist.py`
10. **Market dashboard & daily email** — APScheduler at 07:30/08:00 KST → `services/market_email_service.py`, `services/watchlist_alert_service.py`
11. **AI commentary** — Claude API on-demand stock analysis → `routes/stock_detail.py`
12. **PDF investment report** — Auto-generated analyst-style reports → `services/pdf_report_generator.py`

### Key Files

| Area | File | Purpose |
|------|------|---------|
| Scoring | `services/scoring_engine.py` | Compass Score 4-axis calculation + rule-based commentary |
| Data loading | `services/real_data_loader.py` | Master loader (stocks, pykrx, DART, dividends) |
| Data loading | `services/pykrx_loader.py` | pykrx parallel & batch optimization |
| Data loading | `services/fetchers/dart_fetcher.py` | DART API client with rate limiting |
| Models | `models/real_data.py` | FinancialStatement, FdrStockListing, StockPriceDaily |
| Models | `models/securities.py` | Stock (includes compass_score fields), Bond, ETF |
| Models | `models/watchlist.py` | Watchlist with last_notified_score/grade |
| Models | `models/user_preferences.py` | UserNotificationSetting (email subscriptions) |
| Models | `models/market_email_log.py` | Email sending logs (duplicate prevention) |
| Email | `services/market_email_service.py` | Daily market summary + Compass Score cards |
| Email | `services/watchlist_alert_service.py` | Score change alerts (±5 points threshold) |
| Email | `templates/market_daily_email.html` | HTML email template (all inline CSS) |
| Admin API | `routes/admin.py` | Data loading endpoints |
| Subscription | `routes/market_subscription.py` | Subscribe/unsubscribe + one-click unsubscribe |
| AI | `routes/stock_detail.py` | On-demand AI commentary (Claude Sonnet 4.5) |
| Frontend | `components/ProgressModal.jsx` | Real-time progress display |
| Frontend | `components/ProfileCompletionModal.jsx` | Post-signup profile completion |
| Tests | `tests/conftest.py` | Fixtures: db, client, test_user, test_admin |

## Compass Score System

### Calculation Flow
1. `ScoringEngine.calculate_compass_score(db, ticker)` calls:
   - `FinancialAnalyzer` → financial_score (30%)
   - `ValuationAnalyzer` → valuation_score (20%)
   - `QuantAnalyzer` → technical_score (30%) + risk_score (20%)
2. Weights are dynamically redistributed if any category has no data
3. Grade: S(90+), A+(80+), A(70+), B+(60+), B(50+), C+(40+), C(30+), D(20+), F(<20)
4. Rule-based commentary generated from indicator values
5. Results stored in `stocks` table compass_* columns for fast querying

### Stock Model Compass Fields
`compass_score`, `compass_grade`, `compass_summary`, `compass_commentary`, `compass_financial_score`, `compass_valuation_score`, `compass_technical_score`, `compass_risk_score`, `compass_updated_at`

### AI Commentary
- Endpoint: `POST /admin/stock-detail/{ticker}/ai-commentary`
- Uses Claude Sonnet 4.5 to generate 5-7 sentence Korean analysis
- Falls back to rule-based commentary if `ANTHROPIC_API_KEY` not set or API fails

## Email System

### Two-Tier Schedule (APScheduler in main.py)
| Time (KST) | Task | Subscribers |
|---|---|---|
| 07:30 | Daily market summary | `daily_market_email=True` |
| 08:00 | Watchlist score alerts | `watchlist_score_alerts=True` |

Both require `is_email_verified=True`.

### Market Email Content
- 4 indices (KOSPI, KOSDAQ, S&P 500, NASDAQ) via yfinance
- Top 3 gainers/losers via pykrx
- 5 news items via Naver Finance
- Compass Score highlights: 4-axis bar chart + commentary per stock
- Score movers: stocks with ±5 point changes
- One-click unsubscribe link (JWT token, 30-day validity)

### Email Template Rules
- **All CSS must be inline** — Naver Mail strips `<style>` blocks
- Use `<table>` layouts, not `<div>` with flexbox — email client compatibility
- All `<table>` elements need `cellpadding="0" cellspacing="0"` and inline `style`
- `unsubscribe_url` falls back to `frontend_url + '/profile'` if not provided

### Duplicate Prevention
`MarketEmailLog` table tracks sends per date. Status `completed` or `sending` blocks re-sends.

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

### Model Registration
- All new SQLAlchemy models must be imported in `main.py` with `# noqa` for `Base.metadata` registration
- PostgreSQL: `create_all` is skipped; schema changes require manual SQL migration
- SQLite: `create_all` runs automatically (local dev only)

## Environment Variables

Backend `.env`:
```
DATABASE_URL=postgresql://changrim@localhost:5432/kingo
SECRET_KEY=your-secret-key-min-32-chars
ANTHROPIC_API_KEY=your-api-key  # optional, for AI commentary
ALPHA_VANTAGE_API_KEY=your-api-key
DART_API_KEY=your-api-key
FSS_API_KEY=your-api-key
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
SMTP_HOST=smtp.resend.com
SMTP_PORT=587
SMTP_USER=resend
SMTP_PASSWORD=your-resend-api-key
SMTP_FROM_EMAIL=noreply@yourdomain.com
SMTP_FROM_NAME=Foresto Compass
FRONTEND_URL=http://localhost:5173
API_BASE_URL=http://localhost:8000
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

**Completed milestones:**
- Compass Score system (scoring engine, screener, watchlist, alerts, AI commentary)
- Market email service with Compass Score integration
- Profile completion flow (signup simplification + modal-based onboarding)

**Competitive analysis**: `docs/foresto-competitive-strategy-report.md` — gap analysis vs StockMatrix, AlphaSquare, IntelliQuant, Quantus, Securities Plus.

## UI Theme System

- **Guide document**: `docs/ui-theme-guide.md` — CSS variable mapping, page patterns, new page checklist
- **Theme file**: `frontend/src/styles/theme.css` — `:root` (light) + `[data-theme="dark"]` (dark)
- **Toggle hook**: `frontend/src/hooks/useTheme.js`
- **Key rule**: All colors MUST use CSS variables (`--card`, `--text`, `--border`, `--card-inner`). No hardcoded `white`, `#333`, `#e0e0e0`.
- **Class naming**: Page-scoped prefixes required (`{page}-table`, `{page}-error`) to prevent cross-file conflicts.
- **Disclaimer component**: Uses `.disclaimer-box` CSS class (no inline styles).

## Tech Stack

- **Backend**: FastAPI, Python 3.11, SQLAlchemy 2.0, PostgreSQL
- **Frontend**: React 18, Vite 5, Tailwind CSS 4, React Router 6, Chart.js
- **Testing**: pytest with pytest-asyncio, pytest-cov (markers: unit, integration, e2e, smoke, auth, admin, financial, quant, valuation, slow)
- **Financial Data**: yfinance, pykrx, DART API, FSC API, Alpha Vantage
- **Scheduling**: APScheduler (07:30 market email, 08:00 watchlist alerts)
- **Email**: aiosmtplib via Resend SMTP, Jinja2 templates (inline CSS)
- **AI**: Anthropic Claude API (optional, for AI commentary)
