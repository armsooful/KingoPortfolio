# backend/app/models/alpha_vantage.py

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Date
from datetime import datetime
from app.database import Base
from app.utils.kst_now import kst_now


class AlphaVantageStock(Base):
    """Alpha Vantage 미국 주식 데이터"""
    __tablename__ = "alpha_vantage_stocks"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), unique=True, index=True, nullable=False)  # AAPL, GOOGL 등
    name = Column(String(200), nullable=False)  # Apple Inc., Alphabet Inc.
    exchange = Column(String(50))  # NASDAQ, NYSE
    sector = Column(String(100))  # Technology, Healthcare
    industry = Column(String(100))  # Consumer Electronics, Internet

    # 현재가 정보
    current_price = Column(Float)  # 현재가
    open_price = Column(Float)  # 시가
    high_price = Column(Float)  # 고가
    low_price = Column(Float)  # 저가
    volume = Column(Integer)  # 거래량
    previous_close = Column(Float)  # 전일 종가
    change = Column(Float)  # 변동액
    change_percent = Column(Float)  # 변동률(%)

    # 재무 지표
    market_cap = Column(Float)  # 시가총액
    pe_ratio = Column(Float, nullable=True)  # PER
    peg_ratio = Column(Float, nullable=True)  # PEG
    pb_ratio = Column(Float, nullable=True)  # PBR
    dividend_yield = Column(Float, nullable=True)  # 배당수익률(%)
    eps = Column(Float, nullable=True)  # 주당순이익
    beta = Column(Float, nullable=True)  # 베타(변동성)

    # 수익률
    week_52_high = Column(Float)  # 52주 최고가
    week_52_low = Column(Float)  # 52주 최저가
    day_50_ma = Column(Float)  # 50일 이동평균
    day_200_ma = Column(Float)  # 200일 이동평균
    ytd_return = Column(Float, nullable=True)  # YTD 수익률(%)
    one_year_return = Column(Float, nullable=True)  # 1년 수익률(%)

    # 분류
    risk_level = Column(String(20))  # low, medium, high
    investment_type = Column(String(100))  # conservative, moderate, aggressive
    category = Column(String(50))  # Large Cap, Small Cap, Growth, Value

    description = Column(Text)  # 회사 설명
    logo_url = Column(String(300), nullable=True)
    is_active = Column(Boolean, default=True)

    last_updated = Column(DateTime, default=kst_now, onupdate=kst_now)
    created_at = Column(DateTime, default=kst_now)

    def __repr__(self):
        return f"<AlphaVantageStock {self.symbol}: {self.name}>"


class AlphaVantageFinancials(Base):
    """Alpha Vantage 재무제표 데이터"""
    __tablename__ = "alpha_vantage_financials"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), index=True, nullable=False)
    fiscal_date = Column(Date, nullable=False)  # 회계 연도 (2024-12-31)
    report_type = Column(String(20), nullable=False)  # annual, quarterly

    # 손익계산서 (Income Statement)
    revenue = Column(Float)  # 매출액
    cost_of_revenue = Column(Float)  # 매출원가
    gross_profit = Column(Float)  # 매출총이익
    operating_income = Column(Float)  # 영업이익
    net_income = Column(Float)  # 순이익
    ebitda = Column(Float)  # EBITDA
    eps = Column(Float)  # EPS (주당순이익)

    # 재무상태표 (Balance Sheet)
    total_assets = Column(Float)  # 총자산
    total_liabilities = Column(Float)  # 총부채
    total_equity = Column(Float)  # 총자본
    cash_and_equivalents = Column(Float)  # 현금 및 현금성자산
    short_term_debt = Column(Float)  # 단기부채
    long_term_debt = Column(Float)  # 장기부채

    # 현금흐름표 (Cash Flow)
    operating_cash_flow = Column(Float)  # 영업활동 현금흐름
    investing_cash_flow = Column(Float)  # 투자활동 현금흐름
    financing_cash_flow = Column(Float)  # 재무활동 현금흐름
    free_cash_flow = Column(Float)  # 잉여현금흐름

    # 재무 비율 (자동 계산)
    roe = Column(Float, nullable=True)  # ROE = net_income / total_equity
    roa = Column(Float, nullable=True)  # ROA = net_income / total_assets
    debt_to_equity = Column(Float, nullable=True)  # 부채비율 = total_liabilities / total_equity
    current_ratio = Column(Float, nullable=True)  # 유동비율
    profit_margin = Column(Float, nullable=True)  # 순이익률 = net_income / revenue

    created_at = Column(DateTime, default=kst_now)
    last_updated = Column(DateTime, default=kst_now, onupdate=kst_now)

    def __repr__(self):
        return f"<AlphaVantageFinancials {self.symbol} {self.fiscal_date} ({self.report_type})>"


class AlphaVantageETF(Base):
    """Alpha Vantage 미국 ETF 데이터"""
    __tablename__ = "alpha_vantage_etfs"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), unique=True, index=True, nullable=False)  # SPY, QQQ
    name = Column(String(200), nullable=False)  # SPDR S&P 500 ETF
    etf_type = Column(String(50))  # equity, bond, commodity, sector

    # 현재가 정보
    current_price = Column(Float)
    volume = Column(Integer)
    change_percent = Column(Float)

    # ETF 특성
    aum = Column(Float)  # 운용자산 (Assets Under Management)
    expense_ratio = Column(Float)  # 운용수수료(%)
    inception_date = Column(Date, nullable=True)  # 설정일

    # 수익률
    ytd_return = Column(Float, nullable=True)
    one_year_return = Column(Float, nullable=True)
    three_year_return = Column(Float, nullable=True)
    five_year_return = Column(Float, nullable=True)

    # 분류
    risk_level = Column(String(20))
    investment_type = Column(String(100))
    category = Column(String(50))

    description = Column(Text)
    is_active = Column(Boolean, default=True)

    last_updated = Column(DateTime, default=kst_now, onupdate=kst_now)
    created_at = Column(DateTime, default=kst_now)

    def __repr__(self):
        return f"<AlphaVantageETF {self.symbol}: {self.name}>"


class AlphaVantageTimeSeries(Base):
    """Alpha Vantage 시계열 데이터 (일별)"""
    __tablename__ = "alpha_vantage_timeseries"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)

    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    adjusted_close = Column(Float)  # 조정 종가

    created_at = Column(DateTime, default=kst_now)

    def __repr__(self):
        return f"<AlphaVantageTimeSeries {self.symbol} {self.date}>"
