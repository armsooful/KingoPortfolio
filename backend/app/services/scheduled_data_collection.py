"""
데이터 수집 자동 스케줄 서비스 — Phase 1

매 영업일 자동 실행:
- 16:30 KST: 일별 시세 증분 적재 (pykrx)
- 17:00 KST: Compass Score 일괄 계산
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
