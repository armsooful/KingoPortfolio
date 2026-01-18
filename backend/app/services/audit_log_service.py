"""
Phase 3-C / Epic C-1: 감사 로그 서비스
생성일: 2026-01-18
목적: 모든 수동 개입 및 중요 변경을 추적하는 감사 로그 시스템
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from sqlalchemy.orm import Session
from functools import wraps

from app.models.ops import OpsAuditLog


class AuditType(str, Enum):
    """감사 유형"""
    BATCH_START = "BATCH_START"
    BATCH_STOP = "BATCH_STOP"
    BATCH_REPLAY = "BATCH_REPLAY"
    DATA_CORRECTION = "DATA_CORRECTION"
    CONFIG_CHANGE = "CONFIG_CHANGE"


class TargetType(str, Enum):
    """대상 유형"""
    BATCH_EXECUTION = "BATCH_EXECUTION"
    PORTFOLIO = "PORTFOLIO"
    SIMULATION = "SIMULATION"
    EXPLANATION = "EXPLANATION"
    USER = "USER"
    SYSTEM_CONFIG = "SYSTEM_CONFIG"


class AuditAction(str, Enum):
    """감사 액션"""
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DEACTIVATE = "DEACTIVATE"
    REPLAY = "REPLAY"
    START = "START"
    STOP = "STOP"


class AuditLogError(Exception):
    """감사 로그 관련 예외"""
    pass


class MissingOperatorError(AuditLogError):
    """운영자 정보 누락"""
    def __init__(self):
        super().__init__("operator_id is required for audit logging")


class MissingReasonError(AuditLogError):
    """사유 정보 누락"""
    def __init__(self):
        super().__init__("operator_reason is required for audit logging")


class AuditLogService:
    """감사 로그 서비스"""

    def __init__(self, db: Session):
        self.db = db

    def _validate_required_fields(
        self,
        operator_id: str,
        operator_reason: str
    ) -> None:
        """필수 필드 검증"""
        if not operator_id or not operator_id.strip():
            raise MissingOperatorError()
        if not operator_reason or not operator_reason.strip():
            raise MissingReasonError()

    def log_batch_action(
        self,
        audit_type: AuditType,
        execution_id: str,
        action: AuditAction,
        operator_id: str,
        operator_reason: str,
        operator_ip: Optional[str] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
    ) -> OpsAuditLog:
        """
        배치 관련 감사 로그 기록

        Args:
            audit_type: 감사 유형 (BATCH_START, BATCH_STOP, BATCH_REPLAY)
            execution_id: 배치 실행 ID
            action: 액션 (START, STOP, REPLAY)
            operator_id: 운영자 ID (필수)
            operator_reason: 수행 사유 (필수)
            operator_ip: 운영자 IP
            before_state: 변경 전 상태
            after_state: 변경 후 상태

        Returns:
            OpsAuditLog: 생성된 감사 로그
        """
        self._validate_required_fields(operator_id, operator_reason)

        audit_log = OpsAuditLog(
            audit_type=audit_type.value,
            target_type=TargetType.BATCH_EXECUTION.value,
            target_id=execution_id,
            action=action.value,
            before_state=before_state,
            after_state=after_state,
            operator_id=operator_id.strip(),
            operator_ip=operator_ip,
            operator_reason=operator_reason.strip(),
        )

        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)

        return audit_log

    def log_data_correction(
        self,
        target_type: TargetType,
        target_id: str,
        operator_id: str,
        operator_reason: str,
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
        operator_ip: Optional[str] = None,
        approved_by: Optional[str] = None,
    ) -> OpsAuditLog:
        """
        데이터 보정 감사 로그 기록

        Args:
            target_type: 대상 유형 (PORTFOLIO, SIMULATION 등)
            target_id: 대상 레코드 ID
            operator_id: 운영자 ID (필수)
            operator_reason: 보정 사유 (필수)
            before_state: 변경 전 상태 (필수)
            after_state: 변경 후 상태 (필수)
            operator_ip: 운영자 IP
            approved_by: 승인자 ID

        Returns:
            OpsAuditLog: 생성된 감사 로그
        """
        self._validate_required_fields(operator_id, operator_reason)

        if not before_state or not after_state:
            raise AuditLogError("before_state and after_state are required for data correction")

        audit_log = OpsAuditLog(
            audit_type=AuditType.DATA_CORRECTION.value,
            target_type=target_type.value,
            target_id=target_id,
            action=AuditAction.UPDATE.value,
            before_state=before_state,
            after_state=after_state,
            operator_id=operator_id.strip(),
            operator_ip=operator_ip,
            operator_reason=operator_reason.strip(),
            approved_by=approved_by,
            approved_at=datetime.utcnow() if approved_by else None,
        )

        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)

        return audit_log

    def log_config_change(
        self,
        config_key: str,
        operator_id: str,
        operator_reason: str,
        before_value: Any,
        after_value: Any,
        operator_ip: Optional[str] = None,
    ) -> OpsAuditLog:
        """
        설정 변경 감사 로그 기록

        Args:
            config_key: 설정 키
            operator_id: 운영자 ID (필수)
            operator_reason: 변경 사유 (필수)
            before_value: 변경 전 값
            after_value: 변경 후 값
            operator_ip: 운영자 IP

        Returns:
            OpsAuditLog: 생성된 감사 로그
        """
        self._validate_required_fields(operator_id, operator_reason)

        audit_log = OpsAuditLog(
            audit_type=AuditType.CONFIG_CHANGE.value,
            target_type=TargetType.SYSTEM_CONFIG.value,
            target_id=config_key,
            action=AuditAction.UPDATE.value,
            before_state={"value": before_value},
            after_state={"value": after_value},
            operator_id=operator_id.strip(),
            operator_ip=operator_ip,
            operator_reason=operator_reason.strip(),
        )

        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)

        return audit_log

    def log_generic(
        self,
        audit_type: str,
        target_type: str,
        target_id: str,
        action: str,
        operator_id: str,
        operator_reason: str,
        operator_ip: Optional[str] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        approved_by: Optional[str] = None,
    ) -> OpsAuditLog:
        """
        범용 감사 로그 기록

        Args:
            audit_type: 감사 유형 (문자열)
            target_type: 대상 유형 (문자열)
            target_id: 대상 레코드 ID
            action: 액션 (문자열)
            operator_id: 운영자 ID (필수)
            operator_reason: 수행 사유 (필수)
            operator_ip: 운영자 IP
            before_state: 변경 전 상태
            after_state: 변경 후 상태
            approved_by: 승인자 ID

        Returns:
            OpsAuditLog: 생성된 감사 로그
        """
        self._validate_required_fields(operator_id, operator_reason)

        audit_log = OpsAuditLog(
            audit_type=audit_type,
            target_type=target_type,
            target_id=target_id,
            action=action,
            before_state=before_state,
            after_state=after_state,
            operator_id=operator_id.strip(),
            operator_ip=operator_ip,
            operator_reason=operator_reason.strip(),
            approved_by=approved_by,
            approved_at=datetime.utcnow() if approved_by else None,
        )

        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)

        return audit_log

    def get_audit_logs(
        self,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        audit_type: Optional[str] = None,
        operator_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[OpsAuditLog]:
        """
        감사 로그 조회

        Args:
            target_type: 대상 유형 필터
            target_id: 대상 ID 필터
            audit_type: 감사 유형 필터
            operator_id: 운영자 ID 필터
            start_date: 시작 일시
            end_date: 종료 일시
            limit: 조회 건수
            offset: 시작 위치

        Returns:
            List[OpsAuditLog]: 감사 로그 목록
        """
        query = self.db.query(OpsAuditLog)

        if target_type:
            query = query.filter(OpsAuditLog.target_type == target_type)
        if target_id:
            query = query.filter(OpsAuditLog.target_id == target_id)
        if audit_type:
            query = query.filter(OpsAuditLog.audit_type == audit_type)
        if operator_id:
            query = query.filter(OpsAuditLog.operator_id == operator_id)
        if start_date:
            query = query.filter(OpsAuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(OpsAuditLog.created_at <= end_date)

        return (
            query
            .order_by(OpsAuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_audit_log(self, audit_id: int) -> Optional[OpsAuditLog]:
        """단일 감사 로그 조회"""
        return self.db.query(OpsAuditLog).filter_by(audit_id=audit_id).first()

    def get_audit_logs_by_target(
        self,
        target_type: str,
        target_id: str,
    ) -> List[OpsAuditLog]:
        """대상별 감사 로그 조회"""
        return (
            self.db.query(OpsAuditLog)
            .filter_by(target_type=target_type, target_id=target_id)
            .order_by(OpsAuditLog.created_at.desc())
            .all()
        )

    def get_recent_logs_by_operator(
        self,
        operator_id: str,
        limit: int = 50,
    ) -> List[OpsAuditLog]:
        """운영자별 최근 감사 로그 조회"""
        return (
            self.db.query(OpsAuditLog)
            .filter_by(operator_id=operator_id)
            .order_by(OpsAuditLog.created_at.desc())
            .limit(limit)
            .all()
        )

    def count_logs(
        self,
        target_type: Optional[str] = None,
        audit_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """감사 로그 건수 조회"""
        query = self.db.query(OpsAuditLog)

        if target_type:
            query = query.filter(OpsAuditLog.target_type == target_type)
        if audit_type:
            query = query.filter(OpsAuditLog.audit_type == audit_type)
        if start_date:
            query = query.filter(OpsAuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(OpsAuditLog.created_at <= end_date)

        return query.count()


def audit_log_decorator(
    audit_type: str,
    target_type: str,
    action: str,
):
    """
    감사 로그 데코레이터

    사용 예:
        @audit_log_decorator("BATCH_START", "BATCH_EXECUTION", "START")
        def start_batch(self, execution_id: str, operator_id: str, reason: str):
            ...

    Args:
        audit_type: 감사 유형
        target_type: 대상 유형
        action: 액션
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # 함수 실행 전 상태 캡처 시도
            target_id = kwargs.get('target_id') or kwargs.get('execution_id') or (args[0] if args else None)
            operator_id = kwargs.get('operator_id')
            operator_reason = kwargs.get('reason') or kwargs.get('operator_reason')

            # 함수 실행
            result = func(self, *args, **kwargs)

            # 감사 로그 기록 (db 세션이 있는 경우)
            if hasattr(self, 'db') and operator_id and operator_reason:
                audit_service = AuditLogService(self.db)
                audit_service.log_generic(
                    audit_type=audit_type,
                    target_type=target_type,
                    target_id=str(target_id),
                    action=action,
                    operator_id=operator_id,
                    operator_reason=operator_reason,
                )

            return result
        return wrapper
    return decorator
