from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import TokenData
from app.exceptions import (
    InvalidTokenError,
    TokenExpiredError,
    AdminOnlyError,
    PremiumOnlyError,
    ValidationError as KingoValidationError
)
from app.services.admin_rbac_service import AdminRBACService

import logging
logger = logging.getLogger(__name__)

# 비밀번호 암호화 컨텍스트
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 스키마
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """비밀번호 해시 (bcrypt 72바이트 제한)"""
    byte_len = len(password.encode('utf-8'))
    logger.debug("hash_password 호출: 글자수=%d, 바이트=%d", len(password), byte_len)

    if byte_len > 72:
        logger.warning("비밀번호 72바이트 초과: %d bytes", byte_len)
        raise KingoValidationError(
            detail="비밀번호는 72바이트를 초과할 수 없습니다",
            extra={"max_bytes": 72, "current_bytes": byte_len}
        )

    result = pwd_context.hash(password)
    logger.debug("비밀번호 해싱 완료")
    return result

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """JWT 액세스 토큰 생성"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )

    return encoded_jwt


def create_unsubscribe_token(user_id: str) -> str:
    """이메일 구독 해제 토큰 생성 (30일 유효)"""
    expire = datetime.utcnow() + timedelta(days=30)
    to_encode = {
        "sub": user_id,
        "type": "unsubscribe",
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def verify_unsubscribe_token(token: str) -> Optional[str]:
    """구독 해제 토큰 검증. 유효하면 user_id 반환, 아니면 None."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "unsubscribe":
            return None
        return payload.get("sub")
    except JWTError:
        return None


def create_reset_token(user_id: str) -> str:
    """비밀번호 재설정 토큰 생성

    Args:
        user_id: 사용자 ID

    Returns:
        비밀번호 재설정 토큰 (15분 유효)
    """
    expire = datetime.utcnow() + timedelta(minutes=15)  # 15분 유효
    to_encode = {
        "sub": user_id,
        "type": "reset",  # 토큰 타입 명시
        "exp": expire
    }

    reset_token = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )

    return reset_token


def verify_reset_token(token: str) -> Optional[str]:
    """비밀번호 재설정 토큰 검증

    Args:
        token: 재설정 토큰

    Returns:
        사용자 ID (토큰이 유효한 경우) 또는 None

    Raises:
        TokenExpiredError: 토큰이 만료된 경우
        InvalidTokenError: 토큰이 유효하지 않은 경우
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )

        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")

        # 토큰 타입 확인
        if token_type != "reset":
            raise InvalidTokenError(detail="잘못된 토큰 타입입니다")

        if user_id is None:
            raise InvalidTokenError(detail="토큰에 사용자 정보가 없습니다")

        return user_id

    except JWTError as e:
        error_str = str(e).lower()
        if "expired" in error_str:
            raise TokenExpiredError(detail="재설정 링크가 만료되었습니다")
        else:
            raise InvalidTokenError(detail=f"토큰 검증 실패: {str(e)}")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """현재 사용자 조회 (토큰 검증)"""

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        email: str = payload.get("sub")

        if email is None:
            raise InvalidTokenError(detail="토큰에 사용자 정보가 없습니다")

        token_data = TokenData(email=email)

    except JWTError as e:
        # JWT 에러 종류에 따라 다른 예외 발생
        error_str = str(e).lower()
        if "expired" in error_str:
            raise TokenExpiredError()
        else:
            raise InvalidTokenError(detail=f"토큰 검증 실패: {str(e)}")

    user = db.query(User).filter(User.email == token_data.email).first()

    if user is None:
        raise InvalidTokenError(detail="존재하지 않는 사용자입니다")

    # is_admin이 True면 role을 admin으로 자동 마이그레이션 (하위 호환성)
    if user.is_admin and user.role != 'admin':
        user.role = 'admin'
        db.commit()

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """현재 활성 사용자 조회"""
    # 추후 is_active 필드 추가 시 활용
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """관리자 권한 필수

    Raises:
        HTTPException: 관리자가 아닌 경우 403 Forbidden

    Returns:
        User: 관리자 사용자
    """
    # is_admin 또는 role='admin'인 경우 모두 허용 (하위 호환성)
    if not current_user.is_admin and current_user.role != 'admin':
        raise AdminOnlyError()
    return current_user


async def require_premium(
    current_user: User = Depends(get_current_user)
) -> User:
    """프리미엄 회원 이상 권한 필수

    Raises:
        PremiumOnlyError: 프리미엄 회원이 아닌 경우

    Returns:
        User: 프리미엄 또는 관리자 사용자
    """
    if current_user.role not in ['premium', 'admin']:
        raise PremiumOnlyError()
    return current_user


def require_admin_permission(permission_key: str):
    """관리자 권한 키 기반 접근 제어"""

    async def _require_permission(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        rbac_service = AdminRBACService(db)
        if not rbac_service.has_permission(current_user.id, permission_key):
            raise AdminOnlyError()
        return current_user

    return _require_permission
