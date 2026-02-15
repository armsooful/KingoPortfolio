import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import timedelta
from app.database import get_db
from app.models import User
from app.schemas import (
    UserCreate, UserLogin, Token, UserResponse, ErrorResponse,
    ForgotPasswordRequest, ResetPasswordRequest, MessageResponse,
    UpdateProfileRequest, ChangePasswordRequest, ProfileResponse
)
from app.auth import (
    create_access_token, create_reset_token, verify_reset_token,
    hash_password, verify_password, get_current_user
)
from app.crud import authenticate_user
from app.crud import create_user, get_user_by_email
from app.config import settings
from app.exceptions import (
    UserNotFoundError, InvalidTokenError, TokenExpiredError,
    DuplicateEmailError, ValidationError as KingoValidationError,
    InvalidCredentialsError
)
from app.rate_limiter import limiter, RateLimits
from app.utils.email import send_verification_email, generate_verification_token, is_verification_token_expired
from app.utils.tier_permissions import (
    get_user_permissions, add_activity_points, update_vip_tier,
    get_membership_status, reset_monthly_usage_if_needed
)
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={
        401: {
            "model": ErrorResponse,
            "description": "인증 실패 (Unauthorized)",
        },
        422: {
            "model": ErrorResponse,
            "description": "유효성 검증 실패 (Unprocessable Entity)",
        }
    }
)

@router.post(
    "/signup",
    response_model=Token,
    status_code=201,
    summary="회원가입",
    description="새로운 사용자 계정을 생성하고 JWT 토큰을 발급합니다.",
    response_description="생성된 사용자 정보 및 JWT 토큰",
    responses={
        201: {
            "description": "회원가입 성공",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "user": {
                            "id": "usr_abc123xyz",
                            "email": "user@example.com",
                            "name": "홍길동",
                            "created_at": "2025-12-29T10:00:00Z"
                        }
                    }
                }
            }
        },
        400: {
            "description": "비밀번호가 너무 짧음 (8자 미만)",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "비밀번호는 최소 8자 이상이어야 합니다",
                            "status": 400
                        }
                    }
                }
            }
        },
        409: {
            "description": "이미 사용 중인 이메일",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "DUPLICATE_EMAIL",
                            "message": "이미 사용 중인 이메일입니다: user@example.com",
                            "status": 409,
                            "extra": {"email": "user@example.com"}
                        }
                    }
                }
            }
        }
    }
)
@limiter.limit(RateLimits.AUTH_SIGNUP)
async def signup(
    request: Request,
    user_create: UserCreate,
    db: Session = Depends(get_db)
):
    """
    ## 회원가입

    이메일과 비밀번호만으로 계정을 생성하고 즉시 JWT 토큰을 발급합니다.
    추가 프로필 정보는 가입 후 PUT /auth/profile로 업데이트합니다.

    ### 요청 필드

    - **email** (필수): 이메일 주소 (고유값, 중복 불가)
    - **password** (필수): 비밀번호 (최소 8자, 최대 72바이트)
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

        # 이메일 인증 자동 활성화 (교육용 플랫폼이므로 인증 절차 생략)
        user.is_email_verified = True
        logger.info("이메일 인증 자동 활성화: %s", user.email)

        db.commit()
        db.refresh(user)

        # 토큰 생성
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.email},
            expires_delta=access_token_expires
        )

        logger.info("회원가입 성공: %s", user.email)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": getattr(user, "name", None),
                "role": user.role,
                "created_at": user.created_at
            }
        }
    
    except ValueError as e:
        logger.warning("회원가입 ValueError: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("회원가입 실패: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post(
    "/login",
    response_model=Token,
    summary="로그인",
    description="이메일과 비밀번호로 로그인하고 JWT 토큰을 발급받습니다.",
    response_description="JWT 액세스 토큰 및 사용자 정보",
    responses={
        200: {
            "description": "로그인 성공",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "user": {
                            "id": "usr_abc123xyz",
                            "email": "user@example.com",
                            "name": "홍길동",
                            "created_at": "2025-12-29T10:00:00Z"
                        }
                    }
                }
            }
        },
        401: {
            "description": "인증 실패 (이메일 또는 비밀번호 불일치)",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "INVALID_CREDENTIALS",
                            "message": "이메일 또는 비밀번호가 올바르지 않습니다",
                            "status": 401
                        }
                    }
                }
            }
        }
    }
)
@limiter.limit(RateLimits.AUTH_LOGIN)
async def login(
    request: Request,
    user_login: UserLogin,
    db: Session = Depends(get_db)
):
    """
    ## 로그인

    등록된 이메일과 비밀번호로 인증하고 JWT 액세스 토큰을 발급받습니다.

    ### 요청 필드

    - **email** (필수): 등록된 이메일 주소
    - **password** (필수): 비밀번호

    ### 토큰 사용 방법

    발급받은 `access_token`을 다음과 같이 사용하세요:

    ```
    Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    ```

    ### 토큰 유효 기간

    - 기본 유효 기간: 30분
    - 만료 시 재로그인 필요

    ### 예제 요청

    ```json
    {
        "email": "user@example.com",
        "password": "securePassword123!"
    }
    ```

    ### 예제 응답 (200 OK)

    ```json
    {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer",
        "user": {
            "id": "usr_abc123xyz",
            "email": "user@example.com",
            "name": "홍길동",
            "created_at": "2025-12-29T10:00:00Z"
        }
    }
    ```
    """
    
    # 사용자 인증
    user = authenticate_user(db, user_login.email, user_login.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인 정보가 올바르지 않습니다.\n이메일과 비밀번호를 다시 확인해 주세요."
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
        "user": {
            "id": user.id,
            "email": user.email,
            "name": getattr(user, "name", None),
            "role": user.role,
            "created_at": user.created_at
        }
    }

@router.get(
    "/me",
    response_model=UserResponse,
    summary="현재 사용자 정보 조회",
    description="JWT 토큰으로 인증된 현재 사용자의 정보를 조회합니다.",
    response_description="현재 사용자 정보",
    responses={
        200: {
            "description": "사용자 정보 조회 성공",
            "content": {
                "application/json": {
                    "example": {
                        "id": "usr_abc123xyz",
                        "email": "user@example.com",
                        "name": "홍길동",
                        "created_at": "2025-12-29T10:00:00Z"
                    }
                }
            }
        },
        401: {
            "description": "인증 실패 (토큰 없음, 유효하지 않음, 또는 만료됨)",
            "content": {
                "application/json": {
                    "examples": {
                        "token_expired": {
                            "summary": "토큰 만료",
                            "value": {
                                "error": {
                                    "code": "TOKEN_EXPIRED",
                                    "message": "토큰이 만료되었습니다",
                                    "status": 401
                                }
                            }
                        },
                        "invalid_token": {
                            "summary": "유효하지 않은 토큰",
                            "value": {
                                "error": {
                                    "code": "INVALID_TOKEN",
                                    "message": "유효하지 않은 토큰입니다",
                                    "status": 401
                                }
                            }
                        }
                    }
                }
            }
        }
    }
)
async def get_me(current_user: User = Depends(__import__("app.auth", fromlist=["get_current_user"]).get_current_user)):
    """
    ## 현재 사용자 정보 조회

    JWT 토큰으로 인증된 현재 사용자의 프로필 정보를 조회합니다.

    ### 권한

    - **인증 필수**: 유효한 JWT 토큰 필요
    - 모든 로그인한 사용자 접근 가능

    ### 헤더

    ```
    Authorization: Bearer {access_token}
    ```

    ### 예제 응답 (200 OK)

    ```json
    {
        "id": "usr_abc123xyz",
        "email": "user@example.com",
        "name": "홍길동",
        "created_at": "2025-12-29T10:00:00Z"
    }
    ```

    ### 활용 사례

    - 사용자 프로필 페이지 표시
    - 네비게이션 바에 사용자 이름 표시
    - 현재 로그인 상태 확인
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": getattr(current_user, "name", None),
        "role": current_user.role,
        "created_at": current_user.created_at,
        "vip_tier": getattr(current_user, "vip_tier", "bronze"),
        "membership_plan": getattr(current_user, "membership_plan", "free"),
        "activity_points": getattr(current_user, "activity_points", 0),
    }

@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=200,
    summary="비밀번호 재설정 요청",
    description="등록된 이메일로 비밀번호 재설정 링크를 전송합니다.",
    response_description="재설정 링크 전송 완료 메시지",
    responses={
        200: {
            "description": "재설정 링크 전송 성공",
            "content": {
                "application/json": {
                    "example": {
                        "message": "비밀번호 재설정 링크가 이메일로 전송되었습니다"
                    }
                }
            }
        },
        404: {
            "description": "존재하지 않는 이메일",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "USER_NOT_FOUND",
                            "message": "해당 이메일로 등록된 사용자를 찾을 수 없습니다",
                            "status": 404
                        }
                    }
                }
            }
        }
    }
)
@limiter.limit(RateLimits.AUTH_PASSWORD_RESET)
async def forgot_password(
    request: Request,
    forgot_request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    ## 비밀번호 재설정 요청

    등록된 이메일 주소로 비밀번호 재설정 링크를 전송합니다.

    ### 요청 필드

    - **email** (필수): 등록된 이메일 주소

    ### 프로세스

    1. 이메일로 사용자 조회
    2. 15분 유효 재설정 토큰 생성
    3. 이메일로 재설정 링크 전송 (현재는 콘솔 출력)

    ### 보안

    - 존재하지 않는 이메일도 성공 응답 (보안상 이유로 사용자 존재 여부 노출 방지)
    - 토큰은 15분 후 자동 만료
    - 토큰은 일회용 (사용 후 비밀번호 변경 시 무효화)

    ### 예제 요청

    ```json
    {
        "email": "user@example.com"
    }
    ```

    ### 예제 응답 (200 OK)

    ```json
    {
        "message": "비밀번호 재설정 링크가 이메일로 전송되었습니다"
    }
    ```
    """

    # 사용자 조회
    user = get_user_by_email(db, forgot_request.email)

    if not user:
        # 보안상 존재하지 않는 이메일도 성공 응답 (사용자 존재 여부 노출 방지)
        logger.info("비밀번호 재설정 요청: 존재하지 않는 이메일 %s", forgot_request.email)
        return {"message": "비밀번호 재설정 링크가 이메일로 전송되었습니다"}

    # 재설정 토큰 생성
    reset_token = create_reset_token(user.id)

    # 이메일 전송 (현재는 로그 출력)
    reset_link = f"http://localhost:3000/reset-password?token={reset_token}"
    logger.info("비밀번호 재설정 이메일 — 수신자: %s, ID: %s, 유효: 15분", user.email, user.id)

    return {"message": "비밀번호 재설정 링크가 이메일로 전송되었습니다"}

@router.post(
    "/reset-password",
    response_model=MessageResponse,
    status_code=200,
    summary="비밀번호 재설정",
    description="재설정 토큰을 사용하여 새로운 비밀번호로 변경합니다.",
    response_description="비밀번호 변경 완료 메시지",
    responses={
        200: {
            "description": "비밀번호 변경 성공",
            "content": {
                "application/json": {
                    "example": {
                        "message": "비밀번호가 성공적으로 변경되었습니다"
                    }
                }
            }
        },
        401: {
            "description": "토큰 오류 (유효하지 않음, 만료됨, 또는 잘못된 타입)",
            "content": {
                "application/json": {
                    "examples": {
                        "token_expired": {
                            "summary": "토큰 만료",
                            "value": {
                                "error": {
                                    "code": "TOKEN_EXPIRED",
                                    "message": "재설정 링크가 만료되었습니다",
                                    "status": 401
                                }
                            }
                        },
                        "invalid_token": {
                            "summary": "유효하지 않은 토큰",
                            "value": {
                                "error": {
                                    "code": "INVALID_TOKEN",
                                    "message": "유효하지 않은 토큰입니다",
                                    "status": 401
                                }
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "사용자를 찾을 수 없음",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "USER_NOT_FOUND",
                            "message": "사용자를 찾을 수 없습니다",
                            "status": 404
                        }
                    }
                }
            }
        },
        422: {
            "description": "비밀번호 유효성 검증 실패",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "비밀번호는 최소 8자 이상이어야 합니다",
                            "status": 422
                        }
                    }
                }
            }
        }
    }
)
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    ## 비밀번호 재설정

    재설정 토큰을 사용하여 새로운 비밀번호로 변경합니다.

    ### 요청 필드

    - **token** (필수): 이메일로 전송된 재설정 토큰
    - **new_password** (필수): 새 비밀번호 (최소 8자, 최대 72바이트)

    ### 프로세스

    1. 재설정 토큰 검증 (유효성, 만료 여부, 타입 확인)
    2. 토큰에서 사용자 ID 추출
    3. 사용자 조회
    4. 새 비밀번호 해싱 및 저장

    ### 주의사항

    - 토큰은 15분 후 만료됩니다
    - 토큰은 일회용입니다 (비밀번호 변경 후 이전 토큰은 무효화됨)
    - 비밀번호는 bcrypt로 안전하게 해싱됩니다

    ### 예제 요청

    ```json
    {
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "new_password": "newSecurePassword123!"
    }
    ```

    ### 예제 응답 (200 OK)

    ```json
    {
        "message": "비밀번호가 성공적으로 변경되었습니다"
    }
    ```
    """

    # 토큰 검증 (TokenExpiredError, InvalidTokenError 발생 가능)
    user_id = verify_reset_token(request.token)

    # 사용자 조회
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise UserNotFoundError(user_id=user_id)

    # 새 비밀번호 해싱 (ValidationError 발생 가능)
    new_hashed_password = hash_password(request.new_password)

    # 비밀번호 업데이트
    user.hashed_password = new_hashed_password
    db.commit()

    logger.info("비밀번호 재설정 완료: %s", user.email)

    return {"message": "비밀번호가 성공적으로 변경되었습니다"}

@router.get(
    "/profile",
    response_model=ProfileResponse,
    summary="프로필 조회",
    description="현재 로그인한 사용자의 상세 프로필 정보를 조회합니다.",
    response_description="사용자 프로필 정보"
)
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    """
    ## 프로필 조회

    현재 로그인한 사용자의 상세 프로필 정보를 조회합니다.

    ### 권한

    - **인증 필수**: 유효한 JWT 토큰 필요

    ### 응답 필드

    - **id**: 사용자 고유 ID
    - **email**: 이메일 주소
    - **name**: 사용자 이름
    - **role**: 사용자 역할 (user/premium/admin)
    - **created_at**: 계정 생성 일시

    ### 예제 응답 (200 OK)

    ```json
    {
        "id": "usr_abc123xyz",
        "email": "user@example.com",
        "name": "홍길동",
        "role": "user",
        "created_at": "2025-12-29T10:00:00Z"
    }
    ```
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": getattr(current_user, "name", None),
        "phone": getattr(current_user, "phone", None),
        "birth_date": getattr(current_user, "birth_date", None),
        "age_group": getattr(current_user, "age_group", None),
        "occupation": getattr(current_user, "occupation", None),
        "company": getattr(current_user, "company", None),
        "annual_income": getattr(current_user, "annual_income", None),
        "total_assets": getattr(current_user, "total_assets", None),
        "city": getattr(current_user, "city", None),
        "district": getattr(current_user, "district", None),
        "investment_experience": getattr(current_user, "investment_experience", None),
        "investment_goal": getattr(current_user, "investment_goal", None),
        "risk_tolerance": getattr(current_user, "risk_tolerance", None),
        "role": current_user.role,
        "is_email_verified": getattr(current_user, "is_email_verified", False),
        "vip_tier": getattr(current_user, "vip_tier", "bronze"),
        "activity_points": getattr(current_user, "activity_points", 0),
        "membership_plan": getattr(current_user, "membership_plan", "free"),
        "created_at": current_user.created_at
    }

@router.put(
    "/profile",
    response_model=ProfileResponse,
    summary="프로필 수정",
    description="현재 로그인한 사용자의 프로필 정보를 수정합니다.",
    response_description="수정된 프로필 정보"
)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ## 프로필 수정

    현재 로그인한 사용자의 프로필 정보를 수정합니다.

    ### 권한

    - **인증 필수**: 유효한 JWT 토큰 필요

    ### 요청 필드 (모두 선택사항)

    - **name**: 사용자 이름 (최대 50자)
    - **email**: 이메일 주소 (고유값, 중복 불가)

    ### 주의사항

    - 이메일을 변경하는 경우 중복 확인이 수행됩니다
    - 최소 하나의 필드는 제공되어야 합니다

    ### 예제 요청

    ```json
    {
        "name": "김철수",
        "email": "newemail@example.com"
    }
    ```

    ### 예제 응답 (200 OK)

    ```json
    {
        "id": "usr_abc123xyz",
        "email": "newemail@example.com",
        "name": "김철수",
        "role": "user",
        "created_at": "2025-12-29T10:00:00Z"
    }
    ```
    """
    # 최소 하나의 필드는 제공되어야 함
    if not any(v is not None for v in request.dict(exclude_unset=True).values()):
        raise KingoValidationError(
            detail="최소 하나의 필드를 제공해야 합니다"
        )

    # 이메일 변경 시 중복 확인
    if request.email and request.email != current_user.email:
        existing_user = get_user_by_email(db, request.email)
        if existing_user:
            raise DuplicateEmailError(email=request.email)
        current_user.email = request.email

    # 모든 프로필 필드 업데이트
    updatable_fields = [
        "name", "phone", "birth_date", "age_group", "occupation", "company",
        "annual_income", "total_assets", "city", "district",
        "investment_experience", "investment_goal", "risk_tolerance",
    ]
    for field in updatable_fields:
        value = getattr(request, field, None)
        if value is not None:
            setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)

    return ProfileResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        phone=current_user.phone,
        birth_date=current_user.birth_date,
        age_group=getattr(current_user, 'age_group', None),
        occupation=current_user.occupation,
        company=current_user.company,
        annual_income=current_user.annual_income,
        total_assets=current_user.total_assets,
        city=current_user.city,
        district=current_user.district,
        investment_experience=current_user.investment_experience,
        investment_goal=current_user.investment_goal,
        risk_tolerance=current_user.risk_tolerance,
        role=current_user.role,
        is_email_verified=getattr(current_user, 'is_email_verified', False),
        vip_tier=getattr(current_user, 'vip_tier', 'bronze'),
        activity_points=getattr(current_user, 'activity_points', 0),
        membership_plan=getattr(current_user, 'membership_plan', 'free'),
        created_at=current_user.created_at
    )

@router.put(
    "/change-password",
    response_model=MessageResponse,
    summary="비밀번호 변경",
    description="현재 비밀번호를 확인하고 새 비밀번호로 변경합니다.",
    response_description="비밀번호 변경 완료 메시지"
)
@limiter.limit(RateLimits.AUTH_PASSWORD_RESET)
async def change_password(
    request: Request,
    password_request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ## 비밀번호 변경

    현재 비밀번호를 확인하고 새 비밀번호로 변경합니다.

    ### 권한

    - **인증 필수**: 유효한 JWT 토큰 필요

    ### 요청 필드

    - **current_password** (필수): 현재 비밀번호
    - **new_password** (필수): 새 비밀번호 (최소 8자, 최대 72바이트)

    ### 프로세스

    1. 현재 비밀번호 확인
    2. 새 비밀번호 유효성 검증
    3. 비밀번호 해싱 및 저장

    ### 주의사항

    - 현재 비밀번호가 일치하지 않으면 실패합니다
    - 새 비밀번호는 현재 비밀번호와 달라야 합니다
    - 비밀번호는 bcrypt로 안전하게 해싱됩니다

    ### 예제 요청

    ```json
    {
        "current_password": "currentPassword123!",
        "new_password": "newPassword456!"
    }
    ```

    ### 예제 응답 (200 OK)

    ```json
    {
        "message": "비밀번호가 성공적으로 변경되었습니다"
    }
    ```
    """
    # 현재 비밀번호 확인
    if not verify_password(password_request.current_password, current_user.hashed_password):
        raise InvalidCredentialsError(detail="현재 비밀번호가 올바르지 않습니다")

    # 새 비밀번호가 현재 비밀번호와 동일한지 확인
    if verify_password(password_request.new_password, current_user.hashed_password):
        raise KingoValidationError(
            detail="새 비밀번호는 현재 비밀번호와 달라야 합니다"
        )

    # 새 비밀번호 해싱
    new_hashed_password = hash_password(password_request.new_password)

    # 비밀번호 업데이트
    current_user.hashed_password = new_hashed_password
    db.commit()

    logger.info("비밀번호 변경 완료: %s", current_user.email)

    return {"message": "비밀번호가 성공적으로 변경되었습니다"}

@router.delete(
    "/account",
    response_model=MessageResponse,
    summary="계정 삭제",
    description="현재 로그인한 사용자의 계정을 삭제합니다.",
    response_description="계정 삭제 완료 메시지"
)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ## 계정 삭제

    현재 로그인한 사용자의 계정을 영구적으로 삭제합니다.

    ### 권한

    - **인증 필수**: 유효한 JWT 토큰 필요

    ### 주의사항

    - **이 작업은 되돌릴 수 없습니다**
    - 계정과 관련된 모든 데이터가 삭제됩니다
    - 삭제 후 즉시 로그아웃됩니다

    ### 예제 응답 (200 OK)

    ```json
    {
        "message": "계정이 성공적으로 삭제되었습니다"
    }
    ```

    ### 삭제되는 데이터

    - 사용자 프로필 정보
    - 투자 성향 진단 이력
    - 기타 관련 데이터
    """
    user_email = current_user.email
    user_id = current_user.id

    # 사용자 삭제
    db.delete(current_user)
    db.commit()

    logger.info("계정 삭제 완료: %s (ID: %s)", user_email, user_id)

    return {"message": "계정이 성공적으로 삭제되었습니다"}


# ============================================================
# Profile Endpoints
# ============================================================

@router.get(
    "/profile",
    response_model=ProfileResponse,
    summary="프로필 조회",
    description="현재 로그인한 사용자의 프로필 정보를 조회합니다."
)
@limiter.limit(RateLimits.PROFILE_READ)
async def get_profile(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    ## 프로필 조회

    현재 로그인한 사용자의 전체 프로필 정보를 조회합니다.

    ### 포함되는 정보

    - 기본 정보: 이름, 이메일, 전화번호, 생년월일
    - 직업 정보: 직업, 회사명, 연봉, 총 자산
    - 주소 정보: 거주 도시, 구/군
    - 투자 성향: 투자 경험, 투자 목표, 위험 감수 성향
    - 시스템 정보: 사용자 ID, 역할, 가입일

    ### 인증 필수

    이 엔드포인트는 JWT 토큰 인증이 필요합니다.
    """
    return ProfileResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        phone=current_user.phone,
        birth_date=current_user.birth_date,
        age_group=getattr(current_user, 'age_group', None),
        occupation=current_user.occupation,
        company=current_user.company,
        annual_income=current_user.annual_income,
        total_assets=current_user.total_assets,
        city=current_user.city,
        district=current_user.district,
        investment_experience=current_user.investment_experience,
        investment_goal=current_user.investment_goal,
        risk_tolerance=current_user.risk_tolerance,
        role=current_user.role,
        is_email_verified=getattr(current_user, 'is_email_verified', False),
        vip_tier=getattr(current_user, 'vip_tier', 'bronze'),
        activity_points=getattr(current_user, 'activity_points', 0),
        membership_plan=getattr(current_user, 'membership_plan', 'free'),
        created_at=current_user.created_at
    )


@router.put(
    "/profile",
    response_model=ProfileResponse,
    summary="프로필 수정",
    description="현재 로그인한 사용자의 프로필 정보를 수정합니다."
)
@limiter.limit(RateLimits.PROFILE_UPDATE)
async def update_profile(
    request: Request,
    profile_data: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ## 프로필 수정

    현재 로그인한 사용자의 프로필 정보를 수정합니다.

    ### 수정 가능한 필드

    - 기본 정보: name, phone, birth_date
    - 직업 정보: occupation, company, annual_income, total_assets
    - 주소 정보: city, district
    - 투자 성향: investment_experience, investment_goal, risk_tolerance

    ### 주의사항

    - 모든 필드는 선택사항입니다 (제공된 필드만 업데이트됨)
    - 이메일 변경은 현재 지원되지 않습니다
    - null 값을 전송하면 해당 필드가 삭제됩니다

    ### 예제 요청

    ```json
    {
        "name": "김철수",
        "phone": "010-1234-5678",
        "occupation": "소프트웨어 엔지니어",
        "company": "테크컴퍼니",
        "annual_income": 5000,
        "total_assets": 10000,
        "city": "서울",
        "district": "강남구",
        "investment_experience": "중급",
        "investment_goal": "노후 준비",
        "risk_tolerance": "중립적"
    }
    ```
    """
    # 제공된 필드만 업데이트
    update_data = profile_data.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)

    logger.info("프로필 업데이트 완료: %s", current_user.email)

    return ProfileResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        phone=current_user.phone,
        birth_date=current_user.birth_date,
        age_group=getattr(current_user, 'age_group', None),
        occupation=current_user.occupation,
        company=current_user.company,
        annual_income=current_user.annual_income,
        total_assets=current_user.total_assets,
        city=current_user.city,
        district=current_user.district,
        investment_experience=current_user.investment_experience,
        investment_goal=current_user.investment_goal,
        risk_tolerance=current_user.risk_tolerance,
        role=current_user.role,
        is_email_verified=getattr(current_user, 'is_email_verified', False),
        vip_tier=getattr(current_user, 'vip_tier', 'bronze'),
        activity_points=getattr(current_user, 'activity_points', 0),
        membership_plan=getattr(current_user, 'membership_plan', 'free'),
        created_at=current_user.created_at
    )


# ============================================================
# 프로필 완성도 확인
# ============================================================

@router.get(
    "/profile/completion-status",
    summary="프로필 완성도 조회",
    description="사용자 프로필의 완성 여부와 미입력 항목을 반환합니다."
)
async def get_profile_completion_status(
    current_user: User = Depends(get_current_user),
):
    """포트폴리오 맞춤 서비스에 필요한 프로필 필드 완성 상태를 반환합니다."""
    required_fields = {
        "name": "이름",
        "age_group": "연령대",
        "investment_experience": "투자 경험",
        "risk_tolerance": "위험 성향",
    }

    missing = []
    filled = 0
    for field, label in required_fields.items():
        value = getattr(current_user, field, None)
        if value is None or value == "":
            missing.append({"field": field, "label": label})
        else:
            filled += 1

    total = len(required_fields)
    return {
        "is_complete": filled == total,
        "completion_percent": round(filled / total * 100),
        "filled_count": filled,
        "total_count": total,
        "missing_fields": missing,
    }


# ============================================================
# 이메일 인증 엔드포인트
# ============================================================

@router.post(
    "/send-verification-email",
    response_model=MessageResponse,
    summary="인증 이메일 발송",
    description="사용자의 이메일 주소로 인증 메일을 발송합니다."
)
@limiter.limit("3/hour")  # 시간당 3회로 제한
async def send_verification_email_endpoint(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ## 이메일 인증 메일 발송

    로그인한 사용자의 이메일 주소로 인증 메일을 발송합니다.

    ### 주의사항
    - 이미 인증된 이메일의 경우 재발송이 불가능합니다
    - 인증 링크는 24시간 동안 유효합니다
    - 시간당 3회로 발송이 제한됩니다

    ### 예제 응답 (200 OK)
    ```json
    {
        "message": "인증 이메일이 발송되었습니다. 이메일을 확인해주세요."
    }
    ```
    """
    # 이미 인증된 경우
    if current_user.is_email_verified:
        raise HTTPException(
            status_code=400,
            detail="이미 인증된 이메일입니다."
        )

    # 인증 토큰 생성
    verification_token = generate_verification_token()

    # DB에 토큰 저장
    current_user.email_verification_token = verification_token
    current_user.email_verification_sent_at = datetime.utcnow()
    db.commit()

    # 이메일 발송
    success = await send_verification_email(
        to_email=current_user.email,
        verification_token=verification_token
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail="이메일 발송에 실패했습니다. 잠시 후 다시 시도해주세요."
        )

    logger.info("인증 이메일 발송 완료: %s", current_user.email)

    return MessageResponse(
        message="인증 이메일이 발송되었습니다. 이메일을 확인해주세요."
    )


@router.get(
    "/verify-email",
    response_model=MessageResponse,
    summary="이메일 인증 확인",
    description="이메일 인증 토큰을 확인하고 이메일을 인증 처리합니다."
)
async def verify_email(
    token: str,
    db: Session = Depends(get_db)
):
    """
    ## 이메일 인증 확인

    이메일로 발송된 인증 링크를 클릭했을 때 호출되는 엔드포인트입니다.

    ### 파라미터
    - **token**: 이메일 인증 토큰 (URL 쿼리 파라미터)

    ### 주의사항
    - 토큰은 24시간 동안 유효합니다
    - 이미 인증된 이메일의 토큰은 사용할 수 없습니다

    ### 예제 요청
    ```
    GET /auth/verify-email?token=abc123xyz456
    ```

    ### 예제 응답 (200 OK)
    ```json
    {
        "message": "이메일 인증이 완료되었습니다."
    }
    ```
    """
    # 토큰으로 사용자 찾기
    user = db.query(User).filter(
        User.email_verification_token == token
    ).first()

    if not user:
        raise HTTPException(
            status_code=400,
            detail="유효하지 않은 인증 토큰입니다."
        )

    # 이미 인증된 경우
    if user.is_email_verified:
        raise HTTPException(
            status_code=400,
            detail="이미 인증된 이메일입니다."
        )

    # 토큰 만료 확인
    if is_verification_token_expired(user.email_verification_sent_at):
        raise HTTPException(
            status_code=400,
            detail="인증 링크가 만료되었습니다. 새로운 인증 이메일을 요청해주세요."
        )

    # 이메일 인증 처리
    user.is_email_verified = True
    user.email_verification_token = None  # 토큰 삭제
    db.commit()

    logger.info("이메일 인증 완료: %s", user.email)

    return MessageResponse(
        message="이메일 인증이 완료되었습니다."
    )


@router.post(
    "/resend-verification-email",
    response_model=MessageResponse,
    summary="인증 이메일 재발송",
    description="이메일 인증 메일을 재발송합니다."
)
@limiter.limit("3/hour")  # 시간당 3회로 제한
async def resend_verification_email(
    request: Request,
    email: str,
    db: Session = Depends(get_db)
):
    """
    ## 인증 이메일 재발송

    이메일 주소로 인증 메일을 재발송합니다. 로그인하지 않은 상태에서도 사용 가능합니다.

    ### 파라미터
    - **email**: 이메일 주소

    ### 주의사항
    - 이미 인증된 이메일의 경우 재발송이 불가능합니다
    - 인증 링크는 24시간 동안 유효합니다
    - 시간당 3회로 발송이 제한됩니다

    ### 예제 요청
    ```json
    {
        "email": "user@example.com"
    }
    ```

    ### 예제 응답 (200 OK)
    ```json
    {
        "message": "인증 이메일이 발송되었습니다. 이메일을 확인해주세요."
    }
    ```
    """
    # 사용자 찾기
    user = db.query(User).filter(User.email == email).first()

    if not user:
        # 보안상 사용자가 존재하지 않아도 성공 메시지 반환
        return MessageResponse(
            message="인증 이메일이 발송되었습니다. 이메일을 확인해주세요."
        )

    # 이미 인증된 경우
    if user.is_email_verified:
        raise HTTPException(
            status_code=400,
            detail="이미 인증된 이메일입니다."
        )

    # 인증 토큰 생성
    verification_token = generate_verification_token()

    # DB에 토큰 저장
    user.email_verification_token = verification_token
    user.email_verification_sent_at = datetime.utcnow()
    db.commit()

    # 이메일 발송
    success = await send_verification_email(
        to_email=user.email,
        verification_token=verification_token
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail="이메일 발송에 실패했습니다. 잠시 후 다시 시도해주세요."
        )

    logger.info("인증 이메일 재발송 완료: %s", user.email)

    return MessageResponse(
        message="인증 이메일이 발송되었습니다. 이메일을 확인해주세요."
    )


# ============================================================
# 등급 및 권한 관리 엔드포인트
# ============================================================

@router.get(
    "/tier/permissions",
    summary="사용자 권한 조회",
    description="현재 로그인한 사용자의 VIP 등급 및 멤버십 플랜에 따른 권한을 조회합니다."
)
async def get_permissions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ## 사용자 권한 조회

    현재 사용자의 VIP 등급, 멤버십 플랜, 그리고 이에 따른 모든 권한 정보를 반환합니다.

    ### 응답 정보
    - VIP 등급 권한 (포트폴리오 개수, 과거 데이터 조회 범위 등)
    - 멤버십 플랜 권한 (AI 요청, 리포트 생성, 고급 기능 등)
    - 현재 사용량 (이번 달 AI 요청 횟수, 리포트 생성 횟수)
    """
    # 월별 사용량 리셋 체크
    reset_monthly_usage_if_needed(current_user)
    db.commit()

    permissions = get_user_permissions(current_user)
    membership_status = get_membership_status(current_user)

    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "vip_tier": current_user.vip_tier,
        "activity_points": current_user.activity_points,
        "membership_plan": current_user.membership_plan,
        "membership_status": membership_status,
        "permissions": permissions['combined_permissions'],
        "vip_details": permissions['vip_permissions'],
        "membership_details": permissions['membership_permissions'],
    }


@router.get(
    "/tier/status",
    summary="등급 상태 조회",
    description="현재 로그인한 사용자의 등급 상태 및 다음 등급까지의 진행 상황을 조회합니다."
)
async def get_tier_status(
    current_user: User = Depends(get_current_user)
):
    """
    ## 등급 상태 조회

    사용자의 현재 VIP 등급, 활동 점수, 다음 등급까지 필요한 점수 등을 반환합니다.
    """
    from app.utils.tier_permissions import VIP_TIER_THRESHOLDS

    current_tier = current_user.vip_tier
    activity_points = current_user.activity_points
    total_assets = current_user.total_assets or 0

    # 다음 등급 계산
    tier_order = ['bronze', 'silver', 'gold', 'platinum', 'diamond']
    current_index = tier_order.index(current_tier)

    next_tier_info = None
    if current_index < len(tier_order) - 1:
        next_tier = tier_order[current_index + 1]
        threshold = VIP_TIER_THRESHOLDS[next_tier]

        next_tier_info = {
            "tier": next_tier,
            "required_activity_points": threshold['activity_points'],
            "remaining_activity_points": max(0, threshold['activity_points'] - activity_points),
            "required_total_assets_만원": threshold['total_assets_만원'],
            "remaining_total_assets_만원": max(0, threshold['total_assets_만원'] - total_assets),
            "progress_percentage": min(100, int((activity_points / threshold['activity_points']) * 100))
        }

    return {
        "current_tier": current_tier,
        "activity_points": activity_points,
        "total_assets_만원": total_assets,
        "next_tier": next_tier_info,
        "membership_plan": current_user.membership_plan,
        "membership_active": get_membership_status(current_user)['is_active']
    }


@router.post(
    "/tier/test-upgrade",
    summary="[테스트] VIP 등급 업그레이드 테스트",
    description="활동 점수를 추가하여 VIP 등급을 업그레이드합니다. (테스트/데모용)"
)
async def test_tier_upgrade(
    points: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ## VIP 등급 업그레이드 테스트

    **주의**: 이 엔드포인트는 테스트/데모용입니다.
    실제 프로덕션 환경에서는 제거하거나 admin 권한으로 제한해야 합니다.

    활동 점수를 추가하여 VIP 등급 업그레이드를 테스트합니다.
    """
    old_tier = current_user.vip_tier
    old_points = current_user.activity_points

    # 활동 점수 추가
    new_points = add_activity_points(current_user, points, "테스트 활동")

    db.commit()
    db.refresh(current_user)

    return {
        "message": "활동 점수가 추가되었습니다.",
        "old_tier": old_tier,
        "new_tier": current_user.vip_tier,
        "tier_changed": old_tier != current_user.vip_tier,
        "old_points": old_points,
        "new_points": new_points,
        "points_added": points
    }
