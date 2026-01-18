"""
내부 성과 분석 API (LIVE/SIM/BACK)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.auth import require_admin
from app.models.user import User
from app.models.performance import PerformanceResult


router = APIRouter(prefix="/internal/performance", tags=["Performance Internal"])


@router.get("/results")
def list_performance_results(
    performance_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """성과 결과 조회 (내부)"""
    query = db.query(PerformanceResult)
    if performance_type:
        query = query.filter(PerformanceResult.performance_type == performance_type)
    if entity_type:
        query = query.filter(PerformanceResult.entity_type == entity_type)
    if entity_id:
        query = query.filter(PerformanceResult.entity_id == entity_id)
    results = query.order_by(PerformanceResult.created_at.desc()).limit(200).all()
    return {
        "success": True,
        "data": [
            {
                "performance_id": r.performance_id,
                "performance_type": r.performance_type,
                "entity_type": r.entity_type,
                "entity_id": r.entity_id,
                "period_type": r.period_type,
                "period_start": r.period_start,
                "period_end": r.period_end,
                "period_return": r.period_return,
                "cumulative_return": r.cumulative_return,
                "annualized_return": r.annualized_return,
                "volatility": r.volatility,
                "mdd": r.mdd,
                "sharpe_ratio": r.sharpe_ratio,
                "sortino_ratio": r.sortino_ratio,
                "execution_id": r.execution_id,
                "snapshot_ids": r.snapshot_ids,
                "result_version_id": r.result_version_id,
                "calc_params": r.calc_params,
                "created_at": r.created_at,
            }
            for r in results
        ],
    }
