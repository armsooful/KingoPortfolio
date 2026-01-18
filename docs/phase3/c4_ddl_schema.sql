-- =============================================================================
-- Phase 3-C / Epic C-4: Admin Controls DDL
-- 생성일: 2026-01-18
-- 목적: RBAC, 감사 로그, 승인/정정 워크플로우 테이블 정의
-- 대상 DB: PostgreSQL
-- =============================================================================

BEGIN;

SET search_path TO foresto;

-- -----------------------------------------------------------------------------
-- 1. 관리자 역할/권한 (RBAC)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_role (
    role_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name       VARCHAR(50) NOT NULL UNIQUE, -- ADMIN_VIEWER/ADMIN_OPERATOR/ADMIN_APPROVER/SUPER_ADMIN
    role_desc       TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admin_permission (
    permission_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    permission_key  VARCHAR(100) NOT NULL UNIQUE, -- ADMIN_RUN/ADMIN_STOP/ADMIN_REPLAY/ADMIN_ACTIVATE_VERSION 등
    permission_desc TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admin_role_permission (
    role_id         UUID NOT NULL REFERENCES admin_role(role_id) ON DELETE CASCADE,
    permission_id   UUID NOT NULL REFERENCES admin_permission(permission_id) ON DELETE CASCADE,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS admin_user_role (
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id         UUID NOT NULL REFERENCES admin_role(role_id) ON DELETE CASCADE,
    assigned_by     UUID REFERENCES users(id),
    assigned_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (user_id, role_id)
);

CREATE INDEX idx_admin_user_role_user ON admin_user_role(user_id);
CREATE INDEX idx_admin_user_role_role ON admin_user_role(role_id);

-- -----------------------------------------------------------------------------
-- 2. 관리자 감사 로그
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_audit_log (
    audit_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    operator_id     UUID NOT NULL REFERENCES users(id),
    operator_role   VARCHAR(50) NOT NULL,
    action_type     VARCHAR(50) NOT NULL, -- STOP/RUN/REPLAY/ACTIVATE_VERSION/ADJUST/APPROVE 등
    target_type     VARCHAR(50) NOT NULL, -- JOB/EXECUTION/RESULT_VERSION/DATASET 등
    target_id       VARCHAR(100) NOT NULL,
    reason          TEXT NOT NULL,
    request_id      VARCHAR(100),
    idempotency_key VARCHAR(100),
    before_state    JSONB,
    after_state     JSONB,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_admin_audit_operator ON admin_audit_log(operator_id);
CREATE INDEX idx_admin_audit_target ON admin_audit_log(target_type, target_id);
CREATE INDEX idx_admin_audit_created ON admin_audit_log(created_at);

COMMENT ON TABLE admin_audit_log IS '관리자 감사 로그';

-- -----------------------------------------------------------------------------
-- 3. 승인(Approval) 워크플로우
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_approval (
    approval_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_type    VARCHAR(50) NOT NULL, -- REPLAY/ACTIVATE_VERSION/ADJUSTMENT
    request_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- PENDING/APPROVED/REJECTED/EXECUTED
    requested_by    UUID NOT NULL REFERENCES users(id),
    requested_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    approved_by     UUID REFERENCES users(id),
    approved_at     TIMESTAMP,
    approved_reason TEXT,
    executed_at     TIMESTAMP,
    request_id      VARCHAR(100),
    idempotency_key VARCHAR(100)
);

CREATE INDEX idx_admin_approval_status ON admin_approval(status);
CREATE INDEX idx_admin_approval_request ON admin_approval(request_type);

-- -----------------------------------------------------------------------------
-- 4. 수동 정정(Adjustment)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_adjustment (
    adjustment_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_type     VARCHAR(50) NOT NULL, -- RESULT/DATASET/EXECUTION 등
    target_id       VARCHAR(100) NOT NULL,
    adjustment_type VARCHAR(50) NOT NULL, -- CORRECTION/ROLLBACK/OVERRIDE 등
    adjustment_data JSONB NOT NULL DEFAULT '{}'::JSONB,
    reason          TEXT NOT NULL,
    approval_id     UUID REFERENCES admin_approval(approval_id),
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- PENDING/APPROVED/REJECTED/APPLIED
    requested_by    UUID NOT NULL REFERENCES users(id),
    requested_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    applied_at      TIMESTAMP
);

CREATE INDEX idx_admin_adjustment_target ON admin_adjustment(target_type, target_id);
CREATE INDEX idx_admin_adjustment_status ON admin_adjustment(status);

COMMIT;
