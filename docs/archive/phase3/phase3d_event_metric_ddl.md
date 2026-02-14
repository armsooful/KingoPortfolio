# Phase 3-D / 이벤트·메트릭 DDL 설계
최초작성일자: 2026-01-19
최종수정일자: 2026-01-19

## 1. 목적
- 사용자 행동 이벤트 및 집계 메트릭을 저장하기 위한 스키마 정의
- 추천/선정/성과 예측 관련 데이터는 저장하지 않음

## 2. 이벤트 로그 테이블

```sql
CREATE TABLE IF NOT EXISTS user_event_log (
  event_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  path TEXT NOT NULL,
  status TEXT NOT NULL,
  reason_code TEXT,
  metadata_json TEXT,
  occurred_at DATETIME NOT NULL,
  created_at DATETIME NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_user_event_log_user_time
  ON user_event_log (user_id, occurred_at);

CREATE INDEX IF NOT EXISTS idx_user_event_log_type
  ON user_event_log (event_type);
```

## 3. 메트릭 집계 테이블

```sql
CREATE TABLE IF NOT EXISTS user_metric_aggregate (
  aggregate_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  period_start DATETIME NOT NULL,
  period_end DATETIME NOT NULL,
  completion_rate REAL NOT NULL,
  retry_rate REAL NOT NULL,
  avg_duration_ms INTEGER NOT NULL,
  dropoff_point TEXT,
  created_at DATETIME NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_user_metric_aggregate_user_period
  ON user_metric_aggregate (user_id, period_start, period_end);
```

## 4. 상태/사유 코드
- status: `IN_PROGRESS`, `DEFERRED`, `BLOCKED`, `COMPLETED`
- reason_code: `DATA_DELAY`, `GUARD_BLOCK`, `RATE_LIMIT`, `SYSTEM_ERROR`

## 5. 비고
- metadata_json은 JSON 직렬화 문자열로 저장
- 집계는 배치/스트림 방식 중 운영 환경에 맞춰 확정

## 6. 연계 문서
- `docs/phase3/20260119_phase3d_detailed_design.md`
- `docs/phase3/20260118_phase3d_design_kickoff.md`
