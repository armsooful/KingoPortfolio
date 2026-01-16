"""
Phase 2 Epic D: 성과 분석 엔진 (Performance Analyzer)

시뮬레이션 결과(NAV 시계열)에 대한 정량적 성과 지표(KPI) 계산

**주요 KPI:**
- CAGR (Compound Annual Growth Rate): 연복리수익률
- Volatility: 연율화 변동성
- Sharpe Ratio: 위험 대비 수익 비율
- MDD (Maximum Drawdown): 최대 낙폭

⚠️ 주의사항:
- 이 모듈은 성과 해석/비교 계층으로, 투자 판단이나 추천을 수행하지 않습니다.
- 입력은 이미 확정된 시뮬레이션 결과이며, 결과는 설명 가능한 지표만 제공합니다.
- 과거 데이터 기반 분석이며, 미래 수익을 보장하지 않습니다.
"""

import math
from datetime import date
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


# ============================================================================
# 데이터 구조
# ============================================================================

@dataclass
class NAVPoint:
    """NAV 시계열 데이터 포인트"""
    nav_date: date
    nav: float


@dataclass
class DrawdownInfo:
    """Drawdown 정보"""
    mdd: float  # Maximum Drawdown (음수, 예: -0.15 = -15%)
    peak_date: Optional[date] = None
    trough_date: Optional[date] = None
    peak_nav: Optional[float] = None
    trough_nav: Optional[float] = None
    recovery_date: Optional[date] = None
    recovery_days: Optional[int] = None


@dataclass
class PerformanceMetrics:
    """성과 지표 데이터 클래스"""
    # 기본 정보
    period_start: date
    period_end: date
    trading_days: int

    # 수익률 지표
    total_return: float  # 총 수익률 (예: 0.15 = 15%)
    cagr: float  # 연복리수익률

    # 위험 지표
    volatility: float  # 연율화 변동성
    sharpe: Optional[float]  # Sharpe Ratio (변동성 0이면 None)

    # Drawdown 지표
    mdd: float  # Maximum Drawdown
    mdd_peak_date: Optional[date] = None
    mdd_trough_date: Optional[date] = None
    recovery_days: Optional[int] = None

    # 계산 파라미터
    rf_annual: float = 0.0
    annualization_factor: int = 252

    def to_dict(self) -> dict:
        """dict 변환 (JSON 직렬화용)"""
        return {
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "trading_days": self.trading_days,
            "total_return": round(self.total_return, 6) if self.total_return is not None else None,
            "cagr": round(self.cagr, 6) if self.cagr is not None else None,
            "volatility": round(self.volatility, 6) if self.volatility is not None else None,
            "sharpe": round(self.sharpe, 4) if self.sharpe is not None else None,
            "mdd": round(self.mdd, 6) if self.mdd is not None else None,
            "mdd_peak_date": self.mdd_peak_date.isoformat() if self.mdd_peak_date else None,
            "mdd_trough_date": self.mdd_trough_date.isoformat() if self.mdd_trough_date else None,
            "recovery_days": self.recovery_days,
            "rf_annual": self.rf_annual,
            "annualization_factor": self.annualization_factor,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PerformanceMetrics":
        """dict에서 생성"""
        return cls(
            period_start=date.fromisoformat(data["period_start"]) if data.get("period_start") else None,
            period_end=date.fromisoformat(data["period_end"]) if data.get("period_end") else None,
            trading_days=data.get("trading_days", 0),
            total_return=data.get("total_return", 0.0),
            cagr=data.get("cagr", 0.0),
            volatility=data.get("volatility", 0.0),
            sharpe=data.get("sharpe"),
            mdd=data.get("mdd", 0.0),
            mdd_peak_date=date.fromisoformat(data["mdd_peak_date"]) if data.get("mdd_peak_date") else None,
            mdd_trough_date=date.fromisoformat(data["mdd_trough_date"]) if data.get("mdd_trough_date") else None,
            recovery_days=data.get("recovery_days"),
            rf_annual=data.get("rf_annual", 0.0),
            annualization_factor=data.get("annualization_factor", 252),
        )


# ============================================================================
# KPI 계산 함수
# ============================================================================

def calculate_daily_returns(nav_series: List[NAVPoint]) -> List[float]:
    """
    NAV 시계열에서 일간 수익률 계산

    Args:
        nav_series: NAV 시계열 (날짜 오름차순 정렬)

    Returns:
        일간 수익률 리스트 (첫날 제외, n-1개)
    """
    if len(nav_series) < 2:
        return []

    daily_returns = []
    for i in range(1, len(nav_series)):
        prev_nav = nav_series[i - 1].nav
        curr_nav = nav_series[i].nav

        if prev_nav > 0:
            daily_return = (curr_nav - prev_nav) / prev_nav
            daily_returns.append(daily_return)

    return daily_returns


def calculate_total_return(nav_series: List[NAVPoint]) -> float:
    """
    총 수익률 계산

    Args:
        nav_series: NAV 시계열

    Returns:
        총 수익률 (예: 0.15 = 15%)
    """
    if len(nav_series) < 2:
        return 0.0

    initial_nav = nav_series[0].nav
    final_nav = nav_series[-1].nav

    if initial_nav <= 0:
        return 0.0

    return (final_nav - initial_nav) / initial_nav


def calculate_cagr(
    nav_series: List[NAVPoint],
    annualization_factor: int = 252
) -> float:
    """
    CAGR (Compound Annual Growth Rate) 계산

    CAGR = (final_nav / initial_nav)^(252 / trading_days) - 1

    Args:
        nav_series: NAV 시계열
        annualization_factor: 연율화 계수 (기본 252 거래일)

    Returns:
        CAGR (예: 0.08 = 8% 연율)
    """
    if len(nav_series) < 2:
        return 0.0

    initial_nav = nav_series[0].nav
    final_nav = nav_series[-1].nav
    trading_days = len(nav_series) - 1  # 수익률 개수 기준

    if initial_nav <= 0 or trading_days <= 0:
        return 0.0

    if final_nav <= 0:
        # 손실로 NAV가 0 이하가 된 경우 (극단적 케이스)
        return -1.0

    try:
        ratio = final_nav / initial_nav
        exponent = annualization_factor / trading_days
        cagr = math.pow(ratio, exponent) - 1
        return cagr
    except (ValueError, OverflowError):
        return 0.0


def calculate_volatility(
    daily_returns: List[float],
    annualization_factor: int = 252
) -> float:
    """
    연율화 변동성 계산

    Volatility = std(daily_returns) * sqrt(252)

    Args:
        daily_returns: 일간 수익률 리스트
        annualization_factor: 연율화 계수

    Returns:
        연율화 변동성 (예: 0.15 = 15%)
    """
    if len(daily_returns) < 2:
        return 0.0

    n = len(daily_returns)
    mean = sum(daily_returns) / n

    # 표본 분산 (n-1로 나눔)
    variance = sum((r - mean) ** 2 for r in daily_returns) / (n - 1)
    std_dev = math.sqrt(variance)

    # 연율화
    return std_dev * math.sqrt(annualization_factor)


def calculate_sharpe_ratio(
    cagr: float,
    volatility: float,
    rf_annual: float = 0.0
) -> Optional[float]:
    """
    Sharpe Ratio 계산

    Sharpe = (CAGR - Rf) / Volatility

    Args:
        cagr: 연복리수익률
        volatility: 연율화 변동성
        rf_annual: 무위험 수익률 (연율, 기본 0)

    Returns:
        Sharpe Ratio (변동성 0이면 None)
    """
    if volatility <= 0 or volatility < 1e-10:
        # 변동성이 0이면 Sharpe 정의 불가
        return None

    return (cagr - rf_annual) / volatility


def calculate_drawdown(nav_series: List[NAVPoint]) -> DrawdownInfo:
    """
    Maximum Drawdown (MDD) 계산

    MDD = min((NAV - Peak) / Peak)

    Args:
        nav_series: NAV 시계열

    Returns:
        DrawdownInfo (MDD, peak/trough 날짜, recovery 정보)
    """
    if len(nav_series) < 2:
        return DrawdownInfo(mdd=0.0)

    peak = nav_series[0].nav
    peak_date = nav_series[0].nav_date
    peak_nav = peak

    mdd = 0.0
    mdd_peak_date = None
    mdd_trough_date = None
    mdd_peak_nav = None
    mdd_trough_nav = None

    # 현재 최저점 추적 (recovery 계산용)
    current_trough_date = None
    current_trough_nav = None

    for point in nav_series:
        if point.nav > peak:
            # 새로운 고점 갱신
            peak = point.nav
            peak_date = point.nav_date
            peak_nav = peak
            current_trough_date = None
            current_trough_nav = None
        else:
            # Drawdown 계산
            if peak > 0:
                drawdown = (point.nav - peak) / peak  # 음수

                if drawdown < mdd:
                    mdd = drawdown
                    mdd_peak_date = peak_date
                    mdd_peak_nav = peak_nav
                    mdd_trough_date = point.nav_date
                    mdd_trough_nav = point.nav

    # Recovery 계산 (MDD 이후 고점 회복까지 일수)
    recovery_date = None
    recovery_days = None

    if mdd_trough_date and mdd_peak_nav:
        # MDD trough 이후 데이터에서 peak 회복 시점 찾기
        trough_idx = None
        for i, point in enumerate(nav_series):
            if point.nav_date == mdd_trough_date:
                trough_idx = i
                break

        if trough_idx is not None:
            for i in range(trough_idx + 1, len(nav_series)):
                if nav_series[i].nav >= mdd_peak_nav:
                    recovery_date = nav_series[i].nav_date
                    recovery_days = (recovery_date - mdd_trough_date).days
                    break

    return DrawdownInfo(
        mdd=mdd,
        peak_date=mdd_peak_date,
        trough_date=mdd_trough_date,
        peak_nav=mdd_peak_nav,
        trough_nav=mdd_trough_nav,
        recovery_date=recovery_date,
        recovery_days=recovery_days,
    )


# ============================================================================
# 통합 분석 함수
# ============================================================================

def analyze_performance(
    nav_series: List[NAVPoint],
    rf_annual: float = 0.0,
    annualization_factor: int = 252
) -> PerformanceMetrics:
    """
    NAV 시계열에 대한 종합 성과 분석

    Args:
        nav_series: NAV 시계열 (날짜 오름차순 정렬)
        rf_annual: 무위험 수익률 (연율, 기본 0)
        annualization_factor: 연율화 계수 (기본 252)

    Returns:
        PerformanceMetrics 객체
    """
    if len(nav_series) < 2:
        # 데이터 부족
        start_date = nav_series[0].nav_date if nav_series else None
        end_date = nav_series[0].nav_date if nav_series else None
        return PerformanceMetrics(
            period_start=start_date,
            period_end=end_date,
            trading_days=len(nav_series),
            total_return=0.0,
            cagr=0.0,
            volatility=0.0,
            sharpe=None,
            mdd=0.0,
            rf_annual=rf_annual,
            annualization_factor=annualization_factor,
        )

    # 기본 정보
    period_start = nav_series[0].nav_date
    period_end = nav_series[-1].nav_date
    trading_days = len(nav_series)

    # 일간 수익률 계산
    daily_returns = calculate_daily_returns(nav_series)

    # KPI 계산
    total_return = calculate_total_return(nav_series)
    cagr = calculate_cagr(nav_series, annualization_factor)
    volatility = calculate_volatility(daily_returns, annualization_factor)
    sharpe = calculate_sharpe_ratio(cagr, volatility, rf_annual)
    drawdown_info = calculate_drawdown(nav_series)

    return PerformanceMetrics(
        period_start=period_start,
        period_end=period_end,
        trading_days=trading_days,
        total_return=total_return,
        cagr=cagr,
        volatility=volatility,
        sharpe=sharpe,
        mdd=drawdown_info.mdd,
        mdd_peak_date=drawdown_info.peak_date,
        mdd_trough_date=drawdown_info.trough_date,
        recovery_days=drawdown_info.recovery_days,
        rf_annual=rf_annual,
        annualization_factor=annualization_factor,
    )


def analyze_from_nav_list(
    nav_data: List[Dict],
    rf_annual: float = 0.0,
    annualization_factor: int = 252
) -> PerformanceMetrics:
    """
    NAV dict 리스트에서 성과 분석

    Args:
        nav_data: [{"path_date": date, "nav": float}, ...] 형식
        rf_annual: 무위험 수익률
        annualization_factor: 연율화 계수

    Returns:
        PerformanceMetrics 객체
    """
    # NAVPoint 리스트로 변환
    nav_series = []
    for item in nav_data:
        nav_date = item.get("path_date") or item.get("nav_date") or item.get("date")
        nav_value = item.get("nav") or item.get("value") or item.get("nav_value")

        if nav_date and nav_value is not None:
            # date 타입 변환
            if isinstance(nav_date, str):
                nav_date = date.fromisoformat(nav_date)

            nav_series.append(NAVPoint(nav_date=nav_date, nav=float(nav_value)))

    # 날짜순 정렬
    nav_series.sort(key=lambda x: x.nav_date)

    return analyze_performance(nav_series, rf_annual, annualization_factor)


# ============================================================================
# 비교 분석 함수
# ============================================================================

def compare_metrics(
    metrics_a: PerformanceMetrics,
    metrics_b: PerformanceMetrics
) -> Dict:
    """
    두 성과 지표 비교

    ⚠️ 단순 수치 비교만 제공하며, 어느 쪽이 "더 좋다"는 판단을 하지 않습니다.

    Args:
        metrics_a: 첫 번째 성과 지표
        metrics_b: 두 번째 성과 지표

    Returns:
        비교 결과 dict (delta 값)
    """
    def safe_diff(a, b):
        if a is None or b is None:
            return None
        return a - b

    return {
        "period_a": {
            "start": metrics_a.period_start.isoformat() if metrics_a.period_start else None,
            "end": metrics_a.period_end.isoformat() if metrics_a.period_end else None,
            "trading_days": metrics_a.trading_days,
        },
        "period_b": {
            "start": metrics_b.period_start.isoformat() if metrics_b.period_start else None,
            "end": metrics_b.period_end.isoformat() if metrics_b.period_end else None,
            "trading_days": metrics_b.trading_days,
        },
        "delta": {
            "total_return": safe_diff(metrics_a.total_return, metrics_b.total_return),
            "cagr": safe_diff(metrics_a.cagr, metrics_b.cagr),
            "volatility": safe_diff(metrics_a.volatility, metrics_b.volatility),
            "sharpe": safe_diff(metrics_a.sharpe, metrics_b.sharpe),
            "mdd": safe_diff(metrics_a.mdd, metrics_b.mdd),  # 음수 -> 작을수록 손실 큼
        },
        "note": "단순 수치 차이를 제공합니다. 과거 성과가 미래 수익을 보장하지 않습니다.",
    }
