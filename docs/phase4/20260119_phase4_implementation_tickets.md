# ForestoCompass Phase 4 작업 티켓 (운영 전환)

## 개요
Phase 4는 기능 추가가 아닌 운영 전환 단계다. 성능/SLA, 관측성, 안정성, 운영 문서화를 통해
운영 가능한 제품(Product-Ready) 상태를 만든다.

## Track A. 성능/SLA 검증

### P4-A01. k6 표준 스크립트 초안 작성
- 목적: 재현 가능한 부하 테스트 스크립트 확보
- 범위: 핵심 엔드포인트 3~5개, Guard 경로 포함
- 산출물: k6 스크립트, 실행 가이드
- 상태: 완료
- 참고: `scripts/k6/phase4_standard.js`, `docs/phase4/20260119_phase4_k6_standard_script.md`
- 완료 기준:
  - 스크립트로 재현 가능한 부하 실행 가능
  - Warm-up/Steady/Spike 시나리오 포함

### P4-A02. SLA 기준선 확정 및 리포트 포맷 고정
- 목적: p95/p99 기준선 확정 및 리포트 구조 표준화
- 산출물: SLA 기준 문서, 리포트 템플릿
- 상태: 완료
- 참고: `docs/phase4/20260119_phase4_k6_standard_script.md`
- 완료 기준:
  - Pass/Fail 판정 기준 명확
  - 결과 리포트 자동 작성 가능 수준

### P4-A03. 성능 테스트 실행 및 결과 기록
- 목적: 실제 측정 결과 확보 및 Phase 3 검증 보고서에 Append
- 산출물: 실행 로그, 결과 리포트, Appendix 업데이트
- 상태: 완료
- 참고: `docs/reports/foresto_compass_u3_verification_report_20260119.md`
- 완료 기준:
  - SLA Pass/Fail 판정 완료
  - 재현 가능한 실행 기록 확보

## Track B. 관측성(Observability)

### P4-B01. Correlation ID 전파 표준
- 목적: 요청 단위 추적 가능성 확보
- 범위: API 요청/응답, 내부 이벤트 로그
- 산출물: ID 정책 문서, 로깅 규칙
- 상태: 완료
- 참고: `docs/phase4/20260119_phase4_correlation_id_standard.md`
- 완료 기준:
  - 로그 상에서 요청 단위 상관관계 추적 가능

### P4-B02. 에러 분류 체계 정의
- 목적: 사용자/시스템/외부 오류 분류
- 산출물: 에러 분류표, 응답/로그 규칙
- 상태: 완료
- 참고: `docs/phase4/20260119_phase4_error_classification_standard.md`
- 완료 기준:
  - 장애 1건에 대해 원인 경로 설명 가능

### P4-B03. 메트릭/알림 룰 설정
- 목적: 핵심 지표 수집 및 알림 기준 확정
- 산출물: 메트릭 정의서, 알림 기준표
- 상태: 완료
- 참고: `docs/phase4/20260119_phase4_metrics_alert_rules.md`
- 완료 기준:
  - 장애 감지 및 알림 동작 확인

## Track C. 안정성/회복력

### P4-C01. 타임아웃/재시도/회복 전략 설계
- 목적: 외부 의존성 장애 시 실패 전파 억제
- 산출물: 타임아웃/재시도 정책 문서
- 상태: 완료
- 참고: `docs/phase4/20260119_phase4_timeout_retry_policy.md`
- 완료 기준:
  - 장애 주입 시 핵심 플로우 유지

### P4-C02. Fail-safe 응답 정책 정의
- 목적: 사용자 경험 붕괴 방지
- 산출물: Fail-safe 응답 규격, 예시
- 상태: 완료
- 참고: `docs/phase4/20260119_phase4_fail_safe_policy.md`
- 완료 기준:
  - 주요 오류 상황에서 안전한 응답 유지

### P4-C03. 롤백 시나리오 및 검증 절차
- 목적: 롤백 가능 상태 확보
- 산출물: 롤백 시나리오 문서, 체크리스트
- 상태: 완료
- 참고: `docs/phase4/20260119_phase4_rollback_procedure.md`
- 완료 기준:
  - 롤백 절차 문서화 완료

## Track D. 운영 문서화

### P4-D01. 배포 체크리스트 정비
- 목적: 배포 전/후 필수 점검 표준화
- 산출물: 배포 체크리스트 문서
- 상태: 완료
- 참고: `docs/phase4/20260119_phase4_deployment_checklist.md`
- 완료 기준:
  - 신규 운영자 기준으로도 실행 가능

### P4-D02. 장애 대응 Runbook 작성
- 목적: 장애 시나리오별 대응 절차 정리
- 산출물: Runbook 문서
- 상태: 완료
- 참고: `docs/phase4/20260119_phase4_runbook.md`
- 완료 기준:
  - 대표 장애 시나리오 최소 3종 포함

### P4-D03. 운영자 가이드 최종화
- 목적: 운영 인수 가능 상태 확보
- 산출물: 운영자 가이드 문서
- 상태: 완료
- 참고: `docs/phase4/20260119_phase4_operator_guide.md`
- 완료 기준:
  - 신규 운영자 단독 대응 가능

## 완료 판정 기준
Phase 4는 다음 조건을 모두 충족해야 완료로 판정한다.
- SLA 수치 기반 Pass/Fail 판정 완료
- 장애 원인 추적 가능
- 롤백 절차 문서화
- 운영 문서 완비
- 외부 베타 가능 상태
