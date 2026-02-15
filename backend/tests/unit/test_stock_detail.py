"""
stock_detail.py 엔드포인트 단위 테스트

대상:
- GET /admin/stock-detail/{ticker}
- POST /admin/stock-detail/{ticker}/ai-commentary
- GET /admin/stock-detail/search/ticker-list
"""
import pytest
from datetime import datetime, timedelta, date
from decimal import Decimal
from unittest.mock import patch, MagicMock

from app.models.securities import Stock
from app.models.real_data import StockPriceDaily
from app.utils.kst_now import kst_now


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_stock(db):
    """시계열 데이터 포함 테스트 종목"""
    stock = Stock(
        ticker="005930",
        name="삼성전자",
        market="KOSPI",
        sector="반도체",
        current_price=78500.0,
        market_cap=469_000_000_000_000.0,
        pe_ratio=12.5,
        pb_ratio=1.3,
        dividend_yield=2.1,
        ytd_return=5.2,
        one_year_return=12.3,
        compass_score=72.5,
        compass_grade="A",
        compass_summary="재무 안정, 기술 양호",
        compass_commentary="삼성전자는 반도체 업황 회복에 따라...",
        compass_financial_score=80.0,
        compass_valuation_score=65.0,
        compass_technical_score=70.0,
        compass_risk_score=75.0,
        compass_updated_at=kst_now(),
    )
    db.add(stock)
    db.flush()

    # 시계열 데이터 5일치
    base_date = date.today() - timedelta(days=10)
    prices = [
        (78000, 79000, 77500, 78500, 1_000_000),
        (78500, 80000, 78000, 79500, 1_200_000),
        (79500, 79800, 78200, 78800, 900_000),
        (78800, 81000, 78500, 80500, 1_500_000),
        (80500, 81500, 80000, 81000, 1_100_000),
    ]
    for i, (o, h, l, c, v) in enumerate(prices):
        td = base_date + timedelta(days=i)
        db.add(StockPriceDaily(
            ticker="005930",
            trade_date=td,
            open_price=Decimal(str(o)),
            high_price=Decimal(str(h)),
            low_price=Decimal(str(l)),
            close_price=Decimal(str(c)),
            volume=v,
            source_id="PYKRX",
            as_of_date=td,
        ))
    db.commit()
    return stock


@pytest.fixture
def stock_no_timeseries(db):
    """시계열 없는 종목"""
    stock = Stock(
        ticker="000660",
        name="SK하이닉스",
        market="KOSPI",
        sector="반도체",
        current_price=145000.0,
    )
    db.add(stock)
    db.commit()
    return stock


@pytest.fixture
def multiple_stocks(db):
    """검색 테스트용 복수 종목"""
    stocks = [
        Stock(ticker="005930", name="삼성전자", market="KOSPI", current_price=78500),
        Stock(ticker="005935", name="삼성전자우", market="KOSPI", current_price=66000),
        Stock(ticker="000660", name="SK하이닉스", market="KOSPI", current_price=145000),
        Stock(ticker="035420", name="NAVER", market="KOSPI", current_price=210000),
    ]
    for s in stocks:
        db.add(s)
    db.commit()
    return stocks


# ============================================================================
# GET /{ticker} — 종목 상세 조회
# ============================================================================

@pytest.mark.unit
class TestGetStockDetail:
    """GET /admin/stock-detail/{ticker}"""

    def test_stock_detail_with_timeseries(self, client, admin_headers, sample_stock):
        """종목 + 시계열 + 통계 정상 반환"""
        resp = client.get(
            "/admin/stock-detail/005930",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]

        # basic_info
        info = data["basic_info"]
        assert info["ticker"] == "005930"
        assert info["name"] == "삼성전자"
        assert info["market"] == "KOSPI"
        assert info["current_price"] == 78500.0

        # financials
        fin = data["financials"]
        assert fin["pe_ratio"] == 12.5
        assert fin["pb_ratio"] == 1.3

        # compass
        compass = data["compass"]
        assert compass["score"] == 72.5
        assert compass["grade"] == "A"
        assert compass["financial_score"] == 80.0
        assert compass["updated_at"] is not None

        # timeseries
        ts = data["timeseries"]
        assert ts["data_count"] == 5
        assert len(ts["data"]) == 5
        assert ts["data"][0]["open"] == 78000.0
        assert ts["data"][-1]["close"] == 81000.0

        # statistics
        stats = data["statistics"]
        assert stats["period_days"] == 5
        assert stats["high"] == 81500.0
        assert stats["low"] == 77500.0
        assert stats["period_return"] > 0  # 78500 → 81000

    def test_stock_detail_no_timeseries(self, client, admin_headers, stock_no_timeseries):
        """시계열 없는 종목 — statistics null"""
        resp = client.get(
            "/admin/stock-detail/000660",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["timeseries"]["data_count"] == 0
        assert data["statistics"] is None

    def test_stock_detail_not_found(self, client, admin_headers):
        """존재하지 않는 종목 → 404"""
        resp = client.get(
            "/admin/stock-detail/999999",
            headers=admin_headers,
        )
        assert resp.status_code == 404

    def test_stock_detail_requires_admin(self, client, auth_headers, sample_stock):
        """일반 사용자 접근 → 403"""
        resp = client.get(
            "/admin/stock-detail/005930",
            headers=auth_headers,
        )
        assert resp.status_code == 403

    def test_stock_detail_no_auth(self, client, sample_stock):
        """인증 없음 → 401"""
        resp = client.get("/admin/stock-detail/005930")
        assert resp.status_code == 401


# ============================================================================
# POST /{ticker}/ai-commentary — AI 해설 생성
# ============================================================================

@pytest.mark.unit
class TestAICommentary:
    """POST /admin/stock-detail/{ticker}/ai-commentary"""

    def test_db_cache_hit(self, client, admin_headers, sample_stock):
        """24시간 이내 compass_updated_at → ScoringEngine 호출 없이 캐시 사용"""
        with patch(
            "app.services.scoring_engine.ScoringEngine.calculate_compass_score"
        ) as mock_calc:
            resp = client.post(
                "/admin/stock-detail/005930/ai-commentary",
                headers=admin_headers,
            )
            # 24시간 이내이므로 ScoringEngine 호출되지 않아야 함
            mock_calc.assert_not_called()

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_db_cache_miss_stale(self, client, admin_headers, db, sample_stock):
        """compass_updated_at이 24시간 초과 → ScoringEngine 재계산"""
        sample_stock.compass_updated_at = kst_now() - timedelta(hours=25)
        db.commit()

        mock_result = {
            "compass_score": 70.0,
            "grade": "A",
            "summary": "재계산 결과",
            "commentary": "새로운 해설",
            "company_name": "삼성전자",
            "categories": {},
        }
        with patch("app.services.scoring_engine.ScoringEngine") as mock_engine:
            mock_engine.calculate_compass_score.return_value = mock_result
            resp = client.post(
                "/admin/stock-detail/005930/ai-commentary",
                headers=admin_headers,
            )
            mock_engine.calculate_compass_score.assert_called_once()

        assert resp.status_code == 200

    def test_db_cache_miss_no_score(self, client, admin_headers, db, stock_no_timeseries):
        """compass_score가 None → ScoringEngine 재계산"""
        mock_result = {
            "compass_score": 55.0,
            "grade": "B",
            "summary": "보통",
            "commentary": "해설",
            "company_name": "SK하이닉스",
            "categories": {},
        }
        with patch("app.services.scoring_engine.ScoringEngine") as mock_engine:
            mock_engine.calculate_compass_score.return_value = mock_result
            resp = client.post(
                "/admin/stock-detail/000660/ai-commentary",
                headers=admin_headers,
            )
            mock_engine.calculate_compass_score.assert_called_once()

        assert resp.status_code == 200

    def test_no_api_key_fallback(self, client, admin_headers, sample_stock):
        """ANTHROPIC_API_KEY 미설정 → rule_based 반환"""
        with patch("app.config.settings") as mock_settings:
            mock_settings.anthropic_api_key = None
            resp = client.post(
                "/admin/stock-detail/005930/ai-commentary",
                headers=admin_headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "rule_based"

    def test_claude_api_error_fallback(self, client, admin_headers, sample_stock):
        """Claude API 에러 → rule_based_fallback + ai_error 필드"""
        with patch("app.config.settings") as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            with patch("anthropic.Anthropic") as mock_anthropic:
                mock_client = MagicMock()
                mock_client.messages.create.side_effect = Exception("API timeout")
                mock_anthropic.return_value = mock_client

                resp = client.post(
                    "/admin/stock-detail/005930/ai-commentary",
                    headers=admin_headers,
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["source"] == "rule_based_fallback"
        assert "ai_error" in data
        assert "API timeout" in data["ai_error"]
        assert data["commentary"]  # fallback 해설 존재

    def test_claude_api_success(self, client, admin_headers, sample_stock):
        """Claude API 정상 → source=ai"""
        with patch("app.config.settings") as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            with patch("anthropic.Anthropic") as mock_anthropic:
                mock_msg = MagicMock()
                mock_msg.content = [MagicMock(text="AI가 생성한 상세 해설입니다.")]
                mock_client = MagicMock()
                mock_client.messages.create.return_value = mock_msg
                mock_anthropic.return_value = mock_client

                resp = client.post(
                    "/admin/stock-detail/005930/ai-commentary",
                    headers=admin_headers,
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "ai"
        assert "AI가 생성한" in data["commentary"]

    def test_ticker_not_found(self, client, admin_headers):
        """존재하지 않는 종목 → 404"""
        resp = client.post(
            "/admin/stock-detail/999999/ai-commentary",
            headers=admin_headers,
        )
        assert resp.status_code == 404

    def test_scoring_error(self, client, admin_headers, db, stock_no_timeseries):
        """ScoringEngine이 error 반환 → 404"""
        mock_result = {"error": "데이터 부족"}
        with patch("app.services.scoring_engine.ScoringEngine") as mock_engine:
            mock_engine.calculate_compass_score.return_value = mock_result
            resp = client.post(
                "/admin/stock-detail/000660/ai-commentary",
                headers=admin_headers,
            )
        assert resp.status_code == 404

    def test_requires_admin(self, client, auth_headers, sample_stock):
        """일반 사용자 → 403"""
        resp = client.post(
            "/admin/stock-detail/005930/ai-commentary",
            headers=auth_headers,
        )
        assert resp.status_code == 403


# ============================================================================
# GET /search/ticker-list — 종목 검색
# ============================================================================

@pytest.mark.unit
class TestTickerSearch:
    """GET /admin/stock-detail/search/ticker-list"""

    def test_search_all(self, client, admin_headers, multiple_stocks):
        """검색어 없이 전체 조회"""
        resp = client.get(
            "/admin/stock-detail/search/ticker-list",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["count"] == 4

    def test_search_by_ticker(self, client, admin_headers, multiple_stocks):
        """종목코드로 검색"""
        resp = client.get(
            "/admin/stock-detail/search/ticker-list?q=005930",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["count"] == 1
        assert data["tickers"][0]["ticker"] == "005930"

    def test_search_by_name(self, client, admin_headers, multiple_stocks):
        """종목명으로 검색"""
        resp = client.get(
            "/admin/stock-detail/search/ticker-list?q=삼성",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["count"] == 2  # 삼성전자, 삼성전자우

    def test_search_partial_ticker(self, client, admin_headers, multiple_stocks):
        """종목코드 부분 검색"""
        resp = client.get(
            "/admin/stock-detail/search/ticker-list?q=0059",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["count"] == 2  # 005930, 005935

    def test_search_no_results(self, client, admin_headers, multiple_stocks):
        """검색 결과 없음"""
        resp = client.get(
            "/admin/stock-detail/search/ticker-list?q=없는종목",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["count"] == 0
        assert data["tickers"] == []

    def test_search_limit(self, client, admin_headers, multiple_stocks):
        """limit 파라미터 동작"""
        resp = client.get(
            "/admin/stock-detail/search/ticker-list?limit=2",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["count"] <= 2

    def test_search_requires_admin(self, client, auth_headers, multiple_stocks):
        """일반 사용자 → 403"""
        resp = client.get(
            "/admin/stock-detail/search/ticker-list",
            headers=auth_headers,
        )
        assert resp.status_code == 403
