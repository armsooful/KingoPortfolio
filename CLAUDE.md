# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Foresto Compass (KingoPortfolio) - Investment portfolio simulation and educational platform. This is an educational tool, NOT investment advice. Regulatory compliance (forbidden terms, disclaimers) is enforced throughout.

## Commands

### Backend (Python/FastAPI)

```bash
# Run development server
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run all tests
pytest

# Run tests by category
pytest -m unit -v
pytest -m integration -v
pytest -m e2e -v
pytest -m smoke -v

# Run specific test file
pytest tests/unit/test_auth.py -v

# Run specific test class or function
pytest tests/unit/test_auth.py::TestProfileEndpoints -v
pytest tests/unit/test_auth.py::TestProfileEndpoints::test_get_profile -v

# Run tests with coverage
pytest --cov=app --cov-report=html
```

### Frontend (React/Vite)

```bash
cd frontend
npm run dev      # Start dev server (port 5173)
npm run build    # Production build
npm run lint     # ESLint
npm run preview  # Preview production build
```

## Architecture

```
backend/
├── app/
│   ├── routes/      # 34 API route modules (auth, diagnosis, portfolio, analysis, phase7, etc.)
│   ├── services/    # 47+ service modules (data loading, simulation engines, analytics)
│   ├── models/      # 22 SQLAlchemy ORM models
│   ├── main.py      # FastAPI entry point
│   ├── auth.py      # JWT authentication
│   ├── database.py  # SQLAlchemy configuration
│   ├── config.py    # Environment settings
│   └── schemas.py   # Pydantic request/response schemas
├── tests/
│   ├── unit/        # Unit tests
│   ├── integration/ # Integration tests
│   ├── e2e/         # End-to-end tests
│   └── smoke/       # Smoke tests

frontend/
├── src/
│   ├── pages/       # 26+ page components
│   ├── components/  # Reusable React components
│   ├── services/    # Axios API communication
│   └── styles/      # CSS and Tailwind
```

## Tech Stack

- **Backend**: FastAPI 0.104, Python 3.11, SQLAlchemy 2.0, PostgreSQL
- **Frontend**: React 18, Vite 5, Tailwind CSS 4, React Router 6, Chart.js
- **Testing**: pytest 8.3 with pytest-asyncio, pytest-cov
- **AI Integration**: Anthropic Claude API (optional)
- **Financial Data**: yfinance, pykrx, Alpha Vantage API

## Test Markers

pytest.ini defines 37 markers. Key ones:
- `unit`, `integration`, `e2e`, `smoke` - Test categories
- `auth`, `admin` - Feature areas
- `financial`, `quant`, `valuation` - Financial analysis tests
- `slow` - Long-running tests

## Environment Variables

Backend (.env):
```
DATABASE_URL=postgresql://changrim@localhost:5432/kingo
SECRET_KEY=your-secret-key-min-32-chars
ANTHROPIC_API_KEY=your-api-key (optional)
ALPHA_VANTAGE_API_KEY=your-api-key
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

Frontend (.env.development):
```
VITE_API_URL=http://localhost:8000
```

## Data Management & Admin Routes

### Stock Data Loading
- **Endpoint**: `POST /admin/stocks/load-stocks-from-fdr`
- **Source**: FDR (한국거래소 data) → yfinance (market cap, price) → FSC CRNO API (company registration)
- **Features**: Parallel FSC API calls (5 workers), batch DB upsert, real-time progress tracking
- **Output**: 2885+ Korean stocks with market cap, sector, listing date

### Daily Price Loading
- **Endpoint**: `POST /admin/pykrx/load-daily-prices`
- **Parameters**: `parallel: bool` (default True), `num_workers: int` (1-16, default 8)
- **Optimization**: ThreadPoolExecutor + PostgreSQL batch upsert (0.3s for 500 records)
- **Source**: pykrx → daily OHLCV data
- **Progress**: Real-time updates with Phase 1/2 badges

### Financial Statements & Valuation
- **Endpoint**: `POST /admin/dart/load-financials`
- **Source**: DART API → financial statements (연결, 개별, 재무비율)
- **Calculation**:
  - PER = market_cap / net_income
  - PBR = market_cap / total_equity
  - NULL if negative earnings/equity
- **Features**: Rate limit handling (1 req/sec), corpCode.xml caching, fiscal year selection (default 2024)

### Bond Data Loading
- **Endpoint**: `POST /admin/bonds/load-full-query`
- **Source**: FSC BondBasicInfoFetcher → 19,875+ corporate bonds
- **Features**: Dynamic total calculation, ISIN deduplication, real-time progress with logs
- **Output**: Bond code, name, issuer, maturity, coupon rate, rating

## Frontend Service Architecture

### API Client (`frontend/src/services/api.js`)
- Axios-based HTTP client with base URL from `VITE_API_URL`
- Automatic JWT token injection in headers
- Error handling and response transformation
- Instance-based configuration for different API endpoints

### Component Patterns
- **ProgressModal.jsx**: Real-time task progress display
  - Phase 1/2 badges (green/blue) for visual distinction
  - Polling mechanism with 3-retry 404 handling
  - Auto-dismiss on completion or user action
  - Log scrolling for 50+ item histories

- **DataManagementPage.jsx**: Admin panel for data loading
  - useCallback memoization to prevent unnecessary modal re-renders
  - Multiple loaders (stocks, pykrx, DART, bonds)
  - Success/failure count tracking
  - Real-time UI updates via ProgressModal

### State Management
- Context API for global user auth state
- Local component state for form inputs
- useRef for polling intervals and timeouts

## Key File Locations

### Backend Core Services
- `backend/app/services/real_data_loader.py` — Master loader service (stocks, pykrx, DART, dividends) — 1800+ lines
- `backend/app/services/pykrx_loader.py` — pykrx parallel & batch optimization — 1375 lines
- `backend/app/services/fetchers/dart_fetcher.py` — DART API client with rate limiting
- `backend/app/services/fetchers/bond_basic_info_fetcher.py` — FSC bond data fetcher
- `backend/app/progress_tracker.py` — Task progress tracking system

### Backend Models & Routes
- `backend/app/models/real_data.py` — FinancialStatement, FdrStockListing, DailyPrice models
- `backend/app/models/securities.py` — Stock, Bond, ETF models
- `backend/app/routes/admin.py` — Admin endpoints (load-stocks, load-daily-prices, load-financials, load-bonds)

### Frontend Components
- `frontend/src/components/ProgressModal.jsx` — Real-time progress display with Phase 1/2 badges
- `frontend/src/pages/DataManagementPage.jsx` — Admin panel UI with useCallback optimization
- `frontend/src/services/api.js` — Axios API client

### Database
- `backend/app/database.py` — SQLAlchemy engine, session configuration
- `backend/tests/conftest.py` — Test fixtures (db, client, test_user, test_admin)

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development Phases

The project follows a phased development approach (Phase 0-9):
- **Phase 0**: Basic infrastructure (auth, diagnosis, portfolio design)
- **Phase 1**: Simulation infrastructure (PostgreSQL DDL, ORM models, scenario simulation, caching)
- **Phase 2**: Advanced simulation (rebalancing engine, custom portfolios, performance analysis)
- **Phase 3-A**: Performance interpretation (natural language explanations, benchmark comparison)
- **Phase 3-B**: Premium reporting (PDF reports, analysis history, period comparison)
- **Phase 3-C** (Current): Real data loading (DART, pykrx, FSC bonds, daily prices)

Phase documentation is in `docs/phase*/`.

## Key Patterns

### Core Architecture
- Routes delegate to services for business logic
- Services use SQLAlchemy models for database operations
- Pydantic schemas validate API request/response
- JWT tokens for authentication
- Rate limiting via slowapi (disabled in tests)
- Test fixtures in `backend/tests/conftest.py` provide db, client, test_user, test_admin

### Important Implementation Notes

**DART API & Financial Data**:
- DART response parsing: `account_nm` appears multiple times (income, comprehensive income, cashflow, equity change statements). Use first occurrence only to avoid overwrites.
- Market cap calculation: yfinance combines common + preferred shares (can have minor variance for companies with preferred stock)
- Fiscal year default: 2024 (business reports filed in March 2025; 2026 reports not yet available)
- Some Korean stocks (e.g., NAVER) may have missing DART data for certain fiscal years

**pykrx Limitations**:
- `get_market_fundamental`: KRX endpoint unavailable (HTTP 404)
- `get_market_cap`: Works reliably for Korean stocks
- Use `@dataframe_empty_handler` for graceful error handling

**Progress Tracker Pattern**:
- Always call `update_progress(success=True)` to populate `items_history` (required for Phase 2 detection)
- `complete_task(status='completed')` must use status param, not dict
- First log entry triggers Phase 1→Phase 2 transition in frontend
- Total must be dynamic (set to 0 initially, update after API response)

**React Hooks in ProgressModal**:
- Import destructured: `import { useEffect, useRef }` (not `React.useEffect`)
- Hooks must appear before conditional returns
- Use `useRef` for polling intervals to prevent multiple concurrent polls

### Data Loading & Real Data Pipeline
- **Financial Data Sources**:
  - **yfinance**: US stock market cap, Korean stock prices (FDR integration)
  - **pykrx**: Korean stock daily OHLCV data (6-8x faster with ThreadPoolExecutor + batch upsert)
  - **DART API**: Korean listed company financial statements (PER/PBR calculation)
  - **FSC**: Bond basic info (19,875+ corporate bonds)
  - **Alpha Vantage**: US stock fundamentals (OVERVIEW endpoint)
- **Key Models**: `Stock`, `Bond`, `FinancialStatement`, `DailyPrice`, `DividendHistory`
- **Rate Limiting**: DART enforces 1 request/sec; DartFetcher handles this internally
- **Caching Strategy**: corpCode.xml cached in memory (ticker → corp_code mapping)

### Background Task Management
- **Progress Tracker**: `progress_tracker` class for real-time task monitoring
- **Two-Phase Pattern**:
  - **Phase 1**: Parallel data collection (ThreadPoolExecutor, no progress logging)
  - **Phase 2**: Sequential DB upsert with per-item progress updates
- **Implementation**: BackgroundTasks in FastAPI + SessionLocal per-thread
- **Frontend**: ProgressModal component with real-time polling (1-second intervals)
- **Callback Pattern**: `progress_callback(count, message)` passed to loaders

### Optimization Techniques
- **pykrx Batch Optimization**: PostgreSQL `ON CONFLICT DO UPDATE` reduces N+1 queries (500x improvement)
- **Parallel Threading**: 8 worker threads for API calls + independent DB sessions
- **Progress History**: `items_history` list tracks individual item completion
- **Auto-Close Logic**: Modal closes after 3 seconds or on user dismiss (status="completed")
