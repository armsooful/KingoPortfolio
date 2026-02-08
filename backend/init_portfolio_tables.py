"""
포트폴리오 테이블 초기화 스크립트
"""

import sys
import os

# 현재 디렉토리를 Python path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base
from app.config import settings
from app.models.portfolio import Portfolio, PortfolioHistory
from app.models.user import User

def init_portfolio_tables():
    """포트폴리오 관련 테이블 생성"""
    print("Creating portfolio tables...")

    if settings.database_url.startswith("postgresql"):
        print("Skipping create_all for PostgreSQL. Use migrations instead.")
        return

    # 테이블 생성 (이미 존재하면 무시)
    Base.metadata.create_all(bind=engine)

    print("Portfolio tables created successfully!")
    print("Tables: portfolios, portfolio_histories")

if __name__ == "__main__":
    init_portfolio_tables()
