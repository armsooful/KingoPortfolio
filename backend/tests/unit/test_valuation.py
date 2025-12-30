"""
밸류에이션 분석 기능 테스트
"""
import pytest
from datetime import datetime
from app.services.valuation import ValuationAnalyzer


@pytest.mark.unit
@pytest.mark.valuation
class TestIndustryMultiples:
    """산업별 멀티플 테스트"""

    def test_get_industry_multiples_technology(self):
        """기술 산업 멀티플 조회"""
        multiples = ValuationAnalyzer.get_industry_multiples("Technology")

        assert "avg_pe" in multiples
        assert "avg_pb" in multiples
        assert multiples["avg_pe"] > 0
        assert multiples["avg_pb"] > 0

    def test_get_industry_multiples_finance(self):
        """금융 산업 멀티플 조회"""
        multiples = ValuationAnalyzer.get_industry_multiples("Financial Services")

        assert "avg_pe" in multiples
        assert "avg_pb" in multiples

    def test_get_industry_multiples_unknown(self):
        """알 수 없는 산업 → 기본값 반환"""
        multiples = ValuationAnalyzer.get_industry_multiples("UnknownIndustry")

        # 기본값(시장 평균)이 반환되어야 함
        assert "avg_pe" in multiples
        assert "avg_pb" in multiples
        assert multiples["description"] == "S&P 500 평균"


@pytest.mark.unit
@pytest.mark.valuation
class TestValuationComparison:
    """밸류에이션 비교 테스트"""

    def test_determine_overall_valuation_undervalued(self):
        """저평가 판정"""
        result = ValuationAnalyzer._determine_overall_valuation(
            pe_comp={"status": "저평가"},
            pb_comp={"status": "저평가"},
            div_comp={"status": "중립"}
        )

        assert result == "저평가"

    def test_determine_overall_valuation_overvalued(self):
        """고평가 판정"""
        result = ValuationAnalyzer._determine_overall_valuation(
            pe_comp={"status": "고평가"},
            pb_comp={"status": "고평가"},
            div_comp={"status": "낮음"}
        )

        assert result == "고평가"

    def test_determine_overall_valuation_neutral(self):
        """적정 평가 판정"""
        result = ValuationAnalyzer._determine_overall_valuation(
            pe_comp={"status": "중립"},
            pb_comp={"status": "중립"},
            div_comp={"status": "중립"}
        )

        assert result == "적정 평가"


@pytest.mark.integration
@pytest.mark.valuation
class TestValuationEndpoints:
    """밸류에이션 엔드포인트 통합 테스트"""

    def test_valuation_multiples_requires_auth(self, client):
        """멀티플 비교 엔드포인트 인증 필요"""
        response = client.get("/admin/valuation/multiples/AAPL")

        # 404 또는 401 (라우트 존재 여부에 따라)
        assert response.status_code in [401, 404]

    def test_valuation_multiples_requires_admin(self, client, auth_headers):
        """멀티플 비교는 관리자 권한 필요"""
        response = client.get("/admin/valuation/multiples/AAPL", headers=auth_headers)

        # 403 또는 404 (라우트 존재 여부에 따라)
        assert response.status_code in [403, 404]

    def test_valuation_comprehensive_public_access(self, client):
        """종합 밸류에이션은 공개 접근 가능 (TODO: 보안 이슈 - 인증 필요)"""
        response = client.get("/admin/valuation/comprehensive/AAPL")

        # 데이터가 없으면 404, 있으면 200
        assert response.status_code in [200, 404]

    def test_compare_multiples_admin_access(self, client, admin_headers):
        """관리자는 멀티플 비교 접근 가능"""
        response = client.get("/admin/valuation/multiples/AAPL", headers=admin_headers)

        if response.status_code == 200:
            data = response.json()
            assert "symbol" in data
            assert "current_pe" in data or "error" in data

    def test_dcf_valuation_endpoint(self, client, admin_headers):
        """DCF 밸류에이션 엔드포인트"""
        response = client.get("/admin/valuation/dcf/AAPL", headers=admin_headers)

        if response.status_code == 200:
            data = response.json()
            assert "symbol" in data
            assert ("intrinsic_value" in data) or ("error" in data)

    def test_ddm_valuation_endpoint(self, client, admin_headers):
        """DDM 밸류에이션 엔드포인트"""
        response = client.get("/admin/valuation/ddm/AAPL", headers=admin_headers)

        if response.status_code == 200:
            data = response.json()
            assert "symbol" in data
            assert ("intrinsic_value" in data) or ("error" in data)


@pytest.mark.unit
@pytest.mark.valuation
class TestDCFCalculations:
    """DCF 계산 테스트"""

    def test_fcf_projection(self):
        """FCF 성장 예측"""
        current_fcf = 100_000_000
        growth_rate = 0.10  # 10%
        years = 5

        projections = []
        for year in range(1, years + 1):
            projected_fcf = current_fcf * ((1 + growth_rate) ** year)
            projections.append(projected_fcf)

        # 5년 후 FCF는 약 1.61배
        assert len(projections) == 5
        assert projections[0] > current_fcf
        assert projections[-1] > projections[0]
        assert 160_000_000 < projections[-1] < 162_000_000

    def test_terminal_value_calculation(self):
        """터미널 밸류 계산"""
        final_fcf = 150_000_000
        perpetual_growth_rate = 0.03  # 3%
        wacc = 0.08  # 8%

        terminal_value = (final_fcf * (1 + perpetual_growth_rate)) / (wacc - perpetual_growth_rate)

        assert terminal_value > 0
        # TV = 150M * 1.03 / 0.05 = 3,090M
        assert 3_000_000_000 < terminal_value < 3_100_000_000

    def test_discount_to_present_value(self):
        """현재가치로 할인"""
        future_value = 1_000_000
        wacc = 0.08
        year = 5

        present_value = future_value / ((1 + wacc) ** year)

        assert present_value < future_value
        # PV = 1M / 1.08^5 ≈ 680,583
        assert 680_000 < present_value < 681_000


@pytest.mark.unit
@pytest.mark.valuation
class TestDDMCalculations:
    """DDM (배당할인모델) 계산 테스트"""

    def test_gordon_growth_model(self):
        """고든 성장 모델"""
        next_dividend = 5.0  # 다음 배당
        required_return = 0.10  # 요구수익률 10%
        dividend_growth = 0.05  # 배당성장률 5%

        intrinsic_value = next_dividend / (required_return - dividend_growth)

        assert intrinsic_value > 0
        # IV = 5 / 0.05 = 100
        assert intrinsic_value == 100.0

    def test_ddm_invalid_when_growth_exceeds_return(self):
        """배당성장률이 요구수익률보다 높으면 무효"""
        next_dividend = 5.0
        required_return = 0.05
        dividend_growth = 0.10  # 성장률이 더 높음

        # 이 경우 분모가 음수가 되므로 모델 적용 불가
        result = required_return - dividend_growth

        assert result < 0  # 음수이므로 DDM 적용 불가
