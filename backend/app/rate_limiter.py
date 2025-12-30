"""
API Rate Limiting 설정

slowapi를 사용한 요청 속도 제한 기능을 제공합니다.
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from typing import Callable


def get_client_identifier(request: Request) -> str:
    """
    클라이언트 식별자 추출

    우선순위:
    1. 인증된 사용자 ID (로그인 사용자)
    2. X-Forwarded-For 헤더 (프록시 뒤의 실제 IP)
    3. 원격 주소 (기본)

    Args:
        request: FastAPI Request 객체

    Returns:
        클라이언트 식별자 문자열
    """
    # 1. 인증된 사용자 확인
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.id}"

    # 2. X-Forwarded-For 헤더 확인 (프록시 환경)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # 첫 번째 IP가 실제 클라이언트 IP
        return forwarded.split(",")[0].strip()

    # 3. 원격 주소 (기본)
    return get_remote_address(request)


# Rate Limiter 인스턴스 생성
limiter = Limiter(
    key_func=get_client_identifier,
    default_limits=["1000/hour"],  # 기본 제한: 시간당 1000 요청
    storage_uri="memory://",  # 메모리 스토리지 (개발환경)
    # 프로덕션에서는 Redis 사용 권장:
    # storage_uri="redis://localhost:6379"
)


# Rate Limit 프리셋
class RateLimits:
    """
    엔드포인트별 Rate Limit 프리셋

    형식: "횟수/기간"
    - 기간: second, minute, hour, day
    - 예시: "5/minute" = 분당 5회
    """

    # 인증 관련 (보안 중요)
    AUTH_SIGNUP = "5/hour"           # 회원가입: 시간당 5회
    AUTH_LOGIN = "10/minute"         # 로그인: 분당 10회
    AUTH_REFRESH = "20/hour"         # 토큰 갱신: 시간당 20회
    AUTH_PASSWORD_RESET = "3/hour"   # 비밀번호 재설정: 시간당 3회

    # 진단 관련
    DIAGNOSIS_SUBMIT = "10/hour"     # 진단 제출: 시간당 10회
    DIAGNOSIS_READ = "100/hour"      # 진단 조회: 시간당 100회

    # 데이터 조회
    DATA_READ = "200/hour"           # 데이터 조회: 시간당 200회
    DATA_EXPORT = "20/hour"          # 데이터 내보내기: 시간당 20회

    # 관리자
    ADMIN_WRITE = "100/hour"         # 관리자 작성: 시간당 100회
    ADMIN_READ = "500/hour"          # 관리자 조회: 시간당 500회

    # 공개 API
    PUBLIC_API = "100/hour"          # 공개 API: 시간당 100회

    # AI 분석 (비용 발생)
    AI_ANALYSIS = "5/hour"           # AI 분석: 시간당 5회


def rate_limit_error_handler(request: Request, exc: RateLimitExceeded) -> dict:
    """
    Rate Limit 초과 시 커스텀 에러 응답

    Args:
        request: FastAPI Request 객체
        exc: RateLimitExceeded 예외

    Returns:
        에러 응답 딕셔너리
    """
    return {
        "error": "Rate limit exceeded",
        "message": f"Too many requests. Please try again later.",
        "detail": str(exc.detail),
        "retry_after": exc.retry_after if hasattr(exc, 'retry_after') else None
    }
