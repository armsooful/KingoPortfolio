"""
초기 데이터 소스 시드 스크립트

사용법:
    python -m scripts.seed_data_sources
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.config import settings
from app.models.real_data import DataSource, Base

if not settings.database_url.startswith("postgresql"):
    # 테이블 생성 (없는 경우)
    Base.metadata.create_all(bind=engine)


def seed_data_sources(db: Session):
    """데이터 소스 마스터 초기 데이터 적재"""

    data_sources = [
        {
            "source_id": "KRX",
            "source_name": "한국거래소",
            "source_type": "EXCHANGE",
            "base_url": "http://data.krx.co.kr",
            "api_type": "REST",
            "update_frequency": "DAILY",
            "license_type": "PUBLIC",
            "description": "한국거래소 공식 데이터. KOSPI, KOSDAQ, KONEX 상장 종목 시세 및 지수 데이터 제공.",
            "is_active": True
        },
        {
            "source_id": "PYKRX",
            "source_name": "pykrx 라이브러리",
            "source_type": "VENDOR",
            "base_url": "https://github.com/sharebook-kr/pykrx",
            "api_type": "SCRAPING",
            "update_frequency": "DAILY",
            "license_type": "PUBLIC",
            "description": "KRX 데이터를 Python에서 쉽게 사용할 수 있도록 래핑한 오픈소스 라이브러리.",
            "is_active": True
        },
        {
            "source_id": "NAVER",
            "source_name": "네이버 금융",
            "source_type": "VENDOR",
            "base_url": "https://finance.naver.com",
            "api_type": "SCRAPING",
            "update_frequency": "DAILY",
            "license_type": "PUBLIC",
            "description": "네이버 금융 종목 시세 및 기본 정보. 보조 데이터 소스로 활용.",
            "is_active": True
        },
        {
            "source_id": "DART",
            "source_name": "DART OpenAPI",
            "source_type": "REGULATOR",
            "base_url": "https://opendart.fss.or.kr",
            "api_type": "REST",
            "update_frequency": "DAILY",
            "license_type": "PUBLIC",
            "description": "금융감독원 DART 전자공시시스템. 재무제표, 배당 정보, 공시 정보 등 Level 2 데이터 제공.",
            "is_active": True
        },
        {
            "source_id": "KRX_INFO",
            "source_name": "KRX 정보데이터시스템",
            "source_type": "EXCHANGE",
            "base_url": "http://data.krx.co.kr",
            "api_type": "REST",
            "update_frequency": "DAILY",
            "license_type": "PUBLIC",
            "description": "한국거래소 정보데이터시스템. 업종분류, 기관/외국인 매매, ETF 포트폴리오 등 Level 2 데이터 제공.",
            "is_active": True
        },
        {
            "source_id": "INTERNAL",
            "source_name": "내부 계산",
            "source_type": "CALCULATED",
            "base_url": None,
            "api_type": None,
            "update_frequency": "ON_DEMAND",
            "license_type": "INTERNAL",
            "description": "시스템 내부에서 계산된 파생 데이터 (수정 주가, 수익률 등).",
            "is_active": True
        },
        {
            "source_id": "FSC_BOND_INFO",
            "source_name": "금융위원회_채권기본정보(OpenAPI)",
            "source_type": "GOV",
            "base_url": "http://apis.data.go.kr/1160100/service/GetBondIssuInfoService/getBondBasiInfo",
            "api_type": "REST",
            "update_frequency": "DAILY",
            "license_type": "PUBLIC",
            "description": "금융위원회 채권기본정보 OpenAPI",
            "is_active": True
        },
        {
            "source_id": "MIGRATION",
            "source_name": "기존 데이터 마이그레이션",
            "source_type": "CALCULATED",
            "base_url": None,
            "api_type": None,
            "update_frequency": "MANUAL",
            "license_type": "INTERNAL",
            "description": "기존 krx_time_series, alpha_vantage_daily에서 마이그레이션된 데이터.",
            "is_active": True
        }
    ]

    inserted = 0
    skipped = 0

    for source_data in data_sources:
        existing = db.query(DataSource).filter(
            DataSource.source_id == source_data["source_id"]
        ).first()

        if existing:
            print(f"[SKIP] {source_data['source_id']} already exists")
            skipped += 1
        else:
            source = DataSource(**source_data)
            db.add(source)
            print(f"[INSERT] {source_data['source_id']}: {source_data['source_name']}")
            inserted += 1

    db.commit()
    print(f"\nCompleted: {inserted} inserted, {skipped} skipped")


def main():
    print("=" * 60)
    print("Data Source Seed Script")
    print("=" * 60)

    db = SessionLocal()
    try:
        seed_data_sources(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
