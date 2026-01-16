"""
Phase 2 Epic D: 성과 분석 결과 모델

시뮬레이션 실행에 대한 KPI 결과를 캐시하는 ORM 모델

DDL 기준: Foresto_Phase2_EpicD_Analysis_DDL.sql
"""

from sqlalchemy import (
    Column, Integer, BigInteger, Numeric, DateTime, Index, ForeignKey
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Dict, Optional

from app.database import Base


class AnalysisResult(Base):
    """
    성과 분석 결과 캐시

    시뮬레이션 실행(run_id) + 계산 파라미터(rf, annualization) 기준으로
    KPI 결과를 캐시합니다.

    **캐시 키**: (simulation_run_id, rf_annual, annualization_factor)
    **캐시 값**: metrics_json (CAGR, Volatility, Sharpe, MDD 등)

    ⚠️ 이 테이블은 성과 해석용이며, 투자 추천 정보를 포함하지 않습니다.
    """
    __tablename__ = "analysis_result"

    analysis_id = Column(BigInteger, primary_key=True, autoincrement=True)

    # FK to simulation_run (Phase 1 테이블)
    simulation_run_id = Column(
        BigInteger,
        ForeignKey("simulation_run.run_id", ondelete="CASCADE"),
        nullable=False
    )

    # 계산 가정 파라미터
    rf_annual = Column(Numeric(8, 6), nullable=False, default=0.0)
    annualization_factor = Column(Integer, nullable=False, default=252)

    # KPI 결과 JSON
    # 포함 키: cagr, volatility, sharpe, mdd, mdd_peak_date, mdd_trough_date,
    #         total_return, period_start, period_end, recovery_days
    metrics_json = Column(JSONB, nullable=False)

    # 메타데이터
    calculated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        # 동일 run + 동일 가정이면 결과 1건 (캐시 키)
        Index('ux_analysis_result_run_params', 'simulation_run_id', 'rf_annual', 'annualization_factor', unique=True),
        # 조회 최적화
        Index('idx_analysis_result_run', 'simulation_run_id'),
    )

    def __repr__(self):
        return f"<AnalysisResult {self.analysis_id} run={self.simulation_run_id}>"

    def to_dict(self) -> dict:
        """dict 변환 (API 응답용)"""
        return {
            "analysis_id": self.analysis_id,
            "simulation_run_id": self.simulation_run_id,
            "rf_annual": float(self.rf_annual) if self.rf_annual else 0.0,
            "annualization_factor": self.annualization_factor,
            "metrics": self.metrics_json,
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None,
        }

    def get_metric(self, key: str, default=None):
        """특정 KPI 값 조회"""
        if self.metrics_json and isinstance(self.metrics_json, dict):
            return self.metrics_json.get(key, default)
        return default

    @property
    def cagr(self) -> Optional[float]:
        """CAGR 값"""
        return self.get_metric("cagr")

    @property
    def volatility(self) -> Optional[float]:
        """변동성 값"""
        return self.get_metric("volatility")

    @property
    def sharpe(self) -> Optional[float]:
        """Sharpe Ratio 값"""
        return self.get_metric("sharpe")

    @property
    def mdd(self) -> Optional[float]:
        """MDD 값"""
        return self.get_metric("mdd")

    @property
    def total_return(self) -> Optional[float]:
        """총 수익률 값"""
        return self.get_metric("total_return")
