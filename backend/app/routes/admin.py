# backend/app/routes/admin.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.data_loader import DataLoaderService
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

def is_admin(current_user: User = Depends(get_current_user)) -> User:
    """관리자 확인"""
    if not current_user.is_admin:  # User 모델에 is_admin 필드 필요
        raise HTTPException(status_code=403, detail="관리자만 접근 가능")
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
        result = DataLoaderService.load_korean_stocks(db)
        return {
            "status": "success",
            "message": "주식 데이터 적재 완료",
            "result": result
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