"""
관리자 포트폴리오 관리 API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict

from app.database import get_db
from app.auth import require_admin_permission
from app.models.user import User
from app.services.portfolio_engine import PortfolioEngine, create_default_portfolio
from app.models.securities import Stock, ETF, Bond, DepositProduct
from app.utils.request_meta import require_idempotency


router = APIRouter(
    prefix="/admin/portfolio",
    tags=["Admin Portfolio"],
    dependencies=[Depends(require_idempotency)],
)


@router.get("/strategies")
async def get_portfolio_strategies(
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW")),
    db: Session = Depends(get_db)
):
    """
    모든 투자 성향별 포트폴리오 전략 조회

    관리자가 각 투자 성향별 자산 배분 전략과 기본 포트폴리오 구성을 확인합니다.
    """
    try:
        engine = PortfolioEngine(db)

        # 각 투자 성향별 전략 정보
        strategies = []
        investment_types = ["conservative", "moderate", "aggressive"]
        type_names = {
            "conservative": "안정형",
            "moderate": "중립형",
            "aggressive": "공격형"
        }

        for inv_type in investment_types:
            strategy = engine.ASSET_ALLOCATION_STRATEGIES[inv_type]

            # 샘플 포트폴리오 생성 (1천만원 기준)
            sample_portfolio = create_default_portfolio(
                db=db,
                investment_type=inv_type,
                investment_amount=10000000
            )

            strategies.append({
                "investment_type": inv_type,
                "display_name": type_names[inv_type],
                "allocation_strategy": strategy,
                "sample_portfolio": {
                    "allocation": sample_portfolio["allocation"],
                    "statistics": sample_portfolio["statistics"],
                    "stocks_count": len(sample_portfolio["portfolio"]["stocks"]),
                    "etfs_count": len(sample_portfolio["portfolio"]["etfs"]),
                    "bonds_count": len(sample_portfolio["portfolio"]["bonds"]),
                    "deposits_count": len(sample_portfolio["portfolio"]["deposits"])
                }
            })

        return {
            "success": True,
            "data": {
                "strategies": strategies,
                "total_types": len(strategies)
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get strategies: {str(e)}"
        )


@router.get("/composition/{investment_type}")
async def get_portfolio_composition(
    investment_type: str,
    investment_amount: int = 10000000,
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW")),
    db: Session = Depends(get_db)
):
    """
    특정 투자 성향의 상세 포트폴리오 구성 조회

    관리자가 특정 투자 성향의 포트폴리오를 상세하게 확인합니다.
    """
    try:
        if investment_type not in ["conservative", "moderate", "aggressive"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid investment type"
            )

        # 포트폴리오 생성
        portfolio = create_default_portfolio(
            db=db,
            investment_type=investment_type,
            investment_amount=investment_amount
        )

        return {
            "success": True,
            "data": portfolio
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get composition: {str(e)}"
        )


@router.get("/available-securities")
async def get_available_securities(
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW")),
    db: Session = Depends(get_db)
):
    """
    포트폴리오에 사용 가능한 모든 종목 정보 조회

    주식, ETF, 채권, 예금 상품의 현황을 확인합니다.
    """
    try:
        # 투자 성향별 종목 수 집계
        securities_by_type = {
            "stocks": {},
            "etfs": {},
            "bonds": {},
            "deposits": {}
        }

        for inv_type in ["conservative", "moderate", "aggressive"]:
            # 주식
            stocks_count = db.query(Stock).filter(
                Stock.is_active == True,
                Stock.investment_type.contains(inv_type)
            ).count()
            securities_by_type["stocks"][inv_type] = stocks_count

            # ETF
            etfs_count = db.query(ETF).filter(
                ETF.is_active == True,
                ETF.investment_type.contains(inv_type)
            ).count()
            securities_by_type["etfs"][inv_type] = etfs_count

            # 채권
            bonds_count = db.query(Bond).filter(
                Bond.is_active == True,
                Bond.investment_type.contains(inv_type)
            ).count()
            securities_by_type["bonds"][inv_type] = bonds_count

        # 예금 상품 (투자 성향 무관)
        deposits_count = db.query(DepositProduct).filter(
            DepositProduct.is_active == True
        ).count()
        securities_by_type["deposits"]["all"] = deposits_count

        # 전체 통계
        total_stocks = db.query(Stock).filter(Stock.is_active == True).count()
        total_etfs = db.query(ETF).filter(ETF.is_active == True).count()
        total_bonds = db.query(Bond).filter(Bond.is_active == True).count()
        total_deposits = deposits_count

        return {
            "success": True,
            "data": {
                "by_investment_type": securities_by_type,
                "totals": {
                    "stocks": total_stocks,
                    "etfs": total_etfs,
                    "bonds": total_bonds,
                    "deposits": total_deposits,
                    "grand_total": total_stocks + total_etfs + total_bonds + total_deposits
                }
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get securities: {str(e)}"
        )


@router.get("/top-securities/{investment_type}")
async def get_top_securities(
    investment_type: str,
    limit: int = 10,
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW")),
    db: Session = Depends(get_db)
):
    """
    특정 투자 성향에서 점수가 높은 상위 종목 조회

    관리자가 각 투자 성향별로 매칭 점수가 높은 종목들을 확인합니다.
    """
    try:
        if investment_type not in ["conservative", "moderate", "aggressive"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid investment type"
            )

        engine = PortfolioEngine(db)

        # 주식 점수 계산
        stocks = db.query(Stock).filter(
            Stock.is_active == True,
            Stock.investment_type.contains(investment_type),
            Stock.current_price.isnot(None),
            Stock.current_price > 0
        ).all()

        scored_stocks = []
        for stock in stocks:
            score = engine._calculate_stock_score(stock, investment_type)
            scored_stocks.append({
                "ticker": stock.ticker,
                "name": stock.name,
                "sector": stock.sector,
                "current_price": stock.current_price,
                "one_year_return": stock.one_year_return,
                "dividend_yield": stock.dividend_yield,
                "pe_ratio": stock.pe_ratio,
                "pb_ratio": stock.pb_ratio,
                "risk_level": stock.risk_level,
                "score": round(score, 2)
            })

        scored_stocks.sort(key=lambda x: x["score"], reverse=True)

        # ETF 점수 계산
        etfs = db.query(ETF).filter(
            ETF.is_active == True,
            ETF.investment_type.contains(investment_type),
            ETF.current_price.isnot(None),
            ETF.current_price > 0
        ).all()

        scored_etfs = []
        for etf in etfs:
            score = engine._calculate_etf_score(etf)
            scored_etfs.append({
                "ticker": etf.ticker,
                "name": etf.name,
                "etf_type": etf.etf_type,
                "current_price": etf.current_price,
                "one_year_return": etf.one_year_return,
                "expense_ratio": etf.expense_ratio,
                "aum": etf.aum,
                "risk_level": etf.risk_level,
                "score": round(score, 2)
            })

        scored_etfs.sort(key=lambda x: x["score"], reverse=True)

        return {
            "success": True,
            "data": {
                "investment_type": investment_type,
                "top_stocks": scored_stocks[:limit],
                "top_etfs": scored_etfs[:limit]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get top securities: {str(e)}"
        )
