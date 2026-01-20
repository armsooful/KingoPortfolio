from datetime import date
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.phase7_evaluation import Phase7EvaluationRun
from app.models.phase7_portfolio import Phase7Portfolio
from app.schemas import (
    Phase7EvaluationDetailResponse,
    Phase7EvaluationHistoryItem,
    Phase7EvaluationHistoryResponse,
    Phase7EvaluationRequest,
    Phase7EvaluationResponse,
    Phase7Period,
)
from app.services.phase7_evaluation import (
    Phase7EvaluationError,
    evaluate_phase7_portfolio,
    serialize_result,
)


router = APIRouter(prefix="/api/v1/phase7/evaluations", tags=["Phase7 Evaluations"])


@router.post("", response_model=Phase7EvaluationResponse, status_code=status.HTTP_201_CREATED)
def create_phase7_evaluation(
    payload: Phase7EvaluationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _validate_period(payload.period.start, payload.period.end)

    portfolio = (
        db.query(Phase7Portfolio)
        .filter(
            Phase7Portfolio.portfolio_id == payload.portfolio_id,
            Phase7Portfolio.owner_user_id == current_user.id,
        )
        .first()
    )
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="포트폴리오를 찾을 수 없습니다.",
        )

    try:
        result = evaluate_phase7_portfolio(
            db=db,
            portfolio=portfolio,
            period_start=payload.period.start,
            period_end=payload.period.end,
            rebalance=payload.rebalance,
        )
    except Phase7EvaluationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc

    evaluation_run = Phase7EvaluationRun(
        portfolio_id=portfolio.portfolio_id,
        owner_user_id=current_user.id,
        period_start=payload.period.start,
        period_end=payload.period.end,
        rebalance=payload.rebalance,
        result_json=serialize_result(result),
    )
    db.add(evaluation_run)
    db.commit()

    return Phase7EvaluationResponse(**result)


@router.get("", response_model=Phase7EvaluationHistoryResponse)
def list_phase7_evaluations(
    portfolio_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Phase7EvaluationRun).filter(
        Phase7EvaluationRun.owner_user_id == current_user.id
    )
    if portfolio_id is not None:
        query = query.filter(Phase7EvaluationRun.portfolio_id == portfolio_id)

    evaluations = query.order_by(Phase7EvaluationRun.created_at.desc()).all()
    return Phase7EvaluationHistoryResponse(
        count=len(evaluations),
        evaluations=[
            Phase7EvaluationHistoryItem(**evaluation.to_dict())
            for evaluation in evaluations
        ],
    )


@router.get("/{evaluation_id}", response_model=Phase7EvaluationDetailResponse)
def get_phase7_evaluation(
    evaluation_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    evaluation = (
        db.query(Phase7EvaluationRun)
        .filter(
            Phase7EvaluationRun.evaluation_id == evaluation_id,
            Phase7EvaluationRun.owner_user_id == current_user.id,
        )
        .first()
    )
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="평가 이력을 찾을 수 없습니다.",
        )

    result = json.loads(evaluation.result_json)
    return Phase7EvaluationDetailResponse(
        evaluation_id=evaluation.evaluation_id,
        portfolio_id=evaluation.portfolio_id,
        period=Phase7Period(start=evaluation.period_start, end=evaluation.period_end),
        rebalance=evaluation.rebalance,
        created_at=evaluation.created_at.isoformat() if evaluation.created_at else None,
        result=Phase7EvaluationResponse(**result),
    )


def _validate_period(start: date, end: date) -> None:
    if start >= end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="분석 기간을 확인해 주세요.",
        )
    if end > date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="분석 기간을 확인해 주세요.",
        )
