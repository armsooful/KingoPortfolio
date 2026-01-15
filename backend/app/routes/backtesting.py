"""
백테스팅 API 엔드포인트

Phase 1: 시나리오 기반 포트폴리오 시뮬레이션 지원
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from typing import Optional, List
from pydantic import BaseModel, Field

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.services.backtesting import BacktestingEngine, run_simple_backtest
from app.services.portfolio_engine import create_default_portfolio
from app.services.simulation_cache import get_or_compute, generate_request_hash, get_engine_version
from app.services.simulation_store import (
    get_or_compute_simulation,
    generate_request_hash as generate_hash_v2,
    get_engine_version as get_engine_version_v2
)
from app.services.scenario_simulation import (
    run_scenario_simulation,
    run_scenario_simulation_fallback
)
from app.rate_limiter import limiter, RateLimits
from app.config import settings

# Feature flag: sim_* 구조 사용 여부 (Phase 1)
USE_SIM_STORE = settings.use_sim_store
USE_SCENARIO_DB = settings.use_scenario_db

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/backtest", tags=["Backtesting"])


class BacktestRequest(BaseModel):
    """백테스트 요청"""
    investment_type: Optional[str] = Field(None, description="투자 성향 (conservative, moderate, aggressive)")
    portfolio: Optional[dict] = Field(None, description="백테스트할 포트폴리오 (allocation, securities)")
    investment_amount: int = Field(..., ge=100000, description="투자 금액 (최소 10만원)")
    period_years: int = Field(1, ge=1, le=10, description="백테스트 기간 (년, 1-10)")
    rebalance_frequency: str = Field("quarterly", description="리밸런싱 주기 (monthly, quarterly, yearly, none)")


class ComparePortfoliosRequest(BaseModel):
    """포트폴리오 비교 요청"""
    investment_types: list[str] = Field(..., description="비교할 투자 성향 리스트")
    investment_amount: int = Field(..., ge=100000, description="투자 금액")
    period_years: int = Field(1, ge=1, le=10, description="백테스트 기간 (년)")


@router.post("/run")
@limiter.limit(RateLimits.AI_ANALYSIS)  # AI 분석으로 간주, 시간당 5회 제한
async def run_backtest(
    request: Request,
    backtest_request: BacktestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    포트폴리오 백테스트 실행

    과거 데이터를 기반으로 포트폴리오의 성과를 시뮬레이션합니다.

    두 가지 모드:
    1. **간편 모드**: investment_type만 제공 → 기본 포트폴리오로 백테스트
    2. **정확 모드**: portfolio 데이터 제공 → 실제 사용자 포트폴리오로 백테스트

    **Rate Limit**: 시간당 5회
    **캐싱**: 동일 요청은 캐시된 결과 반환 (request_hash로 추적)
    """
    try:
        # 포트폴리오 데이터 또는 투자 성향 중 하나는 필수
        if not backtest_request.portfolio and not backtest_request.investment_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'portfolio' or 'investment_type' must be provided"
            )

        # 캐시용 요청 파라미터 구성
        cache_params = {
            "investment_type": backtest_request.investment_type,
            "portfolio": backtest_request.portfolio,
            "investment_amount": backtest_request.investment_amount,
            "period_years": backtest_request.period_years,
            "rebalance_frequency": backtest_request.rebalance_frequency
        }

        # 정확 모드: 실제 포트폴리오 백테스트
        if backtest_request.portfolio:
            def compute_portfolio_backtest():
                end_date = datetime.now()
                start_date = end_date - timedelta(days=backtest_request.period_years * 365)

                engine = BacktestingEngine(db)
                return engine.run_backtest(
                    portfolio=backtest_request.portfolio,
                    start_date=start_date,
                    end_date=end_date,
                    initial_investment=backtest_request.investment_amount,
                    rebalance_frequency=backtest_request.rebalance_frequency
                )

            # Phase 1: sim_* 구조 사용 (PostgreSQL)
            if USE_SIM_STORE:
                result, request_hash, cache_hit, engine_version = get_or_compute_simulation(
                    db=db,
                    request_type="backtest_portfolio",
                    request_params=cache_params,
                    compute_fn=compute_portfolio_backtest,
                    user_id=current_user.id if current_user else None,
                    ttl_days=7
                )
            else:
                # Legacy: JSON 캐시 (SQLite)
                result, request_hash, cache_hit, engine_version = get_or_compute(
                    db=db,
                    request_type="backtest_portfolio",
                    request_params=cache_params,
                    compute_fn=compute_portfolio_backtest,
                    ttl_days=7
                )

            logger.info(f"Backtest portfolio - hash: {request_hash[:8]}..., cache_hit: {cache_hit}, engine: {engine_version}, store: {'sim' if USE_SIM_STORE else 'json'}")

            return {
                "success": True,
                "data": result,
                "request_hash": request_hash,
                "cache_hit": cache_hit,
                "engine_version": engine_version,
                "message": f"사용자 포트폴리오 {backtest_request.period_years}년 백테스트 완료"
            }

        # 간편 모드: 투자 성향으로 기본 포트폴리오 백테스트
        else:
            # 투자 성향 검증
            if backtest_request.investment_type not in ["conservative", "moderate", "aggressive"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid investment type. Must be one of: conservative, moderate, aggressive"
                )

            def compute_simple_backtest():
                return run_simple_backtest(
                    investment_type=backtest_request.investment_type,
                    investment_amount=backtest_request.investment_amount,
                    period_years=backtest_request.period_years,
                    db=db
                )

            # Phase 1: sim_* 구조 사용 (PostgreSQL)
            if USE_SIM_STORE:
                result, request_hash, cache_hit, engine_version = get_or_compute_simulation(
                    db=db,
                    request_type="backtest_simple",
                    request_params=cache_params,
                    compute_fn=compute_simple_backtest,
                    user_id=current_user.id if current_user else None,
                    ttl_days=7
                )
            else:
                # Legacy: JSON 캐시 (SQLite)
                result, request_hash, cache_hit, engine_version = get_or_compute(
                    db=db,
                    request_type="backtest_simple",
                    request_params=cache_params,
                    compute_fn=compute_simple_backtest,
                    ttl_days=7
                )

            logger.info(f"Backtest simple - hash: {request_hash[:8]}..., cache_hit: {cache_hit}, engine: {engine_version}, store: {'sim' if USE_SIM_STORE else 'json'}")

            return {
                "success": True,
                "data": result,
                "request_hash": request_hash,
                "cache_hit": cache_hit,
                "engine_version": engine_version,
                "message": f"{backtest_request.period_years}년 백테스트 완료"
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backtest failed: {str(e)}"
        )


@router.post("/compare")
@limiter.limit(RateLimits.AI_ANALYSIS)  # 시간당 5회 제한
async def compare_portfolios(
    request: Request,
    compare_request: ComparePortfoliosRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    여러 투자 성향의 포트폴리오 비교

    다양한 투자 성향의 포트폴리오를 백테스트하여 비교합니다.

    **Rate Limit**: 시간당 5회
    **캐싱**: 동일 요청은 캐시된 결과 반환 (request_hash로 추적)
    """
    try:
        # 투자 성향 검증
        valid_types = ["conservative", "moderate", "aggressive"]
        for inv_type in compare_request.investment_types:
            if inv_type not in valid_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid investment type: {inv_type}"
                )

        # 캐시용 요청 파라미터 구성
        cache_params = {
            "investment_types": sorted(compare_request.investment_types),  # 정렬하여 순서 무관하게 동일 해시
            "investment_amount": compare_request.investment_amount,
            "period_years": compare_request.period_years
        }

        def compute_comparison():
            end_date = datetime.now()
            start_date = end_date - timedelta(days=compare_request.period_years * 365)

            # 각 투자 성향별 포트폴리오 생성
            portfolios = []
            for inv_type in compare_request.investment_types:
                portfolio = create_default_portfolio(
                    db=db,
                    investment_type=inv_type,
                    investment_amount=compare_request.investment_amount
                )
                portfolio["name"] = {
                    "conservative": "안정형",
                    "moderate": "중립형",
                    "aggressive": "공격형"
                }.get(inv_type, inv_type)
                portfolios.append(portfolio)

            # 백테스팅 엔진으로 비교
            engine = BacktestingEngine(db)
            comparison_result = engine.compare_portfolios(
                portfolios=[p["portfolio"] for p in portfolios],
                start_date=start_date,
                end_date=end_date,
                initial_investment=compare_request.investment_amount
            )

            # 포트폴리오 이름 추가
            for i, result in enumerate(comparison_result["comparison"]):
                result["portfolio_name"] = portfolios[i]["name"]

            return comparison_result

        # Note: compare는 단일 시뮬레이션이 아니므로 기존 JSON 캐시 사용
        # Phase 1에서는 개별 백테스트만 sim_* 구조로 저장
        result, request_hash, cache_hit, engine_version = get_or_compute(
            db=db,
            request_type="backtest_compare",
            request_params=cache_params,
            compute_fn=compute_comparison,
            ttl_days=7
        )

        logger.info(f"Backtest compare - hash: {request_hash[:8]}..., cache_hit: {cache_hit}, engine: {engine_version}")

        return {
            "success": True,
            "data": result,
            "request_hash": request_hash,
            "cache_hit": cache_hit,
            "engine_version": engine_version,
            "message": f"{len(compare_request.investment_types)}개 포트폴리오 비교 완료"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Comparison failed: {str(e)}"
        )


@router.get("/metrics/{investment_type}")
async def get_backtest_metrics(
    investment_type: str,
    period_years: int = Query(1, ge=1, le=10),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    투자 성향별 과거 성과 지표 조회

    특정 투자 성향의 과거 성과 지표를 간단히 조회합니다.
    """
    try:
        if investment_type not in ["conservative", "moderate", "aggressive"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid investment type"
            )

        # 간단한 백테스트 실행 (기본 금액 1000만원)
        result = run_simple_backtest(
            investment_type=investment_type,
            investment_amount=10000000,
            period_years=period_years,
            db=db
        )

        # B-1: 손실/회복 지표를 top-level로, 수익률 지표는 historical_observation으로
        return {
            "investment_type": investment_type,
            "period_years": period_years,
            "engine_version": get_engine_version(),
            # 손실/회복 지표 (top-level) - Foresto 핵심 KPI
            "risk_metrics": result["risk_metrics"],
            # 과거 관측치 (historical_observation)
            "historical_observation": result["historical_observation"]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}"
        )


# ============================================================================
# Phase 1: 시나리오 기반 시뮬레이션 (P1-D1)
# ============================================================================

class ScenarioSimulationRequest(BaseModel):
    """시나리오 시뮬레이션 요청"""
    scenario_id: str = Field(..., description="시나리오 ID (MIN_VOL, DEFENSIVE, GROWTH)")
    start_date: str = Field(..., description="시작일 (YYYY-MM-DD)")
    end_date: str = Field(..., description="종료일 (YYYY-MM-DD)")
    initial_amount: float = Field(1000000.0, ge=100000, description="초기 투자금액 (최소 10만원)")


class ScenarioSimulationResponse(BaseModel):
    """시나리오 시뮬레이션 응답"""
    success: bool
    scenario_id: str
    start_date: str
    end_date: str
    initial_amount: float
    final_value: float
    trading_days: int
    risk_metrics: dict
    historical_observation: dict
    allocations: List[dict]
    path_summary: dict  # 전체 경로 대신 요약 정보
    engine_version: str
    cache_hit: bool
    request_hash: str
    message: str


@router.post("/scenario", response_model=ScenarioSimulationResponse)
@limiter.limit(RateLimits.AI_ANALYSIS)
async def run_scenario_backtest(
    request: Request,
    sim_request: ScenarioSimulationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    시나리오 기반 포트폴리오 시뮬레이션 (Phase 1)

    DB에 저장된 포트폴리오 구성비와 일간수익률을 사용하여
    NAV 경로를 계산하고 손실/회복 지표를 산출합니다.

    **시나리오**:
    - MIN_VOL: 변동성 최소화
    - DEFENSIVE: 방어형
    - GROWTH: 성장형

    **Rate Limit**: 시간당 5회
    **캐싱**: 동일 요청은 캐시된 결과 반환

    ⚠️ 본 시뮬레이션은 교육 목적이며, 미래 수익을 보장하지 않습니다.
    """
    try:
        # 날짜 파싱
        try:
            start_date = datetime.strptime(sim_request.start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(sim_request.end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용하세요."
            )

        if end_date <= start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="종료일은 시작일보다 커야 합니다."
            )

        # 시나리오 ID 검증
        scenario_id = sim_request.scenario_id.upper()
        valid_scenarios = ["MIN_VOL", "DEFENSIVE", "GROWTH"]
        if scenario_id not in valid_scenarios:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"유효하지 않은 시나리오입니다. 가능한 값: {valid_scenarios}"
            )

        # 캐시 파라미터
        cache_params = {
            "scenario_id": scenario_id,
            "start_date": sim_request.start_date,
            "end_date": sim_request.end_date,
            "initial_amount": sim_request.initial_amount
        }

        def compute_scenario_simulation():
            """시나리오 시뮬레이션 계산 함수"""
            if USE_SCENARIO_DB:
                try:
                    return run_scenario_simulation(
                        db=db,
                        scenario_id=scenario_id,
                        start_date=start_date,
                        end_date=end_date,
                        initial_amount=sim_request.initial_amount
                    )
                except Exception as e:
                    logger.warning(f"DB 시뮬레이션 실패, 폴백 사용: {e}")
                    return run_scenario_simulation_fallback(
                        scenario_id=scenario_id,
                        start_date=start_date,
                        end_date=end_date,
                        initial_amount=sim_request.initial_amount
                    )
            else:
                # DB 기능 비활성화 시 폴백 사용
                return run_scenario_simulation_fallback(
                    scenario_id=scenario_id,
                    start_date=start_date,
                    end_date=end_date,
                    initial_amount=sim_request.initial_amount
                )

        # 캐시 조회 또는 계산
        if USE_SIM_STORE:
            result, request_hash, cache_hit, engine_version = get_or_compute_simulation(
                db=db,
                request_type="scenario_simulation",
                request_params=cache_params,
                compute_fn=compute_scenario_simulation,
                user_id=current_user.id if current_user else None,
                ttl_days=7
            )
        else:
            result, request_hash, cache_hit, engine_version = get_or_compute(
                db=db,
                request_type="scenario_simulation",
                request_params=cache_params,
                compute_fn=compute_scenario_simulation,
                ttl_days=7
            )

        logger.info(f"Scenario simulation - scenario: {scenario_id}, hash: {request_hash[:8]}..., cache_hit: {cache_hit}")

        # 경로 요약 (전체 경로는 용량이 크므로 요약만 반환)
        path = result.get("path", [])
        path_summary = {
            "total_points": len(path),
            "first_date": path[0]["path_date"].isoformat() if path else None,
            "last_date": path[-1]["path_date"].isoformat() if path else None,
            "first_nav": path[0]["nav"] if path else None,
            "last_nav": path[-1]["nav"] if path else None,
        }

        return ScenarioSimulationResponse(
            success=True,
            scenario_id=scenario_id,
            start_date=sim_request.start_date,
            end_date=sim_request.end_date,
            initial_amount=sim_request.initial_amount,
            final_value=result.get("final_value", sim_request.initial_amount),
            trading_days=result.get("trading_days", 0),
            risk_metrics=result.get("risk_metrics", {}),
            historical_observation=result.get("historical_observation", {}),
            allocations=result.get("allocations", []),
            path_summary=path_summary,
            engine_version=engine_version,
            cache_hit=cache_hit,
            request_hash=request_hash,
            message=f"{scenario_id} 시나리오 시뮬레이션 완료"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scenario simulation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"시뮬레이션 실패: {str(e)}"
        )


@router.get("/scenario/{scenario_id}/path")
@limiter.limit(RateLimits.DATA_READ)
async def get_scenario_path(
    request: Request,
    scenario_id: str,
    start_date: str = Query(..., description="시작일 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="종료일 (YYYY-MM-DD)"),
    initial_amount: float = Query(1000000.0, ge=100000),
    db: Session = Depends(get_db)
):
    """
    시나리오 시뮬레이션 NAV 경로 조회

    일별 NAV, 누적수익률, 낙폭 데이터를 반환합니다.
    차트 렌더링용 데이터입니다.

    **Rate Limit**: 분당 30회
    """
    try:
        # 날짜 파싱
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="날짜 형식이 올바르지 않습니다."
            )

        scenario_id = scenario_id.upper()

        # 시뮬레이션 실행
        if USE_SCENARIO_DB:
            try:
                result = run_scenario_simulation(
                    db=db,
                    scenario_id=scenario_id,
                    start_date=start,
                    end_date=end,
                    initial_amount=initial_amount
                )
            except Exception as e:
                logger.warning(f"DB 조회 실패, 폴백 사용: {e}")
                result = run_scenario_simulation_fallback(
                    scenario_id=scenario_id,
                    start_date=start,
                    end_date=end,
                    initial_amount=initial_amount
                )
        else:
            result = run_scenario_simulation_fallback(
                scenario_id=scenario_id,
                start_date=start,
                end_date=end,
                initial_amount=initial_amount
            )

        # 경로 데이터 직렬화
        path = result.get("path", [])
        serialized_path = [
            {
                "date": p["path_date"].isoformat() if isinstance(p["path_date"], date) else p["path_date"],
                "nav": p["nav"],
                "daily_return": p["daily_return"],
                "cumulative_return": p["cumulative_return"],
                "drawdown": p["drawdown"]
            }
            for p in path
        ]

        return {
            "success": True,
            "scenario_id": scenario_id,
            "path": serialized_path,
            "trading_days": len(serialized_path)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"경로 조회 실패: {str(e)}"
        )
