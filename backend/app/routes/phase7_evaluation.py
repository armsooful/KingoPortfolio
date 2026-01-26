from datetime import date
import json
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.phase7_evaluation import Phase7EvaluationRun
from app.models.phase7_portfolio import Phase7Portfolio
from app.models.securities import KrxTimeSeries, Stock
from app.schemas import (
    Phase7AvailablePeriodResponse,
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
    hash_result,
    serialize_result,
)
from app.services.audit_log_service import AuditLogService, TargetType
from app.utils.structured_logging import (
    get_structured_logger,
    request_context,
    set_user_id,
)

logger = get_structured_logger(__name__)


router = APIRouter(prefix="/api/v1/phase7/evaluations", tags=["Phase7 Evaluations"])


@router.get("/available-period", response_model=Phase7AvailablePeriodResponse)
def get_available_period(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    portfolio = (
        db.query(Phase7Portfolio)
        .filter(
            Phase7Portfolio.portfolio_id == portfolio_id,
            Phase7Portfolio.owner_user_id == current_user.id,
        )
        .first()
    )
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="포트폴리오를 찾을 수 없습니다.",
        )

    items = portfolio.items or []
    if not items:
        return Phase7AvailablePeriodResponse(
            start=None,
            end=None,
            has_overlap=False,
            item_count=0,
            ticker_count=0,
        )

    if portfolio.portfolio_type == "SECTOR":
        sectors = [item.item_key for item in items]
        tickers = [
            row[0]
            for row in db.query(Stock.ticker)
            .filter(
                Stock.sector.in_(sectors),
                Stock.is_active == True,
            )
            .all()
        ]
    else:
        tickers = [item.item_key for item in items]

    if not tickers:
        return Phase7AvailablePeriodResponse(
            start=None,
            end=None,
            has_overlap=False,
            item_count=len(items),
            ticker_count=0,
        )

    ranges = (
        db.query(
            KrxTimeSeries.ticker,
            func.min(KrxTimeSeries.date).label("min_date"),
            func.max(KrxTimeSeries.date).label("max_date"),
        )
        .filter(KrxTimeSeries.ticker.in_(tickers))
        .group_by(KrxTimeSeries.ticker)
        .all()
    )

    if not ranges:
        return Phase7AvailablePeriodResponse(
            start=None,
            end=None,
            has_overlap=False,
            item_count=len(items),
            ticker_count=0,
        )

    min_dates = [row.min_date for row in ranges if row.min_date]
    max_dates = [row.max_date for row in ranges if row.max_date]

    if not min_dates or not max_dates:
        return Phase7AvailablePeriodResponse(
            start=None,
            end=None,
            has_overlap=False,
            item_count=len(items),
            ticker_count=len(ranges),
        )

    start = max(min_dates)
    end = min(max_dates)
    has_overlap = start <= end

    return Phase7AvailablePeriodResponse(
        start=start if has_overlap else None,
        end=end if has_overlap else None,
        has_overlap=has_overlap,
        item_count=len(items),
        ticker_count=len(ranges),
    )


@router.post("", response_model=Phase7EvaluationResponse, status_code=status.HTTP_201_CREATED)
def create_phase7_evaluation(
    payload: Phase7EvaluationRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    start_time = time.perf_counter()

    with request_context() as req_id:
        set_user_id(str(current_user.id))

        logger.info("평가 요청 시작", {
            "portfolio_id": payload.portfolio_id,
            "period_start": str(payload.period.start),
            "period_end": str(payload.period.end),
        })

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
            logger.warning("포트폴리오 없음", {"portfolio_id": payload.portfolio_id})
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
                input_extensions=payload.extensions.dict() if payload.extensions else None,
            )
        except Phase7EvaluationError as exc:
            # 에러 감사 로그
            audit_service = AuditLogService(db)
            audit_service.log_error(
                error_type="Phase7EvaluationError",
                error_message=exc.message,
                target_type=TargetType.EVALUATION.value,
                target_id=str(payload.portfolio_id),
                user_id=str(current_user.id),
                request_id=req_id,
                error_context={
                    "period_start": str(payload.period.start),
                    "period_end": str(payload.period.end),
                },
            )
            logger.error("평가 실패", {
                "portfolio_id": payload.portfolio_id,
                "error": exc.message,
            })
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=exc.message,
            ) from exc

        serialized_result = serialize_result(result)
        evaluation_run = Phase7EvaluationRun(
            portfolio_id=portfolio.portfolio_id,
            owner_user_id=current_user.id,
            period_start=payload.period.start,
            period_end=payload.period.end,
            rebalance=payload.rebalance,
            result_json=serialized_result,
            result_hash=hash_result(serialized_result),
        )
        db.add(evaluation_run)
        db.commit()
        db.refresh(evaluation_run)

        # 평가 실행 감사 로그
        audit_service = AuditLogService(db)
        audit_service.log_evaluation(
            evaluation_id=str(evaluation_run.evaluation_id),
            portfolio_id=str(portfolio.portfolio_id),
            user_id=str(current_user.id),
            period_start=str(payload.period.start),
            period_end=str(payload.period.end),
            request_id=req_id,
            result_summary={
                "result_hash": evaluation_run.result_hash,
                "rebalance": payload.rebalance,
            },
        )

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.log_performance("create_evaluation", duration_ms, {
            "portfolio_id": payload.portfolio_id,
            "evaluation_id": evaluation_run.evaluation_id,
        })

        return Phase7EvaluationResponse(**result)


@router.get("", response_model=Phase7EvaluationHistoryResponse)
def list_phase7_evaluations(
    portfolio_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    with request_context() as req_id:
        set_user_id(str(current_user.id))

        logger.debug("평가 이력 조회", {
            "portfolio_id": portfolio_id,
            "limit": limit,
            "offset": offset,
        })

        query = db.query(Phase7EvaluationRun).filter(
            Phase7EvaluationRun.owner_user_id == current_user.id
        )
        if portfolio_id is not None:
            query = query.filter(Phase7EvaluationRun.portfolio_id == portfolio_id)

        evaluations = (
            query.order_by(Phase7EvaluationRun.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        logger.debug("평가 이력 조회 완료", {"count": len(evaluations)})

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
    with request_context() as req_id:
        set_user_id(str(current_user.id))

        logger.debug("평가 상세 조회", {"evaluation_id": evaluation_id})

        evaluation = (
            db.query(Phase7EvaluationRun)
            .filter(
                Phase7EvaluationRun.evaluation_id == evaluation_id,
                Phase7EvaluationRun.owner_user_id == current_user.id,
            )
            .first()
        )
        if not evaluation:
            logger.warning("평가 이력 없음", {"evaluation_id": evaluation_id})
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="평가 이력을 찾을 수 없습니다.",
            )

        result = json.loads(evaluation.result_json)

        logger.debug("평가 상세 조회 완료", {
            "evaluation_id": evaluation_id,
            "portfolio_id": evaluation.portfolio_id,
        })

        return Phase7EvaluationDetailResponse(
            evaluation_id=evaluation.evaluation_id,
            portfolio_id=evaluation.portfolio_id,
            period=Phase7Period(start=evaluation.period_start, end=evaluation.period_end),
            rebalance=evaluation.rebalance,
            created_at=evaluation.created_at.isoformat() if evaluation.created_at else None,
            result_hash=evaluation.result_hash,
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
