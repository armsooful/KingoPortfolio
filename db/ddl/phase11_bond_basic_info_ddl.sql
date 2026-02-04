-- =====================================================================
-- File: phase11_bond_basic_info_ddl.sql
-- Project: ForestoCompass
-- Phase: Phase 11 / Data Extension
--
-- 작성일: 2026-02-04
-- 목적:
--   금융위원회 채권기본정보 적재 테이블 추가
--   기존 bonds 테이블(교육용)과 독립 구조
--
-- 적용 DB: PostgreSQL
-- 스키마: foresto
-- =====================================================================

BEGIN;

SET search_path TO foresto;

CREATE TABLE IF NOT EXISTS bond_basic_info (
    bond_info_id        BIGSERIAL PRIMARY KEY,

    -- 식별
    isin_cd             VARCHAR(12)  NOT NULL,
    bas_dt              VARCHAR(8),                         -- API 조회 기준일 (YYYYMMDD)
    crno                VARCHAR(13),                        -- 법인등록번호

    -- 종목
    isin_cd_nm          VARCHAR(200),                       -- 채권명
    scrs_itms_kcd       VARCHAR(4),                         -- 유가증권종목종류코드
    scrs_itms_kcd_nm    VARCHAR(100),                       -- 유가증권종목종류코드명
    bond_isur_nm        VARCHAR(200),                       -- 발행인명

    -- 발행
    bond_issu_dt        DATE,                               -- 발행일
    bond_expr_dt        DATE,                               -- 만기일

    -- 금액
    bond_issu_amt       NUMERIC(22,3),                      -- 발행금액
    bond_bal            NUMERIC(22,3),                      -- 잔액

    -- 금리
    bond_srfc_inrt      NUMERIC(15,10),                     -- 표면이율
    irt_chng_dcd        VARCHAR(1),                         -- 금리변동구분: Y=변동, N=고정
    bond_int_tcd        VARCHAR(1),                         -- 이자유형코드
    int_pay_cycl_ctt    VARCHAR(100),                       -- 이자지급주기

    -- 이표
    nxtm_copn_dt        DATE,                               -- 차기이표일
    rbf_copn_dt         DATE,                               -- 직전이표일

    -- 보증/순위
    grn_dcd             VARCHAR(1),                         -- 보증구분코드
    bond_rnkn_dcd       VARCHAR(1),                         -- 순위구분코드

    -- 신용등급
    kis_scrs_itms_kcd   VARCHAR(4),                         -- KIS 신용등급
    kbp_scrs_itms_kcd   VARCHAR(4),                         -- KBP 신용등급
    nice_scrs_itms_kcd  VARCHAR(4),                         -- NICE 신용등급
    fn_scrs_itms_kcd    VARCHAR(4),                         -- FN 신용등급

    -- 모집/상장
    bond_offr_mcd       VARCHAR(2),                         -- 모집방법코드
    lstg_dt             DATE,                               -- 상장일

    -- 특이
    prmnc_bond_yn       CHAR(1),                            -- 영구채권여부
    strips_psbl_yn      CHAR(1),                            -- 스트립스가능여부

    -- 데이터 거버넌스
    source_id           VARCHAR(20) NOT NULL REFERENCES data_source(source_id),
    batch_id            INTEGER REFERENCES data_load_batch(batch_id),
    as_of_date          DATE NOT NULL,

    created_at          TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bond_info_isin    ON bond_basic_info(isin_cd);
CREATE INDEX IF NOT EXISTS idx_bond_info_isur    ON bond_basic_info(bond_isur_nm);
CREATE INDEX IF NOT EXISTS idx_bond_info_expr_dt ON bond_basic_info(bond_expr_dt);
CREATE INDEX IF NOT EXISTS idx_bond_info_asof    ON bond_basic_info(as_of_date);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_bond_basic_info'
    ) THEN
        ALTER TABLE bond_basic_info
            ADD CONSTRAINT uq_bond_basic_info
            UNIQUE (isin_cd, bas_dt, source_id);
    END IF;
END $$;

COMMIT;
