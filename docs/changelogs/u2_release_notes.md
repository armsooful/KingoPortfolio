# U-2 릴리즈 노트 (변경 요약)
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

## 범위
- Phase 3-C 사용자 기능 U-2 (성과 히스토리, 기간 비교, 지표 상세, 북마크)

## 주요 변경 사항
- 성과 히스토리/기간 비교/지표 상세 공개 API 추가
- 북마크 CRUD API 추가(읽기 전용 대상 저장)
- U-2 관련 문서/설계 확정

## API 변경 요약
- GET `/api/v1/portfolios/{portfolio_id}/performance/history`
- GET `/api/v1/portfolios/{portfolio_id}/performance/compare`
- GET `/api/v1/portfolios/{portfolio_id}/metrics/{metric_key}`
- GET `/api/v1/bookmarks`
- POST `/api/v1/bookmarks`
- DELETE `/api/v1/bookmarks/{portfolio_id}`

## 데이터/DB
- 북마크 테이블 추가(사용자/포트폴리오 단위 고유 제약)

## 품질/검증
- U-2 단위 테스트 및 통합 테스트 통과
- 전체 pytest: 495 passed, 6 skipped (0:04:11)

## 참고 문서
- `docs/phase3/20260118_u2_feature_spec_final.md`
- `docs/phase3/20260118_u2_implementation_tickets.md`
- `docs/phase3/20260118_u1_u2_integration_verification_report.md`
- `docs/development/20260118_change_summary.md`
- `docs/phase3/20260118_u1_u2_ops_stabilization_plan.md`
