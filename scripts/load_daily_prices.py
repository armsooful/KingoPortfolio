#!/usr/bin/env python3
"""
P1-B2: 일봉가격 적재 스크립트

pykrx를 이용하여 KRX ETF 일봉 데이터를 daily_price 테이블에 적재
PostgreSQL 환경에서 실행

Usage:
    # 특정 종목 1년치 적재
    python scripts/load_daily_prices.py --ticker 069500 --days 365

    # 모든 seed 종목 적재
    python scripts/load_daily_prices.py --all --days 365

    # 최근 데이터만 업데이트
    python scripts/load_daily_prices.py --all --days 7
"""

import argparse
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from pykrx import stock
except ImportError:
    print("❌ pykrx 패키지가 필요합니다: pip install pykrx")
    sys.exit(1)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import pandas as pd


# ============================================================================
# 설정
# ============================================================================

# KRX ETF 목록 (seed_instruments.py와 동기화)
KRX_TICKERS = [
    "069500",  # KODEX 200
    "114800",  # KODEX 인버스
    "122630",  # KODEX 레버리지
    "148020",  # KBSTAR 200
    "152100",  # ARIRANG 200
    "379800",  # KODEX 미국S&P500TR
    "360750",  # TIGER 미국S&P500
    "133690",  # TIGER 미국나스닥100
    "132030",  # KODEX 골드선물(H)
    "148070",  # KOSEF 국고채10년
]


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


def get_instrument_id(session, ticker: str, exchange: str = "KRX") -> int | None:
    """instrument_master에서 instrument_id 조회"""
    sql = text("""
        SELECT instrument_id FROM instrument_master
        WHERE ticker = :ticker AND exchange = :exchange AND is_active = TRUE
    """)
    result = session.execute(sql, {"ticker": ticker, "exchange": exchange}).fetchone()
    return result[0] if result else None


def record_load_history(session, source_type: str, source_name: str,
                        records_loaded: int, records_failed: int = 0,
                        loaded_by: str = "batch") -> int:
    """적재 이력 기록"""
    status = "SUCCESS" if records_failed == 0 else "PARTIAL"
    sql = text("""
        INSERT INTO source_load_history
        (source_type, source_name, load_status, records_loaded, records_failed, loaded_by, completed_at)
        VALUES (:source_type, :source_name, :status, :records_loaded, :records_failed, :loaded_by, NOW())
        RETURNING load_id
    """)
    result = session.execute(sql, {
        "source_type": source_type,
        "source_name": source_name,
        "status": status,
        "records_loaded": records_loaded,
        "records_failed": records_failed,
        "loaded_by": loaded_by
    })
    session.commit()
    return result.fetchone()[0]


# ============================================================================
# 데이터 수집 및 적재
# ============================================================================

def fetch_ohlcv_from_pykrx(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    pykrx에서 OHLCV 데이터 조회

    Args:
        ticker: 종목코드 (예: 069500)
        start_date: 시작일 (YYYYMMDD)
        end_date: 종료일 (YYYYMMDD)

    Returns:
        DataFrame with columns: 시가, 고가, 저가, 종가, 거래량
    """
    try:
        df = stock.get_market_ohlcv_by_date(start_date, end_date, ticker)
        if df.empty:
            print(f"  ⚠️  {ticker}: 데이터 없음 ({start_date} ~ {end_date})")
            return pd.DataFrame()

        # 컬럼명 통일
        df = df.reset_index()
        df.columns = ["trade_date", "open_price", "high_price", "low_price", "close_price", "volume"]
        return df

    except Exception as e:
        print(f"  ❌ {ticker}: pykrx 조회 실패 - {e}")
        return pd.DataFrame()


def upsert_daily_price(session, instrument_id: int, row: dict, load_id: int) -> bool:
    """
    일봉 데이터 upsert

    Returns:
        True if success, False if error
    """
    try:
        # 기존 데이터 확인
        check_sql = text("""
            SELECT 1 FROM daily_price
            WHERE instrument_id = :instrument_id AND trade_date = :trade_date
        """)
        exists = session.execute(check_sql, {
            "instrument_id": instrument_id,
            "trade_date": row["trade_date"]
        }).fetchone()

        if exists:
            # UPDATE
            update_sql = text("""
                UPDATE daily_price
                SET open_price = :open_price,
                    high_price = :high_price,
                    low_price = :low_price,
                    close_price = :close_price,
                    volume = :volume,
                    load_id = :load_id
                WHERE instrument_id = :instrument_id AND trade_date = :trade_date
            """)
            session.execute(update_sql, {
                "instrument_id": instrument_id,
                "trade_date": row["trade_date"],
                "open_price": row["open_price"],
                "high_price": row["high_price"],
                "low_price": row["low_price"],
                "close_price": row["close_price"],
                "volume": row["volume"],
                "load_id": load_id
            })
        else:
            # INSERT
            insert_sql = text("""
                INSERT INTO daily_price
                (instrument_id, trade_date, open_price, high_price, low_price, close_price, volume, load_id)
                VALUES (:instrument_id, :trade_date, :open_price, :high_price, :low_price, :close_price, :volume, :load_id)
            """)
            session.execute(insert_sql, {
                "instrument_id": instrument_id,
                "trade_date": row["trade_date"],
                "open_price": row["open_price"],
                "high_price": row["high_price"],
                "low_price": row["low_price"],
                "close_price": row["close_price"],
                "volume": row["volume"],
                "load_id": load_id
            })

        return True

    except Exception as e:
        print(f"    ❌ upsert 실패 ({row['trade_date']}): {e}")
        return False


def load_ticker_prices(session, ticker: str, days: int, load_id: int) -> tuple:
    """
    특정 종목의 일봉 데이터 적재

    Returns:
        (loaded_count, failed_count)
    """
    # instrument_id 조회
    instrument_id = get_instrument_id(session, ticker)
    if not instrument_id:
        print(f"  ⚠️  {ticker}: instrument_master에 없음 (seed_instruments.py 먼저 실행)")
        return 0, 0

    # 날짜 범위
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

    # pykrx에서 데이터 조회
    df = fetch_ohlcv_from_pykrx(ticker, start_date, end_date)
    if df.empty:
        return 0, 0

    # 적재
    loaded = 0
    failed = 0

    for _, row in df.iterrows():
        row_dict = {
            "trade_date": row["trade_date"].date() if hasattr(row["trade_date"], "date") else row["trade_date"],
            "open_price": float(row["open_price"]) if row["open_price"] else None,
            "high_price": float(row["high_price"]) if row["high_price"] else None,
            "low_price": float(row["low_price"]) if row["low_price"] else None,
            "close_price": float(row["close_price"]) if row["close_price"] else None,
            "volume": int(row["volume"]) if row["volume"] else None,
        }

        if upsert_daily_price(session, instrument_id, row_dict, load_id):
            loaded += 1
        else:
            failed += 1

    session.commit()
    return loaded, failed


# ============================================================================
# 메인
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="일봉가격 적재 스크립트 (P1-B2)")
    parser.add_argument("--ticker", help="적재할 종목코드 (예: 069500)")
    parser.add_argument("--all", action="store_true", help="모든 KRX ETF 적재")
    parser.add_argument("--days", type=int, default=365, help="적재할 기간 (일, 기본: 365)")
    parser.add_argument("--dry-run", action="store_true", help="실제 적재 없이 대상만 출력")
    args = parser.parse_args()

    if not args.ticker and not args.all:
        parser.print_help()
        print("\n❌ --ticker 또는 --all 옵션이 필요합니다.")
        sys.exit(1)

    print("=" * 60)
    print("Foresto Phase 1 - 일봉가격 적재 (P1-B2)")
    print("=" * 60)

    # 대상 종목
    tickers = KRX_TICKERS if args.all else [args.ticker]
    print(f"\n📊 대상 종목: {len(tickers)}개")
    print(f"📅 기간: 최근 {args.days}일")

    if args.dry_run:
        print("\n⚠️  DRY RUN 모드 - 실제 적재하지 않음")
        for t in tickers:
            print(f"  - {t}")
        return

    # DB 연결
    session, engine = create_session()
    print(f"\n📦 Database: {str(engine.url)[:40]}...")

    # 적재 이력 생성
    load_id = record_load_history(
        session,
        source_type="pykrx",
        source_name=f"load_daily_prices_{datetime.now().strftime('%Y%m%d')}",
        records_loaded=0,
        loaded_by="batch"
    )
    print(f"📝 Load ID: {load_id}")

    # 종목별 적재
    total_loaded = 0
    total_failed = 0

    for ticker in tickers:
        print(f"\n[{ticker}] 적재 중...")
        loaded, failed = load_ticker_prices(session, ticker, args.days, load_id)
        total_loaded += loaded
        total_failed += failed
        print(f"  ✅ {loaded}건 적재, ❌ {failed}건 실패")

    # 적재 이력 업데이트
    update_sql = text("""
        UPDATE source_load_history
        SET records_loaded = :loaded, records_failed = :failed,
            load_status = CASE WHEN :failed = 0 THEN 'SUCCESS' ELSE 'PARTIAL' END,
            completed_at = NOW()
        WHERE load_id = :load_id
    """)
    session.execute(update_sql, {
        "loaded": total_loaded,
        "failed": total_failed,
        "load_id": load_id
    })
    session.commit()

    print("\n" + "=" * 60)
    print(f"✅ 완료: {total_loaded}건 적재, {total_failed}건 실패")
    print("=" * 60)

    session.close()


if __name__ == "__main__":
    main()
