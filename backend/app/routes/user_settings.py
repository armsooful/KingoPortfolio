"""
Phase 3-C / U-3: 사용자 설정/이력 API
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user_preferences import UserPreset, UserNotificationSetting, UserActivityEvent
from app.models.user import User


router = APIRouter(prefix="/api/v1/users/me", tags=["UserSettings"])

_ALLOWED_PRESET_TYPES = {"VIEW", "SORT", "FILTER"}
_ALLOWED_FREQUENCIES = {"LOW", "STANDARD", "HIGH"}
_ALLOWED_STATUSES = {"IN_PROGRESS", "DEFERRED", "BLOCKED", "COMPLETED"}


def _normalize_preset_type(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().upper()


def _normalize_frequency(value: str | None) -> str:
    if not value:
        return "STANDARD"
    return value.strip().upper()


@router.get("/presets")
def list_presets(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    presets = (
        db.query(UserPreset)
        .filter(UserPreset.user_id == current_user.id)
        .order_by(UserPreset.updated_at.desc())
        .all()
    )
    return {
        "success": True,
        "data": [
            {
                "preset_id": preset.preset_id,
                "preset_type": preset.preset_type,
                "preset_name": preset.preset_name,
                "preset_payload": preset.preset_payload,
                "is_default": preset.is_default,
                "created_at": preset.created_at,
                "updated_at": preset.updated_at,
            }
            for preset in presets
        ],
    }


@router.post("/presets")
def create_preset(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    preset_type = _normalize_preset_type(payload.get("preset_type"))
    if preset_type not in _ALLOWED_PRESET_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="preset_type은 VIEW/SORT/FILTER 중 하나여야 합니다.",
        )

    preset_name = (payload.get("preset_name") or "").strip()
    if not preset_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="preset_name이 필요합니다.",
        )

    preset_payload = payload.get("preset_payload")
    if not isinstance(preset_payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="preset_payload는 객체여야 합니다.",
        )

    is_default = bool(payload.get("is_default", False))

    if is_default:
        (
            db.query(UserPreset)
            .filter(
                UserPreset.user_id == current_user.id,
                UserPreset.preset_type == preset_type,
                UserPreset.is_default == True,
            )
            .update({"is_default": False})
        )

    preset = UserPreset(
        user_id=current_user.id,
        preset_type=preset_type,
        preset_name=preset_name,
        preset_payload=preset_payload,
        is_default=is_default,
    )
    db.add(preset)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 동일한 이름의 프리셋이 있습니다.",
        )

    db.refresh(preset)
    return {
        "success": True,
        "data": {
            "preset_id": preset.preset_id,
            "preset_type": preset.preset_type,
            "preset_name": preset.preset_name,
            "preset_payload": preset.preset_payload,
            "is_default": preset.is_default,
            "created_at": preset.created_at,
            "updated_at": preset.updated_at,
        },
    }


@router.patch("/presets/{preset_id}")
def update_preset(
    preset_id: str,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    preset = (
        db.query(UserPreset)
        .filter(
            UserPreset.preset_id == preset_id,
            UserPreset.user_id == current_user.id,
        )
        .first()
    )
    if not preset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="프리셋을 찾을 수 없습니다.",
        )

    if "preset_name" in payload:
        preset_name = (payload.get("preset_name") or "").strip()
        if not preset_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="preset_name이 필요합니다.",
            )
        preset.preset_name = preset_name

    if "preset_payload" in payload:
        preset_payload = payload.get("preset_payload")
        if not isinstance(preset_payload, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="preset_payload는 객체여야 합니다.",
            )
        preset.preset_payload = preset_payload

    if "is_default" in payload:
        is_default = bool(payload.get("is_default"))
        if is_default:
            (
                db.query(UserPreset)
                .filter(
                    UserPreset.user_id == current_user.id,
                    UserPreset.preset_type == preset.preset_type,
                    UserPreset.is_default == True,
                    UserPreset.preset_id != preset.preset_id,
                )
                .update({"is_default": False})
            )
        preset.is_default = is_default

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 동일한 이름의 프리셋이 있습니다.",
        )

    db.refresh(preset)
    return {
        "success": True,
        "data": {
            "preset_id": preset.preset_id,
            "preset_type": preset.preset_type,
            "preset_name": preset.preset_name,
            "preset_payload": preset.preset_payload,
            "is_default": preset.is_default,
            "created_at": preset.created_at,
            "updated_at": preset.updated_at,
        },
    }


@router.delete("/presets/{preset_id}")
def delete_preset(
    preset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    preset = (
        db.query(UserPreset)
        .filter(
            UserPreset.preset_id == preset_id,
            UserPreset.user_id == current_user.id,
        )
        .first()
    )
    if not preset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="프리셋을 찾을 수 없습니다.",
        )

    db.delete(preset)
    db.commit()

    return {"success": True, "data": {"preset_id": preset_id}}


@router.get("/notification-settings")
def get_notification_settings(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    setting = (
        db.query(UserNotificationSetting)
        .filter(UserNotificationSetting.user_id == current_user.id)
        .first()
    )

    if not setting:
        return {
            "success": True,
            "data": {
                "enable_alerts": False,
                "exposure_frequency": "STANDARD",
            },
        }

    return {
        "success": True,
        "data": {
            "enable_alerts": setting.enable_alerts,
            "exposure_frequency": setting.exposure_frequency,
            "created_at": setting.created_at,
            "updated_at": setting.updated_at,
        },
    }


@router.put("/notification-settings")
def update_notification_settings(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enable_alerts = payload.get("enable_alerts", False)
    if not isinstance(enable_alerts, bool):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="enable_alerts는 true/false여야 합니다.",
        )

    exposure_frequency = _normalize_frequency(payload.get("exposure_frequency"))
    if exposure_frequency not in _ALLOWED_FREQUENCIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="exposure_frequency는 LOW/STANDARD/HIGH 중 하나여야 합니다.",
        )

    setting = (
        db.query(UserNotificationSetting)
        .filter(UserNotificationSetting.user_id == current_user.id)
        .first()
    )
    if not setting:
        setting = UserNotificationSetting(
            user_id=current_user.id,
            enable_alerts=enable_alerts,
            exposure_frequency=exposure_frequency,
        )
        db.add(setting)
    else:
        setting.enable_alerts = enable_alerts
        setting.exposure_frequency = exposure_frequency

    db.commit()
    db.refresh(setting)

    return {
        "success": True,
        "data": {
            "enable_alerts": setting.enable_alerts,
            "exposure_frequency": setting.exposure_frequency,
            "created_at": setting.created_at,
            "updated_at": setting.updated_at,
        },
    }


@router.get("/activity-events")
def list_activity_events(
    response: Response,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    safe_limit = max(1, min(limit, 200))
    safe_offset = max(offset, 0)

    events = (
        db.query(UserActivityEvent)
        .filter(UserActivityEvent.user_id == current_user.id)
        .order_by(UserActivityEvent.occurred_at.desc())
        .offset(safe_offset)
        .limit(safe_limit)
        .all()
    )

    return {
        "success": True,
        "data": [
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "status": event.status,
                "reason_code": event.reason_code,
                "metadata": event.metadata_json,
                "occurred_at": event.occurred_at,
            }
            for event in events
        ],
        "meta": {
            "limit": safe_limit,
            "offset": safe_offset,
        },
    }


@router.post("/activity-events")
def create_activity_event(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    event_type = (payload.get("event_type") or "").strip()
    if not event_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="event_type이 필요합니다.",
        )

    status_value = (payload.get("status") or "").strip().upper()
    if status_value not in _ALLOWED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status는 IN_PROGRESS/DEFERRED/BLOCKED/COMPLETED 중 하나여야 합니다.",
        )

    reason_code = payload.get("reason_code")
    if reason_code is not None:
        reason_code = str(reason_code).strip() or None

    metadata = payload.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="metadata는 객체여야 합니다.",
        )

    event = UserActivityEvent(
        user_id=current_user.id,
        event_type=event_type,
        status=status_value,
        reason_code=reason_code,
        metadata_json=metadata,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    return {
        "success": True,
        "data": {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "status": event.status,
            "reason_code": event.reason_code,
            "metadata": event.metadata_json,
            "occurred_at": event.occurred_at,
        },
    }
