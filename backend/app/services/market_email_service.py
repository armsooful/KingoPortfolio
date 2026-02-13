"""
데일리 시장 요약 이메일 서비스

시장 데이터 수집 → HTML 렌더링 → 구독자에게 발송
"""

import asyncio
import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.market_email_log import MarketEmailLog
from app.models.user import User
from app.models.user_preferences import UserNotificationSetting
from app.routes.market import fetch_naver_finance_news, get_top_stocks_by_change
from app.services.scoring_engine import ScoringEngine
from app.utils.email import send_email, FRONTEND_URL

logger = logging.getLogger(__name__)

# Jinja2 템플릿 환경
_templates_dir = Path(__file__).resolve().parent.parent / "templates"
_jinja_env = Environment(loader=FileSystemLoader(str(_templates_dir)), autoescape=True)


def _fetch_index_data() -> List[Dict[str, Any]]:
    """yfinance로 주요 지수 4개 조회 (KOSPI, KOSDAQ, S&P500, NASDAQ)"""
    import yfinance as yf

    symbols = [
        ("^KS11", "KOSPI"),
        ("^KQ11", "KOSDAQ"),
        ("^GSPC", "S&P 500"),
        ("^IXIC", "NASDAQ"),
    ]
    indices = []
    for symbol, name in symbols:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d")
            if not hist.empty and len(hist) >= 2:
                current = hist["Close"].iloc[-1]
                prev = hist["Close"].iloc[-2]
                change = current - prev
                pct = (change / prev) * 100
                indices.append({
                    "name": name,
                    "value": round(current, 2),
                    "change": round(change, 2),
                    "changePercent": round(pct, 2),
                })
            elif not hist.empty:
                indices.append({
                    "name": name,
                    "value": round(hist["Close"].iloc[-1], 2),
                    "change": 0.0,
                    "changePercent": 0.0,
                })
        except Exception as e:
            logger.warning("Failed to fetch %s: %s", name, e)
    return indices


def _fetch_compass_scores(
    db: Session,
    gainers: List[Dict],
    losers: List[Dict],
) -> List[Dict[str, Any]]:
    """gainers + losers에서 ticker 추출 → Compass Score 계산 (최대 6종목)"""
    scored = []
    seen = set()

    for stock in gainers + losers:
        ticker = stock.get("symbol", "")
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)

        try:
            result = ScoringEngine.calculate_compass_score(db, ticker)
            if "error" in result:
                continue
            scored.append({
                "ticker": ticker,
                "name": result.get("company_name") or stock.get("name", ticker),
                "compass_score": result["compass_score"],
                "grade": result["grade"],
                "summary": result["summary"],
                "price": stock.get("price", 0),
                "change": stock.get("change", 0),
            })
        except Exception as e:
            logger.warning("Compass score failed for %s: %s", ticker, e)

    return scored


def get_market_email_content(db: Optional[Session] = None) -> Dict[str, Any]:
    """
    이메일 콘텐츠용 시장 데이터 수집.
    기존 market.py 함수를 재사용한다.
    """
    indices = _fetch_index_data()
    gainers, losers = get_top_stocks_by_change(3)
    news = fetch_naver_finance_news(5)

    # Compass Score 수집 (db가 있을 때만)
    scored_stocks = []
    if db:
        try:
            scored_stocks = _fetch_compass_scores(db, gainers, losers)
        except Exception as e:
            logger.warning("Compass score collection failed: %s", e)

    return {
        "date": date.today().strftime("%Y년 %m월 %d일"),
        "indices": indices,
        "gainers": gainers,
        "losers": losers,
        "news": news,
        "scored_stocks": scored_stocks,
        "frontend_url": FRONTEND_URL,
    }


def render_market_email_html(data: Dict[str, Any]) -> str:
    """Jinja2 HTML 이메일 렌더링"""
    template = _jinja_env.get_template("market_daily_email.html")
    return template.render(**data)


def render_market_email_text(data: Dict[str, Any]) -> str:
    """플레인텍스트 폴백"""
    lines = [
        f"Foresto Compass 시장 요약 - {data['date']}",
        "",
        "=== 주요 지수 ===",
    ]
    for idx in data["indices"]:
        sign = "+" if idx["changePercent"] >= 0 else ""
        lines.append(f"  {idx['name']}: {idx['value']} ({sign}{idx['changePercent']}%)")

    lines.append("")
    lines.append("=== 상승 종목 Top 3 ===")
    for s in data["gainers"]:
        lines.append(f"  {s['name']} ({s['symbol']}): {s['price']:,}원 (+{s['change']}%)")

    lines.append("")
    lines.append("=== 하락 종목 Top 3 ===")
    for s in data["losers"]:
        lines.append(f"  {s['name']} ({s['symbol']}): {s['price']:,}원 ({s['change']}%)")

    lines.append("")
    lines.append("=== 뉴스 ===")
    for n in data["news"]:
        lines.append(f"  - {n['title']}")

    scored = data.get("scored_stocks", [])
    if scored:
        lines.append("")
        lines.append("=== Compass Score 하이라이트 ===")
        for s in scored:
            lines.append(f"  {s['name']} ({s['ticker']}): {s['compass_score']}점 [{s['grade']}] — {s['summary']}")

    lines.append("")
    lines.append("---")
    lines.append("본 이메일은 교육 목적의 참고 자료이며, 투자 권유/추천이 아닙니다.")
    lines.append("과거 성과가 미래 수익을 보장하지 않습니다.")
    lines.append(f"구독 해제: {data['frontend_url']}/profile")

    return "\n".join(lines)


async def send_daily_market_emails(
    db: Session,
    triggered_by: str = "scheduler",
) -> Dict[str, Any]:
    """
    메인 오케스트레이터: 시장 데이터 수집 → 구독자 전원에게 발송.

    Returns:
        dict with success_count, fail_count, total
    """
    today = date.today()

    # 중복 발송 방지
    existing = db.query(MarketEmailLog).filter(
        MarketEmailLog.sent_date == today,
        MarketEmailLog.status.in_(["completed", "sending"]),
    ).first()
    if existing:
        logger.info("Daily market email already sent/sending for %s", today)
        return {"skipped": True, "reason": "already_sent"}

    # 로그 레코드 생성
    log = MarketEmailLog(
        sent_date=today,
        status="sending",
        started_at=datetime.utcnow(),
        triggered_by=triggered_by,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    try:
        # 구독자 조회: daily_market_email=True AND is_email_verified=True
        subscribers = (
            db.query(User.email)
            .join(UserNotificationSetting, User.id == UserNotificationSetting.user_id)
            .filter(
                UserNotificationSetting.daily_market_email.is_(True),
                User.is_email_verified.is_(True),
            )
            .all()
        )
        emails = [row.email for row in subscribers]
        log.total_subscribers = len(emails)
        db.commit()

        if not emails:
            log.status = "completed"
            log.completed_at = datetime.utcnow()
            db.commit()
            return {"success_count": 0, "fail_count": 0, "total": 0}

        # 시장 데이터 1회 fetch (db 전달 → Compass Score 포함)
        data = get_market_email_content(db=db)
        html = render_market_email_html(data)
        text = render_market_email_text(data)
        subject = f"[Foresto Compass] {data['date']} 시장 요약"

        success = 0
        fail = 0

        for email in emails:
            try:
                ok = await send_email(
                    to_email=email,
                    subject=subject,
                    html_content=html,
                    text_content=text,
                )
                if ok:
                    success += 1
                else:
                    fail += 1
            except Exception as e:
                logger.error("Failed to send market email to %s: %s", email, e)
                fail += 1

            # SMTP rate limit 방지
            await asyncio.sleep(0.5)

        log.success_count = success
        log.fail_count = fail
        log.status = "completed"
        log.completed_at = datetime.utcnow()
        db.commit()

        return {"success_count": success, "fail_count": fail, "total": len(emails)}

    except Exception as e:
        logger.exception("send_daily_market_emails failed")
        log.status = "failed"
        log.error_message = str(e)[:500]
        log.completed_at = datetime.utcnow()
        db.commit()
        return {"error": str(e)}


async def scheduled_daily_email():
    """APScheduler에서 호출하는 래퍼 (DB 세션 자체 관리)"""
    db = SessionLocal()
    try:
        result = await send_daily_market_emails(db, triggered_by="scheduler")
        logger.info("Scheduled daily market email result: %s", result)
    finally:
        db.close()
