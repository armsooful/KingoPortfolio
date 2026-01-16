-- =============================================================================
-- Foresto Phase 2 DDL - 리밸런싱 엔진 (Epic B)
-- 작성일: 2026-01-16
-- PostgreSQL 14+ 호환
-- =============================================================================

-- 트랜잭션 시작
BEGIN;

-- =============================================================================
-- 1. 리밸런싱 규칙 테이블
-- =============================================================================

-- 1.1 리밸런싱 규칙 정의
CREATE TABLE IF NOT EXISTS rebalancing_rule (
    rule_id             BIGSERIAL       PRIMARY KEY,
    rule_name           VARCHAR(100)    NOT NULL,
    description         TEXT,

    -- 리밸런싱 타입 (PERIODIC / DRIFT / HYBRID)
    rebalance_type      VARCHAR(20)     NOT NULL,

    -- PERIODIC 설정
    frequency           VARCHAR(10),                    -- 'MONTHLY', 'QUARTERLY', NULL
    periodic_timing     VARCHAR(20)     DEFAULT 'START', -- 'START' (월초/분기초), 'END' (월말/분기말)

    -- DRIFT 설정
    drift_threshold     NUMERIC(5,4),                   -- 0.0001 ~ 0.9999 (예: 0.05 = 5%)

    -- 비용 모델 설정
    cost_rate           NUMERIC(6,5)    DEFAULT 0.00100, -- 기본 10bp (0.001)

    -- 유효 기간
    effective_from      DATE            NOT NULL DEFAULT CURRENT_DATE,
    effective_to        DATE,                            -- NULL = 현재 유효

    -- 메타데이터
    is_active           BOOLEAN         DEFAULT TRUE,
    created_at          TIMESTAMPTZ     DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     DEFAULT NOW(),

    -- 검증 제약조건
    CONSTRAINT chk_rebalance_type CHECK (rebalance_type IN ('PERIODIC', 'DRIFT', 'HYBRID')),
    CONSTRAINT chk_frequency CHECK (frequency IS NULL OR frequency IN ('MONTHLY', 'QUARTERLY')),
    CONSTRAINT chk_periodic_timing CHECK (periodic_timing IN ('START', 'END')),
    CONSTRAINT chk_drift_threshold CHECK (drift_threshold IS NULL OR (drift_threshold >= 0.001 AND drift_threshold <= 0.5)),
    CONSTRAINT chk_cost_rate CHECK (cost_rate >= 0 AND cost_rate <= 0.02),
    CONSTRAINT chk_effective_range CHECK (effective_to IS NULL OR effective_to > effective_from),
    -- PERIODIC일 때 frequency 필수, DRIFT일 때 threshold 필수
    CONSTRAINT chk_periodic_requires_freq CHECK (
        rebalance_type != 'PERIODIC' OR frequency IS NOT NULL
    ),
    CONSTRAINT chk_drift_requires_threshold CHECK (
        rebalance_type != 'DRIFT' OR drift_threshold IS NOT NULL
    ),
    CONSTRAINT chk_hybrid_requires_both CHECK (
        rebalance_type != 'HYBRID' OR (frequency IS NOT NULL AND drift_threshold IS NOT NULL)
    )
);

COMMENT ON TABLE rebalancing_rule IS 'Phase 2: 리밸런싱 규칙 정의';
COMMENT ON COLUMN rebalancing_rule.rebalance_type IS 'PERIODIC=정기, DRIFT=편차기반, HYBRID=둘다';
COMMENT ON COLUMN rebalancing_rule.frequency IS '정기 리밸런싱 주기 (MONTHLY/QUARTERLY)';
COMMENT ON COLUMN rebalancing_rule.drift_threshold IS 'Drift 임계치 (예: 0.05=5%)';
COMMENT ON COLUMN rebalancing_rule.cost_rate IS '거래비용률 (기본 0.001=10bp)';
COMMENT ON COLUMN rebalancing_rule.periodic_timing IS 'START=월초/분기초, END=월말/분기말';

CREATE INDEX idx_rebalancing_rule_type ON rebalancing_rule(rebalance_type);
CREATE INDEX idx_rebalancing_rule_active ON rebalancing_rule(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_rebalancing_rule_effective ON rebalancing_rule(effective_from, effective_to);


-- =============================================================================
-- 2. 리밸런싱 이벤트 테이블
-- =============================================================================

-- 2.1 리밸런싱 이벤트 로그
CREATE TABLE IF NOT EXISTS rebalancing_event (
    event_id            BIGSERIAL       PRIMARY KEY,
    run_id              BIGINT          NOT NULL,   -- simulation_run.run_id 참조
    rule_id             BIGINT,                     -- rebalancing_rule.rule_id 참조 (NULL 허용)

    -- 이벤트 정보
    event_date          DATE            NOT NULL,
    event_order         INTEGER         DEFAULT 1,  -- 동일 run 내 순서

    -- 트리거 정보
    trigger_type        VARCHAR(20)     NOT NULL,   -- 'PERIODIC', 'DRIFT'
    trigger_detail      VARCHAR(100),               -- 예: 'MONTHLY', 'DRIFT>=0.05'

    -- 비중 정보 (JSON)
    before_weights      JSONB           NOT NULL,   -- {"EQUITY": 0.65, "BOND": 0.30, "CASH": 0.05}
    after_weights       JSONB           NOT NULL,   -- {"EQUITY": 0.60, "BOND": 0.30, "CASH": 0.10}

    -- 거래 정보
    turnover            NUMERIC(8,6)    NOT NULL,   -- 회전율 (0~1)
    cost_rate           NUMERIC(6,5)    NOT NULL,   -- 적용된 비용률
    cost_amount         NUMERIC(18,4),              -- 비용 금액 (NAV 기준)
    cost_factor         NUMERIC(10,8),              -- 비용 팩터 (1 - turnover * cost_rate)

    -- NAV 정보
    nav_before          NUMERIC(18,4),              -- 리밸런싱 전 NAV
    nav_after           NUMERIC(18,4),              -- 리밸런싱 후 NAV

    -- 메타데이터
    created_at          TIMESTAMPTZ     DEFAULT NOW(),

    -- 검증 제약조건
    CONSTRAINT chk_trigger_type CHECK (trigger_type IN ('PERIODIC', 'DRIFT')),
    CONSTRAINT chk_turnover CHECK (turnover >= 0 AND turnover <= 1),
    CONSTRAINT chk_cost_factor CHECK (cost_factor IS NULL OR (cost_factor > 0 AND cost_factor <= 1))
);

COMMENT ON TABLE rebalancing_event IS 'Phase 2: 리밸런싱 발생 이벤트 로그';
COMMENT ON COLUMN rebalancing_event.trigger_type IS 'PERIODIC=정기, DRIFT=편차기반';
COMMENT ON COLUMN rebalancing_event.trigger_detail IS '트리거 상세 (예: MONTHLY, DRIFT>=0.05)';
COMMENT ON COLUMN rebalancing_event.turnover IS '회전율 = 0.5 * sum(|after-before|) / V';
COMMENT ON COLUMN rebalancing_event.cost_factor IS 'NAV 감소 팩터 = 1 - turnover * cost_rate';

CREATE INDEX idx_rebalancing_event_run ON rebalancing_event(run_id);
CREATE INDEX idx_rebalancing_event_rule ON rebalancing_event(rule_id);
CREATE INDEX idx_rebalancing_event_date ON rebalancing_event(event_date);
CREATE INDEX idx_rebalancing_event_run_date ON rebalancing_event(run_id, event_date);
CREATE INDEX idx_rebalancing_event_trigger ON rebalancing_event(trigger_type);


-- =============================================================================
-- 3. 기본 리밸런싱 규칙 데이터 (시스템 프리셋)
-- =============================================================================

INSERT INTO rebalancing_rule (rule_name, description, rebalance_type, frequency, drift_threshold, cost_rate)
VALUES
    ('MONTHLY_BASIC', '월간 정기 리밸런싱 (10bp)', 'PERIODIC', 'MONTHLY', NULL, 0.00100),
    ('QUARTERLY_BASIC', '분기 정기 리밸런싱 (10bp)', 'PERIODIC', 'QUARTERLY', NULL, 0.00100),
    ('DRIFT_5PCT', 'Drift 5% 초과 시 리밸런싱', 'DRIFT', NULL, 0.0500, 0.00100),
    ('DRIFT_10PCT', 'Drift 10% 초과 시 리밸런싱', 'DRIFT', NULL, 0.1000, 0.00100),
    ('HYBRID_MONTHLY_5PCT', '월간 + Drift 5% 복합', 'HYBRID', 'MONTHLY', 0.0500, 0.00100),
    ('HYBRID_QUARTERLY_10PCT', '분기 + Drift 10% 복합', 'HYBRID', 'QUARTERLY', 0.1000, 0.00100)
ON CONFLICT DO NOTHING;


-- =============================================================================
-- 커밋
-- =============================================================================

COMMIT;

-- 결과 확인
SELECT 'Phase 2 Rebalancing DDL 적용 완료' AS status, NOW() AS applied_at;
