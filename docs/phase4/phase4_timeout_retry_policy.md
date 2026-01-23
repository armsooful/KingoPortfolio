# Phase 4 타임아웃/재시도 정책

## 목적
외부 의존성 장애 시 실패 전파를 차단하고 핵심 플로우를 유지한다.

## 기본 정책
- 타임아웃은 호출 경로별로 명시
- 재시도는 멱등(idempotent) 요청에만 적용
- 재시도는 지수 백오프 + 지터

## 권장 기준 (초안)
- 외부 API 호출: timeout 2s, retry 2회
- DB 쿼리: timeout 1s (슬로우 쿼리는 별도 큐/배치)
- 내부 API 호출: timeout 1s, retry 1회

## 예외 규칙
- Guard 경로: 재시도 금지 (Fail-fast)
- 인증/결제/권한: 재시도 제한 (보안/중복 방지)

## 로깅
- timeout 발생 시 `error_type=EXTERNAL` 또는 `SYSTEM`으로 분류
- request_id 필수 기록

## 검증 기준
- 장애 주입 시 핵심 플로우 유지
- 타임아웃 이벤트가 알림 기준에 반영됨
