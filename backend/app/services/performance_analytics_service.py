"""
Phase 3-C / Epic C-3: 성과 분석 서비스
"""

from dataclasses import dataclass
from datetime import date
from math import sqrt
from statistics import mean, pstdev
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session

from app.models.performance import PerformanceResult, PerformanceBasis


@dataclass
class PerformanceMetrics:
    period_return: Optional[float] = None
    cumulative_return: Optional[float] = None
    annualized_return: Optional[float] = None
    volatility: Optional[float] = None
    mdd: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None


class PerformanceAnalyticsService:
    """성과 분석 계산 및 저장"""

    def __init__(self, db: Session):
        self.db = db

    def _daily_returns(self, values: List[float]) -> List[float]:
        returns = []
        for i in range(1, len(values)):
            if values[i - 1] == 0:
                continue
            returns.append((values[i] - values[i - 1]) / values[i - 1])
        return returns

    def _max_drawdown(self, values: List[float]) -> Optional[float]:
        if not values:
            return None
        peak = values[0]
        max_dd = 0.0
        for v in values:
            if v > peak:
                peak = v
            if peak > 0:
                dd = (v / peak) - 1.0
                if dd < max_dd:
                    max_dd = dd
        return max_dd

    def calculate_metrics(
        self,
        values: List[float],
        period_days: Optional[int] = None,
        rf: float = 0.0,
    ) -> PerformanceMetrics:
        if len(values) < 2:
            return PerformanceMetrics()

        period_return = (values[-1] - values[0]) / values[0] if values[0] else None
        cumulative_return = (values[-1] / values[0]) - 1.0 if values[0] else None

        period_days = period_days or max(len(values) - 1, 1)
        annualized_return = None
        if cumulative_return is not None and period_days > 0:
            annualized_return = (1 + cumulative_return) ** (365 / period_days) - 1

        daily_returns = self._daily_returns(values)
        volatility = None
        if daily_returns:
            volatility = pstdev(daily_returns) * sqrt(252)

        mdd = self._max_drawdown(values)

        sharpe = None
        if annualized_return is not None and volatility and volatility > 0:
            sharpe = (annualized_return - rf) / volatility

        downside_returns = [r for r in daily_returns if r < 0]
        sortino = None
        if downside_returns:
            downside_vol = pstdev(downside_returns) * sqrt(252)
            if downside_vol > 0 and annualized_return is not None:
                sortino = (annualized_return - rf) / downside_vol

        return PerformanceMetrics(
            period_return=period_return,
            cumulative_return=cumulative_return,
            annualized_return=annualized_return,
            volatility=volatility,
            mdd=mdd,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
        )

    def create_performance_result(
        self,
        performance_type: str,
        entity_type: str,
        entity_id: str,
        period_type: str,
        period_start: date,
        period_end: date,
        values: List[float],
        execution_id: Optional[str] = None,
        snapshot_ids: Optional[List[str]] = None,
        result_version_id: Optional[str] = None,
        calc_params: Optional[Dict[str, Any]] = None,
        rf: float = 0.0,
        include_fee: bool = True,
        include_tax: bool = False,
        include_dividend: bool = False,
        price_basis: str = "CLOSE",
        fx_snapshot_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> PerformanceResult:
        metrics = self.calculate_metrics(
            values=values,
            period_days=(period_end - period_start).days,
            rf=rf,
        )

        result = PerformanceResult(
            performance_type=performance_type,
            entity_type=entity_type,
            entity_id=entity_id,
            period_type=period_type,
            period_start=period_start,
            period_end=period_end,
            period_return=metrics.period_return,
            cumulative_return=metrics.cumulative_return,
            annualized_return=metrics.annualized_return,
            volatility=metrics.volatility,
            mdd=metrics.mdd,
            sharpe_ratio=metrics.sharpe_ratio,
            sortino_ratio=metrics.sortino_ratio,
            execution_id=execution_id,
            snapshot_ids=snapshot_ids or [],
            result_version_id=result_version_id,
            calc_params=calc_params or {},
        )
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)

        basis = PerformanceBasis(
            performance_id=result.performance_id,
            price_basis=price_basis,
            include_fee=include_fee,
            include_tax=include_tax,
            include_dividend=include_dividend,
            fx_snapshot_id=fx_snapshot_id,
            notes=notes,
        )
        self.db.add(basis)
        self.db.commit()

        return result
