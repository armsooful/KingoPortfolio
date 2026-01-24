# 실 데이터 적재용 DDL 설계

작성일: 2026-01-24
버전: v1.0

---

## 1. 설계 원칙

### 1.1 데이터 거버넌스

| 원칙 | 설명 |
|------|------|
| **출처 추적** | 모든 데이터는 source, source_date 기록 |
| **배치 추적** | 어떤 배치 작업으로 적재되었는지 추적 |
| **기준일 명시** | as_of_date로 데이터 시점 명확화 |
| **품질 플래그** | is_verified, quality_score로 품질 표시 |
| **불변성** | 한번 적재된 데이터는 수정하지 않음 (새 레코드 추가) |

### 1.2 제약 조건

- **실시간 데이터 금지**: 장중 데이터, 실시간 시세 불가
- **자동 갱신 금지**: 스케줄러에 의한 자동 적재 불가
- **기준일 필수**: 모든 데이터에 명시적 기준일 필요

---

## 2. 테이블 설계

### 2.1 마스터 데이터

#### 2.1.1 data_source (데이터 소스 마스터)

```sql
CREATE TABLE data_source (
    source_id       VARCHAR(20)  PRIMARY KEY,      -- 'KRX', 'NAVER', 'YAHOO'
    source_name     VARCHAR(100) NOT NULL,
    source_type     VARCHAR(20)  NOT NULL,          -- 'EXCHANGE', 'VENDOR', 'CALCULATED'
    base_url        VARCHAR(500),
    api_type        VARCHAR(20),                    -- 'REST', 'SCRAPING', 'FILE'
    update_frequency VARCHAR(20),                   -- 'DAILY', 'REALTIME', 'MANUAL'
    license_type    VARCHAR(50),                    -- 'PUBLIC', 'COMMERCIAL', 'INTERNAL'
    description     TEXT,
    is_active       BOOLEAN      DEFAULT TRUE,
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
```

#### 2.1.2 data_load_batch (배치 적재 이력)

```sql
CREATE TABLE data_load_batch (
    batch_id        SERIAL       PRIMARY KEY,
    batch_type      VARCHAR(30)  NOT NULL,          -- 'PRICE', 'FUNDAMENTAL', 'INDEX'
    source_id       VARCHAR(20)  NOT NULL REFERENCES data_source(source_id),
    as_of_date      DATE         NOT NULL,          -- 데이터 기준일
    target_start    DATE         NOT NULL,          -- 적재 대상 기간 시작
    target_end      DATE         NOT NULL,          -- 적재 대상 기간 종료
    status          VARCHAR(20)  NOT NULL DEFAULT 'PENDING', -- 'PENDING','RUNNING','SUCCESS','FAILED'

    -- 처리 결과
    total_records   INTEGER      DEFAULT 0,
    success_records INTEGER      DEFAULT 0,
    failed_records  INTEGER      DEFAULT 0,
    skipped_records INTEGER      DEFAULT 0,

    -- 품질 메트릭
    quality_score   DECIMAL(5,2),                   -- 0.00 ~ 100.00
    null_ratio      DECIMAL(5,4),                   -- NULL 비율
    outlier_ratio   DECIMAL(5,4),                   -- 이상치 비율

    -- 운영 정보
    operator_id     VARCHAR(50),
    operator_reason TEXT,
    error_message   TEXT,

    started_at      TIMESTAMP,
    completed_at    TIMESTAMP,
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_data_load_batch_asof ON data_load_batch(as_of_date);
CREATE INDEX idx_data_load_batch_status ON data_load_batch(status);
CREATE INDEX idx_data_load_batch_source ON data_load_batch(source_id, batch_type);
```

---

### 2.2 가격 데이터

#### 2.2.1 stock_price_daily (주식 일별 시세)

```sql
CREATE TABLE stock_price_daily (
    price_id        BIGSERIAL    PRIMARY KEY,
    ticker          VARCHAR(10)  NOT NULL,          -- '005930'
    trade_date      DATE         NOT NULL,          -- 거래일

    -- OHLCV
    open_price      DECIMAL(18,2) NOT NULL,
    high_price      DECIMAL(18,2) NOT NULL,
    low_price       DECIMAL(18,2) NOT NULL,
    close_price     DECIMAL(18,2) NOT NULL,
    volume          BIGINT       NOT NULL,

    -- 추가 지표
    adj_close_price DECIMAL(18,2),                  -- 수정 종가
    market_cap      BIGINT,                         -- 시가총액 (원)
    trading_value   BIGINT,                         -- 거래대금 (원)
    shares_outstanding BIGINT,                      -- 발행주식수

    -- 전일 대비
    prev_close      DECIMAL(18,2),
    price_change    DECIMAL(18,2),
    change_rate     DECIMAL(8,4),                   -- 등락률 (%)

    -- 데이터 거버넌스
    source_id       VARCHAR(20)  NOT NULL REFERENCES data_source(source_id),
    batch_id        INTEGER      REFERENCES data_load_batch(batch_id),
    as_of_date      DATE         NOT NULL,          -- 데이터 기준일

    -- 품질
    is_verified     BOOLEAN      DEFAULT FALSE,
    quality_flag    VARCHAR(10)  DEFAULT 'NORMAL',  -- 'NORMAL','ADJUSTED','ESTIMATED'

    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_stock_price_daily UNIQUE (ticker, trade_date, source_id)
);

-- 인덱스 전략
CREATE INDEX idx_stock_price_ticker_date ON stock_price_daily(ticker, trade_date DESC);
CREATE INDEX idx_stock_price_date ON stock_price_daily(trade_date);
CREATE INDEX idx_stock_price_asof ON stock_price_daily(as_of_date);
CREATE INDEX idx_stock_price_batch ON stock_price_daily(batch_id);

-- 파티션 (연도별) - PostgreSQL 12+
-- CREATE TABLE stock_price_daily_2024 PARTITION OF stock_price_daily
--     FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

#### 2.2.2 index_price_daily (지수 일별 시세)

```sql
CREATE TABLE index_price_daily (
    price_id        BIGSERIAL    PRIMARY KEY,
    index_code      VARCHAR(20)  NOT NULL,          -- 'KOSPI', 'KOSDAQ', 'KS200'
    trade_date      DATE         NOT NULL,

    -- OHLC
    open_price      DECIMAL(18,4) NOT NULL,
    high_price      DECIMAL(18,4) NOT NULL,
    low_price       DECIMAL(18,4) NOT NULL,
    close_price     DECIMAL(18,4) NOT NULL,

    -- 추가 지표
    volume          BIGINT,                         -- 거래량 (주)
    trading_value   BIGINT,                         -- 거래대금 (백만원)
    market_cap      BIGINT,                         -- 시가총액 (억원)

    -- 전일 대비
    prev_close      DECIMAL(18,4),
    price_change    DECIMAL(18,4),
    change_rate     DECIMAL(8,4),

    -- 데이터 거버넌스
    source_id       VARCHAR(20)  NOT NULL REFERENCES data_source(source_id),
    batch_id        INTEGER      REFERENCES data_load_batch(batch_id),
    as_of_date      DATE         NOT NULL,

    is_verified     BOOLEAN      DEFAULT FALSE,
    quality_flag    VARCHAR(10)  DEFAULT 'NORMAL',

    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_index_price_daily UNIQUE (index_code, trade_date, source_id)
);

CREATE INDEX idx_index_price_code_date ON index_price_daily(index_code, trade_date DESC);
CREATE INDEX idx_index_price_date ON index_price_daily(trade_date);
```

---

### 2.3 기본 정보

#### 2.3.1 stock_info (종목 기본 정보)

```sql
CREATE TABLE stock_info (
    info_id         SERIAL       PRIMARY KEY,
    ticker          VARCHAR(10)  NOT NULL,
    as_of_date      DATE         NOT NULL,          -- 정보 기준일

    -- 기본 정보
    stock_name      VARCHAR(100) NOT NULL,
    stock_name_en   VARCHAR(100),
    market_type     VARCHAR(20)  NOT NULL,          -- 'KOSPI', 'KOSDAQ', 'KONEX'
    sector_code     VARCHAR(10),
    sector_name     VARCHAR(50),
    industry_code   VARCHAR(10),
    industry_name   VARCHAR(50),

    -- 상장 정보
    listing_date    DATE,
    fiscal_month    INTEGER,                        -- 결산월 (12, 3, 6 등)
    ceo_name        VARCHAR(100),
    headquarters    VARCHAR(200),
    website         VARCHAR(300),

    -- 주식 정보
    face_value      INTEGER,                        -- 액면가
    shares_listed   BIGINT,                         -- 상장주식수
    shares_outstanding BIGINT,                      -- 발행주식수

    -- 데이터 거버넌스
    source_id       VARCHAR(20)  NOT NULL REFERENCES data_source(source_id),
    batch_id        INTEGER      REFERENCES data_load_batch(batch_id),
    is_active       BOOLEAN      DEFAULT TRUE,

    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_stock_info UNIQUE (ticker, as_of_date, source_id)
);

CREATE INDEX idx_stock_info_ticker ON stock_info(ticker);
CREATE INDEX idx_stock_info_market ON stock_info(market_type);
CREATE INDEX idx_stock_info_asof ON stock_info(as_of_date DESC);
```

---

### 2.4 뷰 정의

#### 2.4.1 v_latest_stock_price (최신 주가 뷰)

```sql
CREATE VIEW v_latest_stock_price AS
SELECT DISTINCT ON (ticker)
    ticker,
    trade_date,
    open_price,
    high_price,
    low_price,
    close_price,
    volume,
    adj_close_price,
    market_cap,
    change_rate,
    source_id,
    as_of_date
FROM stock_price_daily
WHERE is_verified = TRUE OR quality_flag = 'NORMAL'
ORDER BY ticker, trade_date DESC;
```

#### 2.4.2 v_stock_with_info (종목 정보 포함 뷰)

```sql
CREATE VIEW v_stock_with_info AS
SELECT
    p.ticker,
    i.stock_name,
    i.market_type,
    i.sector_name,
    p.trade_date,
    p.close_price,
    p.volume,
    p.market_cap,
    p.change_rate,
    p.source_id,
    p.as_of_date
FROM v_latest_stock_price p
LEFT JOIN LATERAL (
    SELECT *
    FROM stock_info
    WHERE ticker = p.ticker
    ORDER BY as_of_date DESC
    LIMIT 1
) i ON TRUE;
```

---

## 3. 데이터 품질 규칙

### 3.1 검증 규칙

| 규칙 ID | 대상 | 조건 | 심각도 |
|---------|------|------|--------|
| DQ-001 | close_price | > 0 | ERROR |
| DQ-002 | volume | >= 0 | ERROR |
| DQ-003 | high_price | >= low_price | ERROR |
| DQ-004 | high_price | >= open_price AND >= close_price | WARNING |
| DQ-005 | low_price | <= open_price AND <= close_price | WARNING |
| DQ-006 | change_rate | ABS(change_rate) <= 30 | WARNING |
| DQ-007 | market_cap | > 0 (if not NULL) | WARNING |

### 3.2 이상치 탐지

```sql
-- 이상치 탐지 쿼리 예시
SELECT ticker, trade_date, close_price, change_rate
FROM stock_price_daily
WHERE ABS(change_rate) > 15.0  -- 상한가/하한가 기준
   OR close_price <= 0
   OR volume < 0;
```

---

## 4. 초기 데이터 소스 등록

```sql
-- 데이터 소스 초기화
INSERT INTO data_source (source_id, source_name, source_type, api_type, update_frequency, license_type, description)
VALUES
    ('KRX', '한국거래소', 'EXCHANGE', 'FILE', 'DAILY', 'PUBLIC', 'KRX 정보데이터시스템'),
    ('PYKRX', 'PyKRX', 'VENDOR', 'REST', 'DAILY', 'PUBLIC', 'PyKRX 라이브러리 (KRX 데이터)'),
    ('NAVER', '네이버 금융', 'VENDOR', 'SCRAPING', 'REALTIME', 'PUBLIC', '네이버 금융 시세'),
    ('YAHOO', 'Yahoo Finance', 'VENDOR', 'REST', 'DAILY', 'PUBLIC', 'Yahoo Finance API'),
    ('INTERNAL', '내부 계산', 'CALCULATED', 'INTERNAL', 'MANUAL', 'INTERNAL', '내부 계산 데이터');
```

---

## 5. 마이그레이션 계획

### 5.1 기존 테이블 매핑

| 기존 테이블 | 신규 테이블 | 비고 |
|------------|------------|------|
| krx_timeseries | stock_price_daily | source_id='PYKRX' 추가 |
| stocks | stock_info | as_of_date 추가 |

### 5.2 마이그레이션 SQL

```sql
-- krx_timeseries → stock_price_daily 마이그레이션
INSERT INTO stock_price_daily (
    ticker, trade_date,
    open_price, high_price, low_price, close_price, volume,
    source_id, as_of_date, is_verified, quality_flag
)
SELECT
    ticker, date,
    open, high, low, close, volume,
    'PYKRX', CURRENT_DATE, FALSE, 'MIGRATED'
FROM krx_timeseries
ON CONFLICT (ticker, trade_date, source_id) DO NOTHING;
```

---

## 6. 인덱스 전략

### 6.1 주요 쿼리 패턴

| 패턴 | 쿼리 예시 | 권장 인덱스 |
|------|----------|------------|
| 종목별 기간 조회 | ticker='005930' AND trade_date BETWEEN ... | (ticker, trade_date) |
| 일자별 전체 조회 | trade_date = '2024-01-15' | (trade_date) |
| 기준일 기반 조회 | as_of_date = '2024-01-15' | (as_of_date) |
| 배치별 조회 | batch_id = 123 | (batch_id) |

### 6.2 파티션 전략 (대용량 시)

- **연도별 파티션**: `stock_price_daily_YYYY`
- **월별 파티션** (고빈도 조회 시): `stock_price_daily_YYYYMM`

---

## 7. 버전 이력

| 버전 | 일자 | 변경 내용 |
|------|------|----------|
| v1.0 | 2026-01-24 | 최초 작성 |
