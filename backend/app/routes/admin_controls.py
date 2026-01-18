"""
Phase 3-C / Epic C-4: 관리자 통제 API
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.admin_rbac_service import AdminRBACService
from app.services.admin_audit_service import AdminAuditService
from app.services.admin_approval_service import AdminApprovalService
from app.services.admin_adjustment_service import AdminAdjustmentService
from app.services.result_version_service import ResultVersionService, VersionError
from app.utils.request_meta import request_meta, require_idempotency


router = APIRouter(
    prefix="/admin/controls",
    tags=["Admin Controls"],
    dependencies=[Depends(require_idempotency)],
)


def _require_permission(
    db: Session,
    user: User,
    permission_key: str,
) -> None:
    rbac = AdminRBACService(db)
    if not rbac.has_permission(user.id, permission_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다",
        )


@router.post("/rbac/bootstrap")
def bootstrap_rbac(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: Dict[str, Optional[str]] = Depends(request_meta(require_idempotency=True)),
):
    _require_permission(db, current_user, "ADMIN_ROLE_MANAGE")
    AdminRBACService(db).bootstrap_defaults()
    return {"success": True, "request_id": meta["request_id"]}


@router.post("/roles/assign")
def assign_role(
    user_id: str,
    role_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: Dict[str, Optional[str]] = Depends(request_meta(require_idempotency=True)),
):
    _require_permission(db, current_user, "ADMIN_ROLE_MANAGE")
    mapping = AdminRBACService(db).assign_role(
        user_id=user_id,
        role_name=role_name,
        assigned_by=current_user.id,
    )
    return {
        "success": True,
        "data": {
            "user_id": mapping.user_id,
            "role_id": mapping.role_id,
            "is_active": mapping.is_active,
        },
        "request_id": meta["request_id"],
    }


@router.get("/roles")
def list_user_roles(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_permission(db, current_user, "ADMIN_ROLE_MANAGE")
    roles = AdminRBACService(db).list_user_roles(user_id)
    return {"success": True, "data": roles}


@router.post("/approvals")
def create_approval(
    request_type: str,
    request_payload: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: Dict[str, Optional[str]] = Depends(request_meta(require_idempotency=True)),
):
    _require_permission(db, current_user, "ADMIN_APPROVE")
    if not reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="reason is required",
        )
    approval = AdminApprovalService(db).create_request(
        request_type=request_type,
        requested_by=current_user.id,
        request_payload=request_payload,
        request_id=request_id or meta["request_id"],
        idempotency_key=idempotency_key or meta["idempotency_key"],
    )
    AdminAuditService(db).record(
        operator_id=current_user.id,
        operator_role=current_user.role,
        action_type="APPROVAL_REQUEST",
        target_type="APPROVAL",
        target_id=approval.approval_id,
        reason=reason,
        request_id=request_id or meta["request_id"],
        idempotency_key=idempotency_key or meta["idempotency_key"],
        before_state=None,
        after_state={"status": approval.status},
    )
    return {
        "success": True,
        "data": {"approval_id": approval.approval_id},
        "request_id": meta["request_id"],
    }


@router.post("/approvals/{approval_id}/approve")
def approve_request(
    approval_id: str,
    approved_reason: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: Dict[str, Optional[str]] = Depends(request_meta(require_idempotency=True)),
):
    _require_permission(db, current_user, "ADMIN_APPROVE")
    try:
        approval = AdminApprovalService(db).approve(
            approval_id=approval_id,
            approved_by=current_user.id,
            approved_reason=approved_reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    AdminAuditService(db).record(
        operator_id=current_user.id,
        operator_role=current_user.role,
        action_type="APPROVAL_APPROVE",
        target_type="APPROVAL",
        target_id=approval.approval_id,
        reason=approved_reason,
        before_state={"status": AdminApprovalService.STATUS_PENDING},
        after_state={"status": approval.status},
    )
    return {"success": True, "data": {"status": approval.status}, "request_id": meta["request_id"]}


@router.post("/approvals/{approval_id}/reject")
def reject_request(
    approval_id: str,
    approved_reason: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: Dict[str, Optional[str]] = Depends(request_meta(require_idempotency=True)),
):
    _require_permission(db, current_user, "ADMIN_APPROVE")
    try:
        approval = AdminApprovalService(db).reject(
            approval_id=approval_id,
            approved_by=current_user.id,
            approved_reason=approved_reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    AdminAuditService(db).record(
        operator_id=current_user.id,
        operator_role=current_user.role,
        action_type="APPROVAL_REJECT",
        target_type="APPROVAL",
        target_id=approval.approval_id,
        reason=approved_reason,
        before_state={"status": AdminApprovalService.STATUS_PENDING},
        after_state={"status": approval.status},
    )
    return {"success": True, "data": {"status": approval.status}, "request_id": meta["request_id"]}


@router.post("/approvals/{approval_id}/execute")
def execute_request(
    approval_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: Dict[str, Optional[str]] = Depends(request_meta(require_idempotency=True)),
):
    _require_permission(db, current_user, "ADMIN_APPROVE")
    try:
        approval = AdminApprovalService(db).mark_executed(approval_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    AdminAuditService(db).record(
        operator_id=current_user.id,
        operator_role=current_user.role,
        action_type="APPROVAL_EXECUTE",
        target_type="APPROVAL",
        target_id=approval.approval_id,
        reason="execute approved request",
        before_state={"status": AdminApprovalService.STATUS_APPROVED},
        after_state={"status": approval.status},
    )
    return {"success": True, "data": {"status": approval.status}, "request_id": meta["request_id"]}


@router.post("/results/versions/{version_id}/activate")
def activate_result_version(
    version_id: int,
    approval_id: str,
    reason: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: Dict[str, Optional[str]] = Depends(request_meta(require_idempotency=True)),
):
    _require_permission(db, current_user, "ADMIN_ACTIVATE_VERSION")
    if not reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="reason is required",
        )

    approval_service = AdminApprovalService(db)
    approval = approval_service.get(approval_id)
    if not approval:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="approval not found")
    if approval.status != AdminApprovalService.STATUS_APPROVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="approval is not approved")
    if approval.request_type != "RESULT_VERSION_ACTIVATE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="approval type mismatch")

    version_service = ResultVersionService(db)
    target_version = version_service.get_version_by_id(version_id)
    if not target_version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="result version not found")
    if target_version.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="version is already active")

    current_active = version_service.get_active_version(
        target_version.result_type,
        target_version.result_id,
    )

    try:
        version = version_service.reactivate_version(
            version_id=version_id,
            reactivated_by=current_user.id,
            reason=reason,
        )
    except VersionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)

    approval_service.mark_executed(approval_id)

    AdminAuditService(db).record(
        operator_id=current_user.id,
        operator_role=current_user.role,
        action_type="VERSION_ACTIVATE",
        target_type="RESULT_VERSION",
        target_id=str(version_id),
        reason=reason,
        request_id=meta["request_id"],
        idempotency_key=meta["idempotency_key"],
        before_state={
            "active_version_id": current_active.version_id if current_active else None,
            "activated_version_id": version_id,
        },
        after_state={
            "active_version_id": version.version_id,
        },
    )

    return {
        "success": True,
        "data": {
            "version_id": version.version_id,
            "result_type": version.result_type,
            "result_id": version.result_id,
            "is_active": version.is_active,
        },
        "request_id": meta["request_id"],
    }


@router.post("/adjustments")
def create_adjustment(
    target_type: str,
    target_id: str,
    adjustment_type: str,
    adjustment_data: Dict[str, Any],
    reason: str,
    approval_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: Dict[str, Optional[str]] = Depends(request_meta(require_idempotency=True)),
):
    _require_permission(db, current_user, "ADMIN_ADJUST")
    try:
        adjustment = AdminAdjustmentService(db).create_request(
            target_type=target_type,
            target_id=target_id,
            adjustment_type=adjustment_type,
            adjustment_data=adjustment_data,
            reason=reason,
            requested_by=current_user.id,
            approval_id=approval_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    AdminAuditService(db).record(
        operator_id=current_user.id,
        operator_role=current_user.role,
        action_type="ADJUSTMENT_REQUEST",
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        before_state=None,
        after_state={"status": adjustment.status},
    )
    return {
        "success": True,
        "data": {"adjustment_id": adjustment.adjustment_id},
        "request_id": meta["request_id"],
    }


@router.post("/adjustments/{adjustment_id}/status")
def update_adjustment_status(
    adjustment_id: str,
    status: str,
    reason: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: Dict[str, Optional[str]] = Depends(request_meta(require_idempotency=True)),
):
    _require_permission(db, current_user, "ADMIN_ADJUST")
    service = AdminAdjustmentService(db)
    existing = service.get(adjustment_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="adjustment not found",
        )
    adjustment = service.update_status(adjustment_id, status)
    AdminAuditService(db).record(
        operator_id=current_user.id,
        operator_role=current_user.role,
        action_type="ADJUSTMENT_STATUS",
        target_type=adjustment.target_type,
        target_id=adjustment.target_id,
        reason=reason,
        before_state={"status": existing.status},
        after_state={"status": status},
    )
    return {"success": True, "data": {"status": adjustment.status}, "request_id": meta["request_id"]}

@router.get("/audit/logs")
def list_audit_logs(
    operator_id: Optional[str] = None,
    action_type: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_permission(db, current_user, "ADMIN_VIEW")
    logs = AdminAuditService(db).list_logs(
        operator_id=operator_id,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        limit=limit,
        offset=offset,
    )
    return {
        "success": True,
        "data": [
            {
                "audit_id": log.audit_id,
                "operator_id": log.operator_id,
                "operator_role": log.operator_role,
                "action_type": log.action_type,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "reason": log.reason,
                "created_at": log.created_at,
            }
            for log in logs
        ],
    }
