# Phase 3-C / Epic C-4 상세 설계
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

## Epic ID
- **Epic**: C-4
- **명칭**: 관리자·통제 기능 (Admin & Controls)
- **Phase**: Phase 3-C

---

## 1. 목적 (Purpose)

Epic C-4의 목적은 운영자가 시스템을 안전하게 통제(중단/재처리/정정/버전 전환)할 수 있도록 **권한(RBAC), 감사(Audit), 워크플로우(Approval), 안전장치(Guardrails)**를 제공하는 것이다.

> 핵심 원칙: *운영자 편의보다 통제와 추적성 우선*

---

## 2. 범위 (Scope)

### In-Scope
- 관리자 권한 모델(RBAC)
- 관리자 전용 API 엔드포인트 표준
- 수동 개입 워크플로우(재처리/정정/중단/재개/버전 전환)
- 관리자 행위 감사 로그 및 조회
- 사용자 기능과 관리자 기능의 분리 기준

### Out-of-Scope
- 고객센터/CS 업무 시스템
- 완전한 워크플로우 엔진(BPM)
- 다단계 결재(2명 이상 필수 결재) 고도화(단, 확장 가능해야 함)

---

## 3. 사용자/관리자 기능 분리 기준

### 3.1 분리 옵션

| 옵션 | 설명 | 장점 | 단점 |
|---|---|---|---|
| 모듈 분리 | 동일 서비스 내 admin 모듈 | 구현 단순 | 리스크 전파 가능 |
| 별도 서비스 분리 | admin 전용 서비스 | 보안/통제 강화 | 운영 복잡도 증가 |

### 3.2 권장
- Phase 3-C에서는 **모듈 분리 + 강한 권한 통제**로 시작
- Go-Live 이후 운영 리스크/규모 증가 시 별도 서비스 분리로 확장

---

## 4. RBAC(권한) 모델

### 4.1 Role 정의(최소)

| Role | 권한 요약 |
|---|---|
| ADMIN_VIEWER | 조회만 가능 |
| ADMIN_OPERATOR | 실행/중단/재처리 요청 가능 |
| ADMIN_APPROVER | 정정/버전 전환 승인 |
| SUPER_ADMIN | 사용자/권한 관리 포함 |

### 4.2 Permission 매트릭스(예시)

| 기능 | VIEWER | OPERATOR | APPROVER | SUPER |
|---|---:|---:|---:|---:|
| 실행 이력 조회 | ✅ | ✅ | ✅ | ✅ |
| 배치 수동 실행 | ❌ | ✅ | ✅ | ✅ |
| 배치 중단/재개 | ❌ | ✅ | ✅ | ✅ |
| 재처리(REPLAY) | ❌ | ✅ | ✅ | ✅ |
| 결과 버전 전환 | ❌ | ❌ | ✅ | ✅ |
| 수동 정정(보정) | ❌ | ❌ | ✅ | ✅ |
| 권한 관리 | ❌ | ❌ | ❌ | ✅ |

---

## 5. 관리자 행위 감사(Audit)

### 5.1 감사 대상
- 모든 관리자 API 호출(조회 제외는 선택)
- 상태 변경(중단/재개/재처리/버전 전환/정정)

### 5.2 감사 로그 필수 필드
- `audit_id`
- `operator_id`
- `role`
- `action_type` (STOP/RUN/REPLAY/ACTIVATE_VERSION/ADJUST 등)
- `target_type` (JOB/EXECUTION/RESULT_VERSION/DATASET)
- `target_id`
- `reason` (필수)
- `request_id` / `idempotency_key`
- `before_state` / `after_state` (가능하면 JSON)
- `created_at`

> **원칙: 관리자 변경 API 호출 1회 = 감사로그 1건 이상**

---

## 6. 수동 개입 워크플로우

### 6.1 워크플로우 타입

| 워크플로우 | 설명 | 승인 필요 |
|---|---|---|
| 배치 수동 실행 | MANUAL RUN | 선택 |
| 배치 중단/재개 | STOP/RESUME | 선택 |
| 재처리 요청 | REPLAY REQUEST | 기본 1단계(운영자) |
| 결과 버전 전환 | ACTIVATE VERSION | 승인 필수 |
| 수동 정정(보정) | ADJUSTMENT | 승인 필수 |

### 6.2 승인(Approval) 모델 (최소)
- `PENDING → APPROVED → EXECUTED` 또는 `REJECTED`
- 승인자/승인 시각/승인 사유 기록

---

## 7. 관리자 API 설계 표준

### 7.1 공통 규격
- 인증/인가 필수 (관리자 Role)
- 변경 요청에는 `reason` 필수
- `idempotency_key` 헤더 지원
- 응답에 `request_id` 포함

### 7.2 엔드포인트(권장 최소)

#### 조회
- `GET /admin/jobs`
- `GET /admin/executions`
- `GET /admin/executions/{execution_id}`
- `GET /admin/results/versions`
- `GET /admin/audit/logs`

#### 제어
- `POST /admin/jobs/{job_id}/run`
- `POST /admin/executions/{execution_id}/stop`
- `POST /admin/executions/{execution_id}/resume` (옵션)
- `POST /admin/replay`

#### 승인/정정
- `POST /admin/approvals/{approval_id}/approve`
- `POST /admin/approvals/{approval_id}/reject`
- `POST /admin/results/versions/{version_id}/activate`
- `POST /admin/adjustments` (수동 정정 생성)

---

## 8. 안전장치(Guardrails)

- 금지 상태전이 차단 (C-1 상태 전이 규칙 준수)
- RUNNING 중복 실행 금지 또는 큐잉 정책 명시
- 버전 전환 시 active 단일성 보장
- 승인 없는 정정/버전 전환 불가
- 관리자 기능은 사용자 기능과 네임스페이스/라우팅 분리

---

## 9. C-1/C-2/C-3 연계 포인트

| 대상 Epic | 연계 내용 |
|---|---|
| C-1 | execution/job 상태 변경, 재처리 호출, 알림 발생 |
| C-2 | 데이터 스냅샷/룰 버전 확인, 품질 FAIL 시 운영 조치 |
| C-3 | 결과 버전 전환, 성과 재계산 실행 컨텍스트 관리 |

---

## 10. 완료 기준 (Definition of Done)

- [ ] RBAC Role/Permission 적용
- [ ] 관리자 변경 API 전부 감사 로그 남김
- [ ] 재처리/정정/버전 전환은 reason 필수
- [ ] 승인 모델(PENDING/APPROVED/REJECTED) 동작
- [ ] 금지 상태전이/중복 실행 방지

---

## 11. 다음 단계

- C-4 DDL 설계(roles, permissions, audit_logs, approvals, adjustments)
- C-4 구현 작업 티켓 분해
- 관리자 UI/CLI 최소 기능 정의

---

## 12. 관련 문서
- `docs/phase3/c4_ddl_schema.sql`
- `docs/phase3/20260118_c4_ddl_schema.md`
- `docs/phase3/20260118_c4_implementation_tickets.md`
- `docs/phase3/20260118_phase3c_epic_c4_completion_report.md`
- `docs/phase3/20260118_c4_validation_checklist.md`
- `phase3/20260118_phase3c_epic_c1_operations_stability_detailed_design.md`
- `phase3/20260118_phase3c_epic_c2_data_quality_lineage_reproducibility_detailed_design.md`
- `phase3/20260118_phase3c_epic_c3_performance_analysis_advanced_detailed_design.md`

---

*본 문서는 Phase 3-C Epic C-4의 기준 설계 문서이며, 운영 통제 기능의 단일 기준으로 사용된다.*
