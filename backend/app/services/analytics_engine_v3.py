"""
Phase 8-A: 분석 깊이 확장 계산 엔진 (v3)

Phase 7 입력과 NAV 시계열을 그대로 사용하며,
추가 지표는 과거 사실의 확장 정보로만 제공한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List

from app.services.performance_analyzer import NAVPoint, calculate_daily_returns, calculate_volatility


@dataclass
class ExtensionData:
    rolling_returns_3y: List[dict]
    rolling_returns_5y: List[dict]
    rolling_volatility_3y: List[dict]
    yearly_returns: List[dict]
    contributions: List[dict]
    drawdown_segments: List[dict]

    def to_dict(self) -> dict:
        return {
            "rolling_returns": {
                "window_3y": self.rolling_returns_3y,
                "window_5y": self.rolling_returns_5y,
            },
            "rolling_volatility": {
                "window_3y": self.rolling_volatility_3y,
            },
            "yearly_returns": self.yearly_returns,
            "contributions": self.contributions,
            "drawdown_segments": self.drawdown_segments,
        }


def build_extensions(
    nav_series: List[NAVPoint],
    item_series: List[Dict[date, float]],
    weights: List[float],
    items: List[dict],
) -> ExtensionData:
    rolling_returns_3y = _calculate_rolling_returns(nav_series, years=3)
    rolling_returns_5y = _calculate_rolling_returns(nav_series, years=5)
    rolling_volatility_3y = _calculate_rolling_volatility(nav_series, years=3)
    yearly_returns = _calculate_yearly_returns(nav_series)
    contributions = _calculate_contributions(nav_series, item_series, weights, items)
    drawdown_segments = _calculate_drawdown_segments(nav_series)

    return ExtensionData(
        rolling_returns_3y=rolling_returns_3y,
        rolling_returns_5y=rolling_returns_5y,
        rolling_volatility_3y=rolling_volatility_3y,
        yearly_returns=yearly_returns,
        contributions=contributions,
        drawdown_segments=drawdown_segments,
    )


def _calculate_rolling_returns(nav_series: List[NAVPoint], years: int) -> List[dict]:
    window_days = years * 365
    results = []
    for idx, point in enumerate(nav_series):
        target_date = point.nav_date - timedelta(days=window_days)
        start_idx = _find_start_index(nav_series, target_date)
        if start_idx is None or start_idx >= idx:
            continue
        start_nav = nav_series[start_idx].nav
        end_nav = point.nav
        if start_nav <= 0:
            continue
        results.append(
            {
                "end_date": point.nav_date.isoformat(),
                "value": round((end_nav / start_nav) - 1, 6),
            }
        )
    return results


def _calculate_rolling_volatility(nav_series: List[NAVPoint], years: int) -> List[dict]:
    window_days = years * 365
    results = []
    for idx, point in enumerate(nav_series):
        target_date = point.nav_date - timedelta(days=window_days)
        start_idx = _find_start_index(nav_series, target_date)
        if start_idx is None or start_idx >= idx:
            continue
        window_nav = nav_series[start_idx : idx + 1]
        daily_returns = calculate_daily_returns(window_nav)
        if len(daily_returns) < 2:
            continue
        volatility = calculate_volatility(daily_returns)
        results.append(
            {
                "end_date": point.nav_date.isoformat(),
                "value": round(volatility, 6),
            }
        )
    return results


def _calculate_yearly_returns(nav_series: List[NAVPoint]) -> List[dict]:
    if not nav_series:
        return []
    by_year: Dict[int, List[NAVPoint]] = {}
    for point in nav_series:
        by_year.setdefault(point.nav_date.year, []).append(point)

    results = []
    for year in sorted(by_year.keys()):
        year_series = by_year[year]
        start_nav = year_series[0].nav
        end_nav = year_series[-1].nav
        if start_nav <= 0:
            continue
        results.append(
            {
                "year": year,
                "value": round((end_nav / start_nav) - 1, 6),
            }
        )
    return results


def _calculate_contributions(
    nav_series: List[NAVPoint],
    item_series: List[Dict[date, float]],
    weights: List[float],
    items: List[dict],
) -> List[dict]:
    if not nav_series:
        return []
    start_date = nav_series[0].nav_date
    end_date = nav_series[-1].nav_date
    results = []
    for idx, series in enumerate(item_series):
        start_price = series.get(start_date)
        end_price = series.get(end_date)
        if start_price is None or end_price is None or start_price <= 0:
            continue
        item_return = (end_price / start_price) - 1
        item_meta = items[idx] if idx < len(items) else {}
        results.append(
            {
                "item_id": item_meta.get("id", f"item_{idx + 1}"),
                "item_name": item_meta.get("name", f"item_{idx + 1}"),
                "value": round(item_return * weights[idx], 6),
            }
        )
    return results


def _calculate_drawdown_segments(nav_series: List[NAVPoint]) -> List[dict]:
    segments = []
    if len(nav_series) < 2:
        return segments

    peak_nav = nav_series[0].nav
    peak_date = nav_series[0].nav_date
    in_drawdown = False
    trough_nav = peak_nav
    trough_date = peak_date

    for point in nav_series[1:]:
        if point.nav >= peak_nav:
            if in_drawdown:
                segments.append(
                    {
                        "start": peak_date.isoformat(),
                        "end": point.nav_date.isoformat(),
                        "drawdown": round((trough_nav / peak_nav) - 1, 6),
                    }
                )
                in_drawdown = False
            peak_nav = point.nav
            peak_date = point.nav_date
            trough_nav = peak_nav
            trough_date = peak_date
            continue

        drawdown = (point.nav / peak_nav) - 1
        if not in_drawdown:
            in_drawdown = True
            trough_nav = point.nav
            trough_date = point.nav_date
        elif drawdown < (trough_nav / peak_nav) - 1:
            trough_nav = point.nav
            trough_date = point.nav_date

    if in_drawdown:
        segments.append(
            {
                "start": peak_date.isoformat(),
                "end": nav_series[-1].nav_date.isoformat(),
                "drawdown": round((trough_nav / peak_nav) - 1, 6),
            }
        )
    return segments


def _find_start_index(nav_series: List[NAVPoint], target_date: date) -> int | None:
    for idx, point in enumerate(nav_series):
        if point.nav_date >= target_date:
            return idx
    return None
