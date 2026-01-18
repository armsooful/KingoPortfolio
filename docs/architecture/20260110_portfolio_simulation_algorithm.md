# 포트폴리오 시뮬레이션 알고리즘 구현 가이드 (교육용)
최초작성일자: 2026-01-10
최종수정일자: 2026-01-18

⚠️ **중요**: 본 문서는 교육 목적의 시뮬레이션 알고리즘을 설명합니다.
투자 권유·추천·자문·일임 서비스가 아닙니다.

## 1. 전체 구조

```
설문 결과 → 투자 성향 분석 → 전략 유형 매핑 → 샘플 종목 추출 → 비중 계산 → 시뮬레이션 결과
```

## 2. 투자 성향별 전략 매핑

### 위험 성향 5단계 분류
```python
RISK_PROFILES = {
    "매우_보수적": {
        "주식_비중": 20,
        "현금_채권_비중": 80,
        "종목_수": 5,
        "선호_섹터": ["금융", "필수소비재", "유틸리티"],
        "시가총액": "대형주",  # 1조 이상
        "배당수익률_최소": 2.5
    },
    "보수적": {
        "주식_비중": 40,
        "현금_채권_비중": 60,
        "종목_수": 7,
        "선호_섹터": ["금융", "필수소비재", "헬스케어", "산업재"],
        "시가총액": "대형주",
        "배당수익률_최소": 2.0
    },
    "중립적": {
        "주식_비중": 60,
        "현금_채권_비중": 40,
        "종목_수": 10,
        "선호_섹터": ["IT", "금융", "산업재", "헬스케어", "소비재"],
        "시가총액": "대형+중형",
        "배당수익률_최소": 1.5
    },
    "공격적": {
        "주식_비중": 80,
        "현금_채권_비중": 20,
        "종목_수": 12,
        "선호_섹터": ["IT", "바이오", "2차전지", "반도체"],
        "시가총액": "대형+중형+중소형",
        "성장성_중시": True
    },
    "매우_공격적": {
        "주식_비중": 100,
        "현금_채권_비중": 0,
        "종목_수": 15,
        "선호_섹터": ["IT", "바이오", "2차전지", "게임", "엔터"],
        "시가총액": "전체",
        "고변동성_허용": True
    }
}
```

## 3. 종목 선정 알고리즘

### A. 필터링 단계

```python
def filter_stocks(all_stocks, risk_profile):
    """
    1단계: 기본 필터링
    """
    filtered = []
    
    for stock in all_stocks:
        # 1. 시가총액 필터
        if not meets_market_cap(stock, risk_profile["시가총액"]):
            continue
            
        # 2. 유동성 필터 (일평균 거래대금)
        if stock["avg_trading_volume"] < 10_000_000_000:  # 100억 이상
            continue
            
        # 3. 배당 필터 (보수적 성향)
        if "배당수익률_최소" in risk_profile:
            if stock["dividend_yield"] < risk_profile["배당수익률_최소"]:
                continue
        
        # 4. 섹터 필터
        if stock["sector"] in risk_profile["선호_섹터"]:
            filtered.append(stock)
    
    return filtered
```

### B. 스코어링 단계

```python
def calculate_stock_score(stock, risk_profile):
    """
    2단계: 종목별 점수 계산
    """
    score = 0
    
    # 1. 모멘텀 점수 (최근 3개월 수익률)
    momentum_3m = stock["return_3month"]
    if 0 < momentum_3m < 20:  # 적정 상승
        score += 20
    elif momentum_3m > 50:  # 과열
        score -= 10
    
    # 2. 변동성 점수
    volatility = stock["volatility_60d"]
    if risk_profile.get("고변동성_허용"):
        # 공격적: 변동성 무관
        score += 10
    else:
        # 보수적: 낮은 변동성 선호
        if volatility < 15:
            score += 20
        elif volatility > 30:
            score -= 15
    
    # 3. 가치 점수 (PER, PBR)
    if stock["per"] > 0:
        if 5 < stock["per"] < 15:
            score += 15
        elif stock["per"] > 30:
            score -= 10
    
    # 4. 성장성 점수
    if risk_profile.get("성장성_중시"):
        if stock["revenue_growth"] > 20:
            score += 25
        if stock["profit_growth"] > 20:
            score += 20
    
    # 5. 재무건전성 점수
    if stock["debt_ratio"] < 100:
        score += 15
    
    # 6. 배당 점수
    if stock["dividend_yield"] > 3:
        score += 10
    
    return score
```

### C. 종목 선택

```python
def select_stocks(filtered_stocks, risk_profile):
    """
    3단계: 최종 종목 선정
    """
    # 점수 계산
    for stock in filtered_stocks:
        stock["score"] = calculate_stock_score(stock, risk_profile)
    
    # 점수 순 정렬
    sorted_stocks = sorted(filtered_stocks, key=lambda x: x["score"], reverse=True)
    
    # 상위 N개 선택
    num_stocks = risk_profile["종목_수"]
    selected = sorted_stocks[:num_stocks]
    
    # 섹터 다각화 체크 (한 섹터 30% 이하)
    selected = apply_sector_diversification(selected)
    
    return selected
```

## 4. 비중 계산 알고리즘

### A. 기본 균등 배분 (Simple)

```python
def equal_weight(selected_stocks):
    """
    가장 간단한 방법: 균등 배분
    """
    weight = 100 / len(selected_stocks)
    
    for stock in selected_stocks:
        stock["weight"] = round(weight, 2)
    
    return selected_stocks
```

### B. 점수 기반 배분 (Better)

```python
def score_based_weight(selected_stocks):
    """
    점수에 비례해서 배분
    """
    total_score = sum(stock["score"] for stock in selected_stocks)
    
    for stock in selected_stocks:
        stock["weight"] = round((stock["score"] / total_score) * 100, 2)
    
    # 최대/최소 제약
    for stock in selected_stocks:
        if stock["weight"] > 30:  # 한 종목 최대 30%
            stock["weight"] = 30
        if stock["weight"] < 5:   # 한 종목 최소 5%
            stock["weight"] = 5
    
    # 재조정
    total = sum(stock["weight"] for stock in selected_stocks)
    for stock in selected_stocks:
        stock["weight"] = round((stock["weight"] / total) * 100, 2)
    
    return selected_stocks
```

### C. 위험 기반 배분 (Advanced)

```python
def risk_parity_weight(selected_stocks):
    """
    각 종목이 포트폴리오 리스크에 동일하게 기여하도록
    """
    # 변동성의 역수로 가중치 계산
    inv_volatilities = [1 / stock["volatility_60d"] for stock in selected_stocks]
    total_inv_vol = sum(inv_volatilities)
    
    for i, stock in enumerate(selected_stocks):
        stock["weight"] = round((inv_volatilities[i] / total_inv_vol) * 100, 2)
    
    return selected_stocks
```

## 5. 실제 구현 예시 (FastAPI)

```python
# app/services/recommendation.py

from typing import List, Dict
from app.models.stock import Stock
from app.models.survey import SurveyResult

class PortfolioRecommendationService:
    
    def __init__(self, db_session):
        self.db = db_session
        self.risk_profiles = RISK_PROFILES
    
    def generate_recommendation(
        self, 
        survey_result: SurveyResult,
        investment_amount: int = 10_000_000
    ) -> Dict:
        """
        메인 추천 함수
        """
        # 1. 위험 성향 판단
        risk_level = self._determine_risk_level(survey_result)
        risk_profile = self.risk_profiles[risk_level]
        
        # 2. 전체 주식 데이터 로드
        all_stocks = self._load_stock_universe()
        
        # 3. 필터링
        filtered = self._filter_stocks(all_stocks, risk_profile)
        
        # 4. 스코어링 및 선정
        selected = self._select_stocks(filtered, risk_profile)
        
        # 5. 비중 계산
        portfolio = self._calculate_weights(selected, risk_profile)
        
        # 6. 금액 배분
        portfolio = self._allocate_amounts(portfolio, investment_amount)
        
        # 7. 포트폴리오 분석
        analysis = self._analyze_portfolio(portfolio)
        
        return {
            "risk_level": risk_level,
            "portfolio": portfolio,
            "analysis": analysis,
            "rebalancing_date": "3개월 후"
        }
    
    def _determine_risk_level(self, survey: SurveyResult) -> str:
        """
        15문항 점수 → 위험 성향 매핑
        """
        total_score = survey.total_score
        
        if total_score <= 30:
            return "매우_보수적"
        elif total_score <= 45:
            return "보수적"
        elif total_score <= 60:
            return "중립적"
        elif total_score <= 75:
            return "공격적"
        else:
            return "매우_공격적"
    
    def _load_stock_universe(self) -> List[Stock]:
        """
        DB에서 주식 데이터 로드
        """
        return self.db.query(Stock).filter(
            Stock.is_active == True
        ).all()
    
    def _filter_stocks(self, stocks, profile) -> List[Stock]:
        """필터링 로직"""
        # 위의 filter_stocks 함수 내용
        pass
    
    def _select_stocks(self, filtered, profile) -> List[Stock]:
        """선정 로직"""
        # 위의 select_stocks 함수 내용
        pass
    
    def _calculate_weights(self, selected, profile) -> List[Dict]:
        """비중 계산"""
        # 위험 성향에 따라 다른 방법 선택
        if profile["주식_비중"] <= 40:
            return risk_parity_weight(selected)
        else:
            return score_based_weight(selected)
    
    def _allocate_amounts(self, portfolio, total_amount) -> List[Dict]:
        """
        금액 배분 및 주식 수 계산
        """
        stock_amount = total_amount * (portfolio[0].get("주식_비중", 100) / 100)
        
        for stock in portfolio:
            allocated = stock_amount * (stock["weight"] / 100)
            shares = int(allocated / stock["current_price"])
            
            stock["allocated_amount"] = allocated
            stock["shares"] = shares
            stock["actual_amount"] = shares * stock["current_price"]
        
        return portfolio
    
    def _analyze_portfolio(self, portfolio) -> Dict:
        """
        포트폴리오 분석 지표 계산
        """
        total_value = sum(s["actual_amount"] for s in portfolio)
        
        # 예상 수익률 (과거 데이터 기반)
        expected_return = sum(
            s["expected_return"] * s["weight"] / 100 
            for s in portfolio
        )
        
        # 포트폴리오 변동성 (간단화)
        portfolio_volatility = (
            sum(s["volatility_60d"] * s["weight"] / 100 for s in portfolio)
        )
        
        # 섹터 분포
        sector_distribution = {}
        for stock in portfolio:
            sector = stock["sector"]
            sector_distribution[sector] = sector_distribution.get(sector, 0) + stock["weight"]
        
        return {
            "expected_annual_return": round(expected_return, 2),
            "portfolio_volatility": round(portfolio_volatility, 2),
            "sharpe_ratio": round(expected_return / portfolio_volatility, 2),
            "sector_distribution": sector_distribution,
            "num_stocks": len(portfolio),
            "total_value": total_value
        }
```

## 6. API 엔드포인트

```python
# app/api/recommendation.py

from fastapi import APIRouter, Depends
from app.services.recommendation import PortfolioRecommendationService

router = APIRouter()

@router.post("/recommend")
async def get_recommendation(
    survey_id: int,
    investment_amount: int = 10_000_000,
    service: PortfolioRecommendationService = Depends()
):
    """
    포트폴리오 추천 API
    """
    # 설문 결과 조회
    survey_result = service.get_survey_result(survey_id)
    
    # 추천 생성
    recommendation = service.generate_recommendation(
        survey_result, 
        investment_amount
    )
    
    return recommendation
```

## 7. MVP 단순 버전

처음에는 복잡한 계산 없이:

```python
def simple_mvp_recommendation(risk_level: str):
    """
    MVP용 초간단 버전
    """
    # 미리 정의된 템플릿 포트폴리오
    templates = {
        "보수적": [
            {"code": "005930", "name": "삼성전자", "weight": 20},
            {"code": "055550", "name": "신한지주", "weight": 20},
            {"code": "000660", "name": "SK하이닉스", "weight": 15},
            {"code": "005380", "name": "현대차", "weight": 15},
            {"code": "035420", "name": "NAVER", "weight": 15},
            {"code": "051910", "name": "LG화학", "weight": 15}
        ],
        "공격적": [
            {"code": "005930", "name": "삼성전자", "weight": 15},
            {"code": "000660", "name": "SK하이닉스", "weight": 15},
            {"code": "035720", "name": "카카오", "weight": 12},
            {"code": "035420", "name": "NAVER", "weight": 12},
            {"code": "373220", "name": "LG에너지솔루션", "weight": 12},
            {"code": "207940", "name": "삼성바이오로직스", "weight": 10},
            {"code": "006400", "name": "삼성SDI", "weight": 10},
            {"code": "068270", "name": "셀트리온", "weight": 14}
        ]
    }
    
    return templates.get(risk_level)
```

## 8. 개발 우선순위

### Phase 1: 기본 구현 (2주)
- 템플릿 기반 추천 (위의 simple_mvp_recommendation)
- 5가지 위험 성향별 미리 정의된 포트폴리오

### Phase 2: 동적 추천 (3주)
- 실시간 주식 데이터 기반 필터링
- 점수 계산 및 종목 선정

### Phase 3: 고도화 (4주)
- 최적화 알고리즘 (Modern Portfolio Theory)
- 백테스팅 및 성과 검증
- 개인화 요소 추가 (투자 기간, 목표 수익률 등)

## 결론

**즉시 시작**: Phase 1 템플릿 방식으로 빠르게 구현
**점진적 개선**: 데이터 쌓이면서 알고리즘 고도화

핵심은 "일단 작동하는 추천 시스템"을 만드는 것!
