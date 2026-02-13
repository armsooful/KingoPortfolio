"""
시장 요약 이메일 구독/해지 API (사용자용)
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.user_preferences import UserNotificationSetting
from app.routes.auth import get_current_user

router = APIRouter(
    prefix="/api/v1/market-subscription",
    tags=["Market Subscription"],
)


def _get_or_create_setting(db: Session, user_id: str) -> UserNotificationSetting:
    setting = db.query(UserNotificationSetting).filter(
        UserNotificationSetting.user_id == user_id
    ).first()
    if not setting:
        setting = UserNotificationSetting(user_id=user_id)
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return setting


@router.get("/status")
async def get_subscription_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """구독 상태 조회"""
    setting = _get_or_create_setting(db, current_user.id)
    return {
        "subscribed": setting.daily_market_email,
        "subscribed_at": setting.daily_market_email_subscribed_at,
        "unsubscribed_at": setting.daily_market_email_unsubscribed_at,
        "is_email_verified": current_user.is_email_verified,
    }


@router.post("/subscribe")
async def subscribe_market_email(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """시장 요약 이메일 구독 (이메일 인증 필수)"""
    if not current_user.is_email_verified:
        raise HTTPException(
            status_code=400,
            detail="이메일 인증 후 구독이 가능합니다.",
        )

    setting = _get_or_create_setting(db, current_user.id)
    if setting.daily_market_email:
        return {"message": "이미 구독 중입니다.", "subscribed": True}

    setting.daily_market_email = True
    setting.daily_market_email_subscribed_at = datetime.utcnow()
    setting.daily_market_email_unsubscribed_at = None
    db.commit()

    return {"message": "시장 요약 이메일을 구독했습니다.", "subscribed": True}


@router.post("/unsubscribe")
async def unsubscribe_market_email(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """시장 요약 이메일 구독 해제"""
    setting = _get_or_create_setting(db, current_user.id)
    if not setting.daily_market_email:
        return {"message": "현재 구독 중이 아닙니다.", "subscribed": False}

    setting.daily_market_email = False
    setting.daily_market_email_unsubscribed_at = datetime.utcnow()
    db.commit()

    return {"message": "시장 요약 이메일 구독을 해제했습니다.", "subscribed": False}


@router.get("/watchlist-alerts/status")
async def get_watchlist_alert_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """관심 종목 점수 변동 알림 상태 조회"""
    setting = _get_or_create_setting(db, current_user.id)
    return {
        "enabled": setting.watchlist_score_alerts,
        "is_email_verified": current_user.is_email_verified,
    }


@router.post("/watchlist-alerts/toggle")
async def toggle_watchlist_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """관심 종목 점수 변동 알림 토글 (이메일 인증 필수)"""
    if not current_user.is_email_verified:
        raise HTTPException(
            status_code=400,
            detail="이메일 인증 후 알림을 활성화할 수 있습니다.",
        )

    setting = _get_or_create_setting(db, current_user.id)
    setting.watchlist_score_alerts = not setting.watchlist_score_alerts
    db.commit()

    status_text = "활성화" if setting.watchlist_score_alerts else "비활성화"
    return {
        "message": f"관심 종목 알림이 {status_text}되었습니다.",
        "enabled": setting.watchlist_score_alerts,
    }
