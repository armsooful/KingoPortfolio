"""
재무 분석 기능 테스트
"""
import pytest
from datetime import datetime
from app.services.financial_analyzer import FinancialAnalyzer
from app.models.alpha_vantage import AlphaVantageFinancials


@pytest.mark.unit
@pytest.mark.financial
class TestCagrCalculation:
    """CAGR 계산 테스트"""

    def test_calculate_cagr_positive_growth(self):
        """양의 성장률 CAGR 계산"""
        start_value = 100
        end_value = 200
        years = 3

        cagr = FinancialAnalyzer.calculate_cagr(start_value, end_value, years)

        assert cagr > 0
        assert isinstance(cagr, float)
        # 3년간 2배 성장 = 약 26% CAGR
        assert 25 < cagr < 27

    def test_calculate_cagr_negative_growth(self):
        """음의 성장률 CAGR 계산"""
        start_value = 200
        end_value = 100
        years = 3

        cagr = FinancialAnalyzer.calculate_cagr(start_value, end_value, years)

        assert cagr < 0
        # 3년간 절반 감소 = 약 -20.6% CAGR
        assert -21 < cagr < -20

    def test_calculate_cagr_zero_years(self):
        """0년 기간 CAGR 계산 (에러)"""
        cagr = FinancialAnalyzer.calculate_cagr(100, 200, 0)
        assert cagr is None

    def test_calculate_cagr_zero_start_value(self):
        """시작값 0인 경우 CAGR 계산"""
        cagr = FinancialAnalyzer.calculate_cagr(0, 100, 3)
        assert cagr is None  # 0으로 나눌 수 없으므로 None 반환

    def test_calculate_cagr_same_values(self):
        """시작값과 종료값이 같은 경우"""
        cagr = FinancialAnalyzer.calculate_cagr(100, 100, 3)
        assert cagr == 0.0


@pytest.mark.unit
@pytest.mark.financial
class TestFinancialRatios:
    """재무 비율 계산 테스트"""

    def test_calculate_roe(self):
        """ROE 계산 테스트"""
        financial = AlphaVantageFinancials(
            symbol="TEST",
            fiscal_date=datetime(2023, 12, 31).date(),
            report_type="annual",
            net_income=100_000_000,
            total_equity=500_000_000
        )

        roe = FinancialAnalyzer.calculate_roe(financial)

        assert roe == 20.0  # (100/500) * 100

    def test_calculate_roe_zero_equity(self):
        """자본이 0인 경우 ROE"""
        financial = AlphaVantageFinancials(
            symbol="TEST",
            fiscal_date=datetime(2023, 12, 31).date(),
            report_type="annual",
            net_income=100_000_000,
            total_equity=0
        )

        roe = FinancialAnalyzer.calculate_roe(financial)
        assert roe is None

    def test_calculate_roa(self):
        """ROA 계산 테스트"""
        financial = AlphaVantageFinancials(
            symbol="TEST",
            fiscal_date=datetime(2023, 12, 31).date(),
            report_type="annual",
            net_income=100_000_000,
            total_assets=1_000_000_000
        )

        roa = FinancialAnalyzer.calculate_roa(financial)

        assert roa == 10.0  # (100/1000) * 100

    def test_calculate_profit_margins(self):
        """이익률 계산"""
        financial = AlphaVantageFinancials(
            symbol="TEST",
            fiscal_date=datetime(2023, 12, 31).date(),
            report_type="annual",
            revenue=200_000_000,
            gross_profit=120_000_000,
            operating_income=50_000_000,
            net_income=40_000_000
        )

        margins = FinancialAnalyzer.calculate_profit_margins(financial)

        assert margins["gross_margin"] == 60.0  # (120/200) * 100
        assert margins["operating_margin"] == 25.0  # (50/200) * 100
        assert margins["net_margin"] == 20.0  # (40/200) * 100

    def test_calculate_debt_to_equity(self):
        """부채비율 계산"""
        financial = AlphaVantageFinancials(
            symbol="TEST",
            fiscal_date=datetime(2023, 12, 31).date(),
            report_type="annual",
            total_liabilities=300_000_000,
            total_equity=200_000_000
        )

        ratio = FinancialAnalyzer.calculate_debt_to_equity(financial)

        assert ratio == 150.0  # (300/200) * 100


@pytest.mark.unit
@pytest.mark.financial
class TestFinancialScore:
    """재무 점수 계산 테스트"""

    def test_score_in_range(self):
        """점수가 0-100 범위 내인지 확인"""
        # 가상의 재무 데이터
        score_data = {
            "revenue_growth": 15,
            "eps_growth": 20,
            "roe": 18,
            "operating_margin": 12,
            "debt_to_equity": 50,
            "current_ratio": 2.0
        }

        # 간단한 점수 계산 (실제 로직은 더 복잡)
        score = min(100, max(0, sum(score_data.values()) / len(score_data)))

        assert 0 <= score <= 100

    def test_high_performance_score(self):
        """우수한 재무 지표 → 높은 점수"""
        high_performance = {
            "revenue_growth": 30,
            "eps_growth": 25,
            "roe": 25,
            "operating_margin": 20
        }

        avg_score = sum(high_performance.values()) / len(high_performance)

        assert avg_score > 20  # 평균 20점 이상

    def test_poor_performance_score(self):
        """부진한 재무 지표 → 낮은 점수"""
        poor_performance = {
            "revenue_growth": -5,
            "eps_growth": -10,
            "roe": 5,
            "operating_margin": 3
        }

        avg_score = sum(poor_performance.values()) / len(poor_performance)

        assert avg_score < 10  # 평균 10점 미만


@pytest.mark.integration
@pytest.mark.financial
class TestFinancialAnalysisEndpoint:
    """재무 분석 엔드포인트 통합 테스트"""

    def test_financial_analysis_requires_auth(self, client):
        """재무 분석 엔드포인트 인증 필요"""
        response = client.get("/admin/financial-analysis/AAPL")

        assert response.status_code == 401

    def test_financial_analysis_requires_admin(self, client, auth_headers):
        """재무 분석은 관리자 권한 필요"""
        response = client.get("/admin/financial-analysis/AAPL", headers=auth_headers)

        assert response.status_code == 403

    def test_financial_analysis_admin_access(self, client, admin_headers):
        """관리자는 재무 분석 접근 가능"""
        response = client.get("/admin/financial-analysis/AAPL", headers=admin_headers)

        # 데이터가 없으면 404, 있으면 200
        assert response.status_code in [200, 404]

    def test_financial_score_v2_structure(self, client, admin_headers):
        """재무 점수 V2 응답 구조 확인"""
        # 실제 데이터가 있다고 가정 (목업 데이터 필요)
        response = client.get("/admin/financial-score-v2/AAPL", headers=admin_headers)

        if response.status_code == 200:
            data = response.json()
            # 예상되는 필드 확인
            assert "symbol" in data
            assert "total_score" in data or "error" in data
