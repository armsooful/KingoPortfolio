"""
Phase 11: 실 데이터 적재용 ORM 모델

목적: 실 데이터 적재 및 거버넌스를 위한 테이블 정의
작성일: 2026-01-24

주요 원칙:
- 모든 데이터에 source_id, as_of_date 필수
- batch_id로 적재 이력 추적
- 품질 플래그로 데이터 신뢰도 표시
"""

from sqlalchemy import (
    Column, String, Integer, BigInteger, Boolean, DateTime, Date, Text,
    ForeignKey, Index, UniqueConstraint, Numeric, CheckConstraint
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.kst_now import kst_now


# ============================================================================
# 마스터 데이터
# ============================================================================

class DataSource(Base):
    """데이터 소스 마스터"""
    __tablename__ = "data_source"

    source_id = Column(String(20), primary_key=True)  # 'KRX', 'PYKRX', 'NAVER'
    source_name = Column(String(100), nullable=False)
    source_type = Column(String(20), nullable=False)  # 'EXCHANGE', 'VENDOR', 'CALCULATED'
    base_url = Column(String(500))
    api_type = Column(String(20))  # 'REST', 'SCRAPING', 'FILE'
    update_frequency = Column(String(20))  # 'DAILY', 'REALTIME', 'MANUAL'
    license_type = Column(String(50))  # 'PUBLIC', 'COMMERCIAL', 'INTERNAL'
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=kst_now)

    # 관계
    batches = relationship("DataLoadBatch", back_populates="source")

    def __repr__(self):
        return f"<DataSource {self.source_id}: {self.source_name}>"


class DataLoadBatch(Base):
    """데이터 적재 배치 이력"""
    __tablename__ = "data_load_batch"

    batch_id = Column(Integer, primary_key=True, autoincrement=True)
    batch_type = Column(String(30), nullable=False)  # 'PRICE', 'FUNDAMENTAL', 'INDEX'
    source_id = Column(String(20), ForeignKey("data_source.source_id"), nullable=False)
    as_of_date = Column(Date, nullable=False)  # 데이터 기준일
    target_start = Column(Date, nullable=False)  # 적재 대상 기간 시작
    target_end = Column(Date, nullable=False)  # 적재 대상 기간 종료
    status = Column(String(20), nullable=False, default='PENDING')  # 'PENDING','RUNNING','SUCCESS','FAILED'

    # 처리 결과
    total_records = Column(Integer, default=0)
    success_records = Column(Integer, default=0)
    failed_records = Column(Integer, default=0)
    skipped_records = Column(Integer, default=0)

    # 품질 메트릭
    quality_score = Column(Numeric(5, 2))  # 0.00 ~ 100.00
    null_ratio = Column(Numeric(5, 4))
    outlier_ratio = Column(Numeric(5, 4))

    # 운영 정보
    operator_id = Column(String(50))
    operator_reason = Column(Text)
    error_message = Column(Text)

    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=kst_now)

    # 관계
    source = relationship("DataSource", back_populates="batches")

    __table_args__ = (
        Index('idx_data_load_batch_asof', 'as_of_date'),
        Index('idx_data_load_batch_status', 'status'),
        Index('idx_data_load_batch_source', 'source_id', 'batch_type'),
    )

    def __repr__(self):
        return f"<DataLoadBatch {self.batch_id}: {self.batch_type} {self.as_of_date} [{self.status}]>"


# ============================================================================
# 가격 데이터
# ============================================================================

class StockPriceDaily(Base):
    """주식 일별 시세"""
    __tablename__ = "stock_price_daily"

    price_id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False)  # '005930'
    trade_date = Column(Date, nullable=False)  # 거래일

    # OHLCV
    open_price = Column(Numeric(18, 2), nullable=False)
    high_price = Column(Numeric(18, 2), nullable=False)
    low_price = Column(Numeric(18, 2), nullable=False)
    close_price = Column(Numeric(18, 2), nullable=False)
    volume = Column(BigInteger, nullable=False)

    # 추가 지표
    adj_close_price = Column(Numeric(18, 2))  # 수정 종가
    market_cap = Column(BigInteger)  # 시가총액 (원)
    trading_value = Column(BigInteger)  # 거래대금 (원)
    shares_outstanding = Column(BigInteger)  # 발행주식수

    # 전일 대비
    prev_close = Column(Numeric(18, 2))
    price_change = Column(Numeric(18, 2))
    change_rate = Column(Numeric(8, 4))  # 등락률 (%)

    # 데이터 거버넌스
    source_id = Column(String(20), ForeignKey("data_source.source_id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("data_load_batch.batch_id"))
    as_of_date = Column(Date, nullable=False)  # 데이터 기준일

    # 품질
    is_verified = Column(Boolean, default=False)
    quality_flag = Column(String(10), default='NORMAL')  # 'NORMAL','ADJUSTED','ESTIMATED','MIGRATED'

    created_at = Column(DateTime, default=kst_now)

    __table_args__ = (
        UniqueConstraint('ticker', 'trade_date', 'source_id', name='uq_stock_price_daily'),
        Index('idx_stock_price_ticker_date', 'ticker', 'trade_date'),
        Index('idx_stock_price_date', 'trade_date'),
        Index('idx_stock_price_asof', 'as_of_date'),
        Index('idx_stock_price_batch', 'batch_id'),
        CheckConstraint('close_price > 0', name='chk_stock_price_close_positive'),
        CheckConstraint('volume >= 0', name='chk_stock_price_volume_nonnegative'),
        CheckConstraint('high_price >= low_price', name='chk_stock_price_high_low'),
    )

    def __repr__(self):
        return f"<StockPriceDaily {self.ticker} {self.trade_date}: {self.close_price}>"


class IndexPriceDaily(Base):
    """지수 일별 시세"""
    __tablename__ = "index_price_daily"

    price_id = Column(BigInteger, primary_key=True, autoincrement=True)
    index_code = Column(String(20), nullable=False)  # 'KOSPI', 'KOSDAQ', 'KS200'
    trade_date = Column(Date, nullable=False)

    # OHLC
    open_price = Column(Numeric(18, 4), nullable=False)
    high_price = Column(Numeric(18, 4), nullable=False)
    low_price = Column(Numeric(18, 4), nullable=False)
    close_price = Column(Numeric(18, 4), nullable=False)

    # 추가 지표
    volume = Column(BigInteger)  # 거래량 (주)
    trading_value = Column(BigInteger)  # 거래대금 (백만원)
    market_cap = Column(BigInteger)  # 시가총액 (억원)

    # 전일 대비
    prev_close = Column(Numeric(18, 4))
    price_change = Column(Numeric(18, 4))
    change_rate = Column(Numeric(8, 4))

    # 데이터 거버넌스
    source_id = Column(String(20), ForeignKey("data_source.source_id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("data_load_batch.batch_id"))
    as_of_date = Column(Date, nullable=False)

    is_verified = Column(Boolean, default=False)
    quality_flag = Column(String(10), default='NORMAL')

    created_at = Column(DateTime, default=kst_now)

    __table_args__ = (
        UniqueConstraint('index_code', 'trade_date', 'source_id', name='uq_index_price_daily'),
        Index('idx_index_price_code_date', 'index_code', 'trade_date'),
        Index('idx_index_price_date', 'trade_date'),
    )

    def __repr__(self):
        return f"<IndexPriceDaily {self.index_code} {self.trade_date}: {self.close_price}>"


# ============================================================================
# 기본 정보
# ============================================================================

class StockInfo(Base):
    """종목 기본 정보"""
    __tablename__ = "stock_info"

    info_id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False)
    as_of_date = Column(Date, nullable=False)  # 정보 기준일

    # 기본 정보
    stock_name = Column(String(100), nullable=False)
    stock_name_en = Column(String(100))
    market_type = Column(String(20), nullable=False)  # 'KOSPI', 'KOSDAQ', 'KONEX'
    sector_code = Column(String(10))
    sector_name = Column(String(50))
    industry_code = Column(String(10))
    industry_name = Column(String(50))

    # 상장 정보
    listing_date = Column(Date)
    fiscal_month = Column(Integer)  # 결산월 (12, 3, 6 등)
    ceo_name = Column(String(100))
    headquarters = Column(String(200))
    website = Column(String(300))

    # 주식 정보
    face_value = Column(Integer)  # 액면가
    shares_listed = Column(BigInteger)  # 상장주식수
    shares_outstanding = Column(BigInteger)  # 발행주식수

    # 데이터 거버넌스
    source_id = Column(String(20), ForeignKey("data_source.source_id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("data_load_batch.batch_id"))
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=kst_now)

    __table_args__ = (
        UniqueConstraint('ticker', 'as_of_date', 'source_id', name='uq_stock_info'),
        Index('idx_stock_info_ticker', 'ticker'),
        Index('idx_stock_info_market', 'market_type'),
        Index('idx_stock_info_asof', 'as_of_date'),
    )

    def __repr__(self):
        return f"<StockInfo {self.ticker} ({self.stock_name}) as of {self.as_of_date}>"


# ============================================================================
# FinanceDataReader 종목 마스터
# ============================================================================

class FdrStockListing(Base):
    """FinanceDataReader 종목 마스터"""
    __tablename__ = "fdr_stock_listing"

    listing_id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False)  # 종목코드
    name = Column(String(100), nullable=False)  # 종목명
    market = Column(String(20), nullable=False)  # KOSPI/KOSDAQ/KONEX/KRX
    sector = Column(String(100))
    industry = Column(String(100))
    listing_date = Column(Date)
    shares = Column(BigInteger)
    par_value = Column(Numeric(18, 2))

    # 데이터 거버넌스
    as_of_date = Column(Date, nullable=False)
    source_id = Column(String(20), ForeignKey("data_source.source_id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("data_load_batch.batch_id"))

    created_at = Column(DateTime, default=kst_now)

    __table_args__ = (
        UniqueConstraint('ticker', 'as_of_date', 'source_id', name='uq_fdr_stock_listing'),
        Index('idx_fdr_stock_ticker', 'ticker'),
        Index('idx_fdr_stock_market', 'market'),
        Index('idx_fdr_stock_asof', 'as_of_date'),
    )

    def __repr__(self):
        return f"<FdrStockListing {self.ticker} ({self.name}) {self.market}>"


# ============================================================================
# 데이터 품질
# ============================================================================

class DataQualityLog(Base):
    """데이터 품질 검증 로그"""
    __tablename__ = "data_quality_log"

    log_id = Column(BigInteger, primary_key=True, autoincrement=True)
    batch_id = Column(Integer, ForeignKey("data_load_batch.batch_id"), nullable=False)
    table_name = Column(String(50), nullable=False)

    # 검증 결과
    rule_id = Column(String(20), nullable=False)  # 'DQ-001', 'DQ-002', ...
    rule_name = Column(String(100))
    severity = Column(String(10), nullable=False)  # 'ERROR', 'WARNING', 'INFO'

    # 위반 상세
    record_id = Column(BigInteger)  # 위반 레코드 ID
    field_name = Column(String(50))
    field_value = Column(String(200))
    expected_condition = Column(String(200))

    created_at = Column(DateTime, default=kst_now)

    __table_args__ = (
        Index('idx_dq_log_batch', 'batch_id'),
        Index('idx_dq_log_severity', 'severity'),
        Index('idx_dq_log_rule', 'rule_id'),
    )

    def __repr__(self):
        return f"<DataQualityLog [{self.severity}] {self.rule_id}: {self.table_name}>"


# ============================================================================
# Level 2: 재무/공시 데이터 (DART)
# ============================================================================

class FinancialStatement(Base):
    """재무제표 (DART)"""
    __tablename__ = "financial_statement"

    statement_id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False)
    fiscal_year = Column(Integer, nullable=False)
    fiscal_quarter = Column(Integer, nullable=False)  # 1, 2, 3, 4 (연간은 4)
    report_type = Column(String(20), nullable=False)  # 'ANNUAL', 'QUARTERLY'

    # 손익계산서
    revenue = Column(BigInteger)  # 매출액
    operating_income = Column(BigInteger)  # 영업이익
    net_income = Column(BigInteger)  # 당기순이익

    # 재무상태표
    total_assets = Column(BigInteger)  # 자산총계
    total_liabilities = Column(BigInteger)  # 부채총계
    total_equity = Column(BigInteger)  # 자본총계

    # 현금흐름표
    operating_cash_flow = Column(BigInteger)
    investing_cash_flow = Column(BigInteger)
    financing_cash_flow = Column(BigInteger)

    # 주요 비율
    roe = Column(Numeric(8, 4))  # ROE (%)
    roa = Column(Numeric(8, 4))  # ROA (%)
    debt_ratio = Column(Numeric(8, 4))  # 부채비율 (%)

    # 데이터 거버넌스
    source_id = Column(String(20), ForeignKey("data_source.source_id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("data_load_batch.batch_id"))
    as_of_date = Column(Date, nullable=False)
    dart_rcept_no = Column(String(20))  # DART 접수번호

    created_at = Column(DateTime, default=kst_now)

    __table_args__ = (
        UniqueConstraint('ticker', 'fiscal_year', 'fiscal_quarter', 'source_id',
                        name='uq_financial_statement'),
        Index('idx_fin_stmt_ticker', 'ticker'),
        Index('idx_fin_stmt_fiscal', 'fiscal_year', 'fiscal_quarter'),
    )

    def __repr__(self):
        return f"<FinancialStatement {self.ticker} {self.fiscal_year}Q{self.fiscal_quarter}>"


class DividendHistory(Base):
    """배당 이력 (FSC_DATA_GO_KR API 기준)

    데이터 출처: 금융위원회 주식배당정보 API
    - isin_cd + dvdn_bas_dt + scrs_itms_kcd를 복합키로 사용
    - 보통주/우선주 구분하여 저장
    """
    __tablename__ = "dividend_history"

    dividend_id = Column(Integer, primary_key=True, autoincrement=True)

    # 종목 식별 (FSC API 기준)
    isin_cd = Column(String(12), nullable=False)  # ISIN 코드 (KR7005930003)
    isin_cd_nm = Column(String(200))  # ISIN 코드명 (삼성전자)
    crno = Column(String(13))  # 법인등록번호
    ticker = Column(String(10))  # 종목코드 (005930) - 레거시 호환용

    # 배당 일정 (FSC API 필드)
    dvdn_bas_dt = Column(Date, nullable=False)  # 배당기준일자 (주주확정일)
    cash_dvdn_pay_dt = Column(Date)  # 현금배당지급일자
    stck_stac_md = Column(String(4))  # 주식결산월일 (12/31 형식)

    # 유가증권 종류 (보통주/우선주 구분)
    scrs_itms_kcd = Column(String(4))  # 유가증권종목종류코드 (0101=보통주, 0201=우선주)
    scrs_itms_kcd_nm = Column(String(100))  # 유가증권종목종류코드명

    # 배당 사유
    stck_dvdn_rcd = Column(String(2))  # 주식배당사유코드 (00=무배당, 01=현금배당 등)
    stck_dvdn_rcd_nm = Column(String(100))  # 주식배당사유코드명

    # 배당금액 (1주당)
    stck_genr_dvdn_amt = Column(Numeric(22, 3))  # 주식일반배당금액 (현금배당)
    stck_grdn_dvdn_amt = Column(Numeric(22, 3))  # 주식차등배당금액

    # 배당률
    stck_genr_cash_dvdn_rt = Column(Numeric(26, 10))  # 주식일반현금배당률
    stck_genr_dvdn_rt = Column(Numeric(26, 10))  # 주식일반배당률 (액면가 대비)
    cash_grdn_dvdn_rt = Column(Numeric(26, 10))  # 현금차등배당률
    stck_grdn_dvdn_rt = Column(Numeric(26, 10))  # 주식차등배당률

    # 주식 정보
    stck_par_prc = Column(Numeric(22, 3))  # 주식액면가

    # 명의개서대리인 정보
    trsnm_dpty_dcd = Column(String(2))  # 명의개서대리인구분코드
    trsnm_dpty_dcd_nm = Column(String(100))  # 명의개서대리인구분코드명

    # 데이터 거버넌스
    bas_dt = Column(String(8))  # API 조회 기준일자 (YYYYMMDD)
    source_id = Column(String(20), ForeignKey("data_source.source_id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("data_load_batch.batch_id"))
    as_of_date = Column(Date, nullable=False)  # 데이터 기준일

    created_at = Column(DateTime, default=kst_now)

    __table_args__ = (
        # isin_cd + 배당기준일 + 주식종류 + 소스로 유일성 보장
        UniqueConstraint('isin_cd', 'dvdn_bas_dt', 'scrs_itms_kcd', 'source_id',
                        name='uq_dividend_history'),
        Index('idx_dividend_isin', 'isin_cd'),
        Index('idx_dividend_ticker', 'ticker'),
        Index('idx_dividend_dvdn_bas_dt', 'dvdn_bas_dt'),
        Index('idx_dividend_asof', 'as_of_date'),
    )

    def __repr__(self):
        return f"<DividendHistory {self.isin_cd} {self.dvdn_bas_dt} {self.stck_dvdn_rcd_nm}>"


# ============================================================================
# Level 2: 기업 액션 (분할/합병 등)
# ============================================================================

class CorporateAction(Base):
    """기업 액션 이력"""
    __tablename__ = "corporate_action"

    action_id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False)
    action_type = Column(String(20), nullable=False)  # SPLIT, REVERSE_SPLIT, MERGER, SPINOFF
    ratio = Column(Numeric(12, 6))  # 분할/합병 비율 (예: 2.0 = 1:2)
    effective_date = Column(Date, nullable=True)

    # 참고 정보
    report_name = Column(String(200))
    reference_doc = Column(String(50))  # 공시 번호 등

    # 데이터 거버넌스
    source_id = Column(String(20), ForeignKey("data_source.source_id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("data_load_batch.batch_id"))
    as_of_date = Column(Date, nullable=False)

    created_at = Column(DateTime, default=kst_now)

    __table_args__ = (
        Index('idx_action_ticker', 'ticker'),
        Index('idx_action_date', 'effective_date'),
        Index('idx_action_type', 'action_type'),
        UniqueConstraint('ticker', 'action_type', 'effective_date', 'reference_doc', 'source_id',
                        name='uq_corporate_action'),
    )

    def __repr__(self):
        return f"<CorporateAction {self.ticker} {self.action_type} {self.effective_date}>"


# ============================================================================
# Level 2: 시장 데이터 (KRX)
# ============================================================================

class InstitutionTrade(Base):
    """기관/외국인 매매 (KRX)"""
    __tablename__ = "institution_trade"

    trade_id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False)
    trade_date = Column(Date, nullable=False)

    # 기관 매매
    institution_buy = Column(BigInteger)  # 기관 매수 (주)
    institution_sell = Column(BigInteger)  # 기관 매도 (주)
    institution_net = Column(BigInteger)  # 기관 순매수

    # 외국인 매매
    foreign_buy = Column(BigInteger)
    foreign_sell = Column(BigInteger)
    foreign_net = Column(BigInteger)

    # 개인 매매
    individual_buy = Column(BigInteger)
    individual_sell = Column(BigInteger)
    individual_net = Column(BigInteger)

    # 외국인 보유
    foreign_holding_shares = Column(BigInteger)  # 외국인 보유 주식수
    foreign_holding_ratio = Column(Numeric(8, 4))  # 외국인 지분율 (%)

    # 데이터 거버넌스
    source_id = Column(String(20), ForeignKey("data_source.source_id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("data_load_batch.batch_id"))
    as_of_date = Column(Date, nullable=False)

    created_at = Column(DateTime, default=kst_now)

    __table_args__ = (
        UniqueConstraint('ticker', 'trade_date', 'source_id', name='uq_institution_trade'),
        Index('idx_inst_trade_ticker', 'ticker', 'trade_date'),
        Index('idx_inst_trade_date', 'trade_date'),
    )

    def __repr__(self):
        return f"<InstitutionTrade {self.ticker} {self.trade_date}>"


# ============================================================================
# Phase 11: 주식 일별 시세 (stocks_daily_prices DDL 기준)
# ============================================================================

class StocksDailyPrice(Base):
    """주식 일별 시세 (stocks_daily_prices 테이블)

    참조: db/ddl/phase11_stocks_daily_prices_ddl.sql
    - stocks_meta 테이블과 FK 관계
    - pykrx API를 통해 적재
    """
    __tablename__ = "stocks_daily_prices"

    code = Column(String(10), primary_key=True)  # 종목코드 (FK: stocks_meta.code)
    date = Column(Date, primary_key=True)  # 거래일

    # OHLCV
    open_price = Column(Numeric(18, 2))
    high_price = Column(Numeric(18, 2))
    low_price = Column(Numeric(18, 2))
    close_price = Column(Numeric(18, 2))
    volume = Column(BigInteger)

    # 등락률
    change_rate = Column(Numeric(8, 4))  # 전일 대비 등락률 (%)

    __table_args__ = (
        Index('idx_daily_prices_date', 'date'),
    )

    def __repr__(self):
        return f"<StocksDailyPrice {self.code} {self.date}: {self.close_price}>"


# ============================================================================
# Level 2: 채권 기본 정보 (FSC OpenAPI)
# ============================================================================

class BondBasicInfo(Base):
    """채권 기본 정보 (금융위원회 OpenAPI)

    데이터 출처: 금융위원회 채권기본정보 API (GetBondIssuInfoService)
    - isin_cd + bas_dt + source_id 복합키로 유일성 보장
    - 기존 bonds 테이블(교육용)과 독립 구조
    """
    __tablename__ = "bond_basic_info"

    bond_info_id = Column(Integer, primary_key=True, autoincrement=True)

    # 식별
    isin_cd = Column(String(12), nullable=False)  # ISIN 코드
    bas_dt = Column(String(8))  # API 조회 기준일 (YYYYMMDD)
    crno = Column(String(13))  # 법인등록번호

    # 종목
    isin_cd_nm = Column(String(200))  # 채권명
    scrs_itms_kcd = Column(String(4))  # 유가증권종목종류코드
    scrs_itms_kcd_nm = Column(String(100))  # 유가증권종목종류코드명
    bond_isur_nm = Column(String(200))  # 발행인명

    # 발행
    bond_issu_dt = Column(Date)  # 발행일
    bond_expr_dt = Column(Date)  # 만기일

    # 금액
    bond_issu_amt = Column(Numeric(22, 3))  # 발행금액
    bond_bal = Column(Numeric(22, 3))  # 잔액

    # 금리
    bond_srfc_inrt = Column(Numeric(15, 10))  # 표면이율
    irt_chng_dcd = Column(String(1))  # 금리변동구분: Y=변동, N=고정
    bond_int_tcd = Column(String(1))  # 이자유형코드
    int_pay_cycl_ctt = Column(String(100))  # 이자지급주기

    # 이표
    nxtm_copn_dt = Column(Date)  # 차기이표일
    rbf_copn_dt = Column(Date)  # 직전이표일

    # 보증/순위
    grn_dcd = Column(String(1))  # 보증구분코드
    bond_rnkn_dcd = Column(String(1))  # 순위구분코드

    # 신용등급
    kis_scrs_itms_kcd = Column(String(4))  # KIS 신용등급
    kbp_scrs_itms_kcd = Column(String(4))  # KBP 신용등급
    nice_scrs_itms_kcd = Column(String(4))  # NICE 신용등급
    fn_scrs_itms_kcd = Column(String(4))  # FN 신용등급

    # 모집/상장
    bond_offr_mcd = Column(String(2))  # 모집방법코드
    lstg_dt = Column(Date)  # 상장일

    # 특이
    prmnc_bond_yn = Column(String(1))  # 영구채권여부
    strips_psbl_yn = Column(String(1))  # 스트립스가능여부

    # 데이터 거버넌스
    source_id = Column(String(20), ForeignKey("data_source.source_id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("data_load_batch.batch_id"))
    as_of_date = Column(Date, nullable=False)  # 데이터 기준일

    created_at = Column(DateTime, default=kst_now)

    __table_args__ = (
        UniqueConstraint('isin_cd', 'bas_dt', 'source_id', name='uq_bond_basic_info'),
        Index('idx_bond_info_isin', 'isin_cd'),
        Index('idx_bond_info_isur', 'bond_isur_nm'),
        Index('idx_bond_info_expr_dt', 'bond_expr_dt'),
        Index('idx_bond_info_asof', 'as_of_date'),
    )

    def __repr__(self):
        return f"<BondBasicInfo {self.isin_cd} ({self.isin_cd_nm}) expr={self.bond_expr_dt}>"
