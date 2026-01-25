from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.database import Base


class ConsentAgreement(Base):
    __tablename__ = "consent_agreement"

    consent_id = Column(Integer, primary_key=True, autoincrement=True)
    owner_user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    consent_type = Column(String(50), nullable=False)
    consent_version = Column(String(20), nullable=False)
    consent_text = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    agreed_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_consent_owner", "owner_user_id"),
        Index("idx_consent_type_version", "consent_type", "consent_version"),
    )
