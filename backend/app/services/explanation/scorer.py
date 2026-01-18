"""
Phase A 내부 스코어 계산 모듈 (Scorer)

주의사항:
- 스코어는 내부용이며 외부 응답/화면/리포트에 원값 노출 금지
- 스코어는 문구 선택의 "보정 값"으로만 사용
- API 응답에 score 필드가 포함되어서는 안 됨
- 로그에는 남기되 개인정보/민감정보 최소화

버전: v1
생성일: 2026-01-17
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class InternalScores:
    """
    내부 스코어 (외부 노출 금지)

    모든 스코어는 0~100 범위
    """
    stability_score: float  # 안정성 스코어 (0~100)
    growth_score: float  # 성장성 스코어 (0~100)

    def __post_init__(self):
        """범위 검증"""
        self.stability_score = max(0, min(100, self.stability_score))
        self.growth_score = max(0, min(100, self.growth_score))

    def to_log_dict(self) -> dict:
        """
        로그용 dict 변환

        민감정보 최소화: 소수점 없이 정수만 기록
        """
        return {
            "_internal_stability": int(self.stability_score),
            "_internal_growth": int(self.growth_score)
        }


def calculate_stability_score(
    volatility: float,
    mdd: float,
    sharpe: Optional[float]
) -> float:
    """
    안정성 스코어 계산 (0~100)

    높을수록 안정적
    - 변동성이 낮을수록 높음
    - MDD가 작을수록 높음
    - 샤프가 높을수록 높음 (위험 대비 수익 효율)

    Args:
        volatility: 연율화 변동성 (소수점)
        mdd: 최대 낙폭 (음수)
        sharpe: 샤프 비율

    Returns:
        안정성 스코어 (0~100)
    """
    # 변동성 스코어 (0~40점)
    # 5% 이하 = 40점, 30% 이상 = 0점
    vol_score = max(0, 40 - (volatility * 100 - 5) * (40 / 25))
    vol_score = max(0, min(40, vol_score))

    # MDD 스코어 (0~40점)
    # -5% 이상 = 40점, -35% 이하 = 0점
    mdd_pct = abs(mdd * 100)  # 양수로 변환
    mdd_score = max(0, 40 - (mdd_pct - 5) * (40 / 30))
    mdd_score = max(0, min(40, mdd_score))

    # 샤프 스코어 (0~20점)
    # 2.0 이상 = 20점, 0 이하 = 0점
    sharpe_score = 0
    if sharpe is not None and sharpe > 0:
        sharpe_score = min(20, sharpe * 10)

    return vol_score + mdd_score + sharpe_score


def calculate_growth_score(
    cagr: float,
    total_return: float,
    period_years: float
) -> float:
    """
    성장성 스코어 계산 (0~100)

    높을수록 성장성 높음
    - CAGR이 높을수록 높음
    - 누적 수익률이 높을수록 높음

    Args:
        cagr: 연복리수익률 (소수점)
        total_return: 누적 수익률 (소수점)
        period_years: 분석 기간 (년)

    Returns:
        성장성 스코어 (0~100)
    """
    # CAGR 스코어 (0~60점)
    # -10% 이하 = 0점, 15% 이상 = 60점
    cagr_pct = cagr * 100
    if cagr_pct < -10:
        cagr_score = 0
    elif cagr_pct > 15:
        cagr_score = 60
    else:
        # -10% ~ 15% 범위를 0~60으로 매핑
        cagr_score = (cagr_pct + 10) * (60 / 25)

    # 누적 수익률 스코어 (0~40점)
    # 기간에 따라 가중치 조정
    # 3년 기준 50% 누적 = 40점
    expected_return = 0.50  # 기준 누적 수익률
    if period_years > 0:
        # 기간별 정규화
        annualized_factor = min(period_years / 3, 2)  # 최대 2배
        adjusted_threshold = expected_return * annualized_factor
        return_ratio = total_return / adjusted_threshold if adjusted_threshold > 0 else 0
        return_score = min(40, return_ratio * 40)
    else:
        return_score = 0

    return max(0, min(100, cagr_score + return_score))


def calculate_internal_scores(
    cagr: float,
    volatility: float,
    mdd: float,
    total_return: float,
    period_years: float,
    sharpe: Optional[float] = None
) -> InternalScores:
    """
    내부 스코어 통합 계산

    Args:
        cagr: 연복리수익률
        volatility: 변동성
        mdd: 최대 낙폭
        total_return: 누적 수익률
        period_years: 분석 기간 (년)
        sharpe: 샤프 비율

    Returns:
        InternalScores
    """
    stability = calculate_stability_score(volatility, mdd, sharpe)
    growth = calculate_growth_score(cagr, total_return, period_years)

    return InternalScores(
        stability_score=stability,
        growth_score=growth
    )
