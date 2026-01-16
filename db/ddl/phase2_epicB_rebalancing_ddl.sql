-- =====================================================================
-- File: Foresto_Phase2_EpicB_Rebalancing_DDL.sql
-- Project: ForestoCompass
-- Phase: Phase 2 / Epic B (Rebalancing Engine)
--
-- 작성일: 2026-01-16
-- 목적:
--   Phase 2 리밸런싱 엔진 구현을 위한 DB 확장 DDL
--   * Phase 1 테이블은 절대 변경하지 않음
--   * 리밸런싱 규칙 정의와 실행 로그를 분리
--   * 모든 판단 근거를 DB에 기록하여 재현성/설명 가능성 확보
--
-- 적용 DB: PostgreSQL
-- 스키마: foresto
-- =====================================================================

BEGIN;

SET search_path TO foresto;

-- =====================================================================
-- 1. rebalancing_rule
-- =====================================================================

CREATE TABLE IF NOT EXISTS rebalancing_rule (
    rule_id            SERIAL PRIMARY KEY,
    rule_name          VARCHAR(64) NOT NULL,
    rule_type          VARCHAR(16) NOT NULL
                       CHECK (rule_type IN ('PERIODIC', 'DRIFT')),
    frequency          VARCHAR(16)
                       CHECK (frequency IN ('MONTHLY', 'QUARTERLY')),
    base_day_policy    VARCHAR(24) NOT NULL DEFAULT 'FIRST_TRADING_DAY'
                       CHECK (base_day_policy IN ('FIRST_TRADING_DAY', 'LAST_TRADING_DAY')),
    drift_threshold    NUMERIC(8,6)
                       CHECK (drift_threshold > 0 AND drift_threshold < 1),
    cost_rate          NUMERIC(8,6) NOT NULL DEFAULT 0.001
                       CHECK (cost_rate >= 0 AND cost_rate <= 0.02),
    effective_from     DATE NOT NULL DEFAULT CURRENT_DATE,
    effective_to       DATE,
    is_active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE rebalancing_rule IS
'리밸런싱 규칙 정의 테이블 (Phase 2 / Epic B)';

CREATE INDEX IF NOT EXISTS idx_rebalancing_rule_active
    ON rebalancing_rule (is_active);

-- P2-B1: Seed SQL UPSERT를 위한 UNIQUE 인덱스
CREATE UNIQUE INDEX IF NOT EXISTS ux_rebalancing_rule_name
    ON rebalancing_rule (rule_name);

-- =====================================================================
-- 2. rebalancing_event
-- =====================================================================

CREATE TABLE IF NOT EXISTS rebalancing_event (
    event_id           BIGSERIAL PRIMARY KEY,
    simulation_run_id  BIGINT NOT NULL
                       REFERENCES simulation_run(run_id)
                       ON DELETE CASCADE,
    rule_id            INT NOT NULL
                       REFERENCES rebalancing_rule(rule_id),
    event_date         DATE NOT NULL,
    trigger_type       VARCHAR(16) NOT NULL
                       CHECK (trigger_type IN ('PERIODIC', 'DRIFT')),
    trigger_detail     VARCHAR(64),
    before_weights     JSONB NOT NULL,
    after_weights      JSONB NOT NULL,
    turnover           NUMERIC(12,8) NOT NULL
                       CHECK (turnover >= 0),
    cost_rate          NUMERIC(8,6) NOT NULL,
    cost_amount        NUMERIC(18,8),
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE rebalancing_event IS
'리밸런싱 발생 로그 테이블 (Phase 2 / Epic B)';

CREATE INDEX IF NOT EXISTS idx_rebal_event_run_date
    ON rebalancing_event (simulation_run_id, event_date);

CREATE INDEX IF NOT EXISTS idx_rebal_event_rule
    ON rebalancing_event (rule_id);

-- =====================================================================
-- 3. rebalancing_cost_model (옵션)
-- =====================================================================

CREATE TABLE IF NOT EXISTS rebalancing_cost_model (
    model_id       SERIAL PRIMARY KEY,
    model_name     VARCHAR(64) NOT NULL,
    model_type     VARCHAR(32) NOT NULL DEFAULT 'FIXED_RATE',
    description    TEXT,
    param_json     JSONB DEFAULT '{}'::JSONB,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE rebalancing_cost_model IS
'리밸런싱 비용 모델 정의 (확장 대비용)';

-- =====================================================================
-- 4. 권한 정책
-- =====================================================================

REVOKE ALL ON
    rebalancing_rule,
    rebalancing_event,
    rebalancing_cost_model
FROM PUBLIC;

GRANT SELECT, INSERT, UPDATE, DELETE
ON rebalancing_rule, rebalancing_event
TO foresto;

GRANT SELECT
ON rebalancing_rule, rebalancing_event
TO role_readonly;

COMMIT;
