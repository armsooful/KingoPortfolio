"""
포트폴리오 시뮬레이션 엔진

⚠️ 교육 목적: 본 모듈은 투자 전략 학습용 시뮬레이션 도구입니다.
투자 권유·자문·일임 서비스를 제공하지 않습니다.
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from app.models.securities import Stock, ETF, Bond, DepositProduct
from app.diagnosis import DIAGNOSIS_PROFILES
import math


class PortfolioEngine:
    """
    포트폴리오 시뮬레이션 엔진 (교육용)

    ⚠️ 본 클래스는 투자 전략 학습을 위한 시뮬레이션 도구이며,
    투자 권유·자문·일임 서비스를 제공하지 않습니다.
    """

    # 투자 성향별 자산 배분 전략 (알고리즘 문서 기반 개선)
    ASSET_ALLOCATION_STRATEGIES = {
        "conservative": {
            "stocks": {"min": 30, "max": 50, "target": 40},
            "etfs": {"min": 10, "max": 20, "target": 15},
            "bonds": {"min": 25, "max": 35, "target": 30},
            "deposits": {"min": 10, "max": 20, "target": 15},
            "num_stocks": 7,
            "preferred_sectors": ["금융", "필수소비재", "헬스케어", "산업재"],
            "dividend_yield_min": 2.0,
            "name": "보수적"
        },
        "moderate": {
            "stocks": {"min": 50, "max": 70, "target": 60},
            "etfs": {"min": 10, "max": 20, "target": 15},
            "bonds": {"min": 15, "max": 25, "target": 20},
            "deposits": {"min": 0, "max": 10, "target": 5},
            "num_stocks": 10,
            "preferred_sectors": ["IT", "금융", "산업재", "헬스케어", "소비재"],
            "dividend_yield_min": 1.5,
            "name": "중립적"
        },
        "aggressive": {
            "stocks": {"min": 70, "max": 90, "target": 80},
            "etfs": {"min": 5, "max": 15, "target": 10},
            "bonds": {"min": 5, "max": 15, "target": 10},
            "deposits": {"min": 0, "max": 5, "target": 0},
            "num_stocks": 12,
            "preferred_sectors": ["IT", "바이오", "2차전지", "반도체"],
            "dividend_yield_min": 0,
            "growth_focused": True,
            "name": "공격적"
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
        포트폴리오 구성 시뮬레이션 (교육용)

        ⚠️ 본 메서드는 투자 전략 학습을 위한 예시 포트폴리오를 생성합니다.
        특정인에 대한 맞춤형 투자 권유·자문 서비스가 아닙니다.

        Args:
            investment_type: 전략 유형 (conservative, moderate, aggressive)
            investment_amount: 시뮬레이션 금액 (원)
            risk_tolerance: 리스크 레벨 (low, medium, high) - 선택
            preferences: 전략 선호도 (섹터, 배당 등) - 선택

        Returns:
            Dict: 시뮬레이션 결과 (교육 목적)
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
            "simulation_notes": self._generate_simulation_notes(
                investment_type,
                portfolio_stats
            )
        }

    def _calculate_allocation(self, strategy: Dict, total_amount: int) -> Dict:
        """자산 배분 계산"""
        allocation = {}

        # 자산 클래스만 필터링 (stocks, etfs, bonds, deposits)
        asset_classes = ["stocks", "etfs", "bonds", "deposits"]

        for asset_class in asset_classes:
            if asset_class in strategy:
                weights = strategy[asset_class]
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
        """주식 종목 선정 (알고리즘 문서 기반 개선)"""

        if budget < 100000:  # 10만원 미만이면 주식 미선정
            return []

        # 전략 프로필 가져오기
        strategy = self.ASSET_ALLOCATION_STRATEGIES.get(investment_type, {})

        # 1단계: 기본 필터링
        query = self.db.query(Stock).filter(
            and_(
                Stock.is_active == True,
                Stock.current_price.isnot(None),
                Stock.current_price > 0
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

        # 전체 주식 로드
        all_stocks = query.all()

        # 2단계: 필터링 (섹터, 배당)
        filtered_stocks = []
        for stock in all_stocks:
            # 섹터 필터
            if strategy.get("preferred_sectors") and stock.sector:
                if stock.sector not in strategy["preferred_sectors"]:
                    continue

            # 배당 필터 (보수적 성향)
            if strategy.get("dividend_yield_min", 0) > 0:
                if not stock.dividend_yield or stock.dividend_yield < strategy["dividend_yield_min"]:
                    continue

            filtered_stocks.append(stock)

        # 3단계: 점수 계산
        scored_stocks = []
        for stock in filtered_stocks:
            score = self._calculate_stock_score_improved(stock, strategy)
            scored_stocks.append({
                "stock": stock,
                "score": score
            })

        # 점수순 정렬
        scored_stocks.sort(key=lambda x: x["score"], reverse=True)

        # 중복 제거 (같은 이름)
        seen_names = set()
        unique_stocks = []
        for item in scored_stocks:
            if item["stock"].name not in seen_names:
                unique_stocks.append(item)
                seen_names.add(item["stock"].name)

        # 4단계: 상위 N개 선정
        num_stocks = strategy.get("num_stocks", 5)
        selected = unique_stocks[:num_stocks]

        # 5단계: 섹터 다각화 적용 (한 섹터 최대 40%)
        selected = self._apply_sector_diversification(selected)

        # 6단계: 비중 계산 (점수 기반)
        portfolio = self._calculate_weights_score_based(selected)

        # 7단계: 금액 배분
        result = []
        for item in portfolio:
            stock = item["stock"]
            weight = item["weight"]

            allocated_amount = int(budget * (weight / 100))
            shares = allocated_amount // stock.current_price if stock.current_price else 0
            invested_amount = shares * stock.current_price if stock.current_price else 0

            result.append({
                "id": stock.id,
                "ticker": stock.ticker,
                "name": stock.name,
                "sector": stock.sector,
                "current_price": stock.current_price,
                "shares": shares,
                "invested_amount": invested_amount,
                "weight": round(weight, 2),
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

    def _calculate_stock_score_improved(self, stock: Stock, strategy: Dict) -> float:
        """개선된 종목 점수 계산 (알고리즘 문서 기반)"""
        score = 0

        # 1. 모멘텀 점수 (30점)
        if stock.ytd_return is not None:
            if 0 < stock.ytd_return < 20:  # 적정 상승
                score += 20
            elif 20 <= stock.ytd_return < 50:
                score += 15
            elif stock.ytd_return >= 50:  # 과열 가능성
                score += 5
            else:
                score += 10

        if stock.one_year_return is not None:
            if stock.one_year_return > 10:
                score += 10
            elif stock.one_year_return > 0:
                score += 5

        # 2. 가치 점수 (PER, PBR) - 30점
        if stock.pe_ratio and stock.pe_ratio > 0:
            if 5 < stock.pe_ratio < 15:
                score += 15
            elif 15 <= stock.pe_ratio < 25:
                score += 10
            elif stock.pe_ratio > 30:
                score -= 5

        if stock.pb_ratio and stock.pb_ratio > 0:
            if 0.5 < stock.pb_ratio < 2.0:
                score += 15
            elif 2.0 <= stock.pb_ratio < 3.0:
                score += 10

        # 3. 배당 점수 - 20점
        if stock.dividend_yield:
            if stock.dividend_yield > 3:
                score += 20
            elif stock.dividend_yield > 2:
                score += 15
            elif stock.dividend_yield > 1:
                score += 10

        # 4. 성장성 점수 (공격적 성향) - 20점
        if strategy.get("growth_focused"):
            if stock.one_year_return and stock.one_year_return > 20:
                score += 15
            if stock.ytd_return and stock.ytd_return > 15:
                score += 5

        return min(score, 100)

    def _apply_sector_diversification(self, selected: List[Dict]) -> List[Dict]:
        """섹터 다각화 적용 (한 섹터 최대 40%)"""
        if not selected:
            return selected

        max_per_sector = max(2, int(len(selected) * 0.4))

        result = []
        sector_count = {}

        for item in selected:
            sector = item["stock"].sector or "기타"
            current_count = sector_count.get(sector, 0)

            if current_count < max_per_sector:
                result.append(item)
                sector_count[sector] = current_count + 1

            if len(result) >= len(selected):
                break

        return result

    def _calculate_weights_score_based(self, selected: List[Dict]) -> List[Dict]:
        """점수 기반 비중 계산 (알고리즘 문서)"""
        if not selected:
            return []

        total_score = sum(item["score"] for item in selected)

        if total_score == 0:
            # 점수가 모두 0이면 균등 배분
            equal_weight = 100 / len(selected)
            for item in selected:
                item["weight"] = equal_weight
            return selected

        # 점수 비례 배분
        for item in selected:
            item["weight"] = (item["score"] / total_score) * 100

        # 최대/최소 제약 적용
        for item in selected:
            if item["weight"] > 30:  # 한 종목 최대 30%
                item["weight"] = 30
            if item["weight"] < 5:  # 한 종목 최소 5%
                item["weight"] = 5

        # 재조정하여 100%로 맞추기
        total_weight = sum(item["weight"] for item in selected)
        if total_weight > 0:
            for item in selected:
                item["weight"] = (item["weight"] / total_weight) * 100

        return selected

    def _generate_stock_rationale(self, stock: Stock, investment_type: str) -> str:
        """주식 선정 근거 생성"""
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
                ETF.investment_type.contains(investment_type),
                ETF.current_price.isnot(None),
                ETF.current_price > 0
            )
        )

        if risk_tolerance:
            query = query.filter(ETF.risk_level == risk_tolerance)

        # 점수 계산
        etfs = query.all()
        scored_etfs = []

        for etf in etfs:
            score = self._calculate_etf_score(etf)
            scored_etfs.append({
                "etf": etf,
                "score": score
            })

        # 점수 기준 정렬
        scored_etfs.sort(key=lambda x: x["score"], reverse=True)

        # 같은 이름의 ETF 중복 제거 (점수가 높은 것만 유지)
        seen_names = set()
        unique_etfs = []
        for item in scored_etfs:
            if item["etf"].name not in seen_names:
                unique_etfs.append(item)
                seen_names.add(item["etf"].name)

        scored_etfs = unique_etfs

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
                "rationale": f"{deposit.bank} - 원금 보전 및 유동성 확보"
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

        # 섹터 분포 계산 (주식 기준)
        sector_breakdown = {}
        total_stock_amount = sum(item["invested_amount"] for item in stocks)
        if total_stock_amount > 0:
            for stock in stocks:
                sector = stock.get("sector") or "기타"
                weight = (stock["invested_amount"] / total_stock_amount) * 100
                sector_breakdown[sector] = sector_breakdown.get(sector, 0) + weight

        # B-1: expected_annual_return을 historical_observation으로 이동
        return {
            "total_investment": total_investment,
            "actual_invested": actual_invested,
            "cash_reserve": total_investment - actual_invested,
            "portfolio_risk": portfolio_risk,
            "diversification_score": diversification_score,
            "total_items": total_items,
            "asset_breakdown": {
                "stocks_count": len(stocks),
                "etfs_count": len(etfs),
                "bonds_count": len(bonds),
                "deposits_count": len(deposits)
            },
            "sector_breakdown": {k: round(v, 2) for k, v in sector_breakdown.items()},
            # 과거 관측치 (historical_observation) - 기대/예상 수익률 아님
            "historical_observation": {
                "avg_annual_return": round(total_expected_return, 2),  # 과거 평균 연간 수익률
                "note": "과거 데이터 기반 참고치이며 미래 수익을 보장하지 않습니다"
            },
            # 레거시 호환성 (프론트엔드 기존 코드 지원)
            "expected_annual_return": round(total_expected_return, 2)
        }

    def _generate_simulation_notes(
        self,
        investment_type: str,
        stats: Dict
    ) -> List[str]:
        """포트폴리오 시뮬레이션 참고사항 (교육용)"""
        notes = []

        # 다각화
        if stats.get("diversification_score", 0) < 50:
            notes.append("더 많은 종목으로 다각화하여 리스크를 분산하는 방법을 학습할 수 있습니다.")

        if stats["total_items"] < 5:
            notes.append("종목 수가 적습니다. 최소 5개 이상의 종목으로 다각화하는 전략을 검토해보세요.")

        # 섹터 집중도
        if "sector_breakdown" in stats:
            sector_breakdown = stats["sector_breakdown"]
            if sector_breakdown:
                max_sector_weight = max(sector_breakdown.values()) if sector_breakdown.values() else 0
                if max_sector_weight > 40:
                    notes.append(f"특정 섹터 비중이 {max_sector_weight:.1f}%로 높습니다. 섹터 다각화 전략을 학습해보세요.")

        # 현금 보유
        cash_ratio = (stats["cash_reserve"] / stats["total_investment"] * 100) if stats["total_investment"] > 0 else 0
        if cash_ratio > 10:
            notes.append(f"현금 {cash_ratio:.1f}%가 유휴 자금으로 설정되어 있습니다. 자산 배분 전략을 학습해보세요.")

        # 과거 평균 수익률 (historical_observation에서 가져옴)
        historical_return = stats.get("historical_observation", {}).get("avg_annual_return", 0)
        expected_ranges = {
            "conservative": (4, 8),
            "moderate": (6, 12),
            "aggressive": (10, 20)
        }

        min_return, max_return = expected_ranges.get(investment_type, (5, 10))
        if historical_return < min_return:
            notes.append(f"과거 평균 수익률이 {historical_return:.1f}%입니다. 성장주 특성을 학습해보세요.")
        elif historical_return > max_return:
            notes.append(f"과거 평균 수익률이 {historical_return:.1f}%로 높습니다. 리스크 관리 전략을 학습해보세요.")

        # 리스크
        risk_match = {
            "conservative": "low",
            "moderate": "medium",
            "aggressive": "high"
        }

        if stats.get("portfolio_risk") and stats["portfolio_risk"] != risk_match.get(investment_type):
            notes.append(f"포트폴리오 리스크가 학습 성향과 다릅니다. 자산 배분 이론을 학습해보세요.")

        # 리밸런싱 안내
        if not notes:
            notes.append("균형잡힌 시뮬레이션입니다. 리밸런싱 전략을 학습해보세요.")
        else:
            notes.append("시뮬레이션 조정 후 리밸런싱 전략을 학습해보세요.")

        return notes


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
        Dict: 포트폴리오 시뮬레이션 결과
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
        Dict: 포트폴리오 시뮬레이션 결과
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
