# C-4 DDL 설계 (관리자 통제)
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

## 개요
- 대상: 관리자 통제(RBAC/감사/승인/정정)
- 목적: 관리자 권한 통제 및 변경 추적
- 기준 SQL: `docs/phase3/c4_ddl_schema.sql`

---

## 1. admin_role
관리자 역할 정의.

### 주요 컬럼
- `role_id` (PK, UUID)
- `role_name` (ADMIN_VIEWER/ADMIN_OPERATOR/ADMIN_APPROVER/SUPER_ADMIN)
- `role_desc`, `is_active`, `created_at`

---

## 2. admin_permission
관리자 권한 정의.

### 주요 컬럼
- `permission_id` (PK, UUID)
- `permission_key` (예: ADMIN_RUN/ADMIN_STOP/ADMIN_REPLAY/ADMIN_ACTIVATE_VERSION)
- `permission_desc`, `created_at`

---

## 3. admin_role_permission
역할-권한 매핑.

### 주요 컬럼
- `role_id` (FK)
- `permission_id` (FK)
- `created_at`

### 제약
- `(role_id, permission_id)` 복합 PK

---

## 4. admin_user_role
사용자-역할 매핑.

### 주요 컬럼
- `user_id` (FK → users.id)
- `role_id` (FK → admin_role.role_id)
- `assigned_by`, `assigned_at`, `is_active`

---

## 5. admin_audit_log
관리자 감사 로그.

### 주요 컬럼
- `audit_id` (PK, UUID)
- `operator_id`, `operator_role`
- `action_type`, `target_type`, `target_id`
- `reason`, `request_id`, `idempotency_key`
- `before_state`, `after_state` (JSONB)
- `created_at`

---

## 6. admin_approval
승인 워크플로우.

### 주요 컬럼
- `approval_id` (PK, UUID)
- `request_type` (REPLAY/ACTIVATE_VERSION/ADJUSTMENT)
- `request_payload` (JSONB)
- `status` (PENDING/APPROVED/REJECTED/EXECUTED)
- `requested_by/at`, `approved_by/at`, `approved_reason`
- `executed_at`, `request_id`, `idempotency_key`

---

## 7. admin_adjustment
수동 정정(보정).

### 주요 컬럼
- `adjustment_id` (PK, UUID)
- `target_type`, `target_id`
- `adjustment_type` (CORRECTION/ROLLBACK/OVERRIDE)
- `adjustment_data` (JSONB)
- `reason`, `approval_id`
- `status` (PENDING/APPROVED/REJECTED/APPLIED)
- `requested_by/at`, `applied_at`

---

## 참고
- 모든 변경 요청은 감사 로그 + 승인 모델로 추적한다.
- `reason`은 변경 요청의 필수 입력값이다.
