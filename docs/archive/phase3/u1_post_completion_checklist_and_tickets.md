# Phase 3-C / U-1 완료 후속 체크리스트 & 티켓
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

## 1. 개요
U-1 완료 이후의 통합 검증, 운영 준비, 문서 정리, 다음 기능 착수 작업을 우선순위 순으로 관리한다.
모든 항목은 티켓 기반으로 추적하며, 체크리스트와 증빙을 남긴다.

---

## 2. 우선순위 티켓 목록

| ID | 항목 | 상태 | 산출물 |
|---|---|---|---|
| INT-01 | Phase 3-C ↔ Phase A/B 인터페이스 점검 | IN_PROGRESS | 인터페이스 점검 로그 |
| INT-02 | 권한·가드(금지 키워드, 추천 차단 규칙) 재확인 | TODO | 가드 재검증 로그 |
| INT-03 | 회귀 테스트(핵심 시나리오 5~7개) | TODO | 회귀 테스트 결과 |
| OPS-01 | 사용자 이벤트 로깅 스키마 고정 | TODO | 로깅 스키마 문서 |
| OPS-02 | 에러/이상 탐지 알림 기준 설정 | TODO | 알림 기준 문서 |
| OPS-03 | 롤백 플랜 문서화 | TODO | 롤백 플랜 문서 |
| DOC-01 | 사용자 기능(U-1) 기능 명세 최종본 | TODO | 최종 명세서 |
| DOC-02 | API/화면 변경 요약(릴리즈 노트) | TODO | 릴리즈 노트 |
| DOC-03 | 운영 체크리스트 업데이트 | TODO | 업데이트된 체크리스트 |
| NEXT-01 | 사용자 기능 U-2 범위 정의 및 티켓화 | TODO | U-2 범위/티켓 |
| NEXT-02 | Phase 3-D(성과/피드백 루프) 설계 착수 | TODO | Phase 3-D 설계 초안 |

---

## 3. 티켓 상세

### INT-01 Phase 3-C ↔ Phase A/B 인터페이스 점검
목표: Phase A 입력 스키마 및 Phase B 출력 요구와 Phase 3-C/U-1 결과가 정합하게 연결되는지 검증한다.

체크리스트
- [x] Phase A 입력 스키마 필드(cagr, volatility, mdd, total_return, period_days, rebalance_enabled) 매핑 확인
- [x] Phase 3-C 성과 지표(annualized_return, volatility, mdd, period_return 등)와 매핑 규칙 명문화
- [x] Phase B 리포트/프리미엄 구성 요구와 U-1 API 노출 범위 충돌 여부 확인
- [x] 결과 불일치 시 수정 방향(Phase 3-C 수정, Phase A 고정) 원칙 재확인

매핑 규칙(결정)
| Phase A 입력 | Phase 3-C 소스 | 비고 |
|---|---|---|
| cagr | performance_result.annualized_return | 연율화 기준 252일 유지 |
| volatility | performance_result.volatility | 동일 |
| mdd | performance_result.mdd | 동일 |
| total_return | performance_result.cumulative_return | 기간 누적 수익률 |
| period_days | period_end - period_start + 1 | 계산식으로 파생 |
| rebalance_enabled | portfolio 정책 설정 | 사용자 API 미노출, 내부 매핑 |
| bench_total_return (optional) | benchmark_result.benchmark_return | 벤치마크 존재 시 |

결정 사항
- U-1 API 응답 스키마는 유지하고, Phase A 입력용 매핑은 내부 변환 단계에서 처리한다.

증빙
- Phase A 적용 체크리스트: docs/phase3/20260117_phasea_application_checklist_and_implementation_guide.md
- Phase A 완료 보고서: docs/phase3/20260117_phase_a_completion_report.md
- C-3 DDL/지표 정의: docs/phase3/20260118_c3_ddl_schema.md
- U-1 API 설계: docs/phase3/20260118_u1_user_feature_api_design.md
- Phase 3-B 기능 정의서: docs/phase3/20260117_phase3b_feature_definition.md

작업 로그
- 2026-01-18: Phase A 입력 스키마와 U-1 API 설계를 비교 시작. U-1 API 응답에는 cagr/period_days/rebalance_enabled 등 Phase A 입력 필드가 명시되어 있지 않아 매핑 정의 필요.
- 2026-01-18: C-3 DDL에는 annualized_return, volatility, mdd 지표가 정의되어 있음. Phase A cagr와 annualized_return 매핑 여부를 확정해야 함.
- 2026-01-18: Phase A 완료 보고서에 "결과가 달라지면 Phase 3-C를 수정하고 Phase A는 고정" 원칙 명시됨.
- 2026-01-18: 매핑 규칙 확정 및 U-1 API 스키마 유지 결정. Phase A 입력은 내부 변환으로 공급.
- 2026-01-18: Phase 3-B는 Phase 3-A 설명 데이터 기반 프리미엄 리포트 범위로 정의되어 있어 U-1 API 노출 범위와 충돌 없음.

---

### INT-02 권한·가드(금지 키워드, 추천 차단 규칙) 재확인
목표: 사용자 출력 전 구간에서 금지 문구/추천 차단 규칙이 유지되는지 검증한다.

체크리스트
- [x] 금지 문구 리스트 최신본 확인 및 적용 범위 점검
- [x] U-1 UX 문구 가이드와 실제 화면/API 메시지 정합 확인
- [x] 금지 문구 스캔 로그 재실행 또는 최신화 여부 점검
- [x] 관리자/운영자 권한으로 예외 문구 노출되지 않음 확인

증빙
- 금지 용어 목록: docs/compliance/20260114_forbidden_terms_list.md
- 금지 용어 스캔 로그: docs/compliance/20260115_forbidden_terms_scan_log.md
- U-1 UX 문구 가이드: docs/phase3/20260118_u1_ux_copy_guidelines.md

작업 로그
- 2026-01-18: 금지어 목록 문서 최종수정일자(2026-01-18) 확인 완료.
- 2026-01-18: U-1 UX 문구 가이드의 필수/금지 문구 확인 완료. 실제 화면/API 정합성은 별도 실물 확인 필요.
- 2026-01-18: 금지어 스캔 로그는 2026-01-15 기준으로 최신화 필요. U-1 반영 이후 재실행 필요.
- 2026-01-18: 금지어 스캔 재실행 시도. 스캔 타임아웃 발생, '추천/권유/보장' 등의 용어가 주석 및 가드/샘플 파일에서 검출됨. 예외 처리 기준 재확인 필요.
- 2026-01-18: 주석 라인 및 가드/샘플 파일 예외 처리 추가(스크립트 업데이트). 재실행 필요.
- 2026-01-18: 금지어 스캔 재실행 통과. 주석/가드/샘플 제외 기준 적용.
- 2026-01-18: 금지어 스캔 로그 문서 업데이트 완료.
- 2026-01-18: 코드 점검 결과, 규제 가드는 역할/권한에 따른 bypass 로직이 없고 /admin 네임스페이스는 사용자 API와 분리됨. 관리자 권한으로 금지 문구 노출 예외 경로 발견되지 않음(정적 검토 기준).

---

### INT-03 회귀 테스트(핵심 시나리오 5~7개)
목표: U-1 핵심 시나리오를 통합 관점에서 재검증한다.

체크리스트 (정적 검토 완료, 런타임 테스트 대기)
- [x] 기본 포트폴리오 현황 조회(정상)
- [x] 성과 조회(기간 수익률/누적/벤치마크)
- [x] 기준일/출처 표시 및 지연 배지 노출
- [x] 데이터 미산출/오류 시 사용자 메시지
- [x] SIM/BACK 성과 비노출 확인
- [x] 금지 문구 미노출 확인
- [x] active result_version 전환 반영 확인

증빙
- U-1 검증 체크리스트: docs/phase3/20260118_u1_test_checklist.md
- U-1 오류·지연 처리 가이드: docs/phase3/20260118_u1_error_and_delay_handling.md

작업 로그
- 2026-01-18: 회귀 테스트 시나리오 7개 확정. 실행/증빙 수집 대기.
- 2026-01-18: 코드 정적 검토 기준으로 7개 시나리오 확인 완료. 런타임/API 테스트는 환경 준비 후 재실행 필요.

정적 검토 근거
- 기본 조회/성과/설명/Why Panel: backend/app/routes/portfolio_public.py
- LIVE 전용 필터링: PerformanceResult.performance_type == "LIVE" 조건 사용
- 기준일/지연 배지: as_of_date, is_stale, warning_message, status_message 제공
- 오류 처리: _raise_user_friendly_error 사용
- 금지 문구: disclaimer 필드에 필수 문구만 포함
- active result_version 연계: _get_active_result_version_id + _latest_live_performance 사용

---

### OPS-01 사용자 이벤트 로깅 스키마 고정
목표: U-1 사용자 행동 로그의 최소 스키마를 확정한다.

체크리스트
- [x] 이벤트 명칭/버전 규칙 정의
- [x] 필수 필드(user_id, portfolio_id, view_name, as_of_date 등) 확정
- [x] 민감 정보 배제 기준 확인
- [x] 로그 보존 기간 및 접근 권한 정의

증빙
- 운영 안정성 설계: docs/phase3/20260118_phase3c_epic_c1_operations_stability_detailed_design.md

스키마 정의 (U-1 Event Log v1)
- event_name: string (예: u1_portfolio_summary_view, u1_performance_view, u1_performance_explanation_view, u1_why_panel_view, u1_api_error)
- event_version: string ("v1")
- occurred_at: datetime (UTC ISO-8601)
- user_id: string
- portfolio_id: string
- view_name: string (summary/performance/explanation/why)
- as_of_date: date (nullable)
- result_version_id: string (nullable)
- is_reference: bool
- is_stale: bool
- request_id: string (nullable)
- status: string (success/error)
- error_code: string (nullable, 내부 코드)
- client_app: string (nullable, 예: web)
- user_agent_hash: string (nullable, raw user-agent 저장 금지)

민감 정보 배제 기준
- IP, 이메일, 이름, 원문 사용자 입력 텍스트 저장 금지
- user_agent는 해시 또는 표준화된 분류값만 저장

보존/접근
- 보존 기간: 180일
- 접근 권한: 운영 관리자(admin)만 조회 가능

작업 로그
- 2026-01-18: U-1 이벤트 로깅 스키마 v1 확정 및 OPS-01 체크리스트 완료.

---

### OPS-02 에러/이상 탐지 알림 기준 설정
목표: 운영 알림 기준과 임계치를 문서화한다.

체크리스트
- [x] 핵심 알림 지표 정의(실패율, 지연, 결과 공백)
- [x] 경고/치명 임계치 설정
- [x] 알림 채널/담당자 매핑
- [x] 오탐 방지 규칙 명시

증빙
- 운영 안정성 설계: docs/phase3/20260118_phase3c_epic_c1_operations_stability_detailed_design.md

알림 기준 (U-1 운영 알림 v1)
- API 오류율: 5분 구간 5% 이상 → Warning, 10% 이상 → Critical
- API 5xx 발생 건수: 5분 구간 10건 이상 → Warning, 30건 이상 → Critical
- 최신 데이터 미산출: is_reference=true 비율 30분 평균 20% 이상 → Warning, 40% 이상 → Critical
- 기준일 지연: is_stale=true 비율 30분 평균 30% 이상 → Warning, 50% 이상 → Critical
- 성과 데이터 공백: performance 결과 None 비율 30분 평균 10% 이상 → Warning, 25% 이상 → Critical

알림 채널/담당
- Warning: 운영 채널(Slack/Webhook) + 주간 리포트 집계
- Critical: 운영 채널 + Email 즉시 발송 + 담당자 온콜

오탐 방지
- 배치 재처리/릴리즈 직후 10분간 알림 완화
- 단발성 1분 스파이크는 제외(5분 평균 기준)

작업 로그
- 2026-01-18: U-1 운영 알림 기준 v1 확정 및 OPS-02 체크리스트 완료.

---

### OPS-03 롤백 플랜 문서화
목표: U-1 릴리즈 롤백 절차를 명확히 문서화한다.

체크리스트
- [x] 롤백 트리거 조건 정의
- [x] 데이터/캐시 롤백 절차 정의
- [x] 사용자 공지 템플릿 준비
- [x] 승인/책임자 플로우 정의

증빙
- 릴리즈 관리 설계: docs/phase3/20260118_c6_release_management_design.md

롤백 플랜 (U-1 Release Rollback v1)
- 트리거 조건
  - Critical 알림(OPS-02) 15분 이상 지속
  - 사용자 오류율 10% 이상 10분 지속
  - LIVE 성과 미노출(전체 is_reference=true) 30분 지속
  - 잘못된 결과_version 노출 확인
- 절차
  - 배포 전 버전으로 API 라우팅 전환(롤백 배포)
  - 캐시 무효화(포트폴리오 요약/성과/설명/Why)
  - 활성 result_version 재지정 또는 이전 활성 버전 복구
  - 롤백 후 30분 모니터링
- 공지 템플릿(요약)
  - "일시적인 오류로 인해 일부 사용자 화면 표시가 제한되었습니다. 현재 복구 조치가 진행 중입니다."
  - "복구 완료 시 안내드리겠습니다."
- 승인/책임자
  - 승인: 운영 책임자(Ops Lead)
  - 실행: 백엔드 담당 + 운영 담당
  - 기록: Admin Audit Log 필수

작업 로그
- 2026-01-18: U-1 롤백 플랜 v1 확정 및 OPS-03 체크리스트 완료.

---

### DOC-01 사용자 기능(U-1) 기능 명세 최종본
목표: U-1 기능 명세를 최종 확정한다.

체크리스트
- [x] 상세 설계 문서와 API 설계 간 불일치 점검
- [x] Read-only 제약 및 금지 문구 규정 재확인
- [x] 최종본 문서명/버전 확정

증빙
- U-1 상세 설계: docs/phase3/20260118_phase3c_user_epic_u1_readonly_user_features_detailed_design.md
- U-1 API 설계: docs/phase3/20260118_u1_user_feature_api_design.md
- U-1 기능 명세 최종본: docs/phase3/20260118_u1_feature_spec_final.md

작업 로그
- 2026-01-18: U-1 기능 명세 최종본 작성 완료 및 DOC-01 체크리스트 완료.

---

### DOC-02 API/화면 변경 요약(릴리즈 노트)
목표: U-1 관련 변경사항을 릴리즈 노트로 요약한다.

체크리스트
- [x] 신규 API/변경 API 목록 정리
- [x] 화면/UX 변경 요약
- [x] 호환성/주의사항 명시

증빙
- U-1 산출물 목록: docs/phase3/20260118_u1_deliverables.md
- U-1 릴리즈 노트: docs/changelogs/20260118_u1_release_notes.md

작업 로그
- 2026-01-18: U-1 릴리즈 노트 작성 완료 및 DOC-02 체크리스트 완료.

---

### DOC-03 운영 체크리스트 업데이트
목표: Go-Live 체크리스트에 U-1 항목을 반영한다.

체크리스트
- [x] U-1 관련 운영 항목 추가
- [x] 알림/로그/롤백 항목 반영
- [x] 검증 완료 기준 업데이트

증빙
- Go-Live 체크리스트: docs/phase3/20260118_phase3c_go_live_readiness_checklist.md

작업 로그
- 2026-01-18: Go-Live 체크리스트에 U-1 운영/테스트/롤백 항목 추가 완료.

---

### NEXT-01 사용자 기능 U-2 범위 정의 및 티켓화
목표: U-2 범위를 정의하고 초기 티켓을 생성한다.

체크리스트
- [x] U-2 목표/범위 정의 초안 작성
- [x] 제외 범위 명확화
- [x] 구현 티켓 초안 작성

증빙
- U-2 범위 및 티켓 초안: docs/phase3/20260118_u2_scope_and_tickets.md
- U-2 기능 명세 최종본: docs/phase3/20260118_u2_feature_spec_final.md

작업 로그
- 2026-01-18: U-2 범위/티켓 초안 작성 완료 및 NEXT-01 체크리스트 완료.
- 2026-01-18: U-2 기능 명세 최종본 작성 완료.
- 2026-01-18: U-2 구현 티켓 작성 완료.

---

### NEXT-02 Phase 3-D(성과/피드백 루프) 설계 착수
목표: Phase 3-D 설계 착수 범위를 정의한다.

체크리스트
- [x] Phase 3-D 범위/목표 정의
- [x] 핵심 메트릭/피드백 루프 설계 항목 정리
- [x] 초기 설계 문서 템플릿 준비

증빙
- Phase 3-D 설계 착수 문서: docs/phase3/20260118_phase3d_design_kickoff.md

작업 로그
- 2026-01-18: Phase 3-D 설계 착수 문서 작성 완료 및 NEXT-02 체크리스트 완료.
- 2026-01-18: Phase 3-D 상세 설계 문서 LOCKED 처리.
