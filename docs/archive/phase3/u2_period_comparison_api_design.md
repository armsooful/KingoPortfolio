# Phase 3-C / U-2 기간 비교 보기 API 설계
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

## 1. 목적
두 기간의 성과를 비교해 사용자에게 설명형 요약을 제공한다. Read-only이며 예측/권유 표현을 금지한다.

---

## 2. 엔드포인트
- **GET** `/api/v1/portfolios/{portfolio_id}/performance/compare`

### 파라미터
- `left_from` (required): `YYYY-MM-DD`
- `left_to` (required): `YYYY-MM-DD`
- `right_from` (required): `YYYY-MM-DD`
- `right_to` (required): `YYYY-MM-DD`

---

## 3. 응답 스키마
```json
{
  "success": true,
  "data": {
    "portfolio_id": 123,
    "performance_type": "LIVE",
    "left": {
      "from": "2024-01-01",
      "to": "2024-06-30",
      "period_return": 0.034,
      "cumulative_return": 0.152,
      "as_of_date": "2024-06-30"
    },
    "right": {
      "from": "2023-01-01",
      "to": "2023-06-30",
      "period_return": 0.012,
      "cumulative_return": 0.078,
      "as_of_date": "2023-06-30"
    },
    "delta": {
      "period_return": 0.022,
      "cumulative_return": 0.074
    },
    "summary": "최근 비교 기간의 수익률이 이전 기간보다 높습니다.",
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
- summary는 설명형 문구만 사용

### 4.1 데이터 소스
- `performance_result` (period_return, cumulative_return, period_start, period_end)
- `result_version` (active)
- `performance_type` = LIVE
- `entity_type` = PORTFOLIO
- `entity_id` = `custom_{portfolio_id}`

### 4.2 엣지 케이스
- `left_from` > `left_to` 또는 `right_from` > `right_to`: 400 에러
- 기간 길이 차이가 큰 경우에도 비교 허용(요약 문구는 중립 표현 유지)
- 결과 없음: 해당 구간만 `is_reference=true` 처리 및 status_message 제공

---

## 5. 오류 처리
- 포트폴리오 미존재: 404
- 기간 파라미터 누락/역전: 400
- 서버 오류: 사용자 친화 메시지

---

## 6. 캐시
- `Cache-Control: public, max-age=300`

---

## 7. 조회 로직(의사 코드)
```python
entity_id = f"custom_{portfolio_id}"
active_version_id = get_active_result_version_id(entity_id)

def fetch_period(from_date, to_date):
    query = (
        db.query(PerformanceResult)
        .filter(
            PerformanceResult.performance_type == "LIVE",
            PerformanceResult.entity_type == "PORTFOLIO",
            PerformanceResult.entity_id == entity_id,
            PerformanceResult.period_start == from_date,
            PerformanceResult.period_end == to_date,
        )
    )
    if active_version_id:
        query = query.filter(PerformanceResult.result_version_id == active_version_id)
    return query.order_by(PerformanceResult.created_at.desc()).first()

left = fetch_period(left_from, left_to)
right = fetch_period(right_from, right_to)
```
