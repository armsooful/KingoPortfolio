-- =============================================================================
-- Phase 3-C / Epic C-3: Performance Analytics DDL
-- 생성일: 2026-01-18
-- 목적: LIVE/SIM/BACK 성과 저장 및 버전/벤치마크 관리
-- 대상 DB: PostgreSQL
-- =============================================================================

BEGIN;

SET search_path TO foresto;

-- -----------------------------------------------------------------------------
-- 1. 성과 결과 (불변)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS performance_result (
    performance_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    performance_type   VARCHAR(10) NOT NULL,              -- LIVE/SIM/BACK
    entity_type        VARCHAR(20) NOT NULL,              -- PORTFOLIO/ACCOUNT/ASSET_CLASS
    entity_id          VARCHAR(100) NOT NULL,
    period_type        VARCHAR(10) NOT NULL,              -- DAILY/MONTHLY/CUMULATIVE
    period_start       DATE NOT NULL,
    period_end         DATE NOT NULL,

    -- 주요 지표
    period_return      NUMERIC(12,6),
    cumulative_return  NUMERIC(12,6),
    annualized_return  NUMERIC(12,6),
    volatility         NUMERIC(12,6),
    mdd                NUMERIC(12,6),
    sharpe_ratio       NUMERIC(12,6),
    sortino_ratio      NUMERIC(12,6),

    -- 참조 및 재현성
    execution_id       UUID REFERENCES batch_execution(execution_id),
    snapshot_ids       JSONB NOT NULL DEFAULT '[]'::JSONB,
    result_version_id  BIGINT REFERENCES result_version(version_id),
    calc_params        JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_performance_entity ON performance_result(entity_type, entity_id);
CREATE INDEX idx_performance_type ON performance_result(performance_type, period_type);
CREATE INDEX idx_performance_period ON performance_result(period_start, period_end);

COMMENT ON TABLE performance_result IS '성과 분석 결과 (불변)';

-- -----------------------------------------------------------------------------
-- 2. 성과 근거 (산식/기준)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS performance_basis (
    basis_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    performance_id     UUID NOT NULL REFERENCES performance_result(performance_id) ON DELETE CASCADE,
    price_basis        VARCHAR(20) NOT NULL,              -- CLOSE/LAST_VALID
    include_fee        BOOLEAN NOT NULL DEFAULT TRUE,
    include_tax        BOOLEAN NOT NULL DEFAULT FALSE,
    include_dividend   BOOLEAN NOT NULL DEFAULT FALSE,
    fx_snapshot_id     UUID REFERENCES data_snapshot(snapshot_id),
    notes              TEXT,
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_performance_basis_perf ON performance_basis(performance_id);

COMMENT ON TABLE performance_basis IS '성과 산출 근거';

-- -----------------------------------------------------------------------------
-- 3. 벤치마크 결과
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS benchmark_result (
    benchmark_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    performance_id     UUID NOT NULL REFERENCES performance_result(performance_id) ON DELETE CASCADE,
    benchmark_type     VARCHAR(20) NOT NULL,              -- INDEX/MIX/CASH
    benchmark_code     VARCHAR(50) NOT NULL,              -- KOSPI/S&P500 등
    benchmark_return   NUMERIC(12,6),
    excess_return      NUMERIC(12,6),
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_benchmark_perf ON benchmark_result(performance_id);

COMMENT ON TABLE benchmark_result IS '성과 벤치마크 비교 결과';

-- -----------------------------------------------------------------------------
-- 4. 사용자 노출용 요약 (LIVE 전용)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS performance_public_view (
    public_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    performance_id     UUID NOT NULL REFERENCES performance_result(performance_id) ON DELETE CASCADE,
    headline_json      JSONB NOT NULL DEFAULT '{}'::JSONB,
    disclaimer_text    TEXT NOT NULL,
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE performance_public_view IS '사용자 노출용 성과 요약 (LIVE 전용)';

COMMIT;
