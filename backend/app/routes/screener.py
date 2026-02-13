# backend/app/routes/screener.py

"""종목 스크리너 API — Compass Score 기반 종목 탐색"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from typing import Optional, List
from pydantic import BaseModel
from app.database import get_db
from app.models.securities import Stock
from app.models import User
from app.auth import get_current_user

router = APIRouter(
    prefix="/api/v1/screener",
    tags=["Screener"],
)

DISCLAIMER = "교육 목적 참고 정보이며 투자 권유가 아닙니다"

# 정렬 가능 컬럼 화이트리스트 (SQL injection 방지)
SORTABLE_COLUMNS = {
    "compass_score": Stock.compass_score,
    "market_cap": Stock.market_cap,
    "pe_ratio": Stock.pe_ratio,
    "pb_ratio": Stock.pb_ratio,
    "dividend_yield": Stock.dividend_yield,
    "name": Stock.name,
    "current_price": Stock.current_price,
}


class ScreenerStockItem(BaseModel):
    ticker: str
    name: Optional[str] = None
    sector: Optional[str] = None
    market: Optional[str] = None
    current_price: Optional[float] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    compass_score: Optional[float] = None
    compass_grade: Optional[str] = None
    compass_summary: Optional[str] = None

    class Config:
        from_attributes = True


class ScreenerResponse(BaseModel):
    total_count: int
    stocks: List[ScreenerStockItem]
    disclaimer: str


@router.get("/stocks", response_model=ScreenerResponse)
async def screener_stocks(
    search: Optional[str] = Query(None, description="종목명/코드 검색"),
    sector: Optional[str] = Query(None, description="섹터 필터"),
    market: Optional[str] = Query(None, description="시장 필터 (KOSPI, KOSDAQ)"),
    min_score: Optional[float] = Query(None, ge=0, le=100),
    max_score: Optional[float] = Query(None, ge=0, le=100),
    grade: Optional[str] = Query(None, description="등급 필터 (S, A+, A, B+, B, C+, C, D, F)"),
    sort_by: str = Query("compass_score", description="정렬 기준"),
    sort_order: str = Query("desc", description="정렬 방향 (asc/desc)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compass Score가 계산된 종목을 필터/정렬하여 조회"""

    query = db.query(Stock).filter(
        Stock.compass_score.isnot(None),
        Stock.is_active == True,
    )

    # 검색 필터
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Stock.name.ilike(search_term)) | (Stock.ticker.ilike(search_term))
        )

    # 섹터 필터
    if sector:
        query = query.filter(Stock.sector == sector)

    # 시장 필터
    if market:
        query = query.filter(Stock.market == market)

    # 점수 범위 필터
    if min_score is not None:
        query = query.filter(Stock.compass_score >= min_score)
    if max_score is not None:
        query = query.filter(Stock.compass_score <= max_score)

    # 등급 필터
    if grade:
        query = query.filter(Stock.compass_grade == grade)

    # 총 건수
    total_count = query.count()

    # 정렬
    sort_col = SORTABLE_COLUMNS.get(sort_by, Stock.compass_score)
    if sort_order == "asc":
        query = query.order_by(asc(sort_col).nulls_last())
    else:
        query = query.order_by(desc(sort_col).nulls_last())

    # 페이지네이션
    stocks = query.offset(offset).limit(limit).all()

    return ScreenerResponse(
        total_count=total_count,
        stocks=[
            ScreenerStockItem(
                ticker=s.ticker,
                name=s.name,
                sector=s.sector,
                market=s.market,
                current_price=s.current_price,
                market_cap=s.market_cap,
                pe_ratio=s.pe_ratio,
                pb_ratio=s.pb_ratio,
                dividend_yield=s.dividend_yield,
                compass_score=s.compass_score,
                compass_grade=s.compass_grade,
                compass_summary=s.compass_summary,
            )
            for s in stocks
        ],
        disclaimer=DISCLAIMER,
    )
