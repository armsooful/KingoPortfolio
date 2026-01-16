"""
Phase 2 Epic D: 성과 분석 엔진 단위 테스트

performance_analyzer.py의 KPI 계산 로직 검증
"""

import pytest
import math
from datetime import date

from app.services.performance_analyzer import (
    NAVPoint,
    DrawdownInfo,
    PerformanceMetrics,
    calculate_daily_returns,
    calculate_total_return,
    calculate_cagr,
    calculate_volatility,
    calculate_sharpe_ratio,
    calculate_drawdown,
    analyze_performance,
    analyze_from_nav_list,
    compare_metrics,
)


# ============================================================================
# NAVPoint 테스트
# ============================================================================

class TestNAVPoint:
    """NAVPoint 데이터 클래스 테스트"""

    def test_create_nav_point(self):
        """NAVPoint 생성"""
        point = NAVPoint(nav_date=date(2024, 1, 1), nav=1000.0)
        assert point.nav_date == date(2024, 1, 1)
        assert point.nav == 1000.0


# ============================================================================
# 일간 수익률 계산 테스트
# ============================================================================

class TestDailyReturns:
    """일간 수익률 계산 테스트"""

    def test_simple_returns(self):
        """단순 일간 수익률"""
        nav_series = [
            NAVPoint(date(2024, 1, 1), 1000),
            NAVPoint(date(2024, 1, 2), 1010),  # +1%
            NAVPoint(date(2024, 1, 3), 1000),  # -0.99%
        ]
        returns = calculate_daily_returns(nav_series)

        assert len(returns) == 2
        assert abs(returns[0] - 0.01) < 0.0001
        assert abs(returns[1] - (-10 / 1010)) < 0.0001

    def test_empty_series(self):
        """빈 시계열"""
        returns = calculate_daily_returns([])
        assert returns == []

    def test_single_point(self):
        """단일 포인트"""
        nav_series = [NAVPoint(date(2024, 1, 1), 1000)]
        returns = calculate_daily_returns(nav_series)
        assert returns == []


# ============================================================================
# 총 수익률 테스트
# ============================================================================

class TestTotalReturn:
    """총 수익률 계산 테스트"""

    def test_positive_return(self):
        """양의 수익률"""
        nav_series = [
            NAVPoint(date(2024, 1, 1), 1000),
            NAVPoint(date(2024, 12, 31), 1150),
        ]
        total_return = calculate_total_return(nav_series)
        assert abs(total_return - 0.15) < 0.0001

    def test_negative_return(self):
        """음의 수익률"""
        nav_series = [
            NAVPoint(date(2024, 1, 1), 1000),
            NAVPoint(date(2024, 12, 31), 850),
        ]
        total_return = calculate_total_return(nav_series)
        assert abs(total_return - (-0.15)) < 0.0001

    def test_zero_return(self):
        """수익률 0"""
        nav_series = [
            NAVPoint(date(2024, 1, 1), 1000),
            NAVPoint(date(2024, 12, 31), 1000),
        ]
        total_return = calculate_total_return(nav_series)
        assert abs(total_return) < 0.0001


# ============================================================================
# CAGR 테스트
# ============================================================================

class TestCAGR:
    """CAGR 계산 테스트"""

    def test_one_year_cagr(self):
        """1년 CAGR (252 거래일)"""
        from datetime import timedelta
        # 1년간 10% 수익 → CAGR = 10%
        start = date(2024, 1, 1)
        nav_series = [NAVPoint(start, 1000)]
        for i in range(252):
            nav_date = start + timedelta(days=i + 1)
            nav_value = 1000 * (1.10 ** ((i + 1) / 252))
            nav_series.append(NAVPoint(nav_date, nav_value))

        cagr = calculate_cagr(nav_series, annualization_factor=252)
        # 마지막 NAV는 약 1100
        assert abs(cagr - 0.10) < 0.01  # 10% 근처

    def test_short_period_cagr(self):
        """짧은 기간 CAGR"""
        from datetime import timedelta
        # 126 거래일 (6개월)간 5% 수익 → 연율화 CAGR
        start = date(2024, 1, 1)
        nav_series = [NAVPoint(start, 1000)]
        for i in range(126):
            nav_date = start + timedelta(days=i + 1)
            nav_value = 1000 + i * (50 / 126)
            nav_series.append(NAVPoint(nav_date, nav_value))

        cagr = calculate_cagr(nav_series, annualization_factor=252)
        # 6개월 5% → 연율화하면 약 10.25%
        assert cagr > 0.09

    def test_empty_series(self):
        """빈 시계열"""
        cagr = calculate_cagr([], annualization_factor=252)
        assert cagr == 0.0


# ============================================================================
# 변동성 테스트
# ============================================================================

class TestVolatility:
    """변동성 계산 테스트"""

    def test_constant_returns(self):
        """일정한 수익률 → 변동성 0"""
        # 매일 0.1% 수익
        returns = [0.001] * 100
        vol = calculate_volatility(returns, annualization_factor=252)
        assert vol < 0.001  # 거의 0

    def test_varying_returns(self):
        """변동하는 수익률"""
        # ±1% 반복
        returns = [0.01, -0.01] * 50
        vol = calculate_volatility(returns, annualization_factor=252)
        assert vol > 0.1  # 유의미한 변동성

    def test_empty_returns(self):
        """빈 수익률"""
        vol = calculate_volatility([], annualization_factor=252)
        assert vol == 0.0


# ============================================================================
# Sharpe Ratio 테스트
# ============================================================================

class TestSharpeRatio:
    """Sharpe Ratio 계산 테스트"""

    def test_positive_sharpe(self):
        """양의 Sharpe"""
        # CAGR 10%, Vol 15%, Rf 2%
        sharpe = calculate_sharpe_ratio(cagr=0.10, volatility=0.15, rf_annual=0.02)
        expected = (0.10 - 0.02) / 0.15
        assert abs(sharpe - expected) < 0.0001

    def test_zero_volatility(self):
        """변동성 0 → Sharpe None"""
        sharpe = calculate_sharpe_ratio(cagr=0.10, volatility=0.0, rf_annual=0.02)
        assert sharpe is None

    def test_negative_sharpe(self):
        """음의 Sharpe"""
        # CAGR 1%, Rf 3%
        sharpe = calculate_sharpe_ratio(cagr=0.01, volatility=0.20, rf_annual=0.03)
        assert sharpe < 0


# ============================================================================
# MDD 테스트
# ============================================================================

class TestDrawdown:
    """MDD 계산 테스트"""

    def test_simple_drawdown(self):
        """단순 Drawdown"""
        nav_series = [
            NAVPoint(date(2024, 1, 1), 1000),
            NAVPoint(date(2024, 1, 2), 1100),  # 고점
            NAVPoint(date(2024, 1, 3), 990),   # 저점 (-10%)
            NAVPoint(date(2024, 1, 4), 1050),
        ]
        dd_info = calculate_drawdown(nav_series)

        # MDD = (990 - 1100) / 1100 = -0.10
        assert abs(dd_info.mdd - (-0.10)) < 0.001
        assert dd_info.peak_date == date(2024, 1, 2)
        assert dd_info.trough_date == date(2024, 1, 3)

    def test_no_drawdown(self):
        """Drawdown 없음 (계속 상승)"""
        nav_series = [
            NAVPoint(date(2024, 1, 1), 1000),
            NAVPoint(date(2024, 1, 2), 1100),
            NAVPoint(date(2024, 1, 3), 1200),
        ]
        dd_info = calculate_drawdown(nav_series)
        assert dd_info.mdd == 0.0

    def test_recovery(self):
        """Recovery 계산"""
        nav_series = [
            NAVPoint(date(2024, 1, 1), 1000),
            NAVPoint(date(2024, 1, 2), 1100),  # 고점
            NAVPoint(date(2024, 1, 3), 990),   # 저점
            NAVPoint(date(2024, 1, 4), 1050),
            NAVPoint(date(2024, 1, 5), 1100),  # 회복
        ]
        dd_info = calculate_drawdown(nav_series)
        assert dd_info.recovery_date == date(2024, 1, 5)
        assert dd_info.recovery_days == 2  # 1/3 → 1/5


# ============================================================================
# 통합 분석 테스트
# ============================================================================

class TestAnalyzePerformance:
    """통합 성과 분석 테스트"""

    def test_full_analysis(self):
        """전체 분석 흐름"""
        from datetime import timedelta
        # 252 거래일 시뮬레이션
        start = date(2024, 1, 1)
        nav_series = [NAVPoint(start, 1000000)]
        for i in range(251):
            # 약간의 변동과 함께 10% 수익
            daily_return = 0.10 / 252 + (0.001 if i % 2 == 0 else -0.001)
            new_nav = nav_series[-1].nav * (1 + daily_return)
            nav_date = start + timedelta(days=i + 1)
            nav_series.append(NAVPoint(nav_date, new_nav))

        metrics = analyze_performance(nav_series, rf_annual=0.02, annualization_factor=252)

        assert metrics.trading_days == 252
        assert metrics.period_start == date(2024, 1, 1)
        assert 0.05 < metrics.cagr < 0.15  # CAGR 범위 확인
        assert metrics.volatility > 0  # 변동성 있음
        assert metrics.sharpe is not None  # Sharpe 계산됨
        assert metrics.mdd <= 0  # MDD는 0 또는 음수

    def test_analyze_from_dict(self):
        """dict 리스트에서 분석"""
        nav_data = [
            {"path_date": date(2024, 1, 1), "nav": 1000000},
            {"path_date": date(2024, 6, 30), "nav": 1050000},
            {"path_date": date(2024, 12, 31), "nav": 1100000},
        ]
        metrics = analyze_from_nav_list(nav_data)

        assert metrics.total_return > 0
        assert metrics.trading_days == 3


# ============================================================================
# 비교 분석 테스트
# ============================================================================

class TestCompareMetrics:
    """비교 분석 테스트"""

    def test_compare_two_metrics(self):
        """두 지표 비교"""
        metrics_a = PerformanceMetrics(
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
            trading_days=252,
            total_return=0.15,
            cagr=0.15,
            volatility=0.12,
            sharpe=1.08,
            mdd=-0.08,
        )
        metrics_b = PerformanceMetrics(
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
            trading_days=252,
            total_return=0.10,
            cagr=0.10,
            volatility=0.15,
            sharpe=0.53,
            mdd=-0.12,
        )

        result = compare_metrics(metrics_a, metrics_b)

        assert result["delta"]["cagr"] == pytest.approx(0.05, abs=0.001)
        assert result["delta"]["mdd"] == pytest.approx(0.04, abs=0.001)  # -0.08 - (-0.12) = 0.04
        assert "note" in result


# ============================================================================
# PerformanceMetrics 직렬화 테스트
# ============================================================================

class TestMetricsSerialization:
    """지표 직렬화/역직렬화 테스트"""

    def test_to_dict(self):
        """dict 변환"""
        metrics = PerformanceMetrics(
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
            trading_days=252,
            total_return=0.15,
            cagr=0.15,
            volatility=0.12,
            sharpe=1.08,
            mdd=-0.08,
            mdd_peak_date=date(2024, 3, 15),
            mdd_trough_date=date(2024, 4, 10),
        )
        data = metrics.to_dict()

        assert data["period_start"] == "2024-01-01"
        assert data["cagr"] == 0.15
        assert data["sharpe"] == 1.08

    def test_from_dict(self):
        """dict에서 생성"""
        data = {
            "period_start": "2024-01-01",
            "period_end": "2024-12-31",
            "trading_days": 252,
            "total_return": 0.15,
            "cagr": 0.15,
            "volatility": 0.12,
            "sharpe": 1.08,
            "mdd": -0.08,
        }
        metrics = PerformanceMetrics.from_dict(data)

        assert metrics.period_start == date(2024, 1, 1)
        assert metrics.cagr == 0.15


# ============================================================================
# DoD 체크리스트 테스트
# ============================================================================

class TestDoDChecklist:
    """DoD (Definition of Done) 검증 테스트"""

    def test_no_recommendation_language(self):
        """추천/유리/최적 표현 없음 확인"""
        # compare_metrics의 note 확인
        metrics_a = PerformanceMetrics(
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
            trading_days=252,
            total_return=0.15,
            cagr=0.15,
            volatility=0.12,
            sharpe=1.08,
            mdd=-0.08,
        )
        metrics_b = PerformanceMetrics(
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
            trading_days=252,
            total_return=0.10,
            cagr=0.10,
            volatility=0.15,
            sharpe=0.53,
            mdd=-0.12,
        )

        result = compare_metrics(metrics_a, metrics_b)

        # 추천/유리/최적 표현이 없어야 함
        note = result.get("note", "")
        forbidden_words = ["추천", "유리", "최적", "recommend", "better", "optimal"]
        for word in forbidden_words:
            assert word.lower() not in note.lower()

    def test_deterministic_calculation(self):
        """동일 입력 → 동일 결과"""
        nav_series = [
            NAVPoint(date(2024, 1, 1), 1000000),
            NAVPoint(date(2024, 6, 30), 1050000),
            NAVPoint(date(2024, 12, 31), 1100000),
        ]

        metrics1 = analyze_performance(nav_series, rf_annual=0.02, annualization_factor=252)
        metrics2 = analyze_performance(nav_series, rf_annual=0.02, annualization_factor=252)

        assert metrics1.cagr == metrics2.cagr
        assert metrics1.volatility == metrics2.volatility
        assert metrics1.sharpe == metrics2.sharpe
        assert metrics1.mdd == metrics2.mdd

    def test_volatility_zero_sharpe_null(self):
        """변동성 0 → Sharpe NULL"""
        # 모든 NAV가 동일한 경우
        nav_series = [
            NAVPoint(date(2024, 1, 1), 1000000),
            NAVPoint(date(2024, 1, 2), 1000000),
            NAVPoint(date(2024, 1, 3), 1000000),
        ]
        metrics = analyze_performance(nav_series)

        # 변동성이 거의 0이면 Sharpe는 None
        if metrics.volatility < 1e-10:
            assert metrics.sharpe is None
