"""
Phase 2 Epic D: 성과 분석 저장/조회 서비스

analysis_result 테이블에 대한 CRUD 및 캐시 로직

**캐시 전략**:
- (run_id, rf_annual, annualization_factor) 기준으로 1:1 캐시
- 존재 시: 재계산 없이 캐시된 결과 반환
- 미존재 시: 계산 후 저장하고 반환

⚠️ 이 모듈은 성과 해석용이며, 투자 추천 로직을 포함하지 않습니다.
"""
import logging
from typing import Dict, List, Optional
from datetime import date

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.analysis import AnalysisResult

logger = logging.getLogger(__name__)
from app.services.performance_analyzer import (
    analyze_from_nav_list,
    PerformanceMetrics,
    compare_metrics,
)


# ============================================================================
# 캐시 조회/저장
# ============================================================================

def get_cached_analysis(
    db: Session,
    simulation_run_id: int,
    rf_annual: float = 0.0,
    annualization_factor: int = 252
) -> Optional[AnalysisResult]:
    """
    캐시된 분석 결과 조회

    Args:
        db: DB 세션
        simulation_run_id: 시뮬레이션 실행 ID
        rf_annual: 무위험 수익률
        annualization_factor: 연율화 계수

    Returns:
        AnalysisResult 또는 None
    """
    return db.query(AnalysisResult).filter(
        AnalysisResult.simulation_run_id == simulation_run_id,
        AnalysisResult.rf_annual == rf_annual,
        AnalysisResult.annualization_factor == annualization_factor,
    ).first()


def save_analysis_result(
    db: Session,
    simulation_run_id: int,
    metrics: PerformanceMetrics,
    rf_annual: float = 0.0,
    annualization_factor: int = 252
) -> AnalysisResult:
    """
    분석 결과 저장

    Args:
        db: DB 세션
        simulation_run_id: 시뮬레이션 실행 ID
        metrics: 성과 지표 객체
        rf_annual: 무위험 수익률
        annualization_factor: 연율화 계수

    Returns:
        저장된 AnalysisResult
    """
    result = AnalysisResult(
        simulation_run_id=simulation_run_id,
        rf_annual=rf_annual,
        annualization_factor=annualization_factor,
        metrics_json=metrics.to_dict(),
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def get_or_compute_analysis(
    db: Session,
    simulation_run_id: int,
    nav_data: Optional[List[Dict]] = None,
    rf_annual: float = 0.0,
    annualization_factor: int = 252
) -> Dict:
    """
    분석 결과 조회 또는 계산

    캐시 히트: 캐시된 결과 반환
    캐시 미스: 계산 후 저장하고 반환

    Args:
        db: DB 세션
        simulation_run_id: 시뮬레이션 실행 ID
        nav_data: NAV 시계열 (캐시 미스 시 필요)
        rf_annual: 무위험 수익률
        annualization_factor: 연율화 계수

    Returns:
        {
            "cache_hit": bool,
            "analysis_id": int,
            "metrics": dict,
            "calculated_at": str
        }
    """
    # 1. 캐시 확인
    cached = get_cached_analysis(
        db, simulation_run_id, rf_annual, annualization_factor
    )

    if cached:
        return {
            "cache_hit": True,
            "analysis_id": cached.analysis_id,
            "simulation_run_id": simulation_run_id,
            "metrics": cached.metrics_json,
            "calculated_at": cached.calculated_at.isoformat() if cached.calculated_at else None,
        }

    # 2. 캐시 미스 - NAV 데이터가 없으면 DB에서 조회
    if nav_data is None:
        nav_data = get_nav_path_by_run_id(db, simulation_run_id)

    if not nav_data:
        raise ValueError(f"시뮬레이션 실행 ID {simulation_run_id}에 대한 NAV 데이터가 없습니다.")

    # 3. 성과 분석 계산
    metrics = analyze_from_nav_list(nav_data, rf_annual, annualization_factor)

    # 4. 결과 저장
    result = save_analysis_result(
        db, simulation_run_id, metrics, rf_annual, annualization_factor
    )

    return {
        "cache_hit": False,
        "analysis_id": result.analysis_id,
        "simulation_run_id": simulation_run_id,
        "metrics": result.metrics_json,
        "calculated_at": result.calculated_at.isoformat() if result.calculated_at else None,
    }


# ============================================================================
# NAV 데이터 조회
# ============================================================================

def get_nav_path_by_run_id(db: Session, simulation_run_id: int) -> List[Dict]:
    """
    시뮬레이션 실행 ID로 NAV 경로 조회

    Args:
        db: DB 세션
        simulation_run_id: 시뮬레이션 실행 ID

    Returns:
        [{"path_date": date, "nav": float}, ...]
    """
    sql = text("""
        SELECT path_date, nav
        FROM simulation_path
        WHERE run_id = :run_id
        ORDER BY path_date ASC
    """)

    result = db.execute(sql, {"run_id": simulation_run_id}).fetchall()

    return [
        {"path_date": row[0], "nav": float(row[1])}
        for row in result
    ]


# ============================================================================
# 리밸런싱 요약 통합 (P2-D3)
# ============================================================================

def get_rebalancing_summary(db: Session, simulation_run_id: int) -> Dict:
    """
    리밸런싱 이벤트 요약 조회 (Epic B 테이블 조인)

    Args:
        db: DB 세션
        simulation_run_id: 시뮬레이션 실행 ID

    Returns:
        {
            "events_count": int,
            "total_turnover": float,
            "total_cost": float
        }
    """
    sql = text("""
        SELECT
            COUNT(*) AS events_count,
            COALESCE(SUM(turnover), 0) AS total_turnover,
            COALESCE(SUM(cost_amount), 0) AS total_cost
        FROM rebalancing_event
        WHERE simulation_run_id = :run_id
    """)

    try:
        result = db.execute(sql, {"run_id": simulation_run_id}).fetchone()

        if result:
            return {
                "events_count": int(result[0]) if result[0] else 0,
                "total_turnover": float(result[1]) if result[1] else 0.0,
                "total_cost": float(result[2]) if result[2] else 0.0,
            }
    except Exception as e:
        # rebalancing_event 테이블이 없는 경우
        logger.debug(f"리밸런싱 요약 조회 실패 (run_id={simulation_run_id}): {e}")

    return {
        "events_count": 0,
        "total_turnover": 0.0,
        "total_cost": 0.0,
    }


def get_analysis_with_rebalancing(
    db: Session,
    simulation_run_id: int,
    rf_annual: float = 0.0,
    annualization_factor: int = 252
) -> Dict:
    """
    성과 분석 + 리밸런싱 요약 통합 조회

    Args:
        db: DB 세션
        simulation_run_id: 시뮬레이션 실행 ID
        rf_annual: 무위험 수익률
        annualization_factor: 연율화 계수

    Returns:
        {
            "performance": {...},
            "rebalancing": {...}
        }
    """
    # 성과 분석
    analysis = get_or_compute_analysis(
        db, simulation_run_id, None, rf_annual, annualization_factor
    )

    # 리밸런싱 요약
    rebalancing = get_rebalancing_summary(db, simulation_run_id)

    return {
        "simulation_run_id": simulation_run_id,
        "performance": analysis,
        "rebalancing": rebalancing,
    }


# ============================================================================
# 비교 분석 (P2-D5)
# ============================================================================

def compare_runs(
    db: Session,
    run_id_1: int,
    run_id_2: int,
    rf_annual: float = 0.0,
    annualization_factor: int = 252
) -> Dict:
    """
    두 시뮬레이션 실행 결과 비교

    ⚠️ 단순 수치 비교만 제공하며, 어느 쪽이 "더 좋다"는 판단을 하지 않습니다.

    Args:
        db: DB 세션
        run_id_1: 첫 번째 시뮬레이션 실행 ID
        run_id_2: 두 번째 시뮬레이션 실행 ID
        rf_annual: 무위험 수익률
        annualization_factor: 연율화 계수

    Returns:
        비교 결과 dict
    """
    # 각각 분석 결과 조회
    analysis_1 = get_or_compute_analysis(
        db, run_id_1, None, rf_annual, annualization_factor
    )
    analysis_2 = get_or_compute_analysis(
        db, run_id_2, None, rf_annual, annualization_factor
    )

    # PerformanceMetrics로 변환
    metrics_1 = PerformanceMetrics.from_dict(analysis_1["metrics"])
    metrics_2 = PerformanceMetrics.from_dict(analysis_2["metrics"])

    # 비교
    comparison = compare_metrics(metrics_1, metrics_2)

    # 리밸런싱 요약도 포함
    rebal_1 = get_rebalancing_summary(db, run_id_1)
    rebal_2 = get_rebalancing_summary(db, run_id_2)

    return {
        "run_id_1": run_id_1,
        "run_id_2": run_id_2,
        "analysis_1": analysis_1,
        "analysis_2": analysis_2,
        "comparison": comparison,
        "rebalancing_1": rebal_1,
        "rebalancing_2": rebal_2,
        "note": "단순 수치 비교를 제공합니다. 과거 성과가 미래 수익을 보장하지 않습니다.",
    }
