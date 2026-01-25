"""
포트폴리오 및 포트폴리오 히스토리 모델
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Date, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base
from app.utils.kst_now import kst_now


class Portfolio(Base):
    """
    사용자 포트폴리오 모델
    """
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    investment_type = Column(String(50))  # conservative, moderate, aggressive

    # 현재 포트폴리오 가치
    total_value = Column(Float, default=0)
    total_return = Column(Float, default=0)  # 수익률 (%)

    # 포트폴리오 구성 (JSON)
    composition = Column(JSON)  # {stocks: [...], etfs: [...], bonds: [...], deposits: [...]}

    created_at = Column(DateTime, default=kst_now)
    updated_at = Column(DateTime, default=kst_now, onupdate=kst_now)

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

    created_at = Column(DateTime, default=kst_now)

    # 관계
    portfolio = relationship("Portfolio", back_populates="histories")


class SimulationCache(Base):
    """
    시뮬레이션 결과 캐시 모델
    동일 요청에 대해 결과를 재사용하기 위한 캐시
    """
    __tablename__ = "simulation_cache"

    id = Column(Integer, primary_key=True, index=True)
    request_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA-256 해시
    request_type = Column(String(50), nullable=False)  # backtest, compare, etc.
    request_params = Column(JSON, nullable=False)  # 원본 요청 파라미터
    result_data = Column(JSON, nullable=False)  # 캐시된 결과
    engine_version = Column(String(20), nullable=False, default="1.0.0")  # 결과 생성 시 엔진 버전

    hit_count = Column(Integer, default=0)  # 캐시 히트 횟수
    created_at = Column(DateTime, default=kst_now)
    last_accessed_at = Column(DateTime, default=kst_now)
    expires_at = Column(DateTime, nullable=True)  # 만료 시간 (None이면 무기한)
