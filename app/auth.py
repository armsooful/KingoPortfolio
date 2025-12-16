from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status

from app.config import settings
from app.database import get_db

# 비밀번호 해싱 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 설정
SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes


# ============ PASSWORD HASHING ============

def hash_password(password: str) -> str:
    """비밀번호를 bcrypt로 해싱"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """평문 비밀번호와 해시된 비밀번호 비교"""
    return pwd_context.verify(plain_password, hashed_password)


# ============ JWT TOKEN ============

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """JWT 액세스 토큰 생성"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> str:
    """JWT 토큰 검증 후 이메일 반환"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise ValueError("Invalid token")
        return email
    except JWTError:
        raise ValueError("Invalid token")
    except Exception as e:
        raise ValueError(f"Token verification failed: {str(e)}")


# ============ CURRENT USER ============

async def get_current_user(
    token: str = Depends(lambda: None),
    db = Depends(get_db)
):
    """JWT 토큰으로 현재 사용자 조회"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token",
        )
    
    try:
        email = verify_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    
    from app.crud import get_user_by_email
    user = get_user_by_email(db, email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    return user