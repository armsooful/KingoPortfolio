# Phase 3-C / Epic C-2 구현 작업 티켓
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

- 범위: 데이터 품질 · 계보 · 재현성
- 흐름: 수집 → 검증 → 계보 → 리포트

## C2-T01: DDL 스키마 설계
- 스냅샷/계보/검증/컨텍스트/리포트 테이블 정의
- 산출물: `docs/phase3/c2_ddl_schema.sql`

## C2-T02: Validation Rule 메타/정책
- 규칙/버전/스코프 메타 모델 구현
- FAIL/WARN 정책 연계
- 산출물: `backend/app/models/data_quality.py`, `backend/app/services/data_quality_service.py`

## C2-T03: 실행 컨텍스트 저장
- execution_id 기반 컨텍스트 기록
- 스냅샷/룰버전/파라미터/코드버전 저장
- 산출물: `backend/app/services/execution_context_service.py`

## C2-T04: Lineage 추적
- 노드/엣지 생성 및 조회 API
- 결과 → 스냅샷 역추적 지원
- 산출물: `backend/app/services/lineage_service.py`, `backend/app/routes/admin_lineage.py`

## C2-T05: 데이터 품질 리포트
- 일별/재처리 리포트 생성
- 리포트 조회 API
- 산출물: `backend/app/services/data_quality_report_service.py`, `backend/app/routes/admin_data_quality.py`

## C2-T06: C-1 연계
- FAIL → execution FAILED + 알림
- WARN 누적 → 운영 점검 알림
- 산출물: `backend/app/services/data_quality_service.py`, `backend/app/services/ops_alert_service.py`

## C2-T07: 통합 테스트
- 수집 → 검증 → 계보 → 리포트 플로우 검증
- 산출물: `backend/tests/integration/test_data_quality_api.py`

---

## 작업 순서 제안
1) DDL → 2) Rule 메타 → 3) 실행 컨텍스트 → 4) Lineage → 5) 리포트 → 6) C-1 연계 → 7) 통합 테스트
