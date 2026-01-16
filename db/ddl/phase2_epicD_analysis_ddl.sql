-- =====================================================================
-- File: Foresto_Phase2_EpicD_Analysis_DDL.sql
-- Project: ForestoCompass
-- Phase: Phase 2 / Epic D (Performance Analysis)
--
-- 작성일: 2026-01-16
-- 목적:
--   Phase 2 Epic D 성과 분석 결과 저장용 테이블
--   * Phase 1 테이블은 절대 변경하지 않음
--   * 성과 분석 결과는 캐시 성격 → 별도 테이블 저장
--   * 동일 run + 동일 가정(rf, 연율화) → 동일 결과 재사용
--
-- 적용 DB: PostgreSQL
-- 스키마: foresto
-- =====================================================================

BEGIN;

SET search_path TO foresto;

-- =====================================================================
-- 1. analysis_result
-- =====================================================================
-- 시뮬레이션 실행(run_id) 기준 KPI 결과 캐시
-- =====================================================================

CREATE TABLE IF NOT EXISTS analysis_result (
    analysis_id             BIGSERIAL PRIMARY KEY,

    -- FK to simulation_run (Phase 1 테이블)
    simulation_run_id       BIGINT NOT NULL
                            REFERENCES simulation_run(run_id)
                            ON DELETE CASCADE,

    -- 계산 가정 파라미터
    rf_annual               NUMERIC(8,6) NOT NULL DEFAULT 0.0,
    annualization_factor    INT NOT NULL DEFAULT 252,

    -- KPI 결과 JSON
    -- 포함 키: cagr, volatility, sharpe, mdd, mdd_peak_date, mdd_trough_date,
    --         total_return, period_start, period_end, recovery_days (optional)
    metrics_json            JSONB NOT NULL,

    -- 메타데이터
    calculated_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE analysis_result IS
'성과 분석 결과 캐시 (Phase 2 / Epic D)';

COMMENT ON COLUMN analysis_result.simulation_run_id IS
'분석 대상 시뮬레이션 실행 ID (FK → simulation_run.run_id)';

COMMENT ON COLUMN analysis_result.rf_annual IS
'무위험 수익률 (연율화, 기본 0)';

COMMENT ON COLUMN analysis_result.annualization_factor IS
'연율화 계수 (거래일 기준, 기본 252)';

COMMENT ON COLUMN analysis_result.metrics_json IS
'CAGR, Volatility, Sharpe, MDD 등 KPI JSON';

-- 동일 run + 동일 가정이면 결과 1건 (캐시 키)
CREATE UNIQUE INDEX IF NOT EXISTS ux_analysis_result_run_params
    ON analysis_result (simulation_run_id, rf_annual, annualization_factor);

-- 조회 최적화
CREATE INDEX IF NOT EXISTS idx_analysis_result_run
    ON analysis_result (simulation_run_id);

-- =====================================================================
-- 2. 권한 정책
-- =====================================================================

REVOKE ALL ON analysis_result FROM PUBLIC;

GRANT SELECT, INSERT, UPDATE, DELETE
ON analysis_result
TO foresto;

GRANT SELECT
ON analysis_result
TO role_readonly;

COMMIT;

-- =====================================================================
-- 확인 쿼리
-- =====================================================================
-- SELECT analysis_id, simulation_run_id, rf_annual, annualization_factor,
--        metrics_json, calculated_at
--   FROM foresto.analysis_result
--  ORDER BY analysis_id DESC
--  LIMIT 10;
