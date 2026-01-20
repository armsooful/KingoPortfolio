"""
Phase 7: 사용자 주도 포트폴리오 평가용 입력 저장 모델

사용자가 직접 선택한 종목/섹터 구성과 비중을 저장한다.
추천/최적화 로직은 포함하지 않는다.
"""

from datetime import datetime
from sqlalchemy import (
    Integer,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    CheckConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Phase7Portfolio(Base):
    __tablename__ = "phase7_portfolio"

    portfolio_id = Column(Integer, primary_key=True, autoincrement=True)
    owner_user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    portfolio_type = Column(String(20), nullable=False)  # SECURITY | SECTOR
    portfolio_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship(
        "Phase7PortfolioItem",
        back_populates="portfolio",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    __table_args__ = (
        Index("idx_phase7_portfolio_owner", "owner_user_id"),
        Index("idx_phase7_portfolio_type", "portfolio_type"),
    )

    def to_dict(self, include_items: bool = True) -> dict:
        result = {
            "portfolio_id": self.portfolio_id,
            "portfolio_type": self.portfolio_type,
            "portfolio_name": self.portfolio_name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_items:
            result["items"] = [item.to_dict() for item in self.items]
        return result


class Phase7PortfolioItem(Base):
    __tablename__ = "phase7_portfolio_item"

    item_id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(
        Integer,
        ForeignKey("phase7_portfolio.portfolio_id", ondelete="CASCADE"),
        nullable=False,
    )
    item_key = Column(String(50), nullable=False)
    item_name = Column(String(100), nullable=False)
    weight = Column(Numeric(6, 4), nullable=False)

    portfolio = relationship("Phase7Portfolio", back_populates="items")

    __table_args__ = (
        CheckConstraint("weight >= 0 AND weight <= 1", name="chk_phase7_weight_range"),
        Index("idx_phase7_portfolio_item_portfolio", "portfolio_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.item_key,
            "name": self.item_name,
            "weight": float(self.weight),
        }
