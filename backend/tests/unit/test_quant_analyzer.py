"""
QuantAnalyzer 단위 테스트 — 순수 계산 함수 (DB 불필요)

기술 지표 11개 + 리스크 지표 6개. 모든 함수가 list 입출력이라 mock 불필요.
"""
import pytest
from datetime import date, timedelta

from app.services.quant_analyzer import QuantAnalyzer


# ============================================================================
# 테스트 데이터 헬퍼
# ============================================================================

def _prices(values, start_date=None):
    """[(date, price), ...] 형태 생성"""
    start = start_date or date(2025, 1, 1)
    return [(start + timedelta(days=i), v) for i, v in enumerate(values)]


def _ohlcv(n, base_close=100, volatility=5, base_volume=1_000_000):
    """OHLCV dict 리스트 생성 (단순 시뮬레이션)"""
    import random
    random.seed(42)
    data = []
    close = base_close
    for i in range(n):
        change = random.uniform(-volatility, volatility)
        close = max(close + change, 1)
        high = close + abs(random.uniform(0, volatility))
        low = close - abs(random.uniform(0, volatility))
        low = max(low, 0.5)
        data.append({
            "date": date(2025, 1, 1) + timedelta(days=i),
            "open": round(close - change / 2, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close, 2),
            "volume": base_volume + random.randint(-100000, 100000),
        })
    return data


# 공통 데이터 (252일)
_PRICES_252 = _prices([100 + i * 0.1 + (i % 7) for i in range(252)])
_OHLCV_252 = _ohlcv(252)


# ============================================================================
# calculate_returns (2개)
# ============================================================================

@pytest.mark.unit
class TestCalculateReturns:
    """일간 수익률 계산"""

    def test_normal_returns(self):
        """정상 수익률 계산"""
        prices = _prices([100, 105, 103])
        returns = QuantAnalyzer.calculate_returns(prices)
        assert len(returns) == 2
        assert abs(returns[0][1] - 5.0) < 0.01  # (105-100)/100 * 100
        assert returns[1][1] < 0  # 103 < 105

    def test_insufficient_data(self):
        """데이터 1개 → 빈 리스트"""
        assert QuantAnalyzer.calculate_returns(_prices([100])) == []


# ============================================================================
# calculate_moving_averages (3개)
# ============================================================================

@pytest.mark.unit
class TestMovingAverages:
    """이동평균선 계산"""

    def test_basic_ma(self):
        """MA20 계산 정확성"""
        prices = _prices([float(i) for i in range(1, 31)])  # 1~30
        result = QuantAnalyzer.calculate_moving_averages(prices, [20])
        assert "MA20" in result["moving_averages"]
        # MA20 of last 20 values (11~30): avg = 20.5
        assert result["moving_averages"]["MA20"]["value"] == 20.5

    def test_golden_cross_detection(self):
        """골든크로스/데드크로스 시그널"""
        result = QuantAnalyzer.calculate_moving_averages(_PRICES_252)
        assert "signal" in result

    def test_empty_prices(self):
        """빈 입력 → error"""
        result = QuantAnalyzer.calculate_moving_averages([])
        assert "error" in result


# ============================================================================
# calculate_rsi (3개)
# ============================================================================

@pytest.mark.unit
class TestRsi:
    """RSI 계산"""

    def test_overbought(self):
        """연속 상승 → RSI > 70 (과매수)"""
        prices = _prices([100 + i * 2 for i in range(20)])
        result = QuantAnalyzer.calculate_rsi(prices)
        assert result["rsi"] > 70
        assert result["status"] == "과매수 구간"

    def test_oversold(self):
        """연속 하락 → RSI < 30 (과매도)"""
        prices = _prices([200 - i * 3 for i in range(20)])
        result = QuantAnalyzer.calculate_rsi(prices)
        assert result["rsi"] < 30
        assert result["status"] == "과매도 구간"

    def test_insufficient_data(self):
        """데이터 부족 → error"""
        result = QuantAnalyzer.calculate_rsi(_prices([100, 101, 102]))
        assert "error" in result


# ============================================================================
# calculate_bollinger_bands (3개)
# ============================================================================

@pytest.mark.unit
class TestBollingerBands:
    """볼린저밴드 계산"""

    def test_basic_bands(self):
        """상단 > 중간 > 하단"""
        result = QuantAnalyzer.calculate_bollinger_bands(_PRICES_252)
        assert result["upper_band"] > result["middle_band"] > result["lower_band"]
        assert 0 <= result["percent_b"] <= 2  # 약간 벗어날 수 있음

    def test_bandwidth_positive(self):
        """밴드폭 > 0"""
        result = QuantAnalyzer.calculate_bollinger_bands(_PRICES_252)
        assert result["bandwidth"] > 0

    def test_insufficient_data(self):
        """데이터 부족 → error"""
        result = QuantAnalyzer.calculate_bollinger_bands(_prices([100] * 5))
        assert "error" in result


# ============================================================================
# calculate_macd (3개)
# ============================================================================

@pytest.mark.unit
class TestMacd:
    """MACD 계산"""

    def test_basic_macd(self):
        """MACD, signal, histogram 필드 존재"""
        result = QuantAnalyzer.calculate_macd(_PRICES_252)
        assert "macd" in result
        assert "signal" in result
        assert "histogram" in result
        assert "status" in result

    def test_uptrend_histogram(self):
        """강한 상승 추세 → MACD > signal (양의 histogram 또는 0)"""
        prices = _prices([50 + i * 0.5 for i in range(100)])
        result = QuantAnalyzer.calculate_macd(prices)
        if "error" not in result:
            assert result["macd"] >= result["signal"]

    def test_insufficient_data(self):
        """데이터 부족 → error"""
        result = QuantAnalyzer.calculate_macd(_prices([100] * 10))
        assert "error" in result


# ============================================================================
# calculate_stochastic (3개)
# ============================================================================

@pytest.mark.unit
class TestStochastic:
    """Stochastic Oscillator"""

    def test_basic_output(self):
        """K, D 값 0-100 범위"""
        result = QuantAnalyzer.calculate_stochastic(_OHLCV_252)
        assert 0 <= result["k"] <= 100
        assert 0 <= result["d"] <= 100
        assert "status" in result

    def test_overbought_region(self):
        """연속 상승 OHLCV → K > 80"""
        ohlcv = []
        for i in range(30):
            p = 100 + i * 3
            ohlcv.append({
                "date": date(2025, 1, 1) + timedelta(days=i),
                "open": p - 1, "high": p + 1, "low": p - 2, "close": p,
                "volume": 1_000_000,
            })
        result = QuantAnalyzer.calculate_stochastic(ohlcv)
        assert result["k"] > 80

    def test_insufficient_data(self):
        """데이터 부족 → error"""
        result = QuantAnalyzer.calculate_stochastic(_ohlcv(5))
        assert "error" in result


# ============================================================================
# calculate_atr (2개)
# ============================================================================

@pytest.mark.unit
class TestAtr:
    """ATR (Average True Range)"""

    def test_basic_output(self):
        """ATR > 0, atr_ratio > 0"""
        result = QuantAnalyzer.calculate_atr(_OHLCV_252)
        assert result["atr"] > 0
        assert result["atr_ratio"] > 0
        assert "interpretation" in result

    def test_insufficient_data(self):
        """데이터 부족 → error"""
        result = QuantAnalyzer.calculate_atr(_ohlcv(5))
        assert "error" in result


# ============================================================================
# calculate_adx (2개)
# ============================================================================

@pytest.mark.unit
class TestAdx:
    """ADX (Average Directional Index)"""

    def test_basic_output(self):
        """ADX 0-100 범위, plus_di/minus_di 존재"""
        result = QuantAnalyzer.calculate_adx(_OHLCV_252)
        assert 0 <= result["adx"] <= 100
        assert result["plus_di"] >= 0
        assert result["minus_di"] >= 0
        assert "trend_strength" in result
        assert "direction" in result

    def test_insufficient_data(self):
        """데이터 부족 → error"""
        result = QuantAnalyzer.calculate_adx(_ohlcv(10))
        assert "error" in result


# ============================================================================
# calculate_obv (3개)
# ============================================================================

@pytest.mark.unit
class TestObv:
    """OBV (On-Balance Volume)"""

    def test_basic_output(self):
        """OBV 정수, trend 존재"""
        result = QuantAnalyzer.calculate_obv(_OHLCV_252)
        assert isinstance(result["obv"], (int, float))
        assert "trend" in result

    def test_uptrend_obv(self):
        """연속 상승 → OBV 양수"""
        ohlcv = []
        for i in range(30):
            ohlcv.append({
                "date": date(2025, 1, 1) + timedelta(days=i),
                "open": 100 + i, "high": 102 + i, "low": 99 + i,
                "close": 101 + i,
                "volume": 1_000_000,
            })
        result = QuantAnalyzer.calculate_obv(ohlcv)
        assert result["obv"] > 0

    def test_insufficient_data(self):
        """데이터 부족 → error"""
        result = QuantAnalyzer.calculate_obv(_ohlcv(3))
        assert "error" in result


# ============================================================================
# calculate_ma_alignment (3개)
# ============================================================================

@pytest.mark.unit
class TestMaAlignment:
    """이동평균 정배열/역배열"""

    def test_bull_alignment(self):
        """강한 상승 → 정배열"""
        prices = _prices([50 + i * 0.5 for i in range(252)])
        result = QuantAnalyzer.calculate_ma_alignment(prices)
        assert result["alignment"] == "정배열"
        assert result["sma20"] > result["sma50"] > result["sma200"]

    def test_bear_alignment(self):
        """강한 하락 → 역배열"""
        prices = _prices([200 - i * 0.5 for i in range(252)])
        result = QuantAnalyzer.calculate_ma_alignment(prices)
        assert result["alignment"] == "역배열"
        assert result["sma20"] < result["sma50"] < result["sma200"]

    def test_insufficient_data(self):
        """200일 미만 → error"""
        result = QuantAnalyzer.calculate_ma_alignment(_prices([100] * 100))
        assert "error" in result


# ============================================================================
# calculate_52week_position (3개)
# ============================================================================

@pytest.mark.unit
class TestWeek52Position:
    """52주 고저 대비 위치"""

    def test_at_high(self):
        """52주 최고점 → position=100"""
        prices = _prices([50 + i for i in range(100)])
        result = QuantAnalyzer.calculate_52week_position(prices)
        assert result["position"] == 100.0
        assert result["status"] == "52주 고점 근접"

    def test_at_low(self):
        """52주 최저점 → position=0"""
        prices = _prices([200 - i for i in range(100)])
        result = QuantAnalyzer.calculate_52week_position(prices)
        assert result["position"] == 0.0
        assert result["status"] == "52주 저점 근접"

    def test_flat_price(self):
        """변동 없음 → position=50"""
        prices = _prices([100] * 30)
        result = QuantAnalyzer.calculate_52week_position(prices)
        assert result["position"] == 50.0


# ============================================================================
# calculate_volatility (2개)
# ============================================================================

@pytest.mark.unit
class TestVolatility:
    """변동성 계산"""

    def test_zero_volatility(self):
        """수익률 동일 → 변동성 0"""
        returns = [(date(2025, 1, i + 1), 1.0) for i in range(30)]
        assert QuantAnalyzer.calculate_volatility(returns) == 0.0

    def test_annualized(self):
        """연율화 vs 비연율화"""
        returns = QuantAnalyzer.calculate_returns(_PRICES_252)
        vol_annual = QuantAnalyzer.calculate_volatility(returns, annualize=True)
        vol_daily = QuantAnalyzer.calculate_volatility(returns, annualize=False)
        assert vol_annual > vol_daily  # 연율화 → 더 큰 값


# ============================================================================
# calculate_max_drawdown (2개)
# ============================================================================

@pytest.mark.unit
class TestMaxDrawdown:
    """최대 낙폭 (MDD)"""

    def test_known_drawdown(self):
        """100 → 200 → 150 → MDD = -25%"""
        prices = _prices([100, 120, 150, 200, 180, 150, 170])
        result = QuantAnalyzer.calculate_max_drawdown(prices)
        assert result["max_drawdown"] == -25.0  # (150-200)/200

    def test_no_drawdown(self):
        """연속 상승 → MDD = 0"""
        prices = _prices([100, 110, 120, 130])
        result = QuantAnalyzer.calculate_max_drawdown(prices)
        assert result["max_drawdown"] == 0


# ============================================================================
# calculate_beta (2개)
# ============================================================================

@pytest.mark.unit
class TestBeta:
    """베타 계산"""

    def test_same_returns(self):
        """종목==시장 → 베타 ≈ 1"""
        base = date(2025, 1, 1)
        returns = [(base + timedelta(days=i), float(i % 5 - 2)) for i in range(100)]
        result = QuantAnalyzer.calculate_beta(returns, returns)
        assert abs(result["beta"] - 1.0) < 0.01

    def test_insufficient_data(self):
        """데이터 부족 → error"""
        result = QuantAnalyzer.calculate_beta(
            [(date(2025, 1, 1), 1.0)],
            [(date(2025, 1, 1), 1.0)],
        )
        assert "error" in result


# ============================================================================
# calculate_sharpe_ratio (2개)
# ============================================================================

@pytest.mark.unit
class TestSharpeRatio:
    """샤프 비율"""

    def test_positive_sharpe(self):
        """양의 수익률 → 양의 샤프"""
        base = date(2025, 1, 1)
        returns = [(base + timedelta(days=i), 0.1) for i in range(100)]
        result = QuantAnalyzer.calculate_sharpe_ratio(returns, risk_free_rate=2.0)
        assert result["sharpe_ratio"] > 0

    def test_insufficient_data(self):
        """데이터 부족 → error"""
        result = QuantAnalyzer.calculate_sharpe_ratio(
            [(date(2025, 1, 1), 1.0)]
        )
        assert "error" in result


# ============================================================================
# calculate_alpha (1개)
# ============================================================================

@pytest.mark.unit
class TestAlpha:
    """알파 계산"""

    def test_basic_alpha(self):
        """종목이 시장 초과 → 양의 알파"""
        base = date(2025, 1, 1)
        stock = [(base + timedelta(days=i), 0.15) for i in range(100)]
        market = [(base + timedelta(days=i), 0.05) for i in range(100)]
        result = QuantAnalyzer.calculate_alpha(stock, market, risk_free_rate=3.0)
        assert result["alpha"] > 0


# ============================================================================
# calculate_tracking_error (1개)
# ============================================================================

@pytest.mark.unit
class TestTrackingError:
    """트래킹 에러"""

    def test_same_returns(self):
        """동일 수익률 → 트래킹 에러 ≈ 0"""
        base = date(2025, 1, 1)
        returns = [(base + timedelta(days=i), float(i % 3 - 1)) for i in range(100)]
        result = QuantAnalyzer.calculate_tracking_error(returns, returns)
        assert abs(result["tracking_error"]) < 0.01
