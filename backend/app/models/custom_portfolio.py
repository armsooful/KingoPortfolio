"""
Phase 2 Epic C: 사용자 커스텀 포트폴리오 모델

사용자가 자산군 비중을 직접 정의하여 시뮬레이션할 수 있는
커스텀 포트폴리오 ORM 모델

DDL 기준: phase2_epicC_custom_portfolio_ddl.sql
"""

from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Numeric,
    DateTime, Boolean, ForeignKey, Index, CheckConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Dict, List, Optional

from app.database import Base


class AssetClassMaster(Base):
    """
    자산군 코드 마스터

    시스템에서 허용하는 자산군 코드 목록
    - EQUITY: 주식
    - BOND: 채권
    - CASH: 현금성
    - GOLD: 금
    - ALT: 대체투자
    """
    __tablename__ = "asset_class_master"

    asset_class_code = Column(String(20), primary_key=True)
    asset_class_name = Column(String(100), nullable=False)
    description = Column(Text)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<AssetClass {self.asset_class_code}>"

    def to_dict(self) -> dict:
        return {
            "asset_class_code": self.asset_class_code,
            "asset_class_name": self.asset_class_name,
            "description": self.description,
            "display_order": self.display_order,
            "is_active": self.is_active,
        }


class CustomPortfolio(Base):
    """
    사용자 커스텀 포트폴리오

    사용자가 자산군 비중을 직접 정의한 포트폴리오
    시나리오 템플릿을 기반으로 확장할 수 있음

    ⚠️ 본 테이블은 시뮬레이션 파라미터 저장용이며,
    투자 추천이나 자문을 위한 것이 아닙니다.
    """
    __tablename__ = "custom_portfolio"

    portfolio_id = Column(BigInteger, primary_key=True, autoincrement=True)

    # 소유자
    owner_user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True
    )
    owner_key = Column(String(100), nullable=True)

    # 포트폴리오 정보
    portfolio_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # 템플릿 기반 확장 (선택)
    base_template_id = Column(
        String(20),
        ForeignKey("scenario_definition.scenario_id", ondelete="SET NULL"),
        nullable=True
    )

    # 상태
    is_active = Column(Boolean, nullable=False, default=True)

    # 메타데이터
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계
    weights = relationship(
        "CustomPortfolioWeight",
        back_populates="portfolio",
        cascade="all, delete-orphan",
        lazy="joined"
    )

    __table_args__ = (
        # owner_user_id 또는 owner_key 중 하나는 필수
        CheckConstraint(
            "owner_user_id IS NOT NULL OR owner_key IS NOT NULL",
            name="chk_owner"
        ),
        Index("idx_custom_portfolio_owner_user", "owner_user_id"),
        Index("idx_custom_portfolio_owner_key", "owner_key"),
        Index("idx_custom_portfolio_active", "is_active"),
    )

    def __repr__(self):
        return f"<CustomPortfolio {self.portfolio_id} '{self.portfolio_name}'>"

    def to_dict(self, include_weights: bool = True) -> dict:
        """dict 변환 (API 응답용)"""
        result = {
            "portfolio_id": self.portfolio_id,
            "owner_user_id": self.owner_user_id,
            "portfolio_name": self.portfolio_name,
            "description": self.description,
            "base_template_id": self.base_template_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_weights:
            result["weights"] = self.get_weights_dict()

        return result

    def get_weights_dict(self) -> Dict[str, float]:
        """비중을 dict로 반환"""
        return {
            w.asset_class_code: float(w.target_weight)
            for w in self.weights
        }

    def get_weights_sorted(self) -> List[tuple]:
        """비중을 정렬된 리스트로 반환 (request_hash 용)"""
        weights = [(w.asset_class_code, float(w.target_weight)) for w in self.weights]
        return sorted(weights, key=lambda x: x[0])


class CustomPortfolioWeight(Base):
    """
    커스텀 포트폴리오 자산군별 비중

    포트폴리오의 자산군별 목표 비중을 정규화하여 저장
    합계 = 1.0 검증은 애플리케이션 레벨에서 수행
    """
    __tablename__ = "custom_portfolio_weight"

    portfolio_id = Column(
        BigInteger,
        ForeignKey("custom_portfolio.portfolio_id", ondelete="CASCADE"),
        primary_key=True
    )
    asset_class_code = Column(String(20), primary_key=True)
    target_weight = Column(Numeric(6, 4), nullable=False)

    # 관계
    portfolio = relationship("CustomPortfolio", back_populates="weights")

    __table_args__ = (
        # 비중 범위 제약 (0~1)
        CheckConstraint(
            "target_weight >= 0 AND target_weight <= 1",
            name="chk_weight_range"
        ),
        Index("idx_custom_portfolio_weight_portfolio", "portfolio_id"),
    )

    def __repr__(self):
        return f"<Weight {self.asset_class_code}={self.target_weight}>"

    def to_dict(self) -> dict:
        return {
            "asset_class_code": self.asset_class_code,
            "target_weight": float(self.target_weight),
        }
