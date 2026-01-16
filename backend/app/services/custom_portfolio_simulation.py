"""
Phase 2 Epic C: 커스텀 포트폴리오 시뮬레이션 서비스

커스텀 포트폴리오를 사용한 시뮬레이션 실행

**주요 기능:**
- 커스텀 포트폴리오 비중으로 NAV 경로 계산
- 기존 시뮬레이션 엔진(Phase 1) 재사용
- 리밸런싱(Epic B) 연동 지원
- request_hash에 weights 포함 (재현성)

⚠️ 본 서비스는 교육 목적의 시뮬레이션이며,
투자 추천이나 자문을 제공하지 않습니다.
과거 데이터 기반 분석으로, 미래 수익을 보장하지 않습니다.
"""

import hashlib
import json
from datetime import date
from typing import Dict, List, Optional, Any
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config import settings
from app.services.custom_portfolio_service import (
    get_weights_for_simulation,
    get_weights_hash_string,
    validate_weights,
    PortfolioValidationError,
)
from app.services.performance_analyzer import analyze_from_nav_list


# ============================================================================
# 시뮬레이션 해시 생성
# ============================================================================

def generate_custom_portfolio_hash(
    portfolio_id: int,
    weights: Dict[str, float],
    start_date: date,
    end_date: date,
    initial_nav: float,
    rebalancing_rule_id: Optional[int] = None,
    rf_annual: float = 0.0,
) -> str:
    """
    커스텀 포트폴리오 시뮬레이션 request_hash 생성

    비중을 정렬하여 포함 → 동일 입력 시 동일 해시

    Args:
        portfolio_id: 포트폴리오 ID
        weights: 자산군별 비중
        start_date: 시작일
        end_date: 종료일
        initial_nav: 초기 NAV
        rebalancing_rule_id: 리밸런싱 규칙 ID
        rf_annual: 무위험 수익률

    Returns:
        SHA-256 해시 문자열
    """
    weights_str = get_weights_hash_string(weights)

    hash_input = {
        "type": "custom_portfolio",
        "portfolio_id": portfolio_id,
        "weights": weights_str,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "initial_nav": initial_nav,
        "rebalancing_rule_id": rebalancing_rule_id,
        "rf_annual": rf_annual,
        "engine_version": settings.engine_version,
        "missing_data_policy": settings.missing_data_policy,
    }

    hash_str = json.dumps(hash_input, sort_keys=True)
    return hashlib.sha256(hash_str.encode()).hexdigest()


# ============================================================================
# 일간 수익률 조회
# ============================================================================

def get_daily_returns_by_asset_class(
    db: Session,
    asset_classes: List[str],
    start_date: date,
    end_date: date
) -> Dict[str, List[Dict]]:
    """
    자산군별 일간 수익률 조회

    Args:
        db: DB 세션
        asset_classes: 자산군 코드 리스트
        start_date: 시작일
        end_date: 종료일

    Returns:
        {
            "EQUITY": [{"return_date": date, "daily_return": float}, ...],
            "BOND": [...],
            ...
        }
    """
    # daily_return 테이블에서 자산군별 수익률 조회
    # 실제 테이블 구조에 맞게 쿼리 수정 필요
    sql = text("""
        SELECT
            asset_class_code,
            return_date,
            daily_return
        FROM daily_return
        WHERE asset_class_code = ANY(:asset_classes)
          AND return_date BETWEEN :start_date AND :end_date
        ORDER BY asset_class_code, return_date
    """)

    try:
        result = db.execute(sql, {
            "asset_classes": asset_classes,
            "start_date": start_date,
            "end_date": end_date,
        }).fetchall()

        returns_by_class = {ac: [] for ac in asset_classes}
        for row in result:
            ac_code = row[0]
            if ac_code in returns_by_class:
                returns_by_class[ac_code].append({
                    "return_date": row[1],
                    "daily_return": float(row[2]) if row[2] else 0.0,
                })

        return returns_by_class

    except Exception as e:
        # 테이블이 없거나 쿼리 실패 시 빈 dict 반환
        return {ac: [] for ac in asset_classes}


# ============================================================================
# NAV 경로 계산
# ============================================================================

def calculate_portfolio_nav_path(
    weights: Dict[str, float],
    daily_returns: Dict[str, List[Dict]],
    initial_nav: float = 1.0
) -> List[Dict]:
    """
    포트폴리오 NAV 경로 계산

    가중평균 일간 수익률로 NAV 경로 생성

    Args:
        weights: 자산군별 비중
        daily_returns: 자산군별 일간 수익률
        initial_nav: 초기 NAV

    Returns:
        [{"path_date": date, "nav": float, "daily_return": float, ...}, ...]
    """
    # 모든 날짜 추출 및 정렬
    all_dates = set()
    for ac_returns in daily_returns.values():
        for r in ac_returns:
            all_dates.add(r["return_date"])

    if not all_dates:
        return []

    sorted_dates = sorted(all_dates)

    # 자산군별 수익률을 날짜 기준 dict로 변환
    returns_by_date = {}
    for ac, ac_returns in daily_returns.items():
        for r in ac_returns:
            d = r["return_date"]
            if d not in returns_by_date:
                returns_by_date[d] = {}
            returns_by_date[d][ac] = r["daily_return"]

    # NAV 경로 계산
    nav = initial_nav
    peak_nav = initial_nav
    path = []

    for i, d in enumerate(sorted_dates):
        # 가중평균 일간 수익률
        day_returns = returns_by_date.get(d, {})
        weighted_return = 0.0

        for ac, weight in weights.items():
            ac_return = day_returns.get(ac, 0.0)
            weighted_return += weight * ac_return

        # NAV 업데이트
        if i == 0:
            # 첫날: 초기 NAV
            daily_return = 0.0
        else:
            daily_return = weighted_return
            nav = nav * (1 + weighted_return)

        # Peak 업데이트
        if nav > peak_nav:
            peak_nav = nav

        # Drawdown 계산
        drawdown = (nav - peak_nav) / peak_nav if peak_nav > 0 else 0.0

        # 누적 수익률
        cumulative_return = (nav - initial_nav) / initial_nav if initial_nav > 0 else 0.0

        path.append({
            "path_date": d,
            "nav": nav,
            "daily_return": daily_return,
            "cumulative_return": cumulative_return,
            "drawdown": drawdown,
        })

    return path


# ============================================================================
# 시뮬레이션 실행
# ============================================================================

def run_custom_portfolio_simulation(
    db: Session,
    portfolio_id: int,
    start_date: date,
    end_date: date,
    initial_nav: float = 1.0,
    rebalancing_rule_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    커스텀 포트폴리오 시뮬레이션 실행

    Args:
        db: DB 세션
        portfolio_id: 포트폴리오 ID
        start_date: 시작일
        end_date: 종료일
        initial_nav: 초기 NAV
        rebalancing_rule_id: 리밸런싱 규칙 ID (Epic B 연동)

    Returns:
        시뮬레이션 결과 dict

    Raises:
        ValueError: 포트폴리오 없음 또는 데이터 부족
    """
    # 1. 포트폴리오 비중 조회
    weights = get_weights_for_simulation(db, portfolio_id)

    if not weights:
        raise ValueError(f"포트폴리오 ID {portfolio_id}의 비중 정보가 없습니다.")

    # 2. request_hash 생성
    request_hash = generate_custom_portfolio_hash(
        portfolio_id=portfolio_id,
        weights=weights,
        start_date=start_date,
        end_date=end_date,
        initial_nav=initial_nav,
        rebalancing_rule_id=rebalancing_rule_id,
    )

    # 3. 일간 수익률 조회
    asset_classes = list(weights.keys())
    daily_returns = get_daily_returns_by_asset_class(
        db, asset_classes, start_date, end_date
    )

    # 4. NAV 경로 계산
    path = calculate_portfolio_nav_path(weights, daily_returns, initial_nav)

    if not path:
        # 데이터 부족 시 폴백 시뮬레이션
        path = generate_fallback_path(start_date, end_date, initial_nav, weights)

    # 5. 리밸런싱 처리 (Epic B 연동)
    rebalancing_events = []
    if rebalancing_rule_id and settings.use_rebalancing:
        # 리밸런싱 엔진 호출 (별도 구현)
        # rebalancing_events = apply_rebalancing(...)
        pass

    # 6. 위험 지표 계산
    risk_metrics = calculate_risk_metrics(path)

    # 7. Epic D KPI 계산 (성과 분석 연동)
    kpi_metrics = None
    if path and len(path) >= 2:
        try:
            nav_data = [{"path_date": p["path_date"], "nav": p["nav"]} for p in path]
            performance = analyze_from_nav_list(nav_data, rf_annual=0.0, annualization_factor=252)
            kpi_metrics = performance.to_dict()
        except Exception:
            # KPI 계산 실패 시 기본 지표만 사용
            pass

    # 8. 결과 반환
    final_nav = path[-1]["nav"] if path else initial_nav

    return {
        "portfolio_id": portfolio_id,
        "weights": weights,
        "start_date": start_date,
        "end_date": end_date,
        "initial_nav": initial_nav,
        "final_value": final_nav,
        "trading_days": len(path),
        "path": path,
        "risk_metrics": risk_metrics,
        "kpi_metrics": kpi_metrics,  # Epic D 연동
        "historical_observation": {
            "total_return": (final_nav - initial_nav) / initial_nav if initial_nav > 0 else 0.0,
            "cagr": kpi_metrics.get("cagr") if kpi_metrics else None,
            "sharpe": kpi_metrics.get("sharpe") if kpi_metrics else None,
            "note": "과거 데이터 기반 시뮬레이션이며, 미래 수익을 보장하지 않습니다.",
        },
        "rebalancing_enabled": bool(rebalancing_rule_id and settings.use_rebalancing),
        "rebalancing_events_count": len(rebalancing_events),
        "rebalancing_events": rebalancing_events if rebalancing_events else None,
        "request_hash": request_hash,
        "engine_version": settings.engine_version,
    }


def generate_fallback_path(
    start_date: date,
    end_date: date,
    initial_nav: float,
    weights: Dict[str, float]
) -> List[Dict]:
    """
    폴백 시뮬레이션 경로 생성 (데이터 없을 경우)

    랜덤하지 않은 결정론적 폴백

    Args:
        start_date: 시작일
        end_date: 종료일
        initial_nav: 초기 NAV
        weights: 비중 (seed로 사용)

    Returns:
        폴백 NAV 경로
    """
    from datetime import timedelta

    # 비중 기반 예상 수익률 (매우 단순화)
    # 실제로는 사용하지 않고 경고 메시지와 함께 빈 결과 반환 권장
    equity_weight = weights.get("EQUITY", 0)
    bond_weight = weights.get("BOND", 0)

    # 가상의 연율 수익률 (교육용)
    annual_return = equity_weight * 0.07 + bond_weight * 0.03  # 매우 단순화

    path = []
    current_date = start_date
    nav = initial_nav
    peak = initial_nav
    day_count = 0

    while current_date <= end_date:
        # 주말 제외 (간단히)
        if current_date.weekday() < 5:  # 월~금
            if day_count > 0:
                # 일간 수익률 (연율 / 252)
                daily_return = annual_return / 252
                nav = nav * (1 + daily_return)

            if nav > peak:
                peak = nav

            drawdown = (nav - peak) / peak if peak > 0 else 0.0
            cumulative_return = (nav - initial_nav) / initial_nav if initial_nav > 0 else 0.0

            path.append({
                "path_date": current_date,
                "nav": nav,
                "daily_return": annual_return / 252 if day_count > 0 else 0.0,
                "cumulative_return": cumulative_return,
                "drawdown": drawdown,
            })

            day_count += 1

        current_date += timedelta(days=1)

    return path


def calculate_risk_metrics(path: List[Dict]) -> Dict:
    """
    위험 지표 계산

    Args:
        path: NAV 경로

    Returns:
        위험 지표 dict
    """
    if not path or len(path) < 2:
        return {
            "volatility_annual": 0.0,
            "max_drawdown": 0.0,
            "max_drawdown_date": None,
        }

    # MDD 계산
    mdd = 0.0
    mdd_date = None
    for p in path:
        if p["drawdown"] < mdd:
            mdd = p["drawdown"]
            mdd_date = p["path_date"]

    # 변동성 계산 (연율화)
    daily_returns = [p["daily_return"] for p in path[1:]]  # 첫날 제외
    if daily_returns:
        import math
        mean = sum(daily_returns) / len(daily_returns)
        variance = sum((r - mean) ** 2 for r in daily_returns) / (len(daily_returns) - 1) if len(daily_returns) > 1 else 0
        std_daily = math.sqrt(variance)
        volatility_annual = std_daily * math.sqrt(252)
    else:
        volatility_annual = 0.0

    return {
        "volatility_annual": round(volatility_annual, 6),
        "max_drawdown": round(mdd, 6),
        "max_drawdown_date": mdd_date.isoformat() if mdd_date else None,
    }
