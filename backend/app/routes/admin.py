# backend/app/routes/admin.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.data_loader import DataLoaderService
from app.models import User
from app.auth import get_current_user
from app.progress_tracker import progress_tracker
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

def is_admin(current_user: User = Depends(get_current_user)) -> User:
    """관리자 확인 (현재는 로그인한 사용자 모두 허용)"""
    # TODO: 프로덕션에서는 is_admin 필드 체크 필요
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="관리자만 접근 가능")
    return current_user

@router.post("/load-data")
async def load_all_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
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
    current_user: User = Depends(is_admin)
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
    current_user: User = Depends(is_admin)
):
    """ETF 데이터만 적재"""
    try:
        result = DataLoaderService.load_etfs(db)
        return {
            "status": "success",
            "message": "ETF 데이터 적재 완료",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data-status")
async def get_data_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
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
    current_user: User = Depends(is_admin)
):
    """특정 작업의 진행 상황 조회"""
    progress = progress_tracker.get_progress(task_id)

    if not progress:
        raise HTTPException(status_code=404, detail="Task not found")

    return progress

@router.get("/progress")
async def get_all_progress(
    current_user: User = Depends(is_admin)
):
    """모든 작업의 진행 상황 조회"""
    return progress_tracker.get_all_progress()

@router.delete("/progress/{task_id}")
async def clear_progress(
    task_id: str,
    current_user: User = Depends(is_admin)
):
    """진행 상황 제거"""
    progress_tracker.clear_task(task_id)
    return {"status": "success", "message": "Progress cleared"}

@router.get("/stocks")
async def get_stocks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
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
    current_user: User = Depends(is_admin)
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
    current_user: User = Depends(is_admin)
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
    current_user: User = Depends(is_admin)
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