-- ============================================================
-- 한국 주식 일별 시세 테이블 통합 마이그레이션
-- 설계서: docs/architecture/price_table_consolidation_design.md
--
-- 실행 순서:
--   1. 사전 준비 (data_source 등록)
--   2. stock_price_daily에 updated_at 컬럼 추가
--   3. Phase 1: stocks_daily_prices → stock_price_daily
--   4. Phase 2: krx_timeseries → stock_price_daily
--   5. 사후 검증
-- ============================================================

-- ============================================================
-- 0. 사전 준비: data_source 레코드 등록
-- ============================================================

INSERT INTO data_source (source_id, source_name, source_type, is_active)
VALUES ('PYKRX', 'pykrx 한국주식 시세 API', 'API', true)
ON CONFLICT (source_id) DO NOTHING;

INSERT INTO data_source (source_id, source_name, source_type, is_active)
VALUES ('KRX_TS', 'KRX TimeSeries 마이그레이션', 'MIGRATION', true)
ON CONFLICT (source_id) DO NOTHING;

-- ============================================================
-- 1. stock_price_daily 스키마 변경
-- ============================================================

-- updated_at 컬럼 추가 (없는 경우에만)
ALTER TABLE stock_price_daily
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;

-- source_id 인덱스 추가 (없는 경우에만)
CREATE INDEX IF NOT EXISTS idx_stock_price_source
ON stock_price_daily (source_id);

-- ============================================================
-- 2. Phase 1: stocks_daily_prices → stock_price_daily
--    Source: pykrx_loader 적재 데이터
-- ============================================================

-- 백업
CREATE TABLE IF NOT EXISTS stocks_daily_prices_backup AS
SELECT * FROM stocks_daily_prices;

INSERT INTO stock_price_daily (
    ticker, trade_date, open_price, high_price, low_price,
    close_price, volume, change_rate,
    source_id, as_of_date, quality_flag, created_at
)
SELECT
    code,                   -- code → ticker
    date,                   -- date → trade_date
    open_price,
    high_price,
    low_price,
    close_price,
    volume,
    change_rate,
    'PYKRX',                -- source_id
    date,                   -- as_of_date = trade_date
    'NORMAL',               -- quality_flag
    NOW()
FROM stocks_daily_prices
WHERE close_price > 0      -- CheckConstraint 준수
  AND volume >= 0
  AND high_price >= low_price
ON CONFLICT ON CONSTRAINT uq_stock_price_daily DO NOTHING;

-- ============================================================
-- 3. Phase 2: krx_timeseries → stock_price_daily
--    Source: 레거시 KRX 적재 데이터
--    Float → Numeric 변환 포함
-- ============================================================

-- 백업
CREATE TABLE IF NOT EXISTS krx_timeseries_backup AS
SELECT * FROM krx_timeseries;

INSERT INTO stock_price_daily (
    ticker, trade_date, open_price, high_price, low_price,
    close_price, volume,
    source_id, as_of_date, quality_flag, created_at
)
SELECT
    ticker,
    date,                            -- date → trade_date
    ROUND(open::numeric, 2),         -- Float → Numeric(18,2)
    ROUND(high::numeric, 2),
    ROUND(low::numeric, 2),
    ROUND(close::numeric, 2),
    volume,
    'KRX_TS',                        -- source_id
    date,                            -- as_of_date = trade_date
    'MIGRATED',                      -- quality_flag
    COALESCE(created_at, NOW())
FROM krx_timeseries
WHERE close > 0                      -- CheckConstraint 준수
  AND volume >= 0
  AND high >= low
ON CONFLICT ON CONSTRAINT uq_stock_price_daily DO NOTHING;

-- ============================================================
-- 4. 사후 검증
-- ============================================================

-- 레코드 수 비교
SELECT 'stock_price_daily' AS table_name, COUNT(*) AS cnt FROM stock_price_daily
UNION ALL
SELECT 'stocks_daily_prices_backup', COUNT(*) FROM stocks_daily_prices_backup
UNION ALL
SELECT 'krx_timeseries_backup', COUNT(*) FROM krx_timeseries_backup;

-- source_id별 분포 확인
SELECT source_id, quality_flag, COUNT(*)
FROM stock_price_daily
GROUP BY source_id, quality_flag
ORDER BY source_id;

-- 마이그레이션 누락 확인 (0건이어야 정상)
SELECT COUNT(*) AS missed_stocks_daily
FROM stocks_daily_prices sdp
WHERE NOT EXISTS (
    SELECT 1 FROM stock_price_daily spd
    WHERE spd.ticker = sdp.code
      AND spd.trade_date = sdp.date
      AND spd.source_id = 'PYKRX'
)
AND sdp.close_price > 0
AND sdp.volume >= 0
AND sdp.high_price >= sdp.low_price;

SELECT COUNT(*) AS missed_krx_ts
FROM krx_timeseries kt
WHERE NOT EXISTS (
    SELECT 1 FROM stock_price_daily spd
    WHERE spd.ticker = kt.ticker
      AND spd.trade_date = kt.date
      AND spd.source_id = 'KRX_TS'
)
AND kt.close > 0
AND kt.volume >= 0
AND kt.high >= kt.low;

-- ============================================================
-- 롤백 (필요시 수동 실행)
-- ============================================================
-- DELETE FROM stock_price_daily WHERE source_id IN ('PYKRX', 'KRX_TS');
--
-- DROP TABLE IF EXISTS stocks_daily_prices;
-- ALTER TABLE stocks_daily_prices_backup RENAME TO stocks_daily_prices;
--
-- DROP TABLE IF EXISTS krx_timeseries;
-- ALTER TABLE krx_timeseries_backup RENAME TO krx_timeseries;
