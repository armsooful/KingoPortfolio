"""
Phase 3-C / Epic C-4: 관리자 감사 로그 서비스
"""

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.admin_controls import AdminAuditLog


class AdminAuditService:
    """관리자 감사 로그 서비스"""

    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        operator_id: str,
        operator_role: str,
        action_type: str,
        target_type: str,
        target_id: str,
        reason: str,
        request_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
    ) -> AdminAuditLog:
        """감사 로그 기록"""
        if not reason:
            raise ValueError("reason is required for admin audit log")

        log = AdminAuditLog(
            operator_id=operator_id,
            operator_role=operator_role,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            reason=reason,
            request_id=request_id,
            idempotency_key=idempotency_key,
            before_state=before_state,
            after_state=after_state,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get(self, audit_id: str) -> Optional[AdminAuditLog]:
        """audit_id 기준 단건 조회"""
        return self.db.query(AdminAuditLog).filter_by(audit_id=audit_id).first()

    def list_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        operator_id: Optional[str] = None,
        action_type: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
    ) -> List[AdminAuditLog]:
        """감사 로그 목록 조회"""
        query = self.db.query(AdminAuditLog)
        if operator_id:
            query = query.filter(AdminAuditLog.operator_id == operator_id)
        if action_type:
            query = query.filter(AdminAuditLog.action_type == action_type)
        if target_type:
            query = query.filter(AdminAuditLog.target_type == target_type)
        if target_id:
            query = query.filter(AdminAuditLog.target_id == target_id)

        return (
            query.order_by(AdminAuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
