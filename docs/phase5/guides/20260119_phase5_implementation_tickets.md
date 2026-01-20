# Phase 5 상세 작업 티켓 (외부 노출·운영 단계)

## 개요
Phase 5는 외부 노출 및 운영 단계 진입을 위한 실적용 단계다.

## 1. 운영 안정화

### P5-A01. 운영 Runbook v1 작성
- 목적: 장애 대응 절차 표준화
- 산출물: `docs/phase5/guides/phase5_runbook.md`
- 우선순위: P0
- 상태: 완료

### P5-A02. 배치/스케줄 모니터링 정의
- 목적: 배치 실패/지연 탐지
- 산출물: `docs/phase5/specs/batch_monitoring_policy.md`
- 상태: 완료

### P5-A03. 알림 임계치 적용
- 목적: 에러/지연/비정상 수치 감지
- 산출물: `ops_alerting.yaml`
- 우선순위: P0
- 상태: 완료
- 검증: `docs/phase5/checklists/alert_verification_checklist.md` (로그 샘플 확인)

## 2. 보안·권한

### P5-B01. 관리자/운영자 권한 매트릭스 확정
- 목적: 최소 권한 원칙 적용
- 산출물: `docs/phase5/specs/rbac_matrix.md`
- 우선순위: P0
- 상태: 완료
- 검증: `docs/phase5/checklists/rbac_verification_checklist.md` (샘플 로그 확인)

### P5-B02. 감사 로그 스키마/정책 확정
- 목적: 조회/수정/배포 기록
- 산출물: 감사 로그 정책 문서
- 우선순위: P0
- 상태: 완료
- 검증: `docs/phase5/checklists/rbac_verification_checklist.md` (샘플 로그 확인)

### P5-B03. 민감 파라미터 마스킹 적용
- 목적: 응답/로그 마스킹
- 산출물: `docs/phase5/specs/masking_policy.md`
- 상태: 완료(정책 확정)
- 검증: `docs/phase5/checklists/masking_verification_checklist.md` (샘플 로그 확인)

## 3. 외부 노출 정책

### P5-C01. 사용자 고지 문구 최종본 반영
- 목적: 정보제공 한계 명시
- 산출물: `docs/phase5/specs/user_disclaimer_v1.md`
- 우선순위: P1
- 상태: 완료
- 검증: `/health` 응답 헤더 `x-user-disclaimer` URL-encoded 확인 (200 OK)
- 검증 일시: 2026-01-20 00:26:27 GMT

### P5-C02. 추천·선정 로직 차단 유지 검증
- 목적: 규제 준수 확인
- 산출물: 검증 체크리스트
- 상태: 완료
- 검증: `pytest -q -m guard --maxfail=1` (tests/unit/test_forbidden_terms_regression.py)
- 검증 일시: 2026-01-20 09:31:12 KST

### P5-C03. API Rate Limit/Abuse Guard 적용
- 목적: 악용 방지
- 산출물: `docs/phase5/specs/rate_limit_policy.md`
- 상태: 완료
- 참고: `backend/docs/guides/RATE_LIMITING.md`, `backend/app/rate_limiter.py`
- 검증: `/auth/login` 12회 호출 시 11~12번째 429 확인 (1~10번째 401)
- 검증 일시: 2026-01-20 09:36:25 KST

## 4. 운영 지표

### P5-D01. KPI 정의
- 목적: 가용성/처리시간/오류율 기준 고정
- 산출물: `docs/phase5/specs/kpi_dashboard_spec.md`
- 우선순위: P1
- 상태: 완료

### P5-D02. 일/주간 리포트 자동화
- 목적: 운영 리포트 자동화
- 산출물: 리포트 템플릿 및 스케줄
- 우선순위: P1
- 상태: 완료

## 5. 릴리스

### P5-E01. Canary/제한 공개 계획 수립
- 목적: 단계적 외부 노출
- 산출물: 릴리스 계획 문서
- 우선순위: P1
- 상태: 완료

### P5-E02. 롤백 전략 문서화
- 목적: 안정 복구 경로 확보
- 산출물: 롤백 절차 문서
- 우선순위: P1
- 상태: 완료
