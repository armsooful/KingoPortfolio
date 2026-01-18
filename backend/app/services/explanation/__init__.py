"""
Phase A 설명 자동 생성 모듈

버전: v1
생성일: 2026-01-17

모듈 구조:
- classifier.py: 상태 분류 (Deterministic Rules)
- template_resolver.py: 템플릿 매핑
- guard.py: 규제 가드
- scorer.py: 내부 스코어 (비노출)
- input_schema_v1.py: 입력 스키마

리소스:
- templates_v1.md: 템플릿 라이브러리
- banned_words_v1.txt: 금지어 목록
- golden_report_sample.json: Golden Test 기준
"""

from .classifier import (
    CAGRState,
    VolatilityState,
    MDDState,
    SharpeState,
    SummaryBalanceState,
    ComparisonState,
    ClassificationResult,
    ThresholdConfig,
    THRESHOLDS_V1,
    classify_cagr,
    classify_volatility,
    classify_mdd,
    classify_sharpe,
    classify_summary_balance,
    classify_comparison,
    classify_all,
)

from .template_resolver import (
    TemplateResolver,
    ResolvedTemplate,
    TEMPLATES,
    CONTEXT_TEMPLATES,
    DISCLAIMER,
)

from .guard import (
    RegulatoryGuard,
    ViolationResult,
    get_default_guard,
    check_text,
    sanitize,
)

from .scorer import (
    InternalScores,
    calculate_stability_score,
    calculate_growth_score,
    calculate_internal_scores,
)

from .input_schema_v1 import (
    ExplanationInput,
    PerformanceMetrics,
    BenchmarkMetrics,
    create_explanation_input,
    TRADING_DAYS_PER_YEAR,
    CALENDAR_DAYS_PER_YEAR,
)

__version__ = "v1"
__all__ = [
    # Classifier
    "CAGRState",
    "VolatilityState",
    "MDDState",
    "SharpeState",
    "SummaryBalanceState",
    "ComparisonState",
    "ClassificationResult",
    "ThresholdConfig",
    "THRESHOLDS_V1",
    "classify_cagr",
    "classify_volatility",
    "classify_mdd",
    "classify_sharpe",
    "classify_summary_balance",
    "classify_comparison",
    "classify_all",

    # Template Resolver
    "TemplateResolver",
    "ResolvedTemplate",
    "TEMPLATES",
    "CONTEXT_TEMPLATES",
    "DISCLAIMER",

    # Guard
    "RegulatoryGuard",
    "ViolationResult",
    "get_default_guard",
    "check_text",
    "sanitize",

    # Scorer
    "InternalScores",
    "calculate_stability_score",
    "calculate_growth_score",
    "calculate_internal_scores",

    # Input Schema
    "ExplanationInput",
    "PerformanceMetrics",
    "BenchmarkMetrics",
    "create_explanation_input",
    "TRADING_DAYS_PER_YEAR",
    "CALENDAR_DAYS_PER_YEAR",
]
