"""
Phase 7: 평가 실행 이력 저장 모델

포트폴리오 평가 요청과 결과(Output Schema v2)를 저장한다.
"""

from datetime import datetime, date
from sqlalchemy import Integer, Column, Date, DateTime, ForeignKey, String, Text, Index

from app.database import Base


class Phase7EvaluationRun(Base):
    __tablename__ = "phase7_evaluation_run"

    evaluation_id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(
        Integer,
        ForeignKey("phase7_portfolio.portfolio_id", ondelete="CASCADE"),
        nullable=False,
    )
    owner_user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    rebalance = Column(String(20), nullable=False)  # NONE | MONTHLY | QUARTERLY
    result_json = Column(Text, nullable=False)
    result_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_phase7_eval_owner", "owner_user_id"),
        Index("idx_phase7_eval_portfolio", "portfolio_id"),
        Index("idx_phase7_eval_period", "period_start", "period_end"),
    )

    def to_dict(self) -> dict:
        return {
            "evaluation_id": self.evaluation_id,
            "portfolio_id": self.portfolio_id,
            "period": {
                "start": self.period_start.isoformat() if self.period_start else None,
                "end": self.period_end.isoformat() if self.period_end else None,
            },
            "rebalance": self.rebalance,
            "result_hash": self.result_hash,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
