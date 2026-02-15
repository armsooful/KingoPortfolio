"""
관리자용 시장 이메일 관리 API
"""
import logging

from datetime import date, datetime
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models.market_email_log import MarketEmailLog
from app.models.user import User
from app.models.user_preferences import UserNotificationSetting
from app.routes.auth import get_current_user
from app.services.market_email_service import (
    get_market_email_content,
    render_market_email_html,
    render_market_email_text,
    send_daily_market_emails,
)
from app.utils.email import send_email

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/market-email",
    tags=["Admin - Market Email"],
)


def _require_admin(user: User):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")


@router.get("/subscribers")
async def get_subscribers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """구독자 목록 조회"""
    _require_admin(current_user)

    rows = (
        db.query(User.email, User.name, UserNotificationSetting.daily_market_email_subscribed_at)
        .join(UserNotificationSetting, User.id == UserNotificationSetting.user_id)
        .filter(
            UserNotificationSetting.daily_market_email.is_(True),
            User.is_email_verified.is_(True),
        )
        .all()
    )

    return {
        "total": len(rows),
        "subscribers": [
            {
                "email": r.email,
                "name": r.name,
                "subscribed_at": r.daily_market_email_subscribed_at,
            }
            for r in rows
        ],
    }


@router.get("/logs")
async def get_email_logs(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """발송 이력 조회"""
    _require_admin(current_user)

    logs = (
        db.query(MarketEmailLog)
        .order_by(MarketEmailLog.sent_date.desc())
        .limit(limit)
        .all()
    )

    return {
        "total": len(logs),
        "logs": [
            {
                "id": log.id,
                "sent_date": str(log.sent_date),
                "total_subscribers": log.total_subscribers,
                "success_count": log.success_count,
                "fail_count": log.fail_count,
                "status": log.status,
                "started_at": log.started_at,
                "completed_at": log.completed_at,
                "error_message": log.error_message,
                "triggered_by": log.triggered_by,
            }
            for log in logs
        ],
    }


@router.get("/stats")
async def get_email_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """이메일 통계 (구독자 수, 최근 발송)"""
    _require_admin(current_user)

    subscriber_count = (
        db.query(func.count())
        .select_from(UserNotificationSetting)
        .join(User, User.id == UserNotificationSetting.user_id)
        .filter(
            UserNotificationSetting.daily_market_email.is_(True),
            User.is_email_verified.is_(True),
        )
        .scalar()
    )

    last_log = (
        db.query(MarketEmailLog)
        .filter(MarketEmailLog.status == "completed")
        .order_by(MarketEmailLog.sent_date.desc())
        .first()
    )

    return {
        "subscriber_count": subscriber_count,
        "last_sent": {
            "date": str(last_log.sent_date) if last_log else None,
            "success_count": last_log.success_count if last_log else 0,
            "fail_count": last_log.fail_count if last_log else 0,
        } if last_log else None,
    }


@router.post("/send-test")
async def send_test_email(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """관리자 자신에게 테스트 이메일 발송"""
    _require_admin(current_user)

    data = get_market_email_content(db=db)
    html = render_market_email_html(data)
    text = render_market_email_text(data)

    ok = await send_email(
        to_email=current_user.email,
        subject=f"[TEST] Foresto Compass {data['date']} 시장 요약",
        html_content=html,
        text_content=text,
    )

    if not ok:
        raise HTTPException(status_code=500, detail="이메일 발송에 실패했습니다.")

    return {"message": f"테스트 이메일을 {current_user.email}로 발송했습니다."}


@router.post("/send-now")
async def send_now(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """수동 전체 발송 (BackgroundTask)"""
    _require_admin(current_user)

    async def _background_send():
        _db = SessionLocal()
        try:
            result = await send_daily_market_emails(_db, triggered_by="manual")
            logger.info("Manual market email result: %s", result)
        finally:
            _db.close()

    background_tasks.add_task(_background_send)
    return {"message": "시장 요약 이메일 발송을 시작합니다."}
