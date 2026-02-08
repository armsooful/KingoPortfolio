-- Phase 11: stocks_daily_prices 테이블
-- 대상: PostgreSQL

CREATE TABLE IF NOT EXISTS stocks_daily_prices (
    code            VARCHAR(10) REFERENCES stocks_meta(code),
    date            DATE NOT NULL,
    open_price      NUMERIC,
    high_price      NUMERIC,
    low_price       NUMERIC,
    close_price     NUMERIC,
    volume          BIGINT,
    change_rate     NUMERIC,
    PRIMARY KEY (code, date)
);

CREATE INDEX IF NOT EXISTS idx_daily_prices_date ON stocks_daily_prices(date);
