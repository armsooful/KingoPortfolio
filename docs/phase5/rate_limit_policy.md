## Phase 5 Rate Limit / Abuse Guard Policy

목적: 외부 노출 구간에서 과도한 호출/남용을 방지하고 API 안정성을 유지한다.

### 1) 적용 범위
- 인증/로그인/비밀번호 재설정 등 보안 민감 API
- 데이터 조회/내보내기/포트폴리오 생성 API
- 비용 유발 API(AI 분석 등)

### 2) 기본 정책
- 기본 제한: `1000/hour` (전역 기본 한도)
- 엔드포인트별 프리셋 적용
  - AUTH_SIGNUP: `5/hour`
  - AUTH_LOGIN: `10/minute`
  - AUTH_PASSWORD_RESET: `3/hour`
  - DIAGNOSIS_SUBMIT: `10/hour`
  - PORTFOLIO_GENERATE: `100/hour`
  - DATA_EXPORT: `20/hour`
  - AI_ANALYSIS: `5/hour`

### 3) 클라이언트 식별
우선순위:
1. 인증 사용자 ID
2. `X-Forwarded-For` 헤더
3. 원격 주소

### 4) 설정 위치
- Rate Limiter 설정: `backend/app/rate_limiter.py`
- 앱 통합: `backend/app/main.py` (`app.state.limiter` 등록)
- 상세 가이드: `backend/docs/guides/RATE_LIMITING.md`

### 5) 검증 방법(권장)
- Guard 테스트: `pytest -q -m guard --maxfail=1`
- Rate Limit 스모크(수동): 단일 엔드포인트 반복 호출 후 429 확인
- 운영 환경에서는 Redis 스토리지 적용 권장
