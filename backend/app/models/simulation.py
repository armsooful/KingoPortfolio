"""
Phase 1 시뮬레이션 결과 모델

sim_run/sim_path/sim_summary 구조로 시뮬레이션 결과를 표준화하여 저장
"""

from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, DateTime, Date,
    ForeignKey, Numeric, Text, Index, JSON
)
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class SimulationRun(Base):
    """
    시뮬레이션 실행 기록 (sim_run)

    request_hash 기반 캐싱 및 재사용의 핵심 테이블
    """
    __tablename__ = "simulation_run"

    run_id = Column(BigInteger, primary_key=True, autoincrement=True)
    request_hash = Column(String(64), unique=True, nullable=False, index=True)
    scenario_id = Column(String(50), nullable=True)  # scenario_definition 참조
    portfolio_id = Column(BigInteger, nullable=True)  # portfolio_model 참조
    user_id = Column(BigInteger, nullable=True)  # users 테이블 참조

    # 입력 파라미터
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    initial_amount = Column(Numeric(18, 2), nullable=False)
    rebalance_freq = Column(String(20), default='NONE')
    max_loss_limit_pct = Column(Numeric(5, 2), nullable=True)
    request_params = Column(JSON, nullable=True)  # 전체 요청 파라미터 백업

    # 메타데이터
    engine_version = Column(String(20), nullable=False)
    run_status = Column(String(20), default='COMPLETED')  # RUNNING, COMPLETED, FAILED
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # TTL

    # 관계
    summary = relationship("SimulationSummary", back_populates="run", uselist=False, cascade="all, delete-orphan")
    paths = relationship("SimulationPath", back_populates="run", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_simulation_run_scenario', 'scenario_id'),
        Index('idx_simulation_run_user', 'user_id'),
        Index('idx_simulation_run_expires', 'expires_at'),
    )

    def __repr__(self):
        return f"<SimulationRun {self.run_id} hash={self.request_hash[:8]}...>"


class SimulationPath(Base):
    """
    시뮬레이션 일별 경로 (sim_path)

    NAV, 낙폭, 누적수익률 등 일별 시계열 데이터
    """
    __tablename__ = "simulation_path"

    path_id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(BigInteger, ForeignKey("simulation_run.run_id", ondelete="CASCADE"), nullable=False)
    path_date = Column(Date, nullable=False)
    nav = Column(Numeric(18, 4), nullable=False)  # 순자산가치
    daily_return = Column(Numeric(12, 8), nullable=True)  # 일간 수익률
    cumulative_return = Column(Numeric(12, 8), nullable=True)  # 누적 수익률
    drawdown = Column(Numeric(12, 8), nullable=True)  # 낙폭 (음수)
    high_water_mark = Column(Numeric(18, 4), nullable=True)  # 고점

    created_at = Column(DateTime, default=datetime.utcnow)

    # 관계
    run = relationship("SimulationRun", back_populates="paths")

    __table_args__ = (
        Index('idx_simulation_path_run_date', 'run_id', 'path_date'),
    )

    def __repr__(self):
        return f"<SimulationPath run={self.run_id} date={self.path_date}>"


class SimulationSummary(Base):
    """
    시뮬레이션 요약 지표 (sim_summary)

    손실/회복 지표(최상위) + 과거 수익률(참고용) 구조
    """
    __tablename__ = "simulation_summary"

    summary_id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(BigInteger, ForeignKey("simulation_run.run_id", ondelete="CASCADE"), unique=True, nullable=False)

    # 손실/회복 지표 (최상위) - Foresto 핵심 KPI
    max_drawdown = Column(Numeric(8, 4), nullable=False)  # MDD (%)
    max_recovery_days = Column(Integer, nullable=True)  # 최대 회복 기간 (일)
    worst_1m_return = Column(Numeric(8, 4), nullable=True)  # 최악의 1개월 수익률 (%)
    worst_3m_return = Column(Numeric(8, 4), nullable=True)  # 최악의 3개월 수익률 (%)
    volatility = Column(Numeric(8, 4), nullable=True)  # 연간 변동성 (%)

    # 과거 수익률 (참고용)
    total_return = Column(Numeric(10, 4), nullable=False)  # 총 수익률 (%)
    cagr = Column(Numeric(8, 4), nullable=True)  # 연평균 복합 성장률 (%)
    sharpe_ratio = Column(Numeric(8, 4), nullable=True)  # 샤프 비율
    sortino_ratio = Column(Numeric(8, 4), nullable=True)  # 소르티노 비율

    # 기타 통계
    final_value = Column(Numeric(18, 2), nullable=True)  # 최종 자산가치
    trading_days = Column(Integer, nullable=True)  # 거래일 수
    rebalance_count = Column(Integer, default=0)  # 리밸런싱 횟수

    created_at = Column(DateTime, default=datetime.utcnow)

    # 관계
    run = relationship("SimulationRun", back_populates="summary")

    __table_args__ = (
        Index('idx_simulation_summary_run', 'run_id'),
    )

    def __repr__(self):
        return f"<SimulationSummary run={self.run_id} mdd={self.max_drawdown}%>"

    def to_risk_metrics(self) -> dict:
        """손실/회복 지표를 dict로 반환"""
        return {
            "max_drawdown": float(self.max_drawdown) if self.max_drawdown else None,
            "max_recovery_days": self.max_recovery_days,
            "worst_1m_return": float(self.worst_1m_return) if self.worst_1m_return else None,
            "worst_3m_return": float(self.worst_3m_return) if self.worst_3m_return else None,
            "volatility": float(self.volatility) if self.volatility else None,
        }

    def to_historical_observation(self) -> dict:
        """과거 수익률 지표를 dict로 반환"""
        return {
            "total_return": float(self.total_return) if self.total_return else None,
            "cagr": float(self.cagr) if self.cagr else None,
            "sharpe_ratio": float(self.sharpe_ratio) if self.sharpe_ratio else None,
        }
