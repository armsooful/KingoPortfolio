# backend/app/exceptions.py

"""
커스텀 예외 클래스 정의
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class BaseKingoException(HTTPException):
    """KingoPortfolio 기본 예외 클래스"""

    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code or self.__class__.__name__
        self.extra = extra or {}


# === 인증 및 권한 관련 예외 ===

class AuthenticationError(BaseKingoException):
    """인증 실패"""
    def __init__(self, detail: str = "인증에 실패했습니다", error_code: str = "AUTH_FAILED", **kwargs):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code=error_code,
            **kwargs
        )


class InvalidCredentialsError(AuthenticationError):
    """잘못된 인증 정보"""
    def __init__(self, detail: str = "이메일 또는 비밀번호가 올바르지 않습니다", **kwargs):
        super().__init__(detail=detail, error_code="INVALID_CREDENTIALS", **kwargs)


class TokenExpiredError(AuthenticationError):
    """토큰 만료"""
    def __init__(self, detail: str = "토큰이 만료되었습니다", **kwargs):
        super().__init__(detail=detail, error_code="TOKEN_EXPIRED", **kwargs)


class InvalidTokenError(AuthenticationError):
    """잘못된 토큰"""
    def __init__(self, detail: str = "유효하지 않은 토큰입니다", **kwargs):
        super().__init__(detail=detail, error_code="INVALID_TOKEN", **kwargs)


class PermissionDeniedError(BaseKingoException):
    """권한 부족"""
    def __init__(self, detail: str = "이 작업을 수행할 권한이 없습니다", error_code: str = "PERMISSION_DENIED", **kwargs):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code=error_code,
            **kwargs
        )


class AdminOnlyError(PermissionDeniedError):
    """관리자 전용"""
    def __init__(self, detail: str = "관리자 권한이 필요합니다", **kwargs):
        super().__init__(detail=detail, error_code="ADMIN_ONLY", **kwargs)


class PremiumOnlyError(PermissionDeniedError):
    """프리미엄 회원 전용"""
    def __init__(self, detail: str = "프리미엄 회원 전용 기능입니다", **kwargs):
        super().__init__(detail=detail, error_code="PREMIUM_ONLY", **kwargs)


# === 리소스 관련 예외 ===

class ResourceNotFoundError(BaseKingoException):
    """리소스를 찾을 수 없음"""
    def __init__(self, resource: str = "리소스", detail: Optional[str] = None, error_code: str = "RESOURCE_NOT_FOUND", **kwargs):
        detail = detail or f"{resource}를 찾을 수 없습니다"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code=error_code,
            **kwargs
        )


class StockNotFoundError(ResourceNotFoundError):
    """주식 종목을 찾을 수 없음"""
    def __init__(self, symbol: str, **kwargs):
        super().__init__(
            resource=f"주식 종목 ({symbol})",
            error_code="STOCK_NOT_FOUND",
            extra={"symbol": symbol},
            **kwargs
        )


class UserNotFoundError(ResourceNotFoundError):
    """사용자를 찾을 수 없음"""
    def __init__(self, user_id: Optional[str] = None, **kwargs):
        super().__init__(
            resource="사용자",
            error_code="USER_NOT_FOUND",
            extra={"user_id": user_id} if user_id else {},
            **kwargs
        )


class TaskNotFoundError(ResourceNotFoundError):
    """작업을 찾을 수 없음"""
    def __init__(self, task_id: str, **kwargs):
        super().__init__(
            resource=f"작업 ({task_id})",
            error_code="TASK_NOT_FOUND",
            extra={"task_id": task_id},
            **kwargs
        )


# === 데이터 검증 관련 예외 ===

class ValidationError(BaseKingoException):
    """데이터 검증 실패"""
    def __init__(self, detail: str = "입력 데이터가 올바르지 않습니다", **kwargs):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="VALIDATION_ERROR",
            **kwargs
        )


class DuplicateResourceError(BaseKingoException):
    """중복된 리소스"""
    def __init__(self, resource: str = "리소스", detail: Optional[str] = None, error_code: str = "DUPLICATE_RESOURCE", **kwargs):
        detail = detail or f"이미 존재하는 {resource}입니다"
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code=error_code,
            **kwargs
        )


class DuplicateEmailError(DuplicateResourceError):
    """중복된 이메일"""
    def __init__(self, email: str, **kwargs):
        super().__init__(
            resource="이메일",
            detail=f"이미 사용 중인 이메일입니다: {email}",
            error_code="DUPLICATE_EMAIL",
            extra={"email": email},
            **kwargs
        )


# === 외부 API 관련 예외 ===

class ExternalAPIError(BaseKingoException):
    """외부 API 호출 실패"""
    def __init__(self, service: str, detail: Optional[str] = None, error_code: str = "EXTERNAL_API_ERROR", **kwargs):
        detail = detail or f"{service} API 호출에 실패했습니다"
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_code=error_code,
            extra={"service": service},
            **kwargs
        )


class AlphaVantageAPIError(ExternalAPIError):
    """Alpha Vantage API 오류"""
    def __init__(self, detail: Optional[str] = None, **kwargs):
        super().__init__(
            service="Alpha Vantage",
            detail=detail,
            error_code="ALPHA_VANTAGE_ERROR",
            **kwargs
        )


class PykrxAPIError(ExternalAPIError):
    """pykrx API 오류"""
    def __init__(self, detail: Optional[str] = None, **kwargs):
        super().__init__(
            service="pykrx",
            detail=detail,
            error_code="PYKRX_ERROR",
            **kwargs
        )


class ClaudeAPIError(ExternalAPIError):
    """Claude API 오류"""
    def __init__(self, detail: Optional[str] = None, **kwargs):
        super().__init__(
            service="Claude",
            detail=detail,
            error_code="CLAUDE_API_ERROR",
            **kwargs
        )


# === 데이터 처리 관련 예외 ===

class DataProcessingError(BaseKingoException):
    """데이터 처리 오류"""
    def __init__(self, detail: str = "데이터 처리 중 오류가 발생했습니다", error_code: str = "DATA_PROCESSING_ERROR", **kwargs):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code=error_code,
            **kwargs
        )


class InsufficientDataError(DataProcessingError):
    """데이터 부족"""
    def __init__(self, detail: str = "분석에 필요한 데이터가 부족합니다", **kwargs):
        super().__init__(
            detail=detail,
            error_code="INSUFFICIENT_DATA",
            **kwargs
        )


class CalculationError(DataProcessingError):
    """계산 오류"""
    def __init__(self, detail: str = "계산 중 오류가 발생했습니다", **kwargs):
        super().__init__(
            detail=detail,
            error_code="CALCULATION_ERROR",
            **kwargs
        )


# === 비즈니스 로직 관련 예외 ===

class BusinessLogicError(BaseKingoException):
    """비즈니스 로직 오류"""
    def __init__(self, detail: str, **kwargs):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="BUSINESS_LOGIC_ERROR",
            **kwargs
        )


class InvalidPeriodError(BusinessLogicError):
    """잘못된 기간"""
    def __init__(self, detail: str = "유효하지 않은 기간입니다", **kwargs):
        super().__init__(
            detail=detail,
            error_code="INVALID_PERIOD",
            **kwargs
        )


class InvalidSymbolError(BusinessLogicError):
    """잘못된 종목 코드"""
    def __init__(self, symbol: str, **kwargs):
        super().__init__(
            detail=f"유효하지 않은 종목 코드입니다: {symbol}",
            error_code="INVALID_SYMBOL",
            extra={"symbol": symbol},
            **kwargs
        )


# === 서버 오류 ===

class InternalServerError(BaseKingoException):
    """내부 서버 오류"""
    def __init__(self, detail: str = "서버 내부 오류가 발생했습니다", error_code: str = "INTERNAL_SERVER_ERROR", **kwargs):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code=error_code,
            **kwargs
        )


class DatabaseError(InternalServerError):
    """데이터베이스 오류"""
    def __init__(self, detail: str = "데이터베이스 오류가 발생했습니다", **kwargs):
        super().__init__(
            detail=detail,
            error_code="DATABASE_ERROR",
            **kwargs
        )


class ConfigurationError(InternalServerError):
    """설정 오류"""
    def __init__(self, detail: str = "서버 설정 오류가 발생했습니다", **kwargs):
        super().__init__(
            detail=detail,
            error_code="CONFIGURATION_ERROR",
            **kwargs
        )
