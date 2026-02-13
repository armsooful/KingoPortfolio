"""
관심 종목 (Watchlist) CRUD API
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.watchlist import Watchlist
from app.models.securities import Stock
from app.routes.auth import get_current_user

router = APIRouter(
    prefix="/api/v1/watchlist",
    tags=["Watchlist"],
)

MAX_WATCHLIST_SIZE = 50


class AddWatchlistRequest(BaseModel):
    ticker: str


@router.get("/")
async def get_watchlist(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """관심 종목 목록 (최신 점수 포함)"""
    rows = (
        db.query(Watchlist, Stock)
        .join(Stock, Watchlist.ticker == Stock.ticker)
        .filter(Watchlist.user_id == current_user.id)
        .order_by(Watchlist.created_at.desc())
        .all()
    )

    items = []
    for w, s in rows:
        score_change = None
        if w.last_notified_score is not None and s.compass_score is not None:
            score_change = round(s.compass_score - w.last_notified_score, 1)

        items.append({
            "ticker": w.ticker,
            "name": s.name,
            "market": s.market,
            "current_price": s.current_price,
            "compass_score": s.compass_score,
            "compass_grade": s.compass_grade,
            "compass_summary": s.compass_summary,
            "last_notified_score": w.last_notified_score,
            "last_notified_grade": w.last_notified_grade,
            "score_change": score_change,
            "created_at": w.created_at,
        })

    return {"items": items, "count": len(items)}


@router.post("/")
async def add_to_watchlist(
    body: AddWatchlistRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """관심 종목 추가 (최대 50개)"""
    ticker = body.ticker.strip()

    # 종목 존재 확인
    stock = db.query(Stock).filter(Stock.ticker == ticker).first()
    if not stock:
        raise HTTPException(status_code=404, detail="존재하지 않는 종목입니다.")

    # 중복 확인
    existing = db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id,
        Watchlist.ticker == ticker,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="이미 관심 종목에 등록되어 있습니다.")

    # 최대 개수 확인
    count = db.query(Watchlist).filter(Watchlist.user_id == current_user.id).count()
    if count >= MAX_WATCHLIST_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"관심 종목은 최대 {MAX_WATCHLIST_SIZE}개까지 등록할 수 있습니다.",
        )

    entry = Watchlist(
        user_id=current_user.id,
        ticker=ticker,
        last_notified_score=stock.compass_score,
        last_notified_grade=stock.compass_grade,
    )
    db.add(entry)
    db.commit()

    return {"message": f"{stock.name} ({ticker}) 관심 종목에 추가되었습니다.", "ticker": ticker}


@router.delete("/{ticker}")
async def remove_from_watchlist(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """관심 종목 삭제"""
    entry = db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id,
        Watchlist.ticker == ticker,
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="관심 종목에 등록되지 않은 종목입니다.")

    db.delete(entry)
    db.commit()

    return {"message": f"{ticker} 관심 종목에서 삭제되었습니다.", "ticker": ticker}


@router.get("/status/{ticker}")
async def get_watchlist_status(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """특정 종목의 관심 등록 여부 확인"""
    exists = db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id,
        Watchlist.ticker == ticker,
    ).first()

    return {"in_watchlist": exists is not None, "ticker": ticker}
