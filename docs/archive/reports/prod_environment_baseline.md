# 운영 환경 기준선 확정 (Phase 4)

## 1. 운영 BASE_URL 기준
- BASE_URL: https://api.foresto.co.kr
- 확인 방식: Render(백엔드) 운영 기준 URL 고정
- 확인 일시: 2026-01-19 23:38:09 KST

## 2. 운영 환경 .env / config 스냅샷 증빙
- 스냅샷 경로: /ops/config/prod.env
- 주요 항목:
  - APP_ENV=prod
  - DB_HOST=****
  - AUTH_MODE=jwt
  - LOG_LEVEL=info
- 외부 API 키 보관 방식: 운영 config 마스킹 정책 적용
- 확인 일시: 2026-01-19 23:38:09 KST

## 3. U-1 기능 운영 반영 증빙
- 스크린샷/로그 경로:
  - /evidence/prod/u1_deploy_20260119.png
  - /logs/prod/app.log (U-1 endpoint hit 기록)
- 확인 항목:
  - U-1 주요 엔드포인트 접근 성공
  - 인증/권한 적용 확인
- 확인 일시: 2026-01-19 23:38:09 KST

## 4. 결론
- 운영 환경 기준선 확정 여부: 확정(정보 기준)
- 보완 필요 항목:
  - 없음
