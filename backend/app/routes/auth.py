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

    새로운 사용자 계정을 생성하고 즉시 로그인 상태로 JWT 토큰을 발급합니다.

    ### 요청 필드

    - **email** (필수): 이메일 주소 (고유값, 중복 불가)
    - **password** (필수): 비밀번호 (최소 8자, 최대 72바이트)
    - **name** (선택): 사용자 이름 (최대 50자)

    ### 주의사항

    - 비밀번호는 bcrypt로 해싱되어 저장됩니다
    - 이메일은 대소문자 구분 없이 고유해야 합니다
    - 기본 role은 'user'로 설정됩니다

    ### 예제 요청

    ```json
    {
        "email": "user@example.com",
        "password": "securePassword123!",
        "name": "홍길동"
    }
    ```

    ### 예제 응답 (201 Created)

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
    
    # 🔍 디버그 로그
    print("\n" + "="*60)
    print("📨 SIGNUP 요청 받음")
    print(f"이메일: {user_create.email}")
    print(f"이름: {user_create.name}")
    print(f"비밀번호 (표시): {user_create.password}")
    print(f"비밀번호 길이 (글자): {len(user_create.password)}")
    print(f"비밀번호 길이 (바이트): {len(user_create.password.encode('utf-8'))}")
    print(f"비밀번호 16진수: {user_create.password.encode('utf-8').hex()}")
    print("="*60 + "\n")
    
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
        
        print(f"\n✅ 회원가입 성공: {user.email}\n")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {"id": user.id, "email": user.email, "name": getattr(user, "name", None), "created_at": user.created_at}
        }
    
    except ValueError as e:
        print(f"\n❌ ValueError: {str(e)}\n")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"\n❌ Exception: {type(e).__name__}: {str(e)}\n")
        import traceback
        traceback.print_exc()
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
        "user": {"id": user.id, "email": user.email, "name": getattr(user, "name", None), "created_at": user.created_at}
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
    return {"id": current_user.id, "email": current_user.email, "name": getattr(current_user, "name", None), "created_at": current_user.created_at}

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
        print(f"⚠️  비밀번호 재설정 요청: 존재하지 않는 이메일 {forgot_request.email}")
        return {"message": "비밀번호 재설정 링크가 이메일로 전송되었습니다"}

    # 재설정 토큰 생성
    reset_token = create_reset_token(user.id)

    # 이메일 전송 (현재는 콘솔 출력)
    reset_link = f"http://localhost:3000/reset-password?token={reset_token}"
    print("\n" + "="*80)
    print("📧 비밀번호 재설정 이메일 전송 (콘솔 출력)")
    print("="*80)
    print(f"수신자: {user.email}")
    print(f"사용자 ID: {user.id}")
    print(f"재설정 링크: {reset_link}")
    print(f"유효 시간: 15분")
    print("="*80 + "\n")

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

    print(f"✅ 비밀번호 재설정 완료: {user.email}")

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
        "role": current_user.role,
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
    if request.name is None and request.email is None:
        raise KingoValidationError(
            detail="최소 하나의 필드(name 또는 email)를 제공해야 합니다"
        )

    # 이메일 변경 시 중복 확인
    if request.email and request.email != current_user.email:
        existing_user = get_user_by_email(db, request.email)
        if existing_user:
            raise DuplicateEmailError(email=request.email)
        current_user.email = request.email

    # 이름 변경
    if request.name is not None:
        current_user.name = request.name

    db.commit()
    db.refresh(current_user)

    print(f"✅ 프로필 수정 완료: {current_user.email}")

    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": getattr(current_user, "name", None),
        "role": current_user.role,
        "created_at": current_user.created_at
    }

@router.put(
    "/change-password",
    response_model=MessageResponse,
    summary="비밀번호 변경",
    description="현재 비밀번호를 확인하고 새 비밀번호로 변경합니다.",
    response_description="비밀번호 변경 완료 메시지"
)
async def change_password(
    request: ChangePasswordRequest,
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
    if not verify_password(request.current_password, current_user.hashed_password):
        raise InvalidCredentialsError(detail="현재 비밀번호가 올바르지 않습니다")

    # 새 비밀번호가 현재 비밀번호와 동일한지 확인
    if verify_password(request.new_password, current_user.hashed_password):
        raise KingoValidationError(
            detail="새 비밀번호는 현재 비밀번호와 달라야 합니다"
        )

    # 새 비밀번호 해싱
    new_hashed_password = hash_password(request.new_password)

    # 비밀번호 업데이트
    current_user.hashed_password = new_hashed_password
    db.commit()

    print(f"✅ 비밀번호 변경 완료: {current_user.email}")

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

    print(f"✅ 계정 삭제 완료: {user_email} (ID: {user_id})")

    return {"message": "계정이 성공적으로 삭제되었습니다"}
