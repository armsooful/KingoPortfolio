-- =====================================================================
-- File: Foresto_Phase2_EpicC_CustomPortfolio_DDL.sql
-- Project: ForestoCompass
-- Phase: Phase 2 / Epic C (Custom Portfolio)
--
-- 작성일: 2026-01-16
-- 목적:
--   사용자 커스텀 포트폴리오(자산군 비중) 저장 및 시뮬레이션 연동을 위한 DB 확장 DDL
--
-- 원칙:
--   * Phase 1 테이블 변경 금지 (신규 테이블만 추가)
--   * 개별 종목 입력 금지(자산군 단위)
--   * 재현성: 포트폴리오 정의는 정규화된 weight 테이블로 저장
--
-- 적용 DB: PostgreSQL
-- 스키마: foresto
-- =====================================================================

BEGIN;

SET search_path TO foresto;

-- ---------------------------------------------------------------------
-- 1) custom_portfolio
-- ---------------------------------------------------------------------
-- 커스텀 포트폴리오 메타(소유자/이름/기반 템플릿/활성 상태)
--
-- owner_user_id:
--   - 사용자 테이블이 존재한다면 FK로 교체 가능
--   - 사용자 테이블이 없으면 외부 식별자를 BIGINT로 관리(현 DDL)
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS custom_portfolio (
    portfolio_id        BIGSERIAL PRIMARY KEY,

    -- 소유자 식별자 (시스템에 user 테이블이 있으면 FK로 교체)
    owner_user_id       BIGINT NOT NULL,

    portfolio_name      VARCHAR(80) NOT NULL,

    -- 템플릿 기반 확장(선택): scenario/template 테이블이 있으면 FK로 교체
    base_template_id    BIGINT,

    is_active           BOOLEAN NOT NULL DEFAULT TRUE,

    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE custom_portfolio IS
'사용자 커스텀 포트폴리오 메타 (Phase 2 / Epic C)';

COMMENT ON COLUMN custom_portfolio.owner_user_id IS
'포트폴리오 소유자(본인 접근 통제용). 사용자 테이블 존재 시 FK로 교체 가능';

COMMENT ON COLUMN custom_portfolio.base_template_id IS
'기반 템플릿/시나리오 ID(선택). 템플릿 테이블 존재 시 FK로 교체 가능';

CREATE INDEX IF NOT EXISTS idx_custom_portfolio_owner
    ON custom_portfolio (owner_user_id);

CREATE INDEX IF NOT EXISTS idx_custom_portfolio_active
    ON custom_portfolio (is_active);

-- 같은 사용자(owner) 내에서 이름 중복 방지(운영 편의)
CREATE UNIQUE INDEX IF NOT EXISTS ux_custom_portfolio_owner_name
    ON custom_portfolio (owner_user_id, portfolio_name);

-- ---------------------------------------------------------------------
-- 2) custom_portfolio_weight
-- ---------------------------------------------------------------------
-- 포트폴리오 자산군별 목표비중(정규화)
--
-- asset_class_code:
--   - 시스템 표준 코드 사용 (예: EQUITY, BOND, CASH, GOLD, ALT)
-- target_weight:
--   - 0~1 범위
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS custom_portfolio_weight (
    portfolio_id        BIGINT NOT NULL
                        REFERENCES custom_portfolio(portfolio_id)
                        ON DELETE CASCADE,

    asset_class_code    VARCHAR(32) NOT NULL,

    target_weight       NUMERIC(10,8) NOT NULL
                        CHECK (target_weight >= 0 AND target_weight <= 1),

    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (portfolio_id, asset_class_code)
);

COMMENT ON TABLE custom_portfolio_weight IS
'커스텀 포트폴리오 자산군별 비중 (Phase 2 / Epic C)';

COMMENT ON COLUMN custom_portfolio_weight.asset_class_code IS
'자산군 표준 코드 (EQUITY/BOND/CASH/GOLD/ALT 등)';

COMMENT ON COLUMN custom_portfolio_weight.target_weight IS
'목표 비중(0~1). 총합 1.0 검증은 애플리케이션 레이어에서 수행';

CREATE INDEX IF NOT EXISTS idx_custom_portfolio_weight_portfolio
    ON custom_portfolio_weight (portfolio_id);

-- ---------------------------------------------------------------------
-- 3) 권한 정책 (운영 기준)
-- ---------------------------------------------------------------------
-- foresto: DML
-- role_readonly: SELECT
-- ---------------------------------------------------------------------

REVOKE ALL ON custom_portfolio, custom_portfolio_weight FROM PUBLIC;

GRANT SELECT, INSERT, UPDATE, DELETE
ON custom_portfolio, custom_portfolio_weight
TO foresto;

GRANT SELECT
ON custom_portfolio, custom_portfolio_weight
TO role_readonly;

COMMIT;

-- ---------------------------------------------------------------------
-- 실행 후 검증
-- ---------------------------------------------------------------------
-- \d foresto.custom_portfolio
-- \d foresto.custom_portfolio_weight
-- SELECT * FROM foresto.custom_portfolio LIMIT 5;
-- ---------------------------------------------------------------------
