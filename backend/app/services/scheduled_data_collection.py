"""
데이터 수집 자동 스케줄 서비스 — Phase 1 + Phase 2

Phase 1 (일별, 영업일):
- 16:30 KST: 일별 시세 증분 적재 (pykrx)
- 17:00 KST: Compass Score 일괄 계산

Phase 2 (주간/월간):
- 토요일 10:00 KST: 종목 마스터 + 주식 정보 + ETF 순차 갱신
- 토요일 11:00 KST: DART 재무제표 적재
- 매월 1일 13:00 KST: 채권 + 금융상품 6종 순차 적재
"""

import threading
import logging
import json
from datetime import date

from app.database import SessionLocal
from app.utils.kst_now import kst_now

logger = logging.getLogger(__name__)

# ── 동시 실행 방지 Lock ──
_running_tasks: set = set()
_task_lock = threading.Lock()


def _create_collection_alert(db, job_name: str, alert_level: str, error_message: str, detail: dict = None):
    """OpsAlert 생성 헬퍼"""
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
        logger.info("OpsAlert created: [%s] %s", alert_level, job_name)
    except Exception as e:
        db.rollback()
        logger.error("Failed to create OpsAlert for %s: %s", job_name, e)


async def scheduled_incremental_load():
    """16:30 KST — 일별 시세 증분 적재 (pykrx → stock_price_daily)"""
    task_name = "incremental_prices"

    with _task_lock:
        if task_name in _running_tasks:
            logger.warning("[%s] 이미 실행 중 — 스킵", task_name)
            return
        _running_tasks.add(task_name)

    db = SessionLocal()
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

        logger.info(
            "[%s] 완료 — success=%d, failed=%d, skipped=%d",
            task_name, success, failed, skipped,
        )

        if failed > 0:
            _create_collection_alert(
                db,
                job_name="일별 시세 증분 적재",
                alert_level="WARN",
                error_message=f"증분 적재 부분 실패: success={success}, failed={failed}, skipped={skipped}",
                detail={"success": success, "failed": failed, "skipped": skipped, "date": str(date.today())},
            )

    except Exception as e:
        logger.error("[%s] 실패: %s", task_name, e, exc_info=True)
        _create_collection_alert(
            db,
            job_name="일별 시세 증분 적재",
            alert_level="CRITICAL",
            error_message=str(e),
            detail={"date": str(date.today()), "error": str(e)[:500]},
        )
    finally:
        db.close()
        with _task_lock:
            _running_tasks.discard(task_name)


async def scheduled_compass_batch_compute():
    """17:00 KST — Compass Score 일괄 계산 (stocks 테이블 compass_* 갱신)"""
    task_name = "compass_batch"

    with _task_lock:
        if task_name in _running_tasks:
            logger.warning("[%s] 이미 실행 중 — 스킵", task_name)
            return
        _running_tasks.add(task_name)

    db = SessionLocal()
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

        # 실패율 > 30% 시 알림
        if total > 0 and (fail_count / total) > 0.3:
            _create_collection_alert(
                db,
                job_name="Compass Score 일괄 계산",
                alert_level="WARN",
                error_message=f"실패율 {fail_count}/{total} ({fail_count/total*100:.1f}%) — 30% 초과",
                detail={"success": success_count, "failed": fail_count, "total": total, "date": str(date.today())},
            )

    except Exception as e:
        logger.error("[%s] 실패: %s", task_name, e, exc_info=True)
        _create_collection_alert(
            db,
            job_name="Compass Score 일괄 계산",
            alert_level="CRITICAL",
            error_message=str(e),
            detail={"date": str(date.today()), "error": str(e)[:500]},
        )
    finally:
        db.close()
        with _task_lock:
            _running_tasks.discard(task_name)


# ── Phase 2: 주간/월간 수집 자동화 ──


async def scheduled_weekly_stock_refresh():
    """토요일 10:00 KST — 종목 마스터 + 주식 정보 + ETF 순차 갱신"""
    task_name = "weekly_stock_refresh"

    with _task_lock:
        if task_name in _running_tasks:
            logger.warning("[%s] 이미 실행 중 — 스킵", task_name)
            return
        _running_tasks.add(task_name)

    db = SessionLocal()
    try:
        from app.services.real_data_loader import RealDataLoader
        from app.services.data_loader import DataLoaderService

        loader = RealDataLoader(db)

        # Step 1: FDR 종목 마스터 (~20초)
        logger.info("[%s] Step 1/3: FDR 종목 마스터", task_name)
        result1 = loader.load_fdr_stock_listing(
            market="KRX",
            as_of_date=date.today(),
            operator_id="scheduler",
            operator_reason="주간 자동 갱신",
        )
        logger.info("[%s] Step 1 완료: %d건", task_name, result1.total_records)

        # Step 2: 주식 기본 정보 (~3-5분)
        logger.info("[%s] Step 2/3: 주식 기본 정보", task_name)
        result2 = loader.load_stocks_from_fdr(
            as_of_date=date.today(),
            operator_id="scheduler",
            operator_reason="주간 자동 갱신",
        )
        logger.info("[%s] Step 2 완료: success=%d, failed=%d",
                     task_name, result2.success_records, result2.failed_records)

        # Step 3: ETF (~5-10분)
        logger.info("[%s] Step 3/3: ETF", task_name)
        result3 = DataLoaderService.load_etfs(db)
        logger.info("[%s] Step 3 완료: %s", task_name, result3)

        logger.info("[%s] 전체 완료", task_name)

    except Exception as e:
        logger.error("[%s] 실패: %s", task_name, e, exc_info=True)
        _create_collection_alert(
            db, "주간 종목 갱신", "CRITICAL", str(e),
            {"date": str(date.today()), "error": str(e)[:500]},
        )
    finally:
        db.close()
        with _task_lock:
            _running_tasks.discard(task_name)


async def scheduled_dart_financials():
    """토요일 11:00 KST — DART 재무제표 적재"""
    task_name = "dart_financials"

    with _task_lock:
        if task_name in _running_tasks:
            logger.warning("[%s] 이미 실행 중 — 스킵", task_name)
            return
        _running_tasks.add(task_name)

    db = SessionLocal()
    try:
        from app.services.real_data_loader import RealDataLoader

        loader = RealDataLoader(db)

        # fiscal_year: 4월 이후면 전년도, 그 전이면 전전년도
        # (연간 보고서는 보통 3월 말에 공시)
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

        # 실패율 > 50% 시 알림 (DART는 데이터 없는 종목이 많으므로 임계치 높게)
        if result.total_records > 0 and (result.failed_records / result.total_records) > 0.5:
            _create_collection_alert(
                db, "DART 재무제표", "WARN",
                f"실패율 {result.failed_records}/{result.total_records}",
                {"fiscal_year": fiscal_year, "success": result.success_records,
                 "failed": result.failed_records},
            )

    except Exception as e:
        logger.error("[%s] 실패: %s", task_name, e, exc_info=True)
        _create_collection_alert(
            db, "DART 재무제표", "CRITICAL", str(e),
            {"date": str(date.today()), "error": str(e)[:500]},
        )
    finally:
        db.close()
        with _task_lock:
            _running_tasks.discard(task_name)


async def scheduled_monthly_financial_products():
    """매월 1일 13:00 KST — 채권 + 금융상품 6종 순차 적재"""
    task_name = "monthly_products"

    with _task_lock:
        if task_name in _running_tasks:
            logger.warning("[%s] 이미 실행 중 — 스킵", task_name)
            return
        _running_tasks.add(task_name)

    db = SessionLocal()
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

        for i, (name, load_fn) in enumerate(steps, 1):
            try:
                logger.info("[%s] Step %d/7: %s", task_name, i, name)
                result = load_fn()
                results[name] = {"success": result.success_records, "failed": result.failed_records}
                logger.info("[%s] %s 완료: success=%d, failed=%d",
                            task_name, name, result.success_records, result.failed_records)
            except Exception as e:
                results[name] = {"error": str(e)[:200]}
                logger.error("[%s] %s 실패: %s", task_name, name, e)

        failed_steps = [k for k, v in results.items() if "error" in v]
        if failed_steps:
            _create_collection_alert(
                db, "월간 금융상품", "WARN",
                f"실패 항목: {', '.join(failed_steps)}",
                {"results": results, "date": str(date.today())},
            )

        logger.info("[%s] 전체 완료 — 실패: %d/7", task_name, len(failed_steps))

    except Exception as e:
        logger.error("[%s] 실패: %s", task_name, e, exc_info=True)
        _create_collection_alert(
            db, "월간 금융상품", "CRITICAL", str(e),
            {"date": str(date.today()), "error": str(e)[:500]},
        )
    finally:
        db.close()
        with _task_lock:
            _running_tasks.discard(task_name)
