-- Phase 11: stocks_daily_factors 테이블
-- 대상: PostgreSQL

CREATE TABLE IF NOT EXISTS stocks_daily_factors (
    code                VARCHAR(10) REFERENCES stocks_meta(code),
    date                DATE NOT NULL,
    market_cap          BIGINT,
    per                 NUMERIC,
    pbr                 NUMERIC,
    dividend_yield      NUMERIC,
    foreign_net_buy     BIGINT,
    institution_net_buy BIGINT,
    individual_net_buy  BIGINT,
    foreign_hold_ratio  NUMERIC,
    PRIMARY KEY (code, date)
);

CREATE INDEX IF NOT EXISTS idx_daily_factors_date ON stocks_daily_factors(date);
