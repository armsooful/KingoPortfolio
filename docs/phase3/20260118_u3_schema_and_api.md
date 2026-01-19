# Phase 3-C / 사용자 기능(U-3) DDL/API 스키마
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

## 1. DDL (초안)

```sql
-- 사용자 설정 프리셋
CREATE TABLE IF NOT EXISTS user_preset (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  preset_type TEXT NOT NULL,
  preset_name TEXT NOT NULL,
  preset_payload TEXT NOT NULL,
  is_default INTEGER NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE (user_id, preset_type, preset_name)
);

-- 사용자 상태/이력 이벤트
CREATE TABLE IF NOT EXISTS user_activity_event (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  status TEXT NOT NULL,
  reason_code TEXT,
  metadata TEXT,
  occurred_at DATETIME NOT NULL
);

-- 사용자 알림 설정(옵트인)
CREATE TABLE IF NOT EXISTS user_notification_setting (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL UNIQUE,
  enable_alerts INTEGER NOT NULL DEFAULT 0,
  exposure_frequency TEXT NOT NULL DEFAULT 'STANDARD',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);
```

## 2. API 스키마(초안)

### 2.1 설정/프리셋
- GET `/api/v1/users/me/presets`
- POST `/api/v1/users/me/presets`
- PATCH `/api/v1/users/me/presets/{preset_id}`
- DELETE `/api/v1/users/me/presets/{preset_id}`

#### 요청 예시 (POST)
```json
{
  "preset_type": "FILTER",
  "preset_name": "low_volatility",
  "preset_payload": {
    "sort": "volatility",
    "order": "asc",
    "filters": {"risk_level": "low"}
  },
  "is_default": false
}
```

#### 응답 예시
```json
{
  "id": "preset_01",
  "preset_type": "FILTER",
  "preset_name": "low_volatility",
  "preset_payload": {"sort": "volatility", "order": "asc", "filters": {"risk_level": "low"}},
  "is_default": false,
  "created_at": "2026-01-18T10:00:00Z",
  "updated_at": "2026-01-18T10:00:00Z"
}
```

### 2.2 알림/노출 빈도 설정
- GET `/api/v1/users/me/notification-settings`
- PUT `/api/v1/users/me/notification-settings`

#### 요청 예시 (PUT)
```json
{
  "enable_alerts": true,
  "exposure_frequency": "LOW"
}
```

#### 응답 예시
```json
{
  "enable_alerts": true,
  "exposure_frequency": "LOW",
  "updated_at": "2026-01-18T10:05:00Z"
}
```

### 2.3 상태/이력
- GET `/api/v1/users/me/activity-events`
- POST `/api/v1/users/me/activity-events`

#### 요청 예시 (POST)
```json
{
  "event_type": "VIEW_SUMMARY",
  "status": "COMPLETED",
  "reason_code": null,
  "metadata": {"portfolio_id": "p_01"}
}
```

#### 응답 예시
```json
{
  "success": true,
  "data": [
    {
      "event_id": "evt_01",
      "event_type": "VIEW_SUMMARY",
      "status": "COMPLETED",
      "reason_code": null,
      "metadata": {"portfolio_id": "p_01"},
      "occurred_at": "2026-01-18T09:30:00Z"
    }
  ],
  "meta": {
    "limit": 50,
    "offset": 0
  }
}
```

## 3. 상태/사유 코드
- status: `IN_PROGRESS`, `DEFERRED`, `BLOCKED`, `COMPLETED`
- reason_code: `DATA_DELAY`, `GUARD_BLOCK`, `RATE_LIMIT`, `SYSTEM_ERROR`

## 4. 가드/규제 준수
- 추천/선정 관련 API는 제공하지 않음
- 금지 키워드 회귀 테스트 자동화 대상

## 5. 참조
- `docs/phase3/20260118_u3_detailed_design.md`
- `docs/phase3/20260118_u3_implementation_tickets.md`
