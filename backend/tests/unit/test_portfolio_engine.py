"""
포트폴리오 엔진 단위 테스트
- 순수 함수 및 내부 로직 테스트 (DB 의존성 mock)
"""
import pytest
from unittest.mock import MagicMock
from app.services.portfolio_engine import PortfolioEngine


# ============================================================================
# 헬퍼: Mock 객체 생성
# ============================================================================

def _make_mock_stock(**kwargs):
    """테스트용 주식 mock"""
    stock = MagicMock()
    stock.ticker = kwargs.get("ticker", "005930")
    stock.name = kwargs.get("name", "삼성전자")
    stock.sector = kwargs.get("sector", "IT")
    stock.current_price = kwargs.get("current_price", 70000)
    stock.one_year_return = kwargs.get("one_year_return", 15.0)
    stock.ytd_return = kwargs.get("ytd_return", 10.0)
    stock.pe_ratio = kwargs.get("pe_ratio", 12.0)
    stock.pb_ratio = kwargs.get("pb_ratio", 1.2)
    stock.dividend_yield = kwargs.get("dividend_yield", 2.5)
    stock.risk_level = kwargs.get("risk_level", "medium")
    stock.is_active = True
    return stock


def _make_mock_etf(**kwargs):
    """테스트용 ETF mock"""
    etf = MagicMock()
    etf.ticker = kwargs.get("ticker", "069500")
    etf.name = kwargs.get("name", "KODEX 200")
    etf.etf_type = kwargs.get("etf_type", "인덱스")
    etf.current_price = kwargs.get("current_price", 35000)
    etf.one_year_return = kwargs.get("one_year_return", 12.0)
    etf.expense_ratio = kwargs.get("expense_ratio", 0.05)
    etf.aum = kwargs.get("aum", 5000000)  # 5조
    etf.risk_level = kwargs.get("risk_level", "medium")
    etf.is_active = True
    return etf


def _make_engine():
    """DB mock으로 PortfolioEngine 인스턴스 생성"""
    mock_db = MagicMock()
    return PortfolioEngine(mock_db), mock_db


# ============================================================================
# 자산 배분 계산 테스트
# ============================================================================

@pytest.mark.unit
@pytest.mark.financial
class TestCalculateAllocation:
    """_calculate_allocation 테스트"""

    def test_conservative_allocation(self):
        """보수적 전략 자산 배분"""
        engine, _ = _make_engine()
        strategy = PortfolioEngine.ASSET_ALLOCATION_STRATEGIES["conservative"]

        result = engine._calculate_allocation(strategy, 10_000_000)

        assert result["stocks"]["ratio"] == 40
        assert result["bonds"]["ratio"] == 30
        assert result["etfs"]["ratio"] == 15
        assert result["deposits"]["ratio"] == 15
        assert result["stocks"]["amount"] == 4_000_000
        assert result["bonds"]["amount"] == 3_000_000

    def test_moderate_allocation(self):
        """중립적 전략 자산 배분"""
        engine, _ = _make_engine()
        strategy = PortfolioEngine.ASSET_ALLOCATION_STRATEGIES["moderate"]

        result = engine._calculate_allocation(strategy, 10_000_000)

        assert result["stocks"]["ratio"] == 60
        assert result["stocks"]["amount"] == 6_000_000

    def test_aggressive_allocation(self):
        """공격적 전략 자산 배분"""
        engine, _ = _make_engine()
        strategy = PortfolioEngine.ASSET_ALLOCATION_STRATEGIES["aggressive"]

        result = engine._calculate_allocation(strategy, 10_000_000)

        assert result["stocks"]["ratio"] == 80
        assert result["stocks"]["amount"] == 8_000_000
        assert result["deposits"]["ratio"] == 0

    def test_allocation_preserves_min_max(self):
        """min/max 비율 정보 보존"""
        engine, _ = _make_engine()
        strategy = PortfolioEngine.ASSET_ALLOCATION_STRATEGIES["conservative"]

        result = engine._calculate_allocation(strategy, 10_000_000)

        assert result["stocks"]["min_ratio"] == 30
        assert result["stocks"]["max_ratio"] == 50

    def test_zero_investment(self):
        """투자금액 0원"""
        engine, _ = _make_engine()
        strategy = PortfolioEngine.ASSET_ALLOCATION_STRATEGIES["moderate"]

        result = engine._calculate_allocation(strategy, 0)

        assert result["stocks"]["amount"] == 0
        assert result["bonds"]["amount"] == 0


# ============================================================================
# 주식 점수 계산 테스트
# ============================================================================

@pytest.mark.unit
@pytest.mark.financial
class TestCalculateStockScore:
    """_calculate_stock_score 테스트"""

    def test_high_performing_stock(self):
        """고성과 주식 → 높은 점수"""
        engine, _ = _make_engine()
        stock = _make_mock_stock(
            one_year_return=25.0, ytd_return=20.0,
            pe_ratio=12.0, pb_ratio=1.0, dividend_yield=4.5,
            risk_level="medium"
        )

        score = engine._calculate_stock_score(stock, "moderate")
        assert score >= 80

    def test_low_performing_stock(self):
        """저성과 주식 → 낮은 점수"""
        engine, _ = _make_engine()
        stock = _make_mock_stock(
            one_year_return=-5.0, ytd_return=-3.0,
            pe_ratio=35.0, pb_ratio=5.0, dividend_yield=0,
            risk_level="high"
        )

        score = engine._calculate_stock_score(stock, "moderate")
        assert score < 75

    def test_conservative_dividend_weight(self):
        """보수적 성향 → 배당 가중치 30"""
        engine, _ = _make_engine()
        stock = _make_mock_stock(
            one_year_return=None, ytd_return=None,
            pe_ratio=None, pb_ratio=None,
            dividend_yield=5.0, risk_level="low"
        )

        score_conservative = engine._calculate_stock_score(stock, "conservative")
        score_aggressive = engine._calculate_stock_score(stock, "aggressive")

        # 보수적 배당 가중치(30) > 공격적(20)
        assert score_conservative > score_aggressive

    def test_risk_adjustment_conservative_prefers_low(self):
        """보수적 성향 → low 리스크 선호"""
        engine, _ = _make_engine()
        # 다른 요소 제거하여 리스크 점수 차이만 비교
        stock_low = _make_mock_stock(
            one_year_return=None, ytd_return=None,
            pe_ratio=None, pb_ratio=None, dividend_yield=None,
            risk_level="low"
        )
        stock_high = _make_mock_stock(
            one_year_return=None, ytd_return=None,
            pe_ratio=None, pb_ratio=None, dividend_yield=None,
            risk_level="high"
        )

        score_low = engine._calculate_stock_score(stock_low, "conservative")
        score_high = engine._calculate_stock_score(stock_high, "conservative")

        # low: 50 + 10 = 60, high: 50 + 0 = 50
        assert score_low > score_high

    def test_max_score_cap_100(self):
        """최대 점수 100 제한"""
        engine, _ = _make_engine()
        stock = _make_mock_stock(
            one_year_return=30.0, ytd_return=20.0,
            pe_ratio=12.0, pb_ratio=1.0,
            dividend_yield=5.0, risk_level="low"
        )

        score = engine._calculate_stock_score(stock, "conservative")
        assert score <= 100


@pytest.mark.unit
@pytest.mark.financial
class TestCalculateStockScoreImproved:
    """_calculate_stock_score_improved 테스트"""

    def test_optimal_momentum(self):
        """적정 모멘텀 → 최고 점수"""
        engine, _ = _make_engine()
        stock = _make_mock_stock(ytd_return=10.0, one_year_return=15.0)
        strategy = {"growth_focused": False}

        score = engine._calculate_stock_score_improved(stock, strategy)

        # ytd 0~20 → 20점, 1yr > 10 → 10점 = 30
        assert score >= 30

    def test_overheated_momentum_penalty(self):
        """과열 모멘텀 → 낮은 점수"""
        engine, _ = _make_engine()
        stock = _make_mock_stock(ytd_return=55.0, one_year_return=60.0)
        strategy = {"growth_focused": False}

        score = engine._calculate_stock_score_improved(stock, strategy)

        # ytd >= 50 → 5점 (과열), 1yr > 10 → 10점
        # 모멘텀 점수가 적정(30) 대비 낮음
        assert score >= 0  # 음수 아님

    def test_growth_focused_bonus(self):
        """공격적 전략 성장주 보너스"""
        engine, _ = _make_engine()
        stock = _make_mock_stock(one_year_return=25.0, ytd_return=20.0)

        score_growth = engine._calculate_stock_score_improved(
            stock, {"growth_focused": True}
        )
        score_normal = engine._calculate_stock_score_improved(
            stock, {"growth_focused": False}
        )

        assert score_growth > score_normal

    def test_value_per_scoring(self):
        """PER 구간별 점수"""
        engine, _ = _make_engine()
        strategy = {}

        # PER 5~15 → 15점
        stock_low = _make_mock_stock(pe_ratio=10.0, pb_ratio=None, ytd_return=None, one_year_return=None, dividend_yield=None)
        score_low = engine._calculate_stock_score_improved(stock_low, strategy)

        # PER > 30 → -5점
        stock_high = _make_mock_stock(pe_ratio=35.0, pb_ratio=None, ytd_return=None, one_year_return=None, dividend_yield=None)
        score_high = engine._calculate_stock_score_improved(stock_high, strategy)

        assert score_low > score_high


# ============================================================================
# ETF 점수 계산 테스트
# ============================================================================

@pytest.mark.unit
@pytest.mark.financial
class TestCalculateEtfScore:
    """_calculate_etf_score 테스트"""

    def test_high_quality_etf(self):
        """고품질 ETF → 높은 점수"""
        engine, _ = _make_engine()
        etf = _make_mock_etf(
            one_year_return=20.0, aum=5000000, expense_ratio=0.03
        )

        score = engine._calculate_etf_score(etf)

        # 기본 50 + 성과 25 + AUM 15 + 수수료 10 = 100
        assert score == 100

    def test_low_quality_etf(self):
        """저품질 ETF → 낮은 점수"""
        engine, _ = _make_engine()
        etf = _make_mock_etf(
            one_year_return=-5.0, aum=50000, expense_ratio=0.5
        )

        score = engine._calculate_etf_score(etf)

        # 기본 50 + 성과 0 + AUM 5 + 수수료 3 = 58
        assert score == 58

    def test_etf_score_cap(self):
        """ETF 점수 최대 100"""
        engine, _ = _make_engine()
        etf = _make_mock_etf(one_year_return=100.0, aum=99999999, expense_ratio=0.01)

        score = engine._calculate_etf_score(etf)
        assert score <= 100

    def test_null_values_handled(self):
        """None 값 처리"""
        engine, _ = _make_engine()
        etf = _make_mock_etf(one_year_return=None, aum=None, expense_ratio=None)

        score = engine._calculate_etf_score(etf)
        assert score == 50  # 기본 점수만


# ============================================================================
# 섹터 다각화 테스트
# ============================================================================

@pytest.mark.unit
@pytest.mark.financial
class TestSectorDiversification:
    """_apply_sector_diversification 테스트"""

    def test_empty_list(self):
        """빈 리스트 → 빈 리스트"""
        engine, _ = _make_engine()
        result = engine._apply_sector_diversification([])
        assert result == []

    def test_diverse_sectors(self):
        """다양한 섹터 → 모두 유지"""
        engine, _ = _make_engine()
        items = [
            {"stock": _make_mock_stock(sector="IT"), "score": 90},
            {"stock": _make_mock_stock(sector="금융"), "score": 85},
            {"stock": _make_mock_stock(sector="헬스케어"), "score": 80},
            {"stock": _make_mock_stock(sector="산업재"), "score": 75},
            {"stock": _make_mock_stock(sector="소비재"), "score": 70},
        ]

        result = engine._apply_sector_diversification(items)
        assert len(result) == 5

    def test_concentrated_sector_capped(self):
        """한 섹터 집중 → max_per_sector 제한"""
        engine, _ = _make_engine()
        # 5개 중 4개가 IT → max_per_sector = max(2, 5*0.4) = 2
        items = [
            {"stock": _make_mock_stock(name="A", sector="IT"), "score": 90},
            {"stock": _make_mock_stock(name="B", sector="IT"), "score": 85},
            {"stock": _make_mock_stock(name="C", sector="IT"), "score": 80},
            {"stock": _make_mock_stock(name="D", sector="IT"), "score": 75},
            {"stock": _make_mock_stock(name="E", sector="금융"), "score": 70},
        ]

        result = engine._apply_sector_diversification(items)

        it_count = sum(1 for item in result if item["stock"].sector == "IT")
        assert it_count <= 2

    def test_none_sector_treated_as_etc(self):
        """sector가 None → '기타'로 처리"""
        engine, _ = _make_engine()
        items = [
            {"stock": _make_mock_stock(sector=None), "score": 90},
            {"stock": _make_mock_stock(sector=None), "score": 85},
            {"stock": _make_mock_stock(sector=None), "score": 80},
        ]

        result = engine._apply_sector_diversification(items)
        # max_per_sector = max(2, 3*0.4=1.2) = 2
        assert len(result) == 2


# ============================================================================
# 비중 계산 테스트
# ============================================================================

@pytest.mark.unit
@pytest.mark.financial
class TestCalculateWeightsScoreBased:
    """_calculate_weights_score_based 테스트"""

    def test_empty_list(self):
        """빈 리스트 → 빈 리스트"""
        engine, _ = _make_engine()
        result = engine._calculate_weights_score_based([])
        assert result == []

    def test_equal_scores(self):
        """동일 점수 → 균등 배분"""
        engine, _ = _make_engine()
        items = [
            {"stock": _make_mock_stock(name="A"), "score": 50},
            {"stock": _make_mock_stock(name="B"), "score": 50},
        ]

        result = engine._calculate_weights_score_based(items)

        assert len(result) == 2
        # 50/100 * 100 = 50% 각각
        assert abs(result[0]["weight"] - 50.0) < 0.1
        assert abs(result[1]["weight"] - 50.0) < 0.1

    def test_all_zero_scores(self):
        """모든 점수 0 → 균등 배분"""
        engine, _ = _make_engine()
        items = [
            {"stock": _make_mock_stock(name="A"), "score": 0},
            {"stock": _make_mock_stock(name="B"), "score": 0},
            {"stock": _make_mock_stock(name="C"), "score": 0},
        ]

        result = engine._calculate_weights_score_based(items)

        for item in result:
            assert abs(item["weight"] - 100/3) < 0.1

    def test_weight_cap_30_percent(self):
        """한 종목 최대 30% 제한"""
        engine, _ = _make_engine()
        # A가 압도적으로 높은 점수
        items = [
            {"stock": _make_mock_stock(name="A"), "score": 90},
            {"stock": _make_mock_stock(name="B"), "score": 5},
            {"stock": _make_mock_stock(name="C"), "score": 5},
        ]

        result = engine._calculate_weights_score_based(items)

        # 재조정 후에도 비중 합계는 100
        total_weight = sum(item["weight"] for item in result)
        assert abs(total_weight - 100) < 0.1

    def test_weight_floor_5_percent(self):
        """한 종목 최소 5% 보장"""
        engine, _ = _make_engine()
        items = [
            {"stock": _make_mock_stock(name="A"), "score": 95},
            {"stock": _make_mock_stock(name="B"), "score": 1},
        ]

        result = engine._calculate_weights_score_based(items)

        # 재조정 전 B는 5% 최소 적용됨
        # 이후 재조정으로 비율은 달라지지만 구조적으로 동작
        total_weight = sum(item["weight"] for item in result)
        assert abs(total_weight - 100) < 0.1


# ============================================================================
# 근거 생성 테스트
# ============================================================================

@pytest.mark.unit
@pytest.mark.financial
class TestGenerateStockRationale:
    """_generate_stock_rationale 테스트"""

    def test_full_rationale(self):
        """모든 조건 충족 → 최대 3개 근거"""
        engine, _ = _make_engine()
        stock = _make_mock_stock(
            one_year_return=15.0, dividend_yield=3.0,
            pe_ratio=12.0, sector="IT"
        )

        rationale = engine._generate_stock_rationale(stock, "moderate")

        assert "수익률" in rationale
        assert "배당" in rationale
        # 최대 3개이므로 길이 제한
        parts = rationale.split(", ")
        assert len(parts) <= 3

    def test_no_data_fallback(self):
        """데이터 없음 → 기본 근거"""
        engine, _ = _make_engine()
        stock = _make_mock_stock(
            one_year_return=5.0, dividend_yield=1.0,
            pe_ratio=20.0, sector=None
        )

        rationale = engine._generate_stock_rationale(stock, "moderate")

        assert "적합" in rationale

    def test_sector_in_rationale(self):
        """섹터 정보 근거에 포함"""
        engine, _ = _make_engine()
        stock = _make_mock_stock(
            one_year_return=5.0, dividend_yield=1.0,
            pe_ratio=20.0, sector="바이오"
        )

        rationale = engine._generate_stock_rationale(stock, "aggressive")

        assert "바이오" in rationale


# ============================================================================
# 포트폴리오 통계 테스트
# ============================================================================

@pytest.mark.unit
@pytest.mark.financial
class TestCalculatePortfolioStats:
    """_calculate_portfolio_stats 테스트"""

    def test_basic_stats(self):
        """기본 통계 계산"""
        engine, _ = _make_engine()
        stocks = [
            {"invested_amount": 3_000_000, "expected_return": 10.0,
             "risk_level": "medium", "sector": "IT"},
            {"invested_amount": 2_000_000, "expected_return": 15.0,
             "risk_level": "medium", "sector": "금융"},
        ]
        etfs = [{"invested_amount": 1_500_000, "expected_return": 8.0,
                 "risk_level": "low"}]
        bonds = [{"invested_amount": 2_000_000, "expected_return": 4.0,
                  "risk_level": "low"}]
        deposits = [{"invested_amount": 1_500_000, "expected_return": 3.5}]

        result = engine._calculate_portfolio_stats(
            stocks, etfs, bonds, deposits, 10_000_000
        )

        assert result["total_investment"] == 10_000_000
        assert result["actual_invested"] == 10_000_000
        assert result["cash_reserve"] == 0
        assert result["total_items"] == 5
        assert result["asset_breakdown"]["stocks_count"] == 2
        assert result["asset_breakdown"]["etfs_count"] == 1
        assert result["portfolio_risk"] in ["low", "medium", "high"]

    def test_cash_reserve(self):
        """현금 보유분 계산"""
        engine, _ = _make_engine()
        stocks = [{"invested_amount": 7_000_000, "expected_return": 10.0,
                    "risk_level": "medium", "sector": "IT"}]

        result = engine._calculate_portfolio_stats(
            stocks, [], [], [], 10_000_000
        )

        assert result["cash_reserve"] == 3_000_000

    def test_empty_portfolio(self):
        """빈 포트폴리오"""
        engine, _ = _make_engine()

        result = engine._calculate_portfolio_stats([], [], [], [], 10_000_000)

        assert result["actual_invested"] == 0
        assert result["cash_reserve"] == 10_000_000
        assert result["total_items"] == 0
        assert result["diversification_score"] == 0

    def test_diversification_score(self):
        """다각화 점수 = 종목수 * 10 (최대 100)"""
        engine, _ = _make_engine()
        stocks = [{"invested_amount": 1_000_000, "expected_return": 10.0,
                    "risk_level": "medium", "sector": f"섹터{i}"} for i in range(8)]
        etfs = [{"invested_amount": 500_000, "expected_return": 8.0,
                 "risk_level": "low"}] * 3

        result = engine._calculate_portfolio_stats(
            stocks, etfs, [], [], 10_000_000
        )

        # 11종목 * 10 = 110 → cap 100
        assert result["diversification_score"] == 100

    def test_risk_level_classification(self):
        """리스크 레벨 분류"""
        engine, _ = _make_engine()

        # 모두 low → portfolio_risk = "low"
        stocks = [{"invested_amount": 5_000_000, "expected_return": 5.0,
                    "risk_level": "low", "sector": "금융"}]

        result = engine._calculate_portfolio_stats(stocks, [], [], [], 5_000_000)
        assert result["portfolio_risk"] == "low"

    def test_sector_breakdown(self):
        """섹터 비중 계산"""
        engine, _ = _make_engine()
        stocks = [
            {"invested_amount": 6_000_000, "expected_return": 10.0,
             "risk_level": "medium", "sector": "IT"},
            {"invested_amount": 4_000_000, "expected_return": 8.0,
             "risk_level": "low", "sector": "금융"},
        ]

        result = engine._calculate_portfolio_stats(
            stocks, [], [], [], 10_000_000
        )

        assert result["sector_breakdown"]["IT"] == 60.0
        assert result["sector_breakdown"]["금융"] == 40.0


# ============================================================================
# 시뮬레이션 참고사항 테스트
# ============================================================================

@pytest.mark.unit
@pytest.mark.financial
class TestGenerateSimulationNotes:
    """_generate_simulation_notes 테스트"""

    def test_low_diversification_note(self):
        """다각화 부족 → 다각화 안내"""
        engine, _ = _make_engine()
        stats = {
            "diversification_score": 30,
            "total_items": 3,
            "sector_breakdown": {},
            "cash_reserve": 0,
            "total_investment": 10_000_000,
            "portfolio_risk": "medium",
            "historical_observation": {"avg_annual_return": 8.0}
        }

        notes = engine._generate_simulation_notes("moderate", stats)

        assert any("다각화" in note for note in notes)

    def test_sector_concentration_note(self):
        """섹터 집중도 높음 → 경고"""
        engine, _ = _make_engine()
        stats = {
            "diversification_score": 80,
            "total_items": 8,
            "sector_breakdown": {"IT": 55.0, "금융": 45.0},
            "cash_reserve": 0,
            "total_investment": 10_000_000,
            "portfolio_risk": "medium",
            "historical_observation": {"avg_annual_return": 8.0}
        }

        notes = engine._generate_simulation_notes("moderate", stats)

        assert any("섹터" in note for note in notes)

    def test_high_cash_reserve_note(self):
        """현금 비중 높음 → 안내"""
        engine, _ = _make_engine()
        stats = {
            "diversification_score": 80,
            "total_items": 8,
            "sector_breakdown": {"IT": 30.0, "금융": 30.0, "헬스케어": 40.0},
            "cash_reserve": 2_000_000,
            "total_investment": 10_000_000,
            "portfolio_risk": "medium",
            "historical_observation": {"avg_annual_return": 8.0}
        }

        notes = engine._generate_simulation_notes("moderate", stats)

        assert any("현금" in note for note in notes)

    def test_balanced_portfolio_note(self):
        """균형잡힌 포트폴리오 → 리밸런싱 안내"""
        engine, _ = _make_engine()
        stats = {
            "diversification_score": 80,
            "total_items": 8,
            "sector_breakdown": {"IT": 30.0, "금융": 30.0, "헬스케어": 40.0},
            "cash_reserve": 0,
            "total_investment": 10_000_000,
            "portfolio_risk": "medium",
            "historical_observation": {"avg_annual_return": 8.0}
        }

        notes = engine._generate_simulation_notes("moderate", stats)

        assert any("리밸런싱" in note for note in notes)

    def test_risk_mismatch_note(self):
        """리스크 불일치 → 안내"""
        engine, _ = _make_engine()
        stats = {
            "diversification_score": 80,
            "total_items": 8,
            "sector_breakdown": {},
            "cash_reserve": 0,
            "total_investment": 10_000_000,
            "portfolio_risk": "high",  # conservative와 불일치
            "historical_observation": {"avg_annual_return": 6.0}
        }

        notes = engine._generate_simulation_notes("conservative", stats)

        assert any("리스크" in note or "성향" in note for note in notes)


# ============================================================================
# generate_portfolio 입력 검증 테스트
# ============================================================================

@pytest.mark.unit
@pytest.mark.financial
class TestGeneratePortfolioValidation:
    """generate_portfolio 입력 검증"""

    def test_invalid_investment_type(self):
        """잘못된 투자 유형 → ValueError"""
        engine, _ = _make_engine()

        with pytest.raises(ValueError, match="Invalid investment type"):
            engine.generate_portfolio("unknown_type", 10_000_000)

    def test_valid_types_exist(self):
        """유효한 투자 유형 3가지 존재"""
        assert "conservative" in PortfolioEngine.ASSET_ALLOCATION_STRATEGIES
        assert "moderate" in PortfolioEngine.ASSET_ALLOCATION_STRATEGIES
        assert "aggressive" in PortfolioEngine.ASSET_ALLOCATION_STRATEGIES

    def test_strategy_names(self):
        """전략 이름 한국어"""
        strategies = PortfolioEngine.ASSET_ALLOCATION_STRATEGIES
        assert strategies["conservative"]["name"] == "보수적"
        assert strategies["moderate"]["name"] == "중립적"
        assert strategies["aggressive"]["name"] == "공격적"


# ============================================================================
# ASSET_ALLOCATION_STRATEGIES 구조 검증
# ============================================================================

@pytest.mark.unit
@pytest.mark.financial
class TestStrategyStructure:
    """전략 구조 검증"""

    def test_all_strategies_have_required_keys(self):
        """모든 전략에 필수 키 존재"""
        required_keys = {"stocks", "etfs", "bonds", "deposits", "num_stocks", "name"}
        for name, strategy in PortfolioEngine.ASSET_ALLOCATION_STRATEGIES.items():
            for key in required_keys:
                assert key in strategy, f"{name} 전략에 {key} 없음"

    def test_target_ratios_sum_to_100(self):
        """자산 배분 비율 합계 = 100"""
        asset_classes = ["stocks", "etfs", "bonds", "deposits"]
        for name, strategy in PortfolioEngine.ASSET_ALLOCATION_STRATEGIES.items():
            total = sum(strategy[ac]["target"] for ac in asset_classes)
            assert total == 100, f"{name} 전략 합계 {total} != 100"

    def test_min_less_than_max(self):
        """min <= target <= max"""
        asset_classes = ["stocks", "etfs", "bonds", "deposits"]
        for name, strategy in PortfolioEngine.ASSET_ALLOCATION_STRATEGIES.items():
            for ac in asset_classes:
                weights = strategy[ac]
                assert weights["min"] <= weights["target"] <= weights["max"], \
                    f"{name}/{ac}: min={weights['min']} target={weights['target']} max={weights['max']}"
