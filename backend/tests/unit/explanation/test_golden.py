"""
Phase A Golden Test

B-3에서 완성한 샘플 리포트를 기준으로 자동 생성 결과가 동일해야 한다.

테스트 기준:
- template_id 동일
- 문장 유사도 허용 (소수점 자리 차이 등)

버전: v1
생성일: 2026-01-17
"""

import json
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "app"))

from services.explanation import (
    classify_all,
    classify_comparison,
    TemplateResolver,
    RegulatoryGuard,
    CAGRState,
    VolatilityState,
    MDDState,
    SharpeState,
    SummaryBalanceState,
    ComparisonState,
)


# Golden 샘플 로드
GOLDEN_PATH = Path(__file__).parent.parent.parent.parent / "app" / "services" / "explanation" / "golden_report_sample.json"


@pytest.fixture
def golden_sample():
    """Golden 샘플 로드"""
    with open(GOLDEN_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


class TestClassifierGolden:
    """상태 분류 Golden Test"""

    def test_cagr_classification(self, golden_sample):
        """CAGR 상태 분류 검증"""
        metrics = golden_sample["input"]["metrics"]
        expected = golden_sample["state_classification"]["cagr_state"]

        result = classify_all(
            cagr=metrics["cagr"],
            volatility=metrics["volatility"],
            mdd=metrics["mdd"],
            sharpe=metrics["sharpe"]
        )

        assert result.cagr_state.value == expected

    def test_volatility_classification(self, golden_sample):
        """변동성 상태 분류 검증"""
        metrics = golden_sample["input"]["metrics"]
        expected = golden_sample["state_classification"]["volatility_state"]

        result = classify_all(
            cagr=metrics["cagr"],
            volatility=metrics["volatility"],
            mdd=metrics["mdd"],
            sharpe=metrics["sharpe"]
        )

        assert result.volatility_state.value == expected

    def test_mdd_classification(self, golden_sample):
        """MDD 상태 분류 검증"""
        metrics = golden_sample["input"]["metrics"]
        expected = golden_sample["state_classification"]["mdd_state"]

        result = classify_all(
            cagr=metrics["cagr"],
            volatility=metrics["volatility"],
            mdd=metrics["mdd"],
            sharpe=metrics["sharpe"]
        )

        assert result.mdd_state.value == expected

    def test_sharpe_classification(self, golden_sample):
        """샤프 비율 상태 분류 검증"""
        metrics = golden_sample["input"]["metrics"]
        expected = golden_sample["state_classification"]["sharpe_state"]

        result = classify_all(
            cagr=metrics["cagr"],
            volatility=metrics["volatility"],
            mdd=metrics["mdd"],
            sharpe=metrics["sharpe"]
        )

        assert result.sharpe_state.value == expected

    def test_summary_balance_classification(self, golden_sample):
        """종합 균형 상태 분류 검증"""
        metrics = golden_sample["input"]["metrics"]
        expected = golden_sample["state_classification"]["summary_balance"]

        result = classify_all(
            cagr=metrics["cagr"],
            volatility=metrics["volatility"],
            mdd=metrics["mdd"],
            sharpe=metrics["sharpe"]
        )

        assert result.summary_balance.value == expected

    def test_comparison_classification(self, golden_sample):
        """비교 상태 분류 검증"""
        metrics = golden_sample["input"]["metrics"]
        benchmark = golden_sample["input"]["benchmark"]
        expected_template = golden_sample["template_mapping"]["comparison"]

        result = classify_comparison(
            portfolio_cagr=metrics["cagr"],
            benchmark_return=benchmark["total_return"]
        )

        # compare_higher 템플릿인지 확인
        assert result == ComparisonState.HIGHER


class TestTemplateMappingGolden:
    """템플릿 매핑 Golden Test"""

    def test_cagr_template_id(self, golden_sample):
        """CAGR 템플릿 ID 검증"""
        metrics = golden_sample["input"]["metrics"]
        expected_template = golden_sample["template_mapping"]["cagr"]

        classification = classify_all(
            cagr=metrics["cagr"],
            volatility=metrics["volatility"],
            mdd=metrics["mdd"],
            sharpe=metrics["sharpe"]
        )

        resolver = TemplateResolver()
        result = resolver.resolve_cagr(
            state=classification.cagr_state,
            cagr=metrics["cagr"],
            period_years=metrics["period_days"] / 365
        )

        assert result.template_id == expected_template

    def test_volatility_template_id(self, golden_sample):
        """변동성 템플릿 ID 검증"""
        metrics = golden_sample["input"]["metrics"]
        expected_template = golden_sample["template_mapping"]["volatility"]

        classification = classify_all(
            cagr=metrics["cagr"],
            volatility=metrics["volatility"],
            mdd=metrics["mdd"],
            sharpe=metrics["sharpe"]
        )

        resolver = TemplateResolver()
        result = resolver.resolve_volatility(
            state=classification.volatility_state,
            volatility=metrics["volatility"]
        )

        assert result.template_id == expected_template

    def test_mdd_template_id(self, golden_sample):
        """MDD 템플릿 ID 검증"""
        metrics = golden_sample["input"]["metrics"]
        expected_template = golden_sample["template_mapping"]["mdd"]

        classification = classify_all(
            cagr=metrics["cagr"],
            volatility=metrics["volatility"],
            mdd=metrics["mdd"],
            sharpe=metrics["sharpe"]
        )

        resolver = TemplateResolver()
        result = resolver.resolve_mdd(
            state=classification.mdd_state,
            mdd=metrics["mdd"]
        )

        assert result.template_id == expected_template

    def test_sharpe_template_id(self, golden_sample):
        """샤프 템플릿 ID 검증"""
        metrics = golden_sample["input"]["metrics"]
        expected_template = golden_sample["template_mapping"]["sharpe"]

        classification = classify_all(
            cagr=metrics["cagr"],
            volatility=metrics["volatility"],
            mdd=metrics["mdd"],
            sharpe=metrics["sharpe"]
        )

        resolver = TemplateResolver()
        result = resolver.resolve_sharpe(
            state=classification.sharpe_state,
            sharpe=metrics["sharpe"]
        )

        assert result.template_id == expected_template


class TestOutputGolden:
    """출력 검증 Golden Test"""

    def test_summary_format(self, golden_sample):
        """요약 문장 형식 검증"""
        metrics = golden_sample["input"]["metrics"]
        expected_summary = golden_sample["expected_output"]["summary"]

        classification = classify_all(
            cagr=metrics["cagr"],
            volatility=metrics["volatility"],
            mdd=metrics["mdd"],
            sharpe=metrics["sharpe"]
        )

        resolver = TemplateResolver()
        summary = resolver.resolve_summary(
            classification=classification,
            cagr=metrics["cagr"],
            volatility=metrics["volatility"],
            mdd=metrics["mdd"],
            period_years=metrics["period_days"] / 365
        )

        # 주요 키워드 포함 검증
        assert "3.0년" in summary
        assert "8.2%" in summary
        assert "안정성과 변동성 사이의 균형" in summary

    def test_disclaimer_exists(self, golden_sample):
        """면책 조항 존재 검증"""
        expected_disclaimer = golden_sample["expected_output"]["disclaimer"]

        resolver = TemplateResolver()
        disclaimer = resolver.get_disclaimer()

        assert disclaimer == expected_disclaimer


class TestRegulatoryGuardGolden:
    """규제 가드 Golden Test"""

    def test_expected_output_no_violations(self, golden_sample):
        """예상 출력에 위반 없음 검증"""
        expected = golden_sample["expected_output"]
        guard = RegulatoryGuard()

        # Summary 검사
        result = guard.check_text(expected["summary"])
        assert not result.has_violation, f"Summary has violations: {result.violations}"

        # Disclaimer 검사
        result = guard.check_text(expected["disclaimer"])
        assert not result.has_violation, f"Disclaimer has violations: {result.violations}"

        # Risk explanation 검사
        result = guard.check_text(expected["risk_explanation"])
        assert not result.has_violation, f"Risk explanation has violations: {result.violations}"


class TestDeterminism:
    """결정론적 동작 검증"""

    def test_same_input_same_output(self, golden_sample):
        """동일 입력 → 동일 출력 검증 (100회 반복)"""
        metrics = golden_sample["input"]["metrics"]

        first_result = classify_all(
            cagr=metrics["cagr"],
            volatility=metrics["volatility"],
            mdd=metrics["mdd"],
            sharpe=metrics["sharpe"]
        )

        for _ in range(100):
            result = classify_all(
                cagr=metrics["cagr"],
                volatility=metrics["volatility"],
                mdd=metrics["mdd"],
                sharpe=metrics["sharpe"]
            )
            assert result.to_dict() == first_result.to_dict()


class TestEdgeCases:
    """경계값 테스트"""

    @pytest.mark.parametrize("cagr,expected", [
        (-0.10, CAGRState.NEGATIVE),
        (-0.1001, CAGRState.VERY_NEGATIVE),
        (0.0, CAGRState.LOW),
        (-0.0001, CAGRState.NEGATIVE),
        (0.03, CAGRState.MEDIUM),
        (0.0299, CAGRState.LOW),
        (0.07, CAGRState.HIGH),
        (0.0699, CAGRState.MEDIUM),
        (0.12, CAGRState.VERY_HIGH),
        (0.1199, CAGRState.HIGH),
    ])
    def test_cagr_boundary(self, cagr, expected):
        """CAGR 경계값 테스트"""
        result = classify_all(
            cagr=cagr,
            volatility=0.15,
            mdd=-0.15,
            sharpe=0.5
        )
        assert result.cagr_state == expected

    @pytest.mark.parametrize("volatility,expected", [
        (0.05, VolatilityState.LOW),
        (0.0499, VolatilityState.VERY_LOW),
        (0.12, VolatilityState.MEDIUM),
        (0.1199, VolatilityState.LOW),
        (0.20, VolatilityState.HIGH),
        (0.1999, VolatilityState.MEDIUM),
        (0.30, VolatilityState.VERY_HIGH),
        (0.2999, VolatilityState.HIGH),
    ])
    def test_volatility_boundary(self, volatility, expected):
        """변동성 경계값 테스트"""
        result = classify_all(
            cagr=0.08,
            volatility=volatility,
            mdd=-0.15,
            sharpe=0.5
        )
        assert result.volatility_state == expected

    @pytest.mark.parametrize("mdd,expected", [
        (-0.05, MDDState.CAUTION_LOW),
        (-0.0499, MDDState.STABLE),
        (-0.10, MDDState.CAUTION),
        (-0.0999, MDDState.CAUTION_LOW),
        (-0.20, MDDState.LARGE),
        (-0.1999, MDDState.CAUTION),
        (-0.35, MDDState.SEVERE),
        (-0.3499, MDDState.LARGE),
    ])
    def test_mdd_boundary(self, mdd, expected):
        """MDD 경계값 테스트"""
        result = classify_all(
            cagr=0.08,
            volatility=0.15,
            mdd=mdd,
            sharpe=0.5
        )
        assert result.mdd_state == expected
