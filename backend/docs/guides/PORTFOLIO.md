# 포트폴리오 추천 시스템 가이드

**마지막 업데이트**: 2025-12-29
**버전**: 1.0.0

---

## 📋 목차

1. [개요](#개요)
2. [주요 기능](#주요-기능)
3. [포트폴리오 생성](#포트폴리오-생성)
4. [API 엔드포인트](#api-엔드포인트)
5. [자산 배분 전략](#자산-배분-전략)
6. [종목 선정 알고리즘](#종목-선정-알고리즘)
7. [예제 코드](#예제-코드)
8. [문제 해결](#문제-해결)
9. [관련 문서](#관련-문서)

---

## 개요

KingoPortfolio의 포트폴리오 추천 시스템은 사용자의 투자 성향과 주식 종목 분석 데이터를 기반으로 최적의 포트폴리오를 자동으로 생성합니다.

### 핵심 특징

- 🎯 **투자 성향 기반** - 보수형, 중도형, 적극형에 맞춘 자산 배분
- 📊 **다각화 전략** - 주식, ETF, 채권, 예금으로 리스크 분산
- 🔍 **데이터 기반 선정** - 재무 지표, 수익률, 밸류에이션 분석
- 📈 **실시간 리밸런싱** - 투자 금액 변경 시 포트폴리오 재조정
- 💡 **맞춤형 추천** - 섹터 선호도, 배당 선호도 반영

---

## 주요 기능

### 1. 기본 포트폴리오 생성

투자 성향만으로 간단하게 포트폴리오를 생성합니다.

```python
from app.services.portfolio_engine import create_default_portfolio
from app.database import get_db

portfolio = create_default_portfolio(
    db=next(get_db()),
    investment_type="moderate",  # conservative, moderate, aggressive
    investment_amount=10000000    # 1천만원
)
```

### 2. 맞춤형 포트폴리오 생성

사용자의 선호도를 반영한 포트폴리오를 생성합니다.

```python
from app.services.portfolio_engine import create_custom_portfolio

portfolio = create_custom_portfolio(
    db=next(get_db()),
    investment_type="moderate",
    investment_amount=10000000,
    risk_tolerance="medium",               # 리스크 허용도
    sector_preferences=["전자", "금융"],    # 선호 섹터
    dividend_preference=True                # 배당 선호
)
```

### 3. 포트폴리오 리밸런싱

기존 포트폴리오의 투자 금액을 변경하여 재조정합니다.

```python
# API 호출을 통한 리밸런싱
POST /portfolio/rebalance/{diagnosis_id}
{
    "investment_amount": 15000000
}
```

### 4. 수익률 시뮬레이션

장기 투자 시 예상 수익을 계산합니다.

```python
# 10년 투자 시뮬레이션
POST /portfolio/simulate
{
    "investment_type": "moderate",
    "investment_amount": 10000000,
    "years": 10
}
```

---

## 포트폴리오 생성

### 생성 프로세스

```
1. 투자 성향 확인
   ↓
2. 자산 배분 전략 선택
   ↓
3. 각 자산군별 종목 선정
   ├─ 주식: 점수 기반 상위 종목
   ├─ ETF: 수익률 및 AUM 고려
   ├─ 채권: 금리 및 신용도 평가
   └─ 예금: 최고 금리 상품
   ↓
4. 금액 배분
   ↓
5. 포트폴리오 통계 계산
   ↓
6. 개선 추천 생성
```

### 생성 결과

포트폴리오 생성 결과는 다음 정보를 포함합니다:

```json
{
    "investment_type": "moderate",
    "total_investment": 10000000,
    "allocation": {
        "stocks": {"ratio": 40, "amount": 4000000, "min_ratio": 30, "max_ratio": 50},
        "etfs": {"ratio": 20, "amount": 2000000, "min_ratio": 15, "max_ratio": 25},
        "bonds": {"ratio": 25, "amount": 2500000, "min_ratio": 20, "max_ratio": 30},
        "deposits": {"ratio": 15, "amount": 1500000, "min_ratio": 10, "max_ratio": 20}
    },
    "portfolio": {
        "stocks": [...],   // 선정된 주식 목록
        "etfs": [...],     // 선정된 ETF 목록
        "bonds": [...],    // 선정된 채권 목록
        "deposits": [...]  // 선정된 예금 목록
    },
    "statistics": {
        "total_investment": 10000000,
        "actual_invested": 9800000,
        "cash_reserve": 200000,
        "expected_annual_return": 7.5,
        "portfolio_risk": "medium",
        "diversification_score": 80,
        "total_items": 8
    },
    "recommendations": [
        "잘 구성된 포트폴리오입니다. 정기적으로 리밸런싱을 진행하세요."
    ]
}
```

---

## API 엔드포인트

### 1. 포트폴리오 생성

**POST** `/portfolio/generate`

투자 성향에 맞는 포트폴리오를 생성합니다.

#### 요청 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| investment_amount | integer | O | 투자 금액 (최소 10,000원) |
| diagnosis_id | string | X | 진단 ID (없으면 최신 진단 사용) |
| risk_tolerance | string | X | 리스크 허용도 (low, medium, high) |
| sector_preferences | array | X | 선호 섹터 목록 |
| dividend_preference | boolean | X | 배당 선호 여부 |

#### 요청 예제

```bash
curl -X POST "http://localhost:8000/portfolio/generate" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "investment_amount": 10000000,
    "risk_tolerance": "medium",
    "sector_preferences": ["전자", "금융"],
    "dividend_preference": true
  }'
```

#### 응답 예제

```json
{
    "investment_type": "moderate",
    "total_investment": 10000000,
    "allocation": {...},
    "portfolio": {...},
    "statistics": {...},
    "recommendations": [...]
}
```

### 2. 포트폴리오 리밸런싱

**POST** `/portfolio/rebalance/{diagnosis_id}`

기존 진단 결과를 기반으로 새로운 투자 금액에 맞춰 포트폴리오를 재조정합니다.

#### URL 파라미터

- `diagnosis_id`: 진단 ID

#### 요청 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| investment_amount | integer | O | 새로운 투자 금액 |

#### 요청 예제

```bash
curl -X POST "http://localhost:8000/portfolio/rebalance/diag_123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "investment_amount": 15000000
  }'
```

### 3. 자산 배분 전략 조회

**GET** `/portfolio/asset-allocation/{investment_type}`

투자 성향별 권장 자산 배분 비율을 조회합니다.

#### URL 파라미터

- `investment_type`: 투자 성향 (conservative, moderate, aggressive)

#### 요청 예제

```bash
curl "http://localhost:8000/portfolio/asset-allocation/moderate" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### 응답 예제

```json
{
    "investment_type": "moderate",
    "asset_allocation": {
        "stocks": {"min": 30, "max": 50, "target": 40},
        "etfs": {"min": 15, "max": 25, "target": 20},
        "bonds": {"min": 20, "max": 30, "target": 25},
        "deposits": {"min": 10, "max": 20, "target": 15}
    },
    "description": "중도형 - 안정성과 수익성의 균형"
}
```

### 4. 선택 가능한 섹터 조회

**GET** `/portfolio/available-sectors`

포트폴리오 생성 시 선택 가능한 섹터 목록을 반환합니다.

#### 요청 예제

```bash
curl "http://localhost:8000/portfolio/available-sectors" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### 응답 예제

```json
{
    "sectors": ["전자", "금융", "자동차", "바이오", "화학"],
    "total_count": 5
}
```

### 5. 수익률 시뮬레이션

**POST** `/portfolio/simulate`

주어진 투자 기간 동안의 예상 수익률과 자산 가치를 시뮬레이션합니다.

#### 요청 파라미터

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|----------|------|------|--------|------|
| investment_type | string | O | - | 투자 성향 |
| investment_amount | integer | O | - | 투자 금액 |
| years | integer | X | 10 | 투자 기간 (1-30년) |

#### 요청 예제

```bash
curl -X POST "http://localhost:8000/portfolio/simulate" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "investment_type": "moderate",
    "investment_amount": 10000000,
    "years": 10
  }'
```

#### 응답 예제

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
        {"year": 1, "value": 10750000, "profit": 750000, "total_return_pct": 7.5},
        {"year": 2, "value": 11556250, "profit": 1556250, "total_return_pct": 15.56},
        ...
    ]
}
```

---

## 자산 배분 전략

### 1. 보수형 (Conservative)

**투자 성향**: 안정성 중시, 손실 최소화

**자산 배분**:
- 주식: 10-30% (목표: 20%)
- ETF: 10-20% (목표: 15%)
- 채권: 30-45% (목표: 35%)
- 예금: 25-35% (목표: 30%)

**특징**:
- 낮은 변동성
- 안정적인 수익
- 원금 보존 우선

**기대 수익률**: 연 4-6%

### 2. 중도형 (Moderate)

**투자 성향**: 안정성과 수익성의 균형

**자산 배분**:
- 주식: 30-50% (목표: 40%)
- ETF: 15-25% (목표: 20%)
- 채권: 20-30% (목표: 25%)
- 예금: 10-20% (목표: 15%)

**특징**:
- 적정 수준의 위험
- 균형잡힌 포트폴리오
- 중기 투자 적합

**기대 수익률**: 연 6-9%

### 3. 적극형 (Aggressive)

**투자 성향**: 높은 수익 추구, 리스크 감수

**자산 배분**:
- 주식: 50-70% (목표: 60%)
- ETF: 15-25% (목표: 20%)
- 채권: 10-20% (목표: 15%)
- 예금: 0-10% (목표: 5%)

**특징**:
- 높은 변동성
- 공격적인 수익 추구
- 장기 투자 적합

**기대 수익률**: 연 9-15%

---

## 종목 선정 알고리즘

### 주식 선정 기준

포트폴리오 엔진은 다음 기준으로 주식을 점수화합니다 (0-100점):

#### 1. 성과 점수 (40점)
- 1년 수익률 (20점)
  - 20% 이상: 20점
  - 10-20%: 15점
  - 0-10%: 10점
  - 마이너스: 5점

- YTD 수익률 (20점)
  - 15% 이상: 15점
  - 5-15%: 10점
  - 0-5%: 5점

#### 2. 밸류에이션 점수 (30점)
- PER (15점)
  - 10-15: 15점 (이상적)
  - 5-10 또는 15-20: 10점
  - 기타: 5점

- PBR (15점)
  - 0.8-1.5: 15점 (이상적)
  - 0.5-0.8 또는 1.5-2.5: 10점
  - 기타: 5점

#### 3. 배당 점수 (20-30점)
- 보수형: 30점
- 중도형/적극형: 20점

배당 수익률:
- 4% 이상: 최대 점수
- 2-4%: 60%
- 0-2%: 30%

#### 4. 리스크 조정 (10점)
투자 성향에 맞는 리스크 레벨:
- 보수형: low → 10점
- 중도형: medium → 10점
- 적극형: high → 10점

### ETF 선정 기준

#### 1. 성과 (25점)
- 1년 수익률
  - 15% 이상: 25점
  - 8-15%: 20점
  - 0-8%: 10점

#### 2. 운용 규모 (15점)
- 1조 이상: 15점
- 1000억 이상: 10점
- 기타: 5점

#### 3. 수수료 (10점)
- 0.1% 미만: 10점
- 0.1-0.3%: 7점
- 0.3% 이상: 3점

### 채권 선정 기준

- 금리 높은 순
- 신용등급 고려 (AAA, AA 우선)
- 투자 성향에 맞는 채권 타입

### 예금 선정 기준

- 최고 금리 상품
- 예금자 보호 대상
- 유동성 확보

---

## 예제 코드

### Python (Backend)

#### 기본 포트폴리오 생성

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.portfolio_engine import create_default_portfolio

def generate_basic_portfolio(
    investment_type: str,
    amount: int,
    db: Session = Depends(get_db)
):
    """기본 포트폴리오 생성"""
    portfolio = create_default_portfolio(
        db=db,
        investment_type=investment_type,
        investment_amount=amount
    )

    print(f"투자 성향: {portfolio['investment_type']}")
    print(f"총 투자액: {portfolio['total_investment']:,}원")
    print(f"기대 수익률: {portfolio['statistics']['expected_annual_return']}%")
    print(f"선정 종목 수: {portfolio['statistics']['total_items']}개")

    return portfolio
```

#### 맞춤형 포트폴리오 생성

```python
from app.services.portfolio_engine import create_custom_portfolio

def generate_custom_portfolio(
    investment_type: str,
    amount: int,
    db: Session
):
    """맞춤형 포트폴리오 생성"""
    portfolio = create_custom_portfolio(
        db=db,
        investment_type=investment_type,
        investment_amount=amount,
        risk_tolerance="medium",
        sector_preferences=["전자", "금융", "바이오"],
        dividend_preference=True
    )

    # 주식 목록 출력
    for stock in portfolio['portfolio']['stocks']:
        print(f"- {stock['name']}: {stock['shares']}주 ({stock['invested_amount']:,}원)")

    return portfolio
```

### JavaScript (Frontend)

#### 포트폴리오 생성 API 호출

```javascript
async function generatePortfolio(investmentAmount, diagnosisId) {
    const response = await fetch('/portfolio/generate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            investment_amount: investmentAmount,
            diagnosis_id: diagnosisId,
            risk_tolerance: 'medium',
            sector_preferences: ['전자', '금융'],
            dividend_preference: true
        })
    });

    const portfolio = await response.json();
    console.log('포트폴리오 생성 완료:', portfolio);

    return portfolio;
}
```

#### 포트폴리오 리밸런싱

```javascript
async function rebalancePortfolio(diagnosisId, newAmount) {
    const response = await fetch(`/portfolio/rebalance/${diagnosisId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            investment_amount: newAmount
        })
    });

    const rebalanced = await response.json();
    displayPortfolio(rebalanced);
}
```

#### 수익률 시뮬레이션

```javascript
async function simulateReturns(investmentType, amount, years = 10) {
    const response = await fetch('/portfolio/simulate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            investment_type: investmentType,
            investment_amount: amount,
            years: years
        })
    });

    const simulation = await response.json();

    // 연도별 수익 그래프 표시
    displayChart(simulation.yearly_projections);

    return simulation;
}
```

---

## 문제 해결

### 포트폴리오가 생성되지 않아요

**문제**: 포트폴리오 생성 API가 실패합니다.

**원인**:
1. 진단을 먼저 완료하지 않음
2. 최소 투자 금액 미만 (10,000원)
3. DB에 종목 데이터가 없음

**해결**:
1. 진단 먼저 완료: `POST /diagnosis/submit`
2. 투자 금액 확인: 최소 10,000원 이상
3. 관리자가 데이터 수집 실행

```bash
# 진단 완료 후 포트폴리오 생성
POST /diagnosis/submit  # 먼저
POST /portfolio/generate  # 그 다음
```

### 선정된 종목이 너무 적어요

**문제**: 포트폴리오에 종목이 2-3개밖에 없습니다.

**원인**:
1. 투자 금액이 적음
2. DB에 해당 투자 성향의 종목이 부족
3. 선호 섹터가 너무 제한적

**해결**:
1. 투자 금액 증액 (500만원 이상 권장)
2. 관리자가 더 많은 종목 데이터 수집
3. 선호 섹터 조건 완화

### 기대 수익률이 낮아요

**문제**: 포트폴리오의 기대 수익률이 목표보다 낮습니다.

**원인**:
1. 보수형 성향이라 낮은 수익률 상품 위주
2. 현재 시장 상황이 좋지 않음
3. 안전 자산(채권, 예금) 비중이 높음

**해결**:
1. 투자 성향 재진단 (더 적극적으로)
2. 리밸런싱: 주식 비중 증가
3. 맞춤형 설정으로 고수익 섹터 선호

```json
{
    "risk_tolerance": "high",
    "sector_preferences": ["IT", "바이오"],
    "dividend_preference": false
}
```

### 리밸런싱이 제대로 안 돼요

**문제**: 리밸런싱 후에도 포트폴리오가 비슷합니다.

**원인**:
1. 투자 금액 변화가 작음
2. 동일한 투자 성향 사용

**해결**:
1. 투자 금액을 크게 변경 (50% 이상)
2. 새로운 진단으로 다른 성향 적용
3. 맞춤형 설정으로 선호도 변경

### Rate Limit 에러 발생

**문제**: `429 Too Many Requests` 에러

**원인**: 포트폴리오 생성을 시간당 10회 초과

**해결**:
```
1. 1시간 대기
2. 프리미엄 계정으로 업그레이드 (향후)
3. 생성된 포트폴리오 저장 후 재사용
```

---

## 관련 문서

### 가이드 문서
- [진단 가이드](DIAGNOSIS.md) - 투자 성향 진단 방법
- [데이터 내보내기](EXPORT.md) - 포트폴리오 CSV/Excel 다운로드
- [Rate Limiting](RATE_LIMITING.md) - API 사용 제한

### 기술 레퍼런스
- [API 문서](../reference/API_DOCUMENTATION.md) - 전체 API 명세
- [에러 핸들링](../reference/ERROR_HANDLING.md) - 에러 코드 및 처리

### 개발 문서
- [테스트 가이드](../development/TESTING.md) - 포트폴리오 테스트 실행

---

## 참고 자료

### 금융 이론
- [Modern Portfolio Theory (MPT)](https://en.wikipedia.org/wiki/Modern_portfolio_theory) - 현대 포트폴리오 이론
- [Asset Allocation](https://www.investopedia.com/terms/a/assetallocation.asp) - 자산 배분 전략
- [Diversification](https://www.investopedia.com/terms/d/diversification.asp) - 분산 투자

### 밸류에이션
- [PER (Price-to-Earnings Ratio)](https://www.investopedia.com/terms/p/price-earningsratio.asp)
- [PBR (Price-to-Book Ratio)](https://www.investopedia.com/terms/p/price-to-bookratio.asp)
- [Dividend Yield](https://www.investopedia.com/terms/d/dividendyield.asp)

---

## 통계

### 코드 통계
- **엔진 코드**: 228줄 (portfolio_engine.py)
- **API 엔드포인트**: 5개
- **테스트**: 15개 (12 통과, 3 스킵)
- **코드 커버리지**: 47%

### 포트폴리오 메트릭
- **투자 성향**: 3가지 (conservative, moderate, aggressive)
- **자산군**: 4가지 (stocks, etfs, bonds, deposits)
- **평가 지표**: 10+ (PER, PBR, 배당률, 수익률 등)
- **점수 범위**: 0-100점

---

**작성자**: Backend Team
**마지막 업데이트**: 2025-12-29
**버전**: 1.0.0
