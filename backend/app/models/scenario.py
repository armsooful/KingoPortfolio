"""
Phase 1 시나리오/포트폴리오 모델

scenario_definition, portfolio_model, portfolio_allocation 구조로
관리형 시나리오를 DB에서 조회
"""

from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, DateTime, Date,
    ForeignKey, Numeric, Text, Index, Boolean, JSON
)
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class ScenarioDefinition(Base):
    """
    시나리오 정의 (scenario_definition)

    관리형 시나리오 기본 정보
    """
    __tablename__ = "scenario_definition"

    scenario_id = Column(String(50), primary_key=True)
    name_ko = Column(String(100), nullable=False)
    name_en = Column(String(100))
    description = Column(Text)
    objective = Column(Text)
    target_investor = Column(Text)
    risk_level = Column(String(20))  # 'LOW', 'MEDIUM', 'HIGH'
    disclaimer = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계
    portfolios = relationship("PortfolioModel", back_populates="scenario")

    def __repr__(self):
        return f"<ScenarioDefinition {self.scenario_id}>"

    def to_summary(self) -> dict:
        """요약 정보 반환"""
        return {
            "id": self.scenario_id,
            "name": self.name_en or self.name_ko,
            "name_ko": self.name_ko,
            "short_description": self.objective,
        }

    def to_detail(self, allocation: dict = None, risk_metrics: dict = None,
                  learning_points: list = None) -> dict:
        """상세 정보 반환"""
        return {
            "id": self.scenario_id,
            "name": self.name_en or self.name_ko,
            "name_ko": self.name_ko,
            "description": self.description,
            "objective": self.objective,
            "target_investor": self.target_investor,
            "allocation": allocation or {},
            "risk_metrics": risk_metrics or {},
            "disclaimer": self.disclaimer,
            "learning_points": learning_points or [],
        }


class PortfolioModel(Base):
    """
    포트폴리오 모델 (portfolio_model)

    시나리오별 포트폴리오 정의 (적용일자 기준)
    """
    __tablename__ = "portfolio_model"

    portfolio_id = Column(BigInteger, primary_key=True, autoincrement=True)
    scenario_id = Column(String(50), ForeignKey("scenario_definition.scenario_id"), nullable=False)
    portfolio_name = Column(String(100), nullable=False)
    effective_date = Column(Date, nullable=False)
    expiry_date = Column(Date)
    rebalance_freq = Column(String(20), default='NONE')
    engine_version = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)

    # 관계
    scenario = relationship("ScenarioDefinition", back_populates="portfolios")
    allocations = relationship("PortfolioAllocation", back_populates="portfolio")

    __table_args__ = (
        Index('idx_portfolio_model_scenario', 'scenario_id'),
        Index('idx_portfolio_model_effective', 'effective_date'),
    )

    def __repr__(self):
        return f"<PortfolioModel {self.portfolio_id} scenario={self.scenario_id}>"

    def get_allocation_dict(self) -> dict:
        """자산클래스별 구성비 dict 반환"""
        result = {}
        for alloc in self.allocations:
            asset_class = alloc.asset_class or "OTHER"
            result[asset_class.lower()] = float(alloc.weight) * 100  # % 단위
        return result


class PortfolioAllocation(Base):
    """
    포트폴리오 구성비 (portfolio_allocation)

    포트폴리오 내 자산별 비중
    """
    __tablename__ = "portfolio_allocation"

    allocation_id = Column(BigInteger, primary_key=True, autoincrement=True)
    portfolio_id = Column(BigInteger, ForeignKey("portfolio_model.portfolio_id"), nullable=False)
    instrument_id = Column(BigInteger, nullable=False)  # instrument_master 참조
    weight = Column(Numeric(5, 4), nullable=False)  # 0.0000 ~ 1.0000
    asset_class = Column(String(50))  # 'EQUITY', 'BOND', 'CASH', 'COMMODITY', 'OTHER'
    created_at = Column(DateTime, default=datetime.utcnow)

    # 관계
    portfolio = relationship("PortfolioModel", back_populates="allocations")

    __table_args__ = (
        Index('idx_portfolio_allocation_portfolio', 'portfolio_id'),
    )

    def __repr__(self):
        return f"<PortfolioAllocation portfolio={self.portfolio_id} weight={self.weight}>"
