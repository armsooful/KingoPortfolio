"""
Phase 2 Epic C: 커스텀 포트폴리오 API 라우터

커스텀 포트폴리오 CRUD 및 시뮬레이션 실행 API

**엔드포인트:**
- POST /portfolio/custom - 포트폴리오 생성
- GET /portfolio/custom - 목록 조회
- GET /portfolio/custom/{id} - 상세 조회
- PUT /portfolio/custom/{id} - 수정
- DELETE /portfolio/custom/{id} - 삭제

⚠️ 본 API는 시뮬레이션 파라미터 관리용이며,
투자 추천이나 자문을 제공하지 않습니다.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.services.custom_portfolio_service import (
    create_portfolio,
    get_portfolio,
    list_portfolios,
    update_portfolio,
    delete_portfolio,
    get_asset_class_list,
    get_weights_for_simulation,
    get_weights_hash_string,
    validate_weights,
    PortfolioValidationError,
    WEIGHT_SUM_EPSILON,
)
from app.services.custom_portfolio_simulation import (
    run_custom_portfolio_simulation,
)
from app.rate_limiter import limiter, RateLimits


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolio", tags=["Custom Portfolio"])


# ============================================================================
# Pydantic 모델
# ============================================================================

class PortfolioWeights(BaseModel):
    """포트폴리오 비중"""
    EQUITY: Optional[float] = Field(None, ge=0, le=1, description="주식 비중")
    BOND: Optional[float] = Field(None, ge=0, le=1, description="채권 비중")
    CASH: Optional[float] = Field(None, ge=0, le=1, description="현금 비중")
    GOLD: Optional[float] = Field(None, ge=0, le=1, description="금 비중")
    ALT: Optional[float] = Field(None, ge=0, le=1, description="대체투자 비중")

    def to_dict(self) -> Dict[str, float]:
        """0이 아닌 비중만 dict로 변환"""
        result = {}
        for key in ["EQUITY", "BOND", "CASH", "GOLD", "ALT"]:
            value = getattr(self, key)
            if value is not None and value > 0:
                result[key] = value
        return result


class CreatePortfolioRequest(BaseModel):
    """포트폴리오 생성 요청"""
    portfolio_name: str = Field(..., min_length=1, max_length=100, description="포트폴리오 이름")
    weights: Dict[str, float] = Field(..., description="자산군별 비중 (합계=1)")
    description: Optional[str] = Field(None, max_length=500, description="설명")
    base_template_id: Optional[str] = Field(None, description="기반 템플릿 ID")

    @field_validator('weights')
    @classmethod
    def validate_weights_sum(cls, v):
        if not v:
            raise ValueError("비중 정보가 필요합니다.")
        total = sum(v.values())
        if abs(total - 1.0) > WEIGHT_SUM_EPSILON:
            raise ValueError(f"비중 합계({total:.6f})가 1.0이 아닙니다.")
        return v


class UpdatePortfolioRequest(BaseModel):
    """포트폴리오 수정 요청"""
    portfolio_name: Optional[str] = Field(None, min_length=1, max_length=100)
    weights: Optional[Dict[str, float]] = None
    description: Optional[str] = Field(None, max_length=500)

    @field_validator('weights')
    @classmethod
    def validate_weights_sum(cls, v):
        if v is not None:
            total = sum(v.values())
            if abs(total - 1.0) > WEIGHT_SUM_EPSILON:
                raise ValueError(f"비중 합계({total:.6f})가 1.0이 아닙니다.")
        return v


class PortfolioResponse(BaseModel):
    """포트폴리오 응답"""
    portfolio_id: int
    portfolio_name: str
    weights: Dict[str, float]
    description: Optional[str] = None
    base_template_id: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: str


class PortfolioListItem(BaseModel):
    """포트폴리오 목록 항목"""
    portfolio_id: int
    portfolio_name: str
    updated_at: str


# ============================================================================
# API 엔드포인트
# ============================================================================

@router.get("/asset-classes")
async def get_asset_classes(
    db: Session = Depends(get_db)
):
    """
    허용된 자산군 목록 조회

    커스텀 포트폴리오 생성 시 사용 가능한 자산군 코드 목록을 반환합니다.
    """
    asset_classes = get_asset_class_list(db)

    return {
        "success": True,
        "asset_classes": asset_classes,
        "message": f"{len(asset_classes)}개의 자산군이 사용 가능합니다."
    }


@router.post("/custom")
@limiter.limit(RateLimits.DATA_WRITE)
async def create_custom_portfolio(
    request: Request,
    body: CreatePortfolioRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    커스텀 포트폴리오 생성

    사용자가 자산군 비중을 직접 정의하여 포트폴리오를 생성합니다.

    **검증 규칙:**
    - 비중 합계 = 1.0 (허용 오차 0.000001)
    - 각 비중: 0 <= weight <= 1
    - 허용된 자산군 코드만 사용 가능

    **Rate Limit**: 분당 30회

    ⚠️ 본 기능은 시뮬레이션 파라미터 저장용이며,
    투자 추천이나 자문을 제공하지 않습니다.
    """
    try:
        portfolio = create_portfolio(
            db=db,
            owner_user_id=current_user.id,
            portfolio_name=body.portfolio_name,
            weights=body.weights,
            description=body.description,
            base_template_id=body.base_template_id,
        )

        logger.info(f"Custom portfolio created: {portfolio.portfolio_id} by user {current_user.id}")

        return {
            "success": True,
            "portfolio": portfolio.to_dict(),
            "message": "포트폴리오가 생성되었습니다."
        }

    except PortfolioValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Portfolio creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"포트폴리오 생성 실패: {str(e)}"
        )


@router.get("/custom")
async def list_custom_portfolios(
    include_inactive: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    커스텀 포트폴리오 목록 조회

    현재 로그인한 사용자의 포트폴리오 목록을 반환합니다.
    """
    portfolios = list_portfolios(
        db=db,
        owner_user_id=current_user.id,
        include_inactive=include_inactive,
    )

    return {
        "success": True,
        "portfolios": [
            {
                "portfolio_id": p.portfolio_id,
                "portfolio_name": p.portfolio_name,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in portfolios
        ],
        "count": len(portfolios),
        "message": f"{len(portfolios)}개의 포트폴리오가 있습니다."
    }


@router.get("/custom/{portfolio_id}")
async def get_custom_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    커스텀 포트폴리오 상세 조회

    포트폴리오의 상세 정보와 자산군별 비중을 반환합니다.
    본인 소유의 포트폴리오만 조회 가능합니다.
    """
    portfolio = get_portfolio(
        db=db,
        portfolio_id=portfolio_id,
        owner_user_id=current_user.id,
    )

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"포트폴리오 ID {portfolio_id}를 찾을 수 없습니다."
        )

    return {
        "success": True,
        "portfolio": portfolio.to_dict(),
    }


@router.put("/custom/{portfolio_id}")
@limiter.limit(RateLimits.DATA_WRITE)
async def update_custom_portfolio(
    request: Request,
    portfolio_id: int,
    body: UpdatePortfolioRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    커스텀 포트폴리오 수정

    포트폴리오의 이름, 설명, 비중을 수정합니다.
    본인 소유의 포트폴리오만 수정 가능합니다.

    **Rate Limit**: 분당 30회
    """
    try:
        portfolio = update_portfolio(
            db=db,
            portfolio_id=portfolio_id,
            owner_user_id=current_user.id,
            portfolio_name=body.portfolio_name,
            weights=body.weights,
            description=body.description,
        )

        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"포트폴리오 ID {portfolio_id}를 찾을 수 없습니다."
            )

        logger.info(f"Custom portfolio updated: {portfolio_id} by user {current_user.id}")

        return {
            "success": True,
            "portfolio": portfolio.to_dict(),
            "message": "포트폴리오가 수정되었습니다."
        }

    except PortfolioValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Portfolio update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"포트폴리오 수정 실패: {str(e)}"
        )


@router.delete("/custom/{portfolio_id}")
@limiter.limit(RateLimits.DATA_WRITE)
async def delete_custom_portfolio(
    request: Request,
    portfolio_id: int,
    hard_delete: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    커스텀 포트폴리오 삭제

    포트폴리오를 삭제합니다 (기본: soft delete).
    본인 소유의 포트폴리오만 삭제 가능합니다.

    **Rate Limit**: 분당 30회
    """
    success = delete_portfolio(
        db=db,
        portfolio_id=portfolio_id,
        owner_user_id=current_user.id,
        hard_delete=hard_delete,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"포트폴리오 ID {portfolio_id}를 찾을 수 없습니다."
        )

    logger.info(f"Custom portfolio deleted: {portfolio_id} by user {current_user.id}")

    return {
        "success": True,
        "message": "포트폴리오가 삭제되었습니다."
    }


# ============================================================================
# 시뮬레이션 실행 API (Epic C - 3단계)
# ============================================================================

class CustomPortfolioSimulationRequest(BaseModel):
    """커스텀 포트폴리오 시뮬레이션 요청"""
    portfolio_id: int = Field(..., description="포트폴리오 ID")
    start_date: str = Field(..., description="시작일 (YYYY-MM-DD)")
    end_date: str = Field(..., description="종료일 (YYYY-MM-DD)")
    initial_nav: float = Field(1.0, gt=0, description="초기 NAV")
    rebalancing_rule_id: Optional[int] = Field(None, description="리밸런싱 규칙 ID (Epic B)")


@router.post("/custom/simulate")
@limiter.limit(RateLimits.AI_ANALYSIS)
async def run_custom_portfolio_backtest(
    request: Request,
    body: CustomPortfolioSimulationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    커스텀 포트폴리오 시뮬레이션 실행

    사용자가 정의한 포트폴리오로 과거 데이터 기반 시뮬레이션을 실행합니다.

    **파라미터:**
    - portfolio_id: 커스텀 포트폴리오 ID
    - start_date: 시작일 (YYYY-MM-DD)
    - end_date: 종료일 (YYYY-MM-DD)
    - initial_nav: 초기 NAV (기본 1.0)
    - rebalancing_rule_id: 리밸런싱 규칙 ID (선택, Epic B 연동)

    **Rate Limit**: 시간당 5회

    ⚠️ 본 시뮬레이션은 교육 목적이며, 미래 수익을 보장하지 않습니다.
    ⚠️ 과거 데이터 기반 분석입니다.
    """
    try:
        # 1. 날짜 파싱
        try:
            start_dt = datetime.strptime(body.start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(body.end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용하세요."
            )

        if end_dt <= start_dt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="종료일은 시작일보다 커야 합니다."
            )

        # 2. 포트폴리오 소유권 확인
        portfolio = get_portfolio(db, body.portfolio_id, current_user.id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"포트폴리오 ID {body.portfolio_id}를 찾을 수 없습니다."
            )

        # 3. 시뮬레이션 실행
        result = run_custom_portfolio_simulation(
            db=db,
            portfolio_id=body.portfolio_id,
            start_date=start_dt,
            end_date=end_dt,
            initial_nav=body.initial_nav,
            rebalancing_rule_id=body.rebalancing_rule_id,
        )

        logger.info(
            f"Custom portfolio simulation - portfolio: {body.portfolio_id}, "
            f"hash: {result['request_hash'][:8]}..., user: {current_user.id}"
        )

        # 4. 경로 요약 (전체 경로는 용량이 크므로 요약)
        path = result.get("path", [])
        path_summary = {
            "total_points": len(path),
            "first_date": path[0]["path_date"].isoformat() if path and isinstance(path[0]["path_date"], date) else (path[0]["path_date"] if path else None),
            "last_date": path[-1]["path_date"].isoformat() if path and isinstance(path[-1]["path_date"], date) else (path[-1]["path_date"] if path else None),
            "first_nav": path[0]["nav"] if path else None,
            "last_nav": path[-1]["nav"] if path else None,
        }

        return {
            "success": True,
            "portfolio_id": body.portfolio_id,
            "portfolio_name": portfolio.portfolio_name,
            "weights": result["weights"],
            "start_date": body.start_date,
            "end_date": body.end_date,
            "initial_nav": body.initial_nav,
            "final_value": result["final_value"],
            "trading_days": result["trading_days"],
            "risk_metrics": result["risk_metrics"],
            "historical_observation": result["historical_observation"],
            "path_summary": path_summary,
            "rebalancing_enabled": result["rebalancing_enabled"],
            "rebalancing_events_count": result["rebalancing_events_count"],
            "request_hash": result["request_hash"],
            "engine_version": result["engine_version"],
            "message": f"커스텀 포트폴리오 시뮬레이션 완료",
            "note": "과거 데이터 기반 시뮬레이션이며, 미래 수익을 보장하지 않습니다.",
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Custom portfolio simulation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"시뮬레이션 실패: {str(e)}"
        )


@router.get("/custom/{portfolio_id}/simulate/path")
@limiter.limit(RateLimits.DATA_READ)
async def get_custom_portfolio_simulation_path(
    request: Request,
    portfolio_id: int,
    start_date: str,
    end_date: str,
    initial_nav: float = 1.0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    커스텀 포트폴리오 시뮬레이션 NAV 경로 조회

    일별 NAV, 누적수익률, 낙폭 데이터를 반환합니다.
    차트 렌더링용 데이터입니다.

    **Rate Limit**: 분당 30회
    """
    try:
        # 날짜 파싱
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="날짜 형식이 올바르지 않습니다."
            )

        # 포트폴리오 소유권 확인
        portfolio = get_portfolio(db, portfolio_id, current_user.id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"포트폴리오 ID {portfolio_id}를 찾을 수 없습니다."
            )

        # 시뮬레이션 실행
        result = run_custom_portfolio_simulation(
            db=db,
            portfolio_id=portfolio_id,
            start_date=start_dt,
            end_date=end_dt,
            initial_nav=initial_nav,
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
            "portfolio_id": portfolio_id,
            "path": serialized_path,
            "trading_days": len(serialized_path)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Path retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"경로 조회 실패: {str(e)}"
        )
