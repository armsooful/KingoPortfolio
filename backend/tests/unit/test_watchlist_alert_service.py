"""
watchlist_alert_service 단위 테스트

_detect_changes (DB fixture),
_render_alert_email (Jinja2 텍스트/HTML),
send_watchlist_alerts (구독자 없음 케이스).
"""
import pytest
from datetime import date

from app.services.watchlist_alert_service import (
    _detect_changes,
    _render_alert_email,
    send_watchlist_alerts,
    SCORE_THRESHOLD,
)
from app.models.securities import Stock
from app.models.watchlist import Watchlist
from app.models.user import User
from app.models.user_preferences import UserNotificationSetting
from app.auth import hash_password


# ============================================================================
# _detect_changes — DB fixture (5개)
# ============================================================================

@pytest.mark.unit
class TestDetectChanges:
    """watchlist 내 점수/등급 변동 감지"""

    def _setup_stock_and_watchlist(self, db, user_id, ticker, name,
                                   compass_score, compass_grade,
                                   last_score=None, last_grade=None,
                                   compass_summary=""):
        """Stock + Watchlist 레코드 생성 헬퍼"""
        stock = Stock(
            ticker=ticker, name=name,
            compass_score=compass_score, compass_grade=compass_grade,
            compass_summary=compass_summary,
        )
        db.add(stock)
        db.flush()
        wl = Watchlist(
            user_id=user_id, ticker=ticker,
            last_notified_score=last_score, last_notified_grade=last_grade,
        )
        db.add(wl)
        db.commit()

    def test_score_change_above_threshold(self, db, test_user):
        """점수 변동 ≥ SCORE_THRESHOLD → 감지"""
        self._setup_stock_and_watchlist(
            db, test_user.id, "005930", "삼성전자",
            compass_score=72.0, compass_grade="A",
            last_score=65.0, last_grade="B+",
        )
        changes = _detect_changes(db, test_user.id)
        assert len(changes) == 1
        assert changes[0]["ticker"] == "005930"
        assert changes[0]["score_diff"] == 7.0

    def test_score_change_below_threshold(self, db, test_user):
        """점수 변동 < SCORE_THRESHOLD → 미감지"""
        self._setup_stock_and_watchlist(
            db, test_user.id, "005930", "삼성전자",
            compass_score=67.0, compass_grade="B+",
            last_score=65.0, last_grade="B+",
        )
        changes = _detect_changes(db, test_user.id)
        assert len(changes) == 0

    def test_grade_change_only(self, db, test_user):
        """점수 차이 < 5이지만 등급 변경 → 감지"""
        self._setup_stock_and_watchlist(
            db, test_user.id, "005930", "삼성전자",
            compass_score=70.1, compass_grade="A",
            last_score=69.9, last_grade="B+",
        )
        changes = _detect_changes(db, test_user.id)
        assert len(changes) == 1
        assert changes[0]["prev_grade"] == "B+"
        assert changes[0]["current_grade"] == "A"

    def test_no_previous_score_skipped(self, db, test_user):
        """last_notified_score=None (최초) → 스킵"""
        self._setup_stock_and_watchlist(
            db, test_user.id, "005930", "삼성전자",
            compass_score=72.0, compass_grade="A",
            last_score=None, last_grade=None,
        )
        changes = _detect_changes(db, test_user.id)
        assert len(changes) == 0

    def test_compass_score_none_skipped(self, db, test_user):
        """Stock.compass_score=None → 스킵"""
        self._setup_stock_and_watchlist(
            db, test_user.id, "005930", "삼성전자",
            compass_score=None, compass_grade=None,
            last_score=65.0, last_grade="B+",
        )
        changes = _detect_changes(db, test_user.id)
        assert len(changes) == 0

    def test_multiple_stocks_mixed(self, db, test_user):
        """여러 종목 중 변동된 것만 반환"""
        # 변동 O (diff=8)
        self._setup_stock_and_watchlist(
            db, test_user.id, "005930", "삼성전자",
            compass_score=73.0, compass_grade="A",
            last_score=65.0, last_grade="B+",
        )
        # 변동 X (diff=2)
        self._setup_stock_and_watchlist(
            db, test_user.id, "000660", "SK하이닉스",
            compass_score=62.0, compass_grade="B+",
            last_score=60.0, last_grade="B+",
        )
        changes = _detect_changes(db, test_user.id)
        assert len(changes) == 1
        assert changes[0]["ticker"] == "005930"


# ============================================================================
# _render_alert_email — 텍스트/HTML 렌더링 (3개)
# ============================================================================

@pytest.mark.unit
class TestRenderAlertEmail:
    """알림 이메일 렌더링 테스트"""

    def _sample_changes(self):
        return [
            {
                "ticker": "005930",
                "name": "삼성전자",
                "prev_score": 65.0,
                "current_score": 72.0,
                "score_diff": 7.0,
                "prev_grade": "B+",
                "current_grade": "A",
                "summary": "우량 대형주",
                "watchlist_entry": None,
            },
        ]

    def test_text_contains_key_fields(self):
        """텍스트 폴백 — 종목명, 점수, 등급 포함"""
        _, text = _render_alert_email(self._sample_changes(), "테스트유저")
        assert "테스트유저" in text
        assert "삼성전자" in text
        assert "005930" in text
        assert "65.0" in text
        assert "72.0" in text
        assert "B+" in text
        assert "A" in text
        assert "+7.0" in text

    def test_text_includes_disclaimer(self):
        """텍스트에 면책 고지 포함"""
        _, text = _render_alert_email(self._sample_changes(), "테스트유저")
        assert "교육 목적" in text
        assert "투자 권유" in text

    def test_html_rendering(self):
        """HTML 렌더링 에러 없음"""
        html, _ = _render_alert_email(self._sample_changes(), "테스트유저")
        assert "<html" in html.lower()
        assert "삼성전자" in html


# ============================================================================
# send_watchlist_alerts — 구독자 없음 (1개)
# ============================================================================

@pytest.mark.unit
class TestSendWatchlistAlerts:
    """알림 발송 오케스트레이터 테스트"""

    @pytest.mark.asyncio
    async def test_no_subscribers(self, db):
        """구독자 없으면 즉시 반환"""
        result = await send_watchlist_alerts(db)
        assert result["total_users"] == 0
        assert result["emails_sent"] == 0
