"""
Phase 3-C / Epic C-4: 관리자 정정(Adjustment) 서비스
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.admin_controls import AdminAdjustment, AdminApproval


class AdminAdjustmentService:
    """수동 정정(보정) 서비스"""

    STATUS_PENDING = "PENDING"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"
    STATUS_APPLIED = "APPLIED"

    def __init__(self, db: Session):
        self.db = db

    def create_request(
        self,
        target_type: str,
        target_id: str,
        adjustment_type: str,
        adjustment_data: Dict[str, Any],
        reason: str,
        requested_by: str,
        approval_id: Optional[str] = None,
    ) -> AdminAdjustment:
        """정정 요청 생성"""
        if not reason:
            raise ValueError("reason is required for adjustment request")

        existing = (
            self.db.query(AdminAdjustment)
            .filter_by(
                target_type=target_type,
                target_id=target_id,
                status=self.STATUS_PENDING,
            )
            .first()
        )
        if existing:
            raise ValueError("pending adjustment already exists for target")

        adjustment = AdminAdjustment(
            target_type=target_type,
            target_id=target_id,
            adjustment_type=adjustment_type,
            adjustment_data=adjustment_data,
            reason=reason,
            approval_id=approval_id,
            status=self.STATUS_PENDING,
            requested_by=requested_by,
        )
        self.db.add(adjustment)
        self.db.commit()
        self.db.refresh(adjustment)
        return adjustment

    def update_status(
        self,
        adjustment_id: str,
        status: str,
    ) -> AdminAdjustment:
        """정정 상태 변경"""
        adjustment = self.get(adjustment_id)
        if not adjustment:
            raise ValueError("adjustment not found")
        adjustment.status = status
        if status == self.STATUS_APPLIED:
            adjustment.applied_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(adjustment)
        return adjustment

    def link_approval(self, adjustment_id: str, approval_id: str) -> AdminAdjustment:
        """승인 요청 연결"""
        adjustment = self.get(adjustment_id)
        if not adjustment:
            raise ValueError("adjustment not found")
        approval = self.db.query(AdminApproval).filter_by(approval_id=approval_id).first()
        if not approval:
            raise ValueError("approval not found")

        adjustment.approval_id = approval.approval_id
        self.db.commit()
        self.db.refresh(adjustment)
        return adjustment

    def get(self, adjustment_id: str) -> Optional[AdminAdjustment]:
        """adjustment_id 기준 단건 조회"""
        return (
            self.db.query(AdminAdjustment)
            .filter_by(adjustment_id=adjustment_id)
            .first()
        )

    def list_requests(
        self,
        limit: int = 100,
        offset: int = 0,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[AdminAdjustment]:
        """정정 요청 목록 조회"""
        query = self.db.query(AdminAdjustment)
        if target_type:
            query = query.filter(AdminAdjustment.target_type == target_type)
        if target_id:
            query = query.filter(AdminAdjustment.target_id == target_id)
        if status:
            query = query.filter(AdminAdjustment.status == status)

        return (
            query.order_by(AdminAdjustment.requested_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
