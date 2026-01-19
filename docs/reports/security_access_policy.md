# 보안·권한 정책 확정 (Phase 4)

## 1. 인증 필요 API 목록
- `/auth/logout`
- `/auth/refresh`
- `/auth/me`
- `/auth/update-name`
- `/auth/update-profile`
- `/auth/change-password`
- `/auth/request-password-reset`
- `/auth/reset-password`
- `/api/v1/portfolios/{portfolio_id}/summary`
- `/api/v1/portfolios/{portfolio_id}/performance`
- `/api/v1/portfolios/{portfolio_id}/comparison`
- `/api/v1/portfolios/{portfolio_id}/metrics/{metric_key}`
- `/api/v1/bookmarks/*`
- `/api/v1/user-settings/*`
- `/api/v1/events`
- `/api/performance/public`
- `/api/analysis/*`
- `/api/diagnosis/*`
- `/api/market/*`
- `/api/backtesting/*`
- `/api/scenarios/*`
- `/api/admin/*`

## 2. 인증 불필요 API 목록
- `/health`
- `/docs`
- `/openapi.json`
- `/robots.txt`
- `/`
- `/auth/login`
- `/auth/signup`
- `/auth/verify-email`

## 3. 401/403 정책
- 401: 인증 실패/토큰 만료/토큰 누락
- 403: 인증은 되었으나 권한 부족 (예: admin 전용)
- 에러 응답은 전역 에러 핸들러 기준으로 일관된 JSON 포맷 반환

## 4. 비고
- 운영 환경에서 실제 허용/차단 여부는 라우터 의존성(`get_current_user`, RBAC)으로 검증 필요
