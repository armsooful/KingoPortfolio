"""
Phase 7: 과거 데이터 기반 포트폴리오 평가 서비스

추천/판단 없이 입력 구성에 대한 지표를 계산한다.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session

from app.models.phase7_portfolio import Phase7Portfolio
from app.models.securities import KrxTimeSeries, Stock
from app.services.performance_analyzer import NAVPoint, analyze_performance
from app.services.analytics_engine_v3 import build_extensions
from app.services.engine_input_adapter_v3 import build_input_context
from app.services.phase7_errors import Phase7EvaluationError


def evaluate_phase7_portfolio(
    db: Session,
    portfolio: Phase7Portfolio,
    period_start: date,
    period_end: date,
    rebalance: str,
    input_extensions: dict | None = None,
) -> dict:
    build_input_context(input_extensions)
    items = portfolio.items
    if not items:
        raise Phase7EvaluationError("데이터가 일부 누락되어 계산이 제한됩니다.")

    item_series = []
    for item in items:
        series = _load_item_series(
            db=db,
            portfolio_type=portfolio.portfolio_type,
            item_key=item.item_key,
            period_start=period_start,
            period_end=period_end,
        )
        item_series.append(series)

    common_dates = _intersect_dates(item_series)
    if len(common_dates) < 2:
        raise Phase7EvaluationError("선택한 기간의 과거 데이터를 불러올 수 없습니다.")

    nav_series = _build_nav_series(
        common_dates=common_dates,
        item_series=item_series,
        weights=[float(item.weight) for item in items],
        rebalance=rebalance,
    )

    metrics = analyze_performance(nav_series)

    result = {
        "period": {
            "start": common_dates[0].isoformat(),
            "end": common_dates[-1].isoformat(),
        },
        "metrics": {
            "cumulative_return": round(metrics.total_return, 6),
            "cagr": round(metrics.cagr, 6),
            "volatility": round(metrics.volatility, 6),
            "max_drawdown": round(metrics.mdd, 6),
        },
        "disclaimer_version": "v2",
    }

    extensions = build_extensions(
        nav_series,
        item_series,
        [float(item.weight) for item in items],
        [{"id": item.item_key, "name": item.item_name} for item in items],
    )
    result["extensions"] = extensions.to_dict()

    return result


def serialize_result(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False)


def hash_result(serialized_result: str) -> str:
    return hashlib.sha256(serialized_result.encode("utf-8")).hexdigest()


def _load_item_series(
    db: Session,
    portfolio_type: str,
    item_key: str,
    period_start: date,
    period_end: date,
) -> Dict[date, float]:
    if portfolio_type == "SECURITY":
        return _load_security_series(db, item_key, period_start, period_end)
    if portfolio_type == "SECTOR":
        return _load_sector_series(db, item_key, period_start, period_end)
    raise Phase7EvaluationError("데이터가 일부 누락되어 계산이 제한됩니다.")


def _load_security_series(
    db: Session,
    ticker: str,
    period_start: date,
    period_end: date,
) -> Dict[date, float]:
    rows = (
        db.query(KrxTimeSeries)
        .filter(
            KrxTimeSeries.ticker == ticker,
            KrxTimeSeries.date >= period_start,
            KrxTimeSeries.date <= period_end,
        )
        .order_by(KrxTimeSeries.date.asc())
        .all()
    )
    if not rows:
        raise Phase7EvaluationError("조회기간에 해당하는 시계열 데이터가 없습니다.")

    return {row.date: row.close for row in rows}


def _load_sector_series(
    db: Session,
    sector: str,
    period_start: date,
    period_end: date,
) -> Dict[date, float]:
    tickers = [
        row[0]
        for row in db.query(Stock.ticker)
        .filter(Stock.sector == sector, Stock.is_active == True)
        .all()
    ]
    if not tickers:
        raise Phase7EvaluationError("조회기간에 해당하는 시계열 데이터가 없습니다.")

    rows = (
        db.query(KrxTimeSeries)
        .filter(
            KrxTimeSeries.ticker.in_(tickers),
            KrxTimeSeries.date >= period_start,
            KrxTimeSeries.date <= period_end,
        )
        .order_by(KrxTimeSeries.date.asc())
        .all()
    )
    if not rows:
        raise Phase7EvaluationError("조회기간에 해당하는 시계열 데이터가 없습니다.")

    sums: Dict[date, float] = {}
    counts: Dict[date, int] = {}
    for row in rows:
        sums[row.date] = sums.get(row.date, 0.0) + row.close
        counts[row.date] = counts.get(row.date, 0) + 1

    return {day: sums[day] / counts[day] for day in sums}


def _intersect_dates(series_list: List[Dict[date, float]]) -> List[date]:
    common = None
    for series in series_list:
        keys = set(series.keys())
        common = keys if common is None else common.intersection(keys)
    if not common:
        return []
    return sorted(common)


def _build_nav_series(
    common_dates: List[date],
    item_series: List[Dict[date, float]],
    weights: List[float],
    rebalance: str,
) -> List[NAVPoint]:
    prices = [
        [series[day] for day in common_dates]
        for series in item_series
    ]

    if any(prices[i][0] <= 0 for i in range(len(prices))):
        raise Phase7EvaluationError("데이터가 일부 누락되어 계산이 제한됩니다.")

    total_value = 1.0
    units = [
        (weights[i] * total_value) / prices[i][0]
        for i in range(len(prices))
    ]

    nav_series = []
    prev_date = common_dates[0]

    for idx, current_date in enumerate(common_dates):
        if idx > 0 and _should_rebalance(prev_date, current_date, rebalance):
            total_value = sum(units[i] * prices[i][idx] for i in range(len(prices)))
            units = [
                (weights[i] * total_value) / prices[i][idx]
                for i in range(len(prices))
            ]

        total_value = sum(units[i] * prices[i][idx] for i in range(len(prices)))
        nav_series.append(NAVPoint(nav_date=current_date, nav=total_value))
        prev_date = current_date

    return nav_series


def _should_rebalance(prev_date: date, current_date: date, rebalance: str) -> bool:
    if rebalance == "MONTHLY":
        return (prev_date.year, prev_date.month) != (current_date.year, current_date.month)
    if rebalance == "QUARTERLY":
        prev_quarter = (prev_date.month - 1) // 3
        curr_quarter = (current_date.month - 1) // 3
        return (prev_date.year, prev_quarter) != (current_date.year, curr_quarter)
    return False
