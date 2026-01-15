-- =============================================================================
-- Foresto Phase 1 DDL - 데이터 기반 시뮬레이션 인프라
-- 작성일: 2026-01-15
-- PostgreSQL 14+ 호환
-- =============================================================================

-- 트랜잭션 시작
BEGIN;

-- =============================================================================
-- 1. 메타데이터 테이블
-- =============================================================================

-- 1.1 모델 버전 등록부
CREATE TABLE IF NOT EXISTS model_version_registry (
    version_id          VARCHAR(20)     PRIMARY KEY,
    version_name        VARCHAR(100)    NOT NULL,
    description         TEXT,
    release_date        DATE            NOT NULL,
    is_active           BOOLEAN         DEFAULT TRUE,
    created_at          TIMESTAMPTZ     DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     DEFAULT NOW()
);

COMMENT ON TABLE model_version_registry IS '시뮬레이션 엔진/모델 버전 관리';
COMMENT ON COLUMN model_version_registry.version_id IS '버전 식별자 (예: 1.0.0)';

-- 1.2 원천 적재 이력
CREATE TABLE IF NOT EXISTS source_load_history (
    load_id             BIGSERIAL       PRIMARY KEY,
    source_type         VARCHAR(50)     NOT NULL,  -- 'alpha_vantage', 'krx', 'manual'
    source_name         VARCHAR(100)    NOT NULL,  -- 파일명/API명
    load_status         VARCHAR(20)     NOT NULL DEFAULT 'STARTED',  -- STARTED, SUCCESS, FAILED, PARTIAL
    records_loaded      INTEGER         DEFAULT 0,
    records_failed      INTEGER         DEFAULT 0,
    error_message       TEXT,
    started_at          TIMESTAMPTZ     DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,
    loaded_by           VARCHAR(50),  -- 'batch', 'admin', 'system'
    created_at          TIMESTAMPTZ     DEFAULT NOW()
);

COMMENT ON TABLE source_load_history IS '데이터 적재 이력 추적';
CREATE INDEX idx_source_load_history_status ON source_load_history(load_status);
CREATE INDEX idx_source_load_history_source ON source_load_history(source_type, source_name);

-- =============================================================================
-- 2. 기준정보 테이블
-- =============================================================================

-- 2.1 금융상품 기준정보 (통합 마스터)
CREATE TABLE IF NOT EXISTS instrument_master (
    instrument_id       BIGSERIAL       PRIMARY KEY,
    instrument_type     VARCHAR(20)     NOT NULL,  -- 'STOCK', 'ETF', 'BOND', 'INDEX', 'FX'
    ticker              VARCHAR(20)     NOT NULL,  -- 종목코드/심볼
    exchange            VARCHAR(20)     NOT NULL,  -- 'KRX', 'NYSE', 'NASDAQ', 'INTERNAL'
    name_ko             VARCHAR(200),              -- 한글명
    name_en             VARCHAR(200),              -- 영문명
    currency            VARCHAR(3)      NOT NULL DEFAULT 'KRW',  -- 'KRW', 'USD'
    sector              VARCHAR(100),
    is_active           BOOLEAN         DEFAULT TRUE,
    data_source         VARCHAR(50),               -- 데이터 출처
    created_at          TIMESTAMPTZ     DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     DEFAULT NOW(),

    CONSTRAINT uq_instrument_ticker_exchange UNIQUE (instrument_type, ticker, exchange)
);

COMMENT ON TABLE instrument_master IS '금융상품 통합 기준정보';
CREATE INDEX idx_instrument_master_type ON instrument_master(instrument_type);
CREATE INDEX idx_instrument_master_ticker ON instrument_master(ticker);
CREATE INDEX idx_instrument_master_active ON instrument_master(is_active) WHERE is_active = TRUE;

-- =============================================================================
-- 3. 시계열 데이터 테이블 (파티션)
-- =============================================================================

-- 3.1 일봉 가격 테이블 (파티션 부모)
CREATE TABLE IF NOT EXISTS daily_price (
    price_id            BIGSERIAL,
    instrument_id       BIGINT          NOT NULL,
    trade_date          DATE            NOT NULL,
    open_price          NUMERIC(18,4),
    high_price          NUMERIC(18,4),
    low_price           NUMERIC(18,4),
    close_price         NUMERIC(18,4)   NOT NULL,
    adj_close_price     NUMERIC(18,4),  -- 조정 종가 (배당/분할 반영)
    volume              BIGINT,
    load_id             BIGINT,         -- source_load_history 참조
    created_at          TIMESTAMPTZ     DEFAULT NOW(),

    PRIMARY KEY (instrument_id, trade_date)
) PARTITION BY RANGE (trade_date);

COMMENT ON TABLE daily_price IS '일봉 가격 (월별 파티션)';
CREATE INDEX idx_daily_price_date ON daily_price(trade_date);

-- 3.2 일간 수익률 테이블 (파티션 부모)
CREATE TABLE IF NOT EXISTS daily_return (
    return_id           BIGSERIAL,
    instrument_id       BIGINT          NOT NULL,
    trade_date          DATE            NOT NULL,
    daily_return        NUMERIC(12,8)   NOT NULL,  -- 일간 수익률 (소수점)
    log_return          NUMERIC(12,8),             -- 로그 수익률
    data_quality        VARCHAR(20)     DEFAULT 'OK',  -- 'OK', 'MISSING', 'IMPUTED'
    engine_version      VARCHAR(20),
    created_at          TIMESTAMPTZ     DEFAULT NOW(),

    PRIMARY KEY (instrument_id, trade_date)
) PARTITION BY RANGE (trade_date);

COMMENT ON TABLE daily_return IS '일간 수익률 (월별 파티션)';
CREATE INDEX idx_daily_return_date ON daily_return(trade_date);
CREATE INDEX idx_daily_return_quality ON daily_return(data_quality) WHERE data_quality != 'OK';

-- =============================================================================
-- 4. 시나리오/포트폴리오 관리 테이블
-- =============================================================================

-- 4.1 시나리오 정의
CREATE TABLE IF NOT EXISTS scenario_definition (
    scenario_id         VARCHAR(50)     PRIMARY KEY,
    name_ko             VARCHAR(100)    NOT NULL,
    name_en             VARCHAR(100),
    description         TEXT,
    objective           TEXT,                      -- 학습 목표
    target_investor     TEXT,                      -- 대상 투자자 설명
    risk_level          VARCHAR(20),               -- 'LOW', 'MEDIUM', 'HIGH'
    disclaimer          TEXT            NOT NULL,  -- 면책 문구 (필수)
    is_active           BOOLEAN         DEFAULT TRUE,
    display_order       INTEGER         DEFAULT 0,
    created_at          TIMESTAMPTZ     DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     DEFAULT NOW()
);

COMMENT ON TABLE scenario_definition IS '관리형 시나리오 정의';

-- 4.2 포트폴리오 모델 (시나리오별 포트폴리오)
CREATE TABLE IF NOT EXISTS portfolio_model (
    portfolio_id        BIGSERIAL       PRIMARY KEY,
    scenario_id         VARCHAR(50)     NOT NULL REFERENCES scenario_definition(scenario_id),
    portfolio_name      VARCHAR(100)    NOT NULL,
    effective_date      DATE            NOT NULL,  -- 적용 시작일
    expiry_date         DATE,                      -- 적용 종료일 (NULL=현재 적용중)
    rebalance_freq      VARCHAR(20)     DEFAULT 'NONE',  -- 'NONE', 'MONTHLY', 'QUARTERLY', 'ANNUAL'
    engine_version      VARCHAR(20),
    created_at          TIMESTAMPTZ     DEFAULT NOW(),

    CONSTRAINT uq_portfolio_scenario_date UNIQUE (scenario_id, effective_date)
);

COMMENT ON TABLE portfolio_model IS '시나리오별 포트폴리오 모델';
CREATE INDEX idx_portfolio_model_scenario ON portfolio_model(scenario_id);
CREATE INDEX idx_portfolio_model_effective ON portfolio_model(effective_date);

-- 4.3 포트폴리오 구성비
CREATE TABLE IF NOT EXISTS portfolio_allocation (
    allocation_id       BIGSERIAL       PRIMARY KEY,
    portfolio_id        BIGINT          NOT NULL REFERENCES portfolio_model(portfolio_id),
    instrument_id       BIGINT          NOT NULL,  -- instrument_master 참조
    weight              NUMERIC(5,4)    NOT NULL,  -- 비중 (0.0000 ~ 1.0000)
    asset_class         VARCHAR(50),               -- 'EQUITY', 'BOND', 'CASH', 'COMMODITY', 'OTHER'
    created_at          TIMESTAMPTZ     DEFAULT NOW(),

    CONSTRAINT chk_weight_range CHECK (weight >= 0 AND weight <= 1),
    CONSTRAINT uq_allocation_portfolio_instrument UNIQUE (portfolio_id, instrument_id)
);

COMMENT ON TABLE portfolio_allocation IS '포트폴리오 자산 구성비';
CREATE INDEX idx_portfolio_allocation_portfolio ON portfolio_allocation(portfolio_id);

-- 구성비 합계 검증 함수
CREATE OR REPLACE FUNCTION check_portfolio_weight_sum()
RETURNS TRIGGER AS $$
DECLARE
    total_weight NUMERIC;
BEGIN
    SELECT SUM(weight) INTO total_weight
    FROM portfolio_allocation
    WHERE portfolio_id = NEW.portfolio_id;

    IF total_weight > 1.0001 THEN  -- 반올림 오차 허용
        RAISE EXCEPTION 'Portfolio weight sum exceeds 1.0: %', total_weight;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_portfolio_weight
AFTER INSERT OR UPDATE ON portfolio_allocation
FOR EACH ROW EXECUTE FUNCTION check_portfolio_weight_sum();

-- =============================================================================
-- 5. 시뮬레이션 결과 테이블
-- =============================================================================

-- 5.1 시뮬레이션 실행 (sim_run)
CREATE TABLE IF NOT EXISTS simulation_run (
    run_id              BIGSERIAL       PRIMARY KEY,
    request_hash        VARCHAR(64)     NOT NULL UNIQUE,  -- SHA-256
    scenario_id         VARCHAR(50)     REFERENCES scenario_definition(scenario_id),
    portfolio_id        BIGINT          REFERENCES portfolio_model(portfolio_id),
    user_id             BIGINT,                           -- users 테이블 참조 (NULL 허용)

    -- 입력 파라미터
    start_date          DATE            NOT NULL,
    end_date            DATE            NOT NULL,
    initial_amount      NUMERIC(18,2)   NOT NULL,
    rebalance_freq      VARCHAR(20),
    max_loss_limit_pct  NUMERIC(5,2),                     -- 손실 한도 (%)
    request_params      JSONB,                            -- 전체 요청 파라미터 백업

    -- 메타데이터
    engine_version      VARCHAR(20)     NOT NULL,
    run_status          VARCHAR(20)     DEFAULT 'COMPLETED',  -- 'RUNNING', 'COMPLETED', 'FAILED'
    error_message       TEXT,

    created_at          TIMESTAMPTZ     DEFAULT NOW(),
    expires_at          TIMESTAMPTZ,                      -- TTL

    CONSTRAINT chk_date_range CHECK (end_date > start_date)
);

COMMENT ON TABLE simulation_run IS '시뮬레이션 실행 기록';
CREATE INDEX idx_simulation_run_hash ON simulation_run(request_hash);
CREATE INDEX idx_simulation_run_scenario ON simulation_run(scenario_id);
CREATE INDEX idx_simulation_run_user ON simulation_run(user_id);
CREATE INDEX idx_simulation_run_expires ON simulation_run(expires_at) WHERE expires_at IS NOT NULL;

-- 5.2 시뮬레이션 경로 (sim_path) - 파티션
CREATE TABLE IF NOT EXISTS simulation_path (
    path_id             BIGSERIAL,
    run_id              BIGINT          NOT NULL,
    path_date           DATE            NOT NULL,
    nav                 NUMERIC(18,4)   NOT NULL,         -- 순자산가치
    daily_return        NUMERIC(12,8),                    -- 일간 수익률
    cumulative_return   NUMERIC(12,8),                    -- 누적 수익률
    drawdown            NUMERIC(12,8),                    -- 낙폭 (음수)
    high_water_mark     NUMERIC(18,4),                    -- 고점
    created_at          TIMESTAMPTZ     DEFAULT NOW(),

    PRIMARY KEY (run_id, path_date)
) PARTITION BY RANGE (path_date);

COMMENT ON TABLE simulation_path IS '시뮬레이션 일별 경로 (월별 파티션)';
CREATE INDEX idx_simulation_path_run ON simulation_path(run_id);

-- 5.3 시뮬레이션 요약 지표 (sim_summary)
CREATE TABLE IF NOT EXISTS simulation_summary (
    summary_id          BIGSERIAL       PRIMARY KEY,
    run_id              BIGINT          NOT NULL UNIQUE REFERENCES simulation_run(run_id),

    -- 손실/회복 지표 (최상위)
    max_drawdown        NUMERIC(8,4)    NOT NULL,         -- MDD (%)
    max_recovery_days   INTEGER,                          -- 최대 회복 기간 (일)
    worst_1m_return     NUMERIC(8,4),                     -- 최악의 1개월 수익률 (%)
    worst_3m_return     NUMERIC(8,4),                     -- 최악의 3개월 수익률 (%)
    volatility          NUMERIC(8,4),                     -- 연간 변동성 (%)

    -- 과거 수익률 (참고용)
    total_return        NUMERIC(10,4)   NOT NULL,         -- 총 수익률 (%)
    cagr                NUMERIC(8,4),                     -- 연평균 복합 성장률 (%)
    sharpe_ratio        NUMERIC(8,4),                     -- 샤프 비율
    sortino_ratio       NUMERIC(8,4),                     -- 소르티노 비율

    -- 기타 통계
    final_value         NUMERIC(18,2),                    -- 최종 자산가치
    trading_days        INTEGER,                          -- 거래일 수
    rebalance_count     INTEGER         DEFAULT 0,        -- 리밸런싱 횟수

    created_at          TIMESTAMPTZ     DEFAULT NOW()
);

COMMENT ON TABLE simulation_summary IS '시뮬레이션 요약 지표';
CREATE INDEX idx_simulation_summary_run ON simulation_summary(run_id);

-- =============================================================================
-- 6. 파티션 생성 함수
-- =============================================================================

-- 월별 파티션 생성 함수
CREATE OR REPLACE FUNCTION create_monthly_partitions(
    p_table_name TEXT,
    p_start_date DATE,
    p_end_date DATE
)
RETURNS INTEGER AS $$
DECLARE
    v_partition_date DATE;
    v_partition_name TEXT;
    v_partition_start TEXT;
    v_partition_end TEXT;
    v_count INTEGER := 0;
BEGIN
    v_partition_date := DATE_TRUNC('month', p_start_date)::DATE;

    WHILE v_partition_date < p_end_date LOOP
        v_partition_name := p_table_name || '_' || TO_CHAR(v_partition_date, 'YYYYMM');
        v_partition_start := TO_CHAR(v_partition_date, 'YYYY-MM-DD');
        v_partition_end := TO_CHAR(v_partition_date + INTERVAL '1 month', 'YYYY-MM-DD');

        -- 파티션이 없으면 생성
        IF NOT EXISTS (
            SELECT 1 FROM pg_class WHERE relname = v_partition_name
        ) THEN
            EXECUTE format(
                'CREATE TABLE IF NOT EXISTS %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
                v_partition_name,
                p_table_name,
                v_partition_start,
                v_partition_end
            );
            v_count := v_count + 1;
            RAISE NOTICE 'Created partition: %', v_partition_name;
        END IF;

        v_partition_date := v_partition_date + INTERVAL '1 month';
    END LOOP;

    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION create_monthly_partitions IS '월별 파티션 자동 생성 함수';

-- =============================================================================
-- 7. 초기 파티션 생성 (2020-01 ~ 2026-12)
-- =============================================================================

-- daily_price 파티션
SELECT create_monthly_partitions('daily_price', '2020-01-01', '2027-01-01');

-- daily_return 파티션
SELECT create_monthly_partitions('daily_return', '2020-01-01', '2027-01-01');

-- simulation_path 파티션
SELECT create_monthly_partitions('simulation_path', '2020-01-01', '2027-01-01');

-- =============================================================================
-- 8. 초기 데이터 (시나리오 3종)
-- =============================================================================

INSERT INTO scenario_definition (scenario_id, name_ko, name_en, description, objective, target_investor, risk_level, disclaimer, display_order)
VALUES
    ('MIN_VOL', '변동성 최소화', 'Minimum Volatility',
     '변동성을 최소화하는 전략을 학습하기 위한 시나리오입니다.',
     '변동성 최소화를 통한 안정적 자산 운용 학습',
     '변동성에 민감하며 안정적인 자산 운용을 학습하고자 하는 분',
     'LOW',
     '본 시나리오는 교육 목적의 학습 자료이며, 투자 권유가 아닙니다. 과거 데이터 기반 참고치이며 미래 성과를 보장하지 않습니다.',
     1),
    ('DEFENSIVE', '방어형', 'Defensive',
     '시장 하락 시 손실을 최소화하는 전략을 학습하기 위한 시나리오입니다.',
     '시장 하락 시 손실 최소화 전략 학습',
     '하락장에서의 자산 보전을 학습하고자 하는 분',
     'LOW',
     '본 시나리오는 교육 목적의 학습 자료이며, 투자 권유가 아닙니다. 과거 데이터 기반 참고치이며 미래 성과를 보장하지 않습니다.',
     2),
    ('GROWTH', '성장형', 'Growth',
     '장기 자산 성장 전략을 학습하기 위한 시나리오입니다.',
     '장기 자산 성장 전략 학습',
     '장기적인 자산 성장을 학습하고자 하는 분',
     'HIGH',
     '본 시나리오는 교육 목적의 학습 자료이며, 투자 권유가 아닙니다. 과거 데이터 기반 참고치이며 미래 성과를 보장하지 않습니다.',
     3)
ON CONFLICT (scenario_id) DO NOTHING;

-- 초기 모델 버전 등록
INSERT INTO model_version_registry (version_id, version_name, description, release_date)
VALUES ('1.0.0', 'Phase 1 Initial', 'Phase 1 초기 릴리스', CURRENT_DATE)
ON CONFLICT (version_id) DO NOTHING;

-- =============================================================================
-- 9. 인덱스 추가 (성능 최적화)
-- =============================================================================

-- 복합 인덱스
CREATE INDEX IF NOT EXISTS idx_daily_price_instrument_date ON daily_price(instrument_id, trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_return_instrument_date ON daily_return(instrument_id, trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_simulation_path_run_date ON simulation_path(run_id, path_date DESC);

-- =============================================================================
-- 커밋
-- =============================================================================

COMMIT;

-- 결과 확인
SELECT 'Phase 1 DDL 적용 완료' AS status, NOW() AS applied_at;
