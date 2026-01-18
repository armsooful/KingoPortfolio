"""
Phase 3-C / Epic C-3: 성과 분석 모델
"""

from datetime import datetime
import uuid

from sqlalchemy import (
    Column, String, Date, DateTime, Boolean, Text, Numeric,
    ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


def _uuid_str() -> str:
    return str(uuid.uuid4())


class PerformanceResult(Base):
    """성과 분석 결과"""
    __tablename__ = "performance_result"

    performance_id = Column(String(36), primary_key=True, default=_uuid_str)
    performance_type = Column(String(10), nullable=False)  # LIVE/SIM/BACK
    entity_type = Column(String(20), nullable=False)  # PORTFOLIO/ACCOUNT/ASSET_CLASS
    entity_id = Column(String(100), nullable=False)
    period_type = Column(String(10), nullable=False)  # DAILY/MONTHLY/CUMULATIVE
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    period_return = Column(Numeric(12, 6))
    cumulative_return = Column(Numeric(12, 6))
    annualized_return = Column(Numeric(12, 6))
    volatility = Column(Numeric(12, 6))
    mdd = Column(Numeric(12, 6))
    sharpe_ratio = Column(Numeric(12, 6))
    sortino_ratio = Column(Numeric(12, 6))

    execution_id = Column(String(36), ForeignKey("batch_execution.execution_id"), nullable=True)
    snapshot_ids = Column(JSONB, nullable=False, default=list)
    result_version_id = Column(String(36), nullable=True)
    calc_params = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_performance_entity", "entity_type", "entity_id"),
        Index("idx_performance_type", "performance_type", "period_type"),
        Index("idx_performance_period", "period_start", "period_end"),
    )


class PerformanceBasis(Base):
    """성과 산출 근거"""
    __tablename__ = "performance_basis"

    basis_id = Column(String(36), primary_key=True, default=_uuid_str)
    performance_id = Column(String(36), ForeignKey("performance_result.performance_id", ondelete="CASCADE"), nullable=False)
    price_basis = Column(String(20), nullable=False)  # CLOSE/LAST_VALID
    include_fee = Column(Boolean, nullable=False, default=True)
    include_tax = Column(Boolean, nullable=False, default=False)
    include_dividend = Column(Boolean, nullable=False, default=False)
    fx_snapshot_id = Column(String(36), ForeignKey("data_snapshot.snapshot_id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_performance_basis_perf", "performance_id"),
    )


class BenchmarkResult(Base):
    """벤치마크 비교 결과"""
    __tablename__ = "benchmark_result"

    benchmark_id = Column(String(36), primary_key=True, default=_uuid_str)
    performance_id = Column(String(36), ForeignKey("performance_result.performance_id", ondelete="CASCADE"), nullable=False)
    benchmark_type = Column(String(20), nullable=False)  # INDEX/MIX/CASH
    benchmark_code = Column(String(50), nullable=False)
    benchmark_return = Column(Numeric(12, 6))
    excess_return = Column(Numeric(12, 6))
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_benchmark_perf", "performance_id"),
    )


class PerformancePublicView(Base):
    """사용자 노출용 성과 요약"""
    __tablename__ = "performance_public_view"

    public_id = Column(String(36), primary_key=True, default=_uuid_str)
    performance_id = Column(String(36), ForeignKey("performance_result.performance_id", ondelete="CASCADE"), nullable=False)
    headline_json = Column(JSONB, nullable=False, default=dict)
    disclaimer_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
