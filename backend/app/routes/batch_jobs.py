"""
배치 작업 API - 한국 주식 데이터 일괄 수집
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.database import get_db
from app.auth import require_admin
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/batch", tags=["Admin Batch Jobs"])


# 배치 작업 상태를 메모리에 저장 (실제로는 Redis나 DB 사용 권장)
batch_job_status = {}


class BatchJobStatus(BaseModel):
    """배치 작업 상태"""
    job_id: str
    job_type: str
    status: str  # pending, running, completed, failed
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: dict = {}
    result: dict = {}
    error: Optional[str] = None


def run_full_krx_batch_job(
    job_id: str,
    days: int = 365,
    limit: int = 200
):
    """
    전체 한국 주식 데이터 수집 배치 작업

    1. 기본 정보 수집 (pykrx - 주식)
    2. 시계열 데이터 수집 (pykrx - OHLCV)
    3. 재무지표 수집 (pykrx - PER, PBR, etc)
    """
    import traceback
    print(f"[Batch Job] FUNCTION CALLED! job_id={job_id}, days={days}, limit={limit}")

    # Wrap everything to catch any errors
    try:
        from pykrx import stock as pykrx_stock
        from app.models.securities import Stock
        from app.models.real_data import StockPriceDaily
        from app.crud import get_or_create_stock
        from sqlalchemy import and_

        # Create a new database session for this background task
        from app.database import SessionLocal
        print(f"[Batch Job {job_id}] Creating database session...")
        db = SessionLocal()
        print(f"[Batch Job {job_id}] Database session created")
    except Exception as e:
        print(f"[Batch Job {job_id}] ERROR during initialization: {str(e)}")
        print(f"[Batch Job {job_id}] Traceback: {traceback.format_exc()}")
        batch_job_status[job_id]["status"] = "failed"
        batch_job_status[job_id]["error"] = f"Initialization error: {str(e)}"
        batch_job_status[job_id]["completed_at"] = datetime.now().isoformat()
        return

    try:
        # 작업 시작
        print(f"[Batch Job {job_id}] Setting status to running...")
        batch_job_status[job_id]["status"] = "running"
        batch_job_status[job_id]["started_at"] = datetime.now().isoformat()
        batch_job_status[job_id]["progress"] = {
            "phase": "기본 정보 수집 중",
            "current": 0,
            "total": 0,
            "details": ""
        }

        # Step 1: 기본 정보 수집
        print(f"[Batch Job {job_id}] Step 1: 기본 정보 수집 시작")

        from datetime import date, timedelta

        # 최근 거래일 찾기 (최대 10일 전까지 시도)
        today = date.today()
        trading_date = None
        trading_date_str = None

        for days_back in range(10):
            check_date = today - timedelta(days=days_back)
            check_date_str = check_date.strftime("%Y%m%d")

            # 샘플 종목으로 데이터 존재 여부 확인 (삼성전자)
            try:
                test_df = pykrx_stock.get_market_ohlcv(check_date_str, check_date_str, "005930")
                if not test_df.empty:
                    trading_date = check_date
                    trading_date_str = check_date_str
                    logger.info(f"[Batch Job {job_id}] 최근 거래일: {trading_date} ({check_date_str})")
                    break
            except Exception as e:
                logger.debug(f"[Batch Job {job_id}] 거래일 탐색 중 (날짜: {check_date_str}): {e}")
                continue

        if not trading_date_str:
            # 거래일을 찾지 못한 경우 오늘 날짜 사용
            trading_date = today
            trading_date_str = today.strftime("%Y%m%d")
            print(f"[Batch Job {job_id}] 경고: 최근 거래일을 찾지 못함. 오늘 날짜 사용: {trading_date_str}")

        today_str = trading_date_str  # 기존 코드와의 호환성을 위해 today_str 유지

        # pykrx의 get_market_ticker_list()가 작동하지 않으므로
        # 데이터베이스에 이미 있는 종목 또는 주요 종목 리스트 사용
        existing_stocks = db.query(Stock).filter(Stock.market.in_(["KOSPI", "KOSDAQ"])).all()

        if existing_stocks:
            # 기존 종목 업데이트
            all_tickers = [stock.ticker for stock in existing_stocks][:limit]
            print(f"[Batch Job {job_id}] Using {len(all_tickers)} existing stocks from database")
        else:
            # 주요 한국 종목 리스트 (시가총액 기준 상위 종목)
            all_tickers = [
                "005930",  # 삼성전자
                "000660",  # SK하이닉스
                "035420",  # NAVER
                "051910",  # LG화학
                "006400",  # 삼성SDI
                "035720",  # 카카오
                "068270",  # 셀트리온
                "207940",  # 삼성바이오로직스
                "005380",  # 현대차
                "000270",  # 기아
                "105560",  # KB금융
                "055550",  # 신한지주
                "012330",  # 현대모비스
                "028260",  # 삼성물산
                "066570",  # LG전자
                "003550",  # LG
                "096770",  # SK이노베이션
                "017670",  # SK텔레콤
                "009150",  # 삼성전기
                "034020",  # 두산에너빌리티
            ][:limit]
            print(f"[Batch Job {job_id}] Using {len(all_tickers)} major Korean stocks")

        batch_job_status[job_id]["progress"]["total"] = len(all_tickers)

        basic_info_success = 0
        basic_info_failed = 0

        for idx, ticker in enumerate(all_tickers):
            try:
                batch_job_status[job_id]["progress"]["current"] = idx + 1
                batch_job_status[job_id]["progress"]["details"] = f"{ticker} 기본 정보"

                # 종목명 조회
                stock_name = pykrx_stock.get_market_ticker_name(ticker)

                # 현재가 조회
                today_df = pykrx_stock.get_market_ohlcv(today_str, today_str, ticker)
                current_price = None
                if not today_df.empty:
                    current_price = int(today_df.iloc[-1]['종가'])
                    print(f"[Batch Job {job_id}] {ticker} 현재가: {current_price:,}원")
                else:
                    print(f"[Batch Job {job_id}] {ticker} OHLCV 데이터 없음")

                # 시가총액 조회 (단위: 백만원)
                market_cap_df = pykrx_stock.get_market_cap(today_str, today_str, ticker)
                market_cap = None
                if not market_cap_df.empty:
                    market_cap = int(market_cap_df.iloc[-1]['시가총액'] / 1_000_000)  # 억원 단위
                    print(f"[Batch Job {job_id}] {ticker} 시가총액: {market_cap:,}억원")
                else:
                    print(f"[Batch Job {job_id}] {ticker} 시가총액 데이터 없음")

                # DB에 저장
                stock = get_or_create_stock(
                    db=db,
                    ticker=ticker,
                    name=stock_name,
                    current_price=current_price,
                    market_cap=market_cap,
                    market="KOSPI",  # 기본값 (실제로는 구분 필요)
                    sector="기타",  # pykrx는 섹터 정보 미제공
                    investment_type="conservative,moderate,aggressive",  # 기본값
                    risk_level="medium"
                )

                print(f"[Batch Job {job_id}] {ticker} DB 저장 완료 (가격: {current_price})")

                basic_info_success += 1

            except Exception as e:
                print(f"[Batch Job {job_id}] 기본 정보 수집 실패 ({ticker}): {str(e)}")
                basic_info_failed += 1
                continue

        db.commit()

        # Step 2: 시계열 데이터 수집
        print(f"[Batch Job {job_id}] Step 2: 시계열 데이터 수집 시작")
        batch_job_status[job_id]["progress"]["phase"] = "시계열 데이터 수집 중"

        timeseries_success = 0
        timeseries_failed = 0

        from_date = trading_date - timedelta(days=days)
        from_date_str = from_date.strftime("%Y%m%d")

        print(f"[Batch Job {job_id}] 시계열 데이터 기간: {from_date_str} ~ {today_str}")

        for idx, ticker in enumerate(all_tickers):
            try:
                batch_job_status[job_id]["progress"]["current"] = idx + 1
                batch_job_status[job_id]["progress"]["details"] = f"{ticker} 시계열 데이터"

                print(f"[Batch Job {job_id}] {ticker} 시계열 수집 시작 ({from_date_str} ~ {today_str})")

                # OHLCV 데이터 조회
                df = pykrx_stock.get_market_ohlcv(from_date_str, today_str, ticker)

                if df.empty:
                    print(f"[Batch Job {job_id}] {ticker} 시계열 데이터 없음")
                    timeseries_failed += 1
                    continue

                print(f"[Batch Job {job_id}] {ticker} 시계열 {len(df)}개 행 조회 완료")
                records_added = 0

                for date_idx, row in df.iterrows():
                    trade_date = date_idx.date() if hasattr(date_idx, 'date') else date_idx

                    # 이미 존재하는지 확인
                    existing = db.query(StockPriceDaily).filter(
                        and_(
                            StockPriceDaily.ticker == ticker,
                            StockPriceDaily.trade_date == trade_date,
                            StockPriceDaily.source_id == 'PYKRX',
                        )
                    ).first()

                    if not existing:
                        from decimal import Decimal
                        timeseries_record = StockPriceDaily(
                            ticker=ticker,
                            trade_date=trade_date,
                            open_price=Decimal(str(row['시가'])),
                            high_price=Decimal(str(row['고가'])),
                            low_price=Decimal(str(row['저가'])),
                            close_price=Decimal(str(row['종가'])),
                            volume=int(row['거래량']),
                            source_id='PYKRX',
                            as_of_date=trade_date,
                            quality_flag='NORMAL',
                        )
                        db.add(timeseries_record)
                        records_added += 1

                if records_added > 0:
                    db.commit()
                    print(f"[Batch Job {job_id}] {ticker} 시계열 {records_added}개 레코드 저장 완료")
                else:
                    print(f"[Batch Job {job_id}] {ticker} 시계열 신규 데이터 없음 (이미 존재)")

                # 데이터를 조회했으면 성공으로 간주 (신규 추가 여부와 무관)
                timeseries_success += 1

            except Exception as e:
                print(f"[Batch Job {job_id}] 시계열 수집 실패 ({ticker}): {str(e)}")
                import traceback
                print(traceback.format_exc())
                timeseries_failed += 1
                db.rollback()
                continue

        # Step 3: 재무지표 수집 (yfinance 사용)
        print(f"[Batch Job {job_id}] Step 3: 재무지표 수집 시작 (yfinance)")
        batch_job_status[job_id]["progress"]["phase"] = "재무지표 수집 중"

        financial_success = 0
        financial_failed = 0

        for idx, ticker in enumerate(all_tickers):
            try:
                batch_job_status[job_id]["progress"]["current"] = idx + 1
                batch_job_status[job_id]["progress"]["details"] = f"{ticker} 재무지표"

                # yfinance 티커 형식: 종목코드.KS (KOSPI)
                yf_ticker = f"{ticker}.KS"

                print(f"[Batch Job {job_id}] {ticker} yfinance 조회 시작...")
                import yfinance as yf
                stock_yf = yf.Ticker(yf_ticker)
                info = stock_yf.info

                # DB 업데이트
                stock = db.query(Stock).filter(Stock.ticker == ticker).first()

                if not stock:
                    print(f"[Batch Job {job_id}] {ticker} DB에 없음 - 스킵")
                    financial_failed += 1
                    continue

                # 재무지표 업데이트
                updates = {}

                # PER (Forward PE 우선, 없으면 Trailing PE)
                pe_ratio = info.get('forwardPE') or info.get('trailingPE')
                if pe_ratio and pe_ratio > 0:
                    stock.pe_ratio = round(float(pe_ratio), 2)
                    updates['PER'] = stock.pe_ratio

                # PBR
                pb_ratio = info.get('priceToBook')
                if pb_ratio and pb_ratio > 0:
                    stock.pb_ratio = round(float(pb_ratio), 2)
                    updates['PBR'] = stock.pb_ratio

                # EPS
                eps = info.get('trailingEps')
                if eps and eps != 0:
                    stock.eps = round(float(eps), 2)
                    updates['EPS'] = stock.eps

                # 배당수익률 (yfinance: KRX 종목은 이미 %단위로 반환)
                div_yield = info.get('dividendYield')
                if div_yield and div_yield > 0:
                    # KRX 종목: 이미 %(예: 4.11), 소수점 형태(예: 0.0411)면 변환
                    if div_yield < 1:
                        stock.dividend_yield = round(float(div_yield) * 100, 2)
                    else:
                        stock.dividend_yield = round(float(div_yield), 2)
                    updates['DIV'] = stock.dividend_yield

                # ROE
                roe = info.get('returnOnEquity')
                if roe:
                    stock.roe = round(float(roe) * 100, 2)  # 퍼센트로 변환
                    updates['ROE'] = stock.roe

                # 시가총액 (optional, 이미 있으면 업데이트)
                market_cap = info.get('marketCap')
                if market_cap:
                    stock.market_cap = int(market_cap / 100000000)  # 억원 단위
                    updates['시가총액'] = stock.market_cap

                if updates:
                    print(f"[Batch Job {job_id}] {ticker} 재무지표 저장: {updates}")
                    financial_success += 1
                else:
                    print(f"[Batch Job {job_id}] {ticker} 재무지표 없음")
                    financial_failed += 1

            except Exception as e:
                print(f"[Batch Job {job_id}] 재무지표 수집 실패 ({ticker}): {str(e)}")
                financial_failed += 1
                continue

        db.commit()

        # 작업 완료
        batch_job_status[job_id]["status"] = "completed"
        batch_job_status[job_id]["completed_at"] = datetime.now().isoformat()
        batch_job_status[job_id]["progress"]["phase"] = "완료"
        batch_job_status[job_id]["result"] = {
            "total_tickers": len(all_tickers),
            "basic_info": {
                "success": basic_info_success,
                "failed": basic_info_failed
            },
            "timeseries": {
                "success": timeseries_success,
                "failed": timeseries_failed
            },
            "financial": {
                "success": financial_success,
                "failed": financial_failed
            }
        }

        print(f"[Batch Job {job_id}] 전체 배치 작업 완료")

    except Exception as e:
        # 작업 실패
        batch_job_status[job_id]["status"] = "failed"
        batch_job_status[job_id]["completed_at"] = datetime.now().isoformat()
        batch_job_status[job_id]["error"] = str(e)
        batch_job_status[job_id]["result"] = {
            "error_detail": traceback.format_exc()
        }
        print(f"[Batch Job {job_id}] 배치 작업 실패: {str(e)}")
        print(traceback.format_exc())

    finally:
        # Close database session
        db.close()


@router.post("/krx-full-collection")
async def start_full_krx_collection(
    background_tasks: BackgroundTasks,
    days: int = Query(365, ge=1, le=3650, description="시계열 데이터 수집 기간 (일)"),
    limit: int = Query(200, ge=1, le=500, description="처리할 종목 수 (최대 500개)"),
    current_user: User = Depends(require_admin)
):
    """
    한국 주식 전체 데이터 수집 배치 작업 시작

    다음 작업을 순차적으로 수행합니다:
    1. 기본 정보 수집 (종목명, 현재가, 시가총액)
    2. 시계열 데이터 수집 (OHLCV)
    3. 재무지표 수집 (PER, PBR, EPS, 배당률 등)

    **주의**: 이 작업은 오래 걸릴 수 있습니다 (약 10-30분).
    백그라운드에서 실행되며 `/admin/batch/status/{job_id}`로 진행상황을 확인할 수 있습니다.
    """
    try:
        # Job ID 생성
        job_id = f"krx_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 초기 상태 설정
        batch_job_status[job_id] = {
            "job_id": job_id,
            "job_type": "krx_full_collection",
            "status": "pending",
            "started_at": None,
            "completed_at": None,
            "progress": {
                "phase": "대기 중",
                "current": 0,
                "total": 0,
                "details": ""
            },
            "result": {},
            "error": None
        }

        # 백그라운드 작업 시작
        background_tasks.add_task(
            run_full_krx_batch_job,
            job_id,
            days,
            limit
        )

        return {
            "success": True,
            "data": {
                "job_id": job_id,
                "message": "배치 작업이 시작되었습니다. 작업 ID로 진행상황을 확인하세요.",
                "estimated_time_minutes": int(limit / 10),
                "check_status_url": f"/admin/batch/status/{job_id}"
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"배치 작업 시작 실패: {str(e)}"
        )


@router.get("/status/{job_id}")
async def get_batch_job_status(
    job_id: str,
    current_user: User = Depends(require_admin)
):
    """
    배치 작업 상태 조회

    실행 중이거나 완료된 배치 작업의 현재 상태와 진행률을 확인합니다.
    """
    if job_id not in batch_job_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="배치 작업을 찾을 수 없습니다."
        )

    return {
        "success": True,
        "data": batch_job_status[job_id]
    }


@router.get("/jobs")
async def list_batch_jobs(
    current_user: User = Depends(require_admin)
):
    """
    모든 배치 작업 목록 조회

    실행 중이거나 완료된 모든 배치 작업의 목록을 반환합니다.
    """
    jobs = [
        {
            "job_id": job_id,
            "job_type": job_data["job_type"],
            "status": job_data["status"],
            "started_at": job_data["started_at"],
            "completed_at": job_data["completed_at"]
        }
        for job_id, job_data in batch_job_status.items()
    ]

    # 최신순 정렬
    jobs.sort(key=lambda x: x["started_at"] or "", reverse=True)

    return {
        "success": True,
        "data": {
            "total": len(jobs),
            "jobs": jobs
        }
    }


@router.delete("/jobs/{job_id}")
async def delete_batch_job(
    job_id: str,
    current_user: User = Depends(require_admin)
):
    """
    배치 작업 기록 삭제

    완료되거나 실패한 배치 작업의 기록을 삭제합니다.
    실행 중인 작업은 삭제할 수 없습니다.
    """
    if job_id not in batch_job_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="배치 작업을 찾을 수 없습니다."
        )

    job = batch_job_status[job_id]

    if job["status"] == "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="실행 중인 작업은 삭제할 수 없습니다."
        )

    del batch_job_status[job_id]

    return {
        "success": True,
        "message": "배치 작업 기록이 삭제되었습니다."
    }
