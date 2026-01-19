"""
Phase 3-C / U-2: 사용자 북마크 API
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.auth import get_current_user
from app.database import get_db
from app.models.bookmark import Bookmark
from app.models.custom_portfolio import CustomPortfolio
from app.models.user import User


router = APIRouter(prefix="/api/v1/bookmarks", tags=["Bookmarks"])


def _get_user_portfolio(
    db: Session,
    portfolio_id: int,
    user_id: str,
) -> CustomPortfolio | None:
    owner_user_id = None
    try:
        owner_user_id = int(user_id)
    except (TypeError, ValueError):
        owner_user_id = None

    conditions = [CustomPortfolio.owner_key == user_id]
    if owner_user_id is not None:
        conditions.append(CustomPortfolio.owner_user_id == owner_user_id)

    return (
        db.query(CustomPortfolio)
        .filter(
            CustomPortfolio.portfolio_id == portfolio_id,
            CustomPortfolio.is_active == True,
            or_(*conditions),
        )
        .first()
    )


def _portfolio_exists(db: Session, portfolio_id: int) -> bool:
    return (
        db.query(CustomPortfolio)
        .filter(
            CustomPortfolio.portfolio_id == portfolio_id,
            CustomPortfolio.is_active == True,
        )
        .first()
        is not None
    )


@router.get("")
def list_bookmarks(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """북마크 목록 조회 (Read-only)"""
    response.headers["Cache-Control"] = "no-store"
    bookmarks = (
        db.query(Bookmark)
        .filter(Bookmark.user_id == current_user.id)
        .order_by(Bookmark.created_at.desc())
        .all()
    )

    return {
        "success": True,
        "data": [
            {
                "portfolio_id": bookmark.portfolio_id,
                "created_at": bookmark.created_at,
            }
            for bookmark in bookmarks
        ],
    }


@router.post("")
def add_bookmark(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """북마크 추가"""
    portfolio_id = payload.get("portfolio_id")
    if not portfolio_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="portfolio_id가 필요합니다.",
        )

    portfolio = _get_user_portfolio(db, int(portfolio_id), current_user.id)
    if not portfolio:
        if _portfolio_exists(db, int(portfolio_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="접근 권한이 없습니다.",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="포트폴리오를 찾을 수 없습니다.",
        )

    existing = (
        db.query(Bookmark)
        .filter(
            Bookmark.user_id == current_user.id,
            Bookmark.portfolio_id == portfolio.portfolio_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 북마크에 추가된 포트폴리오입니다.",
        )

    bookmark = Bookmark(user_id=current_user.id, portfolio_id=portfolio.portfolio_id)
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)

    return {
        "success": True,
        "data": {
            "portfolio_id": bookmark.portfolio_id,
            "created_at": bookmark.created_at,
        },
    }


@router.delete("/{portfolio_id}")
def remove_bookmark(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """북마크 삭제"""
    bookmark = (
        db.query(Bookmark)
        .filter(
            Bookmark.user_id == current_user.id,
            Bookmark.portfolio_id == portfolio_id,
        )
        .first()
    )
    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="북마크를 찾을 수 없습니다.",
        )

    db.delete(bookmark)
    db.commit()

    return {
        "success": True,
        "data": {
            "portfolio_id": portfolio_id,
        },
    }
