# C-1 ~ C-3 통합 Go-Live 점검표
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

## 상태 표기 기준
- 완료: 검증/테스트 확인
- 부분: 구현 또는 일부 테스트 확인
- 미확인: 검증 근거 없음

## 1. 실행/재현성 (C-1 + C-2 + C-3)
- [ ] 모든 배치 실행이 `batch_execution`에 기록되고 상태 전이 로그가 남는다. (상태: 부분, 근거: `backend/tests/integration/test_ops_reliability.py`)
- [ ] `execution_context`에 `snapshot_ids` / `rule_version_ids` / `code_version`가 기록된다. (상태: 미확인)
- [ ] 성과 결과는 `performance_result`에 불변 저장되고 `result_version`과 연결된다. (상태: 미확인)
- [ ] 재실행 시 동일 입력 → 동일 결과 재현이 가능하다. (상태: 미확인)

## 2. 데이터 품질/계보 (C-2)
- [x] Validation FAIL 시 `batch_execution.status=FAILED`로 전이된다. (상태: 완료, 근거: `backend/tests/integration/test_data_quality_api.py`)
- [ ] FAIL/WARN 발생 시 알림 및 리포트에 반영된다. (상태: 부분, 근거: `backend/tests/integration/test_data_quality_api.py`)
- [ ] 계보(Lineage) 노드/엣지 삭제 금지 정책이 적용된다(비활성화만 허용). (상태: 미확인)

## 3. 운영 안정성 (C-1)
- [ ] 수동 시작/중단/재처리 API가 정상 동작한다. (상태: 부분, 근거: `backend/tests/integration/test_ops_reliability.py`)
- [ ] 감사 로그가 수동 작업에 대해 누락 없이 기록된다. (상태: 부분, 근거: `backend/tests/integration/test_ops_reliability.py`)
- [ ] 운영 알림 채널(Slack/Email 등)이 정상 발송된다. (상태: 미확인)

## 4. 성과 분석 고도화 (C-3)
- [ ] LIVE/SIM/BACK 성과가 분리 저장된다. (상태: 부분, 근거: `backend/tests/integration/test_performance_api.py`)
- [ ] 성과 산식/기준(수수료/세금/배당/FX) 반영 여부가 근거 테이블에 기록된다. (상태: 미확인)
- [ ] 벤치마크 비교 결과가 저장된다. (상태: 미확인)
- [x] 사용자 API는 LIVE 전용 + 면책 문구 포함으로 노출된다. (상태: 완료, 근거: `backend/tests/integration/test_performance_api.py`, `backend/app/routes/performance_public.py`)
- [x] 내부 API는 LIVE/SIM/BACK 모두 조회 가능하다. (상태: 완료, 근거: `backend/tests/integration/test_performance_api.py`, `backend/app/routes/performance_internal.py`)

## 5. API/보안
- [ ] 관리자 전용 엔드포인트는 `require_admin`로 보호된다. (상태: 부분, 근거: `backend/app/routes/performance_internal.py`, `backend/tests/integration/test_performance_api.py`)
- [ ] 사용자 노출 API는 권한 범위가 명확히 분리된다. (상태: 부분, 근거: `backend/app/routes/performance_public.py`)
- [ ] Rate limit 및 입력 검증이 적용된다. (상태: 미확인)

## 6. 데이터 정합성/성능
- [ ] FK/인덱스가 설계대로 적용되어 있다. (상태: 미확인)
- [ ] 대량 처리 시 타임아웃/메모리 한계 테스트를 통과했다. (상태: 미확인)

## 7. 배포/운영 준비
- [ ] 운영자 계정/권한 설정 완료 (상태: 미확인)
- [ ] 알림 수신자/Runbook/긴급 연락망 정리 (상태: 미확인)
- [ ] 롤백 절차 문서화 (상태: 미확인)

## 8. 관리자 통제 (C-4)
- [ ] RBAC Role/Permission 적용 (상태: 부분, 근거: `backend/app/services/admin_rbac_service.py`, `backend/app/routes/admin_controls.py`, 검증: 기본 역할/권한 bootstrap 후 사용자 역할 부여 → 권한별 API 허용/차단 테스트)
- [ ] 관리자 변경 API 전부 감사 로그 남김 (상태: 부분, 근거: `backend/app/services/admin_audit_service.py`, `backend/app/routes/admin_controls.py`, 검증: 승인/정정 요청 생성 후 `GET /admin/controls/audit/logs`로 로그 생성 확인)
- [ ] 재처리/정정/버전 전환은 reason 필수 (상태: 부분, 근거: `backend/app/routes/admin_controls.py`, 검증: reason 누락 요청 시 422 응답 확인)
- [ ] 승인 모델(PENDING/APPROVED/REJECTED/EXECUTED) 동작 (상태: 부분, 근거: `backend/app/services/admin_approval_service.py`, `backend/tests/integration/test_admin_controls.py`, 검증: 승인 생성 → 승인/거절/실행 전이 테스트)
- [ ] 금지 상태전이/중복 실행 방지 (상태: 미확인, 검증: 동일 실행 중복 요청 시 차단 및 감사 로그 기록 확인)
- 참고: `docs/phase3/c4_validation_checklist.md`

---

*본 점검표는 C-1~C-3 기능이 통합된 상태에서 Go-Live 전 반드시 확인해야 할 항목이다.*
