from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from contextlib import asynccontextmanager
from datetime import timedelta

from app.config import settings
from app.database import engine, Base, get_db
from app.routes import auth, diagnosis, admin
from sqlalchemy.orm import Session
from app.database import SessionLocal

# Import models to register them with Base.metadata
from app.models import securities  # noqa

def init_db():
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized")


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
    description="AI Portfolio Recommendation Platform",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    max_age=86400,
    expose_headers=["*"],
)

app.include_router(auth.router)
app.include_router(diagnosis.router)
app.include_router(admin.router)

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

@app.get("/survey/questions")
async def get_survey_questions(current_user = Depends(get_current_user)):
    return {"total": len(SURVEY_QUESTIONS), "questions": SURVEY_QUESTIONS}

@app.post("/survey/submit")
async def submit_survey(data: dict, current_user = Depends(get_current_user)):
    return {"status": "success"}

@app.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    from app.crud import authenticate_user
    from app.auth import create_access_token
    
    db_user = authenticate_user(db, form_data.username, form_data.password)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": db_user.email},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {"message": "Welcome to KingoPortfolio API"}
