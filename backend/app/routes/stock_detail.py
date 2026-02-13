# backend/app/routes/stock_detail.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from app.database import get_db
from app.models.securities import Stock
from app.models.real_data import StockPriceDaily
from app.auth import get_current_user, require_admin
from app.models.user import User
from app.exceptions import StockNotFoundError

logger = logging.getLogger(__name__)

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
    - 시계열 데이터 (stock_price_daily 테이블, 최근 N일)
    - 재무 지표 (stocks 테이블)
    - Compass Score (사전 계산된 점수 + commentary)
    """

    # 1. 기본 정보 조회
    stock = db.query(Stock).filter(Stock.ticker == ticker).first()

    if not stock:
        raise StockNotFoundError(f"종목 코드 {ticker}를 찾을 수 없습니다.")

    # 2. 시계열 데이터 조회 (최근 N일)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    timeseries = db.query(StockPriceDaily).filter(
        StockPriceDaily.ticker == ticker,
        StockPriceDaily.trade_date >= start_date,
        StockPriceDaily.trade_date <= end_date
    ).order_by(StockPriceDaily.trade_date).all()

    # 3. 통계 계산
    stats = None
    if timeseries:
        closes = [float(ts.close_price) for ts in timeseries]
        volumes = [ts.volume for ts in timeseries]

        first_close = closes[0]
        last_close = closes[-1]
        period_return = ((last_close - first_close) / first_close) * 100 if first_close > 0 else 0

        stats = {
            "period_days": len(timeseries),
            "period_return": round(period_return, 2),
            "high": float(max([ts.high_price for ts in timeseries])),
            "low": float(min([ts.low_price for ts in timeseries])),
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
        "compass": {
            "score": stock.compass_score,
            "grade": stock.compass_grade,
            "summary": stock.compass_summary,
            "commentary": stock.compass_commentary,
            "financial_score": stock.compass_financial_score,
            "valuation_score": stock.compass_valuation_score,
            "technical_score": stock.compass_technical_score,
            "risk_score": stock.compass_risk_score,
            "updated_at": stock.compass_updated_at.isoformat() if stock.compass_updated_at else None,
        },
        "timeseries": {
            "period_days": days,
            "data_count": len(timeseries),
            "data": [
                {
                    "date": ts.trade_date.isoformat(),
                    "open": float(ts.open_price),
                    "high": float(ts.high_price),
                    "low": float(ts.low_price),
                    "close": float(ts.close_price),
                    "volume": ts.volume
                }
                for ts in timeseries
            ]
        },
        "statistics": stats
        }
    }


@router.post("/{ticker}/ai-commentary")
def generate_ai_commentary(
    ticker: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    AI 심층 해설 생성 (on-demand, Claude API)
    - Compass Score 전체 결과를 컨텍스트로 Claude에 전달
    - API 키 없으면 rule-based commentary fallback
    - DB 저장 없음
    """
    from app.services.scoring_engine import ScoringEngine
    from app.config import settings

    # 1. Compass Score 계산 (실시간)
    result = ScoringEngine.calculate_compass_score(db, ticker)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    # 2. Claude API 호출 시도
    if not settings.anthropic_api_key:
        return {
            "success": True,
            "source": "rule_based",
            "commentary": result.get("commentary", "AI 해설을 생성할 수 없습니다. (API 키 미설정)"),
        }

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        # 카테고리 점수 요약
        cat_summary = []
        for k, v in result.get("categories", {}).items():
            if v and v.get("score") is not None:
                cat_summary.append(f"- {k}: {v['score']}점 ({v.get('grade', 'N/A')})")

        prompt = f"""당신은 전문 금융 분석가입니다. 아래 종목의 Compass Score 분석 결과를 바탕으로,
투자 학습 목적의 상세 한국어 해설을 5~7문장으로 작성해주세요.

## 종목 정보
- 종목: {result.get('company_name', ticker)} ({ticker})
- Compass Score: {result['compass_score']}점 ({result['grade']}등급)
- 요약: {result.get('summary', '')}

## 카테고리별 점수
{chr(10).join(cat_summary)}

## Rule-based 해설 (참고)
{result.get('commentary', '')}

## 작성 지침
1. 구체적 수치(ROE, PER, ADX 등)를 언급하되 rule-based 해설과 다른 관점/심층 분석 추가
2. 해당 종목의 강점과 리스크를 균형 있게 서술
3. 마지막에 반드시 "교육 목적 참고 정보이며 투자 권유가 아닙니다" 포함
4. 친절하고 전문적인 톤
5. 마크다운 없이 순수 텍스트로 작성"""

        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=800,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        )

        ai_text = message.content[0].text.strip()

        return {
            "success": True,
            "source": "ai",
            "commentary": ai_text,
        }

    except Exception as e:
        logger.warning(f"AI commentary failed for {ticker}: {e}")
        return {
            "success": True,
            "source": "rule_based_fallback",
            "commentary": result.get("commentary", "AI 해설 생성에 실패했습니다."),
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
