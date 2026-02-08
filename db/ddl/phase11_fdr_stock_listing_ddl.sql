-- Phase 11: FinanceDataReader 종목 마스터 테이블
-- 대상: PostgreSQL

CREATE TABLE IF NOT EXISTS fdr_stock_listing (
    listing_id      BIGSERIAL PRIMARY KEY,
    ticker          VARCHAR(10) NOT NULL,
    name            VARCHAR(100) NOT NULL,
    market          VARCHAR(20) NOT NULL,
    sector          VARCHAR(100),
    industry        VARCHAR(100),
    listing_date    DATE,
    shares          BIGINT,
    par_value       NUMERIC(18, 2),
    as_of_date      DATE NOT NULL,
    source_id       VARCHAR(20) NOT NULL REFERENCES data_source(source_id),
    batch_id        INTEGER REFERENCES data_load_batch(batch_id),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_fdr_stock_listing
    ON fdr_stock_listing (ticker, as_of_date, source_id);

CREATE INDEX IF NOT EXISTS idx_fdr_stock_ticker
    ON fdr_stock_listing (ticker);

CREATE INDEX IF NOT EXISTS idx_fdr_stock_market
    ON fdr_stock_listing (market);

CREATE INDEX IF NOT EXISTS idx_fdr_stock_asof
    ON fdr_stock_listing (as_of_date);
