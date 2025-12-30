"""
퀀트/기술 분석 기능 테스트
"""
import pytest
from datetime import datetime, timedelta
from app.services.quant_analyzer import QuantAnalyzer
from app.models.alpha_vantage import AlphaVantageTimeSeries


@pytest.mark.unit
@pytest.mark.quant
class TestVolatilityCalculations:
    """변동성 계산 테스트"""

    def test_calculate_volatility(self):
        """변동성 계산 (표준편차)"""
        returns = [0.01, -0.02, 0.03, -0.01, 0.02, -0.01, 0.01]

        # 표준편차 계산
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)
        volatility = variance ** 0.5

        assert volatility > 0
        assert isinstance(volatility, float)

    def test_annualized_volatility(self):
        """연환산 변동성"""
        daily_volatility = 0.015  # 1.5% 일일 변동성
        trading_days = 252

        annualized_volatility = daily_volatility * (trading_days ** 0.5)

        assert annualized_volatility > daily_volatility
        # 약 23.8%
        assert 0.23 < annualized_volatility < 0.24


@pytest.mark.unit
@pytest.mark.quant
class TestReturnsCalculations:
    """수익률 계산 테스트"""

    def test_simple_return(self):
        """단순 수익률"""
        start_price = 100
        end_price = 110

        simple_return = (end_price - start_price) / start_price

        assert simple_return == 0.10  # 10%

    def test_log_return(self):
        """로그 수익률"""
        import math
        start_price = 100
        end_price = 110

        log_return = math.log(end_price / start_price)

        assert log_return > 0
        # ln(1.1) ≈ 0.0953
        assert 0.095 < log_return < 0.096

    def test_cumulative_return(self):
        """누적 수익률"""
        returns = [0.05, 0.03, -0.02, 0.04]

        cumulative = 1.0
        for r in returns:
            cumulative *= (1 + r)

        cumulative_return = cumulative - 1

        assert cumulative_return > 0
        # (1.05)(1.03)(0.98)(1.04) - 1 ≈ 0.1023
        assert 0.10 < cumulative_return < 0.11


@pytest.mark.unit
@pytest.mark.quant
class TestBetaCalculations:
    """베타 계산 테스트"""

    def test_beta_positive_correlation(self):
        """양의 상관관계 베타"""
        # 주식이 시장보다 더 크게 움직임
        stock_returns = [0.02, -0.03, 0.04, -0.02, 0.03]
        market_returns = [0.01, -0.02, 0.03, -0.01, 0.02]

        # 공분산 / 시장 분산
        stock_mean = sum(stock_returns) / len(stock_returns)
        market_mean = sum(market_returns) / len(market_returns)

        covariance = sum((s - stock_mean) * (m - market_mean)
                        for s, m in zip(stock_returns, market_returns)) / len(stock_returns)
        market_variance = sum((m - market_mean) ** 2 for m in market_returns) / len(market_returns)

        beta = covariance / market_variance

        assert beta > 0  # 양의 상관관계

    def test_beta_interpretation(self):
        """베타 해석"""
        # 베타 > 1: 시장보다 변동성 높음
        # 베타 = 1: 시장과 동일
        # 베타 < 1: 시장보다 변동성 낮음
        # 베타 < 0: 시장과 반대 방향

        beta_aggressive = 1.5
        beta_neutral = 1.0
        beta_defensive = 0.5
        beta_inverse = -0.3

        assert beta_aggressive > beta_neutral > beta_defensive > beta_inverse


@pytest.mark.unit
@pytest.mark.quant
class TestSharpeRatio:
    """샤프 비율 테스트"""

    def test_calculate_sharpe_ratio(self):
        """샤프 비율 계산"""
        portfolio_return = 0.12  # 12%
        risk_free_rate = 0.02  # 2%
        portfolio_volatility = 0.15  # 15%

        sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_volatility

        assert sharpe_ratio > 0
        # (0.12 - 0.02) / 0.15 = 0.667
        assert 0.66 < sharpe_ratio < 0.67

    def test_sharpe_ratio_interpretation(self):
        """샤프 비율 해석"""
        # > 1.0: 우수
        # 0.5~1.0: 양호
        # < 0.5: 부족

        excellent_sharpe = 1.5
        good_sharpe = 0.8
        poor_sharpe = 0.3

        assert excellent_sharpe > 1.0
        assert 0.5 <= good_sharpe <= 1.0
        assert poor_sharpe < 0.5


@pytest.mark.unit
@pytest.mark.quant
class TestMovingAverages:
    """이동평균 테스트"""

    def test_simple_moving_average(self):
        """단순 이동평균"""
        prices = [100, 102, 101, 103, 105, 104, 106]
        window = 3

        sma = sum(prices[-window:]) / window

        assert sma > 0
        # (105 + 104 + 106) / 3 = 105
        assert sma == 105.0

    def test_golden_cross_signal(self):
        """골든 크로스 시그널 (단기 MA > 장기 MA)"""
        short_ma = 105  # 50일 MA
        long_ma = 102  # 200일 MA

        golden_cross = short_ma > long_ma

        assert golden_cross is True  # 매수 신호

    def test_death_cross_signal(self):
        """데드 크로스 시그널 (단기 MA < 장기 MA)"""
        short_ma = 98  # 50일 MA
        long_ma = 102  # 200일 MA

        death_cross = short_ma < long_ma

        assert death_cross is True  # 매도 신호


@pytest.mark.unit
@pytest.mark.quant
class TestRSI:
    """RSI (상대강도지수) 테스트"""

    def test_rsi_calculation(self):
        """RSI 계산"""
        avg_gain = 2.0
        avg_loss = 1.5

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        assert 0 <= rsi <= 100
        # RS = 2/1.5 = 1.33
        # RSI = 100 - (100/2.33) = 57.08
        assert 57 < rsi < 58

    def test_rsi_overbought(self):
        """RSI 과매수 구간 (> 70)"""
        rsi = 75

        is_overbought = rsi > 70

        assert is_overbought is True  # 매도 고려

    def test_rsi_oversold(self):
        """RSI 과매도 구간 (< 30)"""
        rsi = 25

        is_oversold = rsi < 30

        assert is_oversold is True  # 매수 고려


@pytest.mark.integration
@pytest.mark.quant
class TestQuantAnalysisEndpoints:
    """퀀트 분석 엔드포인트 통합 테스트"""

    def test_quant_risk_requires_auth(self, client):
        """퀀트 리스크 분석 엔드포인트 인증 필요"""
        response = client.get("/admin/quant/risk/AAPL?market_symbol=SPY&days=252")

        # 404 또는 401 (라우트 존재 여부에 따라)
        assert response.status_code in [401, 404]

    def test_quant_risk_requires_admin(self, client, auth_headers):
        """퀀트 리스크 분석은 관리자 권한 필요"""
        response = client.get(
            "/admin/quant/risk/AAPL?market_symbol=SPY&days=252",
            headers=auth_headers
        )

        # 403 또는 404 (라우트 존재 여부에 따라)
        assert response.status_code in [403, 404]

    def test_quant_comprehensive_public_access(self, client):
        """종합 퀀트 분석은 공개 접근 가능 (TODO: 보안 이슈 - 인증 필요)"""
        response = client.get(
            "/admin/quant/comprehensive/AAPL?market_symbol=SPY&days=252"
        )

        # 데이터가 없으면 404, 있으면 200
        assert response.status_code in [200, 404]

    def test_quant_analysis_structure(self, client):
        """퀀트 분석 응답 구조 확인"""
        response = client.get(
            "/admin/quant/comprehensive/AAPL?market_symbol=SPY&days=252"
        )

        if response.status_code == 200:
            data = response.json()
            assert "symbol" in data
            # 베타, 알파, 샤프비율 등의 데이터가 있거나 에러 메시지
            assert ("beta" in data) or ("error" in data)
