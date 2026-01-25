"""
Phase 10 Epic 4: 구조화된 로깅 유틸리티

목적: request_id 기반 추적 가능한 구조화된 로깅 제공

주요 기능:
- request_id 자동 생성 및 전파
- 컨텍스트 정보 포함 로깅
- 성능 메트릭 로깅
- JSON 형식 로그 출력 (선택적)
"""

import logging
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional
import pytz

# Context variable for request tracking
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_user_id: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


def setup_logging():
    """
    로깅 기본 설정
    - 레벨: INFO
    - 포맷: [시간 KST] [레벨] [소스] 메시지
    - 시간대: Asia/Seoul
    """
    kst = pytz.timezone('Asia/Seoul')

    class KSTFormatter(logging.Formatter):
        def converter(self, timestamp):
            return datetime.fromtimestamp(timestamp, kst)

        def formatTime(self, record, datefmt=None):
            dt = self.converter(record.created)
            if datefmt:
                s = dt.strftime(datefmt)
            else:
                s = dt.strftime('%Y-%m-%d %H:%M:%S,%f')[:-3] + f" {kst}"
            return s

    formatter = KSTFormatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)


def generate_request_id() -> str:
    """고유 request_id 생성"""
    return str(uuid.uuid4())[:8]


def get_request_id() -> Optional[str]:
    """현재 컨텍스트의 request_id 반환"""
    return _request_id.get()


def set_request_id(request_id: str) -> None:
    """request_id 설정"""
    _request_id.set(request_id)


def get_user_id() -> Optional[str]:
    """현재 컨텍스트의 user_id 반환"""
    return _user_id.get()


def set_user_id(user_id: str) -> None:
    """user_id 설정"""
    _user_id.set(user_id)


@contextmanager
def request_context(request_id: Optional[str] = None, user_id: Optional[str] = None):
    """
    요청 컨텍스트 관리자

    사용법:
        with request_context() as req_id:
            logger.info("Processing request")
    """
    rid = request_id or generate_request_id()
    token_rid = _request_id.set(rid)
    token_uid = None
    if user_id:
        token_uid = _user_id.set(user_id)

    try:
        yield rid
    finally:
        _request_id.reset(token_rid)
        if token_uid:
            _user_id.reset(token_uid)


class StructuredLogger:
    """구조화된 로깅 클래스"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.name = name

    def _format_message(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        include_request_id: bool = True,
    ) -> str:
        """메시지 포맷팅"""
        parts = []

        # request_id 추가
        if include_request_id:
            req_id = get_request_id()
            if req_id:
                parts.append(f"[req:{req_id}]")

        # user_id 추가
        user_id = get_user_id()
        if user_id:
            parts.append(f"[user:{user_id}]")

        # 메시지 추가
        parts.append(message)

        # 컨텍스트 추가
        if context:
            ctx_str = " ".join(f"{k}={v}" for k, v in context.items())
            parts.append(f"({ctx_str})")

        return " ".join(parts)

    def debug(self, message: str, context: Optional[Dict[str, Any]] = None):
        """DEBUG 로그"""
        self.logger.debug(self._format_message(message, context))

    def info(self, message: str, context: Optional[Dict[str, Any]] = None):
        """INFO 로그"""
        self.logger.info(self._format_message(message, context))

    def warning(self, message: str, context: Optional[Dict[str, Any]] = None):
        """WARNING 로그"""
        self.logger.warning(self._format_message(message, context))

    def error(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        exc_info: bool = False,
    ):
        """ERROR 로그"""
        self.logger.error(self._format_message(message, context), exc_info=exc_info)

    def critical(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        exc_info: bool = False,
    ):
        """CRITICAL 로그"""
        self.logger.critical(self._format_message(message, context), exc_info=exc_info)

    def log_performance(
        self,
        operation: str,
        duration_ms: float,
        context: Optional[Dict[str, Any]] = None,
    ):
        """성능 메트릭 로깅"""
        perf_context = {"operation": operation, "duration_ms": round(duration_ms, 2)}
        if context:
            perf_context.update(context)
        self.info(f"Performance: {operation} completed", perf_context)

    def log_error_with_context(
        self,
        error: Exception,
        operation: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        """에러와 컨텍스트 로깅"""
        err_context = {
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": str(error),
        }
        if context:
            err_context.update(context)
        self.error(f"Error in {operation}: {error}", err_context, exc_info=True)


def get_structured_logger(name: str) -> StructuredLogger:
    """구조화된 로거 팩토리"""
    return StructuredLogger(name)


def log_performance(logger: StructuredLogger, operation: str):
    """
    성능 측정 데코레이터

    사용법:
        @log_performance(logger, "calculate_metrics")
        def calculate_metrics():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.log_performance(operation, duration_ms, {"status": "success"})
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.log_performance(
                    operation, duration_ms, {"status": "error", "error": str(e)}
                )
                raise
        return wrapper
    return decorator


@contextmanager
def log_operation(logger: StructuredLogger, operation: str, context: Optional[Dict[str, Any]] = None):
    """
    작업 로깅 컨텍스트 관리자

    사용법:
        with log_operation(logger, "evaluate_portfolio", {"portfolio_id": 123}):
            # do work
    """
    start_time = time.perf_counter()
    logger.info(f"Starting: {operation}", context)

    try:
        yield
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.log_performance(operation, duration_ms, {"status": "success", **(context or {})})
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.log_error_with_context(e, operation, context)
        raise
