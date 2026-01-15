#!/usr/bin/env python3
"""
P1-B3: 일간수익률 생성 배치

daily_price 테이블에서 일간수익률을 계산하여 daily_return 테이블에 적재
PostgreSQL 환경에서 실행

Usage:
    # 모든 종목 수익률 생성
    python scripts/generate_daily_returns.py --all

    # 특정 종목만
    python scripts/generate_daily_returns.py --ticker 069500

    # 특정 기간만
    python scripts/generate_daily_returns.py --all --start-date 2025-01-01 --end-date 2025-12-31
"""

import argparse
import sys
import os
import math
from datetime import datetime, date
from decimal import Decimal

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


# ============================================================================
# 설정
# ============================================================================

ENGINE_VERSION = os.getenv("ENGINE_VERSION", "1.0.0")


# ============================================================================
# 유틸리티
# ============================================================================

def get_database_url():
    """데이터베이스 URL 반환 (PostgreSQL 우선)"""
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url or "sqlite" in db_url:
        print("⚠️  PostgreSQL DATABASE_URL이 설정되지 않았습니다.")
        print("   예: export DATABASE_URL=postgresql://user:pass@localhost:5432/foresto_dev")
        sys.exit(1)
    return db_url


def create_session():
    """SQLAlchemy 세션 생성"""
    db_url = get_database_url()
    engine = create_engine(db_url, echo=False)
    Session = sessionmaker(bind=engine)
    return Session(), engine


def get_active_instruments(session) -> list:
    """활성 금융상품 목록 조회"""
    sql = text("""
        SELECT instrument_id, ticker, name_ko
        FROM instrument_master
        WHERE is_active = TRUE
        ORDER BY ticker
    """)
    result = session.execute(sql).fetchall()
    return [{"id": r[0], "ticker": r[1], "name": r[2]} for r in result]


def get_instrument_by_ticker(session, ticker: str) -> dict | None:
    """티커로 금융상품 조회"""
    sql = text("""
        SELECT instrument_id, ticker, name_ko
        FROM instrument_master
        WHERE ticker = :ticker AND is_active = TRUE
    """)
    result = session.execute(sql, {"ticker": ticker}).fetchone()
    if result:
        return {"id": result[0], "ticker": result[1], "name": result[2]}
    return None


# ============================================================================
# 수익률 계산
# ============================================================================

def calculate_returns_for_instrument(
    session,
    instrument_id: int,
    start_date: date | None = None,
    end_date: date | None = None
) -> tuple:
    """
    특정 종목의 일간수익률 계산 및 적재

    Args:
        session: DB 세션
        instrument_id: 금융상품 ID
        start_date: 시작일 (None이면 전체)
        end_date: 종료일 (None이면 전체)

    Returns:
        (generated_count, skipped_count, error_count)
    """
    # 가격 데이터 조회
    price_sql = text("""
        SELECT trade_date, close_price, adj_close_price
        FROM daily_price
        WHERE instrument_id = :instrument_id
        AND (:start_date IS NULL OR trade_date >= :start_date)
        AND (:end_date IS NULL OR trade_date <= :end_date)
        ORDER BY trade_date
    """)

    prices = session.execute(price_sql, {
        "instrument_id": instrument_id,
        "start_date": start_date,
        "end_date": end_date
    }).fetchall()

    if len(prices) < 2:
        return 0, 0, 0

    generated = 0
    skipped = 0
    errors = 0

    prev_price = None
    prev_date = None

    for row in prices:
        trade_date = row[0]
        close_price = float(row[1]) if row[1] else None
        adj_close = float(row[2]) if row[2] else close_price

        # 사용할 가격 (조정 종가 우선)
        price = adj_close if adj_close else close_price

        if price is None:
            errors += 1
            continue

        if prev_price is None:
            # 첫 데이터 - 수익률 0
            daily_return = 0.0
            log_return = 0.0
            data_quality = "OK"
        else:
            if prev_price > 0:
                daily_return = (price - prev_price) / prev_price
                log_return = math.log(price / prev_price) if price > 0 else None
                data_quality = "OK"
            else:
                daily_return = None
                log_return = None
                data_quality = "MISSING"

        # 기존 데이터 확인
        check_sql = text("""
            SELECT 1 FROM daily_return
            WHERE instrument_id = :instrument_id AND trade_date = :trade_date
        """)
        exists = session.execute(check_sql, {
            "instrument_id": instrument_id,
            "trade_date": trade_date
        }).fetchone()

        if exists:
            # UPDATE
            update_sql = text("""
                UPDATE daily_return
                SET daily_return = :daily_return,
                    log_return = :log_return,
                    data_quality = :data_quality,
                    engine_version = :engine_version
                WHERE instrument_id = :instrument_id AND trade_date = :trade_date
            """)
            session.execute(update_sql, {
                "instrument_id": instrument_id,
                "trade_date": trade_date,
                "daily_return": daily_return,
                "log_return": log_return,
                "data_quality": data_quality,
                "engine_version": ENGINE_VERSION
            })
            skipped += 1
        else:
            # INSERT
            insert_sql = text("""
                INSERT INTO daily_return
                (instrument_id, trade_date, daily_return, log_return, data_quality, engine_version)
                VALUES (:instrument_id, :trade_date, :daily_return, :log_return, :data_quality, :engine_version)
            """)
            try:
                session.execute(insert_sql, {
                    "instrument_id": instrument_id,
                    "trade_date": trade_date,
                    "daily_return": daily_return,
                    "log_return": log_return,
                    "data_quality": data_quality,
                    "engine_version": ENGINE_VERSION
                })
                generated += 1
            except Exception as e:
                print(f"    ❌ INSERT 실패 ({trade_date}): {e}")
                errors += 1

        prev_price = price
        prev_date = trade_date

    session.commit()
    return generated, skipped, errors


def generate_returns_sql_batch(session, start_date: date | None = None, end_date: date | None = None) -> int:
    """
    SQL 배치로 전체 수익률 생성 (대량 데이터용)

    Returns:
        생성된 레코드 수
    """
    sql = text("""
        INSERT INTO daily_return (instrument_id, trade_date, daily_return, log_return, data_quality, engine_version)
        SELECT
            dp.instrument_id,
            dp.trade_date,
            CASE
                WHEN LAG(dp.close_price) OVER (PARTITION BY dp.instrument_id ORDER BY dp.trade_date) > 0
                THEN (dp.close_price - LAG(dp.close_price) OVER (PARTITION BY dp.instrument_id ORDER BY dp.trade_date))
                     / LAG(dp.close_price) OVER (PARTITION BY dp.instrument_id ORDER BY dp.trade_date)
                ELSE 0
            END AS daily_return,
            CASE
                WHEN LAG(dp.close_price) OVER (PARTITION BY dp.instrument_id ORDER BY dp.trade_date) > 0
                     AND dp.close_price > 0
                THEN LN(dp.close_price / LAG(dp.close_price) OVER (PARTITION BY dp.instrument_id ORDER BY dp.trade_date))
                ELSE NULL
            END AS log_return,
            'OK' AS data_quality,
            :engine_version AS engine_version
        FROM daily_price dp
        WHERE (:start_date IS NULL OR dp.trade_date >= :start_date)
          AND (:end_date IS NULL OR dp.trade_date <= :end_date)
          AND NOT EXISTS (
              SELECT 1 FROM daily_return dr
              WHERE dr.instrument_id = dp.instrument_id
                AND dr.trade_date = dp.trade_date
          )
        ORDER BY dp.instrument_id, dp.trade_date
    """)

    result = session.execute(sql, {
        "start_date": start_date,
        "end_date": end_date,
        "engine_version": ENGINE_VERSION
    })
    session.commit()

    return result.rowcount


# ============================================================================
# 메인
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="일간수익률 생성 배치 (P1-B3)")
    parser.add_argument("--ticker", help="특정 종목만 처리")
    parser.add_argument("--all", action="store_true", help="모든 활성 종목 처리")
    parser.add_argument("--start-date", help="시작일 (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="종료일 (YYYY-MM-DD)")
    parser.add_argument("--batch-sql", action="store_true", help="SQL 배치 모드 (대량 데이터)")
    parser.add_argument("--dry-run", action="store_true", help="실제 적재 없이 대상만 출력")
    args = parser.parse_args()

    if not args.ticker and not args.all:
        parser.print_help()
        print("\n❌ --ticker 또는 --all 옵션이 필요합니다.")
        sys.exit(1)

    print("=" * 60)
    print("Foresto Phase 1 - 일간수익률 생성 (P1-B3)")
    print("=" * 60)
    print(f"📌 Engine Version: {ENGINE_VERSION}")

    # 날짜 파싱
    start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date() if args.start_date else None
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date() if args.end_date else None

    if start_date:
        print(f"📅 시작일: {start_date}")
    if end_date:
        print(f"📅 종료일: {end_date}")

    if args.dry_run:
        print("\n⚠️  DRY RUN 모드 - 실제 적재하지 않음")
        return

    # DB 연결
    session, engine = create_session()
    print(f"\n📦 Database: {str(engine.url)[:40]}...")

    # SQL 배치 모드
    if args.batch_sql:
        print("\n🚀 SQL 배치 모드로 실행...")
        count = generate_returns_sql_batch(session, start_date, end_date)
        print(f"✅ {count}건 생성 완료")
        session.close()
        return

    # 대상 종목
    if args.ticker:
        instrument = get_instrument_by_ticker(session, args.ticker)
        if not instrument:
            print(f"❌ {args.ticker}: instrument_master에 없음")
            sys.exit(1)
        instruments = [instrument]
    else:
        instruments = get_active_instruments(session)

    print(f"\n📊 대상 종목: {len(instruments)}개")

    # 종목별 처리
    total_generated = 0
    total_skipped = 0
    total_errors = 0

    for inst in instruments:
        print(f"\n[{inst['ticker']}] {inst['name']} 처리 중...")
        generated, skipped, errors = calculate_returns_for_instrument(
            session, inst["id"], start_date, end_date
        )
        total_generated += generated
        total_skipped += skipped
        total_errors += errors
        print(f"  ✅ 신규: {generated}, 🔄 갱신: {skipped}, ❌ 오류: {errors}")

    print("\n" + "=" * 60)
    print(f"✅ 완료: 신규 {total_generated}건, 갱신 {total_skipped}건, 오류 {total_errors}건")
    print("=" * 60)

    session.close()


if __name__ == "__main__":
    main()
