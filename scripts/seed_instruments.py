#!/usr/bin/env python3
"""
P1-B1: 금융상품 기준정보 Seed 스크립트

운영 가능한 최소 유니버스(ETF/지수/환율)를 instrument_master 테이블에 적재
PostgreSQL 환경에서 실행

Usage:
    # 전체 seed
    python scripts/seed_instruments.py

    # 특정 유형만 seed
    python scripts/seed_instruments.py --type etf
    python scripts/seed_instruments.py --type index
    python scripts/seed_instruments.py --type fx
"""

import argparse
import sys
import os
from datetime import datetime
from decimal import Decimal

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


# ============================================================================
# 최소 유니버스 정의
# ============================================================================

# 한국 대표 ETF
KRX_ETFS = [
    {
        "instrument_type": "ETF",
        "ticker": "069500",
        "exchange": "KRX",
        "name_ko": "KODEX 200",
        "name_en": "KODEX 200 ETF",
        "currency": "KRW",
        "sector": "시장지수",
        "data_source": "KRX",
    },
    {
        "instrument_type": "ETF",
        "ticker": "114800",
        "exchange": "KRX",
        "name_ko": "KODEX 인버스",
        "name_en": "KODEX Inverse ETF",
        "currency": "KRW",
        "sector": "시장지수",
        "data_source": "KRX",
    },
    {
        "instrument_type": "ETF",
        "ticker": "122630",
        "exchange": "KRX",
        "name_ko": "KODEX 레버리지",
        "name_en": "KODEX Leverage ETF",
        "currency": "KRW",
        "sector": "시장지수",
        "data_source": "KRX",
    },
    {
        "instrument_type": "ETF",
        "ticker": "148020",
        "exchange": "KRX",
        "name_ko": "KBSTAR 200",
        "name_en": "KBSTAR 200 ETF",
        "currency": "KRW",
        "sector": "시장지수",
        "data_source": "KRX",
    },
    {
        "instrument_type": "ETF",
        "ticker": "152100",
        "exchange": "KRX",
        "name_ko": "ARIRANG 200",
        "name_en": "ARIRANG 200 ETF",
        "currency": "KRW",
        "sector": "시장지수",
        "data_source": "KRX",
    },
    {
        "instrument_type": "ETF",
        "ticker": "379800",
        "exchange": "KRX",
        "name_ko": "KODEX 미국S&P500TR",
        "name_en": "KODEX S&P 500 TR ETF",
        "currency": "KRW",
        "sector": "해외지수",
        "data_source": "KRX",
    },
    {
        "instrument_type": "ETF",
        "ticker": "360750",
        "exchange": "KRX",
        "name_ko": "TIGER 미국S&P500",
        "name_en": "TIGER S&P 500 ETF",
        "currency": "KRW",
        "sector": "해외지수",
        "data_source": "KRX",
    },
    {
        "instrument_type": "ETF",
        "ticker": "133690",
        "exchange": "KRX",
        "name_ko": "TIGER 미국나스닥100",
        "name_en": "TIGER NASDAQ 100 ETF",
        "currency": "KRW",
        "sector": "해외지수",
        "data_source": "KRX",
    },
    {
        "instrument_type": "ETF",
        "ticker": "132030",
        "exchange": "KRX",
        "name_ko": "KODEX 골드선물(H)",
        "name_en": "KODEX Gold Futures ETF",
        "currency": "KRW",
        "sector": "원자재",
        "data_source": "KRX",
    },
    {
        "instrument_type": "ETF",
        "ticker": "148070",
        "exchange": "KRX",
        "name_ko": "KOSEF 국고채10년",
        "name_en": "KOSEF KTB 10Y ETF",
        "currency": "KRW",
        "sector": "채권",
        "data_source": "KRX",
    },
]

# 미국 대표 ETF
US_ETFS = [
    {
        "instrument_type": "ETF",
        "ticker": "SPY",
        "exchange": "NYSE",
        "name_ko": "SPDR S&P 500 ETF",
        "name_en": "SPDR S&P 500 ETF Trust",
        "currency": "USD",
        "sector": "시장지수",
        "data_source": "AlphaVantage",
    },
    {
        "instrument_type": "ETF",
        "ticker": "QQQ",
        "exchange": "NASDAQ",
        "name_ko": "Invesco QQQ Trust",
        "name_en": "Invesco QQQ Trust",
        "currency": "USD",
        "sector": "기술",
        "data_source": "AlphaVantage",
    },
    {
        "instrument_type": "ETF",
        "ticker": "IWM",
        "exchange": "NYSE",
        "name_ko": "iShares Russell 2000 ETF",
        "name_en": "iShares Russell 2000 ETF",
        "currency": "USD",
        "sector": "시장지수",
        "data_source": "AlphaVantage",
    },
    {
        "instrument_type": "ETF",
        "ticker": "VTI",
        "exchange": "NYSE",
        "name_ko": "Vanguard Total Stock Market ETF",
        "name_en": "Vanguard Total Stock Market ETF",
        "currency": "USD",
        "sector": "시장지수",
        "data_source": "AlphaVantage",
    },
    {
        "instrument_type": "ETF",
        "ticker": "TLT",
        "exchange": "NASDAQ",
        "name_ko": "iShares 20+ Year Treasury Bond ETF",
        "name_en": "iShares 20+ Year Treasury Bond ETF",
        "currency": "USD",
        "sector": "채권",
        "data_source": "AlphaVantage",
    },
    {
        "instrument_type": "ETF",
        "ticker": "GLD",
        "exchange": "NYSE",
        "name_ko": "SPDR Gold Shares",
        "name_en": "SPDR Gold Shares",
        "currency": "USD",
        "sector": "원자재",
        "data_source": "AlphaVantage",
    },
    {
        "instrument_type": "ETF",
        "ticker": "VNQ",
        "exchange": "NYSE",
        "name_ko": "Vanguard Real Estate ETF",
        "name_en": "Vanguard Real Estate ETF",
        "currency": "USD",
        "sector": "리츠",
        "data_source": "AlphaVantage",
    },
    {
        "instrument_type": "ETF",
        "ticker": "EEM",
        "exchange": "NYSE",
        "name_ko": "iShares MSCI Emerging Markets ETF",
        "name_en": "iShares MSCI Emerging Markets ETF",
        "currency": "USD",
        "sector": "신흥시장",
        "data_source": "AlphaVantage",
    },
]

# 주요 지수
INDICES = [
    {
        "instrument_type": "INDEX",
        "ticker": "KOSPI",
        "exchange": "KRX",
        "name_ko": "코스피",
        "name_en": "KOSPI Index",
        "currency": "KRW",
        "sector": "시장지수",
        "data_source": "KRX",
    },
    {
        "instrument_type": "INDEX",
        "ticker": "KOSDAQ",
        "exchange": "KRX",
        "name_ko": "코스닥",
        "name_en": "KOSDAQ Index",
        "currency": "KRW",
        "sector": "시장지수",
        "data_source": "KRX",
    },
    {
        "instrument_type": "INDEX",
        "ticker": "SPX",
        "exchange": "INTERNAL",
        "name_ko": "S&P 500",
        "name_en": "S&P 500 Index",
        "currency": "USD",
        "sector": "시장지수",
        "data_source": "AlphaVantage",
    },
    {
        "instrument_type": "INDEX",
        "ticker": "NDX",
        "exchange": "INTERNAL",
        "name_ko": "나스닥 100",
        "name_en": "NASDAQ 100 Index",
        "currency": "USD",
        "sector": "기술",
        "data_source": "AlphaVantage",
    },
]

# 환율
FX_RATES = [
    {
        "instrument_type": "FX",
        "ticker": "USDKRW",
        "exchange": "INTERNAL",
        "name_ko": "달러/원 환율",
        "name_en": "USD/KRW Exchange Rate",
        "currency": "KRW",
        "sector": "환율",
        "data_source": "BOK",
    },
    {
        "instrument_type": "FX",
        "ticker": "EURKRW",
        "exchange": "INTERNAL",
        "name_ko": "유로/원 환율",
        "name_en": "EUR/KRW Exchange Rate",
        "currency": "KRW",
        "sector": "환율",
        "data_source": "BOK",
    },
    {
        "instrument_type": "FX",
        "ticker": "JPYKRW",
        "exchange": "INTERNAL",
        "name_ko": "엔/원 환율",
        "name_en": "JPY/KRW Exchange Rate",
        "currency": "KRW",
        "sector": "환율",
        "data_source": "BOK",
    },
]


# ============================================================================
# Seed 함수
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


def record_load_history(session, source_type: str, source_name: str, records_loaded: int, loaded_by: str = "seed"):
    """적재 이력 기록"""
    sql = text("""
        INSERT INTO source_load_history (source_type, source_name, load_status, records_loaded, loaded_by, completed_at)
        VALUES (:source_type, :source_name, 'SUCCESS', :records_loaded, :loaded_by, NOW())
        RETURNING load_id
    """)
    result = session.execute(sql, {
        "source_type": source_type,
        "source_name": source_name,
        "records_loaded": records_loaded,
        "loaded_by": loaded_by
    })
    session.commit()
    return result.fetchone()[0]


def upsert_instrument(session, instrument: dict) -> bool:
    """
    금융상품 기준정보 upsert

    Returns:
        True if inserted, False if updated
    """
    # 기존 레코드 확인
    check_sql = text("""
        SELECT instrument_id FROM instrument_master
        WHERE instrument_type = :instrument_type
          AND ticker = :ticker
          AND exchange = :exchange
    """)
    result = session.execute(check_sql, instrument).fetchone()

    if result:
        # UPDATE
        update_sql = text("""
            UPDATE instrument_master
            SET name_ko = :name_ko,
                name_en = :name_en,
                currency = :currency,
                sector = :sector,
                data_source = :data_source,
                updated_at = NOW()
            WHERE instrument_type = :instrument_type
              AND ticker = :ticker
              AND exchange = :exchange
        """)
        session.execute(update_sql, instrument)
        return False
    else:
        # INSERT
        insert_sql = text("""
            INSERT INTO instrument_master
            (instrument_type, ticker, exchange, name_ko, name_en, currency, sector, data_source, is_active)
            VALUES (:instrument_type, :ticker, :exchange, :name_ko, :name_en, :currency, :sector, :data_source, TRUE)
        """)
        session.execute(insert_sql, instrument)
        return True


def seed_instruments(session, instruments: list, category: str) -> tuple:
    """
    금융상품 목록 seed

    Returns:
        (inserted_count, updated_count)
    """
    inserted = 0
    updated = 0

    for inst in instruments:
        try:
            if upsert_instrument(session, inst):
                inserted += 1
                print(f"  ✅ INSERT: {inst['ticker']} ({inst['name_ko']})")
            else:
                updated += 1
                print(f"  🔄 UPDATE: {inst['ticker']} ({inst['name_ko']})")
        except Exception as e:
            print(f"  ❌ ERROR: {inst['ticker']} - {e}")

    session.commit()
    return inserted, updated


def main():
    parser = argparse.ArgumentParser(description="금융상품 기준정보 Seed 스크립트")
    parser.add_argument("--type", choices=["etf", "index", "fx", "all"], default="all",
                        help="적재할 상품 유형 (기본: all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="실제 적재 없이 대상만 출력")
    args = parser.parse_args()

    print("=" * 60)
    print("Foresto Phase 1 - 금융상품 기준정보 Seed")
    print("=" * 60)

    if args.dry_run:
        print("⚠️  DRY RUN 모드 - 실제 적재하지 않음\n")

    # 대상 선정
    targets = []
    if args.type in ("etf", "all"):
        targets.append(("KRX ETF", KRX_ETFS))
        targets.append(("US ETF", US_ETFS))
    if args.type in ("index", "all"):
        targets.append(("INDEX", INDICES))
    if args.type in ("fx", "all"):
        targets.append(("FX", FX_RATES))

    if args.dry_run:
        for category, instruments in targets:
            print(f"\n[{category}] - {len(instruments)}건")
            for inst in instruments:
                print(f"  - {inst['ticker']}: {inst['name_ko']}")
        return

    # DB 연결
    session, engine = create_session()
    print(f"\n📦 Database: {str(engine.url)[:40]}...")

    total_inserted = 0
    total_updated = 0

    for category, instruments in targets:
        print(f"\n[{category}] 적재 중...")
        inserted, updated = seed_instruments(session, instruments, category)
        total_inserted += inserted
        total_updated += updated

        # 적재 이력 기록
        if inserted + updated > 0:
            load_id = record_load_history(
                session,
                source_type="seed",
                source_name=f"seed_instruments_{category.lower().replace(' ', '_')}",
                records_loaded=inserted + updated
            )
            print(f"  📝 Load ID: {load_id}")

    print("\n" + "=" * 60)
    print(f"✅ 완료: INSERT {total_inserted}건, UPDATE {total_updated}건")
    print("=" * 60)

    session.close()


if __name__ == "__main__":
    main()
