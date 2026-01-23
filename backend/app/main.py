from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from datetime import timedelta
import logging
import time
from urllib.parse import quote
import uuid
from dotenv import load_dotenv
from pathlib import Path

# Load .env file
load_dotenv()

from app.config import settings
from app.database import engine, Base, get_db
from app.routes import auth, diagnosis, admin, admin_batch, admin_lineage, admin_data_quality, market, backtesting, krx_timeseries, admin_portfolio, batch_jobs, stock_detail, portfolio_comparison, pdf_report, scenarios, analysis, performance_internal, performance_public, admin_controls, bookmarks, user_settings, event_log, phase7_portfolios, phase7_evaluation, phase7_comparison
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.error_handlers import setup_exception_handlers
from app.rate_limiter import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Import models to register them with Base.metadata
from app.models import securities  # noqa
from app.models import admin_controls as admin_controls_models  # noqa
from app.models.user import User  # noqa
from app.models import phase7_portfolio as phase7_portfolio_models  # noqa
from app.models import phase7_evaluation as phase7_evaluation_models  # noqa

logger = logging.getLogger(__name__)

def init_db():
    if settings.reset_db_on_startup:
        # 환경변수 RESET_DB_ON_STARTUP=true 일 때만 기존 테이블 삭제 후 재생성 (데이터 손실)
        Base.metadata.drop_all(bind=engine)
        print("⚠️ Database tables dropped (RESET_DB_ON_STARTUP=true)")

    # 테이블 생성 (이미 존재하면 무시)
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized (tables created if not exists)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"⚠️ Database initialization warning: {e}")
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
# KingoPortfolio API

투자 전략 학습 플랫폼 백엔드 API

⚠️ **중요**: 본 API는 교육 목적의 시뮬레이션 기능을 제공합니다.
투자 권유·추천·자문·일임 서비스를 제공하지 않습니다.
본 서비스는 자본시장법상 투자자문업·투자일임업에 해당하지 않습니다.

## 주요 기능

- **인증 및 권한 관리**: JWT 기반 사용자 인증, RBAC (Role-Based Access Control)
- **투자 성향 진단**: 설문 기반 투자 성향 분석 (교육 목적)
- **재무 분석**: 주가 데이터 조회 및 재무제표 분석 (정보 제공)
- **밸류에이션**: DCF, DDM, 멀티플 비교 등 기업 가치 평가 학습 도구
- **포트폴리오 시뮬레이션**: 다양한 전략 유형별 구성 예시 (교육 목적)

## 인증 방법

대부분의 엔드포인트는 JWT 토큰 인증이 필요합니다:

1. `/auth/signup` 또는 `/auth/login`으로 토큰 획득
2. `Authorization: Bearer {access_token}` 헤더로 요청
3. Swagger UI에서 우측 상단 "Authorize" 버튼 클릭하여 토큰 입력

## 권한 레벨

- **user**: 일반 사용자 (기본)
- **premium**: 프리미엄 회원 (고급 분석 기능 접근)
- **admin**: 관리자 (모든 기능 접근)

## 에러 응답 형식

모든 에러는 다음 형식으로 반환됩니다:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "사용자 친화적인 에러 메시지",
    "status": 400,
    "extra": {}
  }
}
```
    """,
    summary="KingoPortfolio - 투자 전략 학습 플랫폼 (교육용)",
    terms_of_service="https://github.com/your-org/kingo-portfolio/blob/main/TERMS.md",
    contact={
        "name": "KingoPortfolio Team",
        "url": "https://github.com/your-org/kingo-portfolio",
        "email": "support@kingo-portfolio.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "로컬 개발 서버"
        },
        {
            "url": "https://api.kingo-portfolio.com",
            "description": "프로덕션 서버"
        }
    ],
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "회원가입, 로그인, 토큰 관리 등 인증 관련 API"
        },
        {
            "name": "Survey",
            "description": "투자 성향 진단 설문 API"
        },
        {
            "name": "Diagnosis",
            "description": "투자 성향 분석 API (교육 목적 - 투자 권유 아님)"
        },
        {
            "name": "Admin",
            "description": "관리자 전용 API (데이터 수집, 분석, 모니터링)"
        },
        {
            "name": "Health",
            "description": "서버 상태 확인 API"
        },
        {
            "name": "Scenarios",
            "description": "관리형 시나리오 API (교육 목적 - 투자 권유 아님)"
        },
        {
            "name": "Analysis",
            "description": "포트폴리오 성과 해석 API (Phase 3-A) - 설명 중심, 투자 권유 아님"
        }
    ]
)

# 전역 에러 핸들러 등록
setup_exception_handlers(app)

# Rate Limiter 설정
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    max_age=86400,
    expose_headers=["*"],
)


@app.middleware("http")
async def add_request_id_header(request: Request, call_next):
    request_id = request.headers.get("x-request-id")
    if not request_id:
        request_id = str(uuid.uuid4())
    else:
        try:
            request_id.encode("latin-1")
        except UnicodeEncodeError:
            logger.warning(
                "invalid request_id header; replacing with generated id",
                extra={"request_id": request_id},
            )
            request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.perf_counter()
    response = await call_next(request)
    latency_ms = (time.perf_counter() - start_time) * 1000
    response.headers["x-request-id"] = request_id
    response.headers["x-user-disclaimer"] = quote(settings.user_disclaimer, safe="")
    response.headers["x-user-disclaimer-encoding"] = "urlencoded"
    logger.info(
        "request completed",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "latency_ms": round(latency_ms, 2),
        },
    )
    return response

# Templates 설정
templates_path = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))

app.include_router(auth.router)
app.include_router(diagnosis.router)
app.include_router(admin.router)
app.include_router(admin_batch.router)
app.include_router(admin_lineage.router)
app.include_router(admin_data_quality.router)
app.include_router(market.router)
app.include_router(backtesting.router)
app.include_router(krx_timeseries.router)
app.include_router(admin_portfolio.router)
app.include_router(batch_jobs.router)
app.include_router(stock_detail.router)
app.include_router(portfolio_comparison.router)
app.include_router(pdf_report.router)
app.include_router(scenarios.router)
app.include_router(analysis.router)
app.include_router(performance_internal.router)
app.include_router(performance_public.router)
app.include_router(admin_controls.router)
app.include_router(bookmarks.router)
app.include_router(user_settings.router)
app.include_router(event_log.router)
app.include_router(phase7_portfolios.router)
app.include_router(phase7_evaluation.router)
app.include_router(phase7_comparison.router)
from app.routes import portfolio_public
app.include_router(portfolio_public.router)

# Portfolio router
from app.routes import portfolio
app.include_router(portfolio.router)

from app.auth import get_current_user

# ⚠️ 법적 검토 완료 (2026-01-10): 투자자문업 위반 요소 제거
# 본 설문은 교육 및 정보 제공 목적의 자가 점검 도구입니다.
SURVEY_QUESTIONS = [
    {"id": 1, "category": "experience", "question": "자산 운용 또는 투자 관련 경험은 어느 정도인가요?", "options": [{"value": "A", "text": "처음입니다", "weight": 1.0}, {"value": "B", "text": "약간의 경험이 있습니다", "weight": 2.0}, {"value": "C", "text": "충분한 경험이 있습니다", "weight": 3.0}]},
    {"id": 2, "category": "experience", "question": "과거 자산 운용 또는 투자 과정에서 손실을 경험한 적이 있나요?", "options": [{"value": "A", "text": "없습니다", "weight": 1.0}, {"value": "B", "text": "작은 손실을 경험한 적이 있습니다", "weight": 2.0}, {"value": "C", "text": "큰 손실을 경험한 적이 있습니다", "weight": 3.0}]},
    {"id": 3, "category": "duration", "question": "자산 운용을 학습할 때 주로 고려하는 기간은 어느 정도인가요?", "options": [{"value": "A", "text": "1년 이하", "weight": 1.0}, {"value": "B", "text": "1~3년", "weight": 2.5}, {"value": "C", "text": "3년 이상", "weight": 3.0}]},
    {"id": 4, "category": "duration", "question": "선호하는 투자 전략 학습 방향은 무엇인가요?", "options": [{"value": "A", "text": "안정성 중심 전략", "weight": 1.0}, {"value": "B", "text": "균형형 전략", "weight": 2.0}, {"value": "C", "text": "성장성 중심 전략", "weight": 3.0}]},
    {"id": 5, "category": "risk", "question": "가상 시뮬레이션에서 자산이 10% 하락한 상황을 가정할 때, 학습해 보고 싶은 대응 전략은 무엇인가요?", "options": [{"value": "A", "text": "손실 제한(리스크 관리) 전략", "weight": 1.0}, {"value": "B", "text": "관망 전략", "weight": 2.0}, {"value": "C", "text": "역발상 대응 전략", "weight": 3.0}]},
    {"id": 6, "category": "risk", "question": "자산 가격의 변동성을 어느 정도까지 감내할 수 있다고 느끼시나요?", "options": [{"value": "A", "text": "거의 감내하기 어렵습니다", "weight": 1.0}, {"value": "B", "text": "어느 정도는 감내할 수 있습니다", "weight": 2.0}, {"value": "C", "text": "높은 변동성도 감내할 수 있습니다", "weight": 3.0}]},
    {"id": 7, "category": "risk", "question": "자산 운용을 학습할 때 위험 요소를 어느 정도까지 고려할 수 있나요?", "options": [{"value": "A", "text": "변동성이 낮은 요소 위주로 학습하고 싶습니다", "weight": 1.0}, {"value": "B", "text": "적정 수준의 위험 요소는 고려할 수 있습니다", "weight": 2.0}, {"value": "C", "text": "높은 변동성도 학습 대상으로 고려할 수 있습니다", "weight": 3.0}]},
    {"id": 8, "category": "risk", "question": "가상 시나리오에서 고려 가능한 손실 범위는 어느 정도인가요?", "options": [{"value": "A", "text": "손실은 거의 허용하지 않습니다", "weight": 1.0}, {"value": "B", "text": "약 10% 이내", "weight": 2.0}, {"value": "C", "text": "20% 이상도 학습 대상으로 고려할 수 있습니다", "weight": 3.0}]},
    {"id": 9, "category": "knowledge", "question": "투자와 관련된 일반적인 지식 수준은 어느 정도라고 생각하시나요?", "options": [{"value": "A", "text": "초보자 수준", "weight": 1.0}, {"value": "B", "text": "중급자 수준", "weight": 2.0}, {"value": "C", "text": "고급자 수준", "weight": 3.0}]},
    {"id": 10, "category": "knowledge", "question": "투자 전략을 학습할 때 선호하는 방식은 무엇인가요?", "options": [{"value": "A", "text": "전문가 의견을 참고하며 학습", "weight": 1.5}, {"value": "B", "text": "자료를 분석하며 학습", "weight": 2.0}, {"value": "C", "text": "독립적으로 연구하며 학습", "weight": 2.5}]},
    {"id": 11, "category": "amount", "question": "시뮬레이션에서 학습해 보고 싶은 자산 운용 패턴은 무엇인가요?", "options": [{"value": "A", "text": "단기 변동성 중심 패턴", "weight": 1.0}, {"value": "B", "text": "비정기적 투입 패턴", "weight": 2.0}, {"value": "C", "text": "정기적 적립 패턴", "weight": 3.0}]},
    {"id": 12, "category": "amount", "question": "시뮬레이션에 사용할 가상 월 투자금액 범위는 어느 정도인가요?", "options": [{"value": "A", "text": "소액 (10~50만원)", "weight": 1.0}, {"value": "B", "text": "중액 (50~300만원)", "weight": 2.0}, {"value": "C", "text": "고액 (300만원 이상)", "weight": 3.0}]},
    {"id": 13, "category": "risk", "question": "자산 운용 결과를 확인하는 빈도는 어느 정도가 적절하다고 생각하시나요?", "options": [{"value": "A", "text": "매일 확인", "weight": 1.0}, {"value": "B", "text": "주 1~2회 확인", "weight": 2.0}, {"value": "C", "text": "월 1회 이상 확인", "weight": 3.0}]},
    {"id": 14, "category": "risk", "question": "시장 급변 상황을 가정한 시나리오에서 학습해 보고 싶은 전략은 무엇인가요?", "options": [{"value": "A", "text": "리스크 회피 전략", "weight": 1.0}, {"value": "B", "text": "관망 전략", "weight": 2.0}, {"value": "C", "text": "역발상 대응 전략", "weight": 3.0}]},
    {"id": 15, "category": "duration", "question": "자산 관리 학습 외의 전반적인 재정 상황은 어떠한 편인가요?", "options": [{"value": "A", "text": "여유가 거의 없습니다", "weight": 1.0}, {"value": "B", "text": "크지는 않지만 일정한 여유가 있습니다", "weight": 2.0}, {"value": "C", "text": "여유 자금을 중심으로 학습할 수 있습니다", "weight": 3.0}]},
]

@app.get(
    "/survey/questions",
    tags=["Survey"],
    summary="설문지 문항 조회",
    description="투자 성향 진단을 위한 설문지 문항 목록을 반환합니다.",
    response_description="설문지 문항 목록 (총 15개)"
)
async def get_survey_questions(current_user = Depends(get_current_user)):
    """
    투자 성향 진단 설문지 문항 조회

    총 15개의 문항으로 구성되며, 다음 카테고리로 분류됩니다:
    - **experience**: 투자 경험
    - **duration**: 투자 기간 및 목표
    - **risk**: 위험 감수 성향
    - **knowledge**: 금융 지식 수준
    - **amount**: 투자 금액 및 계획

    각 문항은 A, B, C 선택지를 가지며, 가중치(weight)가 부여됩니다.
    """
    return {"total": len(SURVEY_QUESTIONS), "questions": SURVEY_QUESTIONS}

@app.post(
    "/survey/submit",
    tags=["Survey"],
    summary="설문지 제출",
    description="투자 성향 진단 설문지 답변을 제출합니다.",
    deprecated=True
)
async def submit_survey(data: dict, current_user = Depends(get_current_user)):
    """
    투자 성향 진단 설문지 제출 (Deprecated)

    ⚠️ **주의**: 이 엔드포인트는 더 이상 사용되지 않습니다.
    대신 `/diagnosis/submit`을 사용하세요.
    """
    return {"status": "success"}

@app.post(
    "/token",
    tags=["Authentication"],
    summary="OAuth2 토큰 발급 (Swagger UI용)",
    description="Swagger UI의 Authorize 버튼에서 사용되는 OAuth2 토큰 발급 엔드포인트입니다.",
    response_description="JWT 액세스 토큰"
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 Password Flow 토큰 발급

    Swagger UI의 "Authorize" 버튼에서 사용됩니다.
    일반적인 로그인은 `/auth/login`을 사용하세요.

    **Request Body** (form-data):
    - **username**: 이메일 주소
    - **password**: 비밀번호

    **Response**:
    ```json
    {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer"
    }
    ```
    """
    from app.crud import authenticate_user
    from app.auth import create_access_token

    db_user = authenticate_user(db, form_data.username, form_data.password)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인 정보가 올바르지 않습니다.\n이메일과 비밀번호를 다시 확인해 주세요.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": db_user.email},
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": db_user.id,
            "email": db_user.email,
            "name": getattr(db_user, "name", None),
            "role": db_user.role,
            "created_at": db_user.created_at
        }
    }

@app.get(
    "/health",
    tags=["Health"],
    summary="서버 상태 확인",
    description="서버가 정상 작동 중인지 확인합니다.",
    response_description="서버 상태"
)
async def health():
    """
    헬스 체크 엔드포인트

    서버의 기본적인 응답 가능 여부를 확인합니다.
    로드 밸런서나 모니터링 도구에서 사용됩니다.

    **Response**:
    ```json
    {
        "status": "healthy"
    }
    ```
    """
    return {"status": "healthy"}

@app.get(
    "/",
    response_class=HTMLResponse,
    include_in_schema=False
)
async def landing_page():
    """
    SEO 최적화된 랜딩 페이지

    검색 엔진을 위한 공개 랜딩 페이지를 제공합니다.
    """
    with open(templates_path / "landing.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get(
    "/robots.txt",
    response_class=PlainTextResponse,
    include_in_schema=False
)
async def robots_txt():
    """
    Robots.txt 파일 (검색 엔진 크롤링 규칙)
    """
    return """User-agent: *
Allow: /
Allow: /docs
Allow: /redoc
Disallow: /admin/
Disallow: /auth/
Disallow: /diagnosis/

Sitemap: https://api.kingo-portfolio.com/sitemap.xml
"""

@app.get(
    "/sitemap.xml",
    response_class=PlainTextResponse,
    include_in_schema=False
)
async def sitemap_xml():
    """
    Sitemap.xml 파일 (검색 엔진 인덱싱용)
    """
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://api.kingo-portfolio.com/</loc>
        <lastmod>{today}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>1.0</priority>
    </url>
    <url>
        <loc>https://api.kingo-portfolio.com/docs</loc>
        <lastmod>{today}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>
    <url>
        <loc>https://api.kingo-portfolio.com/redoc</loc>
        <lastmod>{today}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>
    <url>
        <loc>https://kingo-portfolio.vercel.app</loc>
        <lastmod>{today}</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.9</priority>
    </url>
</urlset>
"""
