# 환경 분리 증빙 (prod/stg/local)

## 1. 환경 구분 기준
- APP_ENV 값으로 환경 구분
- 설정 파일/변수는 환경별로 분리 관리

## 2. 환경별 설정 차이

| 항목 | local | staging | production |
|------|------|---------|------------|
| APP_ENV | local | staging | prod |
| BASE_URL | http://localhost:8000 | https://stg-api.foresto.co.kr | https://api.foresto.co.kr |
| DB_HOST | localhost | **** | **** |
| AUTH_MODE | jwt | jwt | jwt |
| LOG_LEVEL | debug | info | info |

## 3. 증빙 경로
- prod config: /ops/config/prod.env
- stg config: /ops/config/stg.env
- local config: .env (로컬)

## 4. 결론
- 환경 분리 여부: 정보 기준 확정
- 보완 필요: 확인 일시 기록 및 실제 파일 스냅샷 첨부
