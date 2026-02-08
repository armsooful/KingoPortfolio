-- =====================================================================
-- File: phase11_corporate_action_ddl.sql
-- Project: ForestoCompass
-- Phase: Phase 11 / Data Extension
--
-- 작성일: 2026-01-28
-- 목적:
--   기업 액션(분할/합병 등) 이력 저장 테이블 추가
--
-- 적용 DB: PostgreSQL
-- 스키마: foresto
-- =====================================================================

BEGIN;

SET search_path TO foresto;

CREATE TABLE IF NOT EXISTS corporate_action (
    action_id       BIGSERIAL PRIMARY KEY,
    ticker          VARCHAR(10) NOT NULL,
    action_type     VARCHAR(20) NOT NULL, -- SPLIT, REVERSE_SPLIT, MERGER, SPINOFF
    ratio           NUMERIC(12,6),
    effective_date  DATE,
    report_name     VARCHAR(200),
    reference_doc   VARCHAR(50),

    source_id       VARCHAR(20) NOT NULL REFERENCES data_source(source_id),
    batch_id        INTEGER REFERENCES data_load_batch(batch_id),
    as_of_date      DATE NOT NULL,

    created_at      TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_action_ticker ON corporate_action(ticker);
CREATE INDEX IF NOT EXISTS idx_action_date ON corporate_action(effective_date);
CREATE INDEX IF NOT EXISTS idx_action_type ON corporate_action(action_type);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_corporate_action'
    ) THEN
        ALTER TABLE corporate_action
            ADD CONSTRAINT uq_corporate_action
            UNIQUE (ticker, action_type, effective_date, reference_doc, source_id);
    END IF;
END $$;

COMMIT;
