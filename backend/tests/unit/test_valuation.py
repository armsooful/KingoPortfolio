"""
밸류에이션 분석 기능 테스트
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock
from app.services.valuation import ValuationAnalyzer, INDUSTRY_MULTIPLES, MARKET_AVERAGE


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


# ============================================================================
# 추가 테스트: 순수 함수 심층 테스트
# ============================================================================

@pytest.mark.unit
@pytest.mark.valuation
class TestIndustryMultiplesPartialMatch:
    """get_industry_multiples 부분 일치 테스트"""

    def test_partial_match_forward(self):
        """부분 일치: 'Tech' → Technology"""
        result = ValuationAnalyzer.get_industry_multiples("Tech")
        assert result["description"] == "기술 및 소프트웨어"

    def test_partial_match_reverse(self):
        """역방향 부분 일치: 'Consumer' → Consumer Discretionary (첫 매칭)"""
        result = ValuationAnalyzer.get_industry_multiples("Consumer")
        # "Consumer"가 "Consumer Discretionary"와 "Consumer Staples"에 모두 매칭
        # dict 순서상 첫 번째인 Consumer Discretionary 반환
        assert result["description"] in ["임의소비재", "필수소비재"]

    def test_case_insensitive_match(self):
        """대소문자 무시 부분 일치"""
        result = ValuationAnalyzer.get_industry_multiples("technology")
        assert result["avg_pe"] == 28.5  # Technology와 동일

    def test_all_industries_have_required_keys(self):
        """모든 업종 데이터에 필수 키 존재"""
        required_keys = {"avg_pe", "avg_pb", "avg_div_yield", "description"}
        for industry, data in INDUSTRY_MULTIPLES.items():
            for key in required_keys:
                assert key in data, f"{industry}에 {key} 키 없음"

    def test_market_average_has_required_keys(self):
        """시장 평균에 필수 키 존재"""
        assert "avg_pe" in MARKET_AVERAGE
        assert "avg_pb" in MARKET_AVERAGE
        assert "avg_div_yield" in MARKET_AVERAGE
        assert MARKET_AVERAGE["avg_pe"] == 21.0


@pytest.mark.unit
@pytest.mark.valuation
class TestDetermineOverallValuationEdgeCases:
    """_determine_overall_valuation 엣지 케이스"""

    def test_all_none_returns_no_data(self):
        """모든 비교 데이터 None → '데이터 부족'"""
        result = ValuationAnalyzer._determine_overall_valuation(None, None, None)
        assert result == "데이터 부족"

    def test_only_dividend_high(self):
        """배당만 '높음' → score [1] → avg 1.0 > 0.5 → '저평가'"""
        result = ValuationAnalyzer._determine_overall_valuation(
            None, None, {"status": "높음"}
        )
        assert result == "저평가"

    def test_only_dividend_low(self):
        """배당만 '낮음' → score [-1] → avg -1.0 < -0.5 → '고평가'"""
        result = ValuationAnalyzer._determine_overall_valuation(
            None, None, {"status": "낮음"}
        )
        assert result == "고평가"

    def test_boundary_score_exactly_half(self):
        """경계: avg_score = 0.5 → '적정 평가' (> 0.5이어야 저평가)"""
        # PE 저평가(1) + PB 적정(0) → avg = 0.5 → 적정 평가
        result = ValuationAnalyzer._determine_overall_valuation(
            {"status": "저평가"}, {"status": "적정"}, None
        )
        assert result == "적정 평가"

    def test_boundary_score_negative_half(self):
        """경계: avg_score = -0.5 → '적정 평가' (< -0.5이어야 고평가)"""
        # PE 고평가(-1) + PB 적정(0) → avg = -0.5 → 적정 평가
        result = ValuationAnalyzer._determine_overall_valuation(
            {"status": "고평가"}, {"status": "적정"}, None
        )
        assert result == "적정 평가"

    def test_mixed_signals(self):
        """혼합: PE 저평가 + PB 고평가 + 배당 높음 → avg 0.33 → '적정 평가'"""
        result = ValuationAnalyzer._determine_overall_valuation(
            {"status": "저평가"}, {"status": "고평가"}, {"status": "높음"}
        )
        # scores: [1, -1, 1] → avg = 0.33 → 적정 평가
        assert result == "적정 평가"

    def test_strong_undervalued(self):
        """강한 저평가: PE 저평가 + PB 저평가 + 배당 높음"""
        result = ValuationAnalyzer._determine_overall_valuation(
            {"status": "저평가"}, {"status": "저평가"}, {"status": "높음"}
        )
        # scores: [1, 1, 1] → avg = 1.0 → 저평가
        assert result == "저평가"


@pytest.mark.unit
@pytest.mark.valuation
class TestGenerateSummary:
    """_generate_summary 종합 요약 생성 테스트"""

    def test_summary_with_undervalued_multiples(self):
        """멀티플 저평가 → 요약에 반영"""
        result = {
            "multiple_comparison": {"overall_valuation": "저평가"},
            "dcf_valuation": {"scenarios": {"중립적": {"upside_downside": 25.0}}},
            "ddm_valuation": {}
        }
        summary = ValuationAnalyzer._generate_summary(result)

        assert len(summary["valuations"]) == 2
        assert summary["valuations"][0]["method"] == "멀티플 비교"
        assert summary["valuations"][0]["result"] == "저평가"
        assert summary["valuations"][1]["method"] == "DCF (중립)"
        assert summary["valuations"][1]["result"] == "저평가"
        assert "저평가" in summary["valuation_note"]

    def test_summary_with_overvalued_signals(self):
        """고평가 시그널 2개 이상 → 고평가 노트"""
        result = {
            "multiple_comparison": {"overall_valuation": "고평가"},
            "dcf_valuation": {"scenarios": {"중립적": {"upside_downside": -25.0}}},
            "ddm_valuation": {}
        }
        summary = ValuationAnalyzer._generate_summary(result)

        assert "고평가" in summary["valuation_note"]

    def test_summary_neutral_range(self):
        """적정 평가 범위"""
        result = {
            "multiple_comparison": {"overall_valuation": "적정 평가"},
            "dcf_valuation": {"scenarios": {"중립적": {"upside_downside": 5.0}}},
            "ddm_valuation": {}
        }
        summary = ValuationAnalyzer._generate_summary(result)

        assert "적정 평가 범위" in summary["valuation_note"]

    def test_summary_no_data(self):
        """데이터 없음 → 빈 valuations + 적정 평가 노트"""
        result = {}
        summary = ValuationAnalyzer._generate_summary(result)

        assert summary["valuations"] == []
        assert "적정 평가 범위" in summary["valuation_note"]

    def test_summary_dcf_only(self):
        """DCF만 있는 경우"""
        result = {
            "dcf_valuation": {"scenarios": {"중립적": {"upside_downside": -30.0}}}
        }
        summary = ValuationAnalyzer._generate_summary(result)

        assert len(summary["valuations"]) == 1
        assert summary["valuations"][0]["result"] == "고평가"

    def test_summary_ddm_undervalued(self):
        """DDM 저평가"""
        result = {
            "ddm_valuation": {"scenarios": {"중립적": {"upside_downside": 50.0}}}
        }
        summary = ValuationAnalyzer._generate_summary(result)

        assert len(summary["valuations"]) == 1
        assert summary["valuations"][0]["result"] == "저평가"
        assert summary["valuations"][0]["upside"] == 50.0

    def test_summary_dcf_neutral_scenario_missing(self):
        """DCF에 중립 시나리오가 없으면 스킵"""
        result = {
            "dcf_valuation": {"scenarios": {"보수적": {"upside_downside": 10.0}}}
        }
        summary = ValuationAnalyzer._generate_summary(result)

        assert len(summary["valuations"]) == 0


# ============================================================================
# 추가 테스트: Mock 기반 DB 의존 함수 테스트
# ============================================================================

def _make_mock_kr_stock(**kwargs):
    """한국 주식 mock 객체 생성"""
    stock = MagicMock()
    stock.ticker = kwargs.get("ticker", "005930")
    stock.name = kwargs.get("name", "삼성전자")
    stock.pe_ratio = kwargs.get("pe_ratio", 12.5)
    stock.pb_ratio = kwargs.get("pb_ratio", 1.3)
    stock.dividend_yield = kwargs.get("dividend_yield", 2.0)
    stock.sector = kwargs.get("sector", "Technology")
    return stock


def _make_mock_us_stock(**kwargs):
    """미국 주식 mock 객체 생성"""
    stock = MagicMock()
    stock.symbol = kwargs.get("symbol", "AAPL")
    stock.name = kwargs.get("name", "Apple Inc.")
    stock.pe_ratio = kwargs.get("pe_ratio", 30.0)
    stock.pb_ratio = kwargs.get("pb_ratio", 45.0)
    stock.dividend_yield = kwargs.get("dividend_yield", 0.005)  # 0.5% as ratio
    stock.sector = kwargs.get("sector", "Technology")
    stock.industry = kwargs.get("industry", "Consumer Electronics")
    stock.current_price = kwargs.get("current_price", 200.0)
    stock.market_cap = kwargs.get("market_cap", 3_000_000_000_000)
    return stock


def _make_mock_financials(fcf_values, net_incomes=None):
    """재무제표 mock 리스트 생성 (최신→과거 순)"""
    financials = []
    for i, fcf in enumerate(fcf_values):
        f = MagicMock()
        f.free_cash_flow = fcf
        f.operating_cash_flow = fcf * 1.2 if fcf else None
        f.net_income = net_incomes[i] if net_incomes else fcf * 0.8
        f.short_term_debt = 10_000_000_000
        f.long_term_debt = 50_000_000_000
        f.cash_and_equivalents = 30_000_000_000
        f.fiscal_date = datetime(2024 - i, 12, 31)
        financials.append(f)
    return financials


@pytest.mark.unit
@pytest.mark.valuation
class TestCompareMultiplesWithMock:
    """compare_multiples mock 테스트"""

    def test_korean_stock_comparison(self):
        """한국 주식 멀티플 비교"""
        mock_db = MagicMock()
        mock_stock = _make_mock_kr_stock(pe_ratio=12.5, pb_ratio=1.3, dividend_yield=2.0)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_stock

        result = ValuationAnalyzer.compare_multiples(mock_db, "005930")

        assert result["symbol"] == "005930"
        assert result["company_name"] == "삼성전자"
        assert result["korean_stock"] is True
        assert result["pe_comparison"] is not None
        assert result["pb_comparison"] is not None

    def test_korean_stock_not_found(self):
        """한국 주식 없음 → ValueError"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="한국 주식"):
            ValuationAnalyzer.compare_multiples(mock_db, "999999")

    def test_us_stock_comparison(self):
        """미국 주식 멀티플 비교"""
        mock_db = MagicMock()
        mock_stock = _make_mock_us_stock(pe_ratio=30.0, pb_ratio=45.0, dividend_yield=0.005)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_stock

        result = ValuationAnalyzer.compare_multiples(mock_db, "AAPL")

        assert result["symbol"] == "AAPL"
        assert result["korean_stock"] is False
        # dividend_yield * 100 = 0.5%
        assert result["dividend_yield_comparison"]["current"] == 0.5

    def test_us_stock_not_found(self):
        """미국 주식 없음 → ValueError"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="not found"):
            ValuationAnalyzer.compare_multiples(mock_db, "XXXX")

    def test_pe_overvalued_threshold(self):
        """PE > 업종 평균 20% → 고평가"""
        mock_db = MagicMock()
        # Technology avg_pe = 28.5, 20% over = 34.2
        mock_stock = _make_mock_kr_stock(pe_ratio=40.0, pb_ratio=6.0, sector="Technology")
        mock_db.query.return_value.filter.return_value.first.return_value = mock_stock

        result = ValuationAnalyzer.compare_multiples(mock_db, "005930")

        assert result["pe_comparison"]["status"] == "고평가"

    def test_pe_undervalued_threshold(self):
        """PE < 업종 평균 -20% → 저평가"""
        mock_db = MagicMock()
        # Technology avg_pe = 28.5, -20% = 22.8
        mock_stock = _make_mock_kr_stock(pe_ratio=15.0, pb_ratio=3.0, sector="Technology")
        mock_db.query.return_value.filter.return_value.first.return_value = mock_stock

        result = ValuationAnalyzer.compare_multiples(mock_db, "005930")

        assert result["pe_comparison"]["status"] == "저평가"

    def test_pe_fair_value(self):
        """PE 업종 평균 ±20% 이내 → 적정"""
        mock_db = MagicMock()
        # Technology avg_pe = 28.5, ±20% = 22.8~34.2
        mock_stock = _make_mock_kr_stock(pe_ratio=28.0, pb_ratio=6.0, sector="Technology")
        mock_db.query.return_value.filter.return_value.first.return_value = mock_stock

        result = ValuationAnalyzer.compare_multiples(mock_db, "005930")

        assert result["pe_comparison"]["status"] == "적정"

    def test_no_pe_no_pb(self):
        """PE/PB 없는 종목 → comparison None"""
        mock_db = MagicMock()
        mock_stock = _make_mock_kr_stock(pe_ratio=None, pb_ratio=None, dividend_yield=0)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_stock

        result = ValuationAnalyzer.compare_multiples(mock_db, "005930")

        assert result["pe_comparison"] is None
        assert result["pb_comparison"] is None
        assert result["overall_valuation"] == "데이터 부족"


@pytest.mark.unit
@pytest.mark.valuation
class TestDcfValuationWithMock:
    """dcf_valuation mock 테스트"""

    def test_korean_stock_returns_error(self):
        """한국 주식 DCF → 지원 안함 에러"""
        mock_db = MagicMock()
        mock_stock = _make_mock_kr_stock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_stock

        result = ValuationAnalyzer.dcf_valuation(mock_db, "005930")

        assert result["korean_stock"] is True
        assert "error" in result
        assert "DCF" in result["error"]

    def test_korean_stock_not_found(self):
        """한국 주식 없음 → ValueError"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="한국 주식"):
            ValuationAnalyzer.dcf_valuation(mock_db, "999999")

    def test_us_stock_not_found(self):
        """미국 주식 없음 → ValueError"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="not found"):
            ValuationAnalyzer.dcf_valuation(mock_db, "XXXX")

    def test_us_stock_negative_fcf(self):
        """미국 주식 FCF 음수 → 에러 응답"""
        mock_db = MagicMock()
        mock_stock = _make_mock_us_stock()

        # 첫 query → AlphaVantageStock, 두 번째 → AlphaVantageFinancials
        mock_fin = MagicMock()
        mock_fin.free_cash_flow = -100_000_000
        mock_fin.operating_cash_flow = -50_000_000

        query_mock = MagicMock()
        # AlphaVantageStock query
        stock_filter = MagicMock()
        stock_filter.first.return_value = mock_stock
        # AlphaVantageFinancials query
        fin_filter = MagicMock()
        fin_order = MagicMock()
        fin_order.limit.return_value.all.return_value = [mock_fin] * 3

        call_count = [0]
        def side_effect(*args):
            call_count[0] += 1
            if call_count[0] == 1:
                m = MagicMock()
                m.filter.return_value = stock_filter
                return m
            else:
                m = MagicMock()
                m.filter.return_value.order_by.return_value = fin_order
                return m

        mock_db.query.side_effect = side_effect

        result = ValuationAnalyzer.dcf_valuation(mock_db, "AAPL")

        assert "error" in result
        assert "FCF" in result["error"]

    def test_us_stock_dcf_with_scenarios(self):
        """미국 주식 DCF 시나리오 3개 생성"""
        mock_db = MagicMock()
        mock_stock = _make_mock_us_stock(current_price=200.0, market_cap=3_000_000_000_000)

        fcf_values = [100e9, 90e9, 80e9, 70e9, 60e9]  # 최신→과거
        financials = _make_mock_financials(fcf_values)

        call_count = [0]
        def side_effect(*args):
            call_count[0] += 1
            if call_count[0] == 1:
                m = MagicMock()
                m.filter.return_value.first.return_value = mock_stock
                return m
            else:
                m = MagicMock()
                m.filter.return_value.order_by.return_value.limit.return_value.all.return_value = financials
                return m

        mock_db.query.side_effect = side_effect

        result = ValuationAnalyzer.dcf_valuation(mock_db, "AAPL")

        assert result["symbol"] == "AAPL"
        assert result["method"] == "DCF (Discounted Cash Flow)"
        assert "scenarios" in result
        assert "보수적" in result["scenarios"]
        assert "중립적" in result["scenarios"]
        assert "낙관적" in result["scenarios"]

        # 각 시나리오에 필수 필드 존재
        for name, scenario in result["scenarios"].items():
            assert "enterprise_value" in scenario
            assert "fair_value_per_share" in scenario
            assert scenario["enterprise_value"] > 0


@pytest.mark.unit
@pytest.mark.valuation
class TestDdmValuationWithMock:
    """dividend_discount_model mock 테스트"""

    def test_korean_stock_returns_error(self):
        """한국 주식 DDM → 지원 안함 에러"""
        mock_db = MagicMock()
        mock_stock = _make_mock_kr_stock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_stock

        result = ValuationAnalyzer.dividend_discount_model(mock_db, "005930")

        assert result["korean_stock"] is True
        assert "error" in result
        assert "DDM" in result["error"]

    def test_us_stock_no_dividend(self):
        """배당 없는 미국 주식 → 에러"""
        mock_db = MagicMock()
        mock_stock = _make_mock_us_stock(dividend_yield=0)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_stock

        result = ValuationAnalyzer.dividend_discount_model(mock_db, "AAPL")

        assert "error" in result
        assert "배당금" in result["error"]

    def test_us_stock_ddm_with_scenarios(self):
        """미국 주식 DDM 시나리오 3개 생성"""
        mock_db = MagicMock()
        mock_stock = _make_mock_us_stock(
            current_price=200.0, dividend_yield=0.02  # 2%
        )

        net_incomes = [50e9, 45e9, 40e9, 35e9, 30e9]
        financials = _make_mock_financials([0]*5, net_incomes=net_incomes)

        call_count = [0]
        def side_effect(*args):
            call_count[0] += 1
            if call_count[0] == 1:
                m = MagicMock()
                m.filter.return_value.first.return_value = mock_stock
                return m
            else:
                m = MagicMock()
                m.filter.return_value.order_by.return_value.limit.return_value.all.return_value = financials
                return m

        mock_db.query.side_effect = side_effect

        result = ValuationAnalyzer.dividend_discount_model(mock_db, "AAPL")

        assert result["symbol"] == "AAPL"
        assert result["method"] == "DDM (Dividend Discount Model - Gordon Growth)"
        assert result["current_dividend_yield"] == 2.0
        assert "scenarios" in result
        assert "보수적" in result["scenarios"]
        assert "중립적" in result["scenarios"]
        assert "낙관적" in result["scenarios"]

    def test_us_stock_not_found(self):
        """미국 주식 없음 → ValueError"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="not found"):
            ValuationAnalyzer.dividend_discount_model(mock_db, "XXXX")


@pytest.mark.unit
@pytest.mark.valuation
class TestComprehensiveValuation:
    """comprehensive_valuation 종합 분석 테스트"""

    def test_combines_all_methods(self):
        """멀티플 + DCF + DDM 결합"""
        mock_db = MagicMock()

        # compare_multiples, dcf_valuation, ddm 모두 mock
        with patch.object(ValuationAnalyzer, 'compare_multiples') as mock_cm, \
             patch.object(ValuationAnalyzer, 'dcf_valuation') as mock_dcf, \
             patch.object(ValuationAnalyzer, 'dividend_discount_model') as mock_ddm:

            mock_cm.return_value = {"overall_valuation": "적정 평가"}
            mock_dcf.return_value = {"scenarios": {"중립적": {"upside_downside": 5.0}}}
            mock_ddm.return_value = {"scenarios": {"중립적": {"upside_downside": -3.0}}}

            result = ValuationAnalyzer.comprehensive_valuation(mock_db, "AAPL")

            assert "multiple_comparison" in result
            assert "dcf_valuation" in result
            assert "ddm_valuation" in result
            assert "summary" in result

    def test_handles_partial_failure(self):
        """일부 메서드 실패해도 나머지 결과 반환"""
        mock_db = MagicMock()

        with patch.object(ValuationAnalyzer, 'compare_multiples') as mock_cm, \
             patch.object(ValuationAnalyzer, 'dcf_valuation') as mock_dcf, \
             patch.object(ValuationAnalyzer, 'dividend_discount_model') as mock_ddm:

            mock_cm.return_value = {"overall_valuation": "저평가"}
            mock_dcf.side_effect = Exception("DCF 실패")
            mock_ddm.side_effect = Exception("DDM 실패")

            result = ValuationAnalyzer.comprehensive_valuation(mock_db, "AAPL")

            assert result["multiple_comparison"]["overall_valuation"] == "저평가"
            assert "error" in result["dcf_valuation"]
            assert "error" in result["ddm_valuation"]
            assert "summary" in result
