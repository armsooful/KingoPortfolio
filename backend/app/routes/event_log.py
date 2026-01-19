"""
Phase 3-D / 이벤트 수집 API
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.event_log import UserEventLog
from app.models.user import User


router = APIRouter(prefix="/api/v1/events", tags=["EventLog"])

_ALLOWED_STATUSES = {"IN_PROGRESS", "DEFERRED", "BLOCKED", "COMPLETED"}
_FORBIDDEN_METADATA_KEYS = {
    "amount",
    "balance",
    "profit",
    "return",
    "performance",
    "score",
    "recommendation",
    "rank",
}


def _normalize_str(value: str | None) -> str:
    if not value:
        return ""
    return value.strip()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_event(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    event_type = _normalize_str(payload.get("event_type"))
    if not event_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="event_type이 필요합니다.",
        )

    path = _normalize_str(payload.get("path"))
    if not path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="path가 필요합니다.",
        )

    status_value = _normalize_str(payload.get("status")).upper()
    if status_value not in _ALLOWED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status는 IN_PROGRESS/DEFERRED/BLOCKED/COMPLETED 중 하나여야 합니다.",
        )

    reason_code = payload.get("reason_code")
    if reason_code is not None:
        reason_code = _normalize_str(str(reason_code)) or None

    metadata = payload.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="metadata는 객체여야 합니다.",
        )

    if metadata:
        forbidden = _FORBIDDEN_METADATA_KEYS.intersection({str(key).lower() for key in metadata.keys()})
        if forbidden:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="metadata에 허용되지 않은 키가 포함되어 있습니다.",
            )

    occurred_at = payload.get("occurred_at")
    if occurred_at:
        try:
            occurred_at = datetime.fromisoformat(str(occurred_at))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="occurred_at 형식이 올바르지 않습니다.",
            )
    else:
        occurred_at = datetime.utcnow()

    event = UserEventLog(
        user_id=current_user.id,
        event_type=event_type,
        path=path,
        status=status_value,
        reason_code=reason_code,
        metadata_json=metadata,
        occurred_at=occurred_at,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    return {
        "success": True,
        "data": {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "path": event.path,
            "status": event.status,
            "reason_code": event.reason_code,
            "metadata": event.metadata_json,
            "occurred_at": event.occurred_at,
        },
    }
