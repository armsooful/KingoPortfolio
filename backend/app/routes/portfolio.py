"""
포트폴리오 추천 API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.schemas import PortfolioGenerateRequest, PortfolioResponse, MessageResponse
from app.services.portfolio_engine import PortfolioEngine, create_default_portfolio, create_custom_portfolio
from app.rate_limiter import limiter, RateLimits
from typing import Optional

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


@router.post("/generate", response_model=PortfolioResponse)
@limiter.limit(RateLimits.DIAGNOSIS_SUBMIT)  # 포트폴리오 생성도 시간당 10회 제한
async def generate_portfolio(
    request: Request,
    portfolio_request: PortfolioGenerateRequest,
    diagnosis_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    맞춤형 포트폴리오 생성

    투자 성향과 선호도를 기반으로 포트폴리오를 추천합니다.
    진단 ID를 제공하면 해당 진단 결과의 투자 성향을 사용합니다.

    **Rate Limit**: 시간당 10회
    """
    try:
        # 진단 ID가 제공된 경우 진단 결과 조회
        investment_type = None
        if diagnosis_id:
            from app.models import Diagnosis

            diagnosis = db.query(Diagnosis).filter(
                and_(
                    Diagnosis.id == diagnosis_id,
                    Diagnosis.user_id == current_user.id
                )
            ).first()

            if not diagnosis:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Diagnosis not found"
                )

            investment_type = diagnosis.investment_type
        else:
            # 진단 ID가 없으면 최신 진단 결과 사용
            from app.models import Diagnosis

            latest_diagnosis = db.query(Diagnosis).filter(
                Diagnosis.user_id == current_user.id
            ).order_by(Diagnosis.created_at.desc()).first()

            if not latest_diagnosis:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No diagnosis found. Please complete diagnosis first."
                )

            investment_type = latest_diagnosis.investment_type

        # 포트폴리오 생성
        if portfolio_request.risk_tolerance or portfolio_request.sector_preferences or portfolio_request.dividend_preference:
            # 맞춤형 포트폴리오
            portfolio = create_custom_portfolio(
                db=db,
                investment_type=investment_type,
                investment_amount=portfolio_request.investment_amount,
                risk_tolerance=portfolio_request.risk_tolerance,
                sector_preferences=portfolio_request.sector_preferences,
                dividend_preference=portfolio_request.dividend_preference
            )
        else:
            # 기본 포트폴리오
            portfolio = create_default_portfolio(
                db=db,
                investment_type=investment_type,
                investment_amount=portfolio_request.investment_amount
            )

        return portfolio

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Portfolio generation failed: {str(e)}"
        )


@router.post("/rebalance/{diagnosis_id}", response_model=PortfolioResponse)
@limiter.limit(RateLimits.DIAGNOSIS_READ)  # 리밸런싱은 시간당 100회
async def rebalance_portfolio(
    request: Request,
    diagnosis_id: str,
    investment_amount: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    기존 포트폴리오 리밸런싱

    기존 진단 결과를 기반으로 새로운 투자 금액에 맞춰 포트폴리오를 재조정합니다.

    **Rate Limit**: 시간당 100회
    """
    try:
        from app.models import Diagnosis

        # 진단 결과 조회
        diagnosis = db.query(Diagnosis).filter(
            and_(
                Diagnosis.id == diagnosis_id,
                Diagnosis.user_id == current_user.id
            )
        ).first()

        if not diagnosis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Diagnosis not found"
            )

        # 포트폴리오 재생성
        portfolio = create_default_portfolio(
            db=db,
            investment_type=diagnosis.investment_type,
            investment_amount=investment_amount
        )

        return portfolio

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Portfolio rebalancing failed: {str(e)}"
        )


@router.get("/asset-allocation/{investment_type}")
async def get_asset_allocation_strategy(
    investment_type: str,
    current_user: User = Depends(get_current_user)
):
    """
    투자 성향별 자산 배분 전략 조회

    각 투자 성향(conservative, moderate, aggressive)에 대한
    권장 자산 배분 비율을 확인할 수 있습니다.
    """
    if investment_type not in PortfolioEngine.ASSET_ALLOCATION_STRATEGIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid investment type: {investment_type}. Must be one of: conservative, moderate, aggressive"
        )

    strategy = PortfolioEngine.ASSET_ALLOCATION_STRATEGIES[investment_type]

    return {
        "investment_type": investment_type,
        "asset_allocation": strategy,
        "description": {
            "conservative": "보수형 - 안정성 중시, 손실 최소화",
            "moderate": "중도형 - 안정성과 수익성의 균형",
            "aggressive": "적극형 - 높은 수익 추구, 리스크 감수"
        }.get(investment_type, "")
    }


@router.get("/available-sectors")
async def get_available_sectors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    선택 가능한 섹터 목록 조회

    포트폴리오 생성 시 선호 섹터로 선택할 수 있는 섹터 목록을 반환합니다.
    """
    from app.models.securities import Stock
    from sqlalchemy import distinct

    # DB에서 unique한 섹터 목록 조회
    sectors = db.query(distinct(Stock.sector)).filter(
        and_(
            Stock.sector.isnot(None),
            Stock.is_active == True
        )
    ).all()

    sector_list = [sector[0] for sector in sectors if sector[0]]

    return {
        "sectors": sorted(sector_list),
        "total_count": len(sector_list)
    }


@router.post("/simulate")
@limiter.limit(RateLimits.DIAGNOSIS_READ)  # 시뮬레이션도 시간당 100회
async def simulate_portfolio_returns(
    request: Request,
    investment_type: str,
    investment_amount: int,
    years: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    포트폴리오 수익률 시뮬레이션

    주어진 투자 기간 동안의 예상 수익률과 자산 가치를 시뮬레이션합니다.

    **Parameters**:
    - investment_type: 투자 성향
    - investment_amount: 투자 금액
    - years: 투자 기간 (연)

    **Rate Limit**: 시간당 100회
    """
    if investment_type not in ["conservative", "moderate", "aggressive"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid investment type"
        )

    if years < 1 or years > 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Years must be between 1 and 30"
        )

    try:
        # 포트폴리오 생성
        portfolio = create_default_portfolio(
            db=db,
            investment_type=investment_type,
            investment_amount=investment_amount
        )

        # 연평균 기대 수익률
        expected_return = portfolio["statistics"]["expected_annual_return"] / 100

        # 시뮬레이션 결과
        simulations = []
        current_value = investment_amount

        for year in range(1, years + 1):
            # 단순 복리 계산
            current_value = current_value * (1 + expected_return)
            total_return = ((current_value - investment_amount) / investment_amount) * 100

            simulations.append({
                "year": year,
                "value": round(current_value, 0),
                "profit": round(current_value - investment_amount, 0),
                "total_return_pct": round(total_return, 2)
            })

        return {
            "investment_type": investment_type,
            "initial_investment": investment_amount,
            "expected_annual_return": portfolio["statistics"]["expected_annual_return"],
            "investment_years": years,
            "final_value": round(current_value, 0),
            "total_profit": round(current_value - investment_amount, 0),
            "total_return_pct": round(((current_value - investment_amount) / investment_amount) * 100, 2),
            "yearly_projections": simulations
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation failed: {str(e)}"
        )
