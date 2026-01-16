-- ============================================================================
-- Phase 2 Epic C: 사용자 커스텀 포트폴리오 DDL
-- 문서: Foresto_Phase2_EpicC_사용자포트폴리오_상세설계.md
-- 작성일: 2026-01-16
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. custom_portfolio: 커스텀 포트폴리오 메타 정보
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS custom_portfolio (
    portfolio_id    BIGSERIAL PRIMARY KEY,

    -- 소유자 (users 테이블 FK, 없으면 owner_key 사용)
    owner_user_id   BIGINT REFERENCES users(id) ON DELETE CASCADE,
    owner_key       VARCHAR(100),  -- user 테이블 없을 경우 대체 키

    -- 포트폴리오 정보
    portfolio_name  VARCHAR(100) NOT NULL,
    description     TEXT,

    -- 템플릿 기반 확장 (선택)
    base_template_id VARCHAR(20) REFERENCES scenario(scenario_id) ON DELETE SET NULL,

    -- 상태
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,

    -- 메타데이터
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),

    -- 제약조건: owner_user_id 또는 owner_key 중 하나는 필수
    CONSTRAINT chk_owner CHECK (
        owner_user_id IS NOT NULL OR owner_key IS NOT NULL
    )
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_custom_portfolio_owner_user
    ON custom_portfolio(owner_user_id) WHERE owner_user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_custom_portfolio_owner_key
    ON custom_portfolio(owner_key) WHERE owner_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_custom_portfolio_active
    ON custom_portfolio(is_active);

-- ----------------------------------------------------------------------------
-- 2. custom_portfolio_weight: 자산군별 비중 (정규화)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS custom_portfolio_weight (
    portfolio_id        BIGINT NOT NULL REFERENCES custom_portfolio(portfolio_id) ON DELETE CASCADE,
    asset_class_code    VARCHAR(20) NOT NULL,
    target_weight       NUMERIC(6, 4) NOT NULL,  -- 0.0000 ~ 1.0000

    -- 복합 PK
    PRIMARY KEY (portfolio_id, asset_class_code),

    -- 비중 범위 제약
    CONSTRAINT chk_weight_range CHECK (
        target_weight >= 0 AND target_weight <= 1
    )
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_custom_portfolio_weight_portfolio
    ON custom_portfolio_weight(portfolio_id);

-- ----------------------------------------------------------------------------
-- 3. asset_class_master: 허용된 자산군 코드 (참조용)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS asset_class_master (
    asset_class_code    VARCHAR(20) PRIMARY KEY,
    asset_class_name    VARCHAR(100) NOT NULL,
    description         TEXT,
    display_order       INTEGER DEFAULT 0,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 초기 데이터 삽입
INSERT INTO asset_class_master (asset_class_code, asset_class_name, description, display_order) VALUES
    ('EQUITY', '주식', '국내외 주식 자산', 1),
    ('BOND', '채권', '국내외 채권 자산', 2),
    ('CASH', '현금성', '현금 및 단기 금융상품', 3),
    ('GOLD', '금', '금 및 귀금속', 4),
    ('ALT', '대체투자', '부동산, 원자재 등 대체 자산', 5)
ON CONFLICT (asset_class_code) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 4. 트리거: updated_at 자동 갱신
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_custom_portfolio_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_custom_portfolio_updated ON custom_portfolio;
CREATE TRIGGER trg_custom_portfolio_updated
    BEFORE UPDATE ON custom_portfolio
    FOR EACH ROW
    EXECUTE FUNCTION update_custom_portfolio_timestamp();

-- ----------------------------------------------------------------------------
-- 5. 코멘트
-- ----------------------------------------------------------------------------
COMMENT ON TABLE custom_portfolio IS '사용자 정의 커스텀 포트폴리오 메타 정보 (Phase 2 Epic C)';
COMMENT ON TABLE custom_portfolio_weight IS '커스텀 포트폴리오의 자산군별 목표 비중';
COMMENT ON TABLE asset_class_master IS '시스템에서 허용하는 자산군 코드 마스터';

COMMENT ON COLUMN custom_portfolio.base_template_id IS '시나리오 템플릿 기반 확장 시 참조';
COMMENT ON COLUMN custom_portfolio_weight.target_weight IS '목표 비중 (0~1, 합계=1 검증은 애플리케이션에서)';
