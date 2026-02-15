"""
market.py 유틸 함수 단위 테스트

외부 API(yfinance, pykrx) 의존 없는 순수 로직 위주
- calculate_market_sentiment: 시장 심리 판단
- generate_simple_summary: 템플릿 기반 요약
- get_mock_news / get_mock_stocks: 정적 데이터
- fetch_naver_finance_news: httpx mock
"""
import pytest
from unittest.mock import patch, MagicMock

from app.routes.market import (
    calculate_market_sentiment,
    generate_simple_summary,
    get_mock_news,
    get_mock_stocks,
    fetch_naver_finance_news,
)


# ============================================================================
# calculate_market_sentiment
# ============================================================================

@pytest.mark.unit
class TestMarketSentiment:
    """시장 심리 신호등 판단"""

    def test_positive_above_05(self):
        """평균 등락률 > 0.5% → 긍정(green)"""
        indices = [
            {"name": "KOSPI", "changePercent": 1.0},
            {"name": "KOSDAQ", "changePercent": 0.5},
        ]
        result = calculate_market_sentiment(indices)
        assert result["color"] == "green"
        assert result["status"] == "긍정적"

    def test_negative_below_minus_05(self):
        """평균 등락률 < -0.5% → 위험(red)"""
        indices = [
            {"name": "KOSPI", "changePercent": -1.0},
            {"name": "KOSDAQ", "changePercent": -0.8},
        ]
        result = calculate_market_sentiment(indices)
        assert result["color"] == "red"
        assert result["status"] == "위험"

    def test_neutral_range(self):
        """평균 등락률 -0.5%~0.5% → 중립(yellow)"""
        indices = [
            {"name": "KOSPI", "changePercent": 0.2},
            {"name": "KOSDAQ", "changePercent": -0.1},
        ]
        result = calculate_market_sentiment(indices)
        assert result["color"] == "yellow"
        assert result["status"] == "중립"

    def test_no_kospi_returns_neutral(self):
        """KOSPI 데이터 없음 → 중립"""
        indices = [{"name": "NASDAQ", "changePercent": 2.0}]
        result = calculate_market_sentiment(indices)
        assert result["color"] == "yellow"

    def test_boundary_exactly_05(self):
        """정확히 0.5% → 중립 (0.5 초과가 아님)"""
        indices = [
            {"name": "KOSPI", "changePercent": 0.5},
        ]
        result = calculate_market_sentiment(indices)
        assert result["color"] == "yellow"


# ============================================================================
# generate_simple_summary
# ============================================================================

@pytest.mark.unit
class TestSimpleSummary:
    """템플릿 기반 시장 요약"""

    def test_kospi_up(self):
        """코스피 상승 → '상승' 포함"""
        indices = [
            {"name": "KOSPI", "changePercent": 1.5},
            {"name": "KOSDAQ", "changePercent": 0.8},
        ]
        gainers = [{"name": "삼성전자"}]
        losers = []
        result = generate_simple_summary(indices, gainers, losers)
        assert "상승" in result["text"]

    def test_kospi_down(self):
        """코스피 하락 → '하락' 포함"""
        indices = [
            {"name": "KOSPI", "changePercent": -1.2},
            {"name": "KOSDAQ", "changePercent": -0.5},
        ]
        result = generate_simple_summary(indices, [], [])
        assert "하락" in result["text"]

    def test_kospi_flat(self):
        """코스피 보합"""
        indices = [
            {"name": "KOSPI", "changePercent": 0.0},
            {"name": "KOSDAQ", "changePercent": 0.1},
        ]
        result = generate_simple_summary(indices, [], [])
        assert "보합" in result["text"]

    def test_no_kospi_data(self):
        """코스피 데이터 없음 → 기본 메시지"""
        result = generate_simple_summary([], [], [])
        assert "불러오는 중" in result["text"]

    def test_returns_sentiment(self):
        """sentiment 포함 확인"""
        indices = [{"name": "KOSPI", "changePercent": 1.0}]
        result = generate_simple_summary(indices, [], [])
        assert "sentiment" in result
        assert "color" in result["sentiment"]

    def test_gainers_mentioned(self):
        """상승 종목명이 요약에 포함"""
        indices = [
            {"name": "KOSPI", "changePercent": 1.0},
            {"name": "KOSDAQ", "changePercent": 0.5},
        ]
        gainers = [{"name": "삼성전자"}, {"name": "SK하이닉스"}]
        result = generate_simple_summary(indices, gainers, [])
        assert "삼성전자" in result["text"]


# ============================================================================
# get_mock_news / get_mock_stocks
# ============================================================================

@pytest.mark.unit
class TestMockData:
    """정적 Mock 데이터"""

    def test_mock_news_structure(self):
        news = get_mock_news()
        assert len(news) == 3
        for item in news:
            assert "title" in item
            assert "source" in item
            assert "publishedAt" in item
            assert "url" in item

    def test_mock_stocks_structure(self):
        gainers, losers = get_mock_stocks()
        assert len(gainers) == 3
        assert len(losers) == 3
        for s in gainers:
            assert s["change"] > 0
        for s in losers:
            assert s["change"] < 0


# ============================================================================
# fetch_naver_finance_news (mock)
# ============================================================================

@pytest.mark.unit
class TestFetchNaverNews:
    """네이버 뉴스 크롤링 (외부 요청 mock)"""

    def test_failure_returns_mock(self):
        """크롤링 실패 → Mock 뉴스 반환"""
        with patch("app.routes.market.get_with_retry") as mock_get:
            mock_get.side_effect = Exception("Connection timeout")
            news = fetch_naver_finance_news(limit=5)

        assert len(news) == 3  # get_mock_news 기본 개수
        assert news[0]["title"]  # 내용 있음

    def test_empty_response_returns_mock(self):
        """빈 HTML → Mock 뉴스 반환"""
        with patch("app.routes.market.get_with_retry") as mock_get:
            mock_resp = MagicMock()
            mock_resp.text = "<html><body></body></html>"
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp
            news = fetch_naver_finance_news(limit=5)

        assert len(news) == 3  # fallback to mock
