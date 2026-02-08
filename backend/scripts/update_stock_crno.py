"""
stocks 테이블에 crno(법인등록번호) 업데이트 스크립트

사용법:
  python -m scripts.update_stock_crno --file data/stock_crno.csv
"""

import argparse
import csv
import sys
from pathlib import Path

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.securities import Stock


def load_mapping(csv_path: Path) -> dict:
    mapping = {}
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = (row.get("ticker") or row.get("code") or "").strip()
            crno = (row.get("crno") or "").strip()
            if ticker and crno:
                mapping[ticker] = crno
    return mapping


def update_crno(db: Session, mapping: dict) -> None:
    updated = 0
    skipped = 0
    for ticker, crno in mapping.items():
        stock = db.query(Stock).filter(Stock.ticker == ticker).first()
        if not stock:
            skipped += 1
            continue
        if stock.crno == crno:
            skipped += 1
            continue
        stock.crno = crno
        updated += 1
    db.commit()
    print(f"updated={updated} skipped={skipped}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Update stocks.crno from CSV")
    parser.add_argument("--file", required=True, help="CSV file with ticker,crno columns")
    args = parser.parse_args(argv)

    csv_path = Path(args.file)
    if not csv_path.exists():
        print(f"file not found: {csv_path}")
        sys.exit(1)

    mapping = load_mapping(csv_path)
    if not mapping:
        print("no rows loaded")
        sys.exit(1)

    db = SessionLocal()
    try:
        update_crno(db, mapping)
    finally:
        db.close()


if __name__ == "__main__":
    main()
