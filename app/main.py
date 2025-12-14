from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from contextlib import asynccontextmanager
from datetime import timedelta

from app.config import settings
from app.database import engine, Base, get_db
from app.models import SurveyQuestion
from app.routes import auth, survey, diagnosis
from sqlalchemy.orm import Session
from app.database import SessionLocal


# 초기화 함수
def init_db():
    """데이터베이스 테이블 생성 및 초기 데이터 삽입"""
    # 테이블 생성
    Base.metadata.create_all(bind=engine)
    
    # 초기 설문 데이터 삽입
    db = SessionLocal()
    try:
        # 기존 데이터 확인
        existing_questions = db.query(SurveyQuestion).count()
        
        if existing_questions == 0:
            # 설문 문항 초기화
            survey_data = [
                # 1. 투자 경험도
                {
                    "category": "experience",
                    "question": "당신의 투자 경험은?",
                    "option_a": "처음입니다 (투자 경험 없음)",
                    "option_b": "약간 있습니다 (1-2년)",
                    "option_c": "충분합니다 (3년 이상)",
                    "weight_a": 1.0,
                    "weight_b": 2.0,
                    "weight_c": 3.0,
                },
                # 2. 손실 경험
                {
                    "category": "experience",
                    "question": "투자로 손실을 본 경험이 있으신가요?",
                    "option_a": "없습니다",
                    "option_b": "작은 손실을 본 적 있습니다",
                    "option_c": "큰 손실을 본 적 있습니다",
                    "weight_a": 1.0,
                    "weight_b": 2.0,
                    "weight_c": 3.0,
                },
                # 3. 투자 기간
                {
                    "category": "duration",
                    "question": "투자 계획 기간은?",
                    "option_a": "1년 이하",
                    "option_b": "1-3년",
                    "weight_a": 1.0,
                    "weight_b": 2.5,
                },
                # 4. 투자 목표
                {
                    "category": "duration",
                    "question": "투자 목표는?",
                    "option_a": "안정적 자산 보관",
                    "option_b": "적당한 자산 증식",
                    "option_c": "높은 수익 추구",
                    "weight_a": 1.0,
                    "weight_b": 2.0,
                    "weight_c": 3.0,
                },
                # 5. 포트폴리오 하락 시 대응
                {
                    "category": "risk",
                    "question": "포트폴리오가 10% 하락했을 때?",
                    "option_a": "즉시 팔고 싶습니다",
                    "option_b": "지켜보겠습니다",
                    "option_c": "오히려 더 사고 싶습니다",
                    "weight_a": 1.0,
                    "weight_b": 2.0,
                    "weight_c": 3.0,
                },
                # 6. 자산 변동성 허용도
                {
                    "category": "risk",
                    "question": "자산 변동성을 얼마나 견딜 수 있나요?",
                    "option_a": "거의 못 견딥니다",
                    "option_b": "어느 정도 견딜 수 있습니다",
                    "option_c": "충분히 견딜 수 있습니다",
                    "weight_a": 1.0,
                    "weight_b": 2.0,
                    "weight_c": 3.0,
                },
                # 7. 위험 선호도
                {
                    "category": "risk",
                    "question": "위험을 감수할 의향이 있으신가요?",
                    "option_a": "아니요, 안정성을 원합니다",
                    "option_b": "적정 수준의 위험은 괜찮습니다",
                    "option_c": "높은 수익을 위해 위험을 감수하겠습니다",
                    "weight_a": 1.0,
                    "weight_b": 2.0,
                    "weight_c": 3.0,
                },
                # 8. 손실 한도
                {
                    "category": "risk",
                    "question": "투자금의 최대 손실을 어느 정도까지 허용하나요?",
                    "option_a": "0% (손실 불가)",
                    "option_b": "10% 이내",
                    "option_c": "20% 이상",
                    "weight_a": 1.0,
                    "weight_b": 2.0,
                    "weight_c": 3.0,
                },
                # 9. 금융 지식
                {
                    "category": "knowledge",
                    "question": "금융상품에 대해 얼마나 알고 있나요?",
                    "option_a": "거의 모릅니다",
                    "option_b": "기본 개념 정도 압니다",
                    "option_c": "깊이 있게 알고 있습니다",
                    "weight_a": 1.0,
                    "weight_b": 2.0,
                    "weight_c": 3.0,
                },
                # 10. 투자 결정 스타일
                {
                    "category": "knowledge",
                    "question": "투자 결정은 어떻게 하시나요?",
                    "option_a": "전문가 조언을 따릅니다",
                    "option_b": "스스로 분석하고 결정합니다",
                    "option_c": "충분한 분석 후 독립적으로 결정합니다",
                    "weight_a": 1.5,
                    "weight_b": 2.0,
                    "weight_c": 2.5,
                },
                # 11. 투자 주기
                {
                    "category": "amount",
                    "question": "정기적인 투자 계획이 있으신가요?",
                    "option_a": "아니요, 수익이 나면 팔려고 합니다",
                    "option_b": "가끔 추가로 투자합니다",
                    "option_c": "정기적으로 계속 투자할 예정입니다",
                    "weight_a": 1.0,
                    "weight_b": 2.0,
                    "weight_c": 3.0,
                },
                # 12. 월 투자 가능액
                {
                    "category": "amount",
                    "question": "월 투자 가능액은 대략 어느 정도인가요?",
                    "option_a": "10-50만원",
                    "option_b": "50-300만원",
                    "option_c": "300만원 이상",
                    "weight_a": 1.0,
                    "weight_b": 2.0,
                    "weight_c": 3.0,
                },
                # 13. 성과 모니터링
                {
                    "category": "risk",
                    "question": "투자 성과를 어자 자주 확인하나요?",
                    "option_a": "매일 확인합니다",
                    "option_b": "주 1-2회 확인합니다",
                    "option_c": "월 1회 이상 확인합니다",
                    "weight_a": 1.0,
                    "weight_b": 2.0,
                    "weight_c": 3.0,
                },
                # 14. 시장 변동 대응
                {
                    "category": "risk",
                    "question": "시장이 급락할 때 당신의 반응은?",
                    "option_a": "불안해서 매도하고 싶습니다",
                    "option_b": "중립적으로 지켜봅니다",
                    "option_c": "기회라고 생각하고 매수합니다",
                    "weight_a": 1.0,
                    "weight_b": 2.0,
                    "weight_c": 3.0,
                },
                # 15. 종합 재무 건강도
                {
                    "category": "duration",
                    "question": "투자 외 금융 생활은 안정적인가요?",
                    "option_a": "생활비 충당이 어렵습니다",
                    "option_b": "생활비는 괜찮지만 여유가 적습니다",
                    "option_c": "여유로운 자금으로 투자합니다",
                    "weight_a": 1.0,
                    "weight_b": 2.0,
                    "weight_c": 3.0,
                },
            ]
            
            # 데이터베이스에 삽입
            for i, data in enumerate(survey_data, 1):
                question = SurveyQuestion(
                    id=i,
                    category=data["category"],
                    question=data["question"],
                    option_a=data["option_a"],
                    option_b=data["option_b"],
                    option_c=data.get("option_c"),
                    weight_a=data["weight_a"],
                    weight_b=data["weight_b"],
                    weight_c=data.get("weight_c"),
                )
                db.add(question)
            
            db.commit()
            print("✅ Survey questions initialized successfully")
    
    finally:
        db.close()

# 애플리케이션 생성
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown
    pass


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-based Portfolio Recommendation Platform - Investment Diagnosis API",
    lifespan=lifespan
)

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우트 포함
app.include_router(auth.router)
app.include_router(survey.router)
app.include_router(diagnosis.router)

# OAuth2 토큰 엔드포인트 (Swagger Authorize용)
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

@app.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Swagger UI 인증용 토큰 엔드포인트"""
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

# 헬스 체크 엔드포인트
@app.get("/health", tags=["Health"])
async def health():
    """
    헬스 체크
    """
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version
    }


# 루트 엔드포인트
@app.get("/", tags=["Root"])
async def root():
    """
    API 개요
    """
    return {
        "message": "Welcome to KingoPortfolio Diagnosis API",
        "version": settings.app_version,
        "docs": "/docs",
        "openapi": "/openapi.json"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )