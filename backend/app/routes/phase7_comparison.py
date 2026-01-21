import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.phase7_evaluation import Phase7EvaluationRun
from app.models.phase7_portfolio import Phase7Portfolio
from app.schemas import (
    Phase7ComparisonItem,
    Phase7ComparisonRequest,
    Phase7ComparisonResponse,
)


router = APIRouter(prefix="/api/v1/phase7/comparisons", tags=["Phase7 Comparisons"])


@router.post("", response_model=Phase7ComparisonResponse)
def compare_phase7_portfolios(
    payload: Phase7ComparisonRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    portfolio_ids = list(dict.fromkeys(payload.portfolio_ids))
    if len(portfolio_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비교 대상은 최소 2개가 필요합니다.",
        )

    portfolios = (
        db.query(Phase7Portfolio)
        .filter(
            Phase7Portfolio.owner_user_id == current_user.id,
            Phase7Portfolio.portfolio_id.in_(portfolio_ids),
        )
        .all()
    )
    if len(portfolios) != len(portfolio_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="포트폴리오를 찾을 수 없습니다.",
        )

    latest_runs = {}
    for portfolio_id in portfolio_ids:
        run = (
            db.query(Phase7EvaluationRun)
            .filter(
                Phase7EvaluationRun.owner_user_id == current_user.id,
                Phase7EvaluationRun.portfolio_id == portfolio_id,
            )
            .order_by(Phase7EvaluationRun.created_at.desc())
            .first()
        )
        if not run:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="평가 이력을 찾을 수 없습니다.",
            )
        latest_runs[portfolio_id] = run

    items = []
    for portfolio_id in portfolio_ids:
        run = latest_runs[portfolio_id]
        result = json.loads(run.result_json)
        items.append(
            Phase7ComparisonItem(
                portfolio_id=portfolio_id,
                period=result["period"],
                metrics=result["metrics"],
                disclaimer_version=result["disclaimer_version"],
            )
        )

    return Phase7ComparisonResponse(
        count=len(items),
        portfolios=items,
    )
