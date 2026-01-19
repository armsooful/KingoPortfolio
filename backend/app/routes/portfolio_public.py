"""
Phase 3-C / Epic U-1: 사용자 Read-only 포트폴리오 조회 API
"""

from datetime import date
import logging
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.auth import get_current_user
from app.database import get_db
from app.models.custom_portfolio import CustomPortfolio
from app.models.performance import PerformanceResult, BenchmarkResult, PerformanceBasis
from app.models.ops import ResultVersion
from app.models.user import User


router = APIRouter(prefix="/api/v1/portfolios", tags=["Portfolio Public"])
_CACHE_CONTROL = "public, max-age=300"
logger = logging.getLogger(__name__)


def _latest_live_performance(
    db: Session,
    portfolio_id: int,
    active_version_id: Optional[str] = None,
) -> Optional[PerformanceResult]:
    entity_id = _performance_entity_id(portfolio_id)
    query = db.query(PerformanceResult).filter(
        PerformanceResult.performance_type == "LIVE",
        PerformanceResult.entity_type == "PORTFOLIO",
        PerformanceResult.entity_id == entity_id,
    )
    if active_version_id:
        result = (
            query.filter(PerformanceResult.result_version_id == active_version_id)
            .order_by(PerformanceResult.created_at.desc())
            .first()
        )
        if result:
            return result
    return query.order_by(PerformanceResult.created_at.desc()).first()


def _performance_entity_id(portfolio_id: int) -> str:
    return f"custom_{portfolio_id}"


def _apply_cache_headers(response: Response) -> None:
    response.headers["Cache-Control"] = _CACHE_CONTROL


def _get_active_result_version_id(
    db: Session,
    portfolio_id: int,
) -> Optional[str]:
    entity_id = _performance_entity_id(portfolio_id)
    version = (
        db.query(ResultVersion)
        .filter(
            ResultVersion.result_type == "PERFORMANCE",
            ResultVersion.result_id == entity_id,
            ResultVersion.is_active == True,
        )
        .first()
    )
    return str(version.version_id) if version else None


def _raise_user_friendly_error(exc: Exception) -> None:
    logger.exception("U-1 portfolio public error", exc_info=exc)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
    )


def _get_user_portfolio(
    db: Session,
    portfolio_id: int,
    user_id: str,
) -> Optional[CustomPortfolio]:
    owner_user_id = None
    try:
        owner_user_id = int(user_id)
    except (TypeError, ValueError):
        owner_user_id = None

    conditions = [CustomPortfolio.owner_key == user_id]
    if owner_user_id is not None:
        conditions.append(CustomPortfolio.owner_user_id == owner_user_id)

    return (
        db.query(CustomPortfolio)
        .filter(
            CustomPortfolio.portfolio_id == portfolio_id,
            CustomPortfolio.is_active == True,
            or_(*conditions),
        )
        .first()
    )


def _normalize_limit(limit: Optional[int]) -> int:
    if limit is None:
        return 60
    if limit < 1 or limit > 120:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit 값이 올바르지 않습니다.",
        )
    return limit


def _build_status_flags(as_of_date: date, has_data: bool) -> Dict[str, Optional[object]]:
    is_reference = not has_data
    is_stale = as_of_date != date.today()
    warning_message = "표시된 기준일이 최신일과 다를 수 있습니다." if is_stale else None
    status_message = (
        "현재 최신 데이터가 준비되지 않았습니다. 잠시 후 다시 확인해주세요."
        if is_reference
        else None
    )
    return {
        "is_reference": is_reference,
        "is_stale": is_stale,
        "warning_message": warning_message,
        "status_message": status_message,
    }


@router.get("/{portfolio_id}/summary")
def get_portfolio_summary(
    portfolio_id: int,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """사용자 포트폴리오 현황 조회 (Read-only)"""
    _apply_cache_headers(response)
    try:
        portfolio = _get_user_portfolio(db, portfolio_id, current_user.id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="포트폴리오를 찾을 수 없습니다.",
            )

        active_version_id = _get_active_result_version_id(db, portfolio_id)
        performance = _latest_live_performance(db, portfolio_id, active_version_id)
        as_of_date = performance.period_end if performance else date.today()
        data_source = "LIVE_PERFORMANCE" if performance else "REFERENCE"
        is_reference = performance is None
        is_stale = as_of_date != date.today()
        warning_message = "표시된 기준일이 최신일과 다를 수 있습니다." if is_stale else None
        status_message = (
            "현재 최신 데이터가 준비되지 않았습니다. 잠시 후 다시 확인해주세요."
            if is_reference
            else None
        )
        is_version_active = (
            performance is not None
            and active_version_id is not None
            and performance.result_version_id == active_version_id
        )

        assets = [
            {
                "asset_class": weight.asset_class_code,
                "weight": float(weight.target_weight),
            }
            for weight in portfolio.weights
        ]

        return {
            "success": True,
            "data": {
                "portfolio_id": portfolio.portfolio_id,
                "portfolio_name": portfolio.portfolio_name,
                "as_of_date": as_of_date,
                "data_source": data_source,
                "data_source_summary": data_source,
                "is_reference": is_reference,
                "is_stale": is_stale,
                "is_version_active": is_version_active,
                "warning_message": warning_message,
                "status_message": status_message,
                "assets": assets,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        _raise_user_friendly_error(exc)


@router.get("/{portfolio_id}/performance")
def get_portfolio_performance(
    portfolio_id: int,
    response: Response,
    period: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """사용자 성과 조회 (Read-only, LIVE 전용)"""
    _apply_cache_headers(response)
    try:
        portfolio = _get_user_portfolio(db, portfolio_id, current_user.id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="포트폴리오를 찾을 수 없습니다.",
            )

        entity_id = _performance_entity_id(portfolio_id)
        period_keys = ["1M", "3M", "6M", "YTD"]

        active_version_id = _get_active_result_version_id(db, portfolio_id)
        results = (
            db.query(PerformanceResult)
            .filter(
                PerformanceResult.performance_type == "LIVE",
                PerformanceResult.entity_type == "PORTFOLIO",
                PerformanceResult.entity_id == entity_id,
                PerformanceResult.period_type.in_(period_keys),
            )
            .order_by(PerformanceResult.period_end.desc())
            .all()
        )

        returns: Dict[str, Optional[float]] = {key: None for key in period_keys}
        for result in results:
            if result.period_type in returns:
                returns[result.period_type] = (
                    float(result.period_return) if result.period_return is not None else None
                )

        latest = _latest_live_performance(db, portfolio_id, active_version_id)
        as_of_date = latest.period_end if latest else date.today()
        cumulative_return = (
            float(latest.cumulative_return) if latest and latest.cumulative_return is not None else None
        )
        is_stale = as_of_date != date.today()
        warning_message = "표시된 기준일이 최신일과 다를 수 있습니다." if is_stale else None
        status_message = (
            "현재 최신 데이터가 준비되지 않았습니다. 잠시 후 다시 확인해주세요."
            if latest is None
            else None
        )
        selected_return = None
        if period:
            if period not in returns:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="지원하지 않는 기간입니다.",
                )
            selected_return = returns[period]

        benchmark_return = None
        if latest:
            benchmark = (
                db.query(BenchmarkResult)
                .filter(BenchmarkResult.performance_id == latest.performance_id)
                .order_by(BenchmarkResult.created_at.desc())
                .first()
            )
            if benchmark and benchmark.benchmark_return is not None:
                benchmark_return = float(benchmark.benchmark_return)

        return {
            "success": True,
            "data": {
                "portfolio_id": portfolio.portfolio_id,
                "as_of_date": as_of_date,
                "performance_type": "LIVE",
                "returns": returns,
                "selected_period": period,
                "selected_return": selected_return,
                "cumulative_return": cumulative_return,
                "benchmark_return": benchmark_return,
                "is_reference": latest is None,
                "is_stale": is_stale,
                "warning_message": warning_message,
                "status_message": status_message,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        _raise_user_friendly_error(exc)


@router.get("/{portfolio_id}/performance/explanation")
def get_portfolio_performance_explanation(
    portfolio_id: int,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """성과 해석 정보 조회 (Read-only)"""
    _apply_cache_headers(response)
    try:
        portfolio = _get_user_portfolio(db, portfolio_id, current_user.id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="포트폴리오를 찾을 수 없습니다.",
            )

        active_version_id = _get_active_result_version_id(db, portfolio_id)
        latest = _latest_live_performance(db, portfolio_id, active_version_id)
        as_of_date = latest.period_end if latest else date.today()
        status_message = (
            "현재 최신 데이터가 준비되지 않았습니다. 잠시 후 다시 확인해주세요."
            if latest is None
            else None
        )
        is_stale = as_of_date != date.today()
        warning_message = "표시된 기준일이 최신일과 다를 수 있습니다." if is_stale else None

        return {
            "success": True,
            "data": {
                "portfolio_id": portfolio.portfolio_id,
                "as_of_date": as_of_date,
                "calculation": "종가 기준 누적 수익률 계산",
                "factors": ["fees", "fx", "dividend"],
                "price_basis": "close",
                "disclaimer": [
                    "본 정보는 투자 권유가 아닙니다.",
                    "과거 성과는 미래 수익을 보장하지 않습니다.",
                    "참고용 정보 제공 목적입니다.",
                ],
                "is_reference": latest is None,
                "is_stale": is_stale,
                "warning_message": warning_message,
                "status_message": status_message,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        _raise_user_friendly_error(exc)


@router.get("/{portfolio_id}/explain/why")
def get_portfolio_why_panel(
    portfolio_id: int,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """신뢰 설명 패널(Why Panel) 조회"""
    _apply_cache_headers(response)
    try:
        portfolio = _get_user_portfolio(db, portfolio_id, current_user.id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="포트폴리오를 찾을 수 없습니다.",
            )

        active_version_id = _get_active_result_version_id(db, portfolio_id)
        latest = _latest_live_performance(db, portfolio_id, active_version_id)
        as_of_date = latest.period_end if latest else date.today()
        calculated_at = latest.created_at if latest else None
        status_message = (
            "현재 최신 데이터가 준비되지 않았습니다. 잠시 후 다시 확인해주세요."
            if latest is None
            else None
        )
        is_stale = as_of_date != date.today()
        warning_message = "표시된 기준일이 최신일과 다를 수 있습니다." if is_stale else None

        return {
            "success": True,
            "data": {
                "title": "이 숫자는 어떻게 계산되었나요?",
                "portfolio_id": portfolio.portfolio_id,
                "as_of_date": as_of_date,
                "calculated_at": calculated_at,
                "data_snapshot": "일일 종가 스냅샷",
                "note": "이 값은 기준일 종가를 바탕으로 계산되었습니다.",
                "disclaimer": [
                    "본 정보는 투자 권유가 아닙니다.",
                    "과거 성과는 미래 수익을 보장하지 않습니다.",
                    "참고용 정보 제공 목적입니다.",
                ],
                "is_reference": latest is None,
                "is_stale": is_stale,
                "warning_message": warning_message,
                "status_message": status_message,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        _raise_user_friendly_error(exc)


@router.get("/{portfolio_id}/performance/history")
def get_portfolio_performance_history(
    portfolio_id: int,
    response: Response,
    interval: str = "MONTHLY",
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    limit: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """성과 히스토리 조회 (Read-only, LIVE 전용)"""
    _apply_cache_headers(response)
    try:
        portfolio = _get_user_portfolio(db, portfolio_id, current_user.id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="포트폴리오를 찾을 수 없습니다.",
            )

        interval = interval.upper()
        if interval not in {"DAILY", "WEEKLY", "MONTHLY"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="지원하지 않는 interval입니다.",
            )

        if from_date and to_date and from_date > to_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="기간 설정이 올바르지 않습니다.",
            )

        limit_value = _normalize_limit(limit)
        entity_id = _performance_entity_id(portfolio_id)
        active_version_id = _get_active_result_version_id(db, portfolio_id)

        query = db.query(PerformanceResult).filter(
            PerformanceResult.performance_type == "LIVE",
            PerformanceResult.entity_type == "PORTFOLIO",
            PerformanceResult.entity_id == entity_id,
            PerformanceResult.period_type == interval,
        )
        if active_version_id:
            query = query.filter(PerformanceResult.result_version_id == active_version_id)
        if from_date:
            query = query.filter(PerformanceResult.period_start >= from_date)
        if to_date:
            query = query.filter(PerformanceResult.period_end <= to_date)

        results = (
            query.order_by(PerformanceResult.period_end.desc())
            .limit(limit_value)
            .all()
        )

        has_data = len(results) > 0
        as_of_date = results[0].period_end if has_data else date.today()
        status_flags = _build_status_flags(as_of_date, has_data)

        items = [
            {
                "period_start": result.period_start,
                "period_end": result.period_end,
                "period_return": float(result.period_return) if result.period_return is not None else None,
                "cumulative_return": float(result.cumulative_return)
                if result.cumulative_return is not None
                else None,
                "is_reference": False,
            }
            for result in results
        ]

        return {
            "success": True,
            "data": {
                "portfolio_id": portfolio.portfolio_id,
                "interval": interval,
                "from": from_date,
                "to": to_date,
                "as_of_date": as_of_date,
                "performance_type": "LIVE",
                "items": items,
                **status_flags,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        _raise_user_friendly_error(exc)


@router.get("/{portfolio_id}/performance/compare")
def compare_portfolio_performance(
    portfolio_id: int,
    response: Response,
    left_from: date,
    left_to: date,
    right_from: date,
    right_to: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """성과 기간 비교 (Read-only, LIVE 전용)"""
    _apply_cache_headers(response)
    try:
        portfolio = _get_user_portfolio(db, portfolio_id, current_user.id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="포트폴리오를 찾을 수 없습니다.",
            )

        if left_from > left_to or right_from > right_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="기간 설정이 올바르지 않습니다.",
            )

        entity_id = _performance_entity_id(portfolio_id)
        active_version_id = _get_active_result_version_id(db, portfolio_id)

        def _fetch_period(period_start: date, period_end: date) -> Optional[PerformanceResult]:
            query = db.query(PerformanceResult).filter(
                PerformanceResult.performance_type == "LIVE",
                PerformanceResult.entity_type == "PORTFOLIO",
                PerformanceResult.entity_id == entity_id,
                PerformanceResult.period_start == period_start,
                PerformanceResult.period_end == period_end,
            )
            if active_version_id:
                query = query.filter(PerformanceResult.result_version_id == active_version_id)
            return query.order_by(PerformanceResult.created_at.desc()).first()

        left_result = _fetch_period(left_from, left_to)
        right_result = _fetch_period(right_from, right_to)

        left_period_return = float(left_result.period_return) if left_result and left_result.period_return is not None else None
        right_period_return = float(right_result.period_return) if right_result and right_result.period_return is not None else None
        left_cumulative_return = (
            float(left_result.cumulative_return) if left_result and left_result.cumulative_return is not None else None
        )
        right_cumulative_return = (
            float(right_result.cumulative_return) if right_result and right_result.cumulative_return is not None else None
        )

        delta_period = (
            left_period_return - right_period_return
            if left_period_return is not None and right_period_return is not None
            else None
        )
        delta_cumulative = (
            left_cumulative_return - right_cumulative_return
            if left_cumulative_return is not None and right_cumulative_return is not None
            else None
        )

        if delta_period is None:
            summary = "비교할 데이터가 충분하지 않습니다."
        elif delta_period > 0:
            summary = "좌측 기간의 수익률이 우측 기간보다 높습니다."
        elif delta_period < 0:
            summary = "좌측 기간의 수익률이 우측 기간보다 낮습니다."
        else:
            summary = "좌측 기간의 수익률이 우측 기간과 유사합니다."

        latest_date_candidates = [
            result.period_end for result in (left_result, right_result) if result
        ]
        as_of_date = max(latest_date_candidates) if latest_date_candidates else date.today()
        status_flags = _build_status_flags(as_of_date, left_result is not None and right_result is not None)

        return {
            "success": True,
            "data": {
                "portfolio_id": portfolio.portfolio_id,
                "performance_type": "LIVE",
                "left": {
                    "from": left_from,
                    "to": left_to,
                    "period_return": left_period_return,
                    "cumulative_return": left_cumulative_return,
                    "as_of_date": left_result.period_end if left_result else None,
                },
                "right": {
                    "from": right_from,
                    "to": right_to,
                    "period_return": right_period_return,
                    "cumulative_return": right_cumulative_return,
                    "as_of_date": right_result.period_end if right_result else None,
                },
                "delta": {
                    "period_return": delta_period,
                    "cumulative_return": delta_cumulative,
                },
                "summary": summary,
                **status_flags,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        _raise_user_friendly_error(exc)


@router.get("/{portfolio_id}/metrics/{metric_key}")
def get_portfolio_metric_detail(
    portfolio_id: int,
    metric_key: str,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """지표 상세 정보 조회 (Read-only, LIVE 전용)"""
    _apply_cache_headers(response)
    try:
        portfolio = _get_user_portfolio(db, portfolio_id, current_user.id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="포트폴리오를 찾을 수 없습니다.",
            )

        metric_key = metric_key.lower()
        metric_map = {
            "cagr": ("annualized_return", "연복리수익률", "(종료 가치 / 시작 가치)^(1/년수) - 1"),
            "volatility": ("volatility", "변동성", "가격 변동의 표준편차(연율화)"),
            "mdd": ("mdd", "최대 낙폭", "최고점 대비 최대 하락 폭"),
            "total_return": ("cumulative_return", "누적 수익률", "(종료 가치 / 시작 가치) - 1"),
            "sharpe": ("sharpe_ratio", "샤프 비율", "(연율화 수익률 - 무위험 수익률) / 변동성"),
            "sortino": ("sortino_ratio", "소르티노 비율", "(연율화 수익률 - 무위험 수익률) / 하방 변동성"),
        }
        if metric_key not in metric_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="지원하지 않는 metric입니다.",
            )

        entity_id = _performance_entity_id(portfolio_id)
        active_version_id = _get_active_result_version_id(db, portfolio_id)
        query = db.query(PerformanceResult).filter(
            PerformanceResult.performance_type == "LIVE",
            PerformanceResult.entity_type == "PORTFOLIO",
            PerformanceResult.entity_id == entity_id,
        )
        if active_version_id:
            query = query.filter(PerformanceResult.result_version_id == active_version_id)
        latest = query.order_by(PerformanceResult.period_end.desc()).first()

        as_of_date = latest.period_end if latest else date.today()
        status_flags = _build_status_flags(as_of_date, latest is not None)

        column_name, label, formula = metric_map[metric_key]
        value = getattr(latest, column_name, None) if latest else None
        value_float = float(value) if value is not None else None

        basis = (
            db.query(PerformanceBasis)
            .filter(PerformanceBasis.performance_id == latest.performance_id)
            .order_by(PerformanceBasis.created_at.desc())
            .first()
            if latest
            else None
        )
        factors = []
        if basis:
            if basis.include_fee:
                factors.append("fees")
            if basis.include_tax:
                factors.append("tax")
            if basis.include_dividend:
                factors.append("dividend")
            if basis.fx_snapshot_id:
                factors.append("fx")

        if value_float is None:
            status_flags["status_message"] = "해당 지표 데이터가 아직 준비되지 않았습니다."

        return {
            "success": True,
            "data": {
                "portfolio_id": portfolio.portfolio_id,
                "metric_key": metric_key,
                "metric_label": label,
                "as_of_date": as_of_date,
                "value": value_float,
                "formatted_value": f"{value_float:.2%}" if value_float is not None else None,
                "definition": "기간 동안의 성과를 설명하기 위한 지표입니다.",
                "formula": formula,
                "factors": factors,
                "notes": ["과거 성과이며 미래 수익을 보장하지 않습니다."],
                **status_flags,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        _raise_user_friendly_error(exc)
