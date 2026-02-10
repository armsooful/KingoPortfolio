# backend/app/models/securities.py

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Date, Numeric, ForeignKey, UniqueConstraint, Index, Text
from sqlalchemy.orm import relationship
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
    """예금 상품 (FSS 금융상품 한 눈에 API 연동)"""
    __tablename__ = "deposit_products"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), index=True)
    bank = Column(String(100))
    product_type = Column(String(50))                     # deposit, cma, savings

    # 금리 (대표 금리 — 12개월 기본금리 등)
    interest_rate = Column(Float, nullable=True)          # 금리 (%)
    term_months = Column(Integer, nullable=True)          # 기간 (개월)

    # 정보
    minimum_investment = Column(Integer, nullable=True)
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)

    # --- FSS API 필드 ---
    fin_co_no = Column(String(20), nullable=True)         # 금융회사코드
    fin_prdt_cd = Column(String(50), nullable=True)       # 금융상품코드 (unique)
    dcls_month = Column(String(6), nullable=True)         # 공시제출월 (YYYYMM)
    join_way = Column(Text, nullable=True)                # 가입방법
    mtrt_int = Column(Text, nullable=True)                # 만기 후 이자율
    spcl_cnd = Column(Text, nullable=True)                # 우대조건
    join_deny = Column(String(1), nullable=True)          # 가입제한 (1:제한없음, 2:서민전용, 3:일부제한)
    join_member = Column(Text, nullable=True)             # 가입대상
    etc_note = Column(Text, nullable=True)                # 기타 유의사항
    max_limit = Column(Float, nullable=True)              # 최고한도

    last_updated = Column(DateTime, default=kst_now, onupdate=kst_now)
    created_at = Column(DateTime, default=kst_now)

    # 금리 옵션 관계
    rate_options = relationship("DepositRateOption", back_populates="deposit_product", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('fin_co_no', 'fin_prdt_cd', name='uq_deposit_co_prdt'),
    )


class DepositRateOption(Base):
    """예금 금리 옵션 (기간별)"""
    __tablename__ = "deposit_rate_options"

    id = Column(Integer, primary_key=True)
    deposit_product_id = Column(Integer, ForeignKey("deposit_products.id", ondelete="CASCADE"), nullable=False)
    save_trm = Column(Integer, nullable=False)            # 저축기간 (개월)
    intr_rate_type = Column(String(1), nullable=True)     # 저축금리유형 (S:단리, M:복리)
    intr_rate_type_nm = Column(String(20), nullable=True) # 저축금리유형명
    intr_rate = Column(Float, nullable=True)              # 기본금리 (%)
    intr_rate2 = Column(Float, nullable=True)             # 최고금리 (%)

    created_at = Column(DateTime, default=kst_now)

    deposit_product = relationship("DepositProduct", back_populates="rate_options")

    __table_args__ = (
        UniqueConstraint('deposit_product_id', 'save_trm', 'intr_rate_type', name='uq_deposit_rate_option'),
        Index('idx_deposit_rate_product', 'deposit_product_id'),
    )


class SavingsProduct(Base):
    """적금 상품 (FSS 금융상품 한 눈에 API 연동)"""
    __tablename__ = "savings_products"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), index=True)
    bank = Column(String(100))
    product_type = Column(String(50))                     # savings

    # 금리 (대표 금리 — 12개월 정액적립식 단리 기본금리)
    interest_rate = Column(Float, nullable=True)          # 금리 (%)
    term_months = Column(Integer, nullable=True)          # 기간 (개월)

    # 정보
    minimum_investment = Column(Integer, nullable=True)
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)

    # --- FSS API 필드 ---
    fin_co_no = Column(String(20), nullable=True)         # 금융회사코드
    fin_prdt_cd = Column(String(50), nullable=True)       # 금융상품코드
    dcls_month = Column(String(6), nullable=True)         # 공시제출월 (YYYYMM)
    join_way = Column(Text, nullable=True)                # 가입방법
    mtrt_int = Column(Text, nullable=True)                # 만기 후 이자율
    spcl_cnd = Column(Text, nullable=True)                # 우대조건
    join_deny = Column(String(1), nullable=True)          # 가입제한 (1:제한없음, 2:서민전용, 3:일부제한)
    join_member = Column(Text, nullable=True)             # 가입대상
    etc_note = Column(Text, nullable=True)                # 기타 유의사항
    max_limit = Column(Float, nullable=True)              # 최고한도

    last_updated = Column(DateTime, default=kst_now, onupdate=kst_now)
    created_at = Column(DateTime, default=kst_now)

    # 금리 옵션 관계
    rate_options = relationship("SavingsRateOption", back_populates="savings_product", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('fin_co_no', 'fin_prdt_cd', name='uq_savings_co_prdt'),
    )


class SavingsRateOption(Base):
    """적금 금리 옵션 (기간별/적립유형별)"""
    __tablename__ = "savings_rate_options"

    id = Column(Integer, primary_key=True)
    savings_product_id = Column(Integer, ForeignKey("savings_products.id", ondelete="CASCADE"), nullable=False)
    save_trm = Column(Integer, nullable=False)            # 저축기간 (개월)
    intr_rate_type = Column(String(1), nullable=True)     # 저축금리유형 (S:단리, M:복리)
    intr_rate_type_nm = Column(String(20), nullable=True) # 저축금리유형명
    rsrv_type = Column(String(1), nullable=True)          # 적립유형 (S:정액적립식, F:자유적립식)
    rsrv_type_nm = Column(String(20), nullable=True)      # 적립유형명
    intr_rate = Column(Float, nullable=True)              # 기본금리 (%)
    intr_rate2 = Column(Float, nullable=True)             # 최고금리 (%)

    created_at = Column(DateTime, default=kst_now)

    savings_product = relationship("SavingsProduct", back_populates="rate_options")

    __table_args__ = (
        UniqueConstraint('savings_product_id', 'save_trm', 'intr_rate_type', 'rsrv_type', name='uq_savings_rate_option'),
        Index('idx_savings_rate_product', 'savings_product_id'),
    )


class AnnuitySavingsProduct(Base):
    """연금저축 상품 (FSS 금융상품 한 눈에 API 연동)"""
    __tablename__ = "annuity_savings_products"

    id = Column(Integer, primary_key=True)
    name = Column(String(300), index=True)                # fin_prdt_nm
    company = Column(String(200))                         # kor_co_nm (운용사/보험사)
    product_type = Column(String(50))                     # annuity_savings

    # --- FSS API 필드 ---
    fin_co_no = Column(String(20), nullable=True)         # 금융회사코드
    fin_prdt_cd = Column(String(50), nullable=True)       # 금융상품코드
    dcls_month = Column(String(6), nullable=True)         # 공시제출월 (YYYYMM)
    join_way = Column(Text, nullable=True)                # 가입방법

    # 연금 종류
    pnsn_kind = Column(String(2), nullable=True)          # 연금종류코드 (1:연금저축보험, 2:연금저축신탁, 3:연금저축손보, 4:연금저축펀드)
    pnsn_kind_nm = Column(String(50), nullable=True)      # 연금종류명

    # 상품 유형
    prdt_type = Column(String(10), nullable=True)         # 상품유형코드 (421:주식형, 422:채권형 등)
    prdt_type_nm = Column(String(50), nullable=True)      # 상품유형명

    # 수익률
    avg_prft_rate = Column(Float, nullable=True)          # 평균수익률 (%)
    dcls_rate = Column(Float, nullable=True)              # 공시이율 (%)
    guar_rate = Column(Float, nullable=True)              # 최저보증이율 (%)
    btrm_prft_rate_1 = Column(Float, nullable=True)       # 전기 수익률 (%)
    btrm_prft_rate_2 = Column(Float, nullable=True)       # 전전기 수익률 (%)
    btrm_prft_rate_3 = Column(Float, nullable=True)       # 전전전기 수익률 (%)

    # 기타
    sale_strt_day = Column(String(8), nullable=True)      # 판매개시일 (YYYYMMDD)
    mntn_cnt = Column(Float, nullable=True)               # 설정액 (원)
    sale_co = Column(Text, nullable=True)                 # 판매사
    etc = Column(Text, nullable=True)                     # 기타

    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime, default=kst_now, onupdate=kst_now)
    created_at = Column(DateTime, default=kst_now)

    # 연금수령 옵션 관계
    pension_options = relationship("AnnuitySavingsOption", back_populates="annuity_product", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('fin_co_no', 'fin_prdt_cd', name='uq_annuity_co_prdt'),
    )


class AnnuitySavingsOption(Base):
    """연금저축 수령 옵션 (가입조건별 연금수령액)"""
    __tablename__ = "annuity_savings_options"

    id = Column(Integer, primary_key=True)
    annuity_product_id = Column(Integer, ForeignKey("annuity_savings_products.id", ondelete="CASCADE"), nullable=False)

    pnsn_recp_trm = Column(String(2), nullable=True)      # 연금수령기간코드 (A:10년확정, B:20년확정 등)
    pnsn_recp_trm_nm = Column(String(30), nullable=True)   # 연금수령기간명
    pnsn_entr_age = Column(String(5), nullable=True)       # 가입나이
    pnsn_entr_age_nm = Column(String(20), nullable=True)   # 가입나이명
    mon_paym_atm = Column(String(10), nullable=True)       # 월납입금코드
    mon_paym_atm_nm = Column(String(30), nullable=True)    # 월납입금명
    paym_prd = Column(String(5), nullable=True)            # 납입기간코드
    paym_prd_nm = Column(String(20), nullable=True)        # 납입기간명
    pnsn_strt_age = Column(String(5), nullable=True)       # 연금개시나이
    pnsn_strt_age_nm = Column(String(20), nullable=True)   # 연금개시나이명
    pnsn_recp_amt = Column(Float, nullable=True)           # 연금수령액 (원)

    created_at = Column(DateTime, default=kst_now)

    annuity_product = relationship("AnnuitySavingsProduct", back_populates="pension_options")

    __table_args__ = (
        Index('idx_annuity_option_product', 'annuity_product_id'),
    )


class MortgageLoanProduct(Base):
    """주택담보대출 상품 (FSS 금융상품 한 눈에 API 연동)"""
    __tablename__ = "mortgage_loan_products"

    id = Column(Integer, primary_key=True)
    name = Column(String(300), index=True)                # fin_prdt_nm
    bank = Column(String(200))                            # kor_co_nm
    product_type = Column(String(50))                     # mortgage_loan

    # --- FSS API 필드 ---
    fin_co_no = Column(String(20), nullable=True)         # 금융회사코드
    fin_prdt_cd = Column(String(50), nullable=True)       # 금융상품코드
    dcls_month = Column(String(6), nullable=True)         # 공시제출월 (YYYYMM)
    join_way = Column(Text, nullable=True)                # 가입방법
    loan_inci_expn = Column(Text, nullable=True)          # 대출 부대비용
    erly_rpay_fee = Column(Text, nullable=True)           # 중도상환 수수료
    dly_rate = Column(Text, nullable=True)                # 연체이율
    loan_lmt = Column(Text, nullable=True)                # 대출한도

    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime, default=kst_now, onupdate=kst_now)
    created_at = Column(DateTime, default=kst_now)

    # 금리 옵션 관계
    rate_options = relationship("MortgageLoanOption", back_populates="mortgage_product", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('fin_co_no', 'fin_prdt_cd', name='uq_mortgage_co_prdt'),
    )


class MortgageLoanOption(Base):
    """주택담보대출 금리 옵션 (담보유형/상환방식/금리유형별)"""
    __tablename__ = "mortgage_loan_options"

    id = Column(Integer, primary_key=True)
    mortgage_product_id = Column(Integer, ForeignKey("mortgage_loan_products.id", ondelete="CASCADE"), nullable=False)

    mrtg_type = Column(String(2), nullable=True)          # 담보유형코드 (A:아파트, B:연립다세대 등)
    mrtg_type_nm = Column(String(30), nullable=True)      # 담보유형명
    rpay_type = Column(String(2), nullable=True)          # 상환방식코드 (D:분할상환)
    rpay_type_nm = Column(String(30), nullable=True)      # 상환방식명
    lend_rate_type = Column(String(2), nullable=True)     # 금리유형코드 (F:고정, V:변동)
    lend_rate_type_nm = Column(String(30), nullable=True) # 금리유형명
    lend_rate_min = Column(Float, nullable=True)          # 최저금리 (%)
    lend_rate_max = Column(Float, nullable=True)          # 최고금리 (%)
    lend_rate_avg = Column(Float, nullable=True)          # 평균금리 (%)

    created_at = Column(DateTime, default=kst_now)

    mortgage_product = relationship("MortgageLoanProduct", back_populates="rate_options")

    __table_args__ = (
        UniqueConstraint('mortgage_product_id', 'mrtg_type', 'rpay_type', 'lend_rate_type', name='uq_mortgage_loan_option'),
        Index('idx_mortgage_option_product', 'mortgage_product_id'),
    )


class RentHouseLoanProduct(Base):
    """전세자금대출 상품 (FSS 금융상품 한 눈에 API 연동)"""
    __tablename__ = "rent_house_loan_products"

    id = Column(Integer, primary_key=True)
    name = Column(String(300), index=True)                # fin_prdt_nm
    bank = Column(String(200))                            # kor_co_nm
    product_type = Column(String(50))                     # rent_house_loan

    # --- FSS API 필드 ---
    fin_co_no = Column(String(20), nullable=True)
    fin_prdt_cd = Column(String(50), nullable=True)
    dcls_month = Column(String(6), nullable=True)
    join_way = Column(Text, nullable=True)
    loan_inci_expn = Column(Text, nullable=True)          # 대출 부대비용
    erly_rpay_fee = Column(Text, nullable=True)           # 중도상환 수수료
    dly_rate = Column(Text, nullable=True)                # 연체이율
    loan_lmt = Column(Text, nullable=True)                # 대출한도

    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime, default=kst_now, onupdate=kst_now)
    created_at = Column(DateTime, default=kst_now)

    rate_options = relationship("RentHouseLoanOption", back_populates="rent_loan_product", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('fin_co_no', 'fin_prdt_cd', name='uq_rent_loan_co_prdt'),
    )


class RentHouseLoanOption(Base):
    """전세자금대출 금리 옵션 (상환방식/금리유형별)"""
    __tablename__ = "rent_house_loan_options"

    id = Column(Integer, primary_key=True)
    rent_loan_product_id = Column(Integer, ForeignKey("rent_house_loan_products.id", ondelete="CASCADE"), nullable=False)

    rpay_type = Column(String(2), nullable=True)          # 상환방식코드 (S:만기일시, D:분할상환)
    rpay_type_nm = Column(String(30), nullable=True)
    lend_rate_type = Column(String(2), nullable=True)     # 금리유형코드 (F:고정, V:변동)
    lend_rate_type_nm = Column(String(30), nullable=True)
    lend_rate_min = Column(Float, nullable=True)
    lend_rate_max = Column(Float, nullable=True)
    lend_rate_avg = Column(Float, nullable=True)

    created_at = Column(DateTime, default=kst_now)

    rent_loan_product = relationship("RentHouseLoanProduct", back_populates="rate_options")

    __table_args__ = (
        UniqueConstraint('rent_loan_product_id', 'rpay_type', 'lend_rate_type', name='uq_rent_loan_option'),
        Index('idx_rent_loan_option_product', 'rent_loan_product_id'),
    )


class CreditLoanProduct(Base):
    """개인신용대출 상품 (FSS 금융상품 한 눈에 API 연동)"""
    __tablename__ = "credit_loan_products"

    id = Column(Integer, primary_key=True)
    name = Column(String(300), index=True)                # fin_prdt_nm
    bank = Column(String(200))                            # kor_co_nm
    product_type = Column(String(50))                     # credit_loan

    # --- FSS API 필드 ---
    fin_co_no = Column(String(20), nullable=True)         # 금융회사코드
    fin_prdt_cd = Column(String(50), nullable=True)       # 금융상품코드
    dcls_month = Column(String(6), nullable=True)         # 공시제출월 (YYYYMM)
    join_way = Column(Text, nullable=True)                # 가입방법
    crdt_prdt_type = Column(String(2), nullable=True)     # 신용대출 상품유형코드 (1:일반,2:마이너스,3:장기카드)
    crdt_prdt_type_nm = Column(String(50), nullable=True) # 신용대출 상품유형명
    cb_name = Column(String(100), nullable=True)          # CB(신용평가) 기관명

    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime, default=kst_now, onupdate=kst_now)
    created_at = Column(DateTime, default=kst_now)

    # 금리 옵션 관계
    rate_options = relationship("CreditLoanOption", back_populates="credit_loan_product", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('fin_co_no', 'fin_prdt_cd', name='uq_credit_loan_co_prdt'),
    )


class CreditLoanOption(Base):
    """개인신용대출 금리 옵션 (신용등급별/금리유형별)"""
    __tablename__ = "credit_loan_options"

    id = Column(Integer, primary_key=True)
    credit_loan_product_id = Column(Integer, ForeignKey("credit_loan_products.id", ondelete="CASCADE"), nullable=False)

    crdt_lend_rate_type = Column(String(2), nullable=True)     # 대출금리유형 (A:대출금리,B:기준금리,C:가산금리,D:가감조정)
    crdt_lend_rate_type_nm = Column(String(30), nullable=True) # 대출금리유형명
    crdt_grad_1 = Column(Float, nullable=True)                 # 신용등급 1등급 금리
    crdt_grad_4 = Column(Float, nullable=True)                 # 신용등급 4등급 금리
    crdt_grad_5 = Column(Float, nullable=True)                 # 신용등급 5등급 금리
    crdt_grad_6 = Column(Float, nullable=True)                 # 신용등급 6등급 금리
    crdt_grad_10 = Column(Float, nullable=True)                # 신용등급 10등급 금리
    crdt_grad_11 = Column(Float, nullable=True)                # 신용등급 11등급 금리
    crdt_grad_12 = Column(Float, nullable=True)                # 신용등급 12등급 금리
    crdt_grad_13 = Column(Float, nullable=True)                # 신용등급 13등급 금리
    crdt_grad_avg = Column(Float, nullable=True)               # 평균 금리

    created_at = Column(DateTime, default=kst_now)

    credit_loan_product = relationship("CreditLoanProduct", back_populates="rate_options")

    __table_args__ = (
        UniqueConstraint('credit_loan_product_id', 'crdt_lend_rate_type', name='uq_credit_loan_option'),
        Index('idx_credit_loan_option_product', 'credit_loan_product_id'),
    )


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
