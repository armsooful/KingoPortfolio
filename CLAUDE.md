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

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development Phases

The project follows a phased development approach (Phase 0-9). Current work is in Phase 7+ (Portfolio Evaluation). Phase documentation is in `docs/phase*/`.

## Key Patterns

- Routes delegate to services for business logic
- Services use SQLAlchemy models for database operations
- Pydantic schemas validate API request/response
- JWT tokens for authentication
- Rate limiting via slowapi (disabled in tests)
- Test fixtures in `backend/tests/conftest.py` provide db, client, test_user, test_admin
