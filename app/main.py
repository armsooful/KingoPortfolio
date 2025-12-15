from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from contextlib import asynccontextmanager
from datetime import timedelta

from app.config import settings
from app.database import get_db
from app.routes import auth, survey, diagnosis
from sqlalchemy.orm import Session


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작 및 종료"""
    print("🚀 Application started")
    yield
    print("🛑 Application stopped")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-based Portfolio Recommendation Platform",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우트
app.include_router(auth.router)
app.include_router(survey.router)
app.include_router(diagnosis.router)

# OAuth2 토큰
@app.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """토큰 엔드포인트"""
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
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version
    }


@app.get("/")
async def root():
    return {
        "message": "Welcome to KingoPortfolio API",
        "version": settings.app_version,
        "docs": "/docs"
    }