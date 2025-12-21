# backend/app/models/securities.py

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from datetime import datetime
from app.database import Base

class Stock(Base):
    """한국 주식"""
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), unique=True, index=True)  # 005930
    name = Column(String(100), index=True)                # 삼성전자
    company = Column(String(100))                         # 회사명 (영문)
    sector = Column(String(50))                           # 전자
    market = Column(String(20))                           # KOSPI, KOSDAQ
    
    # 재무 지표
    current_price = Column(Float)                         # 현재가
    market_cap = Column(Float)                            # 시가총액
    pe_ratio = Column(Float, nullable=True)               # PER
    pb_ratio = Column(Float, nullable=True)               # PBR
    dividend_yield = Column(Float, nullable=True)         # 배당수익률 (%)
    
    # 성과
    ytd_return = Column(Float, nullable=True)             # YTD 수익률 (%)
    one_year_return = Column(Float, nullable=True)        # 1년 수익률 (%)
    
    # 분류
    risk_level = Column(String(20))                       # low, medium, high
    investment_type = Column(String(100))                 # conservative,moderate,aggressive
    category = Column(String(50))                         # 배당주, 기술주, 대형주
    
    description = Column(String(500))
    logo_url = Column(String(300), nullable=True)
    is_active = Column(Boolean, default=True)
    
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class ETF(Base):
    """ETF"""
    __tablename__ = "etfs"
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), unique=True, index=True)
    name = Column(String(100), index=True)
    etf_type = Column(String(50))                         # equity, bond, commodity, reits
    
    # 성과
    current_price = Column(Float)
    aum = Column(Float)                                   # 운용자산 (백만원)
    expense_ratio = Column(Float)                         # 수수료율 (%)
    ytd_return = Column(Float, nullable=True)
    one_year_return = Column(Float, nullable=True)
    
    # 분류
    risk_level = Column(String(20))
    investment_type = Column(String(100))
    category = Column(String(50))
    
    description = Column(String(500))
    is_active = Column(Boolean, default=True)
    
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class Bond(Base):
    """채권"""
    __tablename__ = "bonds"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, index=True)
    bond_type = Column(String(50))                        # government, corporate, high_yield
    issuer = Column(String(100), nullable=True)
    
    # 금리
    interest_rate = Column(Float)                         # 금리 (%)
    coupon_rate = Column(Float, nullable=True)
    maturity_years = Column(Integer)
    
    # 신용도
    credit_rating = Column(String(10))                    # AAA, AA, A, BBB
    risk_level = Column(String(20))
    
    # 정보
    investment_type = Column(String(100))
    minimum_investment = Column(Integer)                  # 최소 투자액 (원)
    description = Column(String(500))
    is_active = Column(Boolean, default=True)
    
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class DepositProduct(Base):
    """예금 상품"""
    __tablename__ = "deposit_products"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, index=True)
    bank = Column(String(100))
    product_type = Column(String(50))                     # deposit, cma, savings
    
    # 금리
    interest_rate = Column(Float)                         # 금리 (%)
    term_months = Column(Integer, nullable=True)          # 기간 (개월)
    
    # 정보
    minimum_investment = Column(Integer)
    description = Column(String(500))
    is_active = Column(Boolean, default=True)
    
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class ProductRecommendation(Base):
    """상품 추천 규칙"""
    __tablename__ = "product_recommendations"
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer)                          # Stock/ETF/Bond ID
    product_type = Column(String(20))                     # stock, etf, bond, deposit
    investment_type = Column(String(50))                  # conservative, moderate, aggressive
    asset_class = Column(String(50))                      # stocks, bonds, cash
    allocation_weight = Column(Float)                     # 배분 비중
    score = Column(Float)                                 # 점수 (0~100)
    reason = Column(String(500))                          # 추천 이유
    
    created_at = Column(DateTime, default=datetime.utcnow)