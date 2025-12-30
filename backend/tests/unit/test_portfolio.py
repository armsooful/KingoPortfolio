"""
포트폴리오 추천 엔진 테스트
"""

import pytest
from app.services.portfolio_engine import PortfolioEngine, create_default_portfolio
from sqlalchemy.orm import Session


@pytest.mark.unit
class TestPortfolioEngine:
    """포트폴리오 엔진 단위 테스트"""

    def test_asset_allocation_strategies_exist(self):
        """자산 배분 전략이 정의되어 있는지 확인"""
        assert "conservative" in PortfolioEngine.ASSET_ALLOCATION_STRATEGIES
        assert "moderate" in PortfolioEngine.ASSET_ALLOCATION_STRATEGIES
        assert "aggressive" in PortfolioEngine.ASSET_ALLOCATION_STRATEGIES

    def test_conservative_allocation(self):
        """보수형 자산 배분 확인"""
        strategy = PortfolioEngine.ASSET_ALLOCATION_STRATEGIES["conservative"]

        assert strategy["stocks"]["target"] == 20
        assert strategy["bonds"]["target"] == 35
        assert strategy["deposits"]["target"] == 30

    def test_moderate_allocation(self):
        """중도형 자산 배분 확인"""
        strategy = PortfolioEngine.ASSET_ALLOCATION_STRATEGIES["moderate"]

        assert strategy["stocks"]["target"] == 40
        assert strategy["bonds"]["target"] == 25
        assert strategy["deposits"]["target"] == 15

    def test_aggressive_allocation(self):
        """적극형 자산 배분 확인"""
        strategy = PortfolioEngine.ASSET_ALLOCATION_STRATEGIES["aggressive"]

        assert strategy["stocks"]["target"] == 60
        assert strategy["bonds"]["target"] == 15
        assert strategy["deposits"]["target"] == 5

    def test_risk_scores(self):
        """리스크 점수 확인"""
        assert PortfolioEngine.RISK_SCORES["low"] == 1
        assert PortfolioEngine.RISK_SCORES["medium"] == 2
        assert PortfolioEngine.RISK_SCORES["high"] == 3


@pytest.mark.unit
class TestPortfolioCalculations:
    """포트폴리오 계산 로직 테스트"""

    def test_calculate_allocation(self, db):
        """자산 배분 계산 테스트"""
        engine = PortfolioEngine(db)
        strategy = PortfolioEngine.ASSET_ALLOCATION_STRATEGIES["moderate"]
        total_amount = 10000000

        allocation = engine._calculate_allocation(strategy, total_amount)

        # 주식 40%
        assert allocation["stocks"]["ratio"] == 40
        assert allocation["stocks"]["amount"] == 4000000

        # 채권 25%
        assert allocation["bonds"]["ratio"] == 25
        assert allocation["bonds"]["amount"] == 2500000

        # 예금 15%
        assert allocation["deposits"]["ratio"] == 15
        assert allocation["deposits"]["amount"] == 1500000

    def test_stock_score_calculation(self, db):
        """주식 점수 계산 테스트"""
        from app.models.securities import Stock

        engine = PortfolioEngine(db)

        # 가상의 주식 생성
        stock = Stock(
            ticker="TEST",
            name="테스트 주식",
            sector="전자",
            current_price=100000,
            one_year_return=15.0,
            ytd_return=10.0,
            pe_ratio=12.0,
            pb_ratio=1.0,
            dividend_yield=3.0,
            risk_level="medium"
        )

        score = engine._calculate_stock_score(stock, "moderate")

        # 점수가 0-100 범위 내에 있는지
        assert 0 <= score <= 100

        # 좋은 지표를 가진 주식이므로 50점 이상이어야 함
        assert score > 50

    def test_stock_score_high_return(self, db):
        """높은 수익률 주식의 점수가 높은지 확인"""
        from app.models.securities import Stock

        engine = PortfolioEngine(db)

        high_return_stock = Stock(
            ticker="HIGH",
            name="고수익 주식",
            sector="IT",
            current_price=50000,
            one_year_return=30.0,  # 높은 수익률
            ytd_return=25.0,
            pe_ratio=15.0,
            pb_ratio=1.2,
            dividend_yield=2.0,
            risk_level="high"
        )

        score = engine._calculate_stock_score(high_return_stock, "aggressive")
        assert score > 70  # 높은 점수 기대


@pytest.mark.integration
class TestPortfolioGeneration:
    """포트폴리오 생성 통합 테스트"""

    @pytest.mark.skip(reason="실제 DB 데이터 필요")
    def test_generate_conservative_portfolio(self, db):
        """보수형 포트폴리오 생성 테스트"""
        portfolio = create_default_portfolio(
            db=db,
            investment_type="conservative",
            investment_amount=10000000
        )

        assert portfolio["investment_type"] == "conservative"
        assert portfolio["total_investment"] == 10000000
        assert "allocation" in portfolio
        assert "portfolio" in portfolio
        assert "statistics" in portfolio
        assert "recommendations" in portfolio

    @pytest.mark.skip(reason="실제 DB 데이터 필요")
    def test_portfolio_has_all_asset_classes(self, db):
        """포트폴리오가 모든 자산군을 포함하는지 확인"""
        portfolio = create_default_portfolio(
            db=db,
            investment_type="moderate",
            investment_amount=10000000
        )

        assert "stocks" in portfolio["portfolio"]
        assert "etfs" in portfolio["portfolio"]
        assert "bonds" in portfolio["portfolio"]
        assert "deposits" in portfolio["portfolio"]

    @pytest.mark.skip(reason="실제 DB 데이터 필요")
    def test_portfolio_statistics_calculation(self, db):
        """포트폴리오 통계 계산 확인"""
        portfolio = create_default_portfolio(
            db=db,
            investment_type="moderate",
            investment_amount=10000000
        )

        stats = portfolio["statistics"]

        assert stats["total_investment"] == 10000000
        assert stats["actual_invested"] <= stats["total_investment"]
        assert stats["cash_reserve"] >= 0
        assert stats["expected_annual_return"] > 0
        assert stats["portfolio_risk"] in ["low", "medium", "high"]
        assert 0 <= stats["diversification_score"] <= 100


@pytest.mark.unit
class TestPortfolioRecommendations:
    """포트폴리오 추천 로직 테스트"""

    def test_generate_recommendations_low_diversification(self, db):
        """다각화 부족 시 추천 메시지 확인"""
        engine = PortfolioEngine(db)

        stats = {
            "total_investment": 10000000,
            "actual_invested": 9000000,
            "cash_reserve": 1000000,
            "expected_annual_return": 7.0,
            "portfolio_risk": "medium",
            "diversification_score": 30,  # 낮은 다각화
            "total_items": 3,
            "asset_breakdown": {}
        }

        recommendations = engine._generate_recommendations("moderate", stats)

        # 다각화 추천이 포함되어야 함
        assert any("다각화" in rec for rec in recommendations)

    def test_generate_recommendations_excess_cash(self, db):
        """현금 과다 보유 시 추천 메시지 확인"""
        engine = PortfolioEngine(db)

        stats = {
            "total_investment": 10000000,
            "actual_invested": 8000000,
            "cash_reserve": 2000000,  # 20% 현금
            "expected_annual_return": 7.0,
            "portfolio_risk": "medium",
            "diversification_score": 80,
            "total_items": 8,
            "asset_breakdown": {}
        }

        recommendations = engine._generate_recommendations("moderate", stats)

        # 유휴 자금 관련 추천이 포함되어야 함
        assert any("유휴 자금" in rec or "현금" in rec for rec in recommendations)


@pytest.mark.unit
class TestPortfolioValidation:
    """포트폴리오 입력 검증 테스트"""

    def test_invalid_investment_type(self, db):
        """잘못된 투자 성향으로 포트폴리오 생성 시 에러"""
        with pytest.raises(ValueError):
            create_default_portfolio(
                db=db,
                investment_type="invalid_type",
                investment_amount=10000000
            )

    def test_minimum_investment_amount(self, db):
        """최소 투자 금액 미만일 때도 처리 가능한지 확인"""
        # 최소 금액으로도 포트폴리오 생성 가능해야 함
        portfolio = create_default_portfolio(
            db=db,
            investment_type="conservative",
            investment_amount=10000  # 1만원
        )

        assert portfolio["total_investment"] == 10000
        # 금액이 작아서 일부 자산군은 선정되지 않을 수 있음
        assert "portfolio" in portfolio
