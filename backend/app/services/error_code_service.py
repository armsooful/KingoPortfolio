"""
Phase 3-C / Epic C-1: 오류 코드 조회 서비스
생성일: 2026-01-18
목적: 오류 코드 마스터 데이터 조회 및 메시지 분리
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from functools import lru_cache

from app.models.ops import ErrorCodeMaster


class ErrorCodeService:
    """오류 코드 조회 서비스"""

    def __init__(self, db: Session):
        self.db = db
        self._cache: Dict[str, ErrorCodeMaster] = {}

    def get_error_code(self, error_code: str) -> Optional[ErrorCodeMaster]:
        """
        오류 코드 조회

        Args:
            error_code: 오류 코드 (C1-XXX-NNN)

        Returns:
            ErrorCodeMaster: 오류 코드 정보
        """
        if error_code in self._cache:
            return self._cache[error_code]

        error = self.db.query(ErrorCodeMaster).filter_by(
            error_code=error_code,
            is_active=True
        ).first()

        if error:
            self._cache[error_code] = error

        return error

    def get_user_message(self, error_code: str) -> str:
        """
        사용자용 메시지 조회

        Args:
            error_code: 오류 코드

        Returns:
            str: 사용자 노출용 메시지
        """
        error = self.get_error_code(error_code)
        if error:
            return error.user_message
        return "시스템 오류가 발생했습니다."

    def get_ops_message(self, error_code: str) -> str:
        """
        운영자용 메시지 조회

        Args:
            error_code: 오류 코드

        Returns:
            str: 운영자용 메시지 (원인 포함)
        """
        error = self.get_error_code(error_code)
        if error:
            return error.ops_message
        return f"Unknown error code: {error_code}"

    def get_action_guide(self, error_code: str) -> Optional[str]:
        """
        조치 가이드 조회

        Args:
            error_code: 오류 코드

        Returns:
            str: 조치 가이드
        """
        error = self.get_error_code(error_code)
        if error:
            return error.action_guide
        return None

    def should_auto_alert(self, error_code: str) -> bool:
        """
        자동 알림 여부 확인

        Args:
            error_code: 오류 코드

        Returns:
            bool: 자동 알림 필요 여부
        """
        error = self.get_error_code(error_code)
        if error:
            return error.auto_alert
        return False

    def get_alert_level(self, error_code: str) -> Optional[str]:
        """
        알림 레벨 조회

        Args:
            error_code: 오류 코드

        Returns:
            str: 알림 레벨 (INFO/WARN/ERROR/CRITICAL)
        """
        error = self.get_error_code(error_code)
        if error:
            return error.alert_level
        return None

    def get_severity(self, error_code: str) -> str:
        """
        심각도 조회

        Args:
            error_code: 오류 코드

        Returns:
            str: 심각도 (LOW/MEDIUM/HIGH/CRITICAL)
        """
        error = self.get_error_code(error_code)
        if error:
            return error.severity
        return "MEDIUM"

    def get_category(self, error_code: str) -> str:
        """
        카테고리 조회

        Args:
            error_code: 오류 코드

        Returns:
            str: 카테고리 (INP/EXT/BAT/DQ/LOG/SYS)
        """
        error = self.get_error_code(error_code)
        if error:
            return error.category
        # 코드에서 카테고리 추출 시도
        if "-" in error_code:
            parts = error_code.split("-")
            if len(parts) >= 2:
                return parts[1]
        return "SYS"

    def get_full_info(self, error_code: str) -> Dict[str, Any]:
        """
        오류 코드 전체 정보 조회

        Args:
            error_code: 오류 코드

        Returns:
            Dict: 전체 오류 코드 정보
        """
        error = self.get_error_code(error_code)
        if error:
            return {
                "error_code": error.error_code,
                "category": error.category,
                "severity": error.severity,
                "user_message": error.user_message,
                "ops_message": error.ops_message,
                "action_guide": error.action_guide,
                "auto_alert": error.auto_alert,
                "alert_level": error.alert_level,
            }
        return {
            "error_code": error_code,
            "category": "SYS",
            "severity": "MEDIUM",
            "user_message": "시스템 오류가 발생했습니다.",
            "ops_message": f"Unknown error code: {error_code}",
            "action_guide": None,
            "auto_alert": False,
            "alert_level": None,
        }

    def get_errors_by_category(self, category: str) -> List[ErrorCodeMaster]:
        """
        카테고리별 오류 코드 조회

        Args:
            category: 카테고리 (INP/EXT/BAT/DQ/LOG/SYS)

        Returns:
            List[ErrorCodeMaster]: 오류 코드 목록
        """
        return self.db.query(ErrorCodeMaster).filter_by(
            category=category,
            is_active=True
        ).all()

    def get_errors_by_severity(self, severity: str) -> List[ErrorCodeMaster]:
        """
        심각도별 오류 코드 조회

        Args:
            severity: 심각도 (LOW/MEDIUM/HIGH/CRITICAL)

        Returns:
            List[ErrorCodeMaster]: 오류 코드 목록
        """
        return self.db.query(ErrorCodeMaster).filter_by(
            severity=severity,
            is_active=True
        ).all()

    def get_auto_alert_errors(self) -> List[ErrorCodeMaster]:
        """
        자동 알림 대상 오류 코드 조회

        Returns:
            List[ErrorCodeMaster]: 자동 알림 대상 오류 코드 목록
        """
        return self.db.query(ErrorCodeMaster).filter_by(
            auto_alert=True,
            is_active=True
        ).all()

    def clear_cache(self) -> None:
        """캐시 초기화"""
        self._cache.clear()


def format_error_response(
    error_code: str,
    ops_message: str,
    user_message: str = None,
    detail: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    표준 오류 응답 포맷

    Args:
        error_code: 오류 코드
        ops_message: 운영자용 메시지
        user_message: 사용자용 메시지 (None이면 기본 메시지)
        detail: 상세 정보

    Returns:
        Dict: 표준 오류 응답
    """
    return {
        "success": False,
        "error": {
            "code": error_code,
            "message": user_message or "시스템 오류가 발생했습니다.",
            "ops_detail": ops_message,
            "detail": detail or {},
        }
    }
