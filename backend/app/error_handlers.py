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


def _get_request_id(request: Request) -> str:
    return request.headers.get("x-request-id") or getattr(request.state, "request_id", "")


def _error_type_from_status(status_code: int) -> str:
    if 400 <= status_code < 500:
        return "USER"
    return "SYSTEM"


def _error_type_from_code(error_code: str) -> str:
    if error_code in {
        "UPSTREAM_UNAVAILABLE",
        "EXTERNAL_DEPENDENCY",
        "EXTERNAL_API_ERROR",
        "ALPHA_VANTAGE_ERROR",
        "PYKRX_ERROR",
        "CLAUDE_API_ERROR",
    }:
        return "EXTERNAL"
    return ""


def _merge_extra(extra: Dict[str, Any], request_id: str, error_type: str) -> Dict[str, Any]:
    merged = dict(extra) if extra else {}
    if request_id:
        merged["request_id"] = request_id
    if error_type:
        merged["error_type"] = error_type
    return merged


def _safe_detail(error_type: str, detail: str) -> str:
    if error_type == "EXTERNAL":
        return "외부 서비스 응답이 지연되고 있습니다. 잠시 후 다시 시도해주세요."
    if error_type == "SYSTEM":
        return "일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
    return detail


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
    request_id = _get_request_id(request)
    error_type = _error_type_from_code(exc.error_code) or _error_type_from_status(exc.status_code)
    logger.error(
        f"{exc.error_code}: {exc.detail}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "request_id": request_id,
            "error_type": error_type,
            **(exc.extra or {})
        }
    )

    return create_error_response(
        status_code=exc.status_code,
        error_code=exc.error_code,
        detail=_safe_detail(error_type, exc.detail),
        extra=_merge_extra(exc.extra, request_id, error_type)
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException
) -> JSONResponse:
    """
    일반 HTTPException 핸들러
    """
    request_id = _get_request_id(request)
    error_type = _error_type_from_status(exc.status_code)
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
            "request_id": request_id,
            "error_type": error_type,
        }
    )

    return create_error_response(
        status_code=exc.status_code,
        error_code=f"HTTP_{exc.status_code}",
        detail=_safe_detail(error_type, str(exc.detail)),
        extra=_merge_extra({}, request_id, error_type)
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

    request_id = _get_request_id(request)
    logger.warning(
        f"Validation error: {len(errors)} errors",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": errors,
            "request_id": request_id,
            "error_type": "USER",
        }
    )

    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="VALIDATION_ERROR",
        detail="입력 데이터 검증에 실패했습니다",
        extra=_merge_extra({"errors": errors}, request_id, "USER")
    )


async def sqlalchemy_exception_handler(
    request: Request,
    exc: SQLAlchemyError
) -> JSONResponse:
    """
    SQLAlchemy 데이터베이스 에러 핸들러
    """
    request_id = _get_request_id(request)
    logger.error(
        f"Database error: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_type": "SYSTEM",
            "request_id": request_id,
            "db_error_type": type(exc).__name__,
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
        detail=_safe_detail("SYSTEM", detail),
        extra=_merge_extra({}, request_id, "SYSTEM")
    )


async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    예상하지 못한 일반 예외 핸들러
    """
    trace = traceback.format_exc()

    request_id = _get_request_id(request)
    logger.critical(
        f"Unhandled exception: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_type": "SYSTEM",
            "request_id": request_id,
            "exception_type": type(exc).__name__,
            "trace": trace,
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
        detail=_safe_detail("SYSTEM", detail),
        include_trace=include_trace,
        trace=trace if include_trace else None,
        extra=_merge_extra({}, request_id, "SYSTEM")
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
