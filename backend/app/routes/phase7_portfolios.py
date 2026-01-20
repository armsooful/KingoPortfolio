from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.phase7_portfolio import Phase7Portfolio, Phase7PortfolioItem
from app.schemas import (
    Phase7PortfolioCreateRequest,
    Phase7PortfolioListResponse,
    Phase7PortfolioResponse,
)


router = APIRouter(prefix="/api/v1/phase7/portfolios", tags=["Phase7 Portfolios"])


def _validate_weight_sum(items) -> None:
    total = sum(Decimal(str(item.weight)) for item in items)
    if abs(total - Decimal("1.0")) > Decimal("0.0001"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비중 합계는 1.0이어야 합니다.",
        )


@router.post("", response_model=Phase7PortfolioResponse, status_code=status.HTTP_201_CREATED)
def create_phase7_portfolio(
    payload: Phase7PortfolioCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _validate_weight_sum(payload.items)

    portfolio = Phase7Portfolio(
        owner_user_id=current_user.id,
        portfolio_type=payload.portfolio_type,
        portfolio_name=payload.portfolio_name,
        description=payload.description,
    )
    db.add(portfolio)
    db.flush()

    items = []
    for item in payload.items:
        items.append(
            Phase7PortfolioItem(
                portfolio_id=portfolio.portfolio_id,
                item_key=item.id,
                item_name=item.name,
                weight=Decimal(str(item.weight)),
            )
        )
    db.add_all(items)
    db.commit()
    db.refresh(portfolio)

    return Phase7PortfolioResponse(**portfolio.to_dict())


@router.get("", response_model=Phase7PortfolioListResponse)
def list_phase7_portfolios(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    portfolios = (
        db.query(Phase7Portfolio)
        .filter(Phase7Portfolio.owner_user_id == current_user.id)
        .order_by(Phase7Portfolio.created_at.desc())
        .all()
    )
    return Phase7PortfolioListResponse(
        count=len(portfolios),
        portfolios=[Phase7PortfolioResponse(**p.to_dict()) for p in portfolios],
    )


@router.get("/{portfolio_id}", response_model=Phase7PortfolioResponse)
def get_phase7_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    portfolio = (
        db.query(Phase7Portfolio)
        .filter(
            Phase7Portfolio.portfolio_id == portfolio_id,
            Phase7Portfolio.owner_user_id == current_user.id,
        )
        .first()
    )
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="포트폴리오를 찾을 수 없습니다.",
        )
    return Phase7PortfolioResponse(**portfolio.to_dict())
