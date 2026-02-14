# U-3 릴리즈 노트 (변경 요약)
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

## 범위
- Phase 3-C 사용자 기능 U-3 (설정/프리셋, 알림 설정, 활동 이력)

## 주요 변경 사항
- 사용자 프리셋 CRUD API 추가
- 사용자 알림/노출 빈도 설정 API 추가
- 사용자 활동 이력 조회/기록 API 추가

## API 변경 요약
- GET `/api/v1/users/me/presets`
- POST `/api/v1/users/me/presets`
- PATCH `/api/v1/users/me/presets/{preset_id}`
- DELETE `/api/v1/users/me/presets/{preset_id}`
- GET `/api/v1/users/me/notification-settings`
- PUT `/api/v1/users/me/notification-settings`
- GET `/api/v1/users/me/activity-events`
- POST `/api/v1/users/me/activity-events`

## 데이터/DB
- 사용자 프리셋/알림 설정/활동 이력 테이블 추가

## 품질/검증
- U-3 단위 테스트 및 통합 테스트 통과

## 참고 문서
- `docs/phase3/20260118_u3_detailed_design.md`
- `docs/phase3/20260118_u3_schema_and_api.md`
- `docs/phase3/20260118_u3_implementation_tickets.md`
