"""
Phase 1/2 시나리오 기반 포트폴리오 시뮬레이션 엔진 (P1-D1, P2-Epic B)

DB에 저장된 포트폴리오 구성비와 일간수익률을 사용하여
NAV 경로를 계산하고 손실/회복 지표를 산출

Phase 2에서 리밸런싱 엔진 통합:
- PERIODIC (월간/분기) 리밸런싱
- DRIFT (편차 기반) 리밸런싱
- 비용 모델 적용

⚠️ 교육 목적: 과거 데이터 기반 시뮬레이션이며, 미래 수익을 보장하지 않습니다.
"""

import math
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_

from app.config import settings


# ============================================================================
# 데이터 로딩 함수
# ============================================================================

def get_portfolio_allocation(
    db: Session,
    scenario_id: str,
    effective_date: date
) -> List[Dict]:
    """
    시나리오의 포트폴리오 구성비 조회 (적용일자 기준)

    Args:
        db: DB 세션
        scenario_id: 시나리오 ID
        effective_date: 적용 기준일

    Returns:
        [{"instrument_id": int, "ticker": str, "weight": float, "asset_class": str}, ...]
    """
    sql = text("""
        SELECT
            pa.instrument_id,
            im.ticker,
            im.name_ko,
            pa.weight,
            pa.asset_class
        FROM portfolio_allocation pa
        JOIN portfolio_model pm ON pa.portfolio_id = pm.portfolio_id
        JOIN instrument_master im ON pa.instrument_id = im.instrument_id
        WHERE pm.scenario_id = :scenario_id
          AND pm.effective_date <= :effective_date
          AND (pm.expiry_date IS NULL OR pm.expiry_date >= :effective_date)
        ORDER BY pa.weight DESC
    """)

    result = db.execute(sql, {
        "scenario_id": scenario_id,
        "effective_date": effective_date
    }).fetchall()

    return [
        {
            "instrument_id": row[0],
            "ticker": row[1],
            "name_ko": row[2],
            "weight": float(row[3]),
            "asset_class": row[4]
        }
        for row in result
    ]


def get_daily_returns(
    db: Session,
    instrument_ids: List[int],
    start_date: date,
    end_date: date
) -> Dict[int, List[Dict]]:
    """
    복수 종목의 일간수익률 조회

    Args:
        db: DB 세션
        instrument_ids: 금융상품 ID 목록
        start_date: 시작일
        end_date: 종료일

    Returns:
        {instrument_id: [{"trade_date": date, "daily_return": float}, ...], ...}
    """
    if not instrument_ids:
        return {}

    sql = text("""
        SELECT
            instrument_id,
            trade_date,
            daily_return,
            data_quality
        FROM daily_return
        WHERE instrument_id = ANY(:instrument_ids)
          AND trade_date >= :start_date
          AND trade_date <= :end_date
          AND data_quality IN ('OK', 'MISSING')
        ORDER BY instrument_id, trade_date
    """)

    result = db.execute(sql, {
        "instrument_ids": instrument_ids,
        "start_date": start_date,
        "end_date": end_date
    }).fetchall()

    # 종목별로 그룹핑
    returns_by_instrument: Dict[int, List[Dict]] = {}
    for row in result:
        inst_id = row[0]
        if inst_id not in returns_by_instrument:
            returns_by_instrument[inst_id] = []
        returns_by_instrument[inst_id].append({
            "trade_date": row[1],
            "daily_return": float(row[2]) if row[2] is not None else 0.0,
            "data_quality": row[3]
        })

    return returns_by_instrument


def get_trade_dates(
    db: Session,
    start_date: date,
    end_date: date
) -> List[date]:
    """
    거래일 목록 조회 (daily_return 기준)

    Args:
        db: DB 세션
        start_date: 시작일
        end_date: 종료일

    Returns:
        거래일 목록
    """
    sql = text("""
        SELECT DISTINCT trade_date
        FROM daily_return
        WHERE trade_date >= :start_date
          AND trade_date <= :end_date
        ORDER BY trade_date
    """)

    result = db.execute(sql, {
        "start_date": start_date,
        "end_date": end_date
    }).fetchall()

    return [row[0] for row in result]


# ============================================================================
# NAV 계산 함수
# ============================================================================

def calculate_portfolio_nav(
    allocations: List[Dict],
    returns_by_instrument: Dict[int, List[Dict]],
    trade_dates: List[date],
    initial_amount: float = 1000000.0
) -> List[Dict]:
    """
    포트폴리오 일별 NAV 경로 계산

    Args:
        allocations: 포트폴리오 구성비
        returns_by_instrument: 종목별 일간수익률
        trade_dates: 거래일 목록
        initial_amount: 초기 투자금액

    Returns:
        [{"path_date": date, "nav": float, "daily_return": float,
          "cumulative_return": float, "drawdown": float, "high_water_mark": float}, ...]
    """
    if not allocations or not trade_dates:
        return []

    # 종목별 수익률을 날짜 인덱스로 변환
    returns_lookup: Dict[int, Dict[date, float]] = {}
    for inst_id, returns in returns_by_instrument.items():
        returns_lookup[inst_id] = {
            r["trade_date"]: r["daily_return"]
            for r in returns
        }

    # NAV 경로 계산
    path = []
    nav = initial_amount
    high_water_mark = initial_amount
    prev_nav = initial_amount

    for trade_date in trade_dates:
        # 포트폴리오 가중 수익률 계산
        portfolio_return = 0.0
        total_weight = 0.0

        for alloc in allocations:
            inst_id = alloc["instrument_id"]
            weight = alloc["weight"]

            # 해당 종목의 해당 날짜 수익률
            inst_return = returns_lookup.get(inst_id, {}).get(trade_date, 0.0)
            portfolio_return += weight * inst_return
            total_weight += weight

        # 가중치 합이 1이 아닌 경우 정규화
        if total_weight > 0 and abs(total_weight - 1.0) > 0.001:
            portfolio_return = portfolio_return / total_weight

        # NAV 갱신
        nav = prev_nav * (1 + portfolio_return)

        # 고점 및 낙폭 계산
        if nav > high_water_mark:
            high_water_mark = nav
        drawdown = (nav - high_water_mark) / high_water_mark if high_water_mark > 0 else 0.0

        # 누적 수익률
        cumulative_return = (nav - initial_amount) / initial_amount if initial_amount > 0 else 0.0

        path.append({
            "path_date": trade_date,
            "nav": round(nav, 4),
            "daily_return": round(portfolio_return, 8),
            "cumulative_return": round(cumulative_return, 8),
            "drawdown": round(drawdown, 8),
            "high_water_mark": round(high_water_mark, 4)
        })

        prev_nav = nav

    return path


# ============================================================================
# 지표 계산 함수
# ============================================================================

def calculate_risk_metrics(
    nav_path: List[Dict],
    initial_amount: float = 1000000.0
) -> Dict:
    """
    손실/회복 지표 산출

    Args:
        nav_path: NAV 경로
        initial_amount: 초기 투자금액

    Returns:
        {
            "max_drawdown": float,
            "max_recovery_days": int,
            "worst_1m_return": float,
            "worst_3m_return": float,
            "volatility": float,
            "total_return": float,
            "cagr": float,
            "sharpe_ratio": float,
            "sortino_ratio": float,
            "final_value": float,
            "trading_days": int
        }
    """
    if not nav_path:
        return {
            "max_drawdown": 0.0,
            "max_recovery_days": None,
            "worst_1m_return": None,
            "worst_3m_return": None,
            "volatility": 0.0,
            "total_return": 0.0,
            "cagr": None,
            "sharpe_ratio": None,
            "sortino_ratio": None,
            "final_value": initial_amount,
            "trading_days": 0
        }

    # 기본 지표
    trading_days = len(nav_path)
    final_nav = nav_path[-1]["nav"]
    total_return = (final_nav - initial_amount) / initial_amount * 100

    # 연환산 수익률 (CAGR)
    if trading_days > 252:
        years = trading_days / 252
        cagr = ((final_nav / initial_amount) ** (1 / years) - 1) * 100
    else:
        cagr = None

    # 일간 수익률 리스트
    daily_returns = [p["daily_return"] for p in nav_path if p["daily_return"] is not None]

    # 연간 변동성
    if len(daily_returns) > 1:
        mean_return = sum(daily_returns) / len(daily_returns)
        variance = sum((r - mean_return) ** 2 for r in daily_returns) / len(daily_returns)
        daily_volatility = math.sqrt(variance)
        volatility = daily_volatility * math.sqrt(252) * 100  # 연환산 (%)
    else:
        volatility = 0.0

    # 샤프 비율 (무위험 수익률 3% 가정)
    risk_free_rate = 3.0
    if volatility > 0 and cagr is not None:
        sharpe_ratio = (cagr - risk_free_rate) / volatility
    else:
        sharpe_ratio = None

    # 소르티노 비율 (하방 변동성만 사용)
    negative_returns = [r for r in daily_returns if r < 0]
    if len(negative_returns) > 1 and cagr is not None:
        downside_variance = sum(r ** 2 for r in negative_returns) / len(negative_returns)
        downside_volatility = math.sqrt(downside_variance) * math.sqrt(252) * 100
        if downside_volatility > 0:
            sortino_ratio = (cagr - risk_free_rate) / downside_volatility
        else:
            sortino_ratio = None
    else:
        sortino_ratio = None

    # 최대 낙폭 (MDD)
    drawdowns = [p["drawdown"] for p in nav_path]
    max_drawdown = abs(min(drawdowns)) * 100 if drawdowns else 0.0

    # 최대 회복 기간
    max_recovery_days = calculate_max_recovery_days(nav_path)

    # 최악의 1개월/3개월 수익률
    worst_1m_return = calculate_worst_period_return(nav_path, 22)  # 약 1개월
    worst_3m_return = calculate_worst_period_return(nav_path, 66)  # 약 3개월

    return {
        "max_drawdown": round(max_drawdown, 4),
        "max_recovery_days": max_recovery_days,
        "worst_1m_return": round(worst_1m_return, 4) if worst_1m_return is not None else None,
        "worst_3m_return": round(worst_3m_return, 4) if worst_3m_return is not None else None,
        "volatility": round(volatility, 4),
        "total_return": round(total_return, 4),
        "cagr": round(cagr, 4) if cagr is not None else None,
        "sharpe_ratio": round(sharpe_ratio, 4) if sharpe_ratio is not None else None,
        "sortino_ratio": round(sortino_ratio, 4) if sortino_ratio is not None else None,
        "final_value": round(final_nav, 2),
        "trading_days": trading_days
    }


def calculate_max_recovery_days(nav_path: List[Dict]) -> Optional[int]:
    """최대 회복 기간 계산"""
    if not nav_path:
        return None

    max_recovery = 0
    in_drawdown = False
    drawdown_start_idx = 0
    high_water_mark = nav_path[0]["nav"]

    for i, p in enumerate(nav_path):
        nav = p["nav"]

        if nav >= high_water_mark:
            # 신고가 도달 - 회복 완료
            if in_drawdown:
                recovery_days = i - drawdown_start_idx
                if recovery_days > max_recovery:
                    max_recovery = recovery_days
                in_drawdown = False
            high_water_mark = nav
        else:
            # 낙폭 중
            if not in_drawdown:
                in_drawdown = True
                drawdown_start_idx = i

    return max_recovery if max_recovery > 0 else None


def calculate_worst_period_return(nav_path: List[Dict], period_days: int) -> Optional[float]:
    """특정 기간의 최악 수익률 계산"""
    if len(nav_path) < period_days:
        return None

    worst_return = 0.0

    for i in range(period_days, len(nav_path)):
        start_nav = nav_path[i - period_days]["nav"]
        end_nav = nav_path[i]["nav"]
        period_return = (end_nav - start_nav) / start_nav * 100
        if period_return < worst_return:
            worst_return = period_return

    return worst_return if worst_return < 0 else None


# ============================================================================
# 통합 시뮬레이션 함수
# ============================================================================

def run_scenario_simulation(
    db: Session,
    scenario_id: str,
    start_date: date,
    end_date: date,
    initial_amount: float = 1000000.0,
    rebalancing_rule: Optional[Dict] = None
) -> Dict:
    """
    시나리오 기반 포트폴리오 시뮬레이션 실행

    Args:
        db: DB 세션
        scenario_id: 시나리오 ID
        start_date: 시작일
        end_date: 종료일
        initial_amount: 초기 투자금액
        rebalancing_rule: 리밸런싱 규칙 (Phase 2, USE_REBALANCING=1 필요)
            {
                "rebalance_type": "PERIODIC"|"DRIFT"|"HYBRID",
                "frequency": "MONTHLY"|"QUARTERLY",
                "drift_threshold": 0.05,
                "cost_rate": 0.001,
                "rule_id": int (optional)
            }

    Returns:
        {
            "scenario_id": str,
            "start_date": date,
            "end_date": date,
            "initial_amount": float,
            "allocations": List[Dict],
            "path": List[Dict],
            "risk_metrics": Dict,
            "historical_observation": Dict,
            "rebalancing_enabled": bool,
            "rebalancing_events_count": int,
            "rebalancing_events": List[Dict] (Phase 2)
        }
    """
    # 1. 포트폴리오 구성비 조회
    allocations = get_portfolio_allocation(db, scenario_id, start_date)
    if not allocations:
        raise ValueError(f"시나리오 '{scenario_id}'의 포트폴리오 구성비가 없습니다.")

    # 2. 거래일 목록 조회
    trade_dates = get_trade_dates(db, start_date, end_date)
    if not trade_dates:
        raise ValueError(f"기간 {start_date} ~ {end_date}의 거래일 데이터가 없습니다.")

    # 3. 종목별 일간수익률 조회
    instrument_ids = [a["instrument_id"] for a in allocations]
    returns_by_instrument = get_daily_returns(db, instrument_ids, start_date, end_date)

    # 4. 리밸런싱 처리 (Phase 2)
    rebalancing_enabled = False
    rebalancing_events = []

    if settings.use_rebalancing and rebalancing_rule:
        # USE_REBALANCING=1 이고 rule이 있을 때만 리밸런싱 적용
        from app.services.rebalancing_engine import (
            RebalancingConfig, calculate_nav_with_rebalancing
        )

        config = RebalancingConfig.from_dict(rebalancing_rule)
        if config.is_enabled():
            rebalancing_enabled = True
            nav_path, events = calculate_nav_with_rebalancing(
                allocations, returns_by_instrument, trade_dates,
                initial_amount, config
            )
            rebalancing_events = [
                {
                    "event_date": e.event_date.isoformat(),
                    "event_order": e.event_order,
                    "trigger_type": e.trigger_type,
                    "trigger_detail": e.trigger_detail,
                    "before_weights": e.before_weights,
                    "after_weights": e.after_weights,
                    "turnover": round(e.turnover, 6),
                    "cost_rate": e.cost_rate,
                    "cost_factor": round(e.cost_factor, 8),
                    "nav_before": round(e.nav_before, 4),
                    "nav_after": round(e.nav_after, 4),
                }
                for e in events
            ]

    elif rebalancing_rule and not settings.use_rebalancing:
        # USE_REBALANCING=0 인데 rule 파라미터가 왔으면 에러 (상세 설계 섹션 13)
        raise ValueError(
            "리밸런싱 기능이 비활성화 상태입니다. "
            "USE_REBALANCING=1로 설정하거나 rebalancing_rule 파라미터를 제거하세요."
        )

    # 5. 리밸런싱 OFF 또는 미적용 시 기존 로직
    if not rebalancing_enabled:
        nav_path = calculate_portfolio_nav(
            allocations, returns_by_instrument, trade_dates, initial_amount
        )

    # 6. 지표 계산
    metrics = calculate_risk_metrics(nav_path, initial_amount)

    # 7. 결과 조합
    result = {
        "scenario_id": scenario_id,
        "start_date": start_date,
        "end_date": end_date,
        "initial_amount": initial_amount,
        "allocations": allocations,
        "path": nav_path,
        "risk_metrics": {
            "max_drawdown": metrics["max_drawdown"],
            "max_recovery_days": metrics["max_recovery_days"],
            "worst_1m_return": metrics["worst_1m_return"],
            "worst_3m_return": metrics["worst_3m_return"],
            "volatility": metrics["volatility"],
        },
        "historical_observation": {
            "total_return": metrics["total_return"],
            "cagr": metrics["cagr"],
            "sharpe_ratio": metrics["sharpe_ratio"],
            "sortino_ratio": metrics["sortino_ratio"],
        },
        "final_value": metrics["final_value"],
        "trading_days": metrics["trading_days"],
        # Phase 2 리밸런싱 정보
        "rebalancing_enabled": rebalancing_enabled,
        "rebalancing_events_count": len(rebalancing_events),
    }

    # 리밸런싱 이벤트 상세 (활성화 시에만)
    if rebalancing_enabled:
        result["rebalancing_events"] = rebalancing_events

    return result


# ============================================================================
# Fallback: 더미 데이터 기반 시뮬레이션 (DB 데이터 없을 때)
# ============================================================================

def run_scenario_simulation_fallback(
    scenario_id: str,
    start_date: date,
    end_date: date,
    initial_amount: float = 1000000.0
) -> Dict:
    """
    DB 데이터 없을 때 더미 시뮬레이션 (테스트/데모용)

    Args:
        scenario_id: 시나리오 ID
        start_date: 시작일
        end_date: 종료일
        initial_amount: 초기 투자금액

    Returns:
        시뮬레이션 결과
    """
    import random

    # 시나리오별 예상 연환산 수익률/변동성 (더미)
    scenario_params = {
        "MIN_VOL": {"annual_return": 0.05, "annual_vol": 0.06},
        "DEFENSIVE": {"annual_return": 0.07, "annual_vol": 0.09},
        "GROWTH": {"annual_return": 0.10, "annual_vol": 0.15},
    }

    params = scenario_params.get(scenario_id, {"annual_return": 0.07, "annual_vol": 0.10})
    daily_return_mean = params["annual_return"] / 252
    daily_return_std = params["annual_vol"] / math.sqrt(252)

    # 거래일 생성 (주말 제외)
    current = start_date
    trade_dates = []
    while current <= end_date:
        if current.weekday() < 5:  # 월~금
            trade_dates.append(current)
        current += timedelta(days=1)

    # NAV 경로 생성
    random.seed(f"{scenario_id}_{start_date}_{end_date}")
    nav = initial_amount
    high_water_mark = initial_amount
    path = []

    for trade_date in trade_dates:
        daily_ret = random.gauss(daily_return_mean, daily_return_std)
        nav = nav * (1 + daily_ret)

        if nav > high_water_mark:
            high_water_mark = nav
        drawdown = (nav - high_water_mark) / high_water_mark
        cumulative_return = (nav - initial_amount) / initial_amount

        path.append({
            "path_date": trade_date,
            "nav": round(nav, 4),
            "daily_return": round(daily_ret, 8),
            "cumulative_return": round(cumulative_return, 8),
            "drawdown": round(drawdown, 8),
            "high_water_mark": round(high_water_mark, 4)
        })

    # 지표 계산
    metrics = calculate_risk_metrics(path, initial_amount)

    return {
        "scenario_id": scenario_id,
        "start_date": start_date,
        "end_date": end_date,
        "initial_amount": initial_amount,
        "allocations": [],  # 더미이므로 빈 값
        "path": path,
        "risk_metrics": {
            "max_drawdown": metrics["max_drawdown"],
            "max_recovery_days": metrics["max_recovery_days"],
            "worst_1m_return": metrics["worst_1m_return"],
            "worst_3m_return": metrics["worst_3m_return"],
            "volatility": metrics["volatility"],
        },
        "historical_observation": {
            "total_return": metrics["total_return"],
            "cagr": metrics["cagr"],
            "sharpe_ratio": metrics["sharpe_ratio"],
            "sortino_ratio": metrics["sortino_ratio"],
        },
        "final_value": metrics["final_value"],
        "trading_days": metrics["trading_days"],
        "_fallback": True,  # 더미 데이터 표시
    }


# ============================================================================
# P2-B7: 리밸런싱 이벤트 DB 저장
# ============================================================================

def save_rebalancing_events(
    db: Session,
    simulation_run_id: int,
    rule_id: int,
    events: List[Dict]
) -> int:
    """
    리밸런싱 이벤트를 DB에 저장 (P2-B7)

    Args:
        db: DB 세션
        simulation_run_id: 시뮬레이션 실행 ID (simulation_run.run_id)
        rule_id: 리밸런싱 규칙 ID
        events: 이벤트 목록 (scenario_simulation에서 생성된 dict 형태)

    Returns:
        저장된 이벤트 수
    """
    if not events:
        return 0

    from app.models.rebalancing import RebalancingEvent
    from datetime import datetime

    saved_count = 0
    for event_dict in events:
        # event_date 파싱 (ISO format string -> date)
        event_date_str = event_dict.get("event_date")
        if isinstance(event_date_str, str):
            event_date = date.fromisoformat(event_date_str)
        else:
            event_date = event_date_str

        # nav_before/after로 cost_amount 계산
        nav_before = event_dict.get("nav_before", 0)
        nav_after = event_dict.get("nav_after", 0)
        cost_amount = nav_before - nav_after if nav_before and nav_after else None

        event = RebalancingEvent(
            simulation_run_id=simulation_run_id,
            rule_id=rule_id,
            event_date=event_date,
            trigger_type=event_dict.get("trigger_type"),
            trigger_detail=event_dict.get("trigger_detail"),
            before_weights=event_dict.get("before_weights", {}),
            after_weights=event_dict.get("after_weights", {}),
            turnover=event_dict.get("turnover", 0),
            cost_rate=event_dict.get("cost_rate", 0),
            cost_amount=cost_amount,
        )
        db.add(event)
        saved_count += 1

    db.flush()  # ID 할당을 위해 flush
    return saved_count


def get_rebalancing_events_by_run(
    db: Session,
    simulation_run_id: int
) -> List[Dict]:
    """
    시뮬레이션 실행에 대한 리밸런싱 이벤트 조회 (P2-B10)

    Args:
        db: DB 세션
        simulation_run_id: 시뮬레이션 실행 ID

    Returns:
        이벤트 목록 (dict 형태)
    """
    from app.models.rebalancing import RebalancingEvent

    events = db.query(RebalancingEvent).filter(
        RebalancingEvent.simulation_run_id == simulation_run_id
    ).order_by(RebalancingEvent.event_date).all()

    return [e.to_dict() for e in events]
