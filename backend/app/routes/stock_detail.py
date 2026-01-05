# backend/app/routes/stock_detail.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.securities import Stock, KrxTimeSeries
from app.auth import get_current_user, require_admin
from app.models.user import User
from app.exceptions import StockNotFoundError

router = APIRouter(prefix="/admin/stock-detail", tags=["Stock Detail"])


@router.get("/{ticker}")
def get_stock_detail(
    ticker: str,
    days: int = 90,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    종목 상세 정보 조회
    - 기본 정보 (stocks 테이블)
    - 시계열 데이터 (krx_timeseries 테이블, 최근 N일)
    - 재무 지표 (stocks 테이블)
    """

    # 1. 기본 정보 조회
    stock = db.query(Stock).filter(Stock.ticker == ticker).first()

    if not stock:
        raise StockNotFoundError(f"종목 코드 {ticker}를 찾을 수 없습니다.")

    # 2. 시계열 데이터 조회 (최근 N일)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    timeseries = db.query(KrxTimeSeries).filter(
        KrxTimeSeries.ticker == ticker,
        KrxTimeSeries.date >= start_date,
        KrxTimeSeries.date <= end_date
    ).order_by(KrxTimeSeries.date).all()

    # 3. 통계 계산
    stats = None
    if timeseries:
        closes = [ts.close for ts in timeseries]
        volumes = [ts.volume for ts in timeseries]

        first_close = closes[0]
        last_close = closes[-1]
        period_return = ((last_close - first_close) / first_close) * 100 if first_close > 0 else 0

        stats = {
            "period_days": len(timeseries),
            "period_return": round(period_return, 2),
            "high": max([ts.high for ts in timeseries]),
            "low": min([ts.low for ts in timeseries]),
            "avg_close": round(sum(closes) / len(closes), 2),
            "avg_volume": int(sum(volumes) / len(volumes)),
            "total_volume": sum(volumes)
        }

    # 4. 응답 데이터 구성
    return {
        "success": True,
        "data": {
        "basic_info": {
            "ticker": stock.ticker,
            "name": stock.name,
            "market": stock.market,
            "sector": stock.sector,
            "current_price": stock.current_price,
            "market_cap": stock.market_cap,
            "last_updated": stock.last_updated.isoformat() if stock.last_updated else None
        },
        "financials": {
            "pe_ratio": stock.pe_ratio,
            "pb_ratio": stock.pb_ratio,
            "dividend_yield": stock.dividend_yield,
            "ytd_return": stock.ytd_return,
            "one_year_return": stock.one_year_return
        },
        "timeseries": {
            "period_days": days,
            "data_count": len(timeseries),
            "data": [
                {
                    "date": ts.date.isoformat(),
                    "open": ts.open,
                    "high": ts.high,
                    "low": ts.low,
                    "close": ts.close,
                    "volume": ts.volume
                }
                for ts in timeseries
            ]
        },
        "statistics": stats
        }
    }


@router.get("/search/ticker-list")
def search_ticker_list(
    q: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    종목 티커 검색 (자동완성용)
    - q: 검색어 (종목코드 또는 종목명)
    - limit: 최대 결과 수
    """
    query = db.query(Stock)

    if q:
        # 종목코드 또는 종목명으로 검색
        query = query.filter(
            (Stock.ticker.like(f"%{q}%")) | (Stock.name.like(f"%{q}%"))
        )

    stocks = query.limit(limit).all()

    return {
        "success": True,
        "data": {
        "count": len(stocks),
        "tickers": [
            {
                "ticker": stock.ticker,
                "name": stock.name,
                "market": stock.market,
                "current_price": stock.current_price
            }
            for stock in stocks
        ]
        }
    }
