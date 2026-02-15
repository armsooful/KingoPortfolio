"""
FinancialAnalyzer 단위 테스트 — 순수 계산 함수 (DB 불필요)

calculate_cagr, calculate_profit_margins, calculate_roe, calculate_roa,
calculate_debt_to_equity, calculate_debt_to_total_debt, calculate_fcf_margin,
_classify_investment_style
"""
import pytest
from unittest.mock import MagicMock

from app.services.financial_analyzer import FinancialAnalyzer


# ============================================================================
# Mock 헬퍼
# ============================================================================

def _mock_financial(**kwargs):
    """AlphaVantageFinancials를 흉내내는 MagicMock"""
    m = MagicMock()
    defaults = {
        "revenue": None,
        "gross_profit": None,
        "operating_income": None,
        "net_income": None,
        "total_assets": None,
        "total_equity": None,
        "total_liabilities": None,
        "short_term_debt": None,
        "long_term_debt": None,
        "cash_and_equivalents": None,
        "free_cash_flow": None,
    }
    defaults.update(kwargs)
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


# ============================================================================
# calculate_cagr (5개)
# ============================================================================

@pytest.mark.unit
class TestCalculateCagr:
    """CAGR 계산 테스트"""

    def test_normal_growth(self):
        """정상 성장: 100 → 200 in 3 years"""
        result = FinancialAnalyzer.calculate_cagr(100, 200, 3)
        assert result is not None
        assert abs(result - 25.99) < 0.1  # ~26%

    def test_no_growth(self):
        """성장 없음: start == end"""
        result = FinancialAnalyzer.calculate_cagr(100, 100, 3)
        assert result == 0.0

    def test_decline(self):
        """하락: 200 → 100 in 3 years"""
        result = FinancialAnalyzer.calculate_cagr(200, 100, 3)
        assert result is not None
        assert result < 0

    def test_zero_start(self):
        """start=0 → None"""
        assert FinancialAnalyzer.calculate_cagr(0, 100, 3) is None

    def test_negative_years(self):
        """years <= 0 → None"""
        assert FinancialAnalyzer.calculate_cagr(100, 200, 0) is None
        assert FinancialAnalyzer.calculate_cagr(100, 200, -1) is None


# ============================================================================
# calculate_profit_margins (4개)
# ============================================================================

@pytest.mark.unit
class TestCalculateProfitMargins:
    """이익률 계산 테스트"""

    def test_all_margins(self):
        """매출총이익률, 영업이익률, 순이익률 정상 계산"""
        f = _mock_financial(
            revenue=1_000_000,
            gross_profit=400_000,
            operating_income=200_000,
            net_income=150_000,
        )
        result = FinancialAnalyzer.calculate_profit_margins(f)
        assert result["gross_margin"] == 40.0
        assert result["operating_margin"] == 20.0
        assert result["net_margin"] == 15.0

    def test_zero_revenue(self):
        """revenue=0 → 전부 None"""
        f = _mock_financial(revenue=0, gross_profit=100)
        result = FinancialAnalyzer.calculate_profit_margins(f)
        assert result["gross_margin"] is None
        assert result["operating_margin"] is None
        assert result["net_margin"] is None

    def test_none_revenue(self):
        """revenue=None → 전부 None"""
        f = _mock_financial(revenue=None)
        result = FinancialAnalyzer.calculate_profit_margins(f)
        assert result == {"gross_margin": None, "operating_margin": None, "net_margin": None}

    def test_partial_data(self):
        """gross_profit=None이면 gross_margin만 None"""
        f = _mock_financial(
            revenue=1_000_000,
            gross_profit=None,
            operating_income=200_000,
            net_income=150_000,
        )
        result = FinancialAnalyzer.calculate_profit_margins(f)
        assert result["gross_margin"] is None
        assert result["operating_margin"] == 20.0
        assert result["net_margin"] == 15.0


# ============================================================================
# calculate_roe (3개)
# ============================================================================

@pytest.mark.unit
class TestCalculateRoe:
    """ROE 계산 테스트"""

    def test_normal_roe(self):
        """정상 ROE: 150K / 1M = 15%"""
        f = _mock_financial(net_income=150_000, total_equity=1_000_000)
        assert FinancialAnalyzer.calculate_roe(f) == 15.0

    def test_negative_equity(self):
        """자본 ≤ 0 → None"""
        f = _mock_financial(net_income=100, total_equity=-500)
        assert FinancialAnalyzer.calculate_roe(f) is None

    def test_none_net_income(self):
        """순이익 None → None"""
        f = _mock_financial(net_income=None, total_equity=1_000_000)
        assert FinancialAnalyzer.calculate_roe(f) is None


# ============================================================================
# calculate_roa (3개)
# ============================================================================

@pytest.mark.unit
class TestCalculateRoa:
    """ROA 계산 테스트"""

    def test_normal_roa(self):
        """정상 ROA: 100K / 2M = 5%"""
        f = _mock_financial(net_income=100_000, total_assets=2_000_000)
        assert FinancialAnalyzer.calculate_roa(f) == 5.0

    def test_zero_assets(self):
        """자산 ≤ 0 → None"""
        f = _mock_financial(net_income=100, total_assets=0)
        assert FinancialAnalyzer.calculate_roa(f) is None

    def test_none_inputs(self):
        """입력 None → None"""
        f = _mock_financial(net_income=None, total_assets=None)
        assert FinancialAnalyzer.calculate_roa(f) is None


# ============================================================================
# calculate_debt_to_equity (3개)
# ============================================================================

@pytest.mark.unit
class TestCalculateDebtToEquity:
    """부채비율 계산 테스트"""

    def test_normal_ratio(self):
        """부채 500K / 자본 1M = 50%"""
        f = _mock_financial(total_liabilities=500_000, total_equity=1_000_000)
        assert FinancialAnalyzer.calculate_debt_to_equity(f) == 50.0

    def test_high_leverage(self):
        """고레버리지: 부채 3M / 자본 1M = 300%"""
        f = _mock_financial(total_liabilities=3_000_000, total_equity=1_000_000)
        assert FinancialAnalyzer.calculate_debt_to_equity(f) == 300.0

    def test_zero_equity(self):
        """자본 ≤ 0 → None"""
        f = _mock_financial(total_liabilities=500_000, total_equity=0)
        assert FinancialAnalyzer.calculate_debt_to_equity(f) is None


# ============================================================================
# calculate_debt_to_total_debt (순부채비율) (3개)
# ============================================================================

@pytest.mark.unit
class TestCalculateNetDebtRatio:
    """순부채비율 계산 테스트"""

    def test_net_cash_positive(self):
        """현금 > 부채 → 음수 비율 (순현금)"""
        f = _mock_financial(
            short_term_debt=100_000, long_term_debt=200_000,
            cash_and_equivalents=500_000, total_equity=1_000_000,
        )
        result = FinancialAnalyzer.calculate_debt_to_total_debt(f)
        # (300K - 500K) / 1M = -20%
        assert result == -20.0

    def test_net_debt_positive(self):
        """부채 > 현금 → 양수 비율"""
        f = _mock_financial(
            short_term_debt=300_000, long_term_debt=400_000,
            cash_and_equivalents=200_000, total_equity=1_000_000,
        )
        result = FinancialAnalyzer.calculate_debt_to_total_debt(f)
        # (700K - 200K) / 1M = 50%
        assert result == 50.0

    def test_zero_equity(self):
        """자본 ≤ 0 → None"""
        f = _mock_financial(
            short_term_debt=100, long_term_debt=200,
            cash_and_equivalents=50, total_equity=0,
        )
        assert FinancialAnalyzer.calculate_debt_to_total_debt(f) is None


# ============================================================================
# calculate_fcf_margin (3개)
# ============================================================================

@pytest.mark.unit
class TestCalculateFcfMargin:
    """FCF 마진 계산 테스트"""

    def test_normal_margin(self):
        """정상: FCF 200K / 매출 1M = 20%"""
        f = _mock_financial(free_cash_flow=200_000, revenue=1_000_000)
        assert FinancialAnalyzer.calculate_fcf_margin(f) == 20.0

    def test_negative_fcf(self):
        """음수 FCF (투자 집중) → 음수 마진"""
        f = _mock_financial(free_cash_flow=-100_000, revenue=1_000_000)
        assert FinancialAnalyzer.calculate_fcf_margin(f) == -10.0

    def test_none_fcf(self):
        """FCF None → None"""
        f = _mock_financial(free_cash_flow=None, revenue=1_000_000)
        assert FinancialAnalyzer.calculate_fcf_margin(f) is None


# ============================================================================
# _classify_investment_style (5개)
# ============================================================================

@pytest.mark.unit
class TestClassifyInvestmentStyle:
    """투자 스타일 분류 테스트"""

    def _analysis(self, revenue_5y=0, eps_5y=0, roe=0, div_yield=0):
        return {
            "growth_metrics": {
                "revenue_cagr_5y": revenue_5y,
                "eps_cagr_5y": eps_5y,
            },
            "profitability": {"roe": roe},
            "dividend_metrics": {"current_dividend_yield": div_yield},
        }

    def test_high_growth_high_roe(self):
        """고수익 성장주: 성장 ≥10% + ROE ≥20%"""
        result = FinancialAnalyzer._classify_investment_style(
            self._analysis(revenue_5y=15, eps_5y=12, roe=25)
        )
        assert result["style"] == "고수익 성장주"

    def test_growth_stock(self):
        """성장주: 성장 ≥10% + ROE < 20%"""
        result = FinancialAnalyzer._classify_investment_style(
            self._analysis(revenue_5y=15, eps_5y=12, roe=10)
        )
        assert result["style"] == "성장주"

    def test_mature_growth(self):
        """성숙한 성장주: 성장 5-10% + ROE ≥20%"""
        result = FinancialAnalyzer._classify_investment_style(
            self._analysis(revenue_5y=7, eps_5y=3, roe=22)
        )
        assert result["style"] == "성숙한 성장주"

    def test_dividend_stock(self):
        """배당주: 배당 ≥3%"""
        result = FinancialAnalyzer._classify_investment_style(
            self._analysis(revenue_5y=2, eps_5y=2, roe=10, div_yield=4.5)
        )
        assert result["style"] == "배당주"

    def test_general_stock(self):
        """일반 기업: 특별 조건 없음"""
        result = FinancialAnalyzer._classify_investment_style(
            self._analysis(revenue_5y=2, eps_5y=2, roe=8, div_yield=1)
        )
        assert result["style"] == "일반 기업"
