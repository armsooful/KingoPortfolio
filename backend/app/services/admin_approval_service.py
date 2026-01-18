"""
Phase 3-C / Epic C-4: 관리자 승인 워크플로우 서비스
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.admin_controls import AdminApproval


class AdminApprovalService:
    """승인 워크플로우 서비스"""

    STATUS_PENDING = "PENDING"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"
    STATUS_EXECUTED = "EXECUTED"

    def __init__(self, db: Session):
        self.db = db

    def create_request(
        self,
        request_type: str,
        requested_by: str,
        request_payload: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> AdminApproval:
        """승인 요청 생성"""
        approval = AdminApproval(
            request_type=request_type,
            request_payload=request_payload or {},
            status=self.STATUS_PENDING,
            requested_by=requested_by,
            request_id=request_id,
            idempotency_key=idempotency_key,
        )
        self.db.add(approval)
        self.db.commit()
        self.db.refresh(approval)
        return approval

    def approve(
        self,
        approval_id: str,
        approved_by: str,
        approved_reason: str,
    ) -> AdminApproval:
        """승인 처리"""
        approval = self.get(approval_id)
        if not approval:
            raise ValueError("approval not found")
        if approval.status != self.STATUS_PENDING:
            raise ValueError("approval is not pending")
        if not approved_reason:
            raise ValueError("approved_reason is required")

        approval.status = self.STATUS_APPROVED
        approval.approved_by = approved_by
        approval.approved_at = datetime.utcnow()
        approval.approved_reason = approved_reason
        self.db.commit()
        self.db.refresh(approval)
        return approval

    def reject(
        self,
        approval_id: str,
        approved_by: str,
        approved_reason: str,
    ) -> AdminApproval:
        """승인 거절 처리"""
        approval = self.get(approval_id)
        if not approval:
            raise ValueError("approval not found")
        if approval.status != self.STATUS_PENDING:
            raise ValueError("approval is not pending")
        if not approved_reason:
            raise ValueError("approved_reason is required")

        approval.status = self.STATUS_REJECTED
        approval.approved_by = approved_by
        approval.approved_at = datetime.utcnow()
        approval.approved_reason = approved_reason
        self.db.commit()
        self.db.refresh(approval)
        return approval

    def mark_executed(self, approval_id: str) -> AdminApproval:
        """실행 완료 상태로 전환"""
        approval = self.get(approval_id)
        if not approval:
            raise ValueError("approval not found")
        if approval.status != self.STATUS_APPROVED:
            raise ValueError("approval is not approved")

        approval.status = self.STATUS_EXECUTED
        approval.executed_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(approval)
        return approval

    def get(self, approval_id: str) -> Optional[AdminApproval]:
        """approval_id 기준 단건 조회"""
        return self.db.query(AdminApproval).filter_by(approval_id=approval_id).first()

    def list_requests(
        self,
        limit: int = 100,
        offset: int = 0,
        request_type: Optional[str] = None,
        status: Optional[str] = None,
        requested_by: Optional[str] = None,
    ) -> List[AdminApproval]:
        """승인 요청 목록 조회"""
        query = self.db.query(AdminApproval)
        if request_type:
            query = query.filter(AdminApproval.request_type == request_type)
        if status:
            query = query.filter(AdminApproval.status == status)
        if requested_by:
            query = query.filter(AdminApproval.requested_by == requested_by)

        return (
            query.order_by(AdminApproval.requested_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
