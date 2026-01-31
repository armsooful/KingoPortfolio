# backend/app/routes/admin.py

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from pydantic import BaseModel, Field
from app.database import get_db
from app.services.data_loader import DataLoaderService
from app.services.alpha_vantage_loader import AlphaVantageDataLoader
from app.services.pykrx_loader import PyKrxDataLoader
from app.services.financial_analyzer import FinancialAnalyzer
from app.services.real_data_loader import RealDataLoader
from app.models import User
from app.auth import get_current_user, require_admin_permission
from app.progress_tracker import progress_tracker
import logging
import uuid
from app.utils.request_meta import require_idempotency

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(require_idempotency)],
)


class DividendLoadRequest(BaseModel):
    tickers: List[str] = Field(..., min_items=1)
    fiscal_year: int = Field(..., ge=1900, le=2100)
    as_of_date: Optional[date] = None


class CorporateActionLoadRequest(BaseModel):
    start_date: date
    end_date: date
    as_of_date: Optional[date] = None
    corp_cls: Optional[str] = Field(None, regex="^[YKNE]$")

@router.post("/load-data")
async def load_all_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """모든 종목 데이터 적재 (관리자용)"""
    try:
        results = DataLoaderService.load_all_data(db)
        return {
            "status": "success",
            "message": "데이터 적재 완료",
            "results": results
        }
    except Exception as e:
        logger.error(f"Data loading failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"데이터 적재 실패: {str(e)}"
        )

@router.post("/load-stocks")
async def load_stocks(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """주식 데이터만 적재"""
    try:
        # task_id 생성
        task_id = f"stocks_{uuid.uuid4().hex[:8]}"

        # 백그라운드에서 실행하지 않고 즉시 실행 (나중에 백그라운드 태스크로 변경 가능)
        result = DataLoaderService.load_korean_stocks(db, task_id=task_id)

        return {
            "status": "success",
            "message": "주식 데이터 적재 완료",
            "result": result,
            "task_id": task_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/load-etfs")
async def load_etfs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """ETF 데이터만 적재"""
    try:
        # task_id 생성
        task_id = f"etfs_{uuid.uuid4().hex[:8]}"

        # 백그라운드에서 실행하지 않고 즉시 실행 (나중에 백그라운드 태스크로 변경 가능)
        result = DataLoaderService.load_etfs(db, task_id=task_id)

        return {
            "status": "success",
            "message": "ETF 데이터 적재 완료",
            "result": result,
            "task_id": task_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dart/load-dividends")
async def load_dividend_history(
    payload: DividendLoadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """DART 배당 이력 적재"""
    try:
        loader = RealDataLoader(db)
        result = loader.load_dividend_history(
            tickers=payload.tickers,
            fiscal_year=payload.fiscal_year,
            as_of_date=payload.as_of_date or date.today(),
            operator_id=str(current_user.id),
            operator_reason=f"DART 배당 이력 적재 ({payload.fiscal_year})",
        )
        return {
            "status": "success",
            "message": "배당 이력 적재 완료",
            "result": result.__dict__,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dart/load-corporate-actions")
async def load_corporate_actions(
    payload: CorporateActionLoadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """DART 기업 액션(분할/합병) 적재"""
    try:
        loader = RealDataLoader(db)
        result = loader.load_corporate_actions(
            start_date=payload.start_date,
            end_date=payload.end_date,
            as_of_date=payload.as_of_date or date.today(),
            corp_cls=payload.corp_cls,
            operator_id=str(current_user.id),
            operator_reason="DART 기업 액션 적재",
        )
        return {
            "status": "success",
            "message": "기업 액션 적재 완료",
            "result": result.__dict__,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data-status")
async def get_data_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW"))
):
    """DB 종목 통계"""
    from sqlalchemy import func
    from app.models.securities import Stock, ETF, Bond, DepositProduct
    
    stock_count = db.query(func.count(Stock.id)).scalar()
    etf_count = db.query(func.count(ETF.id)).scalar()
    bond_count = db.query(func.count(Bond.id)).scalar()
    deposit_count = db.query(func.count(DepositProduct.id)).scalar()
    
    return {
        "stocks": stock_count,
        "etfs": etf_count,
        "bonds": bond_count,
        "deposits": deposit_count,
        "total": stock_count + etf_count + bond_count + deposit_count
    }

@router.get("/progress/{task_id}")
async def get_progress(
    task_id: str,
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW"))
):
    """특정 작업의 진행 상황 조회"""
    progress = progress_tracker.get_progress(task_id)

    if not progress:
        raise HTTPException(status_code=404, detail="Task not found")

    # 디버그 로깅
    logger.info(f"Progress API called - task_id: {task_id}, current: {progress.get('current')}, current_item: {progress.get('current_item')}, success_count: {progress.get('success_count')}, failed_count: {progress.get('failed_count')}")

    return progress

@router.get("/progress")
async def get_all_progress(
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW"))
):
    """모든 작업의 진행 상황 조회"""
    return progress_tracker.get_all_progress()

@router.delete("/progress/{task_id}")
async def clear_progress(
    task_id: str,
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """진행 상황 제거"""
    progress_tracker.clear_task(task_id)
    return {"status": "success", "message": "Progress cleared"}

@router.get("/stocks")
async def get_stocks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW"))
):
    """적재된 주식 데이터 조회"""
    from app.models.securities import Stock

    stocks = db.query(Stock).offset(skip).limit(limit).all()
    total = db.query(Stock).count()

    return {
        "total": total,
        "items": [
            {
                "id": s.id,
                "ticker": s.ticker,
                "name": s.name,
                "current_price": float(s.current_price) if s.current_price else None,
                "market_cap": float(s.market_cap) if s.market_cap else None,
                "sector": s.sector,
                "updated_at": s.last_updated.isoformat() if s.last_updated else None
            }
            for s in stocks
        ]
    }

@router.get("/etfs")
async def get_etfs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW"))
):
    """적재된 ETF 데이터 조회"""
    from app.models.securities import ETF

    etfs = db.query(ETF).offset(skip).limit(limit).all()
    total = db.query(ETF).count()

    return {
        "total": total,
        "items": [
            {
                "id": e.id,
                "ticker": e.ticker,
                "name": e.name,
                "current_price": float(e.current_price) if e.current_price else None,
                "aum": float(e.aum) if e.aum else None,
                "expense_ratio": float(e.expense_ratio) if e.expense_ratio else None,
                "updated_at": e.last_updated.isoformat() if e.last_updated else None
            }
            for e in etfs
        ]
    }

@router.get("/bonds")
async def get_bonds(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW"))
):
    """적재된 채권 데이터 조회"""
    from app.models.securities import Bond

    bonds = db.query(Bond).offset(skip).limit(limit).all()
    total = db.query(Bond).count()

    return {
        "total": total,
        "items": [
            {
                "id": b.id,
                "name": b.name,
                "issuer": b.issuer,
                "interest_rate": float(b.interest_rate) if b.interest_rate else None,
                "maturity_years": b.maturity_years,
                "credit_rating": b.credit_rating,
                "updated_at": b.last_updated.isoformat() if b.last_updated else None
            }
            for b in bonds
        ]
    }

@router.get("/deposits")
async def get_deposits(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW"))
):
    """적재된 예적금 데이터 조회"""
    from app.models.securities import DepositProduct

    deposits = db.query(DepositProduct).offset(skip).limit(limit).all()
    total = db.query(DepositProduct).count()

    return {
        "total": total,
        "items": [
            {
                "id": d.id,
                "name": d.name,
                "bank": d.bank,
                "interest_rate": float(d.interest_rate) if d.interest_rate else None,
                "term_months": d.term_months,
                "product_type": d.product_type,
                "updated_at": d.last_updated.isoformat() if d.last_updated else None
            }
            for d in deposits
        ]
    }


# ========== Alpha Vantage 관련 엔드포인트 ==========

@router.post("/alpha-vantage/load-all-stocks")
async def load_all_alpha_vantage_stocks(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """Alpha Vantage: 인기 미국 주식 전체 적재"""
    try:
        # task_id 생성
        task_id = f"us_stocks_{uuid.uuid4().hex[:8]}"

        # 백그라운드에서 실행
        def run_stock_loading():
            logger.info(f"🚀 Background task started for task_id: {task_id}")
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                logger.info(f"📊 Creating AlphaVantageDataLoader instance")
                loader = AlphaVantageDataLoader()
                logger.info(f"📥 Calling load_all_popular_stocks with task_id: {task_id}")
                result = loader.load_all_popular_stocks(db, task_id=task_id)
                logger.info(f"✅ Background task completed: {result}")
            except Exception as e:
                logger.error(f"❌ Background task failed: {str(e)}", exc_info=True)
            finally:
                logger.info(f"🔒 Closing database session for task_id: {task_id}")
                db.close()

        background_tasks.add_task(run_stock_loading)
        logger.info(f"✅ Background task added to queue: {task_id}")

        return {
            "status": "success",
            "message": "Alpha Vantage 주식 데이터 수집 시작",
            "task_id": task_id
        }
    except Exception as e:
        logger.error(f"Alpha Vantage stock loading failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alpha-vantage/load-stock/{symbol}")
async def load_alpha_vantage_stock(
    symbol: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """Alpha Vantage: 특정 주식 적재"""
    try:
        symbol = symbol.upper()
        task_id = f"stock_{symbol.lower()}_{uuid.uuid4().hex[:8]}"

        # 백그라운드에서 실행
        def run_single_stock_loading():
            logger.info(f"🚀 Background task started for stock {symbol}, task_id: {task_id}")
            from app.database import SessionLocal
            from app.progress_tracker import progress_tracker
            db = SessionLocal()
            try:
                # 진행 상황 추적 시작 (1개 항목)
                progress_tracker.start_task(task_id, 1, f"{symbol} 주식 데이터 수집")

                progress_tracker.update_progress(
                    task_id,
                    current=1,
                    current_item=f"{symbol} 시세 수집 중...",
                    success=None
                )

                loader = AlphaVantageDataLoader()
                result = loader.load_stock_data(db, symbol)

                if result['success']:
                    progress_tracker.update_progress(
                        task_id,
                        current=1,
                        current_item=f"{symbol} - {result['message']}",
                        success=True
                    )
                else:
                    progress_tracker.update_progress(
                        task_id,
                        current=1,
                        current_item=f"{symbol} - {result['message']}",
                        success=False,
                        error=result['message']
                    )

                progress_tracker.complete_task(task_id, "completed")
                logger.info(f"✅ Background task completed for {symbol}: {result}")
            except Exception as e:
                logger.error(f"❌ Background task failed for {symbol}: {str(e)}", exc_info=True)
                progress_tracker.update_progress(
                    task_id,
                    current=1,
                    current_item=f"{symbol} - 오류 발생",
                    success=False,
                    error=str(e)
                )
                progress_tracker.complete_task(task_id, "failed")
            finally:
                logger.info(f"🔒 Closing database session for task_id: {task_id}")
                db.close()

        background_tasks.add_task(run_single_stock_loading)
        logger.info(f"✅ Background task added to queue for {symbol}: {task_id}")

        return {
            "status": "success",
            "message": f"{symbol} 주식 데이터 수집 시작",
            "task_id": task_id
        }
    except Exception as e:
        logger.error(f"Alpha Vantage stock loading failed for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alpha-vantage/load-financials/{symbol}")
async def load_alpha_vantage_financials(
    symbol: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """Alpha Vantage: 특정 주식의 재무제표 적재"""
    try:
        symbol = symbol.upper()
        task_id = f"financials_{symbol.lower()}_{uuid.uuid4().hex[:8]}"

        # 백그라운드에서 실행
        def run_financials_loading():
            logger.info(f"🚀 Background task started for financials {symbol}, task_id: {task_id}")
            from app.database import SessionLocal
            from app.progress_tracker import progress_tracker
            db = SessionLocal()
            try:
                # 진행 상황 추적 시작 (1개 항목)
                progress_tracker.start_task(task_id, 1, f"{symbol} 재무제표 수집")

                progress_tracker.update_progress(
                    task_id,
                    current=1,
                    current_item=f"{symbol} 재무제표 수집 중...",
                    success=None
                )

                loader = AlphaVantageDataLoader()
                result = loader.load_financials(db, symbol)

                if result['success']:
                    progress_tracker.update_progress(
                        task_id,
                        current=1,
                        current_item=f"{symbol} - {result['message']}",
                        success=True
                    )
                else:
                    progress_tracker.update_progress(
                        task_id,
                        current=1,
                        current_item=f"{symbol} - {result['message']}",
                        success=False,
                        error=result['message']
                    )

                progress_tracker.complete_task(task_id, "completed")
                logger.info(f"✅ Background task completed for financials {symbol}: {result}")
            except Exception as e:
                logger.error(f"❌ Background task failed for financials {symbol}: {str(e)}", exc_info=True)
                progress_tracker.update_progress(
                    task_id,
                    current=1,
                    current_item=f"{symbol} 재무제표 - 오류 발생",
                    success=False,
                    error=str(e)
                )
                progress_tracker.complete_task(task_id, "failed")
            finally:
                logger.info(f"🔒 Closing database session for task_id: {task_id}")
                db.close()

        background_tasks.add_task(run_financials_loading)
        logger.info(f"✅ Background task added to queue for financials {symbol}: {task_id}")

        return {
            "status": "success",
            "message": f"{symbol} 재무제표 수집 시작",
            "task_id": task_id
        }
    except Exception as e:
        logger.error(f"Alpha Vantage financials loading failed for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alpha-vantage/load-all-etfs")
async def load_all_alpha_vantage_etfs(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """Alpha Vantage: 인기 미국 ETF 전체 적재"""
    try:
        # task_id 생성
        task_id = f"us_etfs_{uuid.uuid4().hex[:8]}"

        # 백그라운드에서 실행
        def run_etf_loading():
            logger.info(f"🚀 Background task started for task_id: {task_id}")
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                logger.info(f"📊 Creating AlphaVantageDataLoader instance")
                loader = AlphaVantageDataLoader()
                logger.info(f"📥 Calling load_all_popular_etfs with task_id: {task_id}")
                result = loader.load_all_popular_etfs(db, task_id=task_id)
                logger.info(f"✅ Background task completed: {result}")
            except Exception as e:
                logger.error(f"❌ Background task failed: {str(e)}", exc_info=True)
            finally:
                logger.info(f"🔒 Closing database session for task_id: {task_id}")
                db.close()

        background_tasks.add_task(run_etf_loading)
        logger.info(f"✅ Background task added to queue: {task_id}")

        return {
            "status": "success",
            "message": "Alpha Vantage ETF 데이터 수집 시작",
            "task_id": task_id
        }
    except Exception as e:
        logger.error(f"Alpha Vantage ETF loading failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alpha-vantage/stocks")
async def get_alpha_vantage_stocks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW"))
):
    """Alpha Vantage: 적재된 미국 주식 데이터 조회"""
    from app.models.alpha_vantage import AlphaVantageStock

    stocks = db.query(AlphaVantageStock).offset(skip).limit(limit).all()
    total = db.query(AlphaVantageStock).count()

    return {
        "total": total,
        "items": [
            {
                "id": s.id,
                "symbol": s.symbol,
                "name": s.name,
                "sector": s.sector,
                "current_price": float(s.current_price) if s.current_price else None,
                "market_cap": float(s.market_cap) if s.market_cap else None,
                "pe_ratio": float(s.pe_ratio) if s.pe_ratio else None,
                "dividend_yield": float(s.dividend_yield) if s.dividend_yield else None,
                "risk_level": s.risk_level,
                "category": s.category,
                "updated_at": s.last_updated.isoformat() if s.last_updated else None
            }
            for s in stocks
        ]
    }


@router.get("/alpha-vantage/financials/{symbol}")
async def get_alpha_vantage_financials(
    symbol: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW"))
):
    """Alpha Vantage: 특정 주식의 재무제표 조회"""
    from app.models.alpha_vantage import AlphaVantageFinancials

    financials = db.query(AlphaVantageFinancials).filter(
        AlphaVantageFinancials.symbol == symbol.upper()
    ).order_by(AlphaVantageFinancials.fiscal_date.desc()).all()

    return {
        "symbol": symbol.upper(),
        "total": len(financials),
        "items": [
            {
                "fiscal_date": f.fiscal_date.isoformat(),
                "report_type": f.report_type,
                "revenue": float(f.revenue) if f.revenue else None,
                "net_income": float(f.net_income) if f.net_income else None,
                "eps": float(f.eps) if f.eps else None,
                "total_assets": float(f.total_assets) if f.total_assets else None,
                "total_equity": float(f.total_equity) if f.total_equity else None,
                "roe": float(f.roe) if f.roe else None,
                "roa": float(f.roa) if f.roa else None,
                "profit_margin": float(f.profit_margin) if f.profit_margin else None,
            }
            for f in financials
        ]
    }


@router.post("/alpha-vantage/load-all-timeseries")
async def load_all_alpha_vantage_timeseries(
    background_tasks: BackgroundTasks,
    outputsize: str = 'compact',  # 'compact' (최근 100일) or 'full' (20년)
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """Alpha Vantage: 모든 인기 주식/ETF 시계열 데이터 수집 (Background)

    - outputsize='compact': 최근 100일 데이터 (빠름)
    - outputsize='full': 전체 데이터 최대 20년 (느림, API 호출 많음)
    """
    import uuid
    from app.services.alpha_vantage_loader import AlphaVantageDataLoader

    task_id = f"us_timeseries_{uuid.uuid4().hex[:8]}"
    logger.info(f"⏰ Creating background task for Alpha Vantage time series, task_id: {task_id}")

    try:
        def run_timeseries_loading():
            logger.info(f"🚀 Background task started for Alpha Vantage time series, task_id: {task_id}")
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                logger.info(f"📊 Creating AlphaVantageDataLoader instance")
                loader = AlphaVantageDataLoader()
                logger.info(f"📥 Calling load_all_time_series with task_id: {task_id}, outputsize: {outputsize}")
                result = loader.load_all_time_series(db, task_id=task_id, outputsize=outputsize)
                logger.info(f"✅ Background task completed: {result}")
            except Exception as e:
                logger.error(f"❌ Background task failed: {str(e)}", exc_info=True)
            finally:
                logger.info(f"🔒 Closing database session for task_id: {task_id}")
                db.close()

        background_tasks.add_task(run_timeseries_loading)
        logger.info(f"✅ Background task added to queue: {task_id}")

        return {
            "status": "success",
            "message": f"Alpha Vantage 시계열 데이터 수집 시작 (outputsize={outputsize})",
            "task_id": task_id,
            "note": "compact는 최근 100일, full은 최대 20년 데이터를 수집합니다. API 호출 제한으로 인해 시간이 오래 걸릴 수 있습니다."
        }
    except Exception as e:
        logger.error(f"Alpha Vantage time series loading failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alpha-vantage/load-timeseries/{symbol}")
async def load_alpha_vantage_timeseries(
    symbol: str,
    background_tasks: BackgroundTasks,
    outputsize: str = 'compact',
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """Alpha Vantage: 특정 종목의 시계열 데이터 수집 (Background)"""
    import uuid
    from app.services.alpha_vantage_loader import AlphaVantageDataLoader

    task_id = f"us_timeseries_{symbol}_{uuid.uuid4().hex[:8]}"

    try:
        def run_timeseries_loading():
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                from app.progress_tracker import progress_tracker
                progress_tracker.start_task(task_id, 1, f"{symbol} 시계열 데이터 수집")

                progress_tracker.update_progress(
                    task_id,
                    current=1,
                    current_item=f"{symbol} 시계열 수집 중...",
                    success=None
                )

                loader = AlphaVantageDataLoader()
                result = loader.load_time_series_data(db, symbol, outputsize)

                if result['success']:
                    progress_tracker.update_progress(
                        task_id,
                        current=1,
                        current_item=f"{symbol} - {result['message']}",
                        success=True
                    )
                else:
                    progress_tracker.update_progress(
                        task_id,
                        current=1,
                        current_item=f"{symbol} - {result['message']}",
                        success=False,
                        error=result['message']
                    )

                progress_tracker.complete_task(task_id, "completed")
            except Exception as e:
                logger.error(f"Background task failed for {symbol} time series: {str(e)}", exc_info=True)
            finally:
                db.close()

        background_tasks.add_task(run_timeseries_loading)

        return {
            "status": "success",
            "message": f"{symbol} 시계열 데이터 수집 시작",
            "task_id": task_id
        }
    except Exception as e:
        logger.error(f"Time series loading failed for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alpha-vantage/data-status")
async def get_alpha_vantage_data_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW"))
):
    """Alpha Vantage: DB 통계"""
    from sqlalchemy import func
    from app.models.alpha_vantage import AlphaVantageStock, AlphaVantageETF, AlphaVantageFinancials, AlphaVantageTimeSeries

    stock_count = db.query(func.count(AlphaVantageStock.id)).scalar()
    etf_count = db.query(func.count(AlphaVantageETF.id)).scalar()
    financials_count = db.query(func.count(AlphaVantageFinancials.id)).scalar()
    timeseries_count = db.query(func.count(AlphaVantageTimeSeries.id)).scalar()

    # 시계열 데이터가 있는 고유 심볼 수
    timeseries_symbols = db.query(func.count(func.distinct(AlphaVantageTimeSeries.symbol))).scalar()

    return {
        "stocks": stock_count,
        "etfs": etf_count,
        "financials": financials_count,
        "timeseries_records": timeseries_count,
        "timeseries_symbols": timeseries_symbols,
        "total": stock_count + etf_count
    }


# ========== pykrx (한국 주식) 관련 엔드포인트 ==========

@router.post("/pykrx/load-all-stocks")
async def load_all_pykrx_stocks(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """pykrx: 인기 한국 주식 전체 적재"""
    try:
        task_id = f"pykrx_stocks_{uuid.uuid4().hex[:8]}"

        # 백그라운드에서 실행
        def run_pykrx_stock_loading():
            logger.info(f"🚀 Background task started for pykrx stocks, task_id: {task_id}")
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                loader = PyKrxDataLoader()
                result = loader.load_all_popular_stocks(db, task_id=task_id)
                logger.info(f"✅ Background task completed for pykrx stocks: {result}")
            except Exception as e:
                logger.error(f"❌ Background task failed for pykrx stocks: {str(e)}", exc_info=True)
            finally:
                logger.info(f"🔒 Closing database session for task_id: {task_id}")
                db.close()

        background_tasks.add_task(run_pykrx_stock_loading)
        logger.info(f"✅ Background task added to queue for pykrx stocks: {task_id}")

        return {
            "status": "success",
            "message": "pykrx 한국 주식 데이터 수집 시작",
            "task_id": task_id
        }
    except Exception as e:
        logger.error(f"pykrx stock loading failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pykrx/load-stock/{ticker}")
async def load_pykrx_stock(
    ticker: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """pykrx: 특정 한국 주식 적재"""
    try:
        task_id = f"pykrx_stock_{ticker}_{uuid.uuid4().hex[:8]}"

        # 백그라운드에서 실행
        def run_single_pykrx_stock_loading():
            logger.info(f"🚀 Background task started for pykrx stock {ticker}, task_id: {task_id}")
            from app.database import SessionLocal
            from app.progress_tracker import progress_tracker
            db = SessionLocal()
            try:
                # 진행 상황 추적 시작 (1개 항목)
                progress_tracker.start_task(task_id, 1, f"{ticker} pykrx 주식 데이터 수집")

                progress_tracker.update_progress(
                    task_id,
                    current=1,
                    current_item=f"{ticker} 데이터 수집 중...",
                    success=None
                )

                loader = PyKrxDataLoader()
                result = loader.load_stock_data(db, ticker)

                if result['success']:
                    progress_tracker.update_progress(
                        task_id,
                        current=1,
                        current_item=f"{ticker} - {result['message']}",
                        success=True
                    )
                else:
                    progress_tracker.update_progress(
                        task_id,
                        current=1,
                        current_item=f"{ticker} - {result['message']}",
                        success=False,
                        error=result['message']
                    )

                progress_tracker.complete_task(task_id, "completed")
                logger.info(f"✅ Background task completed for pykrx stock {ticker}: {result}")
            except Exception as e:
                logger.error(f"❌ Background task failed for pykrx stock {ticker}: {str(e)}", exc_info=True)
                progress_tracker.update_progress(
                    task_id,
                    current=1,
                    current_item=f"{ticker} - 오류 발생",
                    success=False,
                    error=str(e)
                )
                progress_tracker.complete_task(task_id, "failed")
            finally:
                logger.info(f"🔒 Closing database session for task_id: {task_id}")
                db.close()

        background_tasks.add_task(run_single_pykrx_stock_loading)
        logger.info(f"✅ Background task added to queue for pykrx stock {ticker}: {task_id}")

        return {
            "status": "success",
            "message": f"{ticker} pykrx 주식 데이터 수집 시작",
            "task_id": task_id
        }
    except Exception as e:
        logger.error(f"pykrx stock loading failed for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pykrx/load-all-etfs")
async def load_all_pykrx_etfs(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """pykrx: 인기 한국 ETF 전체 적재"""
    try:
        task_id = f"pykrx_etfs_{uuid.uuid4().hex[:8]}"

        # 백그라운드에서 실행
        def run_pykrx_etf_loading():
            logger.info(f"🚀 Background task started for pykrx ETFs, task_id: {task_id}")
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                loader = PyKrxDataLoader()
                result = loader.load_all_popular_etfs(db, task_id=task_id)
                logger.info(f"✅ Background task completed for pykrx ETFs: {result}")
            except Exception as e:
                logger.error(f"❌ Background task failed for pykrx ETFs: {str(e)}", exc_info=True)
            finally:
                logger.info(f"🔒 Closing database session for task_id: {task_id}")
                db.close()

        background_tasks.add_task(run_pykrx_etf_loading)
        logger.info(f"✅ Background task added to queue for pykrx ETFs: {task_id}")

        return {
            "status": "success",
            "message": "pykrx 한국 ETF 데이터 수집 시작",
            "task_id": task_id
        }
    except Exception as e:
        logger.error(f"pykrx ETF loading failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pykrx/load-etf/{ticker}")
async def load_pykrx_etf(
    ticker: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """pykrx: 특정 한국 ETF 적재"""
    try:
        task_id = f"pykrx_etf_{ticker}_{uuid.uuid4().hex[:8]}"

        # 백그라운드에서 실행
        def run_single_pykrx_etf_loading():
            logger.info(f"🚀 Background task started for pykrx ETF {ticker}, task_id: {task_id}")
            from app.database import SessionLocal
            from app.progress_tracker import progress_tracker
            db = SessionLocal()
            try:
                # 진행 상황 추적 시작 (1개 항목)
                progress_tracker.start_task(task_id, 1, f"{ticker} pykrx ETF 데이터 수집")

                progress_tracker.update_progress(
                    task_id,
                    current=1,
                    current_item=f"{ticker} ETF 데이터 수집 중...",
                    success=None
                )

                loader = PyKrxDataLoader()
                result = loader.load_etf_data(db, ticker)

                if result['success']:
                    progress_tracker.update_progress(
                        task_id,
                        current=1,
                        current_item=f"{ticker} - {result['message']}",
                        success=True
                    )
                else:
                    progress_tracker.update_progress(
                        task_id,
                        current=1,
                        current_item=f"{ticker} - {result['message']}",
                        success=False,
                        error=result['message']
                    )

                progress_tracker.complete_task(task_id, "completed")
                logger.info(f"✅ Background task completed for pykrx ETF {ticker}: {result}")
            except Exception as e:
                logger.error(f"❌ Background task failed for pykrx ETF {ticker}: {str(e)}", exc_info=True)
                progress_tracker.update_progress(
                    task_id,
                    current=1,
                    current_item=f"{ticker} ETF - 오류 발생",
                    success=False,
                    error=str(e)
                )
                progress_tracker.complete_task(task_id, "failed")
            finally:
                logger.info(f"🔒 Closing database session for task_id: {task_id}")
                db.close()

        background_tasks.add_task(run_single_pykrx_etf_loading)
        logger.info(f"✅ Background task added to queue for pykrx ETF {ticker}: {task_id}")

        return {
            "status": "success",
            "message": f"{ticker} pykrx ETF 데이터 수집 시작",
            "task_id": task_id
        }
    except Exception as e:
        logger.error(f"pykrx ETF loading failed for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pykrx/load-all-financials")
async def load_all_pykrx_financials(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """pykrx: 인기 한국 주식 전체 재무제표 적재"""
    try:
        task_id = f"pykrx_financials_{uuid.uuid4().hex[:8]}"

        # 백그라운드에서 실행
        def run_all_pykrx_financials_loading():
            logger.info(f"🚀 Background task started for all pykrx financials, task_id: {task_id}")
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                loader = PyKrxDataLoader()
                result = loader.load_all_stock_financials(db, task_id=task_id)
                logger.info(f"✅ Background task completed for all pykrx financials: {result}")
            except Exception as e:
                logger.error(f"❌ Background task failed for all pykrx financials: {str(e)}", exc_info=True)
                from app.progress_tracker import progress_tracker
                progress_tracker.complete_task(task_id, "failed")
            finally:
                logger.info(f"🔒 Closing database session for task_id: {task_id}")
                db.close()

        background_tasks.add_task(run_all_pykrx_financials_loading)
        logger.info(f"✅ Background task added to queue for all pykrx financials: {task_id}")

        return {
            "status": "success",
            "message": "한국 주식 재무제표 전체 수집 시작",
            "task_id": task_id
        }
    except Exception as e:
        logger.error(f"All pykrx financials loading failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pykrx/load-financials/{ticker}")
async def load_pykrx_financials(
    ticker: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """pykrx: 특정 한국 주식 재무제표 적재"""
    try:
        task_id = f"pykrx_financials_{ticker}_{uuid.uuid4().hex[:8]}"

        # 백그라운드에서 실행
        def run_single_pykrx_financials_loading():
            logger.info(f"🚀 Background task started for pykrx financials {ticker}, task_id: {task_id}")
            from app.database import SessionLocal
            from app.progress_tracker import progress_tracker
            db = SessionLocal()
            try:
                # 진행 상황 추적 시작 (1개 항목)
                progress_tracker.start_task(task_id, 1, f"{ticker} pykrx 재무제표 수집")

                progress_tracker.update_progress(
                    task_id,
                    current=1,
                    current_item=f"{ticker} 재무제표 수집 중...",
                    success=None
                )

                loader = PyKrxDataLoader()
                result = loader.load_stock_financials(db, ticker)

                if result['success']:
                    progress_tracker.update_progress(
                        task_id,
                        current=1,
                        current_item=f"{ticker} - {result['message']}",
                        success=True
                    )
                else:
                    progress_tracker.update_progress(
                        task_id,
                        current=1,
                        current_item=f"{ticker} - {result['message']}",
                        success=False,
                        error=result['message']
                    )

                progress_tracker.complete_task(task_id, "completed")
                logger.info(f"✅ Background task completed for pykrx financials {ticker}: {result}")
            except Exception as e:
                logger.error(f"❌ Background task failed for pykrx financials {ticker}: {str(e)}", exc_info=True)
                progress_tracker.update_progress(
                    task_id,
                    current=1,
                    current_item=f"{ticker} 재무제표 - 오류 발생",
                    success=False,
                    error=str(e)
                )
                progress_tracker.complete_task(task_id, "failed")
            finally:
                logger.info(f"🔒 Closing database session for task_id: {task_id}")
                db.close()

        background_tasks.add_task(run_single_pykrx_financials_loading)
        logger.info(f"✅ Background task added to queue for pykrx financials {ticker}: {task_id}")

        return {
            "status": "success",
            "message": f"{ticker} pykrx 재무제표 수집 시작",
            "task_id": task_id
        }
    except Exception as e:
        logger.error(f"pykrx financials loading failed for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 재무 분석 엔드포인트 ==========

@router.get("/financial-analysis/{symbol}")
async def analyze_stock_financials(
    symbol: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW"))
):
    """
    종목 재무 분석
    - symbol: 종목 심볼 (예: AAPL)
    - 출력: 성장률(CAGR), 마진, ROE, 부채비율, FCF 마진, 배당 분석 등
    """
    try:
        result = FinancialAnalyzer.analyze_stock(db, symbol.upper())

        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["message"])

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Financial analysis failed for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/financial-analysis/compare")
async def compare_stocks_financials(
    symbols: List[str],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """
    여러 종목 재무 비교 분석
    - symbols: 비교할 종목 심볼 리스트 (예: ["AAPL", "GOOGL", "MSFT"])
    """
    try:
        if not symbols or len(symbols) < 2:
            raise HTTPException(status_code=400, detail="최소 2개 이상의 종목을 입력하세요")

        if len(symbols) > 10:
            raise HTTPException(status_code=400, detail="최대 10개 종목까지 비교 가능합니다")

        result = FinancialAnalyzer.compare_stocks(db, symbols)

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stock comparison failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/financial-score/{symbol}")
async def get_stock_financial_score(
    symbol: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW"))
):
    """
    종목 재무 건전성 점수 (100점 만점)
    - symbol: 종목 심볼 (예: AAPL)
    - 출력: 종합 점수, 등급 (A~F), 세부 점수
    """
    try:
        result = FinancialAnalyzer.get_financial_score(db, symbol.upper())

        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["message"])

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Financial score calculation failed for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/financial-score-v2/{symbol}")
async def get_stock_financial_score_v2(
    symbol: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW"))
):
    """
    개선된 재무 건전성 점수 V2 (성숙한 대형주/성장주 적합)
    - symbol: 종목 심볼 (예: AAPL)
    - 성장성: 3년+5년 가중 평균 (기준 완화)
    - 안정성: 고ROE 기업은 부채비율 기준 완화
    - 주주환원: 낮은 배당도 점수 부여
    - 투자 스타일 자동 분류 포함
    """
    try:
        result = FinancialAnalyzer.get_financial_score_v2(db, symbol.upper())

        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["message"])

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Financial score V2 calculation failed for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Valuation Endpoints
# ============================================================

@router.get("/valuation/multiples/{symbol}")
async def get_valuation_multiples(symbol: str, db: Session = Depends(get_db)):
    """
    멀티플 비교 분석
    - PER, PBR, 배당수익률을 업종/시장 평균과 비교
    """
    from app.services.valuation import ValuationAnalyzer

    try:
        result = ValuationAnalyzer.compare_multiples(db, symbol.upper())
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Multiples comparison failed for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/valuation/dcf/{symbol}")
async def get_dcf_valuation(symbol: str, db: Session = Depends(get_db)):
    """
    DCF (Discounted Cash Flow) 밸류에이션
    - 보수적/중립적/낙관적 3가지 시나리오
    """
    from app.services.valuation import ValuationAnalyzer

    try:
        result = ValuationAnalyzer.dcf_valuation(db, symbol.upper())
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"DCF valuation failed for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/valuation/ddm/{symbol}")
async def get_ddm_valuation(symbol: str, db: Session = Depends(get_db)):
    """
    배당할인모형 (DDM - Dividend Discount Model)
    - Gordon Growth Model 사용
    - 꾸준한 배당 지급 기업에 적합
    """
    from app.services.valuation import ValuationAnalyzer

    try:
        result = ValuationAnalyzer.dividend_discount_model(db, symbol.upper())
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"DDM valuation failed for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/valuation/comprehensive/{symbol}")
async def get_comprehensive_valuation(symbol: str, db: Session = Depends(get_db)):
    """
    종합 밸류에이션 분석
    - 멀티플 비교, DCF, DDM 통합
    - 가치 평가 참고치 포함
    """
    from app.services.valuation import ValuationAnalyzer

    try:
        result = ValuationAnalyzer.comprehensive_valuation(db, symbol.upper())
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Comprehensive valuation failed for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Quant Analysis Endpoints
# ============================================================

@router.get("/quant/comprehensive/{symbol}")
async def get_comprehensive_quant_analysis(
    symbol: str,
    market_symbol: str = "SPY",
    days: int = 252,
    db: Session = Depends(get_db)
):
    """
    종합 퀀트 분석
    - 기술적 지표: 이동평균, RSI, 볼린저밴드, MACD
    - 리스크 지표: 변동성, 최대 낙폭, 샤프 비율
    - 시장 대비: 베타, 알파, 트래킹 에러

    Parameters:
    - symbol: 분석할 종목 심볼
    - market_symbol: 벤치마크 심볼 (기본: SPY)
    - days: 분석 기간 (기본: 252일 = 1년)
    """
    from app.services.quant_analyzer import QuantAnalyzer

    try:
        result = QuantAnalyzer.comprehensive_quant_analysis(
            db, symbol.upper(), market_symbol.upper(), days
        )

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quant analysis failed for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quant/technical/{symbol}")
async def get_technical_indicators(
    symbol: str,
    days: int = 252,
    db: Session = Depends(get_db)
):
    """
    기술적 지표 분석
    - 이동평균선 (MA20, MA50, MA200)
    - RSI (14일)
    - 볼린저 밴드
    - MACD
    """
    from app.services.quant_analyzer import QuantAnalyzer

    try:
        prices = QuantAnalyzer.get_price_data(db, symbol.upper(), days)

        if not prices:
            raise HTTPException(status_code=404, detail=f"{symbol} 데이터 없음")

        result = {
            "symbol": symbol.upper(),
            "period_days": days,
            "data_points": len(prices),
            "current_price": prices[-1][1],
            "moving_averages": QuantAnalyzer.calculate_moving_averages(prices),
            "rsi": QuantAnalyzer.calculate_rsi(prices),
            "bollinger_bands": QuantAnalyzer.calculate_bollinger_bands(prices),
            "macd": QuantAnalyzer.calculate_macd(prices)
        }

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Technical analysis failed for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quant/risk/{symbol}")
async def get_risk_metrics(
    symbol: str,
    market_symbol: str = "SPY",
    days: int = 252,
    db: Session = Depends(get_db)
):
    """
    리스크 지표 분석
    - 변동성
    - 최대 낙폭 (MDD)
    - 샤프 비율
    - 베타 (시장 대비)
    - 알파 (시장 대비 초과 수익)
    - 트래킹 에러
    """
    from app.services.quant_analyzer import QuantAnalyzer

    try:
        stock_prices = QuantAnalyzer.get_price_data(db, symbol.upper(), days)
        market_prices = QuantAnalyzer.get_price_data(db, market_symbol.upper(), days)

        if not stock_prices:
            raise HTTPException(status_code=404, detail=f"{symbol} 데이터 없음")

        stock_returns = QuantAnalyzer.calculate_returns(stock_prices)
        market_returns = QuantAnalyzer.calculate_returns(market_prices) if market_prices else []

        result = {
            "symbol": symbol.upper(),
            "market_benchmark": market_symbol.upper(),
            "period_days": days,
            "volatility": QuantAnalyzer.calculate_volatility(stock_returns),
            "max_drawdown": QuantAnalyzer.calculate_max_drawdown(stock_prices),
            "sharpe_ratio": QuantAnalyzer.calculate_sharpe_ratio(stock_returns)
        }

        if market_returns:
            result["beta"] = QuantAnalyzer.calculate_beta(stock_returns, market_returns)
            result["alpha"] = QuantAnalyzer.calculate_alpha(stock_returns, market_returns)
            result["tracking_error"] = QuantAnalyzer.calculate_tracking_error(stock_returns, market_returns)

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Risk metrics calculation failed for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Report Generation Endpoints
# ============================================================

@router.get("/report/comprehensive/{symbol}")
async def get_comprehensive_report(
    symbol: str,
    market_symbol: str = "SPY",
    days: int = 252,
    db: Session = Depends(get_db)
):
    """
    종합 투자 리포트 생성
    - 재무 분석, 밸류에이션, 퀀트 분석 통합
    - 점수화 및 등급화 (매수/매도 권고 없음)
    - 객관적 평가 및 비교 분석

    Parameters:
    - symbol: 분석할 종목 심볼
    - market_symbol: 벤치마크 심볼 (기본: SPY)
    - days: 분석 기간 (기본: 252일 = 1년)

    Returns:
    - 재무 건전성 등급
    - 밸류에이션 범주 (저평가/적정/고평가)
    - 리스크 수준 (1-5단계)
    - 시장 대비 성과 범주
    - 종합 평가 (강점/우려 사항)

    주의: 본 리포트는 투자 권고가 아닌 객관적 분석 정보입니다.
    """
    from app.services.report_generator import ReportGenerator

    try:
        report = ReportGenerator.generate_comprehensive_report(
            db, symbol.upper(), market_symbol.upper(), days
        )
        return report
    except Exception as e:
        logger.error(f"Report generation failed for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/report/comparison")
async def get_comparison_report(
    symbols: List[str],
    db: Session = Depends(get_db)
):
    """
    여러 종목 비교 리포트
    - 최대 5개 종목 비교
    - 재무 점수, 밸류에이션 등급 비교

    Parameters:
    - symbols: 비교할 종목 리스트 (최대 5개)
    """
    from app.services.report_generator import ReportGenerator

    try:
        if len(symbols) > 5:
            raise HTTPException(
                status_code=400,
                detail="최대 5개 종목까지 비교 가능합니다"
            )

        report = ReportGenerator.generate_comparison_report(db, symbols)
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Comparison report failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 정성적 분석 (Qualitative Analysis - AI)
# ============================================================

@router.get("/qualitative/news-sentiment/{symbol}")
async def get_news_sentiment(symbol: str):
    """
    뉴스 감성 분석 (AI 기반)

    **기능**:
    - Alpha Vantage News API로 최근 뉴스 수집
    - Claude AI로 감성 분석 (긍정/중립/부정)
    - 주요 긍정/부정 요인 추출
    - 핵심 이슈 식별

    **중요**: 투자 권고가 아닌 객관적 정보만 제공
    """
    from app.services.qualitative_analyzer import QualitativeAnalyzer

    try:
        analysis = QualitativeAnalyzer.get_comprehensive_news_analysis(symbol.upper())
        return analysis
    except Exception as e:
        logger.error(f"News sentiment analysis failed for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# User Management Endpoints
# ============================================================

@router.get("/users")
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW"))
):
    """
    모든 사용자 목록 조회 (관리자 전용)

    Parameters:
    - skip: 건너뛸 레코드 수
    - limit: 조회할 최대 레코드 수

    Returns:
    - 사용자 목록 (이메일, 이름, 역할, 가입일 등)
    """
    try:
        users = db.query(User).offset(skip).limit(limit).all()
        total = db.query(User).count()

        return {
            "total": total,
            "items": [
                {
                    "id": u.id,
                    "email": u.email,
                    "name": u.name,
                    "phone": u.phone,
                    "birth_date": u.birth_date.isoformat() if u.birth_date else None,
                    "occupation": u.occupation,
                    "company": u.company,
                    "annual_income": u.annual_income,
                    "total_assets": u.total_assets,
                    "city": u.city,
                    "district": u.district,
                    "investment_experience": u.investment_experience,
                    "investment_goal": u.investment_goal,
                    "risk_tolerance": u.risk_tolerance,
                    "role": u.role,
                    "vip_tier": getattr(u, "vip_tier", "bronze"),
                    "activity_points": getattr(u, "activity_points", 0),
                    "membership_plan": getattr(u, "membership_plan", "free"),
                    "created_at": u.created_at.isoformat() if u.created_at else None
                }
                for u in users
            ]
        }
    except Exception as e:
        logger.error(f"Failed to fetch users: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_ROLE_MANAGE"))
):
    """
    사용자 역할 변경 (관리자 전용)

    Parameters:
    - user_id: 변경할 사용자 ID
    - role: 새로운 역할 ("user" 또는 "admin")

    Returns:
    - 업데이트된 사용자 정보
    """
    try:
        # 역할 유효성 검증
        if role not in ["user", "admin"]:
            raise HTTPException(
                status_code=400,
                detail="역할은 'user' 또는 'admin'만 가능합니다"
            )

        # 사용자 조회
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="사용자를 찾을 수 없습니다"
            )

        # 자기 자신의 역할은 변경할 수 없음
        if user.id == current_user.id:
            raise HTTPException(
                status_code=400,
                detail="자신의 역할은 변경할 수 없습니다"
            )

        # 역할 업데이트
        old_role = user.role
        user.role = role
        db.commit()
        db.refresh(user)

        logger.info(f"User role updated: {user.email} ({old_role} -> {role}) by {current_user.email}")

        return {
            "success": True,
            "message": f"사용자 역할이 {old_role}에서 {role}로 변경되었습니다",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update user role: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """
    사용자 삭제 (관리자 전용)

    Parameters:
    - user_id: 삭제할 사용자 ID

    Returns:
    - 삭제 성공 메시지
    """
    try:
        # 사용자 조회
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="사용자를 찾을 수 없습니다"
            )

        # 자기 자신은 삭제할 수 없음
        if user.id == current_user.id:
            raise HTTPException(
                status_code=400,
                detail="자신의 계정은 삭제할 수 없습니다"
            )

        # 사용자 삭제
        user_email = user.email
        db.delete(user)
        db.commit()

        logger.info(f"User deleted: {user_email} by {current_user.email}")

        return {
            "success": True,
            "message": f"사용자 {user_email}가 삭제되었습니다"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
