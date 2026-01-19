# Phase 3-C / U-2 지표 상세 보기 API 설계
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

## 1. 목적
지표별 산식/정의/반영 요소를 상세하게 제공하여 사용자 이해를 돕는다. Read-only이며 금지 문구를 차단한다.

---

## 2. 엔드포인트
- **GET** `/api/v1/portfolios/{portfolio_id}/metrics/{metric_key}`

### 파라미터
- `metric_key` (required): `cagr` | `volatility` | `mdd` | `total_return` | `sharpe` | `sortino`

---

## 3. 응답 스키마
```json
{
  "success": true,
  "data": {
    "portfolio_id": 123,
    "metric_key": "cagr",
    "metric_label": "연복리수익률",
    "as_of_date": "2024-12-31",
    "value": 0.082,
    "formatted_value": "8.20%",
    "definition": "기간 동안의 연복리 수익률입니다.",
    "formula": "(종료 가치 / 시작 가치)^(1/년수) - 1",
    "factors": ["fees", "fx", "dividend"],
    "notes": [
      "과거 성과이며 미래 수익을 보장하지 않습니다."
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
- 문구는 설명형 표현만 사용

### 4.1 데이터 소스
- `performance_result` (annualized_return, volatility, mdd, cumulative_return)
- `performance_basis` (price_basis, include_fee/include_tax/include_dividend)
- `result_version` (active)
- `performance_type` = LIVE
- `entity_type` = PORTFOLIO
- `entity_id` = `custom_{portfolio_id}`

### 4.2 metric_key 매핑
- `cagr` -> `annualized_return`
- `volatility` -> `volatility`
- `mdd` -> `mdd`
- `total_return` -> `cumulative_return`
- `sharpe` -> `sharpe_ratio`
- `sortino` -> `sortino_ratio`

### 4.3 엣지 케이스
- metric 값이 NULL: `value`는 null, `status_message` 안내 제공
- 기준일 지연: `is_stale=true`, `warning_message` 제공
- 지원하지 않는 metric_key: 400 에러

---

## 5. 오류 처리
- 포트폴리오 미존재: 404
- metric_key 미지원: 400
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
    )
)
if active_version_id:
    query = query.filter(PerformanceResult.result_version_id == active_version_id)

latest = query.order_by(PerformanceResult.period_end.desc()).first()
value = extract_metric(latest, metric_key)
```
