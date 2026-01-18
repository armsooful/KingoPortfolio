"""
Phase A 입력 스키마 v1

지표 입력 스키마는 Phase 3-C가 어떤 소스를 쓰든 동일해야 한다.
이 스키마는 고정되며, 데이터 소스가 바뀌어도 변경하지 않는다.

버전: v1
생성일: 2026-01-17
"""

from dataclasses import dataclass
from typing import Optional
from datetime import date


@dataclass
class BenchmarkMetrics:
    """벤치마크 비교 결과 (선택)"""
    name: str  # 벤치마크 이름 (예: "KOSPI", "S&P 500")
    total_return: Optional[float] = None  # 벤치마크 누적 수익률
    cagr: Optional[float] = None  # 벤치마크 CAGR
    volatility: Optional[float] = None  # 벤치마크 변동성


@dataclass
class PerformanceMetrics:
    """
    성과 지표 입력 스키마

    단위 및 정밀도 규칙:
    - cagr: float, 소수점 (예: 0.082 = 8.2%)
    - volatility: float, 연율화 기준 (252 trading days), 소수점 (예: 0.145 = 14.5%)
    - mdd: float, 음수 (예: -0.123 = -12.3%)
    - sharpe: float, 소수점 2자리까지 표시 권장 (예: 0.56)
    - total_return: float, 누적 수익률 소수점 (예: 0.268 = 26.8%)
    - period_days: int, 분석 기간 일수
    """
    cagr: float  # 연복리수익률 (예: 0.082 = 8.2%)
    volatility: float  # 연율화 변동성 (252일 기준, 예: 0.145 = 14.5%)
    mdd: float  # 최대 낙폭 (음수, 예: -0.123 = -12.3%)
    total_return: float  # 누적 수익률 (예: 0.268 = 26.8%)
    period_days: int  # 분석 기간 일수

    sharpe: Optional[float] = None  # 샤프 비율 (변동성 0이면 None)
    rf_annual: float = 0.0  # 무위험 수익률 (기본값 0)

    # MDD 상세 정보 (선택)
    mdd_peak_date: Optional[date] = None  # MDD 고점 날짜
    mdd_trough_date: Optional[date] = None  # MDD 저점 날짜
    recovery_days: Optional[int] = None  # 회복까지 걸린 일수


@dataclass
class ExplanationInput:
    """
    Phase A 설명 생성 입력 스키마

    Phase 3-C가 어떤 데이터 소스를 사용하든 이 스키마를 따라야 한다.
    """
    portfolio_id: str  # 포트폴리오 ID
    start_date: date  # 분석 시작일 (YYYY-MM-DD)
    end_date: date  # 분석 종료일 (YYYY-MM-DD)
    metrics: PerformanceMetrics  # 성과 지표
    rebalance_enabled: bool = False  # 리밸런싱 여부
    benchmark: Optional[BenchmarkMetrics] = None  # 벤치마크 비교 (선택)

    def validate(self) -> list:
        """
        입력값 유효성 검사

        Returns:
            오류 메시지 목록 (빈 리스트면 유효)
        """
        errors = []

        # 날짜 검증
        if self.start_date >= self.end_date:
            errors.append("start_date must be before end_date")

        # 지표 검증
        if self.metrics.volatility < 0:
            errors.append("volatility must be non-negative")

        if self.metrics.mdd > 0:
            errors.append("mdd must be non-positive (0 or negative)")

        if self.metrics.period_days <= 0:
            errors.append("period_days must be positive")

        # period_days와 실제 기간 정합성 검사
        actual_days = (self.end_date - self.start_date).days
        if abs(actual_days - self.metrics.period_days) > 5:
            errors.append(f"period_days ({self.metrics.period_days}) does not match date range ({actual_days} days)")

        return errors

    @property
    def period_years(self) -> float:
        """분석 기간 (년)"""
        return self.metrics.period_days / 365.0


# =============================================================================
# 연율화 기준 상수
# =============================================================================

TRADING_DAYS_PER_YEAR = 252  # 연간 거래일 수 (변동성 연율화 기준)
CALENDAR_DAYS_PER_YEAR = 365  # 연간 일수 (CAGR 계산 기준)


# =============================================================================
# 헬퍼 함수
# =============================================================================

def create_explanation_input(
    portfolio_id: str,
    start_date: str,  # "YYYY-MM-DD"
    end_date: str,  # "YYYY-MM-DD"
    cagr: float,
    volatility: float,
    mdd: float,
    total_return: float,
    sharpe: Optional[float] = None,
    rf_annual: float = 0.0,
    rebalance_enabled: bool = False,
    benchmark_name: Optional[str] = None,
    benchmark_return: Optional[float] = None,
    mdd_peak_date: Optional[str] = None,
    mdd_trough_date: Optional[str] = None,
    recovery_days: Optional[int] = None
) -> ExplanationInput:
    """
    문자열 날짜를 받아 ExplanationInput 생성

    Args:
        portfolio_id: 포트폴리오 ID
        start_date: 시작일 "YYYY-MM-DD"
        end_date: 종료일 "YYYY-MM-DD"
        cagr: 연복리수익률 (소수점)
        volatility: 연율화 변동성 (소수점)
        mdd: 최대 낙폭 (음수, 소수점)
        total_return: 누적 수익률 (소수점)
        sharpe: 샤프 비율 (선택)
        rf_annual: 무위험 수익률 (기본 0)
        rebalance_enabled: 리밸런싱 여부
        benchmark_name: 벤치마크 이름 (선택)
        benchmark_return: 벤치마크 수익률 (선택)
        mdd_peak_date: MDD 고점 날짜 (선택)
        mdd_trough_date: MDD 저점 날짜 (선택)
        recovery_days: 회복 일수 (선택)

    Returns:
        ExplanationInput
    """
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    period_days = (end - start).days

    peak_date = date.fromisoformat(mdd_peak_date) if mdd_peak_date else None
    trough_date = date.fromisoformat(mdd_trough_date) if mdd_trough_date else None

    metrics = PerformanceMetrics(
        cagr=cagr,
        volatility=volatility,
        mdd=mdd,
        total_return=total_return,
        period_days=period_days,
        sharpe=sharpe,
        rf_annual=rf_annual,
        mdd_peak_date=peak_date,
        mdd_trough_date=trough_date,
        recovery_days=recovery_days
    )

    benchmark = None
    if benchmark_name:
        benchmark = BenchmarkMetrics(
            name=benchmark_name,
            total_return=benchmark_return
        )

    return ExplanationInput(
        portfolio_id=portfolio_id,
        start_date=start,
        end_date=end,
        metrics=metrics,
        rebalance_enabled=rebalance_enabled,
        benchmark=benchmark
    )
