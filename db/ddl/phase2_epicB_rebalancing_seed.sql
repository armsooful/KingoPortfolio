-- =====================================================================
-- File: Foresto_Phase2_EpicB_Rebalancing_Seed.sql
-- Project: ForestoCompass
-- Phase: Phase 2 / Epic B (Rebalancing Engine)
--
-- 작성일: 2026-01-16
-- 목적:
--   Phase 2 Epic B rebalancing_rule 초기 데이터(seed)
-- Notes:
--   - 기존 데이터가 있을 수 있으므로, rule_name 기준 UPSERT로 처리
--   - 운영에서는 effective_from/to, is_active 정책에 맞게 조정
--   - 사전 조건: DDL에서 ux_rebalancing_rule_name UNIQUE 인덱스 생성 필요
-- =====================================================================

BEGIN;
SET search_path TO foresto;

-- 1) PERIODIC / MONTHLY / 월초(첫 거래일) / 10bp
INSERT INTO rebalancing_rule (
    rule_name, rule_type, frequency, base_day_policy,
    drift_threshold, cost_rate, effective_from, effective_to, is_active
)
VALUES (
    'P2_PERIODIC_MONTHLY_FTD_10BP', 'PERIODIC', 'MONTHLY', 'FIRST_TRADING_DAY',
    NULL, 0.001, CURRENT_DATE, NULL, TRUE
)
ON CONFLICT (rule_name) DO UPDATE SET
    rule_type = EXCLUDED.rule_type,
    frequency = EXCLUDED.frequency,
    base_day_policy = EXCLUDED.base_day_policy,
    drift_threshold = EXCLUDED.drift_threshold,
    cost_rate = EXCLUDED.cost_rate,
    effective_from = EXCLUDED.effective_from,
    effective_to = EXCLUDED.effective_to,
    is_active = EXCLUDED.is_active,
    updated_at = CURRENT_TIMESTAMP;

-- 2) PERIODIC / QUARTERLY / 분기초(첫 거래일) / 10bp
INSERT INTO rebalancing_rule (
    rule_name, rule_type, frequency, base_day_policy,
    drift_threshold, cost_rate, effective_from, effective_to, is_active
)
VALUES (
    'P2_PERIODIC_QUARTERLY_FTD_10BP', 'PERIODIC', 'QUARTERLY', 'FIRST_TRADING_DAY',
    NULL, 0.001, CURRENT_DATE, NULL, TRUE
)
ON CONFLICT (rule_name) DO UPDATE SET
    rule_type = EXCLUDED.rule_type,
    frequency = EXCLUDED.frequency,
    base_day_policy = EXCLUDED.base_day_policy,
    drift_threshold = EXCLUDED.drift_threshold,
    cost_rate = EXCLUDED.cost_rate,
    effective_from = EXCLUDED.effective_from,
    effective_to = EXCLUDED.effective_to,
    is_active = EXCLUDED.is_active,
    updated_at = CURRENT_TIMESTAMP;

-- 3) DRIFT / threshold=5% / 10bp
INSERT INTO rebalancing_rule (
    rule_name, rule_type, frequency, base_day_policy,
    drift_threshold, cost_rate, effective_from, effective_to, is_active
)
VALUES (
    'P2_DRIFT_5PCT_10BP', 'DRIFT', NULL, 'FIRST_TRADING_DAY',
    0.05, 0.001, CURRENT_DATE, NULL, TRUE
)
ON CONFLICT (rule_name) DO UPDATE SET
    rule_type = EXCLUDED.rule_type,
    frequency = EXCLUDED.frequency,
    base_day_policy = EXCLUDED.base_day_policy,
    drift_threshold = EXCLUDED.drift_threshold,
    cost_rate = EXCLUDED.cost_rate,
    effective_from = EXCLUDED.effective_from,
    effective_to = EXCLUDED.effective_to,
    is_active = EXCLUDED.is_active,
    updated_at = CURRENT_TIMESTAMP;

-- 4) DRIFT / threshold=10% / 10bp
INSERT INTO rebalancing_rule (
    rule_name, rule_type, frequency, base_day_policy,
    drift_threshold, cost_rate, effective_from, effective_to, is_active
)
VALUES (
    'P2_DRIFT_10PCT_10BP', 'DRIFT', NULL, 'FIRST_TRADING_DAY',
    0.10, 0.001, CURRENT_DATE, NULL, TRUE
)
ON CONFLICT (rule_name) DO UPDATE SET
    rule_type = EXCLUDED.rule_type,
    frequency = EXCLUDED.frequency,
    base_day_policy = EXCLUDED.base_day_policy,
    drift_threshold = EXCLUDED.drift_threshold,
    cost_rate = EXCLUDED.cost_rate,
    effective_from = EXCLUDED.effective_from,
    effective_to = EXCLUDED.effective_to,
    is_active = EXCLUDED.is_active,
    updated_at = CURRENT_TIMESTAMP;

COMMIT;

-- =====================================================================
-- 확인 쿼리
-- =====================================================================
-- SELECT rule_id, rule_name, rule_type, frequency, base_day_policy,
--        drift_threshold, cost_rate, is_active
--   FROM foresto.rebalancing_rule
--  ORDER BY rule_id;
