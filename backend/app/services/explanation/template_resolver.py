"""
Phase A 템플릿 리졸버 (Template Resolver)

상태 조합으로 템플릿을 선택한다.
랜덤 선택 금지 - 우선순위 기반(첫 번째) 선택

버전: v1
생성일: 2026-01-17
"""

from dataclasses import dataclass
from typing import Optional, Dict, List
from datetime import date

from .classifier import (
    CAGRState, VolatilityState, MDDState, SharpeState,
    SummaryBalanceState, ComparisonState, ClassificationResult
)


# =============================================================================
# 템플릿 ID 상수
# =============================================================================

# CAGR 템플릿 ID
CAGR_TEMPLATES = {
    CAGRState.VERY_NEGATIVE: "cagr_very_negative",
    CAGRState.NEGATIVE: "cagr_negative",
    CAGRState.LOW: "cagr_low",
    CAGRState.MEDIUM: "cagr_medium",
    CAGRState.HIGH: "cagr_high",
    CAGRState.VERY_HIGH: "cagr_very_high",
}

# Volatility 템플릿 ID
VOL_TEMPLATES = {
    VolatilityState.VERY_LOW: "vol_very_low",
    VolatilityState.LOW: "vol_low",
    VolatilityState.MEDIUM: "vol_medium",
    VolatilityState.HIGH: "vol_high",
    VolatilityState.VERY_HIGH: "vol_very_high",
}

# MDD 템플릿 ID
MDD_TEMPLATES = {
    MDDState.STABLE: "mdd_stable",
    MDDState.CAUTION_LOW: "mdd_caution_low",
    MDDState.CAUTION: "mdd_caution",
    MDDState.LARGE: "mdd_large",
    MDDState.SEVERE: "mdd_severe",
}

# Sharpe 템플릿 ID
SHARPE_TEMPLATES = {
    SharpeState.NA: "sharpe_na",
    SharpeState.NEGATIVE: "sharpe_negative",
    SharpeState.LOW: "sharpe_low",
    SharpeState.MEDIUM: "sharpe_medium",
    SharpeState.HIGH: "sharpe_high",
    SharpeState.VERY_HIGH: "sharpe_very_high",
}

# 비교 템플릿 ID
COMPARISON_TEMPLATES = {
    ComparisonState.NO_DATA: "compare_no_data",
    ComparisonState.HIGHER: "compare_higher",
    ComparisonState.SIMILAR: "compare_similar",
    ComparisonState.LOWER: "compare_lower",
}

# Summary 템플릿 ID
SUMMARY_BALANCE_TEMPLATES = {
    SummaryBalanceState.STABLE: "summary_balance_stable",
    SummaryBalanceState.BALANCED: "summary_balance_balanced",
    SummaryBalanceState.GROWTH: "summary_balance_growth",
}

# Fallback 템플릿 ID
FALLBACK_TEMPLATES = {
    "cagr": "fallback_cagr",
    "volatility": "fallback_vol",
    "mdd": "fallback_mdd",
    "sharpe": "fallback_sharpe",
    "summary": "fallback_summary",
    "neutral": "fallback_neutral",
}


# =============================================================================
# 템플릿 문구 정의
# =============================================================================

TEMPLATES: Dict[str, str] = {
    # CAGR
    "cagr_very_negative": "해당 기간 동안 연평균 {abs_cagr:.1f}%의 손실이 발생했습니다. 이는 초기 투자금 대비 상당한 가치 감소를 의미합니다.",
    "cagr_negative": "해당 기간 동안 연평균 {abs_cagr:.1f}%의 손실이 발생했습니다. 원금 대비 가치가 감소한 상태입니다.",
    "cagr_low": "연평균 {cagr:.1f}%의 수익률을 기록했습니다. 이는 일반적인 예금 금리 수준과 유사한 수익률입니다.",
    "cagr_medium": "연평균 {cagr:.1f}%의 수익률을 기록했습니다. 이는 과거 채권 수익률과 비슷한 수준입니다.",
    "cagr_high": "연평균 {cagr:.1f}%의 수익률을 기록했습니다. 이는 과거 주식시장 장기 평균 수익률과 유사한 수준입니다.",
    "cagr_very_high": "연평균 {cagr:.1f}%의 수익률을 기록했습니다. 이는 과거 시장 평균을 상회하는 수익률이나, 높은 수익률은 일반적으로 높은 위험을 동반합니다.",

    # Volatility
    "vol_very_low": "연간 변동성이 {vol:.1f}%로, 가격 변동 폭이 작은 편입니다. 이는 예금이나 단기 채권과 유사한 안정성을 보입니다.",
    "vol_low": "연간 변동성이 {vol:.1f}%로, 비교적 안정적인 가격 흐름을 보입니다. 채권형 자산과 유사한 변동성 수준입니다.",
    "vol_medium": "연간 변동성이 {vol:.1f}%로, 일반적인 주식시장과 유사한 수준입니다. 단기적으로 상당한 가격 변동이 있을 수 있습니다.",
    "vol_high": "연간 변동성이 {vol:.1f}%로, 상당히 높은 편입니다. 단기간에 큰 폭의 가격 변동을 경험할 수 있습니다.",
    "vol_very_high": "연간 변동성이 {vol:.1f}%로, 매우 높은 수준입니다. 극심한 가격 변동이 발생할 수 있습니다.",

    # MDD
    "mdd_stable": "최대 낙폭이 {abs_mdd:.1f}%로, 하락폭이 제한적이었습니다. 상대적으로 안정적인 가치 흐름을 보였습니다.",
    "mdd_caution_low": "최대 낙폭이 {abs_mdd:.1f}%였습니다. 일시적인 조정 국면을 경험했으나 비교적 제한된 손실이었습니다.",
    "mdd_caution": "최대 낙폭이 {abs_mdd:.1f}%로, 상당한 하락을 경험했습니다. 이 정도 하락은 주식시장에서 종종 발생하는 조정 수준입니다.",
    "mdd_large": "최대 낙폭이 {abs_mdd:.1f}%로, 큰 폭의 하락을 경험했습니다. 고점 대비 1/3 이상의 가치 감소가 있었던 기간이 있었습니다.",
    "mdd_severe": "최대 낙폭이 {abs_mdd:.1f}%로, 극심한 하락을 경험했습니다. 이는 금융위기 수준의 하락폭으로, 회복에 상당한 시간이 필요했을 수 있습니다.",

    # Sharpe
    "sharpe_na": "변동성이 0에 가까워 샤프 비율을 계산할 수 없습니다.",
    "sharpe_negative": "샤프 비율이 {sharpe:.2f}로, 위험 대비 수익이 부정적입니다. 무위험 수익률보다 낮은 수익을 기록했습니다.",
    "sharpe_low": "샤프 비율이 {sharpe:.2f}로, 위험 대비 수익이 낮은 편입니다. 감수한 위험에 비해 초과 수익이 제한적이었습니다.",
    "sharpe_medium": "샤프 비율이 {sharpe:.2f}로, 일반적인 수준입니다. 위험에 대한 적정 수준의 보상을 받았습니다.",
    "sharpe_high": "샤프 비율이 {sharpe:.2f}로, 위험 대비 수익이 양호합니다. 감수한 위험에 비해 좋은 초과 수익을 기록했습니다.",
    "sharpe_very_high": "샤프 비율이 {sharpe:.2f}로, 매우 높은 수준입니다. 그러나 이례적으로 높은 샤프 비율은 지속되기 어려울 수 있습니다.",

    # Comparison
    "compare_no_data": "비교 대상 데이터가 없습니다.",
    "compare_higher": "{benchmark_name} 대비 연평균 {diff_pct:.1f}%p 높은 수익률을 기록했습니다.",
    "compare_similar": "{benchmark_name}와 유사한 수익률을 기록했습니다.",
    "compare_lower": "{benchmark_name} 대비 연평균 {abs_diff_pct:.1f}%p 낮은 수익률을 기록했습니다.",

    # Summary Balance
    "summary_balance_stable": "안정성을 중시한 결과",
    "summary_balance_balanced": "안정성과 변동성 사이의 균형을 추구한 결과",
    "summary_balance_growth": "성장 가능성을 추구하되 변동성을 감수한 결과",

    # Summary Return
    "summary_return_loss": "연평균 {abs_cagr:.1f}%의 손실",
    "summary_return_gain": "연평균 {cagr:.1f}%의 수익",

    # Fallbacks
    "fallback_cagr": "해당 기간의 연평균 수익률을 나타냅니다.",
    "fallback_vol": "해당 기간의 연간 변동성을 나타냅니다.",
    "fallback_mdd": "해당 기간의 최대 낙폭을 나타냅니다.",
    "fallback_sharpe": "위험 대비 수익을 나타내는 지표입니다.",
    "fallback_summary": "해당 포트폴리오의 과거 성과 분석 결과입니다.",
    "fallback_neutral": "해당 지표에 대한 정보입니다.",
}

# 맥락 설명 템플릿
CONTEXT_TEMPLATES: Dict[str, str] = {
    "cagr": "장기적으로 자산이 어떤 속도로 변화했는지를 보여주는 지표입니다. 단기 변동을 평균화한 결과이므로, 중간 과정의 굴곡은 반영되지 않습니다. ({period_years:.1f}년 기준, 과거 성과이며 미래 수익을 보장하지 않습니다.)",
    "volatility": "가격이 오르내린 폭이 얼마나 컸는지를 나타냅니다. 변동성이 크다는 것은 수익 가능성과 함께 심리적 부담도 컸을 수 있음을 의미합니다.",
    "mdd": "과거 기간 중 가장 크게 하락했던 구간을 의미합니다. 이 구간은 많은 투자자들이 가장 불안함을 느끼는 시점입니다.",
    "sharpe": "샤프 비율은 (수익률 - 무위험수익률) / 변동성으로 계산됩니다. 무위험수익률 {rf_pct:.1f}%를 기준으로 계산되었습니다. 높을수록 위험 대비 효율적인 수익을 의미하지만, 과거 지표입니다.",
    "comparison": "비교 수치는 동일 기간 기준입니다. 과거 상대 성과가 미래에도 지속된다는 보장은 없습니다.",
}

# 면책 조항
DISCLAIMER = "본 분석은 과거 데이터에 기반한 정보 제공 목적으로만 작성되었습니다. 과거 성과는 미래 수익을 보장하지 않으며, 투자 권유나 추천이 아닙니다. 모든 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다. 본 서비스는 투자자문업에 해당하지 않습니다."


# =============================================================================
# 템플릿 리졸버 클래스
# =============================================================================

@dataclass
class ResolvedTemplate:
    """리졸브된 템플릿 결과"""
    template_id: str
    text: str
    context: Optional[str] = None


class TemplateResolver:
    """
    템플릿 리졸버

    상태 조합에 따라 템플릿을 선택하고 값을 채워 반환
    """

    def __init__(self, version: str = "v1"):
        self.version = version
        self.templates = TEMPLATES.copy()
        self.context_templates = CONTEXT_TEMPLATES.copy()

    def resolve_cagr(
        self,
        state: CAGRState,
        cagr: float,
        period_years: float
    ) -> ResolvedTemplate:
        """CAGR 템플릿 리졸브"""
        template_id = CAGR_TEMPLATES.get(state, FALLBACK_TEMPLATES["cagr"])
        template = self.templates.get(template_id, self.templates[FALLBACK_TEMPLATES["cagr"]])

        cagr_pct = cagr * 100
        abs_cagr = abs(cagr_pct)

        text = template.format(cagr=cagr_pct, abs_cagr=abs_cagr)
        context = self.context_templates["cagr"].format(period_years=period_years)

        return ResolvedTemplate(template_id=template_id, text=text, context=context)

    def resolve_volatility(
        self,
        state: VolatilityState,
        volatility: float
    ) -> ResolvedTemplate:
        """변동성 템플릿 리졸브"""
        template_id = VOL_TEMPLATES.get(state, FALLBACK_TEMPLATES["volatility"])
        template = self.templates.get(template_id, self.templates[FALLBACK_TEMPLATES["volatility"]])

        vol_pct = volatility * 100

        text = template.format(vol=vol_pct)
        context = self.context_templates["volatility"]

        return ResolvedTemplate(template_id=template_id, text=text, context=context)

    def resolve_mdd(
        self,
        state: MDDState,
        mdd: float,
        peak_date: Optional[date] = None,
        trough_date: Optional[date] = None,
        recovery_days: Optional[int] = None
    ) -> ResolvedTemplate:
        """MDD 템플릿 리졸브"""
        template_id = MDD_TEMPLATES.get(state, FALLBACK_TEMPLATES["mdd"])
        template = self.templates.get(template_id, self.templates[FALLBACK_TEMPLATES["mdd"]])

        abs_mdd = abs(mdd * 100)

        text = template.format(abs_mdd=abs_mdd)

        # 맥락 조합
        context_parts = [self.context_templates["mdd"]]
        if peak_date and trough_date:
            context_parts.append(
                f"해당 낙폭은 {peak_date.strftime('%Y년 %m월')}부터 "
                f"{trough_date.strftime('%Y년 %m월')} 사이에 발생했습니다."
            )
        if recovery_days is not None:
            if recovery_days > 0:
                recovery_months = recovery_days / 30
                context_parts.append(f"이후 약 {recovery_months:.0f}개월 만에 고점을 회복했습니다.")
            else:
                context_parts.append("분석 기간 내 고점을 회복하지 못했습니다.")

        context = " ".join(context_parts)

        return ResolvedTemplate(template_id=template_id, text=text, context=context)

    def resolve_sharpe(
        self,
        state: SharpeState,
        sharpe: Optional[float],
        rf_annual: float = 0.0
    ) -> ResolvedTemplate:
        """샤프 비율 템플릿 리졸브"""
        template_id = SHARPE_TEMPLATES.get(state, FALLBACK_TEMPLATES["sharpe"])
        template = self.templates.get(template_id, self.templates[FALLBACK_TEMPLATES["sharpe"]])

        if sharpe is None:
            sharpe = 0.0

        text = template.format(sharpe=sharpe)
        context = self.context_templates["sharpe"].format(rf_pct=rf_annual * 100)

        return ResolvedTemplate(template_id=template_id, text=text, context=context)

    def resolve_comparison(
        self,
        state: ComparisonState,
        benchmark_name: str,
        portfolio_cagr: float,
        benchmark_return: Optional[float]
    ) -> ResolvedTemplate:
        """비교 템플릿 리졸브"""
        template_id = COMPARISON_TEMPLATES.get(state, FALLBACK_TEMPLATES["neutral"])
        template = self.templates.get(template_id, self.templates[FALLBACK_TEMPLATES["neutral"]])

        diff = 0.0
        if benchmark_return is not None:
            diff = (portfolio_cagr - benchmark_return) * 100

        text = template.format(
            benchmark_name=benchmark_name,
            diff_pct=diff,
            abs_diff_pct=abs(diff)
        )
        context = self.context_templates["comparison"]

        return ResolvedTemplate(template_id=template_id, text=text, context=context)

    def resolve_summary(
        self,
        classification: ClassificationResult,
        cagr: float,
        volatility: float,
        mdd: float,
        period_years: float
    ) -> str:
        """종합 요약 생성"""
        cagr_pct = cagr * 100
        vol_pct = volatility * 100
        mdd_pct = abs(mdd * 100)

        # 수익률 설명
        if cagr < 0:
            return_desc = f"연평균 {abs(cagr_pct):.1f}%의 손실"
        else:
            return_desc = f"연평균 {cagr_pct:.1f}%의 수익"

        # 균형 설명
        balance_template_id = SUMMARY_BALANCE_TEMPLATES.get(
            classification.summary_balance,
            FALLBACK_TEMPLATES["summary"]
        )
        balance_desc = self.templates.get(balance_template_id, "")

        summary = (
            f"지난 {period_years:.1f}년간 이 포트폴리오는 {return_desc}을 기록했습니다. "
            f"이 포트폴리오는 {balance_desc}로 해석할 수 있습니다. "
            f"(변동성 {vol_pct:.1f}%, 최대 낙폭 {mdd_pct:.1f}%)"
        )

        return summary

    def get_disclaimer(self) -> str:
        """면책 조항 반환"""
        return DISCLAIMER

    def get_template_mapping(
        self,
        classification: ClassificationResult,
        comparison_state: Optional[ComparisonState] = None,
        cagr: float = 0.0
    ) -> Dict[str, str]:
        """템플릿 매핑 결과 반환"""
        mapping = {
            "cagr": CAGR_TEMPLATES.get(classification.cagr_state, FALLBACK_TEMPLATES["cagr"]),
            "volatility": VOL_TEMPLATES.get(classification.volatility_state, FALLBACK_TEMPLATES["volatility"]),
            "mdd": MDD_TEMPLATES.get(classification.mdd_state, FALLBACK_TEMPLATES["mdd"]),
            "sharpe": SHARPE_TEMPLATES.get(classification.sharpe_state, FALLBACK_TEMPLATES["sharpe"]),
            "summary_balance": SUMMARY_BALANCE_TEMPLATES.get(classification.summary_balance, FALLBACK_TEMPLATES["summary"]),
            "summary_return": "summary_return_loss" if cagr < 0 else "summary_return_gain",
        }

        if comparison_state:
            mapping["comparison"] = COMPARISON_TEMPLATES.get(comparison_state, FALLBACK_TEMPLATES["neutral"])

        return mapping
