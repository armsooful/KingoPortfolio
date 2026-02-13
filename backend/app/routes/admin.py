# backend/app/routes/admin.py

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, timezone
from pydantic import BaseModel, Field
from app.database import get_db, SessionLocal
from app.services.data_loader import DataLoaderService
from app.services.alpha_vantage_loader import AlphaVantageDataLoader
from app.services.pykrx_loader import PyKrxDataLoader
from app.services.batch_manager import BatchManager, BatchType
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


class FscDividendLoadRequest(BaseModel):
    tickers: List[str] = Field(..., min_items=1)
    bas_dt: Optional[str] = Field(None, regex="^[0-9]{8}$")
    as_of_date: Optional[date] = None


class FdrStockListingLoadRequest(BaseModel):
    market: str = Field("KRX")
    as_of_date: Optional[date] = None


class BondInfoLoadRequest(BaseModel):
    bas_dt: Optional[str] = Field(None, regex="^[0-9]{8}$")
    crno: Optional[str] = Field(None, regex="^[0-9]{13}$")
    bond_isur_nm: Optional[str] = None
    limit: Optional[int] = Field(None, ge=1, le=10000)
    as_of_date: Optional[date] = None


class CorporateActionLoadRequest(BaseModel):
    year: Optional[int] = None
    quarter: Optional[str] = Field(None, regex="^(Q[1-4]|ALL)$")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    as_of_date: Optional[date] = None
    corp_cls: Optional[str] = Field(None, regex="^[YKNE]$")


class DailyPricesLoadRequest(BaseModel):
    start_date: str = Field(..., regex="^[0-9]{8}$")
    end_date: str = Field(..., regex="^[0-9]{8}$")
    tickers: Optional[List[str]] = None
    parallel: bool = Field(True, description="병렬 처리 여부")
    num_workers: int = Field(8, ge=1, le=16, description="동시 작업 스레드 수")


class IncrementalLoadRequest(BaseModel):
    default_days: int = Field(1825, ge=30, le=3650, description="신규 종목 기본 수집 일수 (기본 5년)")
    num_workers: int = Field(4, ge=1, le=8, description="동시 작업 스레드 수 (8GB RAM 권장: 4)")
    market: Optional[str] = Field(None, description="시장 필터 (KOSPI, KOSDAQ, None=전체)")


@router.post("/load-stocks")
async def load_stocks(
    background_tasks: BackgroundTasks,
    as_of_date: Optional[date] = Query(None),
    limit: Optional[int] = Query(None, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """주식 데이터 적재 (fdr_stock_listing → stocks, 백그라운드)

    Prerequisites: POST /admin/fdr/load-stock-listing 실행 완료
    """
    task_id = f"stocks_{uuid.uuid4().hex[:8]}"
    operator_id = str(current_user.id)

    def run_stock_loading():
        from app.database import SessionLocal
        from app.progress_tracker import progress_tracker
        from sqlalchemy import func as sa_func
        from app.models.real_data import FdrStockListing

        db = SessionLocal()
        try:
            effective_as_of_date = as_of_date
            if effective_as_of_date is None:
                latest = (
                    db.query(sa_func.max(FdrStockListing.as_of_date))
                    .filter(FdrStockListing.source_id == "FDR")
                    .scalar()
                )
                effective_as_of_date = latest

            total_items = 0
            if effective_as_of_date:
                total_items = (
                    db.query(sa_func.count(FdrStockListing.ticker))
                    .filter(
                        FdrStockListing.as_of_date == effective_as_of_date,
                        FdrStockListing.source_id == "FDR",
                    )
                    .scalar()
                    or 0
                )

            progress_tracker.start_task(
                task_id,
                total_items,
                "주식 데이터 적재 (FDR + pykrx)",
            )

            # Phase 1: 데이터 수집 중 (진행 상황 메시지 업데이트)
            progress_tracker.set_phase(task_id, "Phase 1")
            progress_tracker.update_progress(
                task_id,
                current=0,
                current_item="⏳ Phase 1: FSC API를 통해 주식 정보를 병렬로 수집 중... (약 2-3분 소요)",
                success=None,
            )

            loader = RealDataLoader(db)

            def on_progress(current, ticker, success=None, error=None):
                # Phase 2 시작 감지: "[Phase 2]" prefix가 있으면 Phase 2로 전환 및 count 리셋
                if ticker and isinstance(ticker, str) and "[Phase 2]" in ticker:
                    current_state = progress_tracker.get_progress(task_id)
                    if current_state and current_state.get("phase") != "Phase 2":
                        # Phase 2로 전환 및 success/failed count 초기화
                        progress_tracker.set_phase(task_id, "Phase 2", reset_counts=True)

                progress_tracker.update_progress(
                    task_id,
                    current=current,
                    current_item=ticker,
                    success=success,
                    error=error,
                )

            result = loader.load_stocks_from_fdr(
                as_of_date=effective_as_of_date,
                limit=limit,
                operator_id=operator_id,
                operator_reason="stocks 적재 (fdr → pykrx)",
                progress_callback=on_progress,
            )
            # 완료 메시지: progress.total을 실제 처리 건수로 동기화
            # (초기 count와 실제 처리 개수의 차이를 보정)
            progress = progress_tracker.get_progress(task_id)
            if progress and progress.get("total") != result.total_records:
                # total 재조정 (상단 진행률의 분모를 맞춤)
                progress["total"] = result.total_records

            progress_tracker.update_progress(
                task_id,
                current=result.total_records,
                current_item=f"완료: {result.success_records}건 성공, {result.failed_records}건 실패",
                success=True,
            )
            # 작업 완료 마킹
            logger.info(f"[CRITICAL] About to call complete_task for {task_id}")
            progress_tracker.complete_task(task_id, "completed")
            # 완료 후 상태 확인
            final_progress = progress_tracker.get_progress(task_id)
            logger.info(f"[CRITICAL] Task {task_id} completed. Final status: {final_progress.get('status') if final_progress else 'TASK NOT FOUND'}")
            logger.info(f"Stock loading completed: batch_id={result.batch_id} total={result.total_records}")
        except Exception as e:
            logger.error(f"[CRITICAL] Stock loading failed with exception: {str(e)}", exc_info=True)
            progress_tracker.update_progress(
                task_id,
                current=0,
                current_item=f"실패: {str(e)}",
                success=False,
                error=str(e),
            )
            logger.error(f"[CRITICAL] Calling complete_task with 'failed' status for {task_id}")
            progress_tracker.complete_task(task_id, "failed")
            final_progress = progress_tracker.get_progress(task_id)
            logger.error(f"[CRITICAL] Task {task_id} marked as failed. Final status: {final_progress.get('status') if final_progress else 'TASK NOT FOUND'}")
        finally:
            db.close()

    background_tasks.add_task(run_stock_loading)

    return {
        "status": "success",
        "message": "주식 데이터 수집 시작",
        "task_id": task_id,
    }

@router.post("/load-etfs")
async def load_etfs(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """ETF 데이터만 적재 (백그라운드)"""
    try:
        task_id = f"etfs_{uuid.uuid4().hex[:8]}"

        def run_etf_loading():
            logger.info(f"Background task started for ETFs, task_id: {task_id}")
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                result = DataLoaderService.load_etfs(db, task_id=task_id)
                logger.info(f"Background task completed for ETFs: {result}")
            except Exception as e:
                logger.error(f"Background task failed for ETFs: {str(e)}", exc_info=True)
            finally:
                db.close()

        background_tasks.add_task(run_etf_loading)

        return {
            "status": "success",
            "message": "ETF 데이터 수집 시작",
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


@router.post("/fsc/load-dividends")
async def load_dividend_history_fsc(
    payload: FscDividendLoadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """금융위원회_주식배당정보 배당 이력 적재"""
    try:
        loader = RealDataLoader(db)
        result = loader.load_dividend_history_fsc(
            tickers=payload.tickers,
            bas_dt=payload.bas_dt,
            as_of_date=payload.as_of_date or date.today(),
            operator_id=str(current_user.id),
            operator_reason=f"FSC 배당 이력 적재 ({payload.bas_dt or 'company'})",
        )
        return {
            "status": "success",
            "message": "FSC 배당 이력 적재 완료",
            "result": result.__dict__,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fsc/load-bonds")
async def load_bond_basic_info(
    payload: BondInfoLoadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """금융위원회_채권기본정보 적재"""
    if not (payload.bas_dt or payload.crno or payload.bond_isur_nm):
        raise HTTPException(
            status_code=422,
            detail="bas_dt, crno, bond_isur_nm 중 하나라도 필수입니다."
        )
    try:
        loader = RealDataLoader(db)
        result = loader.load_bond_basic_info(
            crno=payload.crno,
            bond_isur_nm=payload.bond_isur_nm,
            bas_dt=payload.bas_dt,
            limit=payload.limit,
            as_of_date=payload.as_of_date or date.today(),
            operator_id=str(current_user.id),
            operator_reason=f"FSC 채권기본정보 적재 (bas_dt={payload.bas_dt}, crno={payload.crno})",
        )
        return {
            "status": "success",
            "message": "채권기본정보 적재 완료",
            "result": result.__dict__,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/load-bonds")
async def load_bonds_full_query(
    background_tasks: BackgroundTasks,
    quality_filter: str = Query("all", regex="^(all|investment_grade|high_quality)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """채권 기본정보 전체 조회 (금융위원회 OpenAPI) - 기준일자는 오늘 날짜

    quality_filter:
      - all: 전체 채권
      - investment_grade: 투자적격등급 (AAA~BBB)
      - high_quality: 최우량 (AAA~A)
    """
    operator_id = str(current_user.id)
    task_id = f"bonds_{uuid.uuid4().hex[:8]}"

    # 필터 레이블 (UI 메시지용)
    filter_labels = {
        "all": "전체",
        "investment_grade": "투자적격등급 (AAA~BBB)",
        "high_quality": "최우량 (AAA~A)",
    }
    filter_label = filter_labels.get(quality_filter, "전체")

    # 채권 적재: Progress를 직접 초기화 (start_task로 total 고정 방지)
    progress_tracker._progress[task_id] = {
        "status": "running",
        "total": 0,  # 초기값 0 (나중에 업데이트)
        "current": 0,
        "current_item": f"채권 데이터 조회 중... (필터: {filter_label})",
        "success_count": 0,
        "failed_count": 0,
        "phase": "Phase 2",
        "description": f"채권 데이터 조회 ({filter_label})",
        "error_message": None,
        "items_history": [],
        "operator_id": operator_id,
        "created_at": datetime.now(timezone.utc),
    }

    # 초기 Phase 2 진행 상황 로그
    progress_tracker._progress[task_id]["items_history"].append({
        "index": 0,
        "item": "채권 데이터 조회 시작",
        "success": True,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    def load_bonds_async():
        try:
            db_session = SessionLocal()
            loader = RealDataLoader(db_session)

            # 최근 영업일 기준일자 설정 (FSC API는 미래 날짜 데이터 없음)
            # 현재 날짜에서 최대 7일 이전까지 시도
            from datetime import timedelta
            bas_dt = None
            as_of_date = date.today()

            for days_back in range(7):
                check_date = as_of_date - timedelta(days=days_back)
                check_date_str = str(check_date).replace('-', '')

                # 실제 데이터 조회 전에 해당 날짜가 유효한지 먼저 확인할 수 있지만,
                # 일단 어제 날짜 사용 (대부분의 경우 어제 데이터가 있음)
                if days_back == 0:
                    continue  # 오늘은 건너뛰기 (미래 날짜)
                bas_dt = check_date_str
                as_of_date = check_date
                break

            logger.info(f"[BOND] FSC API 호출 시작: bas_dt={bas_dt}, as_of_date={as_of_date}")

            def bond_progress_callback(current: int, item: str, success: bool = True):
                """채권 적재 진행률 콜백"""
                logger.info(f"[BOND_CALLBACK] current={current}, item={item}, success={success}")
                with progress_tracker._lock:
                    if task_id in progress_tracker._progress:
                        # 특수 케이스: [TOTAL] 메시지로 전체 개수 전달
                        if current == -1 and item.startswith("[TOTAL]"):
                            try:
                                total_count = int(item.replace("[TOTAL]", ""))
                                logger.info(f"[BOND_CALLBACK] Setting total_count={total_count}")
                                progress_tracker._progress[task_id]["total"] = total_count
                                progress_tracker._progress[task_id]["current_item"] = f"채권 {total_count}건 저장 중..."
                                progress_tracker._progress[task_id]["items_history"].append({
                                    "index": len(progress_tracker._progress[task_id]["items_history"]),
                                    "item": f"전체 {total_count}건 조회됨",
                                    "success": True,
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                })
                                logger.info(f"[BOND_CALLBACK] Progress updated: total={progress_tracker._progress[task_id]['total']}")
                            except (ValueError, IndexError) as e:
                                logger.error(f"[BOND_CALLBACK] Error parsing total: {e}")
                        else:
                            progress_tracker._progress[task_id]["current"] = current
                            progress_tracker._progress[task_id]["current_item"] = item
                            if success:
                                progress_tracker._progress[task_id]["success_count"] = current
                            progress_tracker._progress[task_id]["items_history"].append({
                                "index": len(progress_tracker._progress[task_id]["items_history"]),
                                "item": item,
                                "success": success,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            })
                            if current % 100 == 0:  # Log every 100 records
                                logger.info(f"[BOND_CALLBACK] Progress: {current}/{progress_tracker._progress[task_id].get('total', '?')}")

            logger.info(f"[BOND] load_bond_basic_info 호출 전... (quality_filter={quality_filter})")
            try:
                result = loader.load_bond_basic_info(
                    crno=None,
                    bond_isur_nm=None,
                    bas_dt=bas_dt,
                    limit=None,
                    as_of_date=as_of_date,
                    operator_id=operator_id,
                    operator_reason=f"FSC 채권기본정보 전체 조회 (필터: {filter_label})",
                    progress_callback=bond_progress_callback,
                    quality_filter=quality_filter,
                )
                logger.info(f"[BOND] load_bond_basic_info 완료: result type={type(result)}, success={result.success}")
            except Exception as e:
                logger.error(f"[BOND] load_bond_basic_info 호출 중 예외 발생: {type(e).__name__}: {str(e)}", exc_info=True)
                raise

            # 실제 적재된 건수로 진행 상황 업데이트
            if result.success:
                total_records = result.total_records
                success_records = result.success_records
                failed_records = result.failed_records

                logger.info(f"[BOND] FSC API 응답: 총 {total_records}건, 성공 {success_records}건, 실패 {failed_records}건")
                logger.info(f"[BOND] 채권 적재 완료: 총 {total_records}건, 성공 {success_records}건, 실패 {failed_records}건")

                # 진행 상황 업데이트 - total을 실제 데이터로 설정
                with progress_tracker._lock:
                    if task_id in progress_tracker._progress:
                        progress_tracker._progress[task_id]["total"] = total_records
                        progress_tracker._progress[task_id]["current"] = total_records
                        progress_tracker._progress[task_id]["success_count"] = success_records
                        progress_tracker._progress[task_id]["failed_count"] = failed_records
                        progress_tracker._progress[task_id]["current_item"] = f"채권 데이터 적재 완료: {total_records}건"
                        progress_tracker._progress[task_id]["items_history"].append({
                            "index": 1,
                            "item": f"채권 데이터 적재 완료: {total_records}건",
                            "success": True,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })

                progress_tracker.complete_task(task_id, status="completed")
            else:
                raise Exception(result.error_message or "채권 데이터 조회 실패")

        except Exception as e:
            logger.error(f"[BOND] 채권 데이터 적재 실패: {str(e)}")
            with progress_tracker._lock:
                if task_id in progress_tracker._progress:
                    progress_tracker._progress[task_id]["current_item"] = f"오류: {str(e)}"
                    progress_tracker._progress[task_id]["error_message"] = str(e)
                    progress_tracker._progress[task_id]["items_history"].append({
                        "index": 1,
                        "item": f"오류 발생: {str(e)}",
                        "success": False,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
            progress_tracker.complete_task(task_id, status="failed")
        finally:
            db_session.close()

    background_tasks.add_task(load_bonds_async)

    return {
        "status": "success",
        "task_id": task_id,
        "message": "채권 데이터 조회 시작"
    }


@router.post("/load-deposits")
async def load_deposits(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """FSS 정기예금 상품 적재 (금융감독원 금융상품 한 눈에 API)

    은행 정기예금 상품 ~37건을 조회하여 deposit_products + deposit_rate_options 테이블에 저장합니다.
    """
    operator_id = str(current_user.id)
    task_id = f"deposits_{uuid.uuid4().hex[:8]}"

    # Progress 직접 초기화 (단일 단계, Phase 배지 없음)
    progress_tracker._progress[task_id] = {
        "status": "running",
        "total": 0,
        "current": 0,
        "current_item": "FSS 정기예금 상품 조회 중...",
        "success_count": 0,
        "failed_count": 0,
        "phase": "",
        "description": "FSS 정기예금 상품 적재",
        "error_message": None,
        "items_history": [],
        "operator_id": operator_id,
        "created_at": datetime.now(timezone.utc),
    }

    progress_tracker._progress[task_id]["items_history"].append({
        "index": 0,
        "item": "FSS 정기예금 상품 조회 시작",
        "success": True,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    def load_deposits_async():
        try:
            db_session = SessionLocal()
            loader = RealDataLoader(db_session)

            def deposit_progress_callback(current: int, item: str, success: bool = True):
                with progress_tracker._lock:
                    if task_id in progress_tracker._progress:
                        if current == -1 and item.startswith("[TOTAL]"):
                            try:
                                total_count = int(item.replace("[TOTAL]", ""))
                                progress_tracker._progress[task_id]["total"] = total_count
                                progress_tracker._progress[task_id]["current_item"] = f"예금 상품 {total_count}건 저장 중..."
                                progress_tracker._progress[task_id]["items_history"].append({
                                    "index": len(progress_tracker._progress[task_id]["items_history"]),
                                    "item": f"전체 {total_count}건 조회됨",
                                    "success": True,
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                })
                            except (ValueError, IndexError) as e:
                                logger.error(f"[DEPOSIT] Error parsing total: {e}")
                        else:
                            progress_tracker._progress[task_id]["current"] = current
                            progress_tracker._progress[task_id]["current_item"] = item
                            if success:
                                progress_tracker._progress[task_id]["success_count"] = current
                            else:
                                progress_tracker._progress[task_id]["failed_count"] = (
                                    progress_tracker._progress[task_id].get("failed_count", 0) + 1
                                )
                            progress_tracker._progress[task_id]["items_history"].append({
                                "index": len(progress_tracker._progress[task_id]["items_history"]),
                                "item": item,
                                "success": success,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            })

            result = loader.load_deposit_products(
                operator_id=operator_id,
                operator_reason="FSS 정기예금 상품 적재",
                progress_callback=deposit_progress_callback,
            )

            if result.success:
                with progress_tracker._lock:
                    if task_id in progress_tracker._progress:
                        progress_tracker._progress[task_id]["total"] = result.total_records
                        progress_tracker._progress[task_id]["current"] = result.total_records
                        progress_tracker._progress[task_id]["success_count"] = result.success_records
                        progress_tracker._progress[task_id]["failed_count"] = result.failed_records
                        progress_tracker._progress[task_id]["current_item"] = f"예금 상품 적재 완료: {result.success_records}건"
                        progress_tracker._progress[task_id]["items_history"].append({
                            "index": len(progress_tracker._progress[task_id]["items_history"]),
                            "item": f"예금 상품 적재 완료: {result.success_records}건 성공, {result.failed_records}건 실패",
                            "success": True,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })

                progress_tracker.complete_task(task_id, status="completed")
                logger.info(f"[DEPOSIT] 정기예금 적재 완료: {result.success_records}건 성공")
            else:
                raise Exception(result.error_message or "정기예금 적재 실패")

        except Exception as e:
            logger.error(f"[DEPOSIT] 정기예금 적재 실패: {str(e)}")
            with progress_tracker._lock:
                if task_id in progress_tracker._progress:
                    progress_tracker._progress[task_id]["current_item"] = f"오류: {str(e)}"
                    progress_tracker._progress[task_id]["error_message"] = str(e)
                    progress_tracker._progress[task_id]["items_history"].append({
                        "index": len(progress_tracker._progress[task_id]["items_history"]),
                        "item": f"오류 발생: {str(e)}",
                        "success": False,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
            progress_tracker.complete_task(task_id, status="failed")
        finally:
            db_session.close()

    background_tasks.add_task(load_deposits_async)

    return {
        "status": "success",
        "task_id": task_id,
        "message": "FSS 정기예금 상품 조회 시작"
    }


@router.post("/load-savings")
async def load_savings(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """FSS 적금 상품 적재 (금융감독원 금융상품 한 눈에 API)

    은행/저축은행 적금 상품을 조회하여 savings_products + savings_rate_options 테이블에 저장합니다.
    권역별 + 다중 페이지 순차 호출.
    """
    operator_id = str(current_user.id)
    task_id = f"savings_{uuid.uuid4().hex[:8]}"

    # Progress 직접 초기화 (단일 단계, Phase 배지 없음)
    progress_tracker._progress[task_id] = {
        "status": "running",
        "total": 0,
        "current": 0,
        "current_item": "FSS 적금 상품 조회 중...",
        "success_count": 0,
        "failed_count": 0,
        "phase": "",
        "description": "FSS 적금 상품 적재",
        "error_message": None,
        "items_history": [],
        "operator_id": operator_id,
        "created_at": datetime.now(timezone.utc),
    }

    progress_tracker._progress[task_id]["items_history"].append({
        "index": 0,
        "item": "FSS 적금 상품 조회 시작",
        "success": True,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    def load_savings_async():
        try:
            db_session = SessionLocal()
            loader = RealDataLoader(db_session)

            def savings_progress_callback(current: int, item: str, success: bool = True):
                with progress_tracker._lock:
                    if task_id in progress_tracker._progress:
                        if current == -1 and item.startswith("[TOTAL]"):
                            try:
                                total_count = int(item.replace("[TOTAL]", ""))
                                progress_tracker._progress[task_id]["total"] = total_count
                                progress_tracker._progress[task_id]["current_item"] = f"적금 상품 {total_count}건 저장 중..."
                                progress_tracker._progress[task_id]["items_history"].append({
                                    "index": len(progress_tracker._progress[task_id]["items_history"]),
                                    "item": f"전체 {total_count}건 조회됨",
                                    "success": True,
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                })
                            except (ValueError, IndexError) as e:
                                logger.error(f"[SAVINGS] Error parsing total: {e}")
                        else:
                            progress_tracker._progress[task_id]["current"] = current
                            progress_tracker._progress[task_id]["current_item"] = item
                            if success:
                                progress_tracker._progress[task_id]["success_count"] = current
                            else:
                                progress_tracker._progress[task_id]["failed_count"] = (
                                    progress_tracker._progress[task_id].get("failed_count", 0) + 1
                                )
                            progress_tracker._progress[task_id]["items_history"].append({
                                "index": len(progress_tracker._progress[task_id]["items_history"]),
                                "item": item,
                                "success": success,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            })

            result = loader.load_savings_products(
                operator_id=operator_id,
                operator_reason="FSS 적금 상품 적재",
                progress_callback=savings_progress_callback,
            )

            if result.success:
                with progress_tracker._lock:
                    if task_id in progress_tracker._progress:
                        progress_tracker._progress[task_id]["total"] = result.total_records
                        progress_tracker._progress[task_id]["current"] = result.total_records
                        progress_tracker._progress[task_id]["success_count"] = result.success_records
                        progress_tracker._progress[task_id]["failed_count"] = result.failed_records
                        progress_tracker._progress[task_id]["current_item"] = f"적금 상품 적재 완료: {result.success_records}건"
                        progress_tracker._progress[task_id]["items_history"].append({
                            "index": len(progress_tracker._progress[task_id]["items_history"]),
                            "item": f"적금 상품 적재 완료: {result.success_records}건 성공, {result.failed_records}건 실패",
                            "success": True,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })

                progress_tracker.complete_task(task_id, status="completed")
                logger.info(f"[SAVINGS] 적금 적재 완료: {result.success_records}건 성공")
            else:
                raise Exception(result.error_message or "적금 적재 실패")

        except Exception as e:
            logger.error(f"[SAVINGS] 적금 적재 실패: {str(e)}")
            with progress_tracker._lock:
                if task_id in progress_tracker._progress:
                    progress_tracker._progress[task_id]["current_item"] = f"오류: {str(e)}"
                    progress_tracker._progress[task_id]["error_message"] = str(e)
                    progress_tracker._progress[task_id]["items_history"].append({
                        "index": len(progress_tracker._progress[task_id]["items_history"]),
                        "item": f"오류 발생: {str(e)}",
                        "success": False,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
            progress_tracker.complete_task(task_id, status="failed")
        finally:
            db_session.close()

    background_tasks.add_task(load_savings_async)

    return {
        "status": "success",
        "task_id": task_id,
        "message": "FSS 적금 상품 조회 시작"
    }


@router.post("/load-annuity-savings")
async def load_annuity_savings(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """FSS 연금저축 상품 적재 (금융감독원 금융상품 한 눈에 API)

    보험/금융투자 권역의 연금저축 상품을 조회하여 annuity_savings_products + annuity_savings_options 테이블에 저장합니다.
    다중 페이지 순차 호출 (최대 60페이지).
    """
    operator_id = str(current_user.id)
    task_id = f"annuity_{uuid.uuid4().hex[:8]}"

    # Progress 직접 초기화
    progress_tracker._progress[task_id] = {
        "status": "running",
        "total": 0,
        "current": 0,
        "current_item": "FSS 연금저축 상품 조회 중...",
        "success_count": 0,
        "failed_count": 0,
        "phase": "",
        "description": "FSS 연금저축 상품 적재",
        "error_message": None,
        "items_history": [],
        "operator_id": operator_id,
        "created_at": datetime.now(timezone.utc),
    }

    progress_tracker._progress[task_id]["items_history"].append({
        "index": 0,
        "item": "FSS 연금저축 상품 조회 시작",
        "success": True,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    def load_annuity_async():
        try:
            db_session = SessionLocal()
            loader = RealDataLoader(db_session)

            def annuity_progress_callback(current: int, item: str, success: bool = True):
                with progress_tracker._lock:
                    if task_id in progress_tracker._progress:
                        if current == -1 and item.startswith("[TOTAL]"):
                            try:
                                total_count = int(item.replace("[TOTAL]", ""))
                                progress_tracker._progress[task_id]["total"] = total_count
                                progress_tracker._progress[task_id]["current_item"] = f"연금저축 상품 {total_count}건 저장 중..."
                                progress_tracker._progress[task_id]["items_history"].append({
                                    "index": len(progress_tracker._progress[task_id]["items_history"]),
                                    "item": f"전체 {total_count}건 조회됨",
                                    "success": True,
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                })
                            except (ValueError, IndexError) as e:
                                logger.error(f"[ANNUITY] Error parsing total: {e}")
                        else:
                            progress_tracker._progress[task_id]["current"] = current
                            progress_tracker._progress[task_id]["current_item"] = item
                            if success:
                                progress_tracker._progress[task_id]["success_count"] = current
                            else:
                                progress_tracker._progress[task_id]["failed_count"] = (
                                    progress_tracker._progress[task_id].get("failed_count", 0) + 1
                                )
                            progress_tracker._progress[task_id]["items_history"].append({
                                "index": len(progress_tracker._progress[task_id]["items_history"]),
                                "item": item,
                                "success": success,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            })

            result = loader.load_annuity_savings_products(
                operator_id=operator_id,
                operator_reason="FSS 연금저축 상품 적재",
                progress_callback=annuity_progress_callback,
            )

            if result.success:
                with progress_tracker._lock:
                    if task_id in progress_tracker._progress:
                        progress_tracker._progress[task_id]["total"] = result.total_records
                        progress_tracker._progress[task_id]["current"] = result.total_records
                        progress_tracker._progress[task_id]["success_count"] = result.success_records
                        progress_tracker._progress[task_id]["failed_count"] = result.failed_records
                        progress_tracker._progress[task_id]["current_item"] = f"연금저축 상품 적재 완료: {result.success_records}건"
                        progress_tracker._progress[task_id]["items_history"].append({
                            "index": len(progress_tracker._progress[task_id]["items_history"]),
                            "item": f"연금저축 상품 적재 완료: {result.success_records}건 성공, {result.failed_records}건 실패",
                            "success": True,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })

                progress_tracker.complete_task(task_id, status="completed")
                logger.info(f"[ANNUITY] 연금저축 적재 완료: {result.success_records}건 성공")
            else:
                raise Exception(result.error_message or "연금저축 적재 실패")

        except Exception as e:
            logger.error(f"[ANNUITY] 연금저축 적재 실패: {str(e)}")
            with progress_tracker._lock:
                if task_id in progress_tracker._progress:
                    progress_tracker._progress[task_id]["current_item"] = f"오류: {str(e)}"
                    progress_tracker._progress[task_id]["error_message"] = str(e)
                    progress_tracker._progress[task_id]["items_history"].append({
                        "index": len(progress_tracker._progress[task_id]["items_history"]),
                        "item": f"오류 발생: {str(e)}",
                        "success": False,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
            progress_tracker.complete_task(task_id, status="failed")
        finally:
            db_session.close()

    background_tasks.add_task(load_annuity_async)

    return {
        "status": "success",
        "task_id": task_id,
        "message": "FSS 연금저축 상품 조회 시작"
    }


@router.post("/load-mortgage-loans")
async def load_mortgage_loans(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """FSS 주택담보대출 상품 적재 (금융감독원 금융상품 한 눈에 API)

    은행/저축은행/보험 권역의 주택담보대출 상품을 조회하여
    mortgage_loan_products + mortgage_loan_options 테이블에 저장합니다.
    """
    operator_id = str(current_user.id)
    task_id = f"mortgage_{uuid.uuid4().hex[:8]}"

    progress_tracker._progress[task_id] = {
        "status": "running",
        "total": 0,
        "current": 0,
        "current_item": "FSS 주택담보대출 상품 조회 중...",
        "success_count": 0,
        "failed_count": 0,
        "phase": "",
        "description": "FSS 주택담보대출 상품 적재",
        "error_message": None,
        "items_history": [],
        "operator_id": operator_id,
        "created_at": datetime.now(timezone.utc),
    }

    progress_tracker._progress[task_id]["items_history"].append({
        "index": 0,
        "item": "FSS 주택담보대출 상품 조회 시작",
        "success": True,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    def load_mortgage_async():
        try:
            db_session = SessionLocal()
            loader = RealDataLoader(db_session)

            def mortgage_progress_callback(current: int, item: str, success: bool = True):
                with progress_tracker._lock:
                    if task_id in progress_tracker._progress:
                        if current == -1 and item.startswith("[TOTAL]"):
                            try:
                                total_count = int(item.replace("[TOTAL]", ""))
                                progress_tracker._progress[task_id]["total"] = total_count
                                progress_tracker._progress[task_id]["current_item"] = f"주택담보대출 상품 {total_count}건 저장 중..."
                                progress_tracker._progress[task_id]["items_history"].append({
                                    "index": len(progress_tracker._progress[task_id]["items_history"]),
                                    "item": f"전체 {total_count}건 조회됨",
                                    "success": True,
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                })
                            except (ValueError, IndexError) as e:
                                logger.error(f"[MORTGAGE] Error parsing total: {e}")
                        else:
                            progress_tracker._progress[task_id]["current"] = current
                            progress_tracker._progress[task_id]["current_item"] = item
                            if success:
                                progress_tracker._progress[task_id]["success_count"] = current
                            else:
                                progress_tracker._progress[task_id]["failed_count"] = (
                                    progress_tracker._progress[task_id].get("failed_count", 0) + 1
                                )
                            progress_tracker._progress[task_id]["items_history"].append({
                                "index": len(progress_tracker._progress[task_id]["items_history"]),
                                "item": item,
                                "success": success,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            })

            result = loader.load_mortgage_loan_products(
                operator_id=operator_id,
                operator_reason="FSS 주택담보대출 상품 적재",
                progress_callback=mortgage_progress_callback,
            )

            if result.success:
                with progress_tracker._lock:
                    if task_id in progress_tracker._progress:
                        progress_tracker._progress[task_id]["total"] = result.total_records
                        progress_tracker._progress[task_id]["current"] = result.total_records
                        progress_tracker._progress[task_id]["success_count"] = result.success_records
                        progress_tracker._progress[task_id]["failed_count"] = result.failed_records
                        progress_tracker._progress[task_id]["current_item"] = f"주택담보대출 상품 적재 완료: {result.success_records}건"
                        progress_tracker._progress[task_id]["items_history"].append({
                            "index": len(progress_tracker._progress[task_id]["items_history"]),
                            "item": f"주택담보대출 상품 적재 완료: {result.success_records}건 성공, {result.failed_records}건 실패",
                            "success": True,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })

                progress_tracker.complete_task(task_id, status="completed")
                logger.info(f"[MORTGAGE] 주택담보대출 적재 완료: {result.success_records}건 성공")
            else:
                raise Exception(result.error_message or "주택담보대출 적재 실패")

        except Exception as e:
            logger.error(f"[MORTGAGE] 주택담보대출 적재 실패: {str(e)}")
            with progress_tracker._lock:
                if task_id in progress_tracker._progress:
                    progress_tracker._progress[task_id]["current_item"] = f"오류: {str(e)}"
                    progress_tracker._progress[task_id]["error_message"] = str(e)
                    progress_tracker._progress[task_id]["items_history"].append({
                        "index": len(progress_tracker._progress[task_id]["items_history"]),
                        "item": f"오류 발생: {str(e)}",
                        "success": False,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
            progress_tracker.complete_task(task_id, status="failed")
        finally:
            db_session.close()

    background_tasks.add_task(load_mortgage_async)

    return {
        "status": "success",
        "task_id": task_id,
        "message": "FSS 주택담보대출 상품 조회 시작"
    }


@router.post("/load-rent-house-loans")
async def load_rent_house_loans(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """FSS 전세자금대출 상품 적재 (금융감독원 금융상품 한 눈에 API)"""
    operator_id = str(current_user.id)
    task_id = f"rentloan_{uuid.uuid4().hex[:8]}"

    progress_tracker._progress[task_id] = {
        "status": "running",
        "total": 0,
        "current": 0,
        "current_item": "FSS 전세자금대출 상품 조회 중...",
        "success_count": 0,
        "failed_count": 0,
        "phase": "",
        "description": "FSS 전세자금대출 상품 적재",
        "error_message": None,
        "items_history": [],
        "operator_id": operator_id,
        "created_at": datetime.now(timezone.utc),
    }

    progress_tracker._progress[task_id]["items_history"].append({
        "index": 0,
        "item": "FSS 전세자금대출 상품 조회 시작",
        "success": True,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    def load_rent_loan_async():
        try:
            db_session = SessionLocal()
            loader = RealDataLoader(db_session)

            def rent_loan_progress_callback(current: int, item: str, success: bool = True):
                with progress_tracker._lock:
                    if task_id in progress_tracker._progress:
                        if current == -1 and item.startswith("[TOTAL]"):
                            try:
                                total_count = int(item.replace("[TOTAL]", ""))
                                progress_tracker._progress[task_id]["total"] = total_count
                                progress_tracker._progress[task_id]["current_item"] = f"전세자금대출 상품 {total_count}건 저장 중..."
                                progress_tracker._progress[task_id]["items_history"].append({
                                    "index": len(progress_tracker._progress[task_id]["items_history"]),
                                    "item": f"전체 {total_count}건 조회됨",
                                    "success": True,
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                })
                            except (ValueError, IndexError) as e:
                                logger.error(f"[RENT_LOAN] Error parsing total: {e}")
                        else:
                            progress_tracker._progress[task_id]["current"] = current
                            progress_tracker._progress[task_id]["current_item"] = item
                            if success:
                                progress_tracker._progress[task_id]["success_count"] = current
                            else:
                                progress_tracker._progress[task_id]["failed_count"] = (
                                    progress_tracker._progress[task_id].get("failed_count", 0) + 1
                                )
                            progress_tracker._progress[task_id]["items_history"].append({
                                "index": len(progress_tracker._progress[task_id]["items_history"]),
                                "item": item,
                                "success": success,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            })

            result = loader.load_rent_house_loan_products(
                operator_id=operator_id,
                operator_reason="FSS 전세자금대출 상품 적재",
                progress_callback=rent_loan_progress_callback,
            )

            if result.success:
                with progress_tracker._lock:
                    if task_id in progress_tracker._progress:
                        progress_tracker._progress[task_id]["total"] = result.total_records
                        progress_tracker._progress[task_id]["current"] = result.total_records
                        progress_tracker._progress[task_id]["success_count"] = result.success_records
                        progress_tracker._progress[task_id]["failed_count"] = result.failed_records
                        progress_tracker._progress[task_id]["current_item"] = f"전세자금대출 상품 적재 완료: {result.success_records}건"
                        progress_tracker._progress[task_id]["items_history"].append({
                            "index": len(progress_tracker._progress[task_id]["items_history"]),
                            "item": f"전세자금대출 상품 적재 완료: {result.success_records}건 성공, {result.failed_records}건 실패",
                            "success": True,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                progress_tracker.complete_task(task_id, status="completed")
                logger.info(f"[RENT_LOAN] 전세자금대출 적재 완료: {result.success_records}건 성공")
            else:
                raise Exception(result.error_message or "전세자금대출 적재 실패")

        except Exception as e:
            logger.error(f"[RENT_LOAN] 전세자금대출 적재 실패: {str(e)}")
            with progress_tracker._lock:
                if task_id in progress_tracker._progress:
                    progress_tracker._progress[task_id]["current_item"] = f"오류: {str(e)}"
                    progress_tracker._progress[task_id]["error_message"] = str(e)
                    progress_tracker._progress[task_id]["items_history"].append({
                        "index": len(progress_tracker._progress[task_id]["items_history"]),
                        "item": f"오류 발생: {str(e)}",
                        "success": False,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
            progress_tracker.complete_task(task_id, status="failed")
        finally:
            db_session.close()

    background_tasks.add_task(load_rent_loan_async)

    return {
        "status": "success",
        "task_id": task_id,
        "message": "FSS 전세자금대출 상품 조회 시작"
    }


@router.post("/load-credit-loans")
async def load_credit_loans(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """FSS 개인신용대출 상품 적재 (금융감독원 금융상품 한 눈에 API)"""
    operator_id = str(current_user.id)
    task_id = f"creditloan_{uuid.uuid4().hex[:8]}"

    progress_tracker._progress[task_id] = {
        "status": "running",
        "total": 0,
        "current": 0,
        "current_item": "FSS 개인신용대출 상품 조회 중...",
        "success_count": 0,
        "failed_count": 0,
        "phase": "",
        "description": "FSS 개인신용대출 상품 적재",
        "error_message": None,
        "items_history": [],
        "operator_id": operator_id,
        "created_at": datetime.now(timezone.utc),
    }

    progress_tracker._progress[task_id]["items_history"].append({
        "index": 0,
        "item": "FSS 개인신용대출 상품 조회 시작",
        "success": True,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    def load_credit_loan_async():
        try:
            db_session = SessionLocal()
            loader = RealDataLoader(db_session)

            def credit_loan_progress_callback(current: int, item: str, success: bool = True):
                with progress_tracker._lock:
                    if task_id in progress_tracker._progress:
                        if current == -1 and item.startswith("[TOTAL]"):
                            try:
                                total_count = int(item.replace("[TOTAL]", ""))
                                progress_tracker._progress[task_id]["total"] = total_count
                                progress_tracker._progress[task_id]["current_item"] = f"개인신용대출 상품 {total_count}건 저장 중..."
                                progress_tracker._progress[task_id]["items_history"].append({
                                    "index": len(progress_tracker._progress[task_id]["items_history"]),
                                    "item": f"전체 {total_count}건 조회됨",
                                    "success": True,
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                })
                            except (ValueError, IndexError) as e:
                                logger.error(f"[CREDIT_LOAN] Error parsing total: {e}")
                        else:
                            progress_tracker._progress[task_id]["current"] = current
                            progress_tracker._progress[task_id]["current_item"] = item
                            if success:
                                progress_tracker._progress[task_id]["success_count"] = current
                            else:
                                progress_tracker._progress[task_id]["failed_count"] = (
                                    progress_tracker._progress[task_id].get("failed_count", 0) + 1
                                )
                            progress_tracker._progress[task_id]["items_history"].append({
                                "index": len(progress_tracker._progress[task_id]["items_history"]),
                                "item": item,
                                "success": success,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            })

            result = loader.load_credit_loan_products(
                operator_id=operator_id,
                operator_reason="FSS 개인신용대출 상품 적재",
                progress_callback=credit_loan_progress_callback,
            )

            if result.success:
                with progress_tracker._lock:
                    if task_id in progress_tracker._progress:
                        progress_tracker._progress[task_id]["total"] = result.total_records
                        progress_tracker._progress[task_id]["current"] = result.total_records
                        progress_tracker._progress[task_id]["success_count"] = result.success_records
                        progress_tracker._progress[task_id]["failed_count"] = result.failed_records
                        progress_tracker._progress[task_id]["current_item"] = f"개인신용대출 상품 적재 완료: {result.success_records}건"
                        progress_tracker._progress[task_id]["items_history"].append({
                            "index": len(progress_tracker._progress[task_id]["items_history"]),
                            "item": f"개인신용대출 상품 적재 완료: {result.success_records}건 성공, {result.failed_records}건 실패",
                            "success": True,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                progress_tracker.complete_task(task_id, status="completed")
                logger.info(f"[CREDIT_LOAN] 개인신용대출 적재 완료: {result.success_records}건 성공")
            else:
                raise Exception(result.error_message or "개인신용대출 적재 실패")

        except Exception as e:
            logger.error(f"[CREDIT_LOAN] 개인신용대출 적재 실패: {str(e)}")
            with progress_tracker._lock:
                if task_id in progress_tracker._progress:
                    progress_tracker._progress[task_id]["current_item"] = f"오류: {str(e)}"
                    progress_tracker._progress[task_id]["error_message"] = str(e)
                    progress_tracker._progress[task_id]["items_history"].append({
                        "index": len(progress_tracker._progress[task_id]["items_history"]),
                        "item": f"오류 발생: {str(e)}",
                        "success": False,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
            progress_tracker.complete_task(task_id, status="failed")
        finally:
            db_session.close()

    background_tasks.add_task(load_credit_loan_async)

    return {
        "status": "success",
        "task_id": task_id,
        "message": "FSS 개인신용대출 상품 조회 시작"
    }


@router.post("/fdr/load-stock-listing")
async def load_fdr_stock_listing(
    payload: FdrStockListingLoadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """FinanceDataReader 종목 마스터 적재"""
    try:
        loader = RealDataLoader(db)
        result = loader.load_fdr_stock_listing(
            market=payload.market,
            as_of_date=payload.as_of_date or date.today(),
            operator_id=str(current_user.id),
            operator_reason=f"FDR 종목 마스터 적재 ({payload.market})",
        )
        return {
            "status": "success",
            "message": "FDR 종목 마스터 적재 완료",
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
    """DART 기업 액션(분할/합병) 적재 — year/quarter 또는 start_date/end_date"""
    try:
        # quarter → 날짜 변환
        quarter_ranges = {
            "Q1": (1, 1, 3, 31),
            "Q2": (4, 1, 6, 30),
            "Q3": (7, 1, 9, 30),
            "Q4": (10, 1, 12, 31),
            "ALL": (1, 1, 12, 31),
        }

        if payload.year and payload.quarter:
            sm, sd, em, ed = quarter_ranges[payload.quarter]
            start = date(payload.year, sm, sd)
            end = date(payload.year, em, ed)
        elif payload.start_date and payload.end_date:
            start = payload.start_date
            end = payload.end_date
        else:
            raise HTTPException(
                status_code=400,
                detail="year+quarter 또는 start_date+end_date를 입력하세요",
            )

        loader = RealDataLoader(db)
        result = loader.load_corporate_actions(
            start_date=start,
            end_date=end,
            as_of_date=payload.as_of_date or date.today(),
            corp_cls=payload.corp_cls,
            operator_id=str(current_user.id),
            operator_reason=f"DART 기업 액션 적재 ({payload.quarter or f'{start}~{end}'})",
        )
        return {
            "status": "success",
            "message": f"기업 액션 적재 완료 ({start}~{end})",
            "result": result.__dict__,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dart/load-financials")
async def load_dart_financials(
    background_tasks: BackgroundTasks,
    fiscal_year: int = Query(2024),
    report_type: str = Query("ANNUAL"),
    limit: Optional[int] = Query(None, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """DART 재무제표 적재 + PER/PBR 계산 (백그라운드)

    financial_statement 테이블에 재무제표를 저장하고,
    stocks.pe_ratio / pb_ratio를 market_cap 기반으로 계산하여 업데이트합니다.

    - fiscal_year: 회계연도 (기본 2024)
    - report_type: ANNUAL | Q1 | Q2 | Q3
    - limit: 테스트용 종목 수 제한 (시가총액 내림차순)
    """
    task_id = f"dart_fin_{uuid.uuid4().hex[:8]}"
    operator_id = str(current_user.id)

    def run_dart_financials_loading():
        from app.database import SessionLocal
        from app.progress_tracker import progress_tracker

        progress_tracker.start_task(task_id, 0, f"DART 재무제표 적재 (FY{fiscal_year} {report_type})")

        db = SessionLocal()
        try:
            loader = RealDataLoader(db)

            def on_progress(current, ticker):
                progress_tracker.update_progress(
                    task_id,
                    current=current,
                    current_item=f"처리 중: {ticker}",
                )

            result = loader.load_financials_from_dart(
                fiscal_year=fiscal_year,
                report_type=report_type,
                limit=limit,
                operator_id=operator_id,
                operator_reason=f"DART 재무제표 적재 (FY{fiscal_year} {report_type})",
                progress_callback=on_progress,
            )
            progress_tracker.update_progress(
                task_id,
                current=result.total_records,
                current_item=f"완료: {result.success_records}건 성공, {result.failed_records}건 실패, {result.skipped_records}건 스킵",
                success=True,
            )
            progress_tracker.complete_task(task_id, "completed")
            logger.info(f"DART financials loading completed: batch_id={result.batch_id}")
        except Exception as e:
            logger.error(f"DART financials loading failed: {str(e)}", exc_info=True)
            progress_tracker.update_progress(
                task_id,
                current=0,
                current_item=f"실패: {str(e)}",
                success=False,
                error=str(e),
            )
            progress_tracker.complete_task(task_id, "failed")
        finally:
            db.close()

    background_tasks.add_task(run_dart_financials_loading)

    return {
        "status": "success",
        "message": "DART 재무제표 수집 시작",
        "task_id": task_id,
    }


@router.get("/data-status")
async def get_data_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW"))
):
    """DB 종목 통계"""
    from sqlalchemy import func
    from app.models.securities import Stock, ETF, Bond, DepositProduct, SavingsProduct, AnnuitySavingsProduct, MortgageLoanProduct, RentHouseLoanProduct, CreditLoanProduct

    stock_count = db.query(func.count(Stock.ticker)).scalar()
    etf_count = db.query(func.count(ETF.ticker)).scalar()
    bond_count = db.query(func.count(Bond.name)).scalar()
    deposit_count = db.query(func.count(DepositProduct.name)).scalar()
    savings_count = db.query(func.count(SavingsProduct.name)).scalar()
    annuity_count = db.query(func.count(AnnuitySavingsProduct.id)).scalar()
    mortgage_count = db.query(func.count(MortgageLoanProduct.id)).scalar()
    rent_loan_count = db.query(func.count(RentHouseLoanProduct.id)).scalar()
    credit_loan_count = db.query(func.count(CreditLoanProduct.id)).scalar()

    return {
        "stocks": stock_count,
        "etfs": etf_count,
        "bonds": bond_count,
        "deposits": deposit_count,
        "savings": savings_count,
        "annuity_savings": annuity_count,
        "mortgage_loans": mortgage_count,
        "rent_house_loans": rent_loan_count,
        "credit_loans": credit_loan_count,
        "total": stock_count + etf_count + bond_count + deposit_count + savings_count + annuity_count + mortgage_count + rent_loan_count + credit_loan_count
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
    logger.info(f"Progress API called - task_id: {task_id}, status: {progress.get('status')}, current: {progress.get('current')}, current_item: {progress.get('current_item')}, success_count: {progress.get('success_count')}, failed_count: {progress.get('failed_count')}")

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


# ========================================================================
# pykrx 일별 시세 적재 (병렬 처리 최적화)
# ========================================================================

@router.post("/pykrx/load-daily-prices")
async def load_daily_prices(
    req: DailyPricesLoadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """pykrx를 이용하여 일별 시세 적재

    Parameters:
    - start_date: 시작일 (YYYYMMDD)
    - end_date: 종료일 (YYYYMMDD)
    - tickers: 종목코드 리스트 (None이면 인기 종목 20개 사용)
    - parallel: 병렬 처리 여부 (기본값: True, 권장)
    - num_workers: 동시 스레드 수 (기본값: 8, 1-16)

    Returns:
    - task_id: 진행 상황 추적용 ID
    - 병렬 처리로 50-80% 시간 단축 가능
    """
    try:
        task_id = f"daily_prices_{uuid.uuid4().hex[:8]}"
        operator_id = str(current_user.id)

        def run_load_task():
            db_local = SessionLocal()
            try:
                loader = PyKrxDataLoader()

                # BatchManager로 배치 생성 (실패해도 적재는 계속)
                batch_id = None
                try:
                    from datetime import datetime as dt
                    start_dt = dt.strptime(req.start_date, "%Y%m%d").date()
                    end_dt = dt.strptime(req.end_date, "%Y%m%d").date()
                    bm = BatchManager(db_local)
                    batch = bm.create_batch(
                        batch_type=BatchType.PRICE,
                        source_id='PYKRX',
                        as_of_date=end_dt,
                        target_start=start_dt,
                        target_end=end_dt,
                        operator_id=operator_id,
                        operator_reason="pykrx 일별 시세 적재",
                    )
                    batch_id = batch.batch_id
                    logger.info(f"Created batch {batch_id} for daily prices")
                except Exception as be:
                    logger.warning(f"BatchManager create failed (continuing without batch): {be}")

                if req.parallel:
                    # 병렬 처리 (권장)
                    result = loader.load_all_daily_prices_parallel(
                        db=db_local,
                        start_date=req.start_date,
                        end_date=req.end_date,
                        tickers=req.tickers,
                        task_id=task_id,
                        num_workers=req.num_workers,
                        source_id='PYKRX',
                        batch_id=batch_id,
                    )
                else:
                    # 순차 처리 (호환성)
                    result = loader.load_all_daily_prices(
                        db=db_local,
                        start_date=req.start_date,
                        end_date=req.end_date,
                        tickers=req.tickers,
                        task_id=task_id
                    )

                progress_tracker.complete_task(task_id, "completed")
                logger.info(f"Daily prices loading completed: {result}")

            except Exception as e:
                logger.error(f"Failed to load daily prices: {str(e)}")
                progress_tracker.complete_task(task_id, "failed", error=str(e))
            finally:
                db_local.close()

        background_tasks.add_task(run_load_task)

        return {
            "success": True,
            "message": f"일별 시세 적재 작업 시작 (병렬: {req.parallel}, 스레드: {req.num_workers})",
            "task_id": task_id,
            "processing_mode": "parallel" if req.parallel else "sequential"
        }

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start daily prices loading: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ========================================================================
# 증분 시계열 적재 (stocks 테이블 기준 5년치)
# ========================================================================

@router.post("/pykrx/load-stocks-incremental")
async def load_stocks_incremental(
    req: IncrementalLoadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN"))
):
    """stocks 테이블 전체 종목 대상 증분 시계열 적재

    - 이미 적재된 종목: 마지막 적재일 다음 날부터 오늘까지
    - 미적재 종목: default_days 이전부터 오늘까지
    - 모든 종목이 최신이면 스킵

    Parameters:
    - default_days: 신규 종목 수집 일수 (기본 1825 = 5년)
    - num_workers: 스레드 수 (기본 4, 최대 8)
    - market: 시장 필터 (KOSPI/KOSDAQ/None=전체)
    """
    try:
        task_id = f"incremental_{uuid.uuid4().hex[:8]}"
        operator_id = str(current_user.id)

        # 사전 통계 조회 (즉시 응답에 포함)
        from app.models.securities import Stock
        from app.models.real_data import StockPriceDaily
        from sqlalchemy import func as sa_func

        stock_query = db.query(sa_func.count(Stock.ticker))
        if req.market:
            stock_query = stock_query.filter(Stock.market == req.market.upper())
        total_stocks = stock_query.scalar() or 0

        existing_tickers = (
            db.query(sa_func.count(sa_func.distinct(StockPriceDaily.ticker)))
            .filter(StockPriceDaily.source_id == 'PYKRX')
            .scalar() or 0
        )

        new_stocks = max(0, total_stocks - existing_tickers)

        def run_incremental_load():
            db_local = SessionLocal()
            try:
                loader = PyKrxDataLoader()

                # BatchManager로 배치 생성
                batch_id_val = None
                try:
                    from datetime import datetime as dt
                    bm = BatchManager(db_local)
                    batch = bm.create_batch(
                        batch_type=BatchType.PRICE,
                        source_id='PYKRX',
                        as_of_date=dt.now().date(),
                        target_start=dt.now().date(),
                        target_end=dt.now().date(),
                        operator_id=operator_id,
                        operator_reason=f"증분 시계열 적재 (default_days={req.default_days})",
                    )
                    batch_id_val = batch.batch_id
                    logger.info(f"Created batch {batch_id_val} for incremental load")
                except Exception as be:
                    logger.warning(f"BatchManager create failed (continuing): {be}")

                result = loader.load_all_stocks_incremental(
                    db=db_local,
                    default_days=req.default_days,
                    task_id=task_id,
                    num_workers=req.num_workers,
                    source_id='PYKRX',
                    batch_id=batch_id_val,
                    market=req.market,
                )

                logger.info(f"Incremental load completed: {result.get('success', 0)} success, "
                           f"{result.get('failed', 0)} failed, {result.get('skipped', 0)} skipped")

            except Exception as e:
                logger.error(f"Failed incremental load: {str(e)}")
                progress_tracker.complete_task(task_id, "failed", error=str(e))
            finally:
                db_local.close()

        background_tasks.add_task(run_incremental_load)

        return {
            "success": True,
            "task_id": task_id,
            "message": f"증분 적재 시작 (대상: {total_stocks}종목, 신규 추정: {new_stocks}, 스레드: {req.num_workers})",
            "stats": {
                "total_stocks": total_stocks,
                "existing_tickers": existing_tickers,
                "new_stocks_estimate": new_stocks,
                "default_days": req.default_days,
                "num_workers": req.num_workers,
                "market": req.market or "전체",
            }
        }

    except Exception as e:
        logger.error(f"Failed to start incremental load: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Compass Score
# ============================================================

@router.get("/scoring/compass/{ticker}")
async def get_compass_score(
    ticker: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Foresto Compass Score — 종합 투자 학습 점수 (0-100)"""
    from app.services.scoring_engine import ScoringEngine

    result = ScoringEngine.calculate_compass_score(db, ticker)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/scoring/batch-compute")
async def batch_compute_compass_scores(
    background_tasks: BackgroundTasks,
    market: Optional[str] = Query(None, description="시장 필터 (KOSPI, KOSDAQ)"),
    limit: int = Query(100, ge=1, le=3000, description="최대 종목 수"),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN")),
):
    """Compass Score 일괄 계산 — 활성 종목의 compass 점수를 사전 계산하여 stocks 테이블에 저장"""
    from app.services.scoring_engine import ScoringEngine
    from app.models.securities import Stock
    from app.utils.kst_now import kst_now

    task_id = f"compass_{uuid.uuid4().hex[:8]}"
    operator_id = str(current_user.id)

    def _batch_compute():
        db = SessionLocal()
        try:
            query = db.query(Stock).filter(Stock.is_active == True)
            if market:
                query = query.filter(Stock.market == market)
            stocks = query.limit(limit).all()
            total = len(stocks)

            progress_tracker.start_task(task_id, total, "Compass Score 일괄 계산")
            logger.info(f"[batch-compute] started: {total} stocks (operator={operator_id})")

            success_count = 0
            fail_count = 0

            for i, stock in enumerate(stocks):
                try:
                    result = ScoringEngine.calculate_compass_score(db, stock.ticker)
                    if "error" not in result:
                        stock.compass_score = result["compass_score"]
                        stock.compass_grade = result["grade"]
                        stock.compass_summary = result.get("summary", "")[:200]
                        stock.compass_commentary = result.get("commentary", "")[:2000]
                        cats = result.get("categories", {})
                        stock.compass_financial_score = cats.get("financial", {}).get("score") if cats.get("financial") else None
                        stock.compass_valuation_score = cats.get("valuation", {}).get("score") if cats.get("valuation") else None
                        stock.compass_technical_score = cats.get("technical", {}).get("score") if cats.get("technical") else None
                        stock.compass_risk_score = cats.get("risk", {}).get("score") if cats.get("risk") else None
                        stock.compass_updated_at = kst_now()
                        db.commit()
                        success_count += 1
                        progress_tracker.update_progress(
                            task_id, i + 1,
                            current_item=f"{stock.ticker} {stock.name}: {result['compass_score']}점 ({result['grade']})",
                            success=True,
                        )
                    else:
                        fail_count += 1
                        progress_tracker.update_progress(
                            task_id, i + 1,
                            current_item=f"{stock.ticker} {stock.name}: {result['error']}",
                            success=False,
                        )
                except Exception as e:
                    db.rollback()
                    fail_count += 1
                    progress_tracker.update_progress(
                        task_id, i + 1,
                        current_item=f"{stock.ticker}: {str(e)[:80]}",
                        success=False,
                    )

            progress_tracker.complete_task(task_id, status="completed")
            logger.info(f"[batch-compute] done: success={success_count}, fail={fail_count}")
        except Exception as e:
            logger.error(f"[batch-compute] fatal: {e}")
            progress_tracker.complete_task(task_id, status="failed")
        finally:
            db.close()

    background_tasks.add_task(_batch_compute)

    return {
        "task_id": task_id,
        "message": f"Compass Score 일괄 계산 시작 (market={market or '전체'}, limit={limit})",
    }
