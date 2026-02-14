-- =====================================================================================
-- Foresto Phase 1 - PostgreSQL DDL (Partitioning Included)
-- Date: 2026-01-15
-- Scope: Core operational tables for Phase 1
-- Strategy: Native RANGE partition by month for large time-series tables
-- Notes:
--  - Large tables partitioned: 일봉가격, 일간수익률, 시뮬레이션경로
--  - Helper function 월단위_파티션_생성 creates monthly partitions
-- =====================================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid()
CREATE SCHEMA IF NOT EXISTS foresto;
SET search_path TO foresto;

-- =====================================================================================
-- 1) ENUM Types
-- =====================================================================================
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '상품유형') THEN
    CREATE TYPE 상품유형 AS ENUM ('ETF','INDEX','FX','RATE','COMMODITY','CASH_PROXY','MACRO_SERIES');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '상태유형') THEN
    CREATE TYPE 상태유형 AS ENUM ('ACTIVE','INACTIVE');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '데이터품질') THEN
    CREATE TYPE 데이터품질 AS ENUM ('OK','MISSING','IMPUTED');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '리밸런싱규칙') THEN
    CREATE TYPE 리밸런싱규칙 AS ENUM ('MONTHLY','QUARTERLY','SEMIANNUAL','ANNUAL','THRESHOLD','NONE');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '구성방법') THEN
    CREATE TYPE 구성방법 AS ENUM ('FIXED_WEIGHT','RISK_PARITY','HEURISTIC','OPTIMIZED','CUSTOM');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '실행상태') THEN
    CREATE TYPE 실행상태 AS ENUM ('PENDING','RUNNING','DONE','FAILED');
  END IF;
END$$;

-- =====================================================================================
-- 2) Governance
-- =====================================================================================
CREATE TABLE IF NOT EXISTS 모델버전등록부 (
  모델버전          TEXT PRIMARY KEY,
  설명              TEXT NOT NULL,
  깃커밋해시        TEXT,
  파라미터JSON      JSONB NOT NULL DEFAULT '{}'::jsonb,
  배포일시          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS 원천적재이력 (
  적재ID            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  벤더명            TEXT NOT NULL,
  데이터셋명        TEXT NOT NULL,
  기간범위          DATERANGE,
  레코드건수        BIGINT NOT NULL,
  체크섬            TEXT,
  적재일시          TIMESTAMPTZ NOT NULL DEFAULT now(),
  상태              TEXT NOT NULL DEFAULT 'DONE',
  상세JSON          JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_원천적재이력_벤더_데이터셋_시간
  ON 원천적재이력 (벤더명, 데이터셋명, 적재일시 DESC);

-- =====================================================================================
-- 3) Dimensions
-- =====================================================================================
CREATE TABLE IF NOT EXISTS 금융상품기준정보 (
  금융상품ID        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  상품유형          상품유형 NOT NULL,
  티커또는코드      TEXT NOT NULL,
  상품명_한글       TEXT,
  상품명_영문       TEXT,
  통화              TEXT NOT NULL,
  거래소            TEXT,
  국가              TEXT,
  총수익률여부      BOOLEAN NOT NULL DEFAULT FALSE,
  대표벤더          TEXT NOT NULL,
  상태              상태유형 NOT NULL DEFAULT 'ACTIVE',
  생성일시          TIMESTAMPTZ NOT NULL DEFAULT now(),
  수정일시          TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_금융상품기준정보 UNIQUE (상품유형, 티커또는코드, 거래소)
);

CREATE INDEX IF NOT EXISTS idx_금융상품기준정보_유형_코드
  ON 금융상품기준정보 (상품유형, 티커또는코드);

-- =====================================================================================
-- 4) Partition Helpers (Monthly partitions)
-- =====================================================================================
CREATE OR REPLACE FUNCTION 월단위_파티션_생성(
  p_parent_table regclass,
  p_start_month  date,
  p_end_month    date
) RETURNS void LANGUAGE plpgsql AS $$
DECLARE
  d date;
  start_d date;
  end_d date;
  parent_name text;
  part_name text;
BEGIN
  d := date_trunc('month', p_start_month)::date;
  parent_name := p_parent_table::text;

  WHILE d <= date_trunc('month', p_end_month)::date LOOP
    start_d := d;
    end_d := (d + INTERVAL '1 month')::date;
    part_name := replace(parent_name, '.', '_') || '_p' || to_char(start_d, 'YYYYMM');

    EXECUTE format(
      'CREATE TABLE IF NOT EXISTS %I PARTITION OF %s FOR VALUES FROM (%L) TO (%L);',
      part_name, parent_name, start_d, end_d
    );

    d := end_d;
  END LOOP;
END$$;

-- =====================================================================================
-- 5) Facts (Partitioned time-series)
-- =====================================================================================

-- 5.1 EOD Prices
CREATE TABLE IF NOT EXISTS 일봉가격 (
  금융상품ID        UUID NOT NULL REFERENCES 금융상품기준정보(금융상품ID),
  거래일자          DATE NOT NULL,
  종가              NUMERIC(20,8) NOT NULL,
  수정종가          NUMERIC(20,8),
  순자산가치        NUMERIC(20,8),
  거래량            BIGINT,
  원천벤더          TEXT NOT NULL,
  기준시각          TIMESTAMPTZ NOT NULL DEFAULT now(),
  적재ID            UUID REFERENCES 원천적재이력(적재ID),
  PRIMARY KEY (금융상품ID, 거래일자)
) PARTITION BY RANGE (거래일자);

CREATE INDEX IF NOT EXISTS idx_일봉가격_거래일자
  ON 일봉가격 (거래일자);

-- 5.2 Daily Returns Mart
CREATE TABLE IF NOT EXISTS 일간수익률 (
  금융상품ID        UUID NOT NULL REFERENCES 금융상품기준정보(금융상품ID),
  거래일자          DATE NOT NULL,
  일간수익률        DOUBLE PRECISION NOT NULL,
  로그수익률        DOUBLE PRECISION,
  데이터품질        데이터품질 NOT NULL DEFAULT 'OK',
  계산일시          TIMESTAMPTZ NOT NULL DEFAULT now(),
  모델버전          TEXT REFERENCES 모델버전등록부(모델버전),
  PRIMARY KEY (금융상품ID, 거래일자)
) PARTITION BY RANGE (거래일자);

CREATE INDEX IF NOT EXISTS idx_일간수익률_거래일자
  ON 일간수익률 (거래일자);

-- =====================================================================================
-- 6) Scenario / Portfolio
-- =====================================================================================
CREATE TABLE IF NOT EXISTS 시나리오정의 (
  시나리오ID        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  시나리오명        TEXT NOT NULL,
  시나리오유형      TEXT NOT NULL,
  설명문구          TEXT,
  제약조건JSON      JSONB NOT NULL DEFAULT '{}'::jsonb,
  리밸런싱규칙      리밸런싱규칙 NOT NULL DEFAULT 'NONE',
  생성주체          TEXT NOT NULL DEFAULT 'SYSTEM',
  상태              TEXT NOT NULL DEFAULT 'ACTIVE',
  생성일시          TIMESTAMPTZ NOT NULL DEFAULT now(),
  수정일시          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS 포트폴리오모델 (
  포트폴리오ID      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  시나리오ID        UUID NOT NULL REFERENCES 시나리오정의(시나리오ID),
  기준통화          TEXT NOT NULL,
  포트폴리오명      TEXT NOT NULL,
  허용유니버스JSON  JSONB NOT NULL DEFAULT '[]'::jsonb,
  구성방법          구성방법 NOT NULL,
  모델버전          TEXT REFERENCES 모델버전등록부(모델버전),
  생성일시          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_포트폴리오모델_시나리오
  ON 포트폴리오모델 (시나리오ID);

CREATE TABLE IF NOT EXISTS 포트폴리오구성비 (
  포트폴리오ID      UUID NOT NULL REFERENCES 포트폴리오모델(포트폴리오ID),
  적용일자          DATE NOT NULL,
  금융상품ID        UUID NOT NULL REFERENCES 금융상품기준정보(금융상품ID),
  비중              DOUBLE PRECISION NOT NULL,
  PRIMARY KEY (포트폴리오ID, 적용일자, 금융상품ID),
  CONSTRAINT chk_비중_범위 CHECK (비중 >= 0.0 AND 비중 <= 1.0)
);

CREATE INDEX IF NOT EXISTS idx_포트폴리오구성비_적용일자
  ON 포트폴리오구성비 (포트폴리오ID, 적용일자);

-- =====================================================================================
-- 7) Simulation (Run + Path(partitioned) + Summary)
-- =====================================================================================
CREATE TABLE IF NOT EXISTS 시뮬레이션실행 (
  시뮬레이션ID       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  요청해시           TEXT NOT NULL,
  입력프로필JSON     JSONB NOT NULL DEFAULT '{}'::jsonb,
  시작일             DATE NOT NULL,
  종료일             DATE NOT NULL,
  기준통화           TEXT NOT NULL,
  생성일시           TIMESTAMPTZ NOT NULL DEFAULT now(),
  엔진버전           TEXT REFERENCES 모델버전등록부(모델버전),
  상태               실행상태 NOT NULL DEFAULT 'PENDING',
  오류메시지         TEXT,
  CONSTRAINT chk_시뮬레이션기간 CHECK (시작일 <= 종료일)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_시뮬레이션실행_요청해시
  ON 시뮬레이션실행 (요청해시);

CREATE INDEX IF NOT EXISTS idx_시뮬레이션실행_생성일시
  ON 시뮬레이션실행 (생성일시 DESC);

-- Path: partitioned by 거래일자 for pruning & retention
CREATE TABLE IF NOT EXISTS 시뮬레이션경로 (
  시뮬레이션ID       UUID NOT NULL REFERENCES 시뮬레이션실행(시뮬레이션ID) ON DELETE CASCADE,
  거래일자           DATE NOT NULL,
  지수가치           DOUBLE PRECISION NOT NULL,
  낙폭               DOUBLE PRECISION,
  PRIMARY KEY (시뮬레이션ID, 거래일자)
) PARTITION BY RANGE (거래일자);

CREATE INDEX IF NOT EXISTS idx_시뮬레이션경로_거래일자
  ON 시뮬레이션경로 (거래일자);

CREATE TABLE IF NOT EXISTS 시뮬레이션요약지표 (
  시뮬레이션ID       UUID PRIMARY KEY REFERENCES 시뮬레이션실행(시뮬레이션ID) ON DELETE CASCADE,
  연환산수익률       DOUBLE PRECISION,
  연환산변동성       DOUBLE PRECISION,
  최대낙폭           DOUBLE PRECISION,
  최대회복일수       INTEGER,
  최악1개월수익률    DOUBLE PRECISION,
  최악3개월수익률    DOUBLE PRECISION,
  계산일시           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =====================================================================================
-- 8) Sample Partitions (past 6 months ~ next 6 months)
-- =====================================================================================
SELECT 월단위_파티션_생성('foresto.일봉가격',
  (date_trunc('month', now())::date - INTERVAL '6 months')::date,
  (date_trunc('month', now())::date + INTERVAL '6 months')::date
);

SELECT 월단위_파티션_생성('foresto.일간수익률',
  (date_trunc('month', now())::date - INTERVAL '6 months')::date,
  (date_trunc('month', now())::date + INTERVAL '6 months')::date
);

SELECT 월단위_파티션_생성('foresto.시뮬레이션경로',
  (date_trunc('month', now())::date - INTERVAL '6 months')::date,
  (date_trunc('month', now())::date + INTERVAL '6 months')::date
);

-- =====================================================================================
-- End
-- =====================================================================================
