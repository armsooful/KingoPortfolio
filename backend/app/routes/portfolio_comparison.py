# backend/app/routes/portfolio_comparison.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.portfolio import Portfolio, PortfolioHistory
from app.auth import require_admin
from app.models.user import User

router = APIRouter(prefix="/admin/portfolio-comparison", tags=["Portfolio Comparison"])


@router.get("/list")
def get_portfolio_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    포트폴리오 목록 조회 (비교 대상 선택용)
    """
    portfolios = db.query(Portfolio).order_by(Portfolio.created_at.desc()).all()

    return {
        "success": True,
        "data": {
            "count": len(portfolios),
            "portfolios": [
                {
                    "id": p.id,
                    "name": p.name,
                    "user_id": p.user_id,
                    "total_value": p.total_value,
                    "total_return": p.total_return,
                    "created_at": p.created_at.isoformat() if p.created_at else None
                }
                for p in portfolios
            ]
        }
    }


@router.get("/compare")
def compare_portfolios(
    portfolio_ids: str,  # comma-separated IDs: "1,2,3"
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    여러 포트폴리오의 성과를 비교

    Args:
        portfolio_ids: 쉼표로 구분된 포트폴리오 ID 목록 (예: "1,2,3")
        days: 조회 기간 (일)

    Returns:
        - 각 포트폴리오의 기본 정보
        - 시계열 수익률 데이터
        - 비교 통계
    """

    # 1. 포트폴리오 ID 파싱
    try:
        portfolio_id_list = [int(pid.strip()) for pid in portfolio_ids.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="잘못된 포트폴리오 ID 형식입니다.")

    if len(portfolio_id_list) < 1:
        raise HTTPException(status_code=400, detail="최소 1개 이상의 포트폴리오를 선택해야 합니다.")

    if len(portfolio_id_list) > 5:
        raise HTTPException(status_code=400, detail="최대 5개의 포트폴리오까지 비교할 수 있습니다.")

    # 2. 포트폴리오 조회
    portfolios = db.query(Portfolio).filter(Portfolio.id.in_(portfolio_id_list)).all()

    if len(portfolios) != len(portfolio_id_list):
        raise HTTPException(status_code=404, detail="일부 포트폴리오를 찾을 수 없습니다.")

    # 3. 날짜 범위 계산
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    # 4. 각 포트폴리오의 히스토리 데이터 조회
    comparison_data = []

    for portfolio in portfolios:
        # 히스토리 조회
        histories = db.query(PortfolioHistory).filter(
            PortfolioHistory.portfolio_id == portfolio.id,
            PortfolioHistory.date >= start_date,
            PortfolioHistory.date <= end_date
        ).order_by(PortfolioHistory.date).all()

        # 시계열 데이터 구성
        timeseries = []
        for h in histories:
            timeseries.append({
                "date": h.date.isoformat(),
                "total_value": h.total_value,
                "total_return": h.total_return
            })

        # 통계 계산
        if len(histories) > 0:
            first_value = histories[0].total_value if histories[0].total_value else 0
            last_value = histories[-1].total_value if histories[-1].total_value else 0

            period_return = 0
            if first_value > 0:
                period_return = ((last_value - first_value) / first_value) * 100

            max_value = max([h.total_value for h in histories if h.total_value])
            min_value = min([h.total_value for h in histories if h.total_value])
            avg_value = sum([h.total_value for h in histories if h.total_value]) / len(histories)

            stats = {
                "period_return": round(period_return, 2),
                "max_value": max_value,
                "min_value": min_value,
                "avg_value": round(avg_value, 2),
                "data_points": len(histories)
            }
        else:
            stats = {
                "period_return": 0,
                "max_value": portfolio.total_value or 0,
                "min_value": portfolio.total_value or 0,
                "avg_value": portfolio.total_value or 0,
                "data_points": 0
            }

        comparison_data.append({
            "portfolio": {
                "id": portfolio.id,
                "name": portfolio.name,
                "user_id": portfolio.user_id,
                "total_value": portfolio.total_value,
                "total_return": portfolio.total_return
            },
            "timeseries": timeseries,
            "statistics": stats
        })

    return {
        "success": True,
        "data": {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "portfolios": comparison_data
        }
    }
