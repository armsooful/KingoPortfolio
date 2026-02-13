"""
관심 종목 점수 변동 알림 서비스

매일 08:00 KST에 APScheduler가 호출.
watchlist_score_alerts=True AND is_email_verified=True 사용자 대상으로
점수 ±5점 이상 또는 등급 변경 시 이메일 알림.
"""

import asyncio
import logging
from datetime import date
from pathlib import Path
from typing import Dict, Any, List

from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User
from app.models.user_preferences import UserNotificationSetting
from app.models.watchlist import Watchlist
from app.models.securities import Stock
from app.utils.email import send_email, FRONTEND_URL

logger = logging.getLogger(__name__)

SCORE_THRESHOLD = 5.0  # ±5점 이상 변동 시 알림

_templates_dir = Path(__file__).resolve().parent.parent / "templates"
_jinja_env = Environment(loader=FileSystemLoader(str(_templates_dir)), autoescape=True)


def _detect_changes(
    db: Session, user_id: str
) -> List[Dict[str, Any]]:
    """사용자 watchlist에서 변동 감지. 변동된 종목 목록 반환."""
    rows = (
        db.query(Watchlist, Stock)
        .join(Stock, Watchlist.ticker == Stock.ticker)
        .filter(Watchlist.user_id == user_id)
        .all()
    )

    changed = []
    for w, s in rows:
        if s.compass_score is None:
            continue

        score_changed = False
        grade_changed = False

        if w.last_notified_score is not None:
            diff = abs(s.compass_score - w.last_notified_score)
            if diff >= SCORE_THRESHOLD:
                score_changed = True

        if w.last_notified_grade and s.compass_grade:
            if w.last_notified_grade != s.compass_grade:
                grade_changed = True

        # 최초 알림 (last_notified_score가 None인 경우)도 스킵
        if not score_changed and not grade_changed:
            continue

        score_diff = round(s.compass_score - (w.last_notified_score or 0), 1)
        changed.append({
            "ticker": w.ticker,
            "name": s.name or w.ticker,
            "prev_score": w.last_notified_score,
            "current_score": round(s.compass_score, 1),
            "score_diff": score_diff,
            "prev_grade": w.last_notified_grade or "-",
            "current_grade": s.compass_grade or "-",
            "summary": s.compass_summary or "",
            "watchlist_entry": w,
        })

    return changed


def _render_alert_email(changes: List[Dict], user_name: str) -> tuple:
    """HTML + 텍스트 이메일 렌더링"""
    template = _jinja_env.get_template("watchlist_alert_email.html")
    html = template.render(
        date=date.today().strftime("%Y년 %m월 %d일"),
        user_name=user_name,
        changes=changes,
        frontend_url=FRONTEND_URL,
    )

    # 텍스트 폴백
    lines = [
        f"Foresto Compass 관심 종목 점수 변동 알림 — {date.today().strftime('%Y년 %m월 %d일')}",
        f"",
        f"안녕하세요, {user_name}님.",
        f"",
    ]
    for c in changes:
        sign = "+" if c["score_diff"] > 0 else ""
        lines.append(
            f"  {c['name']} ({c['ticker']}): "
            f"{c['prev_score'] or '-'} → {c['current_score']} ({sign}{c['score_diff']}) "
            f"[{c['prev_grade']} → {c['current_grade']}]"
        )
    lines.append("")
    lines.append("---")
    lines.append("본 이메일은 교육 목적의 참고 자료이며, 투자 권유/추천이 아닙니다.")
    lines.append(f"알림 설정 변경: {FRONTEND_URL}/watchlist")

    return html, "\n".join(lines)


async def send_watchlist_alerts(db: Session) -> Dict[str, Any]:
    """
    메인 함수: 변동 감지 → 이메일 발송 → last_notified 갱신
    """
    # 알림 활성화 + 이메일 인증 사용자 조회
    subscribers = (
        db.query(User)
        .join(UserNotificationSetting, User.id == UserNotificationSetting.user_id)
        .filter(
            UserNotificationSetting.watchlist_score_alerts.is_(True),
            User.is_email_verified.is_(True),
        )
        .all()
    )

    if not subscribers:
        logger.info("No watchlist alert subscribers found")
        return {"total_users": 0, "emails_sent": 0}

    emails_sent = 0
    emails_failed = 0

    for user in subscribers:
        try:
            changes = _detect_changes(db, user.id)
            if not changes:
                continue

            user_name = user.name or user.email.split("@")[0]
            html, text = _render_alert_email(changes, user_name)

            ok = await send_email(
                to_email=user.email,
                subject=f"[Foresto Compass] 관심 종목 점수 변동 알림 ({date.today().strftime('%m/%d')})",
                html_content=html,
                text_content=text,
            )

            if ok:
                emails_sent += 1
                # 알림 성공 시 last_notified 갱신
                for c in changes:
                    w = c["watchlist_entry"]
                    w.last_notified_score = c["current_score"]
                    w.last_notified_grade = c["current_grade"]
                db.commit()
            else:
                emails_failed += 1

            # SMTP rate limit 방지
            await asyncio.sleep(0.5)

        except Exception as e:
            logger.error("Watchlist alert failed for user %s: %s", user.id, e)
            emails_failed += 1

    result = {
        "total_users": len(subscribers),
        "emails_sent": emails_sent,
        "emails_failed": emails_failed,
    }
    logger.info("Watchlist alert result: %s", result)
    return result


async def scheduled_watchlist_alerts():
    """APScheduler에서 호출하는 래퍼 (DB 세션 자체 관리)"""
    db = SessionLocal()
    try:
        result = await send_watchlist_alerts(db)
        logger.info("Scheduled watchlist alerts result: %s", result)
    finally:
        db.close()
