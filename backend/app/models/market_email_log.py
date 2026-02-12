"""
시장 요약 이메일 발송 이력 모델
"""

from sqlalchemy import Column, Integer, String, Date, DateTime, Text, Index

from app.database import Base
from app.utils.kst_now import kst_now


class MarketEmailLog(Base):
    """일별 시장 요약 이메일 발송 로그"""
    __tablename__ = "market_email_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sent_date = Column(Date, nullable=False)
    total_subscribers = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    fail_count = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="pending")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    triggered_by = Column(String(50), nullable=False, default="scheduler")
    created_at = Column(DateTime, nullable=False, default=kst_now)

    __table_args__ = (
        Index("idx_market_email_log_date", "sent_date"),
    )
