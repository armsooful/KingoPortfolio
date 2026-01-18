# Phase 3-C / Epic U-1 사용자 기능 API 설계
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

## 1. 개요

U-1 사용자 기능의 조회 전용 API 설계를 정의한다. 모든 엔드포인트는 읽기 전용(GET)이며, active result_version과 LIVE 성과만 노출한다.

---

## 2. 엔드포인트 목록

### 2.1 포트폴리오 현황 조회

- **GET** `/api/v1/portfolios/{portfolio_id}/summary`
- **설명**: 자산 구성, 비중, 기준일, 출처 정보 제공

**응답 예시**
```json
{
  "portfolio_id": "pf-001",
  "as_of_date": "2026-01-18",
  "data_source": "KRX/AlphaVantage",
  "is_reference": false,
  "assets": [
    {"asset_class": "EQUITY", "symbol": "005930", "weight": 0.25},
    {"asset_class": "EQUITY", "symbol": "000660", "weight": 0.15}
  ]
}
```

---

### 2.2 성과 조회

- **GET** `/api/v1/portfolios/{portfolio_id}/performance`
- **설명**: 기간 수익률/누적/벤치마크 대비 수익률 제공

**응답 예시**
```json
{
  "portfolio_id": "pf-001",
  "as_of_date": "2026-01-18",
  "performance_type": "LIVE",
  "returns": {
    "1M": 0.012,
    "3M": 0.034,
    "6M": 0.051,
    "YTD": 0.063
  },
  "cumulative_return": 0.189,
  "benchmark_return": 0.142
}
```

---

### 2.3 성과 해석 정보

- **GET** `/api/v1/portfolios/{portfolio_id}/performance/explanation`
- **설명**: 산식 요약 및 반영 요소 설명

**응답 예시**
```json
{
  "portfolio_id": "pf-001",
  "as_of_date": "2026-01-18",
  "calculation": "daily close 기준 누적",
  "factors": ["fees", "fx", "dividend"],
  "price_basis": "close"
}
```

---

### 2.4 신뢰 설명 패널(Why Panel)

- **GET** `/api/v1/portfolios/{portfolio_id}/explain/why`
- **설명**: 데이터 스냅샷 요약, 계산 시점 안내

**응답 예시**
```json
{
  "as_of_date": "2026-01-18",
  "calculated_at": "2026-01-18T09:30:00Z",
  "data_snapshot": "daily close snapshot",
  "note": "이 값은 기준일 종가 기준으로 계산되었습니다."
}
```

---

## 3. 공통 응답 필드

- `as_of_date`
- `data_source`
- `is_reference`

---

## 4. 금지/제약

- SIM/BACK 성과 노출 금지
- 추천/매수 유도 문구 금지
- 사용자 입력 기반 결과 변경 금지
