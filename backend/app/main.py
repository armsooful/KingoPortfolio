from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from datetime import timedelta
from dotenv import load_dotenv
from pathlib import Path

# Load .env file
load_dotenv()

from app.config import settings
from app.database import engine, Base, get_db
from app.routes import auth, diagnosis, admin, market, backtesting, krx_timeseries, admin_portfolio, batch_jobs, stock_detail, portfolio_comparison, pdf_report
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.error_handlers import setup_exception_handlers
from app.rate_limiter import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Import models to register them with Base.metadata
from app.models import securities  # noqa
from app.models.user import User  # noqa

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

# Templates 설정
templates_path = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))

app.include_router(auth.router)
app.include_router(diagnosis.router)
app.include_router(admin.router)
app.include_router(market.router)
app.include_router(backtesting.router)
app.include_router(krx_timeseries.router)
app.include_router(admin_portfolio.router)
app.include_router(batch_jobs.router)
app.include_router(stock_detail.router)
app.include_router(portfolio_comparison.router)
app.include_router(pdf_report.router)

# Portfolio router
from app.routes import portfolio
app.include_router(portfolio.router)

from app.auth import get_current_user

SURVEY_QUESTIONS = [
    {"id": 1, "category": "experience", "question": "당신의 투자 경험은?", "options": [{"value": "A", "text": "처음입니다", "weight": 1.0}, {"value": "B", "text": "약간 있습니다", "weight": 2.0}, {"value": "C", "text": "충분합니다", "weight": 3.0}]},
    {"id": 2, "category": "experience", "question": "투자로 손실을 본 경험이 있으신가요?", "options": [{"value": "A", "text": "없습니다", "weight": 1.0}, {"value": "B", "text": "작은 손실을 본 적 있습니다", "weight": 2.0}, {"value": "C", "text": "큰 손실을 본 적 있습니다", "weight": 3.0}]},
    {"id": 3, "category": "duration", "question": "투자 계획 기간은?", "options": [{"value": "A", "text": "1년 이하", "weight": 1.0}, {"value": "B", "text": "1-3년", "weight": 2.5}, {"value": "C", "text": "3년 이상", "weight": 3.0}]},
    {"id": 4, "category": "duration", "question": "투자 목표는?", "options": [{"value": "A", "text": "안정적 자산 보관", "weight": 1.0}, {"value": "B", "text": "적당한 자산 증식", "weight": 2.0}, {"value": "C", "text": "높은 수익 추구", "weight": 3.0}]},
    {"id": 5, "category": "risk", "question": "포트폴리오가 10% 하락했을 때?", "options": [{"value": "A", "text": "즉시 팔고 싶습니다", "weight": 1.0}, {"value": "B", "text": "지켜보겠습니다", "weight": 2.0}, {"value": "C", "text": "오히려 더 사고 싶습니다", "weight": 3.0}]},
    {"id": 6, "category": "risk", "question": "자산 변동성을 얼마나 견딜 수 있나요?", "options": [{"value": "A", "text": "거의 못 견딥니다", "weight": 1.0}, {"value": "B", "text": "어느 정도 견딜 수 있습니다", "weight": 2.0}, {"value": "C", "text": "충분히 견딜 수 있습니다", "weight": 3.0}]},
    {"id": 7, "category": "risk", "question": "위험을 감수할 의향이 있으신가요?", "options": [{"value": "A", "text": "아니요, 안정성을 원합니다", "weight": 1.0}, {"value": "B", "text": "적정 수준의 위험은 괜찮습니다", "weight": 2.0}, {"value": "C", "text": "높은 수익을 위해 위험을 감수하겠습니다", "weight": 3.0}]},
    {"id": 8, "category": "risk", "question": "투자금의 최대 손실을 어느 정도까지 허용하나요?", "options": [{"value": "A", "text": "0% (손실 불가)", "weight": 1.0}, {"value": "B", "text": "10% 이내", "weight": 2.0}, {"value": "C", "text": "20% 이상", "weight": 3.0}]},
    {"id": 9, "category": "knowledge", "question": "금융상품에 대해 얼마나 알고 있나요?", "options": [{"value": "A", "text": "거의 모릅니다", "weight": 1.0}, {"value": "B", "text": "기본 개념 정도 압니다", "weight": 2.0}, {"value": "C", "text": "깊이 있게 알고 있습니다", "weight": 3.0}]},
    {"id": 10, "category": "knowledge", "question": "투자 결정은 어떻게 하시나요?", "options": [{"value": "A", "text": "전문가 조언을 따릅니다", "weight": 1.5}, {"value": "B", "text": "스스로 분석하고 결정합니다", "weight": 2.0}, {"value": "C", "text": "충분한 분석 후 독립적으로 결정합니다", "weight": 2.5}]},
    {"id": 11, "category": "amount", "question": "정기적인 투자 계획이 있으신가요?", "options": [{"value": "A", "text": "아니요, 수익이 나면 팔려고 합니다", "weight": 1.0}, {"value": "B", "text": "가끔 추가로 투자합니다", "weight": 2.0}, {"value": "C", "text": "정기적으로 계속 투자할 예정입니다", "weight": 3.0}]},
    {"id": 12, "category": "amount", "question": "월 투자 가능액은 대략 어느 정도인가요?", "options": [{"value": "A", "text": "10-50만원", "weight": 1.0}, {"value": "B", "text": "50-300만원", "weight": 2.0}, {"value": "C", "text": "300만원 이상", "weight": 3.0}]},
    {"id": 13, "category": "risk", "question": "투자 성과를 어자 자주 확인하나요?", "options": [{"value": "A", "text": "매일 확인합니다", "weight": 1.0}, {"value": "B", "text": "주 1-2회 확인합니다", "weight": 2.0}, {"value": "C", "text": "월 1회 이상 확인합니다", "weight": 3.0}]},
    {"id": 14, "category": "risk", "question": "시장이 급락할 때 당신의 반응은?", "options": [{"value": "A", "text": "불안해서 매도하고 싶습니다", "weight": 1.0}, {"value": "B", "text": "중립적으로 지켜봅니다", "weight": 2.0}, {"value": "C", "text": "기회라고 생각하고 매수합니다", "weight": 3.0}]},
    {"id": 15, "category": "duration", "question": "투자 외 금융 생활은 안정적인가요?", "options": [{"value": "A", "text": "생활비 충당이 어렵습니다", "weight": 1.0}, {"value": "B", "text": "생활비는 괜찮지만 여유가 적습니다", "weight": 2.0}, {"value": "C", "text": "여유로운 자금으로 투자합니다", "weight": 3.0}]},
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
