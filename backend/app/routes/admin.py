# backend/app/routes/admin.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.services.data_loader import DataLoaderService
from app.services.alpha_vantage_loader import AlphaVantageDataLoader
from app.services.pykrx_loader import PyKrxDataLoader
from app.services.financial_analyzer import FinancialAnalyzer
from app.models import User
from app.auth import get_current_user
from app.progress_tracker import progress_tracker
from typing import List
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


# ========== Alpha Vantage 관련 엔드포인트 ==========

@router.post("/alpha-vantage/load-all-stocks")
async def load_all_alpha_vantage_stocks(
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
):
    """Alpha Vantage: 인기 미국 주식 전체 적재"""
    try:
        loader = AlphaVantageDataLoader()
        result = loader.load_all_popular_stocks(db)

        return {
            "status": "success",
            "message": "Alpha Vantage 주식 데이터 적재 완료",
            "result": result
        }
    except Exception as e:
        logger.error(f"Alpha Vantage stock loading failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alpha-vantage/load-stock/{symbol}")
async def load_alpha_vantage_stock(
    symbol: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
):
    """Alpha Vantage: 특정 주식 적재"""
    try:
        loader = AlphaVantageDataLoader()
        result = loader.load_stock_data(db, symbol.upper())

        if not result['success']:
            raise HTTPException(status_code=400, detail=result['message'])

        return {
            "status": "success",
            "message": result['message'],
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Alpha Vantage stock loading failed for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alpha-vantage/load-financials/{symbol}")
async def load_alpha_vantage_financials(
    symbol: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
):
    """Alpha Vantage: 특정 주식의 재무제표 적재"""
    try:
        loader = AlphaVantageDataLoader()
        result = loader.load_financials(db, symbol.upper())

        if not result['success']:
            raise HTTPException(status_code=400, detail=result['message'])

        return {
            "status": "success",
            "message": result['message'],
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Alpha Vantage financials loading failed for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alpha-vantage/load-all-etfs")
async def load_all_alpha_vantage_etfs(
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
):
    """Alpha Vantage: 인기 미국 ETF 전체 적재"""
    try:
        loader = AlphaVantageDataLoader()
        result = loader.load_all_popular_etfs(db)

        return {
            "status": "success",
            "message": "Alpha Vantage ETF 데이터 적재 완료",
            "result": result
        }
    except Exception as e:
        logger.error(f"Alpha Vantage ETF loading failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alpha-vantage/stocks")
async def get_alpha_vantage_stocks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
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
    current_user: User = Depends(is_admin)
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


@router.get("/alpha-vantage/data-status")
async def get_alpha_vantage_data_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
):
    """Alpha Vantage: DB 통계"""
    from sqlalchemy import func
    from app.models.alpha_vantage import AlphaVantageStock, AlphaVantageETF, AlphaVantageFinancials

    stock_count = db.query(func.count(AlphaVantageStock.id)).scalar()
    etf_count = db.query(func.count(AlphaVantageETF.id)).scalar()
    financials_count = db.query(func.count(AlphaVantageFinancials.id)).scalar()

    return {
        "stocks": stock_count,
        "etfs": etf_count,
        "financials": financials_count,
        "total": stock_count + etf_count
    }


# ========== pykrx (한국 주식) 관련 엔드포인트 ==========

@router.post("/pykrx/load-all-stocks")
async def load_all_pykrx_stocks(
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
):
    """pykrx: 인기 한국 주식 전체 적재"""
    try:
        loader = PyKrxDataLoader()
        result = loader.load_all_popular_stocks(db)

        return {
            "status": "success",
            "message": "한국 주식 데이터 적재 완료",
            "result": result
        }
    except Exception as e:
        logger.error(f"pykrx stock loading failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pykrx/load-stock/{ticker}")
async def load_pykrx_stock(
    ticker: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
):
    """pykrx: 특정 한국 주식 적재"""
    try:
        loader = PyKrxDataLoader()
        result = loader.load_stock_data(db, ticker)

        if not result['success']:
            raise HTTPException(status_code=400, detail=result['message'])

        return {
            "status": "success",
            "message": result['message'],
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"pykrx stock loading failed for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pykrx/load-all-etfs")
async def load_all_pykrx_etfs(
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
):
    """pykrx: 인기 한국 ETF 전체 적재"""
    try:
        loader = PyKrxDataLoader()
        result = loader.load_all_popular_etfs(db)

        return {
            "status": "success",
            "message": "한국 ETF 데이터 적재 완료",
            "result": result
        }
    except Exception as e:
        logger.error(f"pykrx ETF loading failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pykrx/load-etf/{ticker}")
async def load_pykrx_etf(
    ticker: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
):
    """pykrx: 특정 한국 ETF 적재"""
    try:
        loader = PyKrxDataLoader()
        result = loader.load_etf_data(db, ticker)

        if not result['success']:
            raise HTTPException(status_code=400, detail=result['message'])

        return {
            "status": "success",
            "message": result['message'],
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"pykrx ETF loading failed for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 재무 분석 엔드포인트 ==========

@router.get("/financial-analysis/{symbol}")
async def analyze_stock_financials(
    symbol: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
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
    current_user: User = Depends(is_admin)
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
    current_user: User = Depends(is_admin)
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
    current_user: User = Depends(is_admin)
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
    - 안정적인 배당 지급 기업에 적합
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
    - 투자 추천 포함
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