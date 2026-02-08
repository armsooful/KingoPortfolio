-- Phase 11: stocks_meta 테이블
-- 대상: PostgreSQL

CREATE TABLE IF NOT EXISTS stocks_meta (
    code            VARCHAR(10) PRIMARY KEY, -- 종목코드 (예: 005930)
    name            VARCHAR(100) NOT NULL,   -- 종목명
    market          VARCHAR(20),             -- KOSPI, KOSDAQ, KONEX
    sector          VARCHAR(100),            -- 한국표준산업분류 (fdr/krx 기반)
    industry        VARCHAR(255),            -- 주요 제품 및 사업 상세
    listing_date    DATE,                    -- 상장일
    delisting_date  DATE,                    -- 상장폐지일 (상장 중이면 NULL)
    is_active       BOOLEAN DEFAULT TRUE,    -- 현재 상장 여부 (상장폐지 종목은 FALSE)
    updated_at      TIMESTAMP DEFAULT NOW()  -- 메타데이터 최종 업데이트 시점
);

CREATE INDEX IF NOT EXISTS idx_stocks_meta_name ON stocks_meta(name);
CREATE INDEX IF NOT EXISTS idx_stocks_meta_is_active ON stocks_meta(is_active);
