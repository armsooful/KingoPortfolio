"""
포트폴리오 추천 엔진

투자 성향과 주식 종목 분석 데이터를 기반으로 최적의 포트폴리오를 추천합니다.
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from app.models.securities import Stock, ETF, Bond, DepositProduct
from app.diagnosis import DIAGNOSIS_PROFILES
import math


class PortfolioEngine:
    """포트폴리오 추천 엔진"""

    # 투자 성향별 자산 배분 전략
    ASSET_ALLOCATION_STRATEGIES = {
        "conservative": {
            "stocks": {"min": 10, "max": 30, "target": 20},
            "etfs": {"min": 10, "max": 20, "target": 15},
            "bonds": {"min": 30, "max": 45, "target": 35},
            "deposits": {"min": 25, "max": 35, "target": 30},
        },
        "moderate": {
            "stocks": {"min": 30, "max": 50, "target": 40},
            "etfs": {"min": 15, "max": 25, "target": 20},
            "bonds": {"min": 20, "max": 30, "target": 25},
            "deposits": {"min": 10, "max": 20, "target": 15},
        },
        "aggressive": {
            "stocks": {"min": 50, "max": 70, "target": 60},
            "etfs": {"min": 15, "max": 25, "target": 20},
            "bonds": {"min": 10, "max": 20, "target": 15},
            "deposits": {"min": 0, "max": 10, "target": 5},
        }
    }

    # 리스크 레벨별 점수
    RISK_SCORES = {
        "low": 1,
        "medium": 2,
        "high": 3
    }

    def __init__(self, db: Session):
        self.db = db

    def generate_portfolio(
        self,
        investment_type: str,
        investment_amount: int,
        risk_tolerance: Optional[str] = None,
        preferences: Optional[Dict] = None
    ) -> Dict:
        """
        맞춤형 포트폴리오 생성

        Args:
            investment_type: 투자 성향 (conservative, moderate, aggressive)
            investment_amount: 투자 금액 (원)
            risk_tolerance: 리스크 허용도 (low, medium, high) - 선택
            preferences: 사용자 선호도 (섹터, 배당 선호 등) - 선택

        Returns:
            Dict: 포트폴리오 추천 결과
        """
        if investment_type not in self.ASSET_ALLOCATION_STRATEGIES:
            raise ValueError(f"Invalid investment type: {investment_type}")

        # 기본 전략 가져오기
        strategy = self.ASSET_ALLOCATION_STRATEGIES[investment_type]

        # 자산 배분 계산
        allocation = self._calculate_allocation(strategy, investment_amount)

        # 각 자산군별 상품 선정
        selected_stocks = self._select_stocks(
            investment_type,
            allocation["stocks"]["amount"],
            risk_tolerance,
            preferences
        )

        selected_etfs = self._select_etfs(
            investment_type,
            allocation["etfs"]["amount"],
            risk_tolerance
        )

        selected_bonds = self._select_bonds(
            investment_type,
            allocation["bonds"]["amount"]
        )

        selected_deposits = self._select_deposits(
            allocation["deposits"]["amount"]
        )

        # 포트폴리오 통계 계산
        portfolio_stats = self._calculate_portfolio_stats(
            selected_stocks,
            selected_etfs,
            selected_bonds,
            selected_deposits,
            investment_amount
        )

        return {
            "investment_type": investment_type,
            "total_investment": investment_amount,
            "allocation": allocation,
            "portfolio": {
                "stocks": selected_stocks,
                "etfs": selected_etfs,
                "bonds": selected_bonds,
                "deposits": selected_deposits
            },
            "statistics": portfolio_stats,
            "recommendations": self._generate_recommendations(
                investment_type,
                portfolio_stats
            )
        }

    def _calculate_allocation(self, strategy: Dict, total_amount: int) -> Dict:
        """자산 배분 계산"""
        allocation = {}

        for asset_class, weights in strategy.items():
            target_ratio = weights["target"] / 100
            amount = int(total_amount * target_ratio)

            allocation[asset_class] = {
                "ratio": weights["target"],
                "amount": amount,
                "min_ratio": weights["min"],
                "max_ratio": weights["max"]
            }

        return allocation

    def _select_stocks(
        self,
        investment_type: str,
        budget: int,
        risk_tolerance: Optional[str],
        preferences: Optional[Dict]
    ) -> List[Dict]:
        """주식 종목 선정"""

        if budget < 100000:  # 10만원 미만이면 주식 미선정
            return []

        # 기본 필터링
        query = self.db.query(Stock).filter(
            and_(
                Stock.is_active == True,
                Stock.investment_type.contains(investment_type)
            )
        )

        # 리스크 허용도 적용
        if risk_tolerance:
            query = query.filter(Stock.risk_level == risk_tolerance)

        # 선호도 적용
        if preferences:
            if preferences.get("sectors"):
                query = query.filter(Stock.sector.in_(preferences["sectors"]))

            if preferences.get("dividend_preference"):
                query = query.filter(Stock.dividend_yield >= 2.0)

        # 점수 계산 및 정렬
        stocks = query.all()
        scored_stocks = []

        for stock in stocks:
            score = self._calculate_stock_score(stock, investment_type)
            scored_stocks.append({
                "stock": stock,
                "score": score
            })

        # 점수순 정렬
        scored_stocks.sort(key=lambda x: x["score"], reverse=True)

        # 상위 3-5개 선정 (다각화)
        max_stocks = 5 if budget >= 5000000 else 3
        selected = scored_stocks[:max_stocks]

        # 금액 배분
        result = []
        per_stock_budget = budget // len(selected) if selected else 0

        for item in selected:
            stock = item["stock"]
            shares = per_stock_budget // stock.current_price if stock.current_price else 0
            invested_amount = shares * stock.current_price if stock.current_price else 0

            result.append({
                "id": stock.id,
                "ticker": stock.ticker,
                "name": stock.name,
                "sector": stock.sector,
                "current_price": stock.current_price,
                "shares": shares,
                "invested_amount": invested_amount,
                "weight": round((invested_amount / budget * 100), 2) if budget > 0 else 0,
                "expected_return": stock.one_year_return,
                "dividend_yield": stock.dividend_yield,
                "risk_level": stock.risk_level,
                "pe_ratio": stock.pe_ratio,
                "pb_ratio": stock.pb_ratio,
                "score": round(item["score"], 2),
                "rationale": self._generate_stock_rationale(stock, investment_type)
            })

        return result

    def _calculate_stock_score(self, stock: Stock, investment_type: str) -> float:
        """주식 점수 계산 (0-100)"""
        score = 50.0  # 기본 점수

        # 1. 성과 점수 (40점)
        if stock.one_year_return is not None:
            if stock.one_year_return > 20:
                score += 20
            elif stock.one_year_return > 10:
                score += 15
            elif stock.one_year_return > 0:
                score += 10
            else:
                score += 5

        if stock.ytd_return is not None:
            if stock.ytd_return > 15:
                score += 15
            elif stock.ytd_return > 5:
                score += 10
            elif stock.ytd_return > 0:
                score += 5

        # 2. 밸류에이션 점수 (30점)
        if stock.pe_ratio is not None and 0 < stock.pe_ratio < 30:
            # PER 10-15가 이상적
            if 10 <= stock.pe_ratio <= 15:
                score += 15
            elif 5 <= stock.pe_ratio < 10 or 15 < stock.pe_ratio <= 20:
                score += 10
            else:
                score += 5

        if stock.pb_ratio is not None and stock.pb_ratio > 0:
            # PBR 1 근처가 이상적
            if 0.8 <= stock.pb_ratio <= 1.5:
                score += 15
            elif 0.5 <= stock.pb_ratio < 0.8 or 1.5 < stock.pb_ratio <= 2.5:
                score += 10
            else:
                score += 5

        # 3. 배당 점수 (20점) - 보수형에게 더 중요
        if stock.dividend_yield is not None:
            dividend_weight = 30 if investment_type == "conservative" else 20

            if stock.dividend_yield > 4:
                score += dividend_weight * 0.8
            elif stock.dividend_yield > 2:
                score += dividend_weight * 0.6
            elif stock.dividend_yield > 0:
                score += dividend_weight * 0.3

        # 4. 리스크 조정 (10점)
        risk_adjustment = {
            "conservative": {"low": 10, "medium": 5, "high": 0},
            "moderate": {"low": 5, "medium": 10, "high": 5},
            "aggressive": {"low": 0, "medium": 5, "high": 10}
        }

        if stock.risk_level in risk_adjustment.get(investment_type, {}):
            score += risk_adjustment[investment_type][stock.risk_level]

        return min(score, 100)  # 최대 100점

    def _generate_stock_rationale(self, stock: Stock, investment_type: str) -> str:
        """주식 추천 근거 생성"""
        rationales = []

        # 성과
        if stock.one_year_return and stock.one_year_return > 10:
            rationales.append(f"1년 수익률 {stock.one_year_return:.1f}%의 우수한 성과")

        # 배당
        if stock.dividend_yield and stock.dividend_yield > 2:
            rationales.append(f"배당수익률 {stock.dividend_yield:.1f}%")

        # 밸류에이션
        if stock.pe_ratio and 10 <= stock.pe_ratio <= 15:
            rationales.append(f"적정 PER {stock.pe_ratio:.1f}")

        # 섹터
        if stock.sector:
            rationales.append(f"{stock.sector} 섹터 대표주")

        if not rationales:
            rationales.append(f"{investment_type} 투자 성향에 적합")

        return ", ".join(rationales[:3])  # 최대 3개

    def _select_etfs(
        self,
        investment_type: str,
        budget: int,
        risk_tolerance: Optional[str]
    ) -> List[Dict]:
        """ETF 선정"""

        if budget < 50000:  # 5만원 미만이면 ETF 미선정
            return []

        query = self.db.query(ETF).filter(
            and_(
                ETF.is_active == True,
                ETF.investment_type.contains(investment_type)
            )
        )

        if risk_tolerance:
            query = query.filter(ETF.risk_level == risk_tolerance)

        # 점수 계산 및 정렬
        etfs = query.all()
        scored_etfs = []

        for etf in etfs:
            score = self._calculate_etf_score(etf)
            scored_etfs.append({
                "etf": etf,
                "score": score
            })

        scored_etfs.sort(key=lambda x: x["score"], reverse=True)

        # 상위 2-3개 선정
        max_etfs = 3 if budget >= 1000000 else 2
        selected = scored_etfs[:max_etfs]

        # 금액 배분
        result = []
        per_etf_budget = budget // len(selected) if selected else 0

        for item in selected:
            etf = item["etf"]
            shares = per_etf_budget // etf.current_price if etf.current_price else 0
            invested_amount = shares * etf.current_price if etf.current_price else 0

            result.append({
                "id": etf.id,
                "ticker": etf.ticker,
                "name": etf.name,
                "etf_type": etf.etf_type,
                "current_price": etf.current_price,
                "shares": shares,
                "invested_amount": invested_amount,
                "weight": round((invested_amount / budget * 100), 2) if budget > 0 else 0,
                "expected_return": etf.one_year_return,
                "expense_ratio": etf.expense_ratio,
                "aum": etf.aum,
                "risk_level": etf.risk_level,
                "score": round(item["score"], 2),
                "rationale": f"{etf.etf_type} ETF - 분산 투자 효과"
            })

        return result

    def _calculate_etf_score(self, etf: ETF) -> float:
        """ETF 점수 계산"""
        score = 50.0

        # 성과
        if etf.one_year_return is not None:
            if etf.one_year_return > 15:
                score += 25
            elif etf.one_year_return > 8:
                score += 20
            elif etf.one_year_return > 0:
                score += 10

        # 운용 규모 (AUM이 클수록 안정적)
        if etf.aum is not None:
            if etf.aum > 1000000:  # 1조 이상
                score += 15
            elif etf.aum > 100000:  # 1000억 이상
                score += 10
            else:
                score += 5

        # 수수료 (낮을수록 좋음)
        if etf.expense_ratio is not None:
            if etf.expense_ratio < 0.1:
                score += 10
            elif etf.expense_ratio < 0.3:
                score += 7
            else:
                score += 3

        return min(score, 100)

    def _select_bonds(self, investment_type: str, budget: int) -> List[Dict]:
        """채권 선정"""

        if budget < 100000:
            return []

        query = self.db.query(Bond).filter(
            and_(
                Bond.is_active == True,
                Bond.investment_type.contains(investment_type)
            )
        ).order_by(Bond.interest_rate.desc())

        bonds = query.limit(2).all()

        result = []
        per_bond_budget = budget // len(bonds) if bonds else 0

        for bond in bonds:
            result.append({
                "id": bond.id,
                "name": bond.name,
                "bond_type": bond.bond_type,
                "issuer": bond.issuer,
                "interest_rate": bond.interest_rate,
                "maturity_years": bond.maturity_years,
                "credit_rating": bond.credit_rating,
                "invested_amount": per_bond_budget,
                "weight": round((per_bond_budget / budget * 100), 2) if budget > 0 else 0,
                "expected_return": bond.interest_rate,
                "risk_level": bond.risk_level,
                "rationale": f"{bond.bond_type} - 안정적 수익 {bond.interest_rate:.1f}%"
            })

        return result

    def _select_deposits(self, budget: int) -> List[Dict]:
        """예금 상품 선정"""

        if budget < 10000:
            return []

        deposits = self.db.query(DepositProduct).filter(
            DepositProduct.is_active == True
        ).order_by(DepositProduct.interest_rate.desc()).limit(1).all()

        result = []
        for deposit in deposits:
            result.append({
                "id": deposit.id,
                "name": deposit.name,
                "bank": deposit.bank,
                "product_type": deposit.product_type,
                "interest_rate": deposit.interest_rate,
                "term_months": deposit.term_months,
                "invested_amount": budget,
                "weight": 100.0,
                "expected_return": deposit.interest_rate,
                "rationale": f"{deposit.bank} - 원금 보장 및 유동성 확보"
            })

        return result

    def _calculate_portfolio_stats(
        self,
        stocks: List[Dict],
        etfs: List[Dict],
        bonds: List[Dict],
        deposits: List[Dict],
        total_investment: int
    ) -> Dict:
        """포트폴리오 통계 계산"""

        # 실제 투자 금액 계산
        actual_invested = sum([
            sum(item["invested_amount"] for item in stocks),
            sum(item["invested_amount"] for item in etfs),
            sum(item["invested_amount"] for item in bonds),
            sum(item["invested_amount"] for item in deposits)
        ])

        # 기대 수익률 계산 (가중 평균)
        total_expected_return = 0

        for item in stocks:
            if item["expected_return"]:
                weight = item["invested_amount"] / actual_invested if actual_invested > 0 else 0
                total_expected_return += item["expected_return"] * weight

        for item in etfs:
            if item["expected_return"]:
                weight = item["invested_amount"] / actual_invested if actual_invested > 0 else 0
                total_expected_return += item["expected_return"] * weight

        for item in bonds:
            weight = item["invested_amount"] / actual_invested if actual_invested > 0 else 0
            total_expected_return += item["expected_return"] * weight

        for item in deposits:
            weight = item["invested_amount"] / actual_invested if actual_invested > 0 else 0
            total_expected_return += item["expected_return"] * weight

        # 리스크 레벨 계산
        risk_items = []
        for item in stocks + etfs + bonds:
            if "risk_level" in item:
                risk_items.append(self.RISK_SCORES.get(item["risk_level"], 2))

        avg_risk_score = sum(risk_items) / len(risk_items) if risk_items else 1.5

        if avg_risk_score <= 1.5:
            portfolio_risk = "low"
        elif avg_risk_score <= 2.5:
            portfolio_risk = "medium"
        else:
            portfolio_risk = "high"

        # 다각화 점수 (종목 수)
        total_items = len(stocks) + len(etfs) + len(bonds) + len(deposits)
        diversification_score = min(total_items * 10, 100)  # 최대 100점

        return {
            "total_investment": total_investment,
            "actual_invested": actual_invested,
            "cash_reserve": total_investment - actual_invested,
            "expected_annual_return": round(total_expected_return, 2),
            "portfolio_risk": portfolio_risk,
            "diversification_score": diversification_score,
            "total_items": total_items,
            "asset_breakdown": {
                "stocks_count": len(stocks),
                "etfs_count": len(etfs),
                "bonds_count": len(bonds),
                "deposits_count": len(deposits)
            }
        }

    def _generate_recommendations(
        self,
        investment_type: str,
        stats: Dict
    ) -> List[str]:
        """포트폴리오 개선 추천"""
        recommendations = []

        # 다각화
        if stats["diversification_score"] < 50:
            recommendations.append("더 많은 종목으로 다각화하여 리스크를 분산하는 것을 권장합니다.")

        # 현금 보유
        cash_ratio = (stats["cash_reserve"] / stats["total_investment"] * 100) if stats["total_investment"] > 0 else 0
        if cash_ratio > 10:
            recommendations.append(f"현금 {cash_ratio:.1f}%가 유휴 자금으로 남아있습니다. 추가 투자를 고려해보세요.")

        # 기대 수익률
        expected_ranges = {
            "conservative": (4, 6),
            "moderate": (6, 9),
            "aggressive": (9, 15)
        }

        min_return, max_return = expected_ranges.get(investment_type, (5, 10))
        if stats["expected_annual_return"] < min_return:
            recommendations.append(f"기대 수익률이 낮습니다. 더 높은 수익률의 상품을 추가하는 것을 고려해보세요.")
        elif stats["expected_annual_return"] > max_return:
            recommendations.append(f"기대 수익률이 높은 편입니다. 리스크가 적절한지 확인해보세요.")

        # 리스크
        risk_match = {
            "conservative": "low",
            "moderate": "medium",
            "aggressive": "high"
        }

        if stats["portfolio_risk"] != risk_match.get(investment_type):
            recommendations.append(f"포트폴리오 리스크가 투자 성향과 다릅니다. 자산 배분을 조정해보세요.")

        if not recommendations:
            recommendations.append("잘 구성된 포트폴리오입니다. 정기적으로 리밸런싱을 진행하세요.")

        return recommendations


def create_default_portfolio(
    db: Session,
    investment_type: str,
    investment_amount: int
) -> Dict:
    """
    기본 포트폴리오 생성 (간편 버전)

    Args:
        db: 데이터베이스 세션
        investment_type: 투자 성향
        investment_amount: 투자 금액

    Returns:
        Dict: 포트폴리오 추천 결과
    """
    engine = PortfolioEngine(db)
    return engine.generate_portfolio(investment_type, investment_amount)


def create_custom_portfolio(
    db: Session,
    investment_type: str,
    investment_amount: int,
    risk_tolerance: str,
    sector_preferences: List[str] = None,
    dividend_preference: bool = False
) -> Dict:
    """
    맞춤형 포트폴리오 생성 (고급 버전)

    Args:
        db: 데이터베이스 세션
        investment_type: 투자 성향
        investment_amount: 투자 금액
        risk_tolerance: 리스크 허용도
        sector_preferences: 선호 섹터 리스트
        dividend_preference: 배당 선호 여부

    Returns:
        Dict: 포트폴리오 추천 결과
    """
    preferences = {
        "sectors": sector_preferences,
        "dividend_preference": dividend_preference
    }

    engine = PortfolioEngine(db)
    return engine.generate_portfolio(
        investment_type,
        investment_amount,
        risk_tolerance,
        preferences
    )
