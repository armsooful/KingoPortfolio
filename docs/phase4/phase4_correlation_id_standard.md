# Phase 4 Correlation ID 전파 표준

## 목적
요청 단위 추적 가능성 확보를 위해 모든 요청/응답/로그에 Correlation ID를 포함한다.

## 적용 범위
- API 요청/응답 헤더
- 내부 이벤트 로그
- 에러 로그

## 표준 헤더
- 요청 헤더: `X-Request-Id`
- 응답 헤더: `X-Request-Id` (요청 값 그대로 또는 서버 생성)

## 생성 규칙
- 클라이언트가 `X-Request-Id`를 전달하면 그대로 사용
- 없을 경우 서버에서 UUIDv4 생성

## 로그 포맷 규칙(권장)
- 필수 필드: `request_id`, `path`, `method`, `status_code`, `latency_ms`
- 권장 필드: `user_id`, `ip`, `user_agent`

## 구현 위치
- FastAPI middleware에서 `X-Request-Id` 주입
- DB/이벤트 로그에는 `request_id` 컬럼 저장

## 검증 기준
- 모든 응답에 `X-Request-Id`가 포함됨
- 장애 1건에 대해 요청/로그/이벤트를 단일 ID로 추적 가능
