from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserLogin, Token, UserResponse
from app.auth import create_access_token
from app.crud import authenticate_user
from app.crud import create_user, get_user_by_email
from app.config import settings

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post("/signup", response_model=Token, status_code=201)
async def signup(
    user_create: UserCreate,
    db: Session = Depends(get_db)
):
    """
    회원가입
    
    - **email**: 사용자 이메일 (고유)
    - **password**: 비밀번호 (최소 8자)
    - **name**: 사용자 이름 (선택)
    """
    
    # 기존 이메일 확인
    existing_user = get_user_by_email(db, user_create.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # 비밀번호 길이 확인
    if len(user_create.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )
    
    try:
        # 사용자 생성
        user = create_user(db, user_create)
        
        # 토큰 생성
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.email},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserResponse.from_orm(user)
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=Token)
async def login(
    user_login: UserLogin,
    db: Session = Depends(get_db)
):
    """
    로그인
    
    - **email**: 사용자 이메일
    - **password**: 비밀번호
    
    Returns: JWT 토큰 및 사용자 정보
    """
    
    # 사용자 인증
    user = authenticate_user(db, user_login.email, user_login.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # 토큰 생성
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user)
    }


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(__import__("app.auth", fromlist=["get_current_user"]).get_current_user)):
    """
    현재 사용자 정보 조회
    
    **권한**: 로그인 필수
    """
    return UserResponse.from_orm(current_user)