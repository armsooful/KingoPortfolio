"""
종목/섹터 조회 API

포트폴리오 구성을 위한 종목 및 섹터 정보 조회
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.securities import Stock, ETF


router = APIRouter(prefix="/api/v1/securities", tags=["Securities"])


# ============================================================
# Response Models
# ============================================================


class StockItem(BaseModel):
    """주식 종목 정보"""

    ticker: str
    name: str
    sector: Optional[str] = None
    market: Optional[str] = None
    current_price: Optional[float] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    ytd_return: Optional[float] = None
    one_year_return: Optional[float] = None
    risk_level: Optional[str] = None
    category: Optional[str] = None

    class Config:
        from_attributes = True


class ETFItem(BaseModel):
    """ETF 종목 정보"""

    ticker: str
    name: str
    etf_type: Optional[str] = None
    current_price: Optional[float] = None
    aum: Optional[float] = None
    expense_ratio: Optional[float] = None
    ytd_return: Optional[float] = None
    one_year_return: Optional[float] = None
    risk_level: Optional[str] = None
    category: Optional[str] = None

    class Config:
        from_attributes = True


class SectorInfo(BaseModel):
    """섹터 정보"""

    sector_code: str
    sector_name: str
    stock_count: int
    avg_pe_ratio: Optional[float] = None
    avg_dividend_yield: Optional[float] = None
    avg_ytd_return: Optional[float] = None


class StockListResponse(BaseModel):
    """주식 목록 응답"""

    total_count: int
    stocks: List[StockItem]


class ETFListResponse(BaseModel):
    """ETF 목록 응답"""

    total_count: int
    etfs: List[ETFItem]


class SectorListResponse(BaseModel):
    """섹터 목록 응답"""

    total_count: int
    sectors: List[SectorInfo]


# ============================================================
# Endpoints
# ============================================================


@router.get("/stocks", response_model=StockListResponse)
def list_stocks(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None, description="종목명 또는 종목코드 검색"),
    sector: Optional[str] = Query(None, description="섹터 필터"),
    market: Optional[str] = Query(None, description="시장 필터 (KOSPI, KOSDAQ)"),
    risk_level: Optional[str] = Query(None, description="위험도 필터 (low, medium, high)"),
    category: Optional[str] = Query(None, description="카테고리 필터"),
    sort_by: Optional[str] = Query("market_cap", description="정렬 기준"),
    sort_order: Optional[str] = Query("desc", description="정렬 순서 (asc, desc)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    주식 종목 목록 조회

    포트폴리오 구성을 위해 활성화된 주식 종목을 조회합니다.
    검색, 필터링, 정렬 기능을 제공합니다.
    """
    query = db.query(Stock).filter(Stock.is_active == True)

    # 검색
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Stock.ticker.ilike(search_pattern)) | (Stock.name.ilike(search_pattern))
        )

    # 필터
    if sector:
        query = query.filter(Stock.sector == sector)
    if market:
        query = query.filter(Stock.market == market)
    if risk_level:
        query = query.filter(Stock.risk_level == risk_level)
    if category:
        query = query.filter(Stock.category == category)

    # 전체 개수
    total_count = query.count()

    # 정렬
    sort_column = getattr(Stock, sort_by, Stock.market_cap)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # 페이징
    stocks = query.offset(offset).limit(limit).all()

    return StockListResponse(
        total_count=total_count,
        stocks=[StockItem.model_validate(s) for s in stocks],
    )


@router.get("/etfs", response_model=ETFListResponse)
def list_etfs(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None, description="ETF명 또는 종목코드 검색"),
    etf_type: Optional[str] = Query(None, description="ETF 유형 필터"),
    risk_level: Optional[str] = Query(None, description="위험도 필터"),
    sort_by: Optional[str] = Query("aum", description="정렬 기준"),
    sort_order: Optional[str] = Query("desc", description="정렬 순서"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    ETF 목록 조회

    포트폴리오 구성을 위해 활성화된 ETF를 조회합니다.
    """
    query = db.query(ETF).filter(ETF.is_active == True)

    # 검색
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (ETF.ticker.ilike(search_pattern)) | (ETF.name.ilike(search_pattern))
        )

    # 필터
    if etf_type:
        query = query.filter(ETF.etf_type == etf_type)
    if risk_level:
        query = query.filter(ETF.risk_level == risk_level)

    # 전체 개수
    total_count = query.count()

    # 정렬
    sort_column = getattr(ETF, sort_by, ETF.aum)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # 페이징
    etfs = query.offset(offset).limit(limit).all()

    return ETFListResponse(
        total_count=total_count,
        etfs=[ETFItem.model_validate(e) for e in etfs],
    )


@router.get("/sectors", response_model=SectorListResponse)
def list_sectors(
    db: Session = Depends(get_db),
    market: Optional[str] = Query(None, description="시장 필터"),
):
    """
    섹터 목록 조회

    활성화된 주식의 섹터별 통계를 조회합니다.
    섹터 기반 포트폴리오 구성에 사용됩니다.
    """
    query = db.query(
        Stock.sector,
        func.count(Stock.id).label("stock_count"),
        func.avg(Stock.pe_ratio).label("avg_pe_ratio"),
        func.avg(Stock.dividend_yield).label("avg_dividend_yield"),
        func.avg(Stock.ytd_return).label("avg_ytd_return"),
    ).filter(
        Stock.is_active == True,
        Stock.sector.isnot(None),
    )

    if market:
        query = query.filter(Stock.market == market)

    query = query.group_by(Stock.sector).order_by(func.count(Stock.id).desc())

    results = query.all()

    sectors = []
    for row in results:
        sectors.append(
            SectorInfo(
                sector_code=row.sector,
                sector_name=row.sector,  # 섹터 마스터가 없으면 코드를 이름으로 사용
                stock_count=row.stock_count,
                avg_pe_ratio=round(row.avg_pe_ratio, 2) if row.avg_pe_ratio else None,
                avg_dividend_yield=round(row.avg_dividend_yield, 2) if row.avg_dividend_yield else None,
                avg_ytd_return=round(row.avg_ytd_return, 2) if row.avg_ytd_return else None,
            )
        )

    return SectorListResponse(
        total_count=len(sectors),
        sectors=sectors,
    )


@router.get("/stocks/{ticker}", response_model=StockItem)
def get_stock(
    ticker: str,
    db: Session = Depends(get_db),
):
    """
    주식 종목 상세 조회
    """
    stock = db.query(Stock).filter(Stock.ticker == ticker, Stock.is_active == True).first()

    if not stock:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"종목을 찾을 수 없습니다: {ticker}",
        )

    return StockItem.model_validate(stock)


@router.get("/etfs/{ticker}", response_model=ETFItem)
def get_etf(
    ticker: str,
    db: Session = Depends(get_db),
):
    """
    ETF 상세 조회
    """
    etf = db.query(ETF).filter(ETF.ticker == ticker, ETF.is_active == True).first()

    if not etf:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ETF를 찾을 수 없습니다: {ticker}",
        )

    return ETFItem.model_validate(etf)


@router.get("/markets")
def list_markets(db: Session = Depends(get_db)):
    """
    시장 목록 조회
    """
    markets = (
        db.query(Stock.market)
        .filter(Stock.is_active == True, Stock.market.isnot(None))
        .distinct()
        .all()
    )

    return {"markets": [m[0] for m in markets if m[0]]}


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    """
    카테고리 목록 조회
    """
    categories = (
        db.query(Stock.category)
        .filter(Stock.is_active == True, Stock.category.isnot(None))
        .distinct()
        .all()
    )

    return {"categories": [c[0] for c in categories if c[0]]}
