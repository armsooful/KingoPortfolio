"""
BacktestingEngine 단위 테스트

순수 계산 로직 위주 테스트 (DB 의존 최소화)
- run_backtest 입력 검증
- _should_rebalance 각 주기별
- _calculate_metrics 수익률/변동성/샤프/MDD 정확성
- _initialize_portfolio 구조 파싱
"""
import pytest
import math
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from app.services.backtesting import BacktestingEngine


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def engine():
    """DB 세션 mock으로 엔진 생성"""
    mock_db = MagicMock()
    return BacktestingEngine(mock_db)


@pytest.fixture
def sample_portfolio():
    """기본 포트폴리오 구조"""
    return {
        "stocks": [
            {"ticker": "005930", "shares": 10, "current_price": 78500},
            {"ticker": "000660", "shares": 5, "current_price": 145000},
        ],
        "etfs": [
            {"ticker": "069500", "shares": 20, "current_price": 35000},
        ],
        "bonds": [
            {"id": "bond_1", "invested_amount": 5_000_000, "interest_rate": 3.5},
        ],
        "deposits": [
            {"id": "dep_1", "invested_amount": 10_000_000, "interest_rate": 2.0},
        ],
    }


# ============================================================================
# run_backtest 입력 검증
# ============================================================================

@pytest.mark.unit
class TestRunBacktestValidation:
    """run_backtest 입력값 검증"""

    def test_end_before_start_raises(self, engine, sample_portfolio):
        """종료일이 시작일보다 이전 → ValueError"""
        with pytest.raises(ValueError, match="종료 날짜는 시작 날짜보다"):
            engine.run_backtest(
                sample_portfolio,
                start_date=datetime(2025, 6, 1),
                end_date=datetime(2025, 1, 1),
                initial_investment=10_000_000,
            )

    def test_same_date_raises(self, engine, sample_portfolio):
        """시작일 == 종료일 → ValueError"""
        d = datetime(2025, 1, 1)
        with pytest.raises(ValueError, match="종료 날짜는 시작 날짜보다"):
            engine.run_backtest(sample_portfolio, d, d, 10_000_000)

    def test_period_under_30_days_raises(self, engine, sample_portfolio):
        """30일 미만 기간 → ValueError"""
        with pytest.raises(ValueError, match="최소 30일"):
            engine.run_backtest(
                sample_portfolio,
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2025, 1, 20),
                initial_investment=10_000_000,
            )

    def test_exactly_30_days_ok(self, engine, sample_portfolio):
        """정확히 30일 → 정상 실행"""
        result = engine.run_backtest(
            sample_portfolio,
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 1, 31),
            initial_investment=10_000_000,
        )
        assert "total_return" in result
        assert "daily_values" in result


# ============================================================================
# _should_rebalance
# ============================================================================

@pytest.mark.unit
class TestShouldRebalance:
    """리밸런싱 주기 판단 로직"""

    def test_none_never_rebalances(self, engine):
        base = datetime(2025, 1, 1)
        assert engine._should_rebalance(base + timedelta(days=365), base, "none") is False

    def test_monthly_before_30(self, engine):
        base = datetime(2025, 1, 1)
        assert engine._should_rebalance(base + timedelta(days=29), base, "monthly") is False

    def test_monthly_at_30(self, engine):
        base = datetime(2025, 1, 1)
        assert engine._should_rebalance(base + timedelta(days=30), base, "monthly") is True

    def test_quarterly_before_90(self, engine):
        base = datetime(2025, 1, 1)
        assert engine._should_rebalance(base + timedelta(days=89), base, "quarterly") is False

    def test_quarterly_at_90(self, engine):
        base = datetime(2025, 1, 1)
        assert engine._should_rebalance(base + timedelta(days=90), base, "quarterly") is True

    def test_yearly_before_365(self, engine):
        base = datetime(2025, 1, 1)
        assert engine._should_rebalance(base + timedelta(days=364), base, "yearly") is False

    def test_yearly_at_365(self, engine):
        base = datetime(2025, 1, 1)
        assert engine._should_rebalance(base + timedelta(days=365), base, "yearly") is True


# ============================================================================
# _initialize_portfolio
# ============================================================================

@pytest.mark.unit
class TestInitializePortfolio:
    """포트폴리오 초기 구성 파싱"""

    def test_stocks_parsed(self, engine, sample_portfolio):
        holdings = engine._initialize_portfolio(sample_portfolio, 10_000_000)
        assert "stock_005930" in holdings
        assert holdings["stock_005930"]["shares"] == 10
        assert holdings["stock_005930"]["type"] == "stock"

    def test_etfs_parsed(self, engine, sample_portfolio):
        holdings = engine._initialize_portfolio(sample_portfolio, 10_000_000)
        assert "etf_069500" in holdings
        assert holdings["etf_069500"]["shares"] == 20

    def test_bonds_parsed(self, engine, sample_portfolio):
        holdings = engine._initialize_portfolio(sample_portfolio, 10_000_000)
        assert "bond_bond_1" in holdings
        assert holdings["bond_bond_1"]["amount"] == 5_000_000

    def test_deposits_parsed(self, engine, sample_portfolio):
        holdings = engine._initialize_portfolio(sample_portfolio, 10_000_000)
        assert "deposit_dep_1" in holdings
        assert holdings["deposit_dep_1"]["annual_rate"] == 2.0

    def test_nested_portfolio_unwrap(self, engine, sample_portfolio):
        """중첩 구조 portfolio.portfolio 처리"""
        wrapped = {"portfolio": sample_portfolio}
        holdings = engine._initialize_portfolio(wrapped, 10_000_000)
        assert "stock_005930" in holdings

    def test_empty_portfolio(self, engine):
        holdings = engine._initialize_portfolio({}, 10_000_000)
        assert holdings == {}


# ============================================================================
# _calculate_metrics
# ============================================================================

@pytest.mark.unit
class TestCalculateMetrics:
    """성과 지표 계산 정확성"""

    def test_total_return_positive(self, engine):
        """상승 시나리오 수익률"""
        daily_values = [
            {"date": "2025-01-01", "value": 10_000_000, "return": 0},
            {"date": "2025-02-01", "value": 11_000_000, "return": 10},
        ]
        metrics = engine._calculate_metrics(daily_values, 10_000_000, 31)
        assert metrics["total_return"] == 10.0

    def test_total_return_negative(self, engine):
        """하락 시나리오 수익률"""
        daily_values = [
            {"date": "2025-01-01", "value": 10_000_000, "return": 0},
            {"date": "2025-02-01", "value": 9_000_000, "return": -10},
        ]
        metrics = engine._calculate_metrics(daily_values, 10_000_000, 31)
        assert metrics["total_return"] == -10.0

    def test_zero_return(self, engine):
        """수익률 0%"""
        daily_values = [
            {"date": "2025-01-01", "value": 10_000_000, "return": 0},
            {"date": "2025-02-01", "value": 10_000_000, "return": 0},
        ]
        metrics = engine._calculate_metrics(daily_values, 10_000_000, 31)
        assert metrics["total_return"] == 0.0

    def test_volatility_flat(self, engine):
        """일정한 가격 → 변동성 0"""
        daily_values = [{"date": f"d{i}", "value": 100, "return": 0} for i in range(10)]
        metrics = engine._calculate_metrics(daily_values, 100, 10)
        assert metrics["volatility"] == 0.0

    def test_volatility_nonzero(self, engine):
        """가격 변동 있으면 변동성 > 0"""
        daily_values = [
            {"date": "d0", "value": 100, "return": 0},
            {"date": "d1", "value": 105, "return": 5},
            {"date": "d2", "value": 95, "return": -5},
            {"date": "d3", "value": 102, "return": 2},
        ]
        metrics = engine._calculate_metrics(daily_values, 100, 3)
        assert metrics["volatility"] > 0

    def test_sharpe_ratio_formula(self, engine):
        """샤프 비율 = (연환산수익률 - 2%) / 변동성"""
        daily_values = [
            {"date": "d0", "value": 10_000_000, "return": 0},
        ]
        # 365일 동안 20% 상승
        for i in range(1, 366):
            v = 10_000_000 * (1 + 0.20 * i / 365)
            daily_values.append({"date": f"d{i}", "value": v, "return": 0})

        metrics = engine._calculate_metrics(daily_values, 10_000_000, 365)
        # 무위험 수익률 2%, 연환산 수익률 ≈ 20%
        assert metrics["sharpe_ratio"] > 0
        assert metrics["annualized_return"] == pytest.approx(20.0, abs=1.0)

    def test_max_drawdown(self, engine):
        """MDD: 고점 대비 최대 하락폭"""
        daily_values = [
            {"date": "d0", "value": 100, "return": 0},
            {"date": "d1", "value": 120, "return": 20},  # 고점
            {"date": "d2", "value": 96, "return": -4},    # 120→96 = -20%
            {"date": "d3", "value": 110, "return": 10},
        ]
        metrics = engine._calculate_metrics(daily_values, 100, 3)
        assert metrics["max_drawdown"] == 20.0

    def test_max_drawdown_zero_no_decline(self, engine):
        """지속 상승 → MDD 0"""
        daily_values = [
            {"date": "d0", "value": 100, "return": 0},
            {"date": "d1", "value": 110, "return": 10},
            {"date": "d2", "value": 120, "return": 20},
        ]
        metrics = engine._calculate_metrics(daily_values, 100, 2)
        assert metrics["max_drawdown"] == 0.0

    def test_single_daily_value_no_crash(self, engine):
        """일별 데이터 1개 — 에러 없이 처리"""
        daily_values = [{"date": "d0", "value": 100, "return": 0}]
        metrics = engine._calculate_metrics(daily_values, 100, 1)
        assert metrics["total_return"] == 0.0
        assert metrics["volatility"] == 0.0
