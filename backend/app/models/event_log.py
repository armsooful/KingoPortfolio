"""
Phase 3-D / 이벤트 로그 모델
"""

from datetime import datetime
import uuid

from sqlalchemy import Column, String, DateTime, JSON, Index

from app.database import Base


def _uuid_str() -> str:
    return str(uuid.uuid4())


class UserEventLog(Base):
    """사용자 행동 이벤트 로그"""
    __tablename__ = "user_event_log"

    event_id = Column(String(36), primary_key=True, default=_uuid_str)
    user_id = Column(String(36), nullable=False)
    event_type = Column(String(50), nullable=False)
    path = Column(String(200), nullable=False)
    status = Column(String(20), nullable=False)
    reason_code = Column(String(50), nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_user_event_log_user_time", "user_id", "occurred_at"),
        Index("idx_user_event_log_type", "event_type"),
    )
