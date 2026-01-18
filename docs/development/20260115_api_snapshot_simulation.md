# API 스냅샷: 시뮬레이션 응답 (Phase 0)
최초작성일자: 2026-01-15
최종수정일자: 2026-01-18

> 작성일: 2026-01-15
> 엔진 버전: 1.0.0

본 문서는 Foresto Compass 시뮬레이션 API의 응답 구조를 정의합니다.
**손실·회복 지표를 최상위에 배치**하여 규제 준수 및 리스크 인지를 우선합니다.

---

## 1. POST /backtest/run

### 요청 예시
```json
{
  "investment_type": "moderate",
  "investment_amount": 10000000,
  "period_years": 3,
  "rebalance_frequency": "quarterly"
}
```

### 응답 예시 (손실·회복 중심)
```json
{
  "success": true,
  "data": {
    "start_date": "2023-01-15T00:00:00",
    "end_date": "2026-01-15T00:00:00",
    "initial_investment": 10000000,
    "final_value": 11250000,

    "risk_metrics": {
      "max_drawdown": 15.3,
      "max_recovery_days": 87,
      "worst_1m_return": -8.2,
      "worst_3m_return": -12.1,
      "volatility": 14.5
    },

    "historical_observation": {
      "total_return": 12.5,
      "cagr": 4.0,
      "sharpe_ratio": 0.72
    },

    "total_return": 12.5,
    "annualized_return": 4.0,
    "volatility": 14.5,
    "sharpe_ratio": 0.72,
    "max_drawdown": 15.3,
    "daily_values": [...],
    "rebalance_frequency": "quarterly",
    "number_of_rebalances": 12
  },
  "request_hash": "a1b2c3d4e5f6...64자리",
  "cache_hit": false,
  "engine_version": "1.0.0",
  "message": "3년 백테스트 완료"
}
```

### 핵심 필드 설명

#### `risk_metrics` (최상위 - 손실/회복 지표)
| 필드 | 설명 | 단위 |
|------|------|------|
| `max_drawdown` | 최대 낙폭 (MDD) - 고점 대비 최대 하락폭 | % |
| `max_recovery_days` | 최대 회복 기간 - 낙폭 후 원금 회복까지 일수 | 일 |
| `worst_1m_return` | 최악의 1개월 수익률 | % |
| `worst_3m_return` | 최악의 3개월 수익률 | % |
| `volatility` | 연간 변동성 (표준편차 × √252) | % |

#### `historical_observation` (참고용 - 과거 수익률)
| 필드 | 설명 | 단위 |
|------|------|------|
| `total_return` | 총 수익률 | % |
| `cagr` | 연평균 복합 성장률 | % |
| `sharpe_ratio` | 샤프 비율 (위험 조정 수익) | - |

#### 재현성 관련 필드
| 필드 | 설명 |
|------|------|
| `request_hash` | 요청의 SHA-256 해시 (64자리) |
| `cache_hit` | 캐시 적중 여부 (true/false) |
| `engine_version` | 시뮬레이션 엔진 버전 |

---

## 2. GET /backtest/metrics/{investment_type}

### 요청 예시
```
GET /backtest/metrics/conservative?period_years=1
```

### 응답 예시
```json
{
  "investment_type": "conservative",
  "period_years": 1,
  "engine_version": "1.0.0",

  "risk_metrics": {
    "max_drawdown": 8.5,
    "max_recovery_days": 32,
    "worst_1m_return": -4.2,
    "worst_3m_return": -6.8,
    "volatility": 9.2
  },

  "historical_observation": {
    "total_return": 5.2,
    "cagr": 5.2,
    "sharpe_ratio": 0.85
  }
}
```

---

## 3. POST /backtest/compare

### 요청 예시
```json
{
  "investment_types": ["conservative", "moderate", "aggressive"],
  "investment_amount": 10000000,
  "period_years": 3
}
```

### 응답 예시
```json
{
  "success": true,
  "data": {
    "comparison": [
      {
        "portfolio_name": "안정형",
        "max_drawdown": 8.5,
        "volatility": 9.2,
        "sharpe_ratio": 0.85,
        "total_return": 15.2,
        "annualized_return": 4.8
      },
      {
        "portfolio_name": "중립형",
        "max_drawdown": 15.3,
        "volatility": 14.5,
        "sharpe_ratio": 0.72,
        "total_return": 22.1,
        "annualized_return": 6.9
      },
      {
        "portfolio_name": "공격형",
        "max_drawdown": 25.8,
        "volatility": 22.3,
        "sharpe_ratio": 0.65,
        "total_return": 35.4,
        "annualized_return": 10.6
      }
    ],
    "lowest_risk": "안정형",
    "best_risk_adjusted": "안정형",
    "best_return": "공격형"
  },
  "request_hash": "b2c3d4e5f6g7...64자리",
  "cache_hit": false,
  "engine_version": "1.0.0",
  "message": "3개 포트폴리오 비교 완료"
}
```

---

## 4. GET /scenarios

### 응답 예시
```json
[
  {
    "id": "MIN_VOL",
    "name": "Minimum Volatility",
    "name_ko": "변동성 최소화",
    "short_description": "변동성 최소화를 통한 안정적 자산 운용 학습"
  },
  {
    "id": "DEFENSIVE",
    "name": "Defensive",
    "name_ko": "방어형",
    "short_description": "시장 하락 시 손실 최소화 전략 학습"
  },
  {
    "id": "GROWTH",
    "name": "Growth",
    "name_ko": "성장형",
    "short_description": "장기 자산 성장 전략 학습"
  }
]
```

---

## 5. GET /scenarios/{scenario_id}

### 응답 예시
```json
{
  "id": "MIN_VOL",
  "name": "Minimum Volatility",
  "name_ko": "변동성 최소화",
  "description": "변동성을 최소화하는 전략을 학습하기 위한 시나리오입니다.",
  "objective": "변동성 최소화를 통한 안정적 자산 운용 학습",
  "target_investor": "변동성에 민감하며 안정적인 자산 운용을 학습하고자 하는 분",

  "allocation": {
    "stocks": 15,
    "bonds": 45,
    "money_market": 25,
    "gold": 10,
    "other": 5
  },

  "risk_metrics": {
    "expected_volatility": "5-8% (연간)",
    "historical_max_drawdown": "8-12%",
    "recovery_expectation": "상대적으로 짧은 회복 기간 예상"
  },

  "disclaimer": "본 시나리오는 교육 목적의 학습 자료이며, 투자 권유가 아닙니다. 과거 데이터 기반 참고치이며 미래 성과를 보장하지 않습니다.",

  "learning_points": [
    "변동성과 위험의 관계 이해",
    "방어적 자산 배분의 원리",
    "안정성 중심 포트폴리오 구성 방법",
    "낮은 변동성이 장기 성과에 미치는 영향"
  ]
}
```

---

## 캐싱 동작

### 요청 해시 생성
- 알고리즘: SHA-256
- 입력: `{request_type}:{canonicalized_params}`
- 출력: 64자리 16진수 문자열

### 캐시 정책
- TTL: 7일
- 동일 요청 시 `cache_hit: true` 반환
- 엔진 버전이 캐시된 버전과 함께 반환

### 캐시 키 생성 예시
```python
# 입력
request_type = "backtest_simple"
request_params = {
    "investment_type": "moderate",
    "investment_amount": 10000000,
    "period_years": 3
}

# 정규화
canonical = '{"investment_amount":10000000,"investment_type":"moderate","period_years":3}'
hash_input = "backtest_simple:{"investment_amount":10000000,"investment_type":"moderate","period_years":3}"

# 해시
request_hash = sha256(hash_input.encode()).hexdigest()
# → "a1b2c3d4..."
```

---

## 버전 정보

| 항목 | 값 |
|------|-----|
| API 버전 | 1.0.0 |
| 엔진 버전 | 1.0.0 |
| 스냅샷 날짜 | 2026-01-15 |
| Phase | 0 (정렬 단계) |
