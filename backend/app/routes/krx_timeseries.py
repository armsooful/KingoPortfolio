"""
한국거래소 시계열 데이터 수집 API
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import logging

from app.database import get_db
from app.models import User
from app.models.securities import Stock, ETF, KrxTimeSeries
from app.auth import require_admin
from pykrx import stock as krx_stock

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/krx-timeseries", tags=["KRX TimeSeries"])


@router.post("/load-stock/{ticker}")
async def load_stock_timeseries(
    ticker: str,
    days: int = Query(365, ge=1, le=3650, description="가져올 일수 (최대 10년)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    특정 한국 주식의 시계열 데이터 수집

    - ticker: 6자리 종목 코드 (예: 005930)
    - days: 수집할 기간 (일수, 기본 1년)
    """
    try:
        if not (ticker.isdigit() and len(ticker) == 6):
            raise HTTPException(
                status_code=400,
                detail="Invalid ticker format. Must be 6-digit code (e.g., 005930)"
            )

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # pykrx로 데이터 수집
        df = krx_stock.get_market_ohlcv_by_date(
            fromdate=start_date.strftime("%Y%m%d"),
            todate=end_date.strftime("%Y%m%d"),
            ticker=ticker
        )

        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for ticker {ticker}"
            )

        # DB에 저장
        records_added = 0
        for date_index, row in df.iterrows():
            # 중복 체크
            existing = db.query(KrxTimeSeries).filter(
                KrxTimeSeries.ticker == ticker,
                KrxTimeSeries.date == date_index.date()
            ).first()

            if not existing:
                timeseries = KrxTimeSeries(
                    ticker=ticker,
                    date=date_index.date(),
                    open=float(row['시가']),
                    high=float(row['고가']),
                    low=float(row['저가']),
                    close=float(row['종가']),
                    volume=int(row['거래량'])
                )
                db.add(timeseries)
                records_added += 1

        db.commit()

        return {
            "success": True,
            "ticker": ticker,
            "records_added": records_added,
            "date_range": {
                "start": start_date.date().isoformat(),
                "end": end_date.date().isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to load timeseries for {ticker}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load timeseries: {str(e)}"
        )


@router.post("/load-all-stocks")
async def load_all_stocks_timeseries(
    background_tasks: BackgroundTasks,
    days: int = Query(365, ge=1, le=3650),
    limit: int = Query(50, ge=1, le=200, description="처리할 종목 수"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    모든 활성 한국 주식의 시계열 데이터 수집 (백그라운드)

    - days: 수집할 기간 (일수)
    - limit: 처리할 종목 수 제한
    """
    try:
        # 활성 주식 목록 조회
        stocks = db.query(Stock).filter(
            Stock.is_active == True
        ).limit(limit).all()

        if not stocks:
            raise HTTPException(
                status_code=404,
                detail="No active stocks found"
            )

        tickers = [stock.ticker for stock in stocks]

        # 백그라운드 태스크로 실행
        background_tasks.add_task(
            _load_multiple_timeseries,
            db=db,
            tickers=tickers,
            days=days
        )

        return {
            "success": True,
            "message": f"{len(tickers)}개 종목의 시계열 데이터 수집 시작",
            "tickers": tickers[:10],  # 처음 10개만 표시
            "total_count": len(tickers)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start timeseries collection: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start collection: {str(e)}"
        )


def _load_multiple_timeseries(db: Session, tickers: list, days: int):
    """백그라운드에서 여러 종목의 시계열 데이터 수집"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    for ticker in tickers:
        try:
            logger.info(f"Loading timeseries for {ticker}...")

            df = krx_stock.get_market_ohlcv_by_date(
                fromdate=start_date.strftime("%Y%m%d"),
                todate=end_date.strftime("%Y%m%d"),
                ticker=ticker
            )

            if df.empty:
                logger.warning(f"No data found for {ticker}")
                continue

            records_added = 0
            for date_index, row in df.iterrows():
                existing = db.query(KrxTimeSeries).filter(
                    KrxTimeSeries.ticker == ticker,
                    KrxTimeSeries.date == date_index.date()
                ).first()

                if not existing:
                    timeseries = KrxTimeSeries(
                        ticker=ticker,
                        date=date_index.date(),
                        open=float(row['시가']),
                        high=float(row['고가']),
                        low=float(row['저가']),
                        close=float(row['종가']),
                        volume=int(row['거래량'])
                    )
                    db.add(timeseries)
                    records_added += 1

            db.commit()
            logger.info(f"Loaded {records_added} records for {ticker}")

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to load {ticker}: {str(e)}")
            continue


@router.get("/data-status")
async def get_timeseries_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """시계열 데이터 현황 조회"""
    try:
        # 총 레코드 수
        total_records = db.query(KrxTimeSeries).count()

        # 종목별 데이터 수
        ticker_counts = db.execute("""
            SELECT ticker, COUNT(*) as count
            FROM krx_timeseries
            GROUP BY ticker
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()

        # 최신 데이터 날짜
        latest_date = db.execute("""
            SELECT MAX(date) as latest_date
            FROM krx_timeseries
        """).scalar()

        # 가장 오래된 데이터 날짜
        oldest_date = db.execute("""
            SELECT MIN(date) as oldest_date
            FROM krx_timeseries
        """).scalar()

        return {
            "total_records": total_records,
            "unique_tickers": len(ticker_counts),
            "latest_date": str(latest_date) if latest_date else None,
            "oldest_date": str(oldest_date) if oldest_date else None,
            "top_tickers": [
                {"ticker": row[0], "records": row[1]}
                for row in ticker_counts
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get timeseries status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status: {str(e)}"
        )
