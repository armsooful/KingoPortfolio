# C-4 검증 체크리스트 (Admin Controls)
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

## 1. RBAC 초기화/권한 부여
- [x] `POST /admin/controls/rbac/bootstrap` 호출 후 기본 역할/권한 생성 확인 (상태: 완료, 근거: `backend/tests/integration/test_admin_controls.py`)
- [x] `POST /admin/controls/roles/assign`로 사용자 역할 부여 확인 (상태: 완료, 근거: `backend/tests/integration/test_admin_controls.py`)
- [x] 권한 미보유 사용자 접근 시 403 확인 (상태: 완료, 근거: `backend/tests/integration/test_admin_controls.py`)
- [x] 권한 보유 사용자 접근 시 200 확인 (상태: 완료, 근거: `backend/tests/integration/test_admin_controls.py`)

## 2. 승인(Approval) 워크플로우
- [x] 승인 요청 생성 → 상태 `PENDING` 확인 (상태: 완료, 근거: `backend/tests/integration/test_admin_controls.py`)
- [x] 승인 처리 → 상태 `APPROVED` 확인 (상태: 완료, 근거: `backend/tests/integration/test_admin_controls.py`)
- [x] 거절 처리 → 상태 `REJECTED` 확인 (상태: 완료, 근거: `backend/tests/integration/test_admin_controls.py`)
- [x] 실행 처리 → 상태 `EXECUTED` 확인 (상태: 완료, 근거: `backend/tests/integration/test_admin_controls.py`)

## 3. 정정(Adjustment) 워크플로우
- [x] 정정 요청 생성 → 상태 `PENDING` 확인 (상태: 완료, 근거: `backend/tests/integration/test_admin_controls.py`)
- [x] 정정 상태 변경 → `APPROVED/REJECTED/APPLIED` 전이 확인 (상태: 완료, 근거: `backend/tests/integration/test_admin_controls.py`)
- [x] 정정 상태 변경 시 `applied_at` 업데이트 확인 (APPLIED) (상태: 완료, 근거: `backend/tests/integration/test_admin_controls.py`)

## 4. 감사 로그
- [ ] 승인 요청/승인/거절/실행 시 감사 로그 생성 (상태: 부분, 근거: `backend/tests/integration/test_admin_controls.py`)
- [x] 정정 요청/상태 변경 시 감사 로그 생성 (상태: 완료, 근거: `backend/tests/integration/test_admin_controls.py`)
- [x] `GET /admin/controls/audit/logs`로 로그 조회 가능 (상태: 완료, 근거: `backend/tests/integration/test_admin_controls.py`)

## 5. 입력 검증/보안
- [x] `reason` 누락 시 422 응답 확인 (승인/정정 요청) (상태: 완료, 근거: `backend/tests/integration/test_admin_controls.py`)
- [x] 권한 없는 사용자의 승인/정정 요청 403 확인 (상태: 완료, 근거: `backend/tests/integration/test_admin_controls.py`)
- [ ] idempotency_key/request_id 입력 유지 확인 (요청 추적) (상태: 부분, 근거: `backend/app/utils/request_meta.py`, `backend/app/main.py`)

## 6. 상태 전이 안전장치
- [x] `PENDING` 아닌 승인 요청에 승인/거절 시 400/422 확인 (상태: 완료, 근거: `backend/tests/integration/test_admin_controls.py`)
- [x] 승인되지 않은 요청에 `EXECUTED` 전이 차단 확인 (상태: 완료, 근거: `backend/tests/integration/test_admin_controls.py`)
- [x] 중복 실행/중복 정정 요청에 대한 정책 확인 (상태: 완료, 근거: `backend/tests/integration/test_ops_reliability.py`, `backend/tests/integration/test_admin_controls.py`)

---

*본 체크리스트는 Epic C-4 기능 검증을 위한 최소 확인 항목이다.*
