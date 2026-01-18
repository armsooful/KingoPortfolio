"""
사용자 노출용 성과 분석 API (LIVE 전용)
"""

from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.performance import PerformanceResult, PerformanceBasis, PerformancePublicView
from app.models.user import User


PERFORMANCE_DISCLAIMER = (
    "본 분석은 과거 데이터에 기반한 정보 제공 목적으로만 작성되었습니다. "
    "과거 성과는 미래 수익을 보장하지 않으며, 투자 권유나 추천이 아닙니다. "
    "모든 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다. "
    "본 서비스는 투자자문업에 해당하지 않습니다."
)


router = APIRouter(prefix="/api/performance", tags=["Performance"])


def _basis_summary(basis: Optional[PerformanceBasis]) -> Optional[Dict[str, Any]]:
    if not basis:
        return None
    return {
        "price_basis": basis.price_basis,
        "include_fee": basis.include_fee,
        "include_tax": basis.include_tax,
        "include_dividend": basis.include_dividend,
        "fx_snapshot_id": basis.fx_snapshot_id,
        "notes": basis.notes,
    }


@router.get("/public")
def list_public_performance_results(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    period_type: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """성과 결과 조회 (사용자 노출용, LIVE 전용)"""
    query = db.query(PerformanceResult).filter(PerformanceResult.performance_type == "LIVE")
    if entity_type:
        query = query.filter(PerformanceResult.entity_type == entity_type)
    if entity_id:
        query = query.filter(PerformanceResult.entity_id == entity_id)
    if period_type:
        query = query.filter(PerformanceResult.period_type == period_type)

    results = query.order_by(PerformanceResult.created_at.desc()).limit(limit).all()
    performance_ids = [r.performance_id for r in results]

    basis_map: Dict[str, PerformanceBasis] = {}
    public_map: Dict[str, PerformancePublicView] = {}
    if performance_ids:
        for basis in db.query(PerformanceBasis).filter(
            PerformanceBasis.performance_id.in_(performance_ids)
        ).all():
            basis_map[basis.performance_id] = basis

        for view in db.query(PerformancePublicView).filter(
            PerformancePublicView.performance_id.in_(performance_ids)
        ).all():
            public_map[view.performance_id] = view

    data: List[Dict[str, Any]] = []
    for result in results:
        public_view = public_map.get(result.performance_id)
        disclaimer = public_view.disclaimer_text if public_view else PERFORMANCE_DISCLAIMER
        headline = public_view.headline_json if public_view else {}

        data.append({
            "performance_id": result.performance_id,
            "performance_type": result.performance_type,
            "entity_type": result.entity_type,
            "entity_id": result.entity_id,
            "period_type": result.period_type,
            "period_start": result.period_start,
            "period_end": result.period_end,
            "metrics": {
                "period_return": result.period_return,
                "cumulative_return": result.cumulative_return,
                "annualized_return": result.annualized_return,
                "volatility": result.volatility,
                "mdd": result.mdd,
                "sharpe_ratio": result.sharpe_ratio,
                "sortino_ratio": result.sortino_ratio,
            },
            "basis_summary": _basis_summary(basis_map.get(result.performance_id)),
            "headline": headline,
            "disclaimer": disclaimer,
            "created_at": result.created_at,
        })

    return {
        "success": True,
        "data": data,
    }
