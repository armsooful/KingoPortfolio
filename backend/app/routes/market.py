"""
시장 데이터 API 라우터
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Dict, Any
import yfinance as yf

from app.database import get_db
from app.models.user import User
from app.routes.auth import get_current_user

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/overview")
async def get_market_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    시장 현황 개요 조회
    - 주요 지수 (KOSPI, KOSDAQ, S&P 500, NASDAQ)
    - 상승/하락 종목
    - 시장 뉴스 (Mock)
    """
    try:
        # 주요 지수 데이터
        indices = []

        # KOSPI
        try:
            kospi = yf.Ticker("^KS11")
            kospi_info = kospi.history(period="1d")
            if not kospi_info.empty:
                current_price = kospi_info['Close'].iloc[-1]
                prev_close = kospi_info['Open'].iloc[0]
                change = current_price - prev_close
                change_percent = (change / prev_close) * 100

                indices.append({
                    "name": "KOSPI",
                    "value": round(current_price, 2),
                    "change": round(change, 2),
                    "changePercent": round(change_percent, 2),
                    "updatedAt": datetime.now().isoformat()
                })
        except Exception as e:
            print(f"KOSPI 데이터 조회 실패: {e}")
            indices.append({
                "name": "KOSPI",
                "value": 2645.85,
                "change": 15.32,
                "changePercent": 0.58,
                "updatedAt": datetime.now().isoformat()
            })

        # KOSDAQ
        try:
            kosdaq = yf.Ticker("^KQ11")
            kosdaq_info = kosdaq.history(period="1d")
            if not kosdaq_info.empty:
                current_price = kosdaq_info['Close'].iloc[-1]
                prev_close = kosdaq_info['Open'].iloc[0]
                change = current_price - prev_close
                change_percent = (change / prev_close) * 100

                indices.append({
                    "name": "KOSDAQ",
                    "value": round(current_price, 2),
                    "change": round(change, 2),
                    "changePercent": round(change_percent, 2),
                    "updatedAt": datetime.now().isoformat()
                })
        except Exception as e:
            print(f"KOSDAQ 데이터 조회 실패: {e}")
            indices.append({
                "name": "KOSDAQ",
                "value": 845.23,
                "change": -3.45,
                "changePercent": -0.41,
                "updatedAt": datetime.now().isoformat()
            })

        # S&P 500
        try:
            sp500 = yf.Ticker("^GSPC")
            sp500_info = sp500.history(period="1d")
            if not sp500_info.empty:
                current_price = sp500_info['Close'].iloc[-1]
                prev_close = sp500_info['Open'].iloc[0]
                change = current_price - prev_close
                change_percent = (change / prev_close) * 100

                indices.append({
                    "name": "S&P 500",
                    "value": round(current_price, 2),
                    "change": round(change, 2),
                    "changePercent": round(change_percent, 2),
                    "updatedAt": datetime.now().isoformat()
                })
        except Exception as e:
            print(f"S&P 500 데이터 조회 실패: {e}")
            indices.append({
                "name": "S&P 500",
                "value": 4783.45,
                "change": 12.87,
                "changePercent": 0.27,
                "updatedAt": datetime.now().isoformat()
            })

        # NASDAQ
        try:
            nasdaq = yf.Ticker("^IXIC")
            nasdaq_info = nasdaq.history(period="1d")
            if not nasdaq_info.empty:
                current_price = nasdaq_info['Close'].iloc[-1]
                prev_close = nasdaq_info['Open'].iloc[0]
                change = current_price - prev_close
                change_percent = (change / prev_close) * 100

                indices.append({
                    "name": "NASDAQ",
                    "value": round(current_price, 2),
                    "change": round(change, 2),
                    "changePercent": round(change_percent, 2),
                    "updatedAt": datetime.now().isoformat()
                })
        except Exception as e:
            print(f"NASDAQ 데이터 조회 실패: {e}")
            indices.append({
                "name": "NASDAQ",
                "value": 15043.97,
                "change": 45.23,
                "changePercent": 0.30,
                "updatedAt": datetime.now().isoformat()
            })

        # Mock 데이터 - 상승/하락 종목 (실제로는 별도 API 또는 DB에서 조회)
        top_gainers = [
            {"symbol": "005930", "name": "삼성전자", "price": 78500, "change": 3.5},
            {"symbol": "000660", "name": "SK하이닉스", "price": 145000, "change": 4.2},
            {"symbol": "035420", "name": "NAVER", "price": 245000, "change": 2.8}
        ]

        top_losers = [
            {"symbol": "051910", "name": "LG화학", "price": 425000, "change": -2.3},
            {"symbol": "006400", "name": "삼성SDI", "price": 485000, "change": -1.8},
            {"symbol": "028260", "name": "삼성물산", "price": 128000, "change": -1.5}
        ]

        # Mock 뉴스 데이터
        news = [
            {
                "title": "미 연준 금리 동결 전망... 국내 증시 영향은?",
                "source": "한국경제",
                "publishedAt": "2시간 전",
                "url": "#"
            },
            {
                "title": "삼성전자, AI 반도체 신제품 공개",
                "source": "전자신문",
                "publishedAt": "4시간 전",
                "url": "#"
            },
            {
                "title": "KOSPI 2650 돌파... 외국인 매수세 지속",
                "source": "연합뉴스",
                "publishedAt": "5시간 전",
                "url": "#"
            }
        ]

        return {
            "indices": indices,
            "topGainers": top_gainers,
            "topLosers": top_losers,
            "news": news
        }

    except Exception as e:
        print(f"Market overview error: {e}")
        raise HTTPException(status_code=500, detail=f"시장 데이터 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/indices/{symbol}")
async def get_index_detail(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    특정 지수의 상세 정보 조회
    """
    symbol_map = {
        "kospi": "^KS11",
        "kosdaq": "^KQ11",
        "sp500": "^GSPC",
        "nasdaq": "^IXIC"
    }

    ticker_symbol = symbol_map.get(symbol.lower())
    if not ticker_symbol:
        raise HTTPException(status_code=404, detail="지수를 찾을 수 없습니다")

    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="1mo")

        if hist.empty:
            raise HTTPException(status_code=404, detail="데이터를 찾을 수 없습니다")

        current_price = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else hist['Open'].iloc[0]
        change = current_price - prev_close
        change_percent = (change / prev_close) * 100

        return {
            "symbol": symbol.upper(),
            "name": symbol.upper(),
            "currentPrice": round(current_price, 2),
            "change": round(change, 2),
            "changePercent": round(change_percent, 2),
            "high": round(hist['High'].iloc[-1], 2),
            "low": round(hist['Low'].iloc[-1], 2),
            "volume": int(hist['Volume'].iloc[-1]),
            "updatedAt": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Index detail error: {e}")
        raise HTTPException(status_code=500, detail=f"지수 정보 조회 중 오류가 발생했습니다: {str(e)}")
