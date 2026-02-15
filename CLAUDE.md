# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Foresto Compass (KingoPortfolio) — Investment portfolio simulation and educational platform for Korean markets. This is an educational tool, NOT investment advice. Regulatory compliance (forbidden terms, disclaimers) is enforced throughout.

### Regulatory Compliance (Critical)
- All user-facing analysis must include disclaimer: "교육 목적 참고 정보이며 투자 권유가 아닙니다"
- Forbidden terms: "투자 추천", "매수 추천", "수익 보장" — use "학습 도구", "시뮬레이션", "교육 목적" instead
- Three permission levels: user (default), premium, admin
- Email templates must include full legal notice referencing 자본시장법 제6조
- Compliance docs: `docs/compliance/` (forbidden terms list, terminology guide, scan log)

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

Test markers: `unit`, `integration`, `e2e`, `smoke`, `auth`, `admin`, `financial`, `quant`, `valuation`, `slow`

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
createdb kingo                                    # Create database
psql $DATABASE_URL -f db/ddl/foresto_phase1.sql   # Apply DDL
```

- PostgreSQL: `create_all` is skipped; schema changes require manual SQL migration
- SQLite: `create_all` runs automatically (local dev only)
- `RESET_DB_ON_STARTUP=true` in .env drops and recreates all tables (dev only)

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
└── utils/               # email, export, kst_now, tier_permissions, structured_logging

frontend/src/
├── pages/               # Page components (20+ pages)
├── components/          # Reusable: ProgressModal, ProfileCompletionModal, DataTable, Disclaimer, Footer
├── hooks/useTheme.js    # Dark mode toggle hook (localStorage + system preference)
├── services/api.js      # Axios client with JWT injection + idempotency keys
└── styles/
    ├── theme.css        # CSS design tokens (:root light + [data-theme="dark"])
    └── *.css            # Per-page/component CSS (all theme-aware)
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
| Tier system | `utils/tier_permissions.py` | VIP tier + membership plan permission logic |
| Tests | `tests/conftest.py` | Fixtures: db, client, test_user, test_admin |

## UI Theme System

### Architecture
- **Guide document**: `docs/ui-theme-guide.md` — Complete CSS variable mapping, page patterns, new page checklist
- **Design tokens**: `frontend/src/styles/theme.css` — `:root` (light) + `[data-theme="dark"]` (dark)
- **Toggle hook**: `frontend/src/hooks/useTheme.js` — `useThemeInit()` for App.jsx, `useTheme()` for components
- **Legacy bridge**: App.css `:root` maps `--primary-color` → `var(--primary)` for backward compat

### CSS Variable Categories
| Category | Variables | Light Example | Dark Example |
|----------|-----------|---------------|--------------|
| Background | `--bg`, `--card`, `--card-inner`, `--card-hover` | `#f0f2f5`, `#ffffff` | `#0f172a`, `#1e293b` |
| Text | `--text`, `--text-secondary`, `--text-muted` | `#1f2937`, `#6b7280` | `#f1f5f9`, `#94a3b8` |
| Border | `--border`, `--border-light` | `#e5e7eb`, `#f3f4f6` | `#334155`, `#1e293b` |
| Shadow | `--shadow-sm`, `--shadow-md`, `--shadow-lg` | light rgba | dark rgba |
| Brand | `--primary`, `--primary-dark`, `--accent` | `#667eea`, `#5a6fd1` | same values |
| Stock | `--stock-up`, `--stock-down` | `#16a34a`, `#dc2626` | same values |

### Rules for CSS
- **All colors MUST use CSS variables**. No hardcoded `white`, `#333`, `#e0e0e0`.
- **Class naming**: Page-scoped prefixes required (`{page}-table`, `{page}-error`) to prevent cross-file conflicts.
- **Dark mode overrides**: Use `[data-theme="dark"] .selector` for colors that need different dark values (e.g., error backgrounds use higher opacity `rgba()`).
- **Brand gradients**: `linear-gradient(135deg, #667eea 0%, #764ba2 100%)` is universal — no dark override needed.
- **Disclaimer component**: Uses `.disclaimer-box` CSS class (no inline styles).

### Theme Toggle Implementation
```js
// App.jsx — initialize theme once at app root
const { theme, toggleTheme } = useThemeInit();
// Sets document.documentElement.setAttribute('data-theme', theme)
// Persists to localStorage, listens to system prefers-color-scheme
```

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

## Tier & Permission System

Dual-tier system documented in `backend/docs/TIER_SYSTEM_GUIDE.md`:

- **VIP Tiers** (activity-based): Bronze → Silver → Gold → Platinum → Diamond
  - Earned via activity points: portfolio creation, diagnosis, reports, daily login
  - VIP multiplier: 1.0x (Bronze) to 3.0x (Diamond)
- **Membership Plans**: Free → Starter → Pro → Enterprise
  - Controls feature limits: max portfolios, AI requests, historical data range
- **API**: `GET /auth/tier/permissions`, `GET /auth/tier/status`

## Email System

### Two-Tier Schedule (APScheduler in main.py)
| Time (KST) | Task | Subscribers |
|---|---|---|
| 07:30 | Daily market summary | `daily_market_email=True` |
| 08:00 | Watchlist score alerts | `watchlist_score_alerts=True` |

Both require `is_email_verified=True`. Uses `AsyncIOScheduler` with `CronTrigger(timezone="Asia/Seoul")`.

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

## Frontend Patterns

### API Client (`services/api.js`)
- Axios instance with `VITE_API_URL` base
- Request interceptor: JWT token injection from localStorage
- Idempotency keys: auto-generated for POST/PUT/PATCH/DELETE (header `X-Idempotency-Key`)
- Response interceptor: 401 → clear token + redirect to login

### Component Conventions
- Hooks must appear before any conditional returns (React rules)
- Use `useRef` for polling intervals to prevent multiple concurrent polls
- ProgressModal: 3-retry 404 handling before giving up
- Disclaimer: always use `<Disclaimer />` component, never inline disclaimer text

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

### Timestamp Convention
- `app/utils/kst_now.py` provides `kst_now()` — returns KST (UTC+9) aware datetime
- All `OpsAuditLog`, `BatchJobDefinition`, `OpsAlert` models use `kst_now` for `created_at`
- When querying these tables by date range, use `kst_now()` not `datetime.utcnow()`

### Signup Schema
- `UserCreate` only has `email` + `password` (no `name` field)
- Name is set after signup via `PUT /auth/profile`
- Signup auto-enables `is_email_verified=True` (educational platform, no email verification flow)

### Error Handler Message Sanitization
- `error_handlers.py::_safe_detail()` replaces SYSTEM error messages with generic user-friendly text
- 500 errors → `"일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요."`
- External API errors → `"외부 서비스 응답이 지연되고 있습니다..."`
- Only USER-type errors (4xx) pass through the original detail message

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

## Documentation Index

| Location | Content |
|----------|---------|
| `docs/README.md` | 문서 디렉토리 전체 구조 & 인덱스 |
| `docs/PRD.md` | Product Requirements Document |
| `docs/ui-theme-guide.md` | CSS theme system guide + new page checklist |
| `docs/strategy/` | Business consulting report, competitive analysis, Compass Score report |
| `docs/compliance/` | Forbidden terms, terminology guide, legal review |
| `docs/deployment/` | Vercel, Render, Cloudflare setup guides |
| `docs/architecture/` | System design, algorithms, technical specs |
| `docs/guides/` | Developer & operator guides (DB, data loading, testing, APIs) |
| `docs/ui-mockup/` | Dashboard redesign HTML mockup |
| `docs/archive/` | Historical: phase1-11 docs, changelogs, reports (221 files) |
| `backend/docs/TIER_SYSTEM_GUIDE.md` | VIP tier + membership plan reference |
| `backend/docs/development/` | PROJECT_STATUS, CHANGELOG, TESTING |
| `backend/docs/guides/` | Feature-specific guides (profile, export, rate limiting) |
| `backend/docs/reference/` | API docs, RBAC, error handling reference |

## Development Status

Phased development (Phase 0–11). Phase docs archived in `docs/archive/phase*/`.

**Completed milestones:**
- Compass Score system (scoring engine, screener, watchlist, alerts, AI commentary)
- Market email service with Compass Score integration
- Profile completion flow (signup simplification + modal-based onboarding)
- Global theme system: dark/light mode with CSS variables across all 36+ CSS files
- Dashboard UI redesign: KPI sparklines, AI summary, watchlist cards, news timeline
- Stock comparison page (max 5 stocks, Compass Score comparison)
- PWA support: home screen install, offline app shell, Service Worker caching
- React.lazy code splitting + ErrorBoundary for chunk loading failures

## Tech Stack

- **Backend**: FastAPI, Python 3.11, SQLAlchemy 2.0, PostgreSQL
- **Frontend**: React 18, Vite 5, React Router 6, Chart.js
- **Styling**: CSS custom properties (theme.css) — no CSS-in-JS, no Tailwind utility classes in components
- **Testing**: pytest with pytest-asyncio, pytest-cov (~690 tests, 31% coverage)
- **Financial Data**: yfinance, pykrx, DART API, FSC API, Alpha Vantage
- **Scheduling**: APScheduler (07:30 market email, 08:00 watchlist alerts)
- **Email**: aiosmtplib via Resend SMTP, Jinja2 templates (inline CSS)
- **AI**: Anthropic Claude API (optional, for AI commentary)
