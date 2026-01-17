"""
Phase 3-A: 성과 해석 엔진 (Explanation Engine)

포트폴리오 성과 지표를 자연어 설명으로 변환하는 엔진

**핵심 컨셉**: 정답을 주지 않는다. 대신 이해를 준다.

**주요 기능:**
- 수익률(CAGR) 해석
- 변동성 해석
- MDD(최대 낙폭) 해석
- 샤프 비율 해석
- 맥락 비교 (시장 지수 대비)

**규제 준수:**
- 투자 권유 표현 금지
- 과거 데이터 기반 고지 필수
- 추천, 최적 표현 사용 금지
"""

from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import date
from enum import Enum


class PerformanceLevel(Enum):
    """성과 수준 분류 (비교 목적, 판단 아님)"""
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class RiskLevel(Enum):
    """위험 수준 분류 (정보 제공 목적)"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class MetricExplanation:
    """개별 지표 해석"""
    metric: str  # 지표명 (CAGR, Volatility, MDD, Sharpe)
    value: float  # 지표 값
    formatted_value: str  # 표시용 값 (예: "8.5%")
    description: str  # 자연어 설명
    context: Optional[str] = None  # 추가 맥락
    level: Optional[str] = None  # 수준 분류 (참고용)


@dataclass
class RiskPeriod:
    """위험 구간 정보"""
    period_type: str  # "mdd_period", "high_volatility_period"
    start_date: Optional[date]
    end_date: Optional[date]
    description: str
    severity: str  # "mild", "moderate", "severe"


@dataclass
class ComparisonContext:
    """비교 맥락"""
    benchmark_name: str  # 비교 대상 (예: "KOSPI 200", "S&P 500")
    benchmark_return: Optional[float]
    relative_performance: str  # 상대적 성과 설명
    note: str  # 주의사항


@dataclass
class ExplanationResult:
    """해석 결과 종합"""
    summary: str  # 전체 요약
    performance_explanations: List[MetricExplanation]  # 성과 지표 해석
    risk_explanation: str  # 위험 요약 설명
    risk_periods: List[RiskPeriod]  # 위험 구간 목록
    comparison: Optional[ComparisonContext]  # 비교 맥락 (선택)
    disclaimer: str  # 면책 조항


# ============================================================================
# CAGR (연복리수익률) 해석
# ============================================================================

def explain_cagr(cagr: float, period_years: float) -> MetricExplanation:
    """
    CAGR 지표를 자연어로 해석

    Args:
        cagr: 연복리수익률 (예: 0.08 = 8%)
        period_years: 분석 기간 (년)

    Returns:
        MetricExplanation
    """
    cagr_pct = cagr * 100
    formatted = f"{cagr_pct:+.2f}%"

    # 수준 분류 (참고용, 판단 아님)
    if cagr < -0.10:
        level = PerformanceLevel.VERY_LOW.value
        description = (
            f"해당 기간 동안 연평균 {abs(cagr_pct):.1f}%의 손실이 발생했습니다. "
            f"이는 초기 투자금 대비 상당한 가치 감소를 의미합니다."
        )
    elif cagr < 0:
        level = PerformanceLevel.LOW.value
        description = (
            f"해당 기간 동안 연평균 {abs(cagr_pct):.1f}%의 손실이 발생했습니다. "
            f"원금 대비 가치가 감소한 상태입니다."
        )
    elif cagr < 0.03:
        level = PerformanceLevel.LOW.value
        description = (
            f"연평균 {cagr_pct:.1f}%의 수익률을 기록했습니다. "
            f"이는 일반적인 예금 금리 수준과 유사한 수익률입니다."
        )
    elif cagr < 0.07:
        level = PerformanceLevel.MODERATE.value
        description = (
            f"연평균 {cagr_pct:.1f}%의 수익률을 기록했습니다. "
            f"이는 과거 채권 수익률과 비슷한 수준입니다."
        )
    elif cagr < 0.12:
        level = PerformanceLevel.HIGH.value
        description = (
            f"연평균 {cagr_pct:.1f}%의 수익률을 기록했습니다. "
            f"이는 과거 주식시장 장기 평균 수익률과 유사한 수준입니다."
        )
    else:
        level = PerformanceLevel.VERY_HIGH.value
        description = (
            f"연평균 {cagr_pct:.1f}%의 수익률을 기록했습니다. "
            f"이는 과거 시장 평균을 상회하는 수익률이나, "
            f"높은 수익률은 일반적으로 높은 위험을 동반합니다."
        )

    context = (
        f"CAGR(연복리수익률)은 {period_years:.1f}년 동안의 복리 기준 연평균 수익률입니다. "
        f"과거 성과이며, 미래 수익을 보장하지 않습니다."
    )

    return MetricExplanation(
        metric="CAGR",
        value=cagr,
        formatted_value=formatted,
        description=description,
        context=context,
        level=level
    )


# ============================================================================
# 변동성 해석
# ============================================================================

def explain_volatility(volatility: float) -> MetricExplanation:
    """
    연율화 변동성을 자연어로 해석

    Args:
        volatility: 연율화 변동성 (예: 0.15 = 15%)

    Returns:
        MetricExplanation
    """
    vol_pct = volatility * 100
    formatted = f"{vol_pct:.1f}%"

    if volatility < 0.05:
        level = RiskLevel.LOW.value
        description = (
            f"연간 변동성이 {vol_pct:.1f}%로, 가격 변동 폭이 작은 편입니다. "
            f"이는 예금이나 단기 채권과 유사한 안정성을 보입니다."
        )
    elif volatility < 0.12:
        level = RiskLevel.LOW.value
        description = (
            f"연간 변동성이 {vol_pct:.1f}%로, 비교적 안정적인 가격 흐름을 보입니다. "
            f"채권형 자산과 유사한 변동성 수준입니다."
        )
    elif volatility < 0.20:
        level = RiskLevel.MODERATE.value
        description = (
            f"연간 변동성이 {vol_pct:.1f}%로, 일반적인 주식시장과 유사한 수준입니다. "
            f"단기적으로 상당한 가격 변동이 있을 수 있습니다."
        )
    elif volatility < 0.30:
        level = RiskLevel.HIGH.value
        description = (
            f"연간 변동성이 {vol_pct:.1f}%로, 상당히 높은 편입니다. "
            f"단기간에 큰 폭의 가격 변동을 경험할 수 있습니다."
        )
    else:
        level = RiskLevel.VERY_HIGH.value
        description = (
            f"연간 변동성이 {vol_pct:.1f}%로, 매우 높은 수준입니다. "
            f"극심한 가격 변동이 발생할 수 있으며, 이는 개별 종목이나 "
            f"레버리지 상품에서 흔히 볼 수 있는 특성입니다."
        )

    context = (
        f"변동성은 가격이 평균에서 얼마나 벗어나는지를 나타냅니다. "
        f"높은 변동성은 큰 수익 가능성과 함께 큰 손실 가능성도 의미합니다."
    )

    return MetricExplanation(
        metric="Volatility",
        value=volatility,
        formatted_value=formatted,
        description=description,
        context=context,
        level=level
    )


# ============================================================================
# MDD (최대 낙폭) 해석
# ============================================================================

def explain_mdd(
    mdd: float,
    peak_date: Optional[date] = None,
    trough_date: Optional[date] = None,
    recovery_days: Optional[int] = None
) -> MetricExplanation:
    """
    MDD(최대 낙폭)를 자연어로 해석

    Args:
        mdd: 최대 낙폭 (음수, 예: -0.20 = -20%)
        peak_date: 고점 날짜
        trough_date: 저점 날짜
        recovery_days: 회복까지 걸린 일수

    Returns:
        MetricExplanation
    """
    mdd_pct = mdd * 100  # 이미 음수
    formatted = f"{mdd_pct:.1f}%"

    if mdd > -0.05:
        level = RiskLevel.LOW.value
        description = (
            f"최대 낙폭이 {abs(mdd_pct):.1f}%로, 하락폭이 제한적이었습니다. "
            f"상대적으로 안정적인 가치 흐름을 보였습니다."
        )
    elif mdd > -0.10:
        level = RiskLevel.LOW.value
        description = (
            f"최대 낙폭이 {abs(mdd_pct):.1f}%였습니다. "
            f"일시적인 조정 국면을 경험했으나 비교적 제한된 손실이었습니다."
        )
    elif mdd > -0.20:
        level = RiskLevel.MODERATE.value
        description = (
            f"최대 낙폭이 {abs(mdd_pct):.1f}%로, 상당한 하락을 경험했습니다. "
            f"이 정도 하락은 주식시장에서 종종 발생하는 조정 수준입니다."
        )
    elif mdd > -0.35:
        level = RiskLevel.HIGH.value
        description = (
            f"최대 낙폭이 {abs(mdd_pct):.1f}%로, 큰 폭의 하락을 경험했습니다. "
            f"고점 대비 1/3 이상의 가치 감소가 있었던 기간이 있었습니다."
        )
    else:
        level = RiskLevel.VERY_HIGH.value
        description = (
            f"최대 낙폭이 {abs(mdd_pct):.1f}%로, 극심한 하락을 경험했습니다. "
            f"이는 금융위기 수준의 하락폭으로, 회복에 상당한 시간이 필요했을 수 있습니다."
        )

    # 추가 맥락: 기간 및 회복 정보
    context_parts = [
        f"MDD(최대 낙폭)는 특정 기간 동안 고점에서 저점까지의 최대 하락률입니다."
    ]

    if peak_date and trough_date:
        context_parts.append(
            f"해당 낙폭은 {peak_date.strftime('%Y년 %m월')}부터 "
            f"{trough_date.strftime('%Y년 %m월')} 사이에 발생했습니다."
        )

    if recovery_days is not None:
        if recovery_days > 0:
            recovery_months = recovery_days / 30
            context_parts.append(
                f"이후 약 {recovery_months:.0f}개월 만에 고점을 회복했습니다."
            )
        else:
            context_parts.append(
                f"분석 기간 내 고점을 회복하지 못했습니다."
            )

    context = " ".join(context_parts)

    return MetricExplanation(
        metric="MDD",
        value=mdd,
        formatted_value=formatted,
        description=description,
        context=context,
        level=level
    )


# ============================================================================
# 샤프 비율 해석
# ============================================================================

def explain_sharpe(sharpe: Optional[float], rf_annual: float = 0.0) -> MetricExplanation:
    """
    샤프 비율을 자연어로 해석

    Args:
        sharpe: 샤프 비율 (None일 수 있음)
        rf_annual: 무위험 수익률

    Returns:
        MetricExplanation
    """
    if sharpe is None:
        return MetricExplanation(
            metric="Sharpe Ratio",
            value=0.0,
            formatted_value="N/A",
            description="변동성이 0에 가까워 샤프 비율을 계산할 수 없습니다.",
            context="샤프 비율은 위험 대비 초과 수익을 측정하는 지표입니다.",
            level=None
        )

    formatted = f"{sharpe:.2f}"

    if sharpe < 0:
        level = PerformanceLevel.VERY_LOW.value
        description = (
            f"샤프 비율이 {sharpe:.2f}로, 위험 대비 수익이 부정적입니다. "
            f"무위험 수익률보다 낮은 수익을 기록했으며 위험을 감수한 것에 대한 "
            f"보상이 없었음을 의미합니다."
        )
    elif sharpe < 0.5:
        level = PerformanceLevel.LOW.value
        description = (
            f"샤프 비율이 {sharpe:.2f}로, 위험 대비 수익이 낮은 편입니다. "
            f"감수한 위험에 비해 초과 수익이 제한적이었습니다."
        )
    elif sharpe < 1.0:
        level = PerformanceLevel.MODERATE.value
        description = (
            f"샤프 비율이 {sharpe:.2f}로, 일반적인 수준입니다. "
            f"위험에 대한 적정 수준의 보상을 받았습니다."
        )
    elif sharpe < 2.0:
        level = PerformanceLevel.HIGH.value
        description = (
            f"샤프 비율이 {sharpe:.2f}로, 위험 대비 수익이 양호합니다. "
            f"감수한 위험에 비해 좋은 초과 수익을 기록했습니다."
        )
    else:
        level = PerformanceLevel.VERY_HIGH.value
        description = (
            f"샤프 비율이 {sharpe:.2f}로, 매우 높은 수준입니다. "
            f"그러나 이례적으로 높은 샤프 비율은 지속되기 어려울 수 있습니다."
        )

    rf_pct = rf_annual * 100
    context = (
        f"샤프 비율은 (수익률 - 무위험수익률) / 변동성으로 계산됩니다. "
        f"무위험수익률 {rf_pct:.1f}%를 기준으로 계산되었습니다. "
        f"높을수록 위험 대비 효율적인 수익을 의미하지만, 과거 지표입니다."
    )

    return MetricExplanation(
        metric="Sharpe Ratio",
        value=sharpe,
        formatted_value=formatted,
        description=description,
        context=context,
        level=level
    )


# ============================================================================
# 위험 구간 분석
# ============================================================================

def analyze_risk_periods(
    mdd: float,
    peak_date: Optional[date] = None,
    trough_date: Optional[date] = None,
    recovery_days: Optional[int] = None
) -> List[RiskPeriod]:
    """
    위험 구간 분석

    Args:
        mdd: 최대 낙폭
        peak_date: MDD 고점 날짜
        trough_date: MDD 저점 날짜
        recovery_days: 회복 일수

    Returns:
        위험 구간 목록
    """
    risk_periods = []

    # MDD 구간 분석
    if peak_date and trough_date:
        if mdd > -0.10:
            severity = "mild"
            desc = f"{abs(mdd*100):.1f}%의 소폭 조정이 있었습니다."
        elif mdd > -0.20:
            severity = "moderate"
            desc = f"{abs(mdd*100):.1f}%의 조정 국면이 있었습니다."
        else:
            severity = "severe"
            desc = f"{abs(mdd*100):.1f}%의 큰 폭 하락이 있었습니다."

        risk_periods.append(RiskPeriod(
            period_type="mdd_period",
            start_date=peak_date,
            end_date=trough_date,
            description=desc,
            severity=severity
        ))

    return risk_periods


# ============================================================================
# 비교 맥락 생성
# ============================================================================

def create_comparison_context(
    portfolio_cagr: float,
    benchmark_name: str = "시장 지수",
    benchmark_return: Optional[float] = None
) -> ComparisonContext:
    """
    비교 맥락 생성

    Args:
        portfolio_cagr: 포트폴리오 CAGR
        benchmark_name: 비교 대상 이름
        benchmark_return: 비교 대상 수익률

    Returns:
        ComparisonContext
    """
    if benchmark_return is None:
        return ComparisonContext(
            benchmark_name=benchmark_name,
            benchmark_return=None,
            relative_performance="비교 대상 데이터가 없습니다.",
            note="비교를 위해서는 동일 기간의 벤치마크 데이터가 필요합니다."
        )

    diff = portfolio_cagr - benchmark_return
    diff_pct = diff * 100

    if diff > 0.02:
        relative = f"{benchmark_name} 대비 연평균 {diff_pct:.1f}%p 높은 수익률을 기록했습니다."
    elif diff < -0.02:
        relative = f"{benchmark_name} 대비 연평균 {abs(diff_pct):.1f}%p 낮은 수익률을 기록했습니다."
    else:
        relative = f"{benchmark_name}와 유사한 수익률을 기록했습니다."

    note = (
        f"비교 수치는 동일 기간 기준입니다. "
        f"과거 상대 성과가 미래에도 지속된다는 보장은 없습니다."
    )

    return ComparisonContext(
        benchmark_name=benchmark_name,
        benchmark_return=benchmark_return,
        relative_performance=relative,
        note=note
    )


# ============================================================================
# 요약 생성
# ============================================================================

def generate_summary(
    cagr: float,
    volatility: float,
    mdd: float,
    period_years: float
) -> str:
    """
    전체 성과 요약 생성

    Args:
        cagr: 연복리수익률
        volatility: 변동성
        mdd: 최대 낙폭
        period_years: 분석 기간 (년)

    Returns:
        요약 문자열
    """
    cagr_pct = cagr * 100
    vol_pct = volatility * 100
    mdd_pct = abs(mdd * 100)

    # 수익률 평가
    if cagr < 0:
        return_desc = f"연평균 {abs(cagr_pct):.1f}%의 손실"
    else:
        return_desc = f"연평균 {cagr_pct:.1f}%의 수익"

    # 위험 평가
    if volatility < 0.10 and mdd > -0.10:
        risk_desc = "낮은 변동성과 제한적인 낙폭"
    elif volatility < 0.20 and mdd > -0.20:
        risk_desc = "중간 수준의 위험"
    else:
        risk_desc = "높은 변동성 또는 큰 낙폭"

    summary = (
        f"지난 {period_years:.1f}년간 이 포트폴리오는 {return_desc}을 기록했으며, "
        f"{risk_desc}을 보였습니다. "
        f"변동성 {vol_pct:.1f}%, 최대 낙폭 {mdd_pct:.1f}%를 경험했습니다."
    )

    return summary


# ============================================================================
# 면책 조항
# ============================================================================

DISCLAIMER = (
    "본 분석은 과거 데이터에 기반한 정보 제공 목적으로만 작성되었습니다. "
    "과거 성과는 미래 수익을 보장하지 않으며, 투자 권유나 추천이 아닙니다. "
    "모든 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다. "
    "본 서비스는 투자자문업에 해당하지 않습니다."
)


# ============================================================================
# 통합 해석 함수
# ============================================================================

def explain_performance(
    cagr: float,
    volatility: float,
    mdd: float,
    sharpe: Optional[float],
    period_start: date,
    period_end: date,
    rf_annual: float = 0.0,
    benchmark_name: Optional[str] = None,
    benchmark_return: Optional[float] = None,
    mdd_peak_date: Optional[date] = None,
    mdd_trough_date: Optional[date] = None,
    recovery_days: Optional[int] = None
) -> ExplanationResult:
    """
    종합 성과 해석

    Args:
        cagr: 연복리수익률
        volatility: 연율화 변동성
        mdd: 최대 낙폭
        sharpe: 샤프 비율
        period_start: 분석 시작일
        period_end: 분석 종료일
        rf_annual: 무위험 수익률
        benchmark_name: 벤치마크 이름
        benchmark_return: 벤치마크 수익률
        mdd_peak_date: MDD 고점 날짜
        mdd_trough_date: MDD 저점 날짜
        recovery_days: 회복 일수

    Returns:
        ExplanationResult
    """
    # 기간 계산
    period_days = (period_end - period_start).days
    period_years = period_days / 365.0

    # 개별 지표 해석
    explanations = [
        explain_cagr(cagr, period_years),
        explain_volatility(volatility),
        explain_mdd(mdd, mdd_peak_date, mdd_trough_date, recovery_days),
        explain_sharpe(sharpe, rf_annual),
    ]

    # 위험 요약
    vol_pct = volatility * 100
    mdd_pct = abs(mdd * 100)
    risk_explanation = (
        f"이 포트폴리오는 연간 {vol_pct:.1f}%의 가격 변동성을 보였으며, "
        f"최대 {mdd_pct:.1f}%까지 가치가 하락한 적이 있습니다. "
        f"이러한 변동은 투자 과정에서 자연스럽게 발생할 수 있으나, "
        f"개인의 위험 감수 성향에 따라 체감되는 불안감은 다를 수 있습니다."
    )

    # 위험 구간
    risk_periods = analyze_risk_periods(mdd, mdd_peak_date, mdd_trough_date, recovery_days)

    # 비교 맥락
    comparison = None
    if benchmark_name:
        comparison = create_comparison_context(cagr, benchmark_name, benchmark_return)

    # 요약
    summary = generate_summary(cagr, volatility, mdd, period_years)

    return ExplanationResult(
        summary=summary,
        performance_explanations=explanations,
        risk_explanation=risk_explanation,
        risk_periods=risk_periods,
        comparison=comparison,
        disclaimer=DISCLAIMER
    )


def explanation_result_to_dict(result: ExplanationResult) -> dict:
    """ExplanationResult를 dict로 변환 (JSON 직렬화용)"""
    return {
        "summary": result.summary,
        "performance_explanation": [
            {
                "metric": exp.metric,
                "value": exp.value,
                "formatted_value": exp.formatted_value,
                "description": exp.description,
                "context": exp.context,
                "level": exp.level
            }
            for exp in result.performance_explanations
        ],
        "risk_explanation": result.risk_explanation,
        "risk_periods": [
            {
                "period_type": rp.period_type,
                "start_date": rp.start_date.isoformat() if rp.start_date else None,
                "end_date": rp.end_date.isoformat() if rp.end_date else None,
                "description": rp.description,
                "severity": rp.severity
            }
            for rp in result.risk_periods
        ],
        "comparison": {
            "benchmark_name": result.comparison.benchmark_name,
            "benchmark_return": result.comparison.benchmark_return,
            "relative_performance": result.comparison.relative_performance,
            "note": result.comparison.note
        } if result.comparison else None,
        "disclaimer": result.disclaimer
    }
