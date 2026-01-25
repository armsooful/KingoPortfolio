"""
Phase 3-C / U-2: 북마크 모델
"""

from datetime import datetime
import uuid

from sqlalchemy import Column, String, BigInteger, DateTime, ForeignKey, UniqueConstraint, Index

from app.database import Base
from app.utils.kst_now import kst_now


def _uuid_str() -> str:
    return str(uuid.uuid4())


class Bookmark(Base):
    """사용자 북마크"""
    __tablename__ = "bookmark"

    bookmark_id = Column(String(36), primary_key=True, default=_uuid_str)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    portfolio_id = Column(BigInteger, ForeignKey("custom_portfolio.portfolio_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=kst_now)

    __table_args__ = (
        UniqueConstraint("user_id", "portfolio_id", name="uq_bookmark_user_portfolio"),
        Index("idx_bookmark_user", "user_id"),
        Index("idx_bookmark_portfolio", "portfolio_id"),
    )
