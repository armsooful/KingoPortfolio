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
    """배당 이력 (DART)"""
    __tablename__ = "dividend_history"

    dividend_id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False)
    fiscal_year = Column(Integer, nullable=False)

    # DART 원본 필드
    rcept_no = Column(String(14))  # 접수번호
    corp_cls = Column(String(1))  # 법인구분
    corp_code = Column(String(8))
    corp_name = Column(String(100))
    se = Column(String(200))  # 구분
    stock_knd = Column(String(50))  # 주식 종류
    thstrm = Column(Numeric(18, 2))  # 당기
    frmtrm = Column(Numeric(18, 2))  # 전기
    lwfr = Column(Numeric(18, 2))  # 전전기
    stlm_dt = Column(Date)  # 결산기준일

    # 배당 정보
    dividend_type = Column(String(20), nullable=False)  # 'CASH', 'STOCK', 'INTERIM'
    dividend_per_share = Column(Numeric(18, 2))  # 주당 배당금
    dividend_rate = Column(Numeric(8, 4))  # 배당률 (%)
    dividend_yield = Column(Numeric(8, 4))  # 배당수익률 (%)

    # 배당 일정
    record_date = Column(Date)  # 배당 기준일
    payment_date = Column(Date)  # 배당 지급일
    ex_dividend_date = Column(Date)  # 배당락일

    # 데이터 거버넌스
    source_id = Column(String(20), ForeignKey("data_source.source_id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("data_load_batch.batch_id"))
    as_of_date = Column(Date, nullable=False)

    created_at = Column(DateTime, default=kst_now)

    __table_args__ = (
        UniqueConstraint('ticker', 'fiscal_year', 'dividend_type', 'source_id',
                        name='uq_dividend_history'),
        Index('idx_dividend_ticker', 'ticker'),
        Index('idx_dividend_year', 'fiscal_year'),
        Index('idx_dividend_rcept', 'rcept_no'),
    )

    def __repr__(self):
        return f"<DividendHistory {self.ticker} {self.fiscal_year} {self.dividend_type}>"


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
