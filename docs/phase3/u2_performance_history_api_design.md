# Phase 3-C / U-2 성과 히스토리 조회 API 설계
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

## 1. 목적
U-2 성과 히스토리 조회는 사용자가 기간별 성과 흐름을 이해하도록 돕는 Read-only API다.

---

## 2. 엔드포인트
- **GET** `/api/v1/portfolios/{portfolio_id}/performance/history`

### 파라미터
- `interval` (optional): `DAILY` | `WEEKLY` | `MONTHLY` (default: `MONTHLY`)
- `from` (optional): `YYYY-MM-DD`
- `to` (optional): `YYYY-MM-DD`
- `limit` (optional): 최대 120 (default: 60)

---

## 3. 응답 스키마
```json
{
  "success": true,
  "data": {
    "portfolio_id": 123,
    "interval": "MONTHLY",
    "from": "2024-01-01",
    "to": "2024-12-31",
    "as_of_date": "2024-12-31",
    "performance_type": "LIVE",
    "items": [
      {
        "period_start": "2024-01-01",
        "period_end": "2024-01-31",
        "period_return": 0.0123,
        "cumulative_return": 0.0456,
        "is_reference": false
      }
    ],
    "is_reference": false,
    "is_stale": false,
    "warning_message": null,
    "status_message": null
  }
}
```

---

## 4. 규칙/제약
- LIVE 성과만 노출
- active result_version 기준
- Read-only (GET only)
- SIM/BACK 노출 금지
- 기준일/지연 배지 제공 (`as_of_date`, `is_stale`, `warning_message`)

### 4.1 데이터 소스
- `performance_result` (period_return, cumulative_return, period_start, period_end)
- `result_version` (active)
- `performance_type` = LIVE
- `entity_type` = PORTFOLIO
- `entity_id` = `custom_{portfolio_id}`

### 4.2 interval 매핑
- `DAILY`  -> `period_type` = DAILY
- `WEEKLY` -> `period_type` = WEEKLY
- `MONTHLY` -> `period_type` = MONTHLY

### 4.3 정렬/제한
- `period_end` desc 정렬 후 `limit` 적용 (default 60, max 120)
- 응답 items는 최신순 정렬 유지

### 4.4 엣지 케이스
- `from`/`to` 미지정: 최신 `limit`만 반환
- `from` > `to`: 400 에러
- 결과 없음: items 빈 배열 + `is_reference=true` + status_message
- `interval` 미지원: 400 에러

---

## 5. 오류 처리
- 포트폴리오 미존재: 404
- 잘못된 기간/interval: 400
- 서버 오류: 사용자 친화 메시지

---

## 6. 캐시
- `Cache-Control: public, max-age=300`

---

## 7. 조회 로직(의사 코드)
```python
entity_id = f"custom_{portfolio_id}"
active_version_id = get_active_result_version_id(entity_id)

query = (
    db.query(PerformanceResult)
    .filter(
        PerformanceResult.performance_type == "LIVE",
        PerformanceResult.entity_type == "PORTFOLIO",
        PerformanceResult.entity_id == entity_id,
        PerformanceResult.period_type == interval,
    )
)

if active_version_id:
    query = query.filter(PerformanceResult.result_version_id == active_version_id)

if from_date:
    query = query.filter(PerformanceResult.period_start >= from_date)
if to_date:
    query = query.filter(PerformanceResult.period_end <= to_date)

results = query.order_by(PerformanceResult.period_end.desc()).limit(limit).all()
```
