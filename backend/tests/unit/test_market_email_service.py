"""
market_email_service 단위 테스트

render_market_email_text (순수 함수, mock 불필요),
render_market_email_html (Jinja2 템플릿),
_fetch_compass_scores / _fetch_score_movers (ScoringEngine mock),
send_daily_market_emails 중복 방지 (DB fixture).
"""
import pytest
from datetime import date, datetime
from unittest.mock import patch, MagicMock

from app.services.market_email_service import (
    render_market_email_text,
    render_market_email_html,
    _fetch_compass_scores,
    _fetch_score_movers,
    send_daily_market_emails,
)
from app.models.market_email_log import MarketEmailLog
from app.models.securities import Stock


# ============================================================================
# 테스트용 데이터 헬퍼
# ============================================================================

def _base_data(**overrides):
    """render 함수에 넘길 최소 data dict"""
    data = {
        "date": "2026년 02월 15일",
        "indices": [
            {"name": "KOSPI", "value": 2650.12, "change": 15.30, "changePercent": 0.58},
            {"name": "KOSDAQ", "value": 870.45, "change": -3.20, "changePercent": -0.37},
        ],
        "gainers": [
            {"name": "삼성전자", "symbol": "005930", "price": 72000, "change": 3.5},
        ],
        "losers": [
            {"name": "LG에너지솔루션", "symbol": "373220", "price": 380000, "change": -2.1},
        ],
        "news": [
            {"title": "코스피 반등...외국인 순매수", "url": "https://example.com/1"},
        ],
        "scored_stocks": [],
        "score_movers": [],
        "frontend_url": "http://localhost:5173",
    }
    data.update(overrides)
    return data


def _scored_stock(**overrides):
    """Compass Score 종목 dict"""
    item = {
        "ticker": "005930",
        "name": "삼성전자",
        "compass_score": 72.5,
        "grade": "A",
        "summary": "우량 대형주",
        "commentary": "재무 안정적, 기술적 과매도 구간",
        "categories": {
            "financial": 80,
            "valuation": 65,
            "technical": 70,
            "risk": 75,
        },
        "price": 72000,
        "change": 3.5,
    }
    item.update(overrides)
    return item


def _score_mover(**overrides):
    """Score 변동 종목 dict"""
    item = {
        "ticker": "005930",
        "name": "삼성전자",
        "prev_score": 65.0,
        "current_score": 72.5,
        "diff": 7.5,
        "grade": "A",
        "summary": "우량 대형주",
        "commentary": "기술적 반등 신호",
    }
    item.update(overrides)
    return item


# ============================================================================
# render_market_email_text — 순수 함수 테스트 (5개)
# ============================================================================

@pytest.mark.unit
class TestRenderMarketEmailText:
    """플레인텍스트 렌더링 테스트"""

    def test_basic_rendering(self):
        """기본 렌더링 — 지수, 상승/하락, 뉴스 섹션 포함"""
        text = render_market_email_text(_base_data())

        assert "2026년 02월 15일" in text
        assert "=== 주요 지수 ===" in text
        assert "KOSPI" in text
        assert "KOSDAQ" in text
        assert "=== 상승 종목 Top 3 ===" in text
        assert "삼성전자" in text
        assert "=== 하락 종목 Top 3 ===" in text
        assert "LG에너지솔루션" in text
        assert "=== 뉴스 ===" in text
        assert "코스피 반등" in text

    def test_with_compass_scores(self):
        """scored_stocks 포함 시 Compass Score 하이라이트 섹션 렌더"""
        data = _base_data(scored_stocks=[_scored_stock()])
        text = render_market_email_text(data)

        assert "=== Compass Score 하이라이트 ===" in text
        assert "72.5점" in text
        assert "[A]" in text
        assert "재무 80" in text
        assert "밸류 65" in text
        assert "기술 70" in text
        assert "리스크 75" in text
        assert "재무 안정적" in text

    def test_with_score_movers(self):
        """score_movers 포함 시 변동 종목 섹션 + 화살표/diff"""
        up_mover = _score_mover(diff=7.5)
        down_mover = _score_mover(
            ticker="373220", name="LG에너지솔루션",
            prev_score=70.0, current_score=62.0, diff=-8.0,
            grade="B+", commentary="밸류에이션 부담",
        )
        data = _base_data(score_movers=[up_mover, down_mover])
        text = render_market_email_text(data)

        assert "=== Score 변동 주목 종목 ===" in text
        assert "▲" in text
        assert "▼" in text
        assert "+7.5" in text
        assert "-8.0" in text
        assert "65.0점 → 72.5점" in text

    def test_empty_data(self):
        """빈 데이터 → 에러 없이 렌더링"""
        data = _base_data(indices=[], gainers=[], losers=[], news=[])
        text = render_market_email_text(data)

        assert "Foresto Compass 시장 요약" in text
        assert "=== 주요 지수 ===" in text
        # 빈 섹션이지만 에러 없이 렌더 완료
        assert "=== 뉴스 ===" in text

    def test_legal_notice(self):
        """법적 고지 — 자본시장법 제6조, 구독 해제 링크 포함"""
        data = _base_data(unsubscribe_url="https://example.com/unsub/token123")
        text = render_market_email_text(data)

        assert "[법적 고지]" in text
        assert "자본시장법" in text
        assert "제6조" in text
        assert "투자 권유" in text
        assert "투자 추천" in text
        assert "구독 해제: https://example.com/unsub/token123" in text

    def test_legal_notice_fallback_url(self):
        """unsubscribe_url 없으면 frontend_url/profile로 폴백"""
        data = _base_data()
        # unsubscribe_url 키 없음
        text = render_market_email_text(data)
        assert "구독 해제: http://localhost:5173/profile" in text


# ============================================================================
# render_market_email_html — Jinja2 실제 템플릿 테스트 (2개)
# ============================================================================

@pytest.mark.unit
class TestRenderMarketEmailHtml:
    """HTML 렌더링 테스트 (실제 Jinja2 템플릿 사용)"""

    def test_basic_html_rendering(self):
        """HTML 기본 렌더링 — <html> 태그, 에러 없음"""
        html = render_market_email_html(_base_data())

        assert "<html" in html.lower()
        assert "Foresto Compass" in html
        assert "2026년 02월 15일" in html
        assert "KOSPI" in html

    def test_html_with_compass_scores(self):
        """HTML에 Compass Score 데이터 반영"""
        data = _base_data(scored_stocks=[_scored_stock()])
        html = render_market_email_html(data)

        assert "삼성전자" in html
        # 템플릿이 compass_score|int 필터 사용 → 72로 렌더
        assert ">72<" in html
        assert "재무 안정적" in html


# ============================================================================
# _fetch_compass_scores — ScoringEngine mock (2개)
# ============================================================================

@pytest.mark.unit
class TestFetchCompassScores:
    """Compass Score 수집 테스트"""

    @patch("app.services.market_email_service.ScoringEngine")
    def test_normal_collection(self, mock_engine):
        """정상 수집 — ScoringEngine mock → 올바른 dict 구조"""
        mock_engine.calculate_compass_score.return_value = {
            "compass_score": 72.5,
            "grade": "A",
            "company_name": "삼성전자",
            "summary": "우량 대형주",
            "commentary": "재무 안정적",
            "categories": {
                "financial": {"score": 80},
                "valuation": {"score": 65},
                "technical": {"score": 70},
                "risk": {"score": 75},
            },
        }
        db = MagicMock()
        gainers = [{"symbol": "005930", "name": "삼성전자", "price": 72000, "change": 3.5}]
        losers = [{"symbol": "373220", "name": "LG에너지솔루션", "price": 380000, "change": -2.1}]

        result = _fetch_compass_scores(db, gainers, losers)

        assert len(result) == 2
        assert result[0]["ticker"] == "005930"
        assert result[0]["compass_score"] == 72.5
        assert result[0]["grade"] == "A"
        assert result[0]["categories"]["financial"] == 80
        assert result[1]["ticker"] == "373220"

    @patch("app.services.market_email_service.ScoringEngine")
    def test_error_stock_skipped(self, mock_engine):
        """ScoringEngine이 error 반환 → 해당 종목 제외"""
        mock_engine.calculate_compass_score.side_effect = [
            {"error": "데이터 부족"},  # 첫 번째 종목 실패
            {
                "compass_score": 55.0,
                "grade": "B",
                "company_name": "LG에너지솔루션",
                "summary": "보통",
                "categories": {
                    "financial": {"score": 50},
                    "valuation": {"score": 60},
                    "technical": {"score": 55},
                    "risk": {"score": 50},
                },
            },
        ]
        db = MagicMock()
        gainers = [{"symbol": "005930", "name": "삼성전자", "price": 72000, "change": 3.5}]
        losers = [{"symbol": "373220", "name": "LG에너지솔루션", "price": 380000, "change": -2.1}]

        result = _fetch_compass_scores(db, gainers, losers)

        assert len(result) == 1
        assert result[0]["ticker"] == "373220"


# ============================================================================
# _fetch_score_movers — DB fixture + ScoringEngine mock (2개)
# ============================================================================

@pytest.mark.unit
class TestFetchScoreMovers:
    """Score 변동 종목 선별 테스트"""

    @patch("app.services.market_email_service.ScoringEngine")
    def test_only_5_plus_diff(self, mock_engine, db):
        """±5점 이상만 반환, 미만은 제외"""
        # DB에 compass_score가 있는 Stock 생성
        s1 = Stock(ticker="005930", name="삼성전자", compass_score=65.0, market_cap=400_000_000_000_000)
        s2 = Stock(ticker="000660", name="SK하이닉스", compass_score=70.0, market_cap=100_000_000_000_000)
        db.add_all([s1, s2])
        db.commit()

        mock_engine.calculate_compass_score.side_effect = [
            # 삼성전자: 65→72 (diff=7, ≥5 → 포함)
            {"compass_score": 72.0, "grade": "A", "company_name": "삼성전자", "summary": "s", "commentary": "c"},
            # SK하이닉스: 70→73 (diff=3, <5 → 제외)
            {"compass_score": 73.0, "grade": "A", "company_name": "SK하이닉스", "summary": "s", "commentary": "c"},
        ]

        result = _fetch_score_movers(db, limit=3)

        assert len(result) == 1
        assert result[0]["ticker"] == "005930"
        assert result[0]["diff"] == 7.0

    @patch("app.services.market_email_service.ScoringEngine")
    def test_sorted_by_abs_diff_and_limited(self, mock_engine, db):
        """|diff| 큰 순서 정렬 + limit 적용"""
        stocks = [
            Stock(ticker="A", name="종목A", compass_score=50.0, market_cap=300_000_000_000_000),
            Stock(ticker="B", name="종목B", compass_score=50.0, market_cap=200_000_000_000_000),
            Stock(ticker="C", name="종목C", compass_score=50.0, market_cap=100_000_000_000_000),
            Stock(ticker="D", name="종목D", compass_score=50.0, market_cap=50_000_000_000_000),
        ]
        db.add_all(stocks)
        db.commit()

        mock_engine.calculate_compass_score.side_effect = [
            # A: diff=+6
            {"compass_score": 56.0, "grade": "B", "company_name": "종목A", "summary": "s", "commentary": "c"},
            # B: diff=-10
            {"compass_score": 40.0, "grade": "C+", "company_name": "종목B", "summary": "s", "commentary": "c"},
            # C: diff=+15
            {"compass_score": 65.0, "grade": "B+", "company_name": "종목C", "summary": "s", "commentary": "c"},
            # D: diff=+8
            {"compass_score": 58.0, "grade": "B", "company_name": "종목D", "summary": "s", "commentary": "c"},
        ]

        result = _fetch_score_movers(db, limit=3)

        assert len(result) == 3
        # |diff| 순서: C(15) > B(10) > D(8), A(6)는 limit 밖
        assert result[0]["ticker"] == "C"
        assert result[0]["diff"] == 15.0
        assert result[1]["ticker"] == "B"
        assert result[1]["diff"] == -10.0
        assert result[2]["ticker"] == "D"
        assert result[2]["diff"] == 8.0


# ============================================================================
# send_daily_market_emails — 중복 방지 (1개)
# ============================================================================

@pytest.mark.unit
class TestSendDailyMarketEmails:
    """이메일 발송 오케스트레이터 테스트"""

    @pytest.mark.asyncio
    async def test_duplicate_prevention(self, db):
        """이미 completed 로그 존재 → skipped=True"""
        log = MarketEmailLog(
            sent_date=date.today(),
            status="completed",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            triggered_by="scheduler",
        )
        db.add(log)
        db.commit()

        result = await send_daily_market_emails(db, triggered_by="manual")

        assert result["skipped"] is True
        assert result["reason"] == "already_sent"
