# Phase 4 Fail-safe 응답 정책

## 목적
장애 상황에서도 사용자 경험이 붕괴되지 않도록 안전한 응답을 제공한다.

## 기본 원칙
- 과도한 상세 오류 노출 금지
- 안전한 기본 메시지 제공
- 재시도 가능 여부 명시

## 예시 응답

### 일반 오류
```json
{
  "error": {
    "code": "TEMPORARY_FAILURE",
    "message": "일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
    "status": 503
  }
}
```

### 외부 의존성 장애
```json
{
  "error": {
    "code": "UPSTREAM_UNAVAILABLE",
    "message": "외부 서비스 응답이 지연되고 있습니다. 잠시 후 다시 시도해주세요.",
    "status": 503
  }
}
```

## 적용 범위
- 핵심 사용자 플로우 (U-1~U-3)
- Guard 경로 (Fail-fast 유지)

## 로그 규칙
- request_id 포함
- error_type=SYSTEM 또는 EXTERNAL

## 완료 기준
- 주요 오류 상황에서 안전한 응답 유지
