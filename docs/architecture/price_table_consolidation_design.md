# 한국 주식 일별 시세 테이블 통합 설계서

> **문서 유형**: 아키텍처 설계서
> **작성일**: 2026-02-09
> **상태**: Draft
> **우선순위**: Priority 1 (Critical)
> **관련 보고서**: `docs/reports/krx_timeseries_operations_report.md`

---

## 1. 개요 & 목표

### 1.1 현재 문제

운용 분석 보고서에서 다음 Critical 이슈가 식별되었다:

1. **4개 분산 테이블**: 동일 목적(한국 주식 OHLCV)의 데이터가 4개 테이블에 분산 저장
2. **백테스팅 엔진 단절**: 백테스팅 엔진(`backtesting.py`)이 참조하는 `krx_timeseries`와 실제 적재 대상(`stocks_daily_prices`)이 서로 다른 테이블
3. **타입 불일치**: `Float`(krx_timeseries) vs `Numeric(18,2)`(stock_price_daily, stocks_daily_prices) — 금융 데이터에 부동소수점 사용은 정밀도 리스크
4. **거버넌스 부재**: `krx_timeseries`, `stocks_daily_prices` 모두 source_id, batch_id, quality_flag 없음

### 1.2 목표

- **`stock_price_daily` 단일 테이블로 통합** (가장 완성도 높은 스키마)
- 백테스팅 엔진과 적재 파이프라인을 동일 테이블로 연결
- `Float` → `Numeric(18,2)` 통일로 금융 데이터 정밀도 확보
- 데이터 거버넌스(source_id, batch_id, quality_flag) 일관 적용

### 1.3 범위

- **대상**: 한국 주식 일별 시세 3개 테이블 → `stock_price_daily` 1개로 통합
- **제외**: `alpha_vantage_timeseries` — 미국 주식 전용이며 `symbol` 컬럼, `adjusted_close` 고유 속성 보유. `backtesting.py`에서 이미 한국/미국 분기 처리 중(`ticker.isdigit()` 조건)이므로 별도 유지

---

## 2. 현재 상태 분석 (AS-IS)

### 2.1 4개 테이블 비교

| 항목 | `stock_price_daily` | `stocks_daily_prices` | `krx_timeseries` | `alpha_vantage_timeseries` |
|------|--------------------|-----------------------|-------------------|---------------------------|
| **모델** | `StockPriceDaily` | `StocksDailyPrice` | `KrxTimeSeries` | `AlphaVantageTimeSeries` |
| **모델 파일** | `real_data.py:98` | `real_data.py:529` | `securities.py:531` | `alpha_vantage.py:149` |
| **PK** | `price_id` (auto) | `(code, date)` 복합PK | `id` (auto) | `id` (auto) |
| **가격 타입** | `Numeric(18,2)` | `Numeric(18,2)` | **`Float`** | **`Float`** |
| **컬럼 수** | 18 | 8 | 7 | 8 |
| **Unique 제약** | `(ticker, trade_date, source_id)` | PK 자체 | 없음 | 없음 |
| **거버넌스** | source_id, batch_id, quality_flag | 없음 | 없음 | 없음 |
| **CheckConstraint** | close>0, vol>=0, H>=L | 없음 | 없음 | 없음 |
| **적재 현황** | **0건** (미사용) | ~420건 (pykrx) | ~2,155건 (krx_timeseries.py) | 0건 |
| **코드 참조** | 3개 파일 | 5개 파일 | **18개 파일** | 별도 유지 |

### 2.2 소비자(Consumer) 영향도 분석

#### KrxTimeSeries (18개 파일 참조, HIGH)

| 카테고리 | 파일 | 사용 방식 |
|---------|------|----------|
| **모델 정의** | `securities.py:531`, `models/__init__.py` | 모델 선언, export |
| **핵심 서비스** | `backtesting.py:228-264` | `_get_historical_price()` — 한국주식 가격 조회 |
| **핵심 서비스** | `phase7_evaluation.py:112-168` | `_load_security_series()`, `_load_sector_series()` |
| **라우트** | `krx_timeseries.py:22-100` | 단건/다건 적재 API |
| **라우트** | `stock_detail.py:42-46` | 종목 상세 시계열 조회 |
| **라우트** | `batch_jobs.py:240-258` | 배치 적재 |
| **라우트** | `phase7_evaluation.py` (route) | phase7 평가 라우트 |
| **테스트** | `test_phase7_evaluation.py`, `test_phase7_comparison.py` | 통합 테스트 (2개) |
| **테스트** | `test_phase9_*.py` (6개), `test_phase10_*.py` (1개) | E2E 테스트 (7개) |

#### StocksDailyPrice (5개 파일 참조, MEDIUM)

| 카테고리 | 파일 | 사용 방식 |
|---------|------|----------|
| **모델 정의** | `real_data.py:529`, `models/__init__.py` | 모델 선언, export |
| **핵심 서비스** | `pykrx_loader.py:966-1078` | `load_daily_prices_batch()` — 배치 upsert |
| **테스트** | `test_pykrx_batch.py`, `test_pykrx_parallel.py` | 단위 테스트 (2개) |

#### StockPriceDaily (3개 파일 참조, LOW)

| 카테고리 | 파일 | 사용 방식 |
|---------|------|----------|
| **모델 정의** | `real_data.py:98`, `models/__init__.py` | 모델 선언, export |
| **서비스** | `real_data_loader.py` | import만 존재 (실제 적재 로직 미구현) |

### 2.3 핵심 단절 지점

```
pykrx_loader.py ─── 적재 ──→ stocks_daily_prices (StocksDailyPrice)
                                     ╳ 단절
backtesting.py ──── 조회 ──→ krx_timeseries (KrxTimeSeries)
phase7_evaluation.py ─ 조회 → krx_timeseries (KrxTimeSeries)
```

이로 인해 `pykrx_loader`로 적재한 데이터를 백테스팅에서 사용할 수 없다.

---

## 3. 통합 후 설계 (TO-BE)

### 3.1 대상 테이블: `stock_price_daily` (StockPriceDaily)

기존 `real_data.py:98-148`에 정의된 모델을 그대로 활용한다. 이미 다음을 갖추고 있다:

- `Numeric(18,2)` 가격 타입
- `source_id`, `batch_id` 거버넌스 컬럼
- `quality_flag`, `is_verified` 품질 관리
- `UniqueConstraint('ticker', 'trade_date', 'source_id')`
- `CheckConstraint` 3개 (close>0, volume>=0, high>=low)
- 4개 인덱스 (ticker+date, date, as_of_date, batch_id)

#### 추가 변경사항

```python
# real_data.py:98-148 StockPriceDaily에 추가
updated_at = Column(DateTime, onupdate=kst_now)  # 업데이트 타임스탬프
```

```python
# __table_args__에 인덱스 추가
Index('idx_stock_price_source', 'source_id'),  # source_id 단독 인덱스
```

#### 통합 후 데이터 흐름

```
pykrx_loader.py ─── 적재 ──→ stock_price_daily (StockPriceDaily)
                                     ↑ 통합
backtesting.py ──── 조회 ──→ stock_price_daily (StockPriceDaily)
phase7_evaluation.py ─ 조회 → stock_price_daily (StockPriceDaily)
stock_detail.py ──── 조회 ──→ stock_price_daily (StockPriceDaily)
batch_jobs.py ──── 적재 ──→ stock_price_daily (StockPriceDaily)
```

### 3.2 source_id 전략

`stock_price_daily.source_id`는 `data_source` 테이블에 대한 FK이다. 다음 레코드를 사전 등록해야 한다:

| source_id | 설명 | 용도 |
|-----------|------|------|
| `PYKRX` | pykrx API | 신규 적재 (pykrx_loader, batch_jobs) |
| `KRX_TS` | KRX TimeSeries 마이그레이션 | krx_timeseries 레거시 데이터 |

- 신규 pykrx 적재: `source_id='PYKRX'`
- 레거시 krx_timeseries 마이그레이션: `source_id='KRX_TS'`, `quality_flag='MIGRATED'`

### 3.3 ON CONFLICT 전략 변경

**변경 전** (pykrx_loader.py:1044-1055):
```python
# stocks_daily_prices의 복합PK
stmt = pg_insert(table).values(chunk)
stmt = stmt.on_conflict_do_update(
    index_elements=['code', 'date'],  # PRIMARY KEY
    set_={...}
)
```

**변경 후**:
```python
# stock_price_daily의 UniqueConstraint
stmt = pg_insert(StockPriceDaily.__table__).values(chunk)
stmt = stmt.on_conflict_do_update(
    constraint='uq_stock_price_daily',  # (ticker, trade_date, source_id)
    set_={
        'open_price': stmt.excluded.open_price,
        'high_price': stmt.excluded.high_price,
        'low_price': stmt.excluded.low_price,
        'close_price': stmt.excluded.close_price,
        'volume': stmt.excluded.volume,
        'change_rate': stmt.excluded.change_rate,
        'updated_at': func.now(),
    }
)
```

### 3.4 컬럼 매핑

| 원본 (StocksDailyPrice / KrxTimeSeries) | 대상 (StockPriceDaily) | 변환 |
|-----------------------------------------|----------------------|------|
| `code` / `ticker` | `ticker` | 직접 매핑 |
| `date` / `date` | `trade_date` | 직접 매핑 |
| `open_price` / `open` | `open_price` | Numeric / `Decimal(str(float))` |
| `high_price` / `high` | `high_price` | Numeric / `Decimal(str(float))` |
| `low_price` / `low` | `low_price` | Numeric / `Decimal(str(float))` |
| `close_price` / `close` | `close_price` | Numeric / `Decimal(str(float))` |
| `volume` / `volume` | `volume` | int |
| `change_rate` / — | `change_rate` | Numeric / NULL |
| — | `source_id` | `'PYKRX'` 또는 `'KRX_TS'` |
| — | `as_of_date` | `trade_date`와 동일 값 |
| — | `quality_flag` | `'NORMAL'` 또는 `'MIGRATED'` |

### 3.5 AlphaVantageTimeSeries 처리

**별도 유지** — 미국 주식 전용 테이블로 통합 대상에서 제외한다.

근거:
- `symbol` 컬럼 (ticker와 형식 상이: `'AAPL'` vs `'005930'`)
- `adjusted_close` 고유 컬럼 (미국 주식 수정종가)
- `backtesting.py:218-226`에서 이미 한국/미국 분기 처리: `ticker.isdigit()` 조건으로 분기

---

## 4. 데이터 마이그레이션 계획

### 4.1 사전 준비

```sql
-- 1. data_source 레코드 등록
INSERT INTO data_source (source_id, source_name, source_type, is_active)
VALUES ('PYKRX', 'pykrx 한국주식 시세 API', 'API', true)
ON CONFLICT (source_id) DO NOTHING;

INSERT INTO data_source (source_id, source_name, source_type, is_active)
VALUES ('KRX_TS', 'KRX TimeSeries 마이그레이션', 'MIGRATION', true)
ON CONFLICT (source_id) DO NOTHING;
```

### 4.2 마이그레이션 SQL 스크립트

파일: `backend/scripts/migrate_price_tables.sql`

```sql
-- ============================================================
-- Phase 1: stocks_daily_prices → stock_price_daily
-- Source: pykrx_loader 적재 데이터 (~420건)
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
-- Phase 2: krx_timeseries → stock_price_daily
-- Source: 레거시 KRX 적재 데이터 (~2,155건)
-- Float → Numeric 변환 포함
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
```

### 4.3 사후 검증

```sql
-- 레코드 수 비교
SELECT 'stock_price_daily' AS table_name, COUNT(*) AS cnt FROM stock_price_daily
UNION ALL
SELECT 'stocks_daily_prices_backup', COUNT(*) FROM stocks_daily_prices_backup
UNION ALL
SELECT 'krx_timeseries_backup', COUNT(*) FROM krx_timeseries_backup;

-- source_id별 분포 확인
SELECT source_id, quality_flag, COUNT(*)
FROM stock_price_daily
GROUP BY source_id, quality_flag;

-- 마이그레이션 누락 확인 (0건이어야 정상)
SELECT COUNT(*) AS missed_stocks_daily
FROM stocks_daily_prices sdp
WHERE NOT EXISTS (
    SELECT 1 FROM stock_price_daily spd
    WHERE spd.ticker = sdp.code AND spd.trade_date = sdp.date AND spd.source_id = 'PYKRX'
)
AND sdp.close_price > 0 AND sdp.volume >= 0 AND sdp.high_price >= sdp.low_price;

SELECT COUNT(*) AS missed_krx_ts
FROM krx_timeseries kt
WHERE NOT EXISTS (
    SELECT 1 FROM stock_price_daily spd
    WHERE spd.ticker = kt.ticker AND spd.trade_date = kt.date AND spd.source_id = 'KRX_TS'
)
AND kt.close > 0 AND kt.volume >= 0 AND kt.high >= kt.low;
```

### 4.4 롤백 전략

마이그레이션 전 백업 테이블이 자동 생성되므로:

```sql
-- stock_price_daily에서 마이그레이션 데이터만 삭제
DELETE FROM stock_price_daily WHERE source_id IN ('PYKRX', 'KRX_TS');

-- 원본 테이블 복원 (필요시)
DROP TABLE IF EXISTS stocks_daily_prices;
ALTER TABLE stocks_daily_prices_backup RENAME TO stocks_daily_prices;

DROP TABLE IF EXISTS krx_timeseries;
ALTER TABLE krx_timeseries_backup RENAME TO krx_timeseries;
```

코드 롤백은 `git revert` 사용.

---

## 5. 코드 변경 목록

### 5.1 Backend 서비스 (핵심 3개)

| 파일 | 위치 | 변경 내용 | 영향도 |
|------|------|----------|--------|
| `pykrx_loader.py` | 966-1078 | `StocksDailyPrice` → `StockPriceDaily`, column mapping (`code`→`ticker`, `date`→`trade_date`), ON CONFLICT `constraint='uq_stock_price_daily'`, `source_id`/`batch_id`/`as_of_date` 추가, `Table()` 대신 `StockPriceDaily.__table__` 사용 | **HIGH** |
| `pykrx_loader.py` | 1177-1337 | `load_all_daily_prices_parallel()` — BatchManager 연동 (batch_id 전달), source_id 파라미터 추가 | **HIGH** |
| `backtesting.py` | 228-264 | `KrxTimeSeries` → `StockPriceDaily`, `.close` → `.close_price`, `.date` → `.trade_date` | **HIGH** |
| `phase7_evaluation.py` | 112-168 | `KrxTimeSeries` → `StockPriceDaily`, `.close` → `.close_price`, `.date` → `.trade_date` (`_load_security_series`, `_load_sector_series` 2개 메서드) | **HIGH** |

### 5.2 Backend 라우트 (4개)

| 파일 | 위치 | 변경 내용 |
|------|------|----------|
| `admin.py` | 2696-2768 | `BatchManager.create_batch()` 호출 추가, `batch_id`를 `run_load_task()`에 전달 |
| `krx_timeseries.py` | 22-100 | `KrxTimeSeries` → `StockPriceDaily`, column mapping 적용, `source_id='PYKRX'`/`as_of_date` 추가. 또는 DEPRECATED 주석 + `admin.py`의 pykrx 엔드포인트로 리다이렉트 |
| `stock_detail.py` | 42-46 | `KrxTimeSeries` → `StockPriceDaily`, `.close` → `.close_price`, `.date` → `.trade_date` |
| `batch_jobs.py` | 240-258 | `KrxTimeSeries` → `StockPriceDaily`, column mapping, `source_id`/`as_of_date` 추가 |

### 5.3 Backend 모델 (3개)

| 파일 | 위치 | 변경 내용 |
|------|------|----------|
| `real_data.py` | 98-148 | `StockPriceDaily`에 `updated_at` 컬럼 추가, `idx_stock_price_source` 인덱스 추가 |
| `real_data.py` | 529-557 | `StocksDailyPrice` 클래스에 `# DEPRECATED: stock_price_daily로 통합됨` 주석 |
| `securities.py` | 531-548 | `KrxTimeSeries` 클래스에 `# DEPRECATED: stock_price_daily로 통합됨` 주석 |

### 5.4 테스트 (11개)

| 카테고리 | 파일 | 변경 내용 |
|---------|------|----------|
| **Unit** | `test_pykrx_batch.py` | import 변경, 쿼리 대상 `StockPriceDaily`, `source_id` assertion 추가 |
| **Unit** | `test_pykrx_parallel.py` | 동일 패턴 |
| **Integration** | `test_phase7_evaluation.py` | `_seed_timeseries()` 헬퍼를 `StockPriceDaily`로 변경, column mapping |
| **Integration** | `test_phase7_comparison.py` | 동일 패턴 |
| **E2E** | `test_phase9_evaluation_flow.py` | `_seed_timeseries()` → `StockPriceDaily` + source_id/as_of_date |
| **E2E** | `test_phase9_comparison.py` | 동일 패턴 |
| **E2E** | `test_phase9_reproducibility.py` | 동일 패턴 |
| **E2E** | `test_phase9_error_handling.py` | 동일 패턴 |
| **E2E** | `test_phase9_audit_log.py` | 동일 패턴 |
| **E2E** | `test_phase9_rate_limit.py` | 동일 패턴 |
| **E2E** | `test_phase9_timeout_retry.py` | 동일 패턴 |
| **E2E** | `test_phase10_edge_cases.py` | 동일 패턴 |

### 5.5 라우트 (추가)

| 파일 | 변경 내용 |
|------|----------|
| `routes/phase7_evaluation.py` | import `KrxTimeSeries` 제거 (사용하지 않는 경우) 또는 `StockPriceDaily`로 변경 |
| `models/__init__.py` | `StockPriceDaily` export 확인, 레거시 모델은 유지 (DB 마이그레이션 필요) |

---

## 6. 구현 순서

### Step 1: 모델 변경 + 마이그레이션 준비

1. `StockPriceDaily`에 `updated_at`, `idx_stock_price_source` 추가
2. `data_source`에 'PYKRX', 'KRX_TS' 레코드 등록
3. DB migration 실행 (`alembic` 또는 수동 DDL)

### Step 2: pykrx_loader 전환

1. `load_daily_prices_batch()` — 대상 테이블 변경, column mapping, source_id 추가
2. `load_all_daily_prices_parallel()` — BatchManager 연동
3. Unit 테스트 수정 및 통과 확인

### Step 3: 소비자(Consumer) 전환

1. `backtesting.py` — `StockPriceDaily` 전환
2. `phase7_evaluation.py` — `StockPriceDaily` 전환
3. `stock_detail.py`, `batch_jobs.py` — 전환
4. `krx_timeseries.py` — DEPRECATED 처리
5. Integration/E2E 테스트 수정 및 통과 확인

### Step 4: 데이터 마이그레이션

1. `migrate_price_tables.sql` 실행
2. 사후 검증 쿼리 실행
3. 레코드 수 정합성 확인

### Step 5: 정리

1. 레거시 모델에 DEPRECATED 주석
2. 전체 테스트 스위트 실행 (`pytest -v`)
3. 운영 데이터 검증

---

## 7. 리스크 평가

| 리스크 | 영향 | 확률 | 완화 방안 |
|--------|------|------|----------|
| **Float→Numeric 정밀도 손실** | Medium | Low | `ROUND(float::numeric, 2)` 안전 변환. Python에서 `Decimal(str(round(v, 2)))` 사용 |
| **KrxTimeSeries 18개 참조 누락** | High | Medium | `grep -r "KrxTimeSeries" backend/` 전수 검사 + 전체 테스트 커버리지 확인 |
| **source_id FK 위반** | High | Medium | 마이그레이션 전 `data_source` 레코드 등록 필수. Step 1에서 선행 |
| **ON CONFLICT 동작 변경** | Medium | Low | `constraint='uq_stock_price_daily'`는 3-column unique (`ticker`, `trade_date`, `source_id`). 동일 source에서 같은 날짜 재적재 시 UPDATE 동작 보장 |
| **성능 퇴화** | Medium | Low | 기존 `pg_insert().on_conflict_do_update()` 배치 패턴 유지. 인덱스 추가로 조회 성능 유지 |
| **데이터 손실** | High | Very Low | 백업 테이블 자동 생성 (`CREATE TABLE AS SELECT`), `ON CONFLICT DO NOTHING` 안전 처리, 롤백 스크립트 준비 |
| **테스트 일괄 실패** | Medium | Medium | Step 2/3에서 단위→통합→E2E 순서로 점진적 전환. 각 단계별 `pytest` 실행 |

---

## 부록 A: StockPriceDaily 최종 스키마

```python
class StockPriceDaily(Base):
    """주식 일별 시세 (통합 테이블)"""
    __tablename__ = "stock_price_daily"

    price_id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False)       # '005930'
    trade_date = Column(Date, nullable=False)          # 거래일

    # OHLCV
    open_price = Column(Numeric(18, 2), nullable=False)
    high_price = Column(Numeric(18, 2), nullable=False)
    low_price = Column(Numeric(18, 2), nullable=False)
    close_price = Column(Numeric(18, 2), nullable=False)
    volume = Column(BigInteger, nullable=False)

    # 추가 지표
    adj_close_price = Column(Numeric(18, 2))           # 수정 종가
    market_cap = Column(BigInteger)                     # 시가총액
    trading_value = Column(BigInteger)                  # 거래대금
    shares_outstanding = Column(BigInteger)             # 발행주식수

    # 전일 대비
    prev_close = Column(Numeric(18, 2))
    price_change = Column(Numeric(18, 2))
    change_rate = Column(Numeric(8, 4))                # 등락률 (%)

    # 데이터 거버넌스
    source_id = Column(String(20), ForeignKey("data_source.source_id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("data_load_batch.batch_id"))
    as_of_date = Column(Date, nullable=False)          # 데이터 기준일

    # 품질
    is_verified = Column(Boolean, default=False)
    quality_flag = Column(String(10), default='NORMAL')

    created_at = Column(DateTime, default=kst_now)
    updated_at = Column(DateTime, onupdate=kst_now)    # [신규]

    __table_args__ = (
        UniqueConstraint('ticker', 'trade_date', 'source_id', name='uq_stock_price_daily'),
        Index('idx_stock_price_ticker_date', 'ticker', 'trade_date'),
        Index('idx_stock_price_date', 'trade_date'),
        Index('idx_stock_price_asof', 'as_of_date'),
        Index('idx_stock_price_batch', 'batch_id'),
        Index('idx_stock_price_source', 'source_id'),  # [신규]
        CheckConstraint('close_price > 0', name='chk_stock_price_close_positive'),
        CheckConstraint('volume >= 0', name='chk_stock_price_volume_nonnegative'),
        CheckConstraint('high_price >= low_price', name='chk_stock_price_high_low'),
    )
```

## 부록 B: pykrx_loader 레코드 변환 예시 (변경 후)

```python
record = {
    'ticker': ticker,                    # code → ticker
    'trade_date': trade_date,            # date → trade_date
    'open_price': Decimal(str(row['시가'])) if pd.notna(row['시가']) else Decimal('0'),
    'high_price': Decimal(str(row['고가'])) if pd.notna(row['고가']) else Decimal('0'),
    'low_price': Decimal(str(row['저가'])) if pd.notna(row['저가']) else Decimal('0'),
    'close_price': Decimal(str(row['종가'])) if pd.notna(row['종가']) else Decimal('0'),
    'volume': int(row['거래량']) if pd.notna(row['거래량']) else 0,
    'change_rate': Decimal(str(row['등락률'])) if '등락률' in row and pd.notna(row['등락률']) else None,
    'source_id': 'PYKRX',               # [신규]
    'as_of_date': trade_date,            # [신규]
    'quality_flag': 'NORMAL',            # [신규]
}
```
