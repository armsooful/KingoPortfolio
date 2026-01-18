"""
Phase A 상태 분류 모듈 (Classifier)

Rule은 반드시 결정적(deterministic)이어야 하며, 랜덤/LLM 의존을 금지한다.
동일 입력 → 동일 상태 (항상)

버전: v1
생성일: 2026-01-17
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


# =============================================================================
# 상태 열거형 정의
# =============================================================================

class CAGRState(Enum):
    """CAGR 상태 분류"""
    VERY_NEGATIVE = "very_negative"  # cagr < -10%
    NEGATIVE = "negative"  # -10% <= cagr < 0%
    LOW = "low"  # 0% <= cagr < 3%
    MEDIUM = "medium"  # 3% <= cagr < 7%
    HIGH = "high"  # 7% <= cagr < 12%
    VERY_HIGH = "very_high"  # cagr >= 12%


class VolatilityState(Enum):
    """변동성 상태 분류"""
    VERY_LOW = "very_low"  # vol < 5%
    LOW = "low"  # 5% <= vol < 12%
    MEDIUM = "medium"  # 12% <= vol < 20%
    HIGH = "high"  # 20% <= vol < 30%
    VERY_HIGH = "very_high"  # vol >= 30%


class MDDState(Enum):
    """MDD 상태 분류"""
    STABLE = "stable"  # mdd > -5%
    CAUTION_LOW = "caution_low"  # -10% < mdd <= -5%
    CAUTION = "caution"  # -20% < mdd <= -10%
    LARGE = "large"  # -35% < mdd <= -20%
    SEVERE = "severe"  # mdd <= -35%


class SharpeState(Enum):
    """샤프 비율 상태 분류"""
    NA = "na"  # None
    NEGATIVE = "negative"  # sharpe < 0
    LOW = "low"  # 0 <= sharpe < 0.5
    MEDIUM = "medium"  # 0.5 <= sharpe < 1.0
    HIGH = "high"  # 1.0 <= sharpe < 2.0
    VERY_HIGH = "very_high"  # sharpe >= 2.0


class SummaryBalanceState(Enum):
    """종합 균형 상태 분류"""
    STABLE = "stable"  # 안정성 중시
    BALANCED = "balanced"  # 균형 추구
    GROWTH = "growth"  # 성장 추구


# =============================================================================
# Threshold 상수 테이블
# 운영 변경은 버전 관리를 통해서만 반영
# =============================================================================

@dataclass(frozen=True)
class ThresholdConfig:
    """
    임계값 설정 (불변)

    모든 수치는 소수점 형태 (예: 0.07 = 7%)
    """
    # CAGR 임계값
    CAGR_VERY_NEGATIVE: float = -0.10
    CAGR_NEGATIVE: float = 0.0
    CAGR_LOW: float = 0.03
    CAGR_MEDIUM: float = 0.07
    CAGR_HIGH: float = 0.12

    # Volatility 임계값
    VOL_VERY_LOW: float = 0.05
    VOL_LOW: float = 0.12
    VOL_MEDIUM: float = 0.20
    VOL_HIGH: float = 0.30

    # MDD 임계값 (음수)
    MDD_STABLE: float = -0.05
    MDD_CAUTION_LOW: float = -0.10
    MDD_CAUTION: float = -0.20
    MDD_LARGE: float = -0.35

    # Sharpe 임계값
    SHARPE_NEGATIVE: float = 0.0
    SHARPE_LOW: float = 0.5
    SHARPE_MEDIUM: float = 1.0
    SHARPE_HIGH: float = 2.0

    # Summary 임계값
    SUMMARY_STABLE_VOL: float = 0.10
    SUMMARY_STABLE_MDD: float = -0.10
    SUMMARY_BALANCED_VOL: float = 0.20
    SUMMARY_BALANCED_MDD: float = -0.20


# 기본 임계값 인스턴스 (v1)
THRESHOLDS_V1 = ThresholdConfig()


# =============================================================================
# 분류 함수 (Pure Functions)
# =============================================================================

def classify_cagr(cagr: float, config: ThresholdConfig = THRESHOLDS_V1) -> CAGRState:
    """
    CAGR 상태 분류

    Args:
        cagr: 연복리수익률 (소수점, 예: 0.082 = 8.2%)
        config: 임계값 설정

    Returns:
        CAGRState
    """
    if cagr < config.CAGR_VERY_NEGATIVE:
        return CAGRState.VERY_NEGATIVE
    elif cagr < config.CAGR_NEGATIVE:
        return CAGRState.NEGATIVE
    elif cagr < config.CAGR_LOW:
        return CAGRState.LOW
    elif cagr < config.CAGR_MEDIUM:
        return CAGRState.MEDIUM
    elif cagr < config.CAGR_HIGH:
        return CAGRState.HIGH
    else:
        return CAGRState.VERY_HIGH


def classify_volatility(volatility: float, config: ThresholdConfig = THRESHOLDS_V1) -> VolatilityState:
    """
    변동성 상태 분류

    Args:
        volatility: 연율화 변동성 (소수점, 예: 0.145 = 14.5%)
        config: 임계값 설정

    Returns:
        VolatilityState
    """
    if volatility < config.VOL_VERY_LOW:
        return VolatilityState.VERY_LOW
    elif volatility < config.VOL_LOW:
        return VolatilityState.LOW
    elif volatility < config.VOL_MEDIUM:
        return VolatilityState.MEDIUM
    elif volatility < config.VOL_HIGH:
        return VolatilityState.HIGH
    else:
        return VolatilityState.VERY_HIGH


def classify_mdd(mdd: float, config: ThresholdConfig = THRESHOLDS_V1) -> MDDState:
    """
    MDD 상태 분류

    Args:
        mdd: 최대 낙폭 (음수, 예: -0.123 = -12.3%)
        config: 임계값 설정

    Returns:
        MDDState
    """
    if mdd > config.MDD_STABLE:
        return MDDState.STABLE
    elif mdd > config.MDD_CAUTION_LOW:
        return MDDState.CAUTION_LOW
    elif mdd > config.MDD_CAUTION:
        return MDDState.CAUTION
    elif mdd > config.MDD_LARGE:
        return MDDState.LARGE
    else:
        return MDDState.SEVERE


def classify_sharpe(sharpe: Optional[float], config: ThresholdConfig = THRESHOLDS_V1) -> SharpeState:
    """
    샤프 비율 상태 분류

    Args:
        sharpe: 샤프 비율 (None일 수 있음)
        config: 임계값 설정

    Returns:
        SharpeState
    """
    if sharpe is None:
        return SharpeState.NA
    elif sharpe < config.SHARPE_NEGATIVE:
        return SharpeState.NEGATIVE
    elif sharpe < config.SHARPE_LOW:
        return SharpeState.LOW
    elif sharpe < config.SHARPE_MEDIUM:
        return SharpeState.MEDIUM
    elif sharpe < config.SHARPE_HIGH:
        return SharpeState.HIGH
    else:
        return SharpeState.VERY_HIGH


def classify_summary_balance(
    volatility: float,
    mdd: float,
    config: ThresholdConfig = THRESHOLDS_V1
) -> SummaryBalanceState:
    """
    종합 균형 상태 분류

    Args:
        volatility: 연율화 변동성
        mdd: 최대 낙폭
        config: 임계값 설정

    Returns:
        SummaryBalanceState
    """
    if volatility < config.SUMMARY_STABLE_VOL and mdd > config.SUMMARY_STABLE_MDD:
        return SummaryBalanceState.STABLE
    elif volatility < config.SUMMARY_BALANCED_VOL and mdd > config.SUMMARY_BALANCED_MDD:
        return SummaryBalanceState.BALANCED
    else:
        return SummaryBalanceState.GROWTH


# =============================================================================
# 통합 분류 결과
# =============================================================================

@dataclass
class ClassificationResult:
    """전체 상태 분류 결과"""
    cagr_state: CAGRState
    volatility_state: VolatilityState
    mdd_state: MDDState
    sharpe_state: SharpeState
    summary_balance: SummaryBalanceState

    def to_dict(self) -> dict:
        """dict 변환 (JSON 직렬화용)"""
        return {
            "cagr_state": self.cagr_state.value,
            "volatility_state": self.volatility_state.value,
            "mdd_state": self.mdd_state.value,
            "sharpe_state": self.sharpe_state.value,
            "summary_balance": self.summary_balance.value
        }


def classify_all(
    cagr: float,
    volatility: float,
    mdd: float,
    sharpe: Optional[float],
    config: ThresholdConfig = THRESHOLDS_V1
) -> ClassificationResult:
    """
    모든 지표를 한 번에 분류

    Args:
        cagr: 연복리수익률
        volatility: 변동성
        mdd: 최대 낙폭
        sharpe: 샤프 비율
        config: 임계값 설정

    Returns:
        ClassificationResult
    """
    return ClassificationResult(
        cagr_state=classify_cagr(cagr, config),
        volatility_state=classify_volatility(volatility, config),
        mdd_state=classify_mdd(mdd, config),
        sharpe_state=classify_sharpe(sharpe, config),
        summary_balance=classify_summary_balance(volatility, mdd, config)
    )


# =============================================================================
# 비교 상태 분류
# =============================================================================

class ComparisonState(Enum):
    """비교 상태 분류"""
    NO_DATA = "no_data"  # 벤치마크 데이터 없음
    HIGHER = "higher"  # 2%p 초과 상회
    SIMILAR = "similar"  # ±2%p 유사
    LOWER = "lower"  # 2%p 초과 하회


def classify_comparison(
    portfolio_cagr: float,
    benchmark_return: Optional[float],
    threshold: float = 0.02  # 2%p
) -> ComparisonState:
    """
    벤치마크 대비 상대 성과 분류

    Args:
        portfolio_cagr: 포트폴리오 CAGR
        benchmark_return: 벤치마크 수익률
        threshold: 유사 판단 임계값 (기본 2%p)

    Returns:
        ComparisonState
    """
    if benchmark_return is None:
        return ComparisonState.NO_DATA

    diff = portfolio_cagr - benchmark_return

    if diff > threshold:
        return ComparisonState.HIGHER
    elif diff < -threshold:
        return ComparisonState.LOWER
    else:
        return ComparisonState.SIMILAR
