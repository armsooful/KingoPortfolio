"""
관심 종목 (Watchlist) 모델
"""

import uuid

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, UniqueConstraint, Index

from app.database import Base
from app.utils.kst_now import kst_now


def _uuid_str() -> str:
    return str(uuid.uuid4())


class Watchlist(Base):
    """사용자 관심 종목"""
    __tablename__ = "watchlist"

    watchlist_id = Column(String(36), primary_key=True, default=_uuid_str)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ticker = Column(String(10), ForeignKey("stocks.ticker", ondelete="CASCADE"), nullable=False)
    last_notified_score = Column(Float, nullable=True)
    last_notified_grade = Column(String(5), nullable=True)
    created_at = Column(DateTime, nullable=False, default=kst_now)

    __table_args__ = (
        UniqueConstraint("user_id", "ticker", name="uq_watchlist_user_ticker"),
        Index("idx_watchlist_user", "user_id"),
        Index("idx_watchlist_ticker", "ticker"),
    )
