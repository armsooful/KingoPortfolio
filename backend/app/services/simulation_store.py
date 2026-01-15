"""
Phase 1 시뮬레이션 결과 저장 서비스

sim_run/sim_path/sim_summary 구조로 결과를 저장하고 조회
기존 simulation_cache.py의 JSON 저장 방식을 대체
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Optional, Any, Dict, List, Tuple

from sqlalchemy.orm import Session

from app.models.simulation import SimulationRun, SimulationPath, SimulationSummary
from app.config import settings

logger = logging.getLogger(__name__)


def get_engine_version() -> str:
    """현재 시뮬레이션 엔진 버전 반환"""
    return settings.engine_version


def canonicalize_request(request_data: Dict[str, Any]) -> str:
    """
    요청 데이터를 정규화하여 일관된 해시를 생성

    - 키를 정렬
    - 불필요한 필드 제거
    - JSON 문자열로 변환
    """
    def sort_dict(d):
        if isinstance(d, dict):
            return {k: sort_dict(v) for k, v in sorted(d.items())}
        elif isinstance(d, list):
            return [sort_dict(item) for item in d]
        else:
            return d

    # 캐시에 영향을 주지 않아야 하는 필드 제거
    excluded_keys = {'timestamp', 'request_id', 'user_id'}
    filtered_data = {k: v for k, v in request_data.items() if k not in excluded_keys}

    sorted_data = sort_dict(filtered_data)
    return json.dumps(sorted_data, ensure_ascii=False, separators=(',', ':'))


def generate_request_hash(request_type: str, request_data: Dict[str, Any]) -> str:
    """
    요청에 대한 SHA-256 해시 생성

    Args:
        request_type: 요청 유형 (backtest, compare 등)
        request_data: 요청 파라미터

    Returns:
        64자리 SHA-256 해시 문자열
    """
    canonical = canonicalize_request(request_data)
    hash_input = f"{request_type}:{canonical}"
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()


def get_cached_simulation(
    db: Session,
    request_hash: str
) -> Optional[Tuple[SimulationRun, SimulationSummary]]:
    """
    캐시된 시뮬레이션 결과 조회

    Args:
        db: DB 세션
        request_hash: 요청 해시

    Returns:
        (SimulationRun, SimulationSummary) 튜플 또는 None
    """
    run = db.query(SimulationRun).filter(
        SimulationRun.request_hash == request_hash
    ).first()

    if not run:
        logger.info(f"Cache MISS for hash {request_hash[:8]}...")
        return None

    # 만료 확인
    if run.expires_at and run.expires_at < datetime.utcnow():
        logger.info(f"Cache expired for hash {request_hash[:8]}...")
        db.delete(run)  # cascade로 summary, paths도 삭제됨
        db.commit()
        return None

    # 요약 지표 조회
    summary = run.summary
    if not summary:
        logger.warning(f"No summary found for run {run.run_id}")
        return None

    logger.info(f"Cache HIT for hash {request_hash[:8]}... (engine: {run.engine_version})")
    return run, summary


def save_simulation_result(
    db: Session,
    request_hash: str,
    request_type: str,
    request_params: Dict[str, Any],
    backtest_result: Dict[str, Any],
    engine_version: str,
    scenario_id: Optional[str] = None,
    user_id: Optional[int] = None,
    ttl_days: Optional[int] = 7
) -> SimulationRun:
    """
    시뮬레이션 결과를 sim_run/sim_path/sim_summary 구조로 저장

    Args:
        db: DB 세션
        request_hash: 요청 해시
        request_type: 요청 유형
        request_params: 원본 요청 파라미터
        backtest_result: 백테스트 결과 (BacktestingEngine.run_backtest() 반환값)
        engine_version: 엔진 버전
        scenario_id: 시나리오 ID (선택)
        user_id: 사용자 ID (선택)
        ttl_days: 캐시 유효 기간

    Returns:
        생성된 SimulationRun
    """
    expires_at = None
    if ttl_days:
        expires_at = datetime.utcnow() + timedelta(days=ttl_days)

    # 날짜 파싱
    start_date = _parse_date(backtest_result.get("start_date"))
    end_date = _parse_date(backtest_result.get("end_date"))

    # 1. SimulationRun 생성
    run = SimulationRun(
        request_hash=request_hash,
        scenario_id=scenario_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        initial_amount=Decimal(str(backtest_result.get("initial_investment", 0))),
        rebalance_freq=backtest_result.get("rebalance_frequency", "NONE").upper(),
        request_params=request_params,
        engine_version=engine_version,
        run_status="COMPLETED",
        expires_at=expires_at
    )
    db.add(run)
    db.flush()  # run_id 확보

    # 2. SimulationSummary 생성
    risk_metrics = backtest_result.get("risk_metrics", {})
    historical = backtest_result.get("historical_observation", {})

    summary = SimulationSummary(
        run_id=run.run_id,
        # 손실/회복 지표
        max_drawdown=Decimal(str(risk_metrics.get("max_drawdown", 0))),
        max_recovery_days=risk_metrics.get("max_recovery_days"),
        worst_1m_return=_to_decimal(risk_metrics.get("worst_1m_return")),
        worst_3m_return=_to_decimal(risk_metrics.get("worst_3m_return")),
        volatility=_to_decimal(risk_metrics.get("volatility")),
        # 과거 수익률
        total_return=Decimal(str(historical.get("total_return", backtest_result.get("total_return", 0)))),
        cagr=_to_decimal(historical.get("cagr", backtest_result.get("annualized_return"))),
        sharpe_ratio=_to_decimal(historical.get("sharpe_ratio", backtest_result.get("sharpe_ratio"))),
        # 기타
        final_value=_to_decimal(backtest_result.get("final_value")),
        trading_days=len(backtest_result.get("daily_values", [])),
        rebalance_count=backtest_result.get("number_of_rebalances", 0)
    )
    db.add(summary)

    # 3. SimulationPath 생성 (일별 경로)
    daily_values = backtest_result.get("daily_values", [])
    initial_value = backtest_result.get("initial_investment", 0)
    high_water_mark = initial_value
    prev_value = initial_value

    paths = []
    for i, dv in enumerate(daily_values):
        nav = dv.get("value", 0)
        path_date = _parse_date(dv.get("date"))

        # 일간 수익률
        daily_return = None
        if i > 0 and prev_value > 0:
            daily_return = (nav - prev_value) / prev_value

        # 누적 수익률
        cumulative_return = (nav - initial_value) / initial_value if initial_value > 0 else 0

        # 고점 및 낙폭
        if nav > high_water_mark:
            high_water_mark = nav
        drawdown = (nav - high_water_mark) / high_water_mark if high_water_mark > 0 else 0

        path = SimulationPath(
            run_id=run.run_id,
            path_date=path_date,
            nav=Decimal(str(nav)),
            daily_return=_to_decimal(daily_return),
            cumulative_return=_to_decimal(cumulative_return),
            drawdown=_to_decimal(drawdown),
            high_water_mark=Decimal(str(high_water_mark))
        )
        paths.append(path)
        prev_value = nav

    db.bulk_save_objects(paths)
    db.commit()
    db.refresh(run)

    logger.info(f"Saved simulation run={run.run_id} hash={request_hash[:8]}... paths={len(paths)}")
    return run


def get_or_compute_simulation(
    db: Session,
    request_type: str,
    request_params: Dict[str, Any],
    compute_fn: callable,
    scenario_id: Optional[str] = None,
    user_id: Optional[int] = None,
    ttl_days: Optional[int] = 7
) -> Tuple[Dict[str, Any], str, bool, str]:
    """
    캐시에서 결과를 조회하거나, 없으면 계산 후 저장

    Args:
        db: DB 세션
        request_type: 요청 유형
        request_params: 요청 파라미터
        compute_fn: 결과를 계산하는 함수
        scenario_id: 시나리오 ID
        user_id: 사용자 ID
        ttl_days: 캐시 유효 기간

    Returns:
        (결과 데이터, request_hash, cache_hit 여부, engine_version) 튜플
    """
    request_hash = generate_request_hash(request_type, request_params)
    current_engine_version = get_engine_version()

    # 캐시 조회
    cached = get_cached_simulation(db, request_hash)
    if cached is not None:
        run, summary = cached
        # DB에서 결과를 재구성하여 반환
        result = _reconstruct_result(db, run, summary)
        return result, request_hash, True, run.engine_version

    # 결과 계산
    result = compute_fn()

    # sim_* 구조로 저장
    try:
        save_simulation_result(
            db=db,
            request_hash=request_hash,
            request_type=request_type,
            request_params=request_params,
            backtest_result=result,
            engine_version=current_engine_version,
            scenario_id=scenario_id,
            user_id=user_id,
            ttl_days=ttl_days
        )
    except Exception as e:
        logger.warning(f"Failed to save simulation result: {e}")

    return result, request_hash, False, current_engine_version


def _reconstruct_result(
    db: Session,
    run: SimulationRun,
    summary: SimulationSummary
) -> Dict[str, Any]:
    """DB에 저장된 결과를 기존 API 응답 형식으로 재구성"""

    # 경로 데이터 조회
    paths = db.query(SimulationPath).filter(
        SimulationPath.run_id == run.run_id
    ).order_by(SimulationPath.path_date).all()

    daily_values = [
        {
            "date": p.path_date.isoformat() if p.path_date else None,
            "value": float(p.nav) if p.nav else 0,
            "return": float(p.cumulative_return * 100) if p.cumulative_return else 0
        }
        for p in paths
    ]

    return {
        "start_date": run.start_date.isoformat() if run.start_date else None,
        "end_date": run.end_date.isoformat() if run.end_date else None,
        "initial_investment": float(run.initial_amount) if run.initial_amount else 0,
        "final_value": float(summary.final_value) if summary.final_value else 0,
        # B-1: 손실/회복 지표 (최상위)
        "risk_metrics": summary.to_risk_metrics(),
        # 과거 관측치
        "historical_observation": summary.to_historical_observation(),
        # 레거시 호환성
        "total_return": float(summary.total_return) if summary.total_return else 0,
        "annualized_return": float(summary.cagr) if summary.cagr else 0,
        "volatility": float(summary.volatility) if summary.volatility else 0,
        "sharpe_ratio": float(summary.sharpe_ratio) if summary.sharpe_ratio else 0,
        "max_drawdown": float(summary.max_drawdown) if summary.max_drawdown else 0,
        "daily_values": daily_values,
        "rebalance_frequency": run.rebalance_freq.lower() if run.rebalance_freq else "none",
        "number_of_rebalances": summary.rebalance_count or 0
    }


def _parse_date(date_str: Any) -> Optional[date]:
    """날짜 문자열을 date 객체로 변환"""
    if date_str is None:
        return None
    if isinstance(date_str, date):
        return date_str
    if isinstance(date_str, datetime):
        return date_str.date()
    if isinstance(date_str, str):
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
        except ValueError:
            return None
    return None


def _to_decimal(value: Any) -> Optional[Decimal]:
    """값을 Decimal로 변환 (None 허용)"""
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except:
        return None


def cleanup_expired_simulations(db: Session) -> int:
    """
    만료된 시뮬레이션 결과 삭제

    Returns:
        삭제된 run 수
    """
    deleted = db.query(SimulationRun).filter(
        SimulationRun.expires_at < datetime.utcnow()
    ).delete()
    db.commit()

    if deleted > 0:
        logger.info(f"Cleaned up {deleted} expired simulation runs")

    return deleted


def get_simulation_by_hash(db: Session, request_hash: str) -> Optional[Dict[str, Any]]:
    """
    request_hash로 시뮬레이션 결과 조회

    Returns:
        시뮬레이션 결과 dict 또는 None
    """
    cached = get_cached_simulation(db, request_hash)
    if cached is None:
        return None

    run, summary = cached
    return _reconstruct_result(db, run, summary)
