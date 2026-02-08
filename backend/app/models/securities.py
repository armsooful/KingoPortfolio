# backend/app/models/securities.py

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Date, Numeric, ForeignKey, UniqueConstraint, Index
from app.database import Base
from app.utils.kst_now import kst_now

class Stock(Base):
    """한국 주식"""
    __tablename__ = "stocks"

    ticker = Column(String(10), primary_key=True)  # 005930 (PK)
    name = Column(String(100), index=True)                # 삼성전자
    company = Column(String(100))                         # 회사명 (영문)
    crno = Column(String(13), nullable=True)              # 법인등록번호 (FSC 배당 조회용)
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
    
    last_updated = Column(DateTime, default=kst_now, onupdate=kst_now)
    created_at = Column(DateTime, default=kst_now)


class ETF(Base):
    """ETF"""
    __tablename__ = "etfs"

    ticker = Column(String(10), primary_key=True)  # PK
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
    
    last_updated = Column(DateTime, default=kst_now, onupdate=kst_now)
    created_at = Column(DateTime, default=kst_now)


class Bond(Base):
    """채권 (교육용 + 실데이터 통합)"""
    __tablename__ = "bonds"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, index=True)
    bond_type = Column(String(50))                        # government, corporate, high_yield
    issuer = Column(String(100), nullable=True)

    # 금리
    interest_rate = Column(Float)                         # 금리 (%) — bond_srfc_inrt과 통합
    coupon_rate = Column(Float, nullable=True)
    maturity_years = Column(Integer)

    # 신용도
    credit_rating = Column(String(10))                    # AAA, AA, A, BBB (코드로부터 유도)
    risk_level = Column(String(20))

    # 정보
    investment_type = Column(String(100))                 # conservative,moderate,aggressive (유도)
    minimum_investment = Column(Integer)                  # 최소 투자액 (원)
    description = Column(String(500))
    is_active = Column(Boolean, default=True)

    # --- 실데이터 컬럼 (FSC API) ---
    # 식별
    isin_cd = Column(String(12), nullable=True)           # ISIN 코드 (unique)
    bas_dt = Column(String(8), nullable=True)             # API 조회 기준일 (YYYYMMDD)
    crno = Column(String(13), nullable=True)              # 법인등록번호

    # 종목
    scrs_itms_kcd = Column(String(4), nullable=True)      # 유가증권종목종류코드
    scrs_itms_kcd_nm = Column(String(100), nullable=True) # 유가증권종목종류코드명

    # 발행
    bond_issu_dt = Column(Date, nullable=True)            # 발행일
    bond_expr_dt = Column(Date, nullable=True)            # 만기일

    # 금액
    bond_issu_amt = Column(Numeric(22, 3), nullable=True) # 발행금액
    bond_bal = Column(Numeric(22, 3), nullable=True)      # 잔액

    # 금리 세부
    irt_chng_dcd = Column(String(1), nullable=True)       # 금리변동구분: Y=변동, N=고정
    bond_int_tcd = Column(String(1), nullable=True)       # 이자유형코드
    int_pay_cycl_ctt = Column(String(100), nullable=True) # 이자지급주기

    # 이표
    nxtm_copn_dt = Column(Date, nullable=True)            # 차기이표일
    rbf_copn_dt = Column(Date, nullable=True)             # 직전이표일

    # 보증/순위
    grn_dcd = Column(String(1), nullable=True)            # 보증구분코드
    bond_rnkn_dcd = Column(String(1), nullable=True)      # 순위구분코드

    # 신용등급 코드 (원본)
    kis_scrs_itms_kcd = Column(String(4), nullable=True)  # KIS 신용등급 코드
    kbp_scrs_itms_kcd = Column(String(4), nullable=True)  # KBP 신용등급 코드
    nice_scrs_itms_kcd = Column(String(4), nullable=True) # NICE 신용등급 코드
    fn_scrs_itms_kcd = Column(String(4), nullable=True)   # FN 신용등급 코드

    # 모집/상장
    bond_offr_mcd = Column(String(2), nullable=True)      # 모집방법코드
    lstg_dt = Column(Date, nullable=True)                 # 상장일

    # 특이
    prmnc_bond_yn = Column(String(1), nullable=True)      # 영구채권여부
    strips_psbl_yn = Column(String(1), nullable=True)     # 스트립스가능여부

    # 거버넌스
    source_id = Column(String(20), ForeignKey("data_source.source_id"), nullable=True)
    batch_id = Column(Integer, ForeignKey("data_load_batch.batch_id"), nullable=True)
    as_of_date = Column(Date, nullable=True)

    last_updated = Column(DateTime, default=kst_now, onupdate=kst_now)
    created_at = Column(DateTime, default=kst_now)

    __table_args__ = (
        UniqueConstraint('isin_cd', name='uq_bond_isin'),
        Index('idx_bond_isin', 'isin_cd'),
        Index('idx_bond_expr_dt', 'bond_expr_dt'),
    )


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

    last_updated = Column(DateTime, default=kst_now, onupdate=kst_now)
    created_at = Column(DateTime, default=kst_now)


class KrxTimeSeries(Base):
    """한국거래소 시계열 데이터 (일별)"""
    __tablename__ = "krx_timeseries"

    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), index=True, nullable=False)  # 005930, 069500 등
    date = Column(Date, index=True, nullable=False)

    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)

    created_at = Column(DateTime, default=kst_now)

    def __repr__(self):
        return f"<KrxTimeSeries {self.ticker} {self.date}>"


class StockFinancials(Base):
    """한국 주식 재무제표 데이터"""
    __tablename__ = "stock_financials"

    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), index=True, nullable=False)  # 005930
    fiscal_date = Column(Date, nullable=False)  # 회계 연도 (2024-12-31)
    report_type = Column(String(20), nullable=False)  # annual, quarterly

    # 손익계산서 (Income Statement)
    revenue = Column(Float)  # 매출액
    operating_income = Column(Float)  # 영업이익
    net_income = Column(Float)  # 순이익

    # 재무상태표 (Balance Sheet)
    total_assets = Column(Float)  # 총자산
    total_liabilities = Column(Float)  # 총부채
    total_equity = Column(Float)  # 총자본

    # 재무 비율 (자동 계산)
    roe = Column(Float, nullable=True)  # ROE = net_income / total_equity
    roa = Column(Float, nullable=True)  # ROA = net_income / total_assets
    debt_to_equity = Column(Float, nullable=True)  # 부채비율 = total_liabilities / total_equity
    operating_margin = Column(Float, nullable=True)  # 영업이익률 = operating_income / revenue
    net_margin = Column(Float, nullable=True)  # 순이익률 = net_income / revenue

    created_at = Column(DateTime, default=kst_now)
    last_updated = Column(DateTime, default=kst_now, onupdate=kst_now)

    def __repr__(self):
        return f"<StockFinancials {self.ticker} {self.fiscal_date} ({self.report_type})>"


class ProductRecommendation(Base):
    """상품 매칭 규칙 (교육용 시나리오)"""
    __tablename__ = "product_recommendations"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer)                          # Stock/ETF/Bond ID
    product_type = Column(String(20))                     # stock, etf, bond, deposit
    investment_type = Column(String(50))                  # conservative, moderate, aggressive
    asset_class = Column(String(50))                      # stocks, bonds, cash
    allocation_weight = Column(Float)                     # 배분 비중
    score = Column(Float)                                 # 점수 (0~100)
    reason = Column(String(500))                          # 매칭 사유

    created_at = Column(DateTime, default=kst_now)
