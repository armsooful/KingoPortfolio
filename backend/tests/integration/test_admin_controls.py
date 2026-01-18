from datetime import datetime

from app.models.admin_controls import (
    AdminRole,
    AdminPermission,
    AdminRolePermission,
    AdminApproval,
    AdminAuditLog,
)
from app.models.ops import ResultVersion


def _bootstrap_rbac(db):
    role = AdminRole(role_name="ADMIN_APPROVER", role_desc="approver", is_active=True)
    perm = AdminPermission(permission_key="ADMIN_APPROVE", permission_desc="approve")
    db.add(role)
    db.add(perm)
    db.commit()
    db.refresh(role)
    db.refresh(perm)
    db.add(
        AdminRolePermission(role_id=role.role_id, permission_id=perm.permission_id)
    )
    db.commit()
    return role


def _bootstrap_role_manage(db):
    role = AdminRole(role_name="SUPER_ADMIN", role_desc="super", is_active=True)
    perm = AdminPermission(permission_key="ADMIN_ROLE_MANAGE", permission_desc="role manage")
    db.add(role)
    db.add(perm)
    db.commit()
    db.refresh(role)
    db.refresh(perm)
    db.add(AdminRolePermission(role_id=role.role_id, permission_id=perm.permission_id))
    db.commit()
    return role


def _bootstrap_adjuster(db):
    role = AdminRole(role_name="ADMIN_APPROVER", role_desc="approver", is_active=True)
    perm = AdminPermission(permission_key="ADMIN_ADJUST", permission_desc="adjust")
    db.add(role)
    db.add(perm)
    db.commit()
    db.refresh(role)
    db.refresh(perm)
    db.add(AdminRolePermission(role_id=role.role_id, permission_id=perm.permission_id))
    db.commit()
    return role


def _bootstrap_version_activator(db):
    role = AdminRole(role_name="ADMIN_APPROVER", role_desc="approver", is_active=True)
    perm_approve = AdminPermission(permission_key="ADMIN_APPROVE", permission_desc="approve")
    perm_activate = AdminPermission(
        permission_key="ADMIN_ACTIVATE_VERSION",
        permission_desc="activate version",
    )
    db.add(role)
    db.add(perm_approve)
    db.add(perm_activate)
    db.commit()
    db.refresh(role)
    db.refresh(perm_approve)
    db.refresh(perm_activate)
    db.add(AdminRolePermission(role_id=role.role_id, permission_id=perm_approve.permission_id))
    db.add(AdminRolePermission(role_id=role.role_id, permission_id=perm_activate.permission_id))
    db.commit()
    return role


def _assign_role_to_user(db, user_id: str, role_id: str):
    from app.models.admin_controls import AdminUserRole

    mapping = AdminUserRole(user_id=user_id, role_id=role_id, is_active=True)
    db.add(mapping)
    db.commit()


def test_admin_controls_approval_flow(client, db, test_admin, admin_headers):
    role = _bootstrap_rbac(db)
    _assign_role_to_user(db, test_admin.id, role.role_id)
    headers = {**admin_headers, "X-Idempotency-Key": "approval-flow"}

    create_response = client.post(
        "/admin/controls/approvals",
        headers=headers,
        params={"request_type": "REPLAY", "reason": "request replay"},
    )
    assert create_response.status_code == 200
    approval_id = create_response.json()["data"]["approval_id"]

    approve_response = client.post(
        f"/admin/controls/approvals/{approval_id}/approve",
        headers=headers,
        params={"approved_reason": "ok to proceed"},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["data"]["status"] == "APPROVED"

    logs_response = client.get(
        "/admin/controls/audit/logs",
        headers=admin_headers,
        params={"target_type": "APPROVAL"},
    )
    assert logs_response.status_code == 200
    logs = logs_response.json()["data"]
    assert any(log["action_type"] == "APPROVAL_REQUEST" for log in logs)
    assert any(log["action_type"] == "APPROVAL_APPROVE" for log in logs)


def test_admin_controls_reject_and_execute_guards(client, db, test_admin, admin_headers):
    role = _bootstrap_rbac(db)
    _assign_role_to_user(db, test_admin.id, role.role_id)
    headers = {**admin_headers, "X-Idempotency-Key": "approval-guards"}

    create_response = client.post(
        "/admin/controls/approvals",
        headers=headers,
        params={"request_type": "REPLAY", "reason": "request replay"},
    )
    approval_id = create_response.json()["data"]["approval_id"]

    reject_response = client.post(
        f"/admin/controls/approvals/{approval_id}/reject",
        headers=headers,
        params={"approved_reason": "not needed"},
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["data"]["status"] == "REJECTED"

    execute_response = client.post(
        f"/admin/controls/approvals/{approval_id}/execute",
        headers=headers,
    )
    assert execute_response.status_code == 400


def test_admin_controls_approval_state_guard(client, db, test_admin, admin_headers):
    role = _bootstrap_rbac(db)
    _assign_role_to_user(db, test_admin.id, role.role_id)
    headers = {**admin_headers, "X-Idempotency-Key": "approval-state-guard"}

    create_response = client.post(
        "/admin/controls/approvals",
        headers=headers,
        params={"request_type": "REPLAY", "reason": "request replay"},
    )
    approval_id = create_response.json()["data"]["approval_id"]

    approve_response = client.post(
        f"/admin/controls/approvals/{approval_id}/approve",
        headers=headers,
        params={"approved_reason": "ok to proceed"},
    )
    assert approve_response.status_code == 200

    reject_response = client.post(
        f"/admin/controls/approvals/{approval_id}/reject",
        headers=headers,
        params={"approved_reason": "late reject"},
    )
    assert reject_response.status_code == 400


def test_admin_controls_execute_success(client, db, test_admin, admin_headers):
    role = _bootstrap_rbac(db)
    _assign_role_to_user(db, test_admin.id, role.role_id)
    headers = {**admin_headers, "X-Idempotency-Key": "approval-execute"}

    create_response = client.post(
        "/admin/controls/approvals",
        headers=headers,
        params={"request_type": "REPLAY", "reason": "request replay"},
    )
    approval_id = create_response.json()["data"]["approval_id"]

    approve_response = client.post(
        f"/admin/controls/approvals/{approval_id}/approve",
        headers=headers,
        params={"approved_reason": "ok to proceed"},
    )
    assert approve_response.status_code == 200

    execute_response = client.post(
        f"/admin/controls/approvals/{approval_id}/execute",
        headers=headers,
    )
    assert execute_response.status_code == 200
    assert execute_response.json()["data"]["status"] == "EXECUTED"


def test_admin_controls_adjustment_flow(client, db, test_admin, admin_headers):
    role = _bootstrap_adjuster(db)
    _assign_role_to_user(db, test_admin.id, role.role_id)
    headers = {**admin_headers, "X-Idempotency-Key": "adjustment-flow"}

    create_response = client.post(
        "/admin/controls/adjustments",
        headers=headers,
        params={
            "target_type": "RESULT",
            "target_id": "result-1",
            "adjustment_type": "CORRECTION",
            "reason": "fix data",
        },
        json={"field": "value"},
    )
    assert create_response.status_code == 200
    adjustment_id = create_response.json()["data"]["adjustment_id"]

    status_response = client.post(
        f"/admin/controls/adjustments/{adjustment_id}/status",
        headers=headers,
        params={"status": "APPLIED", "reason": "applied"},
    )
    assert status_response.status_code == 200
    assert status_response.json()["data"]["status"] == "APPLIED"

    from app.models.admin_controls import AdminAdjustment
    adjustment = db.query(AdminAdjustment).filter_by(adjustment_id=adjustment_id).first()
    assert adjustment.applied_at is not None

    logs_response = client.get(
        "/admin/controls/audit/logs",
        headers=headers,
        params={"target_id": "result-1"},
    )
    assert logs_response.status_code == 200
    logs = logs_response.json()["data"]
    assert any(log["action_type"] == "ADJUSTMENT_REQUEST" for log in logs)
    assert any(log["action_type"] == "ADJUSTMENT_STATUS" for log in logs)


def test_admin_controls_adjustment_status_variants(client, db, test_admin, admin_headers):
    role = _bootstrap_adjuster(db)
    _assign_role_to_user(db, test_admin.id, role.role_id)
    headers = {**admin_headers, "X-Idempotency-Key": "adjustment-status-variants"}

    create_response = client.post(
        "/admin/controls/adjustments",
        headers=headers,
        params={
            "target_type": "RESULT",
            "target_id": "result-2",
            "adjustment_type": "CORRECTION",
            "reason": "fix data",
        },
        json={"field": "value"},
    )
    adjustment_id = create_response.json()["data"]["adjustment_id"]

    approved_response = client.post(
        f"/admin/controls/adjustments/{adjustment_id}/status",
        headers=headers,
        params={"status": "APPROVED", "reason": "approved"},
    )
    assert approved_response.status_code == 200
    assert approved_response.json()["data"]["status"] == "APPROVED"

    rejected_response = client.post(
        f"/admin/controls/adjustments/{adjustment_id}/status",
        headers=headers,
        params={"status": "REJECTED", "reason": "rejected"},
    )
    assert rejected_response.status_code == 200
    assert rejected_response.json()["data"]["status"] == "REJECTED"


def test_admin_controls_adjustment_duplicate_guard(client, db, test_admin, admin_headers):
    role = _bootstrap_adjuster(db)
    _assign_role_to_user(db, test_admin.id, role.role_id)
    headers = {**admin_headers, "X-Idempotency-Key": "adjustment-dup"}

    create_response = client.post(
        "/admin/controls/adjustments",
        headers=headers,
        params={
            "target_type": "RESULT",
            "target_id": "result-dup",
            "adjustment_type": "CORRECTION",
            "reason": "fix data",
        },
        json={"field": "value"},
    )
    assert create_response.status_code == 200

    duplicate_response = client.post(
        "/admin/controls/adjustments",
        headers={**headers, "X-Idempotency-Key": "adjustment-dup-2"},
        params={
            "target_type": "RESULT",
            "target_id": "result-dup",
            "adjustment_type": "CORRECTION",
            "reason": "fix data again",
        },
        json={"field": "value"},
    )
    assert duplicate_response.status_code == 400


def test_admin_controls_reason_required(client, db, test_admin, admin_headers):
    role = _bootstrap_rbac(db)
    _assign_role_to_user(db, test_admin.id, role.role_id)
    headers = {**admin_headers, "X-Idempotency-Key": "reason-required"}

    response = client.post(
        "/admin/controls/approvals",
        headers=headers,
        params={"request_type": "REPLAY"},
    )
    assert response.status_code == 422


def test_admin_controls_rbac_bootstrap_and_assign(client, db, test_admin, admin_headers):
    role = _bootstrap_role_manage(db)
    _assign_role_to_user(db, test_admin.id, role.role_id)
    headers = {**admin_headers, "X-Idempotency-Key": "rbac-bootstrap"}

    bootstrap_response = client.post("/admin/controls/rbac/bootstrap", headers=headers)
    assert bootstrap_response.status_code == 200

    assign_response = client.post(
        "/admin/controls/roles/assign",
        headers=headers,
        params={"user_id": test_admin.id, "role_name": "ADMIN_VIEWER"},
    )
    assert assign_response.status_code == 200


def test_admin_controls_adjustment_requires_permission(client, auth_headers):
    adjust_response = client.post(
        "/admin/controls/adjustments",
        headers={**auth_headers, "X-Idempotency-Key": "adjustment-deny"},
        params={
            "target_type": "RESULT",
            "target_id": "result-1",
            "adjustment_type": "CORRECTION",
            "reason": "fix data",
        },
        json={"field": "value"},
    )
    assert adjust_response.status_code == 403


def test_admin_controls_activate_version_requires_approved(client, db, test_admin, admin_headers):
    role = _bootstrap_version_activator(db)
    _assign_role_to_user(db, test_admin.id, role.role_id)

    approval_response = client.post(
        "/admin/controls/approvals",
        headers={**admin_headers, "X-Idempotency-Key": "version-approval-pending"},
        params={"request_type": "RESULT_VERSION_ACTIVATE", "reason": "activate version"},
    )
    approval_id = approval_response.json()["data"]["approval_id"]

    inactive_version = ResultVersion(
        result_type="PERFORMANCE",
        result_id="perf-activate",
        version_no=2,
        is_active=False,
        deactivated_at=datetime.utcnow(),
        deactivated_by="seed",
        deactivate_reason="seed",
    )
    db.add(inactive_version)
    db.commit()

    activate_response = client.post(
        f"/admin/controls/results/versions/{inactive_version.version_id}/activate",
        headers={**admin_headers, "X-Idempotency-Key": "version-activate-pending"},
        params={"approval_id": approval_id, "reason": "activate version"},
    )
    assert activate_response.status_code == 400


def test_admin_controls_activate_version_success(client, db, test_admin, admin_headers):
    role = _bootstrap_version_activator(db)
    _assign_role_to_user(db, test_admin.id, role.role_id)

    approval_response = client.post(
        "/admin/controls/approvals",
        headers={**admin_headers, "X-Idempotency-Key": "version-approval"},
        params={"request_type": "RESULT_VERSION_ACTIVATE", "reason": "activate version"},
    )
    approval_id = approval_response.json()["data"]["approval_id"]

    approve_response = client.post(
        f"/admin/controls/approvals/{approval_id}/approve",
        headers={**admin_headers, "X-Idempotency-Key": "version-approval-approve"},
        params={"approved_reason": "ok"},
    )
    assert approve_response.status_code == 200

    active_version = ResultVersion(
        result_type="PERFORMANCE",
        result_id="perf-activate",
        version_no=1,
        is_active=True,
    )
    inactive_version = ResultVersion(
        result_type="PERFORMANCE",
        result_id="perf-activate",
        version_no=2,
        is_active=False,
        deactivated_at=datetime.utcnow(),
        deactivated_by="seed",
        deactivate_reason="seed",
    )
    db.add(active_version)
    db.add(inactive_version)
    db.commit()

    activate_response = client.post(
        f"/admin/controls/results/versions/{inactive_version.version_id}/activate",
        headers={**admin_headers, "X-Idempotency-Key": "version-activate"},
        params={"approval_id": approval_id, "reason": "rollback to v2"},
    )
    assert activate_response.status_code == 200

    db.refresh(active_version)
    db.refresh(inactive_version)
    assert active_version.is_active is False
    assert inactive_version.is_active is True

    approval = db.query(AdminApproval).filter_by(approval_id=approval_id).first()
    assert approval.status == "EXECUTED"

    audit_logs = db.query(AdminAuditLog).filter_by(target_type="RESULT_VERSION").all()
    assert any(log.action_type == "VERSION_ACTIVATE" for log in audit_logs)
