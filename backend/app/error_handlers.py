# backend/app/error_handlers.py

"""
전역 에러 핸들러
- 모든 예외를 일관된 형식으로 처리
- 로깅 및 모니터링
"""

import logging
import traceback
from typing import Union, Dict, Any
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError

from app.exceptions import BaseKingoException, InternalServerError, DatabaseError

logger = logging.getLogger(__name__)


def create_error_response(
    status_code: int,
    error_code: str,
    detail: str,
    extra: Dict[str, Any] = None,
    include_trace: bool = False,
    trace: str = None
) -> JSONResponse:
    """에러 응답 생성"""
    error_response = {
        "error": {
            "code": error_code,
            "message": detail,
            "status": status_code
        }
    }

    if extra:
        error_response["error"]["extra"] = extra

    # 개발 환경에서만 스택 트레이스 포함
    if include_trace and trace:
        error_response["error"]["trace"] = trace

    return JSONResponse(
        status_code=status_code,
        content=error_response
    )


async def base_kingo_exception_handler(
    request: Request,
    exc: BaseKingoException
) -> JSONResponse:
    """
    커스텀 KingoPortfolio 예외 핸들러
    """
    logger.error(
        f"{exc.error_code}: {exc.detail}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            **exc.extra
        }
    )

    return create_error_response(
        status_code=exc.status_code,
        error_code=exc.error_code,
        detail=exc.detail,
        extra=exc.extra if exc.extra else None
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException
) -> JSONResponse:
    """
    일반 HTTPException 핸들러
    """
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code
        }
    )

    return create_error_response(
        status_code=exc.status_code,
        error_code=f"HTTP_{exc.status_code}",
        detail=str(exc.detail)
    )


async def validation_exception_handler(
    request: Request,
    exc: Union[RequestValidationError, ValidationError]
) -> JSONResponse:
    """
    Pydantic 검증 에러 핸들러
    """
    errors = []
    if isinstance(exc, RequestValidationError):
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })
    else:
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })

    logger.warning(
        f"Validation error: {len(errors)} errors",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": errors
        }
    )

    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="VALIDATION_ERROR",
        detail="입력 데이터 검증에 실패했습니다",
        extra={"errors": errors}
    )


async def sqlalchemy_exception_handler(
    request: Request,
    exc: SQLAlchemyError
) -> JSONResponse:
    """
    SQLAlchemy 데이터베이스 에러 핸들러
    """
    logger.error(
        f"Database error: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__
        },
        exc_info=True
    )

    # IntegrityError는 중복 키 등 제약 조건 위반
    if isinstance(exc, IntegrityError):
        detail = "데이터 무결성 제약 조건 위반입니다"
        error_code = "INTEGRITY_ERROR"
    else:
        detail = "데이터베이스 오류가 발생했습니다"
        error_code = "DATABASE_ERROR"

    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code=error_code,
        detail=detail
    )


async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    예상하지 못한 일반 예외 핸들러
    """
    trace = traceback.format_exc()

    logger.critical(
        f"Unhandled exception: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__,
            "trace": trace
        },
        exc_info=True
    )

    # 개발 환경에서만 상세 에러 메시지 반환
    import os
    is_dev = os.getenv("ENVIRONMENT", "production") == "development"

    if is_dev:
        detail = f"Internal server error: {str(exc)}"
        include_trace = True
    else:
        detail = "서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        include_trace = False

    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="INTERNAL_SERVER_ERROR",
        detail=detail,
        include_trace=include_trace,
        trace=trace if include_trace else None
    )


def setup_exception_handlers(app):
    """
    FastAPI 앱에 전역 예외 핸들러 등록

    사용법:
        from app.error_handlers import setup_exception_handlers

        app = FastAPI()
        setup_exception_handlers(app)
    """
    # 우선순위: 구체적인 예외부터 처리

    # 1. 커스텀 KingoPortfolio 예외
    app.add_exception_handler(BaseKingoException, base_kingo_exception_handler)

    # 2. Pydantic 검증 에러
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)

    # 3. SQLAlchemy 데이터베이스 에러
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)

    # 4. 일반 HTTP 예외
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # 5. 예상하지 못한 모든 예외 (최후의 보루)
    app.add_exception_handler(Exception, general_exception_handler)

    logger.info("✅ Global exception handlers registered")
