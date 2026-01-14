"""
백테스팅 API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, Field

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.services.backtesting import BacktestingEngine, run_simple_backtest
from app.services.portfolio_engine import create_default_portfolio
from app.rate_limiter import limiter, RateLimits


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
    """
    try:
        # 포트폴리오 데이터 또는 투자 성향 중 하나는 필수
        if not backtest_request.portfolio and not backtest_request.investment_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'portfolio' or 'investment_type' must be provided"
            )

        # 정확 모드: 실제 포트폴리오 백테스트
        if backtest_request.portfolio:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=backtest_request.period_years * 365)

            engine = BacktestingEngine(db)
            result = engine.run_backtest(
                portfolio=backtest_request.portfolio,
                start_date=start_date,
                end_date=end_date,
                initial_investment=backtest_request.investment_amount,
                rebalance_frequency=backtest_request.rebalance_frequency
            )

            return {
                "success": True,
                "data": result,
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

            # 백테스트 실행
            result = run_simple_backtest(
                investment_type=backtest_request.investment_type,
                investment_amount=backtest_request.investment_amount,
                period_years=backtest_request.period_years,
                db=db
            )

            return {
                "success": True,
                "data": result,
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

        # 백테스트 기간 설정
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

        return {
            "success": True,
            "data": comparison_result,
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
