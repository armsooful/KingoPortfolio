"""
시장 요약 이메일 구독/해지 API (사용자용)
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.auth import verify_unsubscribe_token
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


@router.get("/one-click-unsubscribe/{token}", response_class=HTMLResponse)
async def one_click_unsubscribe(token: str, db: Session = Depends(get_db)):
    """원클릭 구독 해제 (로그인 불필요, 토큰 기반)"""
    user_id = verify_unsubscribe_token(token)
    if not user_id:
        return HTMLResponse(content=_unsub_html("링크가 만료되었거나 유효하지 않습니다.", success=False))

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return HTMLResponse(content=_unsub_html("사용자를 찾을 수 없습니다.", success=False))

    setting = db.query(UserNotificationSetting).filter(
        UserNotificationSetting.user_id == user_id
    ).first()

    if not setting or not setting.daily_market_email:
        return HTMLResponse(content=_unsub_html("이미 구독이 해제된 상태입니다.", success=True))

    setting.daily_market_email = False
    setting.daily_market_email_unsubscribed_at = datetime.utcnow()
    db.commit()

    return HTMLResponse(content=_unsub_html("시장 요약 이메일 구독이 해제되었습니다.", success=True))


def _unsub_html(message: str, success: bool) -> str:
    color = "#4caf50" if success else "#f44336"
    icon = "&#10003;" if success else "&#10007;"
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>구독 해제 - Foresto Compass</title>
  <style>
    body {{ font-family: 'Segoe UI', sans-serif; background: #f4f4f4; margin: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; }}
    .card {{ background: #fff; border-radius: 12px; padding: 48px 40px; text-align: center; max-width: 420px; box-shadow: 0 4px 24px rgba(0,0,0,0.1); }}
    .icon {{ font-size: 48px; color: {color}; margin-bottom: 16px; }}
    h1 {{ font-size: 20px; color: #333; margin: 0 0 12px; }}
    p {{ font-size: 14px; color: #666; line-height: 1.6; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">{icon}</div>
    <h1>{message}</h1>
    <p>Foresto Compass를 이용해 주셔서 감사합니다.</p>
  </div>
</body>
</html>"""
