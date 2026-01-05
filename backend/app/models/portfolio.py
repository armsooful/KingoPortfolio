"""
포트폴리오 및 포트폴리오 히스토리 모델
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Date, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Portfolio(Base):
    """
    사용자 포트폴리오 모델
    """
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    investment_type = Column(String(50))  # conservative, moderate, aggressive

    # 현재 포트폴리오 가치
    total_value = Column(Float, default=0)
    total_return = Column(Float, default=0)  # 수익률 (%)

    # 포트폴리오 구성 (JSON)
    composition = Column(JSON)  # {stocks: [...], etfs: [...], bonds: [...], deposits: [...]}

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계
    user = relationship("User", back_populates="portfolios")
    histories = relationship("PortfolioHistory", back_populates="portfolio", cascade="all, delete-orphan")


class PortfolioHistory(Base):
    """
    포트폴리오 일별 히스토리 모델
    성과 추적을 위한 시계열 데이터
    """
    __tablename__ = "portfolio_histories"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)

    # 일별 포트폴리오 가치
    total_value = Column(Float, nullable=False)
    total_return = Column(Float, default=0)  # 수익률 (%)

    # 일별 변동
    daily_change = Column(Float, default=0)  # 전일 대비 변동 금액
    daily_change_percent = Column(Float, default=0)  # 전일 대비 변동률 (%)

    # 자산별 구성 비율 (스냅샷)
    allocation_snapshot = Column(JSON)  # {stocks: 60, etfs: 20, bonds: 15, deposits: 5}

    created_at = Column(DateTime, default=datetime.utcnow)

    # 관계
    portfolio = relationship("Portfolio", back_populates="histories")
