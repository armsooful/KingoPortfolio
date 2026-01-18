# Phase 3-C / Epic C-3 구현 작업 티켓
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

- 범위: 성과 분석 고도화 (Performance Analytics)

## C3-T01: DDL 스키마 설계
- LIVE/SIM/BACK 성과 저장 및 버전/벤치마크 테이블 정의
- 산출물: `docs/phase3/c3_ddl_schema.sql`

## C3-T02: 성과 계산 엔진 설계
- 산식/지표/입력/출력 정의
- 산출물: `docs/phase3/20260118_20260118_c3_performance_engine_spec.md`

## C3-T03: 성과 계산 서비스 구현
- 결과 계산 및 `performance_result` 저장
- 산출 근거 저장 (`performance_basis`)
- 산출물: `backend/app/services/performance_analytics_service.py`

## C3-T04: 벤치마크 비교 구현
- 벤치마크 수익률/초과 수익률 계산
- `benchmark_result` 저장
- 산출물: `backend/app/services/benchmark_service.py`

## C3-T05: 버전 관리 연계
- `result_version`와 성과 결과 연결
- active 버전 1건 유지
- 산출물: `backend/app/services/result_version_service.py` 확장

## C3-T06: 사용자/내부 API 분리
- 내부 API: LIVE/SIM/BACK 전부 제공
- 사용자 API: LIVE만 제공 + 면책
- 산출물: `backend/app/routes/performance_internal.py`, `backend/app/routes/performance_public.py`

## C3-T07: 통합 테스트
- LIVE/SIM/BACK 분리 저장 및 조회 테스트
- 벤치마크 비교 테스트
- 산출물: `backend/tests/integration/test_performance_analytics.py`

---

## 작업 순서 제안
1) DDL → 2) 계산 엔진 → 3) 성과 계산 서비스 → 4) 벤치마크 → 5) 버전 연계 → 6) API 분리 → 7) 통합 테스트
