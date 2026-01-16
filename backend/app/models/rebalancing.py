"""
Phase 2 리밸런싱 모델

리밸런싱 규칙 및 이벤트 관리를 위한 ORM 모델

DDL 기준: Foresto_Phase2_EpicB_Rebalancing_DDL.sql
"""

from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, DateTime, Date,
    ForeignKey, Numeric, Text, Index, Boolean, CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, date
from typing import Dict, Optional, List

from app.database import Base


class RebalancingRule(Base):
    """
    리밸런싱 규칙 정의

    PERIODIC: 정기 리밸런싱 (월간/분기)
    DRIFT: 편차 기반 리밸런싱
    """
    __tablename__ = "rebalancing_rule"

    rule_id = Column(Integer, primary_key=True, autoincrement=True)
    rule_name = Column(String(64), nullable=False)

    # 리밸런싱 타입 (PERIODIC / DRIFT)
    rule_type = Column(String(16), nullable=False)

    # PERIODIC 설정
    frequency = Column(String(16), nullable=True)  # MONTHLY, QUARTERLY
    base_day_policy = Column(String(24), nullable=False, default='FIRST_TRADING_DAY')
    # FIRST_TRADING_DAY / LAST_TRADING_DAY

    # DRIFT 설정
    drift_threshold = Column(Numeric(8, 6), nullable=True)  # 예: 0.05 = 5%

    # 비용 모델 설정
    cost_rate = Column(Numeric(8, 6), nullable=False, default=0.001)  # 기본 10bp

    # 유효 기간
    effective_from = Column(Date, nullable=False, default=date.today)
    effective_to = Column(Date, nullable=True)  # NULL = 현재 유효

    # 메타데이터
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계
    events = relationship("RebalancingEvent", back_populates="rule")

    __table_args__ = (
        CheckConstraint("rule_type IN ('PERIODIC', 'DRIFT')", name='chk_rule_type'),
        CheckConstraint("frequency IN ('MONTHLY', 'QUARTERLY')", name='chk_frequency'),
        CheckConstraint("base_day_policy IN ('FIRST_TRADING_DAY', 'LAST_TRADING_DAY')", name='chk_base_day_policy'),
        CheckConstraint("drift_threshold > 0 AND drift_threshold < 1", name='chk_drift_threshold'),
        CheckConstraint("cost_rate >= 0 AND cost_rate <= 0.02", name='chk_cost_rate'),
        Index('idx_rebalancing_rule_active', 'is_active'),
    )

    def __repr__(self):
        return f"<RebalancingRule {self.rule_id} {self.rule_name} ({self.rule_type})>"

    def is_periodic(self) -> bool:
        """정기 리밸런싱 여부"""
        return self.rule_type == 'PERIODIC'

    def is_drift_based(self) -> bool:
        """Drift 기반 리밸런싱 여부"""
        return self.rule_type == 'DRIFT'

    def get_drift_threshold_float(self) -> Optional[float]:
        """Drift 임계치를 float로 반환"""
        if self.drift_threshold is None:
            return None
        return float(self.drift_threshold)

    def get_cost_rate_float(self) -> float:
        """비용률을 float로 반환"""
        return float(self.cost_rate) if self.cost_rate else 0.001

    def to_dict(self) -> dict:
        """규칙을 dict로 변환"""
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "rule_type": self.rule_type,
            "frequency": self.frequency,
            "base_day_policy": self.base_day_policy,
            "drift_threshold": self.get_drift_threshold_float(),
            "cost_rate": self.get_cost_rate_float(),
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "is_active": self.is_active,
        }

    def to_engine_config(self) -> dict:
        """RebalancingConfig용 dict 변환"""
        # base_day_policy를 periodic_timing으로 변환
        timing = "START" if self.base_day_policy == "FIRST_TRADING_DAY" else "END"
        return {
            "rebalance_type": self.rule_type,
            "frequency": self.frequency,
            "periodic_timing": timing,
            "drift_threshold": self.get_drift_threshold_float(),
            "cost_rate": self.get_cost_rate_float(),
            "rule_id": self.rule_id,
        }


class RebalancingEvent(Base):
    """
    리밸런싱 발생 이벤트 로그

    시뮬레이션 중 발생한 모든 리밸런싱 이벤트를 기록

    DDL 기준: Foresto_Phase2_EpicB_Rebalancing_DDL.sql
    """
    __tablename__ = "rebalancing_event"

    event_id = Column(BigInteger, primary_key=True, autoincrement=True)
    simulation_run_id = Column(
        BigInteger,
        ForeignKey("simulation_run.run_id", ondelete="CASCADE"),
        nullable=False
    )
    rule_id = Column(Integer, ForeignKey("rebalancing_rule.rule_id"), nullable=False)

    # 이벤트 정보
    event_date = Column(Date, nullable=False)

    # 트리거 정보
    trigger_type = Column(String(16), nullable=False)  # PERIODIC, DRIFT
    trigger_detail = Column(String(64), nullable=True)  # 예: MONTHLY, DRIFT>=0.05

    # 비중 정보 (JSONB)
    before_weights = Column(JSONB, nullable=False)
    after_weights = Column(JSONB, nullable=False)

    # 거래 정보
    turnover = Column(Numeric(12, 8), nullable=False)  # 회전율
    cost_rate = Column(Numeric(8, 6), nullable=False)
    cost_amount = Column(Numeric(18, 8), nullable=True)

    # 메타데이터
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # 관계
    rule = relationship("RebalancingRule", back_populates="events")

    __table_args__ = (
        CheckConstraint("trigger_type IN ('PERIODIC', 'DRIFT')", name='chk_event_trigger_type'),
        CheckConstraint("turnover >= 0", name='chk_event_turnover'),
        Index('idx_rebal_event_run_date', 'simulation_run_id', 'event_date'),
        Index('idx_rebal_event_rule', 'rule_id'),
    )

    def __repr__(self):
        return f"<RebalancingEvent {self.event_id} run={self.simulation_run_id} date={self.event_date} {self.trigger_type}>"

    def get_turnover_float(self) -> float:
        """회전율을 float로 반환"""
        return float(self.turnover) if self.turnover else 0.0

    def to_dict(self) -> dict:
        """이벤트를 dict로 변환"""
        return {
            "event_id": self.event_id,
            "simulation_run_id": self.simulation_run_id,
            "rule_id": self.rule_id,
            "event_date": self.event_date.isoformat() if self.event_date else None,
            "trigger_type": self.trigger_type,
            "trigger_detail": self.trigger_detail,
            "before_weights": self.before_weights,
            "after_weights": self.after_weights,
            "turnover": self.get_turnover_float(),
            "cost_rate": float(self.cost_rate) if self.cost_rate else None,
            "cost_amount": float(self.cost_amount) if self.cost_amount else None,
        }

    @classmethod
    def create_event(
        cls,
        simulation_run_id: int,
        rule_id: int,
        event_date: date,
        trigger_type: str,
        trigger_detail: str,
        before_weights: Dict[str, float],
        after_weights: Dict[str, float],
        turnover: float,
        cost_rate: float,
        cost_amount: Optional[float] = None,
    ) -> "RebalancingEvent":
        """이벤트 생성 팩토리 메서드"""
        return cls(
            simulation_run_id=simulation_run_id,
            rule_id=rule_id,
            event_date=event_date,
            trigger_type=trigger_type,
            trigger_detail=trigger_detail,
            before_weights=before_weights,
            after_weights=after_weights,
            turnover=turnover,
            cost_rate=cost_rate,
            cost_amount=cost_amount,
        )


class RebalancingCostModel(Base):
    """
    리밸런싱 비용 모델 정의 (확장 대비용)

    DDL 기준: Foresto_Phase2_EpicB_Rebalancing_DDL.sql
    """
    __tablename__ = "rebalancing_cost_model"

    model_id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(64), nullable=False)
    model_type = Column(String(32), nullable=False, default='FIXED_RATE')
    description = Column(Text, nullable=True)
    param_json = Column(JSONB, default={})
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<RebalancingCostModel {self.model_id} {self.model_name}>"

    def to_dict(self) -> dict:
        """모델을 dict로 변환"""
        return {
            "model_id": self.model_id,
            "model_name": self.model_name,
            "model_type": self.model_type,
            "description": self.description,
            "param_json": self.param_json,
        }
