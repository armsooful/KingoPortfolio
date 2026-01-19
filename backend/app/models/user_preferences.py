"""
Phase 3-C / U-3: 사용자 설정/이력 모델
"""

from datetime import datetime
import uuid

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON, Index, UniqueConstraint

from app.database import Base


def _uuid_str() -> str:
    return str(uuid.uuid4())


class UserPreset(Base):
    """사용자 프리셋(보기/정렬/필터)"""
    __tablename__ = "user_preset"

    preset_id = Column(String(36), primary_key=True, default=_uuid_str)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    preset_type = Column(String(20), nullable=False)
    preset_name = Column(String(100), nullable=False)
    preset_payload = Column(JSON, nullable=False)
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "preset_type", "preset_name", name="uq_user_preset_name"),
        Index("idx_user_preset_user", "user_id"),
        Index("idx_user_preset_type", "preset_type"),
    )


class UserNotificationSetting(Base):
    """사용자 알림/노출 빈도 설정"""
    __tablename__ = "user_notification_setting"

    setting_id = Column(String(36), primary_key=True, default=_uuid_str)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    enable_alerts = Column(Boolean, nullable=False, default=False)
    exposure_frequency = Column(String(20), nullable=False, default="STANDARD")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_user_notification_user", "user_id"),
    )


class UserActivityEvent(Base):
    """사용자 활동/상태 이벤트"""
    __tablename__ = "user_activity_event"

    event_id = Column(String(36), primary_key=True, default=_uuid_str)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)
    reason_code = Column(String(50), nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_user_activity_user", "user_id"),
        Index("idx_user_activity_time", "occurred_at"),
    )
