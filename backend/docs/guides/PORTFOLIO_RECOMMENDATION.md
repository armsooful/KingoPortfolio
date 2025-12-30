# 맞춤형 포트폴리오 추천 기능 가이드

## 목차

1. [개요](#개요)
2. [포트폴리오 엔진 아키텍처](#포트폴리오-엔진-아키텍처)
3. [자산 배분 전략](#자산-배분-전략)
4. [API 엔드포인트](#api-엔드포인트)
5. [포트폴리오 생성 알고리즘](#포트폴리오-생성-알고리즘)
6. [점수 계산 방식](#점수-계산-방식)
7. [사용 예제](#사용-예제)
8. [커스터마이징](#커스터마이징)

---

## 개요

맞춤형 포트폴리오 추천 기능은 사용자의 투자 성향 진단 결과를 기반으로 최적의 자산 배분과 상품을 추천하는 AI 기반 시스템입니다.

### 주요 특징

- **투자 성향 기반 추천**: 보수형, 중도형, 적극형 3가지 유형별 맞춤 전략
- **다양한 자산군**: 주식, ETF, 채권, 예금 상품을 균형있게 배분
- **리스크 관리**: 각 상품의 리스크 레벨을 고려한 포트폴리오 구성
- **성과 예측**: 기대 수익률과 리스크 지표 제공
- **맞춤 선호도**: 섹터, 배당, 리스크 선호도 반영

### 지원 기능

1. 기본 포트폴리오 생성 - 투자 성향과 금액만으로 자동 생성
2. 맞춤형 포트폴리오 생성 - 사용자 선호도를 추가 반영
3. 포트폴리오 리밸런싱 - 투자 금액 변경 시 재조정
4. 수익률 시뮬레이션 - 장기 투자 성과 예측
5. 자산 배분 전략 조회 - 투자 유형별 권장 비율 확인

---

## 포트폴리오 엔진 아키텍처

### 구조

```
PortfolioEngine (포트폴리오 엔진)
├── 자산 배분 전략 (ASSET_ALLOCATION_STRATEGIES)
│   ├── conservative (보수형)
│   ├── moderate (중도형)
│   └── aggressive (적극형)
│
├── 상품 선정 로직
│   ├── _select_stocks() - 주식 선정
│   ├── _select_etfs() - ETF 선정
│   ├── _select_bonds() - 채권 선정
│   └── _select_deposits() - 예금 선정
│
├── 점수 계산
│   ├── _calculate_stock_score() - 주식 점수
│   ├── _calculate_etf_score() - ETF 점수
│   ├── _calculate_bond_score() - 채권 점수
│   └── _calculate_deposit_score() - 예금 점수
│
└── 통계 및 추천
    ├── _calculate_statistics() - 포트폴리오 통계
    └── _generate_recommendations() - 개선 제안
```

### 주요 클래스

**PortfolioEngine** (`backend/app/services/portfolio_engine.py`)

```python
class PortfolioEngine:
    """포트폴리오 추천 엔진"""

    # 투자 성향별 자산 배분 전략
    ASSET_ALLOCATION_STRATEGIES = {
        "conservative": {...},  # 보수형
        "moderate": {...},      # 중도형
        "aggressive": {...}     # 적극형
    }

    # 리스크 점수 가중치
    RISK_SCORES = {
        "low": 1,
        "medium": 2,
        "high": 3
    }
```

**헬퍼 함수**

```python
def create_default_portfolio(
    db: Session,
    investment_type: str,
    investment_amount: int
) -> dict:
    """기본 포트폴리오 생성"""

def create_custom_portfolio(
    db: Session,
    investment_type: str,
    investment_amount: int,
    risk_tolerance: Optional[str] = None,
    sector_preferences: Optional[List[str]] = None,
    dividend_preference: Optional[bool] = None
) -> dict:
    """맞춤형 포트폴리오 생성"""
```

---

## 자산 배분 전략

### 보수형 (Conservative)

**특징**: 안정성 중시, 손실 최소화

```json
{
  "stocks": {
    "min": 10,
    "max": 30,
    "target": 20
  },
  "etfs": {
    "min": 10,
    "max": 20,
    "target": 15
  },
  "bonds": {
    "min": 30,
    "max": 45,
    "target": 35
  },
  "deposits": {
    "min": 25,
    "max": 35,
    "target": 30
  }
}
```

**권장 대상**:
- 투자 경험이 적은 초보자
- 손실을 견디기 어려운 투자자
- 안정적인 자산 보관이 목표인 투자자

**기대 수익률**: 연 4-5%

---

### 중도형 (Moderate)

**특징**: 안정성과 수익성의 균형

```json
{
  "stocks": {
    "min": 30,
    "max": 50,
    "target": 40
  },
  "etfs": {
    "min": 15,
    "max": 25,
    "target": 20
  },
  "bonds": {
    "min": 20,
    "max": 30,
    "target": 25
  },
  "deposits": {
    "min": 10,
    "max": 20,
    "target": 15
  }
}
```

**권장 대상**:
- 어느 정도 투자 경험이 있는 투자자
- 적정 수준의 리스크를 감수할 수 있는 투자자
- 자산 증식이 주 목표인 투자자

**기대 수익률**: 연 6-8%

---

### 적극형 (Aggressive)

**특징**: 높은 수익 추구, 리스크 감수

```json
{
  "stocks": {
    "min": 50,
    "max": 70,
    "target": 60
  },
  "etfs": {
    "min": 20,
    "max": 30,
    "target": 20
  },
  "bonds": {
    "min": 10,
    "max": 20,
    "target": 15
  },
  "deposits": {
    "min": 0,
    "max": 10,
    "target": 5
  }
}
```

**권장 대상**:
- 충분한 투자 경험이 있는 투자자
- 높은 변동성을 견딜 수 있는 투자자
- 장기적 고수익이 목표인 투자자

**기대 수익률**: 연 10-15%

---

## API 엔드포인트

### 1. 포트폴리오 생성

**Endpoint**: `POST /portfolio/generate`

**Request**:
```json
{
  "investment_amount": 10000000,
  "risk_tolerance": "medium",          // Optional
  "sector_preferences": ["전자", "IT"], // Optional
  "dividend_preference": true          // Optional
}
```

**Response**:
```json
{
  "investment_type": "moderate",
  "total_investment": 10000000,
  "allocation": {
    "stocks": {
      "ratio": 40.0,
      "amount": 4000000,
      "target": 40,
      "min": 30,
      "max": 50
    },
    "etfs": {...},
    "bonds": {...},
    "deposits": {...}
  },
  "portfolio": {
    "stocks": [
      {
        "ticker": "005930",
        "name": "삼성전자",
        "sector": "전자",
        "allocation_amount": 1500000,
        "allocation_ratio": 15.0,
        "current_price": 75000,
        "shares": 20,
        "score": 85.5,
        "risk_level": "medium",
        "expected_return": 12.5
      }
    ],
    "etfs": [...],
    "bonds": [...],
    "deposits": [...]
  },
  "statistics": {
    "total_investment": 10000000,
    "actual_invested": 9500000,
    "cash_reserve": 500000,
    "expected_annual_return": 7.8,
    "portfolio_risk": "medium",
    "diversification_score": 85,
    "total_items": 12,
    "asset_breakdown": {
      "stocks": 4,
      "etfs": 3,
      "bonds": 3,
      "deposits": 2
    }
  },
  "recommendations": [
    "포트폴리오가 적절히 분산되어 있습니다.",
    "기대 수익률이 목표 범위 내에 있습니다."
  ]
}
```

**Rate Limit**: 시간당 10회

---

### 2. 포트폴리오 리밸런싱

**Endpoint**: `POST /portfolio/rebalance/{diagnosis_id}`

**Query Parameters**:
- `investment_amount` (required): 새로운 투자 금액

**Response**: 포트폴리오 생성과 동일

**Rate Limit**: 시간당 100회

---

### 3. 자산 배분 전략 조회

**Endpoint**: `GET /portfolio/asset-allocation/{investment_type}`

**Path Parameters**:
- `investment_type`: `conservative`, `moderate`, `aggressive`

**Response**:
```json
{
  "investment_type": "moderate",
  "asset_allocation": {
    "stocks": {
      "min": 30,
      "max": 50,
      "target": 40
    },
    "etfs": {...},
    "bonds": {...},
    "deposits": {...}
  },
  "description": "중도형 - 안정성과 수익성의 균형"
}
```

---

### 4. 선택 가능한 섹터 조회

**Endpoint**: `GET /portfolio/available-sectors`

**Response**:
```json
{
  "sectors": [
    "전자/반도체",
    "자동차",
    "바이오/제약",
    "화학",
    "통신",
    "기타",
    "Technology",
    "Healthcare",
    "Financial Services"
  ],
  "total_count": 13
}
```

---

### 5. 수익률 시뮬레이션

**Endpoint**: `POST /portfolio/simulate`

**Query Parameters**:
- `investment_type` (required): 투자 성향
- `investment_amount` (required): 투자 금액
- `years` (optional, default=10): 투자 기간 (1-30년)

**Response**:
```json
{
  "investment_type": "moderate",
  "initial_investment": 10000000,
  "expected_annual_return": 7.5,
  "investment_years": 10,
  "final_value": 20610000,
  "total_profit": 10610000,
  "total_return_pct": 106.1,
  "yearly_projections": [
    {
      "year": 1,
      "value": 10750000,
      "profit": 750000,
      "total_return_pct": 7.5
    },
    {
      "year": 2,
      "value": 11556250,
      "profit": 1556250,
      "total_return_pct": 15.56
    },
    ...
  ]
}
```

**Rate Limit**: 시간당 100회

---

## 포트폴리오 생성 알고리즘

### 1. 투자 성향 확인

```python
# 진단 결과에서 투자 성향 가져오기
investment_type = diagnosis.investment_type  # conservative, moderate, aggressive
```

### 2. 자산 배분 계산

```python
def _calculate_allocation(strategy, total_amount):
    """전략에 따른 자산 배분 금액 계산"""
    allocation = {}

    for asset_class, config in strategy.items():
        ratio = config["target"]  # 목표 비율
        amount = int(total_amount * ratio / 100)

        allocation[asset_class] = {
            "ratio": ratio,
            "amount": amount,
            "min": config["min"],
            "max": config["max"],
            "target": config["target"]
        }

    return allocation
```

### 3. 상품 선정

각 자산군별로 점수 기반 상품 선정:

```python
def _select_stocks(db, allocation_amount, investment_type, preferences):
    """주식 선정"""

    # 1. 활성 상품 조회
    stocks = db.query(Stock).filter(Stock.is_active == True).all()

    # 2. 선호도 필터링
    if preferences.get("sector_preferences"):
        stocks = [s for s in stocks if s.sector in preferences["sector_preferences"]]

    # 3. 점수 계산 및 정렬
    scored_stocks = []
    for stock in stocks:
        score = _calculate_stock_score(stock, investment_type)
        scored_stocks.append((stock, score))

    scored_stocks.sort(key=lambda x: x[1], reverse=True)

    # 4. 상위 종목 선택 (3-5개)
    selected = scored_stocks[:5]

    # 5. 금액 배분
    return _allocate_amounts(selected, allocation_amount)
```

### 4. 통계 계산

```python
def _calculate_statistics(portfolio, allocation, total_investment):
    """포트폴리오 통계 계산"""

    # 실제 투자 금액
    actual_invested = sum(item["allocation_amount"] for items in portfolio.values() for item in items)

    # 현금 보유액
    cash_reserve = total_investment - actual_invested

    # 기대 수익률 (가중 평균)
    total_return = 0
    for items in portfolio.values():
        for item in items:
            weight = item["allocation_amount"] / actual_invested
            total_return += item.get("expected_return", 5.0) * weight

    # 리스크 레벨 (가중 평균)
    risk_scores = {"low": 1, "medium": 2, "high": 3}
    avg_risk_score = sum(
        risk_scores[item.get("risk_level", "medium")] * item["allocation_amount"]
        for items in portfolio.values()
        for item in items
    ) / actual_invested

    portfolio_risk = "low" if avg_risk_score < 1.5 else "medium" if avg_risk_score < 2.5 else "high"

    # 다각화 점수
    total_items = sum(len(items) for items in portfolio.values())
    diversification_score = min(100, total_items * 10 + len(portfolio) * 5)

    return {
        "total_investment": total_investment,
        "actual_invested": actual_invested,
        "cash_reserve": cash_reserve,
        "expected_annual_return": round(total_return, 2),
        "portfolio_risk": portfolio_risk,
        "diversification_score": diversification_score,
        "total_items": total_items
    }
```

### 5. 추천 생성

```python
def _generate_recommendations(investment_type, statistics):
    """개선 제안 생성"""
    recommendations = []

    # 현금 비율 체크
    cash_ratio = (statistics["cash_reserve"] / statistics["total_investment"]) * 100
    if cash_ratio > 15:
        recommendations.append(
            f"현금 {cash_ratio:.1f}%가 유휴 자금으로 남아있습니다. 추가 투자를 고려해보세요."
        )

    # 다각화 체크
    if statistics["diversification_score"] < 50:
        recommendations.append(
            "포트폴리오의 다각화가 부족합니다. 더 많은 종목에 분산 투자를 권장합니다."
        )

    # 수익률 체크
    expected_ranges = {
        "conservative": (4, 6),
        "moderate": (6, 9),
        "aggressive": (10, 15)
    }
    min_return, max_return = expected_ranges[investment_type]

    if statistics["expected_annual_return"] > max_return:
        recommendations.append(
            "기대 수익률이 높은 편입니다. 리스크가 적절한지 확인해보세요."
        )
    elif statistics["expected_annual_return"] < min_return:
        recommendations.append(
            "기대 수익률이 낮은 편입니다. 더 공격적인 자산을 추가해보세요."
        )

    return recommendations
```

---

## 점수 계산 방식

### 주식 점수

```python
def _calculate_stock_score(stock, investment_type):
    """주식 점수 계산 (0-100)"""
    score = 50  # 기본 점수

    # 1. 수익률 (+30점)
    if stock.one_year_return:
        if stock.one_year_return > 20:
            score += 30
        elif stock.one_year_return > 10:
            score += 20
        elif stock.one_year_return > 0:
            score += 10
        elif stock.one_year_return > -10:
            score += 5

    # 2. 배당수익률 (+15점)
    if stock.dividend_yield:
        if stock.dividend_yield > 4:
            score += 15
        elif stock.dividend_yield > 2:
            score += 10
        elif stock.dividend_yield > 1:
            score += 5

    # 3. 밸류에이션 (+15점)
    if stock.pe_ratio and stock.pb_ratio:
        if stock.pe_ratio < 15 and stock.pb_ratio < 1.5:
            score += 15
        elif stock.pe_ratio < 20 and stock.pb_ratio < 2:
            score += 10
        elif stock.pe_ratio < 30:
            score += 5

    # 4. 리스크 조정 (-10 ~ +10점)
    risk_adjustment = {
        "conservative": {"low": 10, "medium": 0, "high": -10},
        "moderate": {"low": 5, "medium": 10, "high": 5},
        "aggressive": {"low": -5, "medium": 5, "high": 10}
    }
    score += risk_adjustment[investment_type].get(stock.risk_level, 0)

    return min(100, max(0, score))
```

### ETF 점수

```python
def _calculate_etf_score(etf, investment_type):
    """ETF 점수 계산 (0-100)"""
    score = 50

    # 수익률
    if etf.one_year_return and etf.one_year_return > 10:
        score += 20

    # 운용 규모 (AUM)
    if etf.aum and etf.aum > 100000:  # 1000억 이상
        score += 15

    # 수수료율 (낮을수록 좋음)
    if etf.expense_ratio and etf.expense_ratio < 0.5:
        score += 15

    return min(100, max(0, score))
```

### 채권 점수

```python
def _calculate_bond_score(bond, investment_type):
    """채권 점수 계산 (0-100)"""
    score = 50

    # 금리
    if bond.interest_rate > 5:
        score += 20
    elif bond.interest_rate > 3:
        score += 10

    # 신용등급
    rating_scores = {"AAA": 20, "AA": 15, "A": 10, "BBB": 5}
    score += rating_scores.get(bond.credit_rating, 0)

    # 투자 성향 매칭
    if investment_type == "conservative" and bond.bond_type == "government":
        score += 10

    return min(100, max(0, score))
```

### 예금 점수

```python
def _calculate_deposit_score(deposit, investment_type):
    """예금 점수 계산 (0-100)"""
    score = 50

    # 금리
    if deposit.interest_rate > 4:
        score += 30
    elif deposit.interest_rate > 3:
        score += 20
    elif deposit.interest_rate > 2:
        score += 10

    # 보수형일수록 예금 선호
    if investment_type == "conservative":
        score += 20
    elif investment_type == "moderate":
        score += 10

    return min(100, max(0, score))
```

---

## 사용 예제

### 예제 1: 기본 포트폴리오 생성

```python
from app.services.portfolio_engine import create_default_portfolio

# 1000만원, 중도형 포트폴리오 생성
portfolio = create_default_portfolio(
    db=db,
    investment_type="moderate",
    investment_amount=10000000
)

print(f"총 투자액: {portfolio['total_investment']:,}원")
print(f"기대 수익률: {portfolio['statistics']['expected_annual_return']}%")
print(f"리스크: {portfolio['statistics']['portfolio_risk']}")
```

### 예제 2: 맞춤형 포트폴리오 (섹터 선호도)

```python
from app.services.portfolio_engine import create_custom_portfolio

# IT, 전자 섹터 선호, 배당 중시
portfolio = create_custom_portfolio(
    db=db,
    investment_type="moderate",
    investment_amount=10000000,
    sector_preferences=["Technology", "전자/반도체"],
    dividend_preference=True
)
```

### 예제 3: API 호출 (cURL)

```bash
# 1. 로그인
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com", "password":"password"}' \
  | jq -r '.access_token')

# 2. 포트폴리오 생성
curl -X POST http://localhost:8000/portfolio/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "investment_amount": 10000000,
    "sector_preferences": ["전자", "바이오"],
    "dividend_preference": true
  }' | jq .

# 3. 수익률 시뮬레이션
curl -X POST "http://localhost:8000/portfolio/simulate?investment_type=moderate&investment_amount=10000000&years=10" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

### 예제 4: Python 클라이언트

```python
import requests

BASE_URL = "http://localhost:8000"

# 로그인
response = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": "user@test.com", "password": "password"}
)
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 포트폴리오 생성
response = requests.post(
    f"{BASE_URL}/portfolio/generate",
    headers=headers,
    json={
        "investment_amount": 10000000,
        "risk_tolerance": "medium",
        "sector_preferences": ["전자", "IT"],
        "dividend_preference": True
    }
)

portfolio = response.json()
print(f"기대 수익률: {portfolio['statistics']['expected_annual_return']}%")
print(f"주식 {len(portfolio['portfolio']['stocks'])}개")
print(f"ETF {len(portfolio['portfolio']['etfs'])}개")
```

---

## 커스터마이징

### 자산 배분 전략 수정

[portfolio_engine.py](../app/services/portfolio_engine.py#L20-L59) 파일에서 수정:

```python
ASSET_ALLOCATION_STRATEGIES = {
    "conservative": {
        "stocks": {"min": 10, "max": 30, "target": 20},
        "etfs": {"min": 10, "max": 20, "target": 15},
        "bonds": {"min": 30, "max": 45, "target": 35},
        "deposits": {"min": 25, "max": 35, "target": 30}
    },
    # 새로운 전략 추가
    "super_aggressive": {
        "stocks": {"min": 70, "max": 90, "target": 80},
        "etfs": {"min": 10, "max": 20, "target": 15},
        "bonds": {"min": 0, "max": 10, "target": 5},
        "deposits": {"min": 0, "max": 5, "target": 0}
    }
}
```

### 점수 계산 가중치 조정

```python
def _calculate_stock_score(self, stock, investment_type):
    score = 50

    # 수익률 가중치 증가 (30 → 40점)
    if stock.one_year_return:
        if stock.one_year_return > 20:
            score += 40  # 변경
        elif stock.one_year_return > 10:
            score += 25  # 변경

    # ... 나머지 로직
```

### 새로운 자산군 추가

1. 모델 추가 (`models/securities.py`):
```python
class RealEstate(Base):
    """부동산"""
    __tablename__ = "real_estates"
    # ... 컬럼 정의
```

2. 전략에 추가 (`portfolio_engine.py`):
```python
ASSET_ALLOCATION_STRATEGIES = {
    "moderate": {
        "stocks": {"min": 30, "max": 40, "target": 35},
        "real_estate": {"min": 10, "max": 20, "target": 15},  # 추가
        # ...
    }
}
```

3. 선정 함수 추가:
```python
def _select_real_estates(self, db, allocation_amount, investment_type):
    # 부동산 선정 로직
    pass
```

### 추천 로직 커스터마이징

```python
def _generate_recommendations(self, investment_type, statistics):
    recommendations = []

    # 커스텀 추천 로직
    if statistics["total_items"] > 20:
        recommendations.append(
            "포트폴리오가 너무 복잡합니다. 관리가 쉬운 10-15개 종목으로 축소를 권장합니다."
        )

    # ESG 점수 추가 (향후)
    if hasattr(statistics, "esg_score") and statistics["esg_score"] < 50:
        recommendations.append(
            "ESG 점수가 낮습니다. 친환경·사회책임 투자 종목을 추가해보세요."
        )

    return recommendations
```

---

## 문제 해결

### Q1. 포트폴리오 생성 시 상품이 부족한 경우

**원인**: DB에 활성 상품이 충분하지 않음

**해결**:
```bash
# 관리자 API로 데이터 수집
curl -X POST http://localhost:8000/admin/collect-all-data \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Q2. 기대 수익률이 비정상적으로 높은 경우

**원인**: 일부 상품의 과거 수익률이 과도하게 높음

**해결**:
```python
# 수익률 상한선 적용
expected_return = min(item.get("one_year_return", 5.0), 30.0)  # 최대 30%
```

### Q3. 투자 금액이 너무 작아서 배분이 안 되는 경우

**원인**: 최소 투자 금액 미달

**해결**:
- 최소 권장 금액: 100만원 이상
- 소액일 경우 ETF 또는 예금 위주로 구성

---

## 성능 최적화

### 1. 쿼리 최적화

```python
# Before (N+1 쿼리)
stocks = db.query(Stock).filter(Stock.is_active == True).all()
for stock in stocks:
    score = calculate_score(stock)

# After (한 번에 조회)
stocks = db.query(Stock).filter(
    Stock.is_active == True,
    Stock.one_year_return.isnot(None)
).order_by(Stock.one_year_return.desc()).limit(100).all()
```

### 2. 캐싱

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_asset_allocation_strategy(investment_type: str):
    """자산 배분 전략 캐싱"""
    return ASSET_ALLOCATION_STRATEGIES[investment_type]
```

### 3. 비동기 처리

```python
import asyncio

async def generate_portfolio_async(db, investment_type, amount):
    """비동기 포트폴리오 생성"""
    tasks = [
        asyncio.create_task(select_stocks_async(db, ...)),
        asyncio.create_task(select_etfs_async(db, ...)),
        asyncio.create_task(select_bonds_async(db, ...))
    ]

    results = await asyncio.gather(*tasks)
    return combine_results(results)
```

---

## 관련 문서

- [투자 성향 진단 가이드](./DIAGNOSIS.md)
- [재무 분석 가이드](./FINANCIAL_ANALYSIS.md)
- [데이터 수집 가이드](./DATA_COLLECTION.md)
- [API 레퍼런스](../api/README.md)

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0.0 | 2025-12-30 | 초기 버전 작성 |

---

## 라이선스

MIT License - KingoPortfolio Team
