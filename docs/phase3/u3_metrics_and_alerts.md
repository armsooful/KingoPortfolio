# Phase 3-C / U-3 메트릭·알림 연계 정의서
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

## 1. 목적
U-3 사용자 설정/이력 기능의 운영 지표를 고정하고 알림 임계치를 명확히 정의한다.

## 2. 이벤트/메트릭 정의

### 이벤트
- `u3_preset_create`
- `u3_preset_update`
- `u3_preset_delete`
- `u3_notification_update`
- `u3_activity_event_create`

### 메트릭(산식)
- 실패율: `failed_requests / total_requests`
- 재시도율: `retry_requests / total_requests` (60초 내 동일 사용자 동일 API)
- 설정 변경률: `u3_notification_update / active_users`
- 프리셋 활용률: `u3_preset_create + u3_preset_update / active_users`

## 3. 알림 임계치(초안)

### 오류율
- 5xx > 1.0% (5분) → 경고
- 5xx > 2.0% (5분) → 긴급

### 지연
- 95p > 1.0s (5분) → 경고
- 99p > 2.5s (5분) → 긴급

### 재시도
- 재시도율 > 5% (15분) → 경고
- 재시도율 > 10% (15분) → 긴급

## 4. 대응 정책
- 경고: 원인 분석 + 재현 로그 확보
- 긴급: 롤백 플랜 검토 + 알림 채널 확대

## 5. 연계 문서
- `docs/phase3/20260118_u3_detailed_design.md`
- `docs/phase3/20260118_u1_u2_ops_stabilization_plan.md`
