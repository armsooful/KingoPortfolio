"""
데이터 수집 자동 스케줄 서비스 — Phase 1 + Phase 2 + Phase 3

Phase 1 (일별, 영업일):
- 16:30 KST: 일별 시세 증분 적재 (pykrx)
- 17:00 KST: Compass Score 일괄 계산

Phase 2 (주간/월간):
- 토요일 10:00 KST: 종목 마스터 + 주식 정보 + ETF 순차 갱신
- 토요일 11:00 KST: DART 재무제표 적재
- 매월 1일 13:00 KST: 채권 + 금융상품 6종 순차 적재

Phase 3 (모니터링):
- DataCollectionLog 이력 기록
- 정합성 검증 (job별 SQL 검증)
- 재시도 데코레이터 (max_retries=2, base_delay=30)
- 실패 시 OpsAlert + 이메일/Slack 알림
"""

import threading
import logging
import asyncio
import functools
import json
from datetime import date, datetime, timedelta

from app.database import SessionLocal
from app.utils.kst_now import kst_now

logger = logging.getLogger(__name__)

# ── 동시 실행 방지 Lock ──
_running_tasks: set = set()
_task_lock = threading.Lock()

# ── Job 라벨 매핑 ──
JOB_LABELS = {
    "incremental_prices": "일별 시세 증분 적재",
    "compass_batch": "Compass Score 일괄 계산",
    "weekly_stock_refresh": "주간 종목 갱신",
    "dart_financials": "DART 재무제표 적재",
    "monthly_products": "월간 금융상품 적재",
}


# ══════════════════════════════════════════
# Phase 3: 이력 기록 헬퍼
# ══════════════════════════════════════════

def _log_collection_start(db, job_name: str, job_label: str) -> int:
    """DataCollectionLog INSERT (status=running), return log.id"""
    try:
        from app.models.ops import DataCollectionLog
        log = DataCollectionLog(
            job_name=job_name,
            job_label=job_label,
            status="running",
            started_at=kst_now(),
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log.id
    except Exception as e:
        db.rollback()
        logger.error("Failed to create DataCollectionLog for %s: %s", job_name, e)
        return 0


def _log_collection_complete(
    db, log_id: int, success: int, failed: int, total: int,
    detail: dict = None, validation_status: str = None, validation_detail: dict = None,
):
    """DataCollectionLog UPDATE (status=completed)"""
    if not log_id:
        return
    try:
        from app.models.ops import DataCollectionLog
        log = db.query(DataCollectionLog).filter_by(id=log_id).first()
        if log:
            now = kst_now()
            log.status = "completed"
            log.completed_at = now
            log.duration_seconds = (now - log.started_at).total_seconds()
            log.success_count = success
            log.failed_count = failed
            log.total_count = total
            log.detail = detail
            log.validation_status = validation_status
            log.validation_detail = validation_detail
            db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Failed to update DataCollectionLog %d: %s", log_id, e)


def _log_collection_failed(db, log_id: int, error_message: str):
    """DataCollectionLog UPDATE (status=failed)"""
    if not log_id:
        return
    try:
        from app.models.ops import DataCollectionLog
        log = db.query(DataCollectionLog).filter_by(id=log_id).first()
        if log:
            now = kst_now()
            log.status = "failed"
            log.completed_at = now
            log.duration_seconds = (now - log.started_at).total_seconds()
            log.error_message = error_message[:2000]
            db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Failed to mark DataCollectionLog %d as failed: %s", log_id, e)


# ══════════════════════════════════════════
# Phase 3: 정합성 검증
# ══════════════════════════════════════════

def _validate_after_collection(db, job_name: str, result_counts: dict = None) -> tuple:
    """
    수집 후 간단한 SQL 기반 정합성 검증.
    Returns: (status: str, detail: dict)  — status = 'pass' | 'warn' | 'fail'
    """
    try:
        from sqlalchemy import text

        if job_name == "incremental_prices":
            today_str = date.today().isoformat()
            row = db.execute(text(
                "SELECT COUNT(*) FROM stock_price_daily WHERE trade_date = :d"
            ), {"d": today_str}).scalar() or 0
            if row == 0:
                return "fail", {"message": f"오늘({today_str}) 시세 0건", "count": row}
            if row < 1000:
                return "warn", {"message": f"오늘 시세 {row}건 (< 1000)", "count": row}
            return "pass", {"message": f"오늘 시세 {row}건", "count": row}

        elif job_name == "compass_batch":
            success = (result_counts or {}).get("success", 0)
            total = (result_counts or {}).get("total", 0)
            failed = (result_counts or {}).get("failed", 0)
            if success == 0:
                return "fail", {"message": "갱신 0건", "success": success, "total": total}
            if total > 0 and (failed / total) > 0.3:
                return "warn", {"message": f"실패율 {failed}/{total} > 30%", "success": success, "failed": failed}
            return "pass", {"message": f"갱신 {success}/{total}", "success": success, "total": total}

        elif job_name == "weekly_stock_refresh":
            row = db.execute(text("SELECT COUNT(*) FROM stocks")).scalar() or 0
            if row < 1000:
                return "fail", {"message": f"stocks {row}건 (< 1000)", "count": row}
            if row < 2500:
                return "warn", {"message": f"stocks {row}건 (< 2500)", "count": row}
            return "pass", {"message": f"stocks {row}건", "count": row}

        elif job_name == "dart_financials":
            success = (result_counts or {}).get("success", 0)
            total = (result_counts or {}).get("total", 0)
            failed = (result_counts or {}).get("failed", 0)
            if success == 0:
                return "fail", {"message": "적재 0건"}
            if total > 0 and (failed / total) > 0.5:
                return "warn", {"message": f"실패율 {failed}/{total} > 50%"}
            return "pass", {"message": f"적재 {success}/{total}"}

        elif job_name == "monthly_products":
            failed_steps = (result_counts or {}).get("failed_steps", [])
            total_steps = (result_counts or {}).get("total_steps", 7)
            if len(failed_steps) == total_steps:
                return "fail", {"message": "전체 실패", "failed_steps": failed_steps}
            if len(failed_steps) > 0:
                return "warn", {"message": f"{len(failed_steps)}/{total_steps} 실패", "failed_steps": failed_steps}
            return "pass", {"message": f"전체 성공 ({total_steps}개)"}

        return "pass", {"message": "검증 규칙 없음"}

    except Exception as e:
        logger.error("Validation error for %s: %s", job_name, e)
        return "warn", {"message": f"검증 오류: {str(e)[:200]}"}


# ══════════════════════════════════════════
# Phase 3: 알림 발송 헬퍼
# ══════════════════════════════════════════

def _create_collection_alert(db, job_name: str, alert_level: str, error_message: str, detail: dict = None):
    """OpsAlert 생성 + 채널 발송"""
    try:
        from app.models.ops import OpsAlert

        alert = OpsAlert(
            alert_type="BATCH_FAILED",
            alert_level=alert_level,
            alert_title=f"[데이터 수집] {job_name}",
            alert_message=error_message[:500],
            alert_detail=detail,
            created_at=kst_now(),
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        logger.info("OpsAlert created: [%s] %s", alert_level, job_name)

        # Phase 3: 실제 채널 발송
        try:
            from app.services.ops_alert_service import OpsAlertService
            svc = OpsAlertService(db)
            svc._dispatch_alert(alert, svc._get_default_channels(
                svc._resolve_alert_level(alert_level)
            ))
        except Exception as dispatch_err:
            logger.error("Alert dispatch failed for %s: %s", job_name, dispatch_err)

    except Exception as e:
        db.rollback()
        logger.error("Failed to create OpsAlert for %s: %s", job_name, e)


# ══════════════════════════════════════════
# Phase 3: 재시도 데코레이터
# ══════════════════════════════════════════

def with_retry(max_retries: int = 2, base_delay: int = 30):
    """
    async 함수용 재시도 데코레이터.
    실패 시 base_delay * attempt 초 대기 후 재시도.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, max_retries + 2):  # 1 ~ max_retries+1
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt <= max_retries:
                        wait = base_delay * attempt
                        logger.warning(
                            "[%s] attempt %d/%d 실패, %d초 후 재시도: %s",
                            func.__name__, attempt, max_retries + 1, wait, str(e)[:200],
                        )
                        await asyncio.sleep(wait)
                    else:
                        logger.error(
                            "[%s] 최종 실패 (attempt %d): %s",
                            func.__name__, attempt, str(e)[:200],
                        )
                        raise
        return wrapper
    return decorator


# ══════════════════════════════════════════
# 수집 함수들 (Phase 1 + 2 + 3)
# ══════════════════════════════════════════

@with_retry(max_retries=2, base_delay=30)
async def scheduled_incremental_load():
    """16:30 KST — 일별 시세 증분 적재 (pykrx → stock_price_daily)"""
    task_name = "incremental_prices"

    with _task_lock:
        if task_name in _running_tasks:
            logger.warning("[%s] 이미 실행 중 — 스킵", task_name)
            return
        _running_tasks.add(task_name)

    db = SessionLocal()
    log_id = _log_collection_start(db, task_name, JOB_LABELS[task_name])
    try:
        from app.services.pykrx_loader import PyKrxDataLoader

        logger.info("[%s] 시작 — %s", task_name, date.today())

        loader = PyKrxDataLoader()
        result = loader.load_all_stocks_incremental(
            db=db,
            default_days=1825,
            num_workers=4,
            source_id="PYKRX",
        )

        success = result.get("success", 0)
        failed = result.get("failed", 0)
        skipped = result.get("skipped", 0)
        total = success + failed + skipped

        logger.info(
            "[%s] 완료 — success=%d, failed=%d, skipped=%d",
            task_name, success, failed, skipped,
        )

        # 정합성 검증
        v_status, v_detail = _validate_after_collection(db, task_name)

        # 이력 기록
        _log_collection_complete(
            db, log_id, success, failed, total,
            detail={"skipped": skipped, "date": str(date.today())},
            validation_status=v_status,
            validation_detail=v_detail,
        )

        if failed > 0:
            _create_collection_alert(
                db,
                job_name=JOB_LABELS[task_name],
                alert_level="WARN",
                error_message=f"증분 적재 부분 실패: success={success}, failed={failed}, skipped={skipped}",
                detail={"success": success, "failed": failed, "skipped": skipped, "date": str(date.today())},
            )

    except Exception as e:
        logger.error("[%s] 실패: %s", task_name, e, exc_info=True)
        _log_collection_failed(db, log_id, str(e))
        _create_collection_alert(
            db,
            job_name=JOB_LABELS[task_name],
            alert_level="CRITICAL",
            error_message=str(e),
            detail={"date": str(date.today()), "error": str(e)[:500]},
        )
        raise  # 재시도 데코레이터가 잡음
    finally:
        db.close()
        with _task_lock:
            _running_tasks.discard(task_name)


@with_retry(max_retries=2, base_delay=30)
async def scheduled_compass_batch_compute():
    """17:00 KST — Compass Score 일괄 계산 (stocks 테이블 compass_* 갱신)"""
    task_name = "compass_batch"

    with _task_lock:
        if task_name in _running_tasks:
            logger.warning("[%s] 이미 실행 중 — 스킵", task_name)
            return
        _running_tasks.add(task_name)

    db = SessionLocal()
    log_id = _log_collection_start(db, task_name, JOB_LABELS[task_name])
    try:
        from app.services.scoring_engine import ScoringEngine
        from app.models.securities import Stock

        stocks = db.query(Stock).filter(Stock.is_active == True).all()
        total = len(stocks)

        logger.info("[%s] 시작 — %d종목", task_name, total)

        success_count = 0
        fail_count = 0

        for stock in stocks:
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
                else:
                    fail_count += 1
            except Exception as e:
                db.rollback()
                fail_count += 1
                logger.warning("[%s] %s 실패: %s", task_name, stock.ticker, str(e)[:100])

        logger.info("[%s] 완료 — success=%d, fail=%d / total=%d", task_name, success_count, fail_count, total)

        # 정합성 검증
        v_status, v_detail = _validate_after_collection(
            db, task_name,
            result_counts={"success": success_count, "failed": fail_count, "total": total},
        )

        # 이력 기록
        _log_collection_complete(
            db, log_id, success_count, fail_count, total,
            detail={"date": str(date.today())},
            validation_status=v_status,
            validation_detail=v_detail,
        )

        # 실패율 > 30% 시 알림
        if total > 0 and (fail_count / total) > 0.3:
            _create_collection_alert(
                db,
                job_name=JOB_LABELS[task_name],
                alert_level="WARN",
                error_message=f"실패율 {fail_count}/{total} ({fail_count/total*100:.1f}%) — 30% 초과",
                detail={"success": success_count, "failed": fail_count, "total": total, "date": str(date.today())},
            )

    except Exception as e:
        logger.error("[%s] 실패: %s", task_name, e, exc_info=True)
        _log_collection_failed(db, log_id, str(e))
        _create_collection_alert(
            db,
            job_name=JOB_LABELS[task_name],
            alert_level="CRITICAL",
            error_message=str(e),
            detail={"date": str(date.today()), "error": str(e)[:500]},
        )
        raise
    finally:
        db.close()
        with _task_lock:
            _running_tasks.discard(task_name)


# ── Phase 2: 주간/월간 수집 자동화 ──


@with_retry(max_retries=2, base_delay=30)
async def scheduled_weekly_stock_refresh():
    """토요일 10:00 KST — 종목 마스터 + 주식 정보 + ETF 순차 갱신"""
    task_name = "weekly_stock_refresh"

    with _task_lock:
        if task_name in _running_tasks:
            logger.warning("[%s] 이미 실행 중 — 스킵", task_name)
            return
        _running_tasks.add(task_name)

    db = SessionLocal()
    log_id = _log_collection_start(db, task_name, JOB_LABELS[task_name])
    try:
        from app.services.real_data_loader import RealDataLoader
        from app.services.data_loader import DataLoaderService

        loader = RealDataLoader(db)
        step_results = {}

        # Step 1: FDR 종목 마스터 (~20초)
        logger.info("[%s] Step 1/3: FDR 종목 마스터", task_name)
        result1 = loader.load_fdr_stock_listing(
            market="KRX",
            as_of_date=date.today(),
            operator_id="scheduler",
            operator_reason="주간 자동 갱신",
        )
        step_results["fdr_listing"] = {"total": result1.total_records}
        logger.info("[%s] Step 1 완료: %d건", task_name, result1.total_records)

        # Step 2: 주식 기본 정보 (~3-5분)
        logger.info("[%s] Step 2/3: 주식 기본 정보", task_name)
        result2 = loader.load_stocks_from_fdr(
            as_of_date=date.today(),
            operator_id="scheduler",
            operator_reason="주간 자동 갱신",
        )
        step_results["stocks"] = {"success": result2.success_records, "failed": result2.failed_records}
        logger.info("[%s] Step 2 완료: success=%d, failed=%d",
                     task_name, result2.success_records, result2.failed_records)

        # Step 3: ETF (~5-10분)
        logger.info("[%s] Step 3/3: ETF", task_name)
        result3 = DataLoaderService.load_etfs(db)
        step_results["etf"] = {"result": str(result3)[:200]}
        logger.info("[%s] Step 3 완료: %s", task_name, result3)

        total_success = result2.success_records
        total_failed = result2.failed_records

        logger.info("[%s] 전체 완료", task_name)

        # 정합성 검증
        v_status, v_detail = _validate_after_collection(db, task_name)

        _log_collection_complete(
            db, log_id, total_success, total_failed, total_success + total_failed,
            detail={"steps": step_results, "date": str(date.today())},
            validation_status=v_status,
            validation_detail=v_detail,
        )

    except Exception as e:
        logger.error("[%s] 실패: %s", task_name, e, exc_info=True)
        _log_collection_failed(db, log_id, str(e))
        _create_collection_alert(
            db, JOB_LABELS[task_name], "CRITICAL", str(e),
            {"date": str(date.today()), "error": str(e)[:500]},
        )
        raise
    finally:
        db.close()
        with _task_lock:
            _running_tasks.discard(task_name)


@with_retry(max_retries=2, base_delay=30)
async def scheduled_dart_financials():
    """토요일 11:00 KST — DART 재무제표 적재"""
    task_name = "dart_financials"

    with _task_lock:
        if task_name in _running_tasks:
            logger.warning("[%s] 이미 실행 중 — 스킵", task_name)
            return
        _running_tasks.add(task_name)

    db = SessionLocal()
    log_id = _log_collection_start(db, task_name, JOB_LABELS[task_name])
    try:
        from app.services.real_data_loader import RealDataLoader

        loader = RealDataLoader(db)

        # fiscal_year: 4월 이후면 전년도, 그 전이면 전전년도
        today = date.today()
        fiscal_year = today.year - 1 if today.month >= 4 else today.year - 2

        logger.info("[%s] 시작 — FY%d ANNUAL", task_name, fiscal_year)
        result = loader.load_financials_from_dart(
            fiscal_year=fiscal_year,
            report_type="ANNUAL",
            operator_id="scheduler",
            operator_reason=f"주간 자동 갱신 (FY{fiscal_year})",
        )
        logger.info("[%s] 완료 — success=%d, failed=%d",
                     task_name, result.success_records, result.failed_records)

        # 정합성 검증
        v_status, v_detail = _validate_after_collection(
            db, task_name,
            result_counts={"success": result.success_records, "failed": result.failed_records,
                           "total": result.total_records},
        )

        _log_collection_complete(
            db, log_id, result.success_records, result.failed_records, result.total_records,
            detail={"fiscal_year": fiscal_year, "date": str(date.today())},
            validation_status=v_status,
            validation_detail=v_detail,
        )

        # 실패율 > 50% 시 알림
        if result.total_records > 0 and (result.failed_records / result.total_records) > 0.5:
            _create_collection_alert(
                db, JOB_LABELS[task_name], "WARN",
                f"실패율 {result.failed_records}/{result.total_records}",
                {"fiscal_year": fiscal_year, "success": result.success_records,
                 "failed": result.failed_records},
            )

    except Exception as e:
        logger.error("[%s] 실패: %s", task_name, e, exc_info=True)
        _log_collection_failed(db, log_id, str(e))
        _create_collection_alert(
            db, JOB_LABELS[task_name], "CRITICAL", str(e),
            {"date": str(date.today()), "error": str(e)[:500]},
        )
        raise
    finally:
        db.close()
        with _task_lock:
            _running_tasks.discard(task_name)


@with_retry(max_retries=2, base_delay=30)
async def scheduled_monthly_financial_products():
    """매월 1일 13:00 KST — 채권 + 금융상품 6종 순차 적재"""
    task_name = "monthly_products"

    with _task_lock:
        if task_name in _running_tasks:
            logger.warning("[%s] 이미 실행 중 — 스킵", task_name)
            return
        _running_tasks.add(task_name)

    db = SessionLocal()
    log_id = _log_collection_start(db, task_name, JOB_LABELS[task_name])
    try:
        from app.services.real_data_loader import RealDataLoader

        loader = RealDataLoader(db)
        results = {}

        steps = [
            ("채권", lambda: loader.load_bond_basic_info(
                operator_id="scheduler", operator_reason="월간 자동 갱신")),
            ("정기예금", lambda: loader.load_deposit_products(
                operator_id="scheduler", operator_reason="월간 자동 갱신")),
            ("적금", lambda: loader.load_savings_products(
                operator_id="scheduler", operator_reason="월간 자동 갱신")),
            ("연금저축", lambda: loader.load_annuity_savings_products(
                operator_id="scheduler", operator_reason="월간 자동 갱신")),
            ("주택담보대출", lambda: loader.load_mortgage_loan_products(
                operator_id="scheduler", operator_reason="월간 자동 갱신")),
            ("전세자금대출", lambda: loader.load_rent_house_loan_products(
                operator_id="scheduler", operator_reason="월간 자동 갱신")),
            ("개인신용대출", lambda: loader.load_credit_loan_products(
                operator_id="scheduler", operator_reason="월간 자동 갱신")),
        ]

        total_success = 0
        total_failed = 0

        for i, (name, load_fn) in enumerate(steps, 1):
            try:
                logger.info("[%s] Step %d/7: %s", task_name, i, name)
                result = load_fn()
                results[name] = {"success": result.success_records, "failed": result.failed_records}
                total_success += result.success_records
                total_failed += result.failed_records
                logger.info("[%s] %s 완료: success=%d, failed=%d",
                            task_name, name, result.success_records, result.failed_records)
            except Exception as e:
                results[name] = {"error": str(e)[:200]}
                logger.error("[%s] %s 실패: %s", task_name, name, e)

        failed_steps = [k for k, v in results.items() if "error" in v]

        # 정합성 검증
        v_status, v_detail = _validate_after_collection(
            db, task_name,
            result_counts={"failed_steps": failed_steps, "total_steps": len(steps)},
        )

        _log_collection_complete(
            db, log_id, total_success, total_failed + len(failed_steps), len(steps),
            detail={"results": results, "date": str(date.today())},
            validation_status=v_status,
            validation_detail=v_detail,
        )

        if failed_steps:
            _create_collection_alert(
                db, JOB_LABELS[task_name], "WARN",
                f"실패 항목: {', '.join(failed_steps)}",
                {"results": results, "date": str(date.today())},
            )

        logger.info("[%s] 전체 완료 — 실패: %d/7", task_name, len(failed_steps))

    except Exception as e:
        logger.error("[%s] 실패: %s", task_name, e, exc_info=True)
        _log_collection_failed(db, log_id, str(e))
        _create_collection_alert(
            db, JOB_LABELS[task_name], "CRITICAL", str(e),
            {"date": str(date.today()), "error": str(e)[:500]},
        )
        raise
    finally:
        db.close()
        with _task_lock:
            _running_tasks.discard(task_name)
