# 한국 주식 일별 시세 테이블 통합 Phase 2 설계서: 레거시 제거 및 데이터 마이그레이션

> **문서 유형**: 아키텍처 설계서
> **작성일**: 2026-02-10
> **상태**: Draft
> **우선순위**: Priority 1 (Critical)
> **선행 문서**: `docs/architecture/price_table_consolidation_design.md` (Phase 1)
> **마이그레이션 스크립트**: `backend/scripts/migrate_price_tables.sql`

---

## 1. 개요

### 1.1 Phase 1 완료 요약

Phase 1(코드 전환)이 완료되어 모든 런타임 코드가 `StockPriceDaily` 단일 모델을 참조한다.

| 카테고리 | 전환 현황 |
|---------|----------|
| **서비스** | `pykrx_loader.py`, `backtesting.py`, `phase7_evaluation.py` → `StockPriceDaily` 전환 완료 |
| **라우트** | `admin.py`, `krx_timeseries.py`, `stock_detail.py`, `batch_jobs.py` → `StockPriceDaily` 전환 완료 |
| **테스트** | 19개 파일 → `StockPriceDaily` 전환 완료 (638 passed, 2 pre-existing failures) |
| **conftest.py** | SQLite → PostgreSQL 마이그레이션 완료 |

### 1.2 Phase 2 목표

Phase 1에서 코드만 전환했으므로, Phase 2에서는 **데이터 마이그레이션**과 **레거시 코드/테이블 완전 제거**를 수행한다.

1. 레거시 테이블 데이터(`stocks_daily_prices`, `krx_timeseries`)를 `stock_price_daily`로 마이그레이션
2. deprecated 모델 정의(`StocksDailyPrice`, `KrxTimeSeries`) 완전 삭제
3. 레거시 import/export 정리 (`models/__init__.py`)
4. 불필요한 라우터 등록 제거 (`main.py`)
5. 레거시 DB 테이블 DROP

### 1.3 잔존 항목 목록

| 위치 | 내용 | 유형 |
|------|------|------|
| `app/models/real_data.py:531-561` | `StocksDailyPrice` 클래스 정의 (DEPRECATED 주석 포함) | 모델 |
| `app/models/securities.py:531-552` | `KrxTimeSeries` 클래스 정의 (DEPRECATED 주석 포함) | 모델 |
| `app/models/__init__.py:2` | `from .securities import KrxTimeSeries` import | import |
| `app/models/__init__.py:34` | `StocksDailyPrice` import | import |
| `app/models/__init__.py:38,54,71` | `__all__`에 두 모델 포함 | export |
| `app/main.py:20` | `krx_timeseries` 라우터 import | import |
| `app/main.py:259` | `app.include_router(krx_timeseries.router)` | 라우터 등록 |
| `app/routes/stock_detail.py:29` | `"krx_timeseries 테이블"` 주석 | 주석 |
| `scripts/load_market_data.py:290` | `Table("stocks_daily_prices", ...)` 직접 참조 | 스크립트 |

### 1.4 DB 테이블 현황

| 테이블 | 레코드 수 | 상태 |
|--------|----------|------|
| `stock_price_daily` | 0건 | 신규 (마이그레이션 대기) |
| `stocks_daily_prices` | ~420건 | deprecated (마이그레이션 필요) |
| `krx_timeseries` | ~2,155건 | deprecated (마이그레이션 필요) |

---

## 2. 데이터 마이그레이션

### 2.1 마이그레이션 스크립트

이미 작성 완료: `backend/scripts/migrate_price_tables.sql`

### 2.2 사전 준비

`data_source` 테이블에 마이그레이션용 레코드가 등록되어 있어야 한다.

```sql
INSERT INTO data_source (source_id, source_name, source_type, is_active)
VALUES ('PYKRX', 'pykrx 한국주식 시세 API', 'API', true)
ON CONFLICT (source_id) DO NOTHING;

INSERT INTO data_source (source_id, source_name, source_type, is_active)
VALUES ('KRX_TS', 'KRX TimeSeries 마이그레이션', 'MIGRATION', true)
ON CONFLICT (source_id) DO NOTHING;
```

### 2.3 스키마 변경

```sql
-- updated_at 컬럼 추가 (Phase 1 설계서에서 정의)
ALTER TABLE stock_price_daily
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;

-- source_id 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_stock_price_source
ON stock_price_daily (source_id);
```

### 2.4 Phase 2-1: stocks_daily_prices → stock_price_daily

- **대상**: pykrx_loader 적재 데이터 (~420건)
- **source_id**: `'PYKRX'`
- **quality_flag**: `'NORMAL'`
- **컬럼 매핑**: `code` → `ticker`, `date` → `trade_date`
- **타입 변환**: 없음 (양쪽 모두 `Numeric(18,2)`)
- **중복 처리**: `ON CONFLICT ON CONSTRAINT uq_stock_price_daily DO NOTHING`
- **데이터 필터**: `close_price > 0 AND volume >= 0 AND high_price >= low_price` (CheckConstraint 준수)

### 2.5 Phase 2-2: krx_timeseries → stock_price_daily

- **대상**: 레거시 KRX 적재 데이터 (~2,155건)
- **source_id**: `'KRX_TS'`
- **quality_flag**: `'MIGRATED'`
- **컬럼 매핑**: `ticker` → `ticker` (동일), `date` → `trade_date`, `open/high/low/close` → `open_price/high_price/low_price/close_price`
- **타입 변환**: `Float` → `Numeric(18,2)` — `ROUND(column::numeric, 2)` 사용
- **중복 처리**: `ON CONFLICT ON CONSTRAINT uq_stock_price_daily DO NOTHING`
- **데이터 필터**: `close > 0 AND volume >= 0 AND high >= low`
- **created_at 보존**: `COALESCE(created_at, NOW())` — 원본 타임스탬프 유지

### 2.6 사후 검증

마이그레이션 실행 후 아래 쿼리로 결과를 확인한다.

#### 2.6.1 레코드 수 비교

```sql
SELECT 'stock_price_daily' AS table_name, COUNT(*) AS cnt FROM stock_price_daily
UNION ALL
SELECT 'stocks_daily_prices_backup', COUNT(*) FROM stocks_daily_prices_backup
UNION ALL
SELECT 'krx_timeseries_backup', COUNT(*) FROM krx_timeseries_backup;
```

**기대 결과**: `stock_price_daily` 레코드 수 ≥ `stocks_daily_prices_backup` + `krx_timeseries_backup` (중복 제거로 약간 작을 수 있음)

#### 2.6.2 source_id별 분포

```sql
SELECT source_id, quality_flag, COUNT(*)
FROM stock_price_daily
GROUP BY source_id, quality_flag
ORDER BY source_id;
```

**기대 결과**:

| source_id | quality_flag | count |
|-----------|-------------|-------|
| `KRX_TS` | `MIGRATED` | ~2,155 |
| `PYKRX` | `NORMAL` | ~420 |

#### 2.6.3 마이그레이션 누락 확인

```sql
-- 0건이어야 정상
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

**기대 결과**: 양쪽 모두 0건

---

## 3. 레거시 모델 제거

### 3.1 StocksDailyPrice 삭제

**파일**: `backend/app/models/real_data.py`
**위치**: 라인 527-561

삭제 대상:
```python
# ============================================================================
# Phase 11: 주식 일별 시세 (stocks_daily_prices DDL 기준)
# ============================================================================

class StocksDailyPrice(Base):
    """주식 일별 시세 (stocks_daily_prices 테이블)
    DEPRECATED: stock_price_daily(StockPriceDaily)로 통합됨.
    마이그레이션 완료 후 제거 예정.
    ...
    """
    __tablename__ = "stocks_daily_prices"
    # ... (전체 클래스)
```

### 3.2 KrxTimeSeries 삭제

**파일**: `backend/app/models/securities.py`
**위치**: 라인 531-552

삭제 대상:
```python
class KrxTimeSeries(Base):
    """한국거래소 시계열 데이터 (일별)
    DEPRECATED: stock_price_daily(StockPriceDaily)로 통합됨.
    마이그레이션 완료 후 제거 예정.
    """
    __tablename__ = "krx_timeseries"
    # ... (전체 클래스)
```

### 3.3 models/__init__.py 정리

**파일**: `backend/app/models/__init__.py`

변경 내용:

| 라인 | 변경 전 | 변경 후 |
|------|--------|--------|
| 2 | `from .securities import KrxTimeSeries` | 삭제 |
| 34 | `StocksDailyPrice` import | 삭제 |
| 38 | `__all__`에 `'KrxTimeSeries'` 포함 | 제거 |
| 54 | `__all__`에 `'StocksDailyPrice'` 포함 | 제거 |
| 71 | 두 번째 `__all__`에 `'KrxTimeSeries'` 포함 | 제거 |

---

## 4. 라우트 및 스크립트 정리

### 4.1 krx_timeseries 라우터 제거

`krx_timeseries.py`의 기능은 `admin.py`의 pykrx 엔드포인트(`POST /admin/pykrx/load-daily-prices`)와 중복된다. Phase 1에서 코드가 `StockPriceDaily`로 전환되었으므로 라우터 등록을 제거한다.

**main.py 변경**:

| 라인 | 변경 전 | 변경 후 |
|------|--------|--------|
| 20 | `from app.routes import ..., krx_timeseries, ...` | `krx_timeseries` 제거 |
| 259 | `app.include_router(krx_timeseries.router)` | 삭제 |

**파일 처리**: `app/routes/krx_timeseries.py`는 삭제하지 않고 유지한다. 라우터 등록만 해제하여 API 노출을 차단하되, 코드 레퍼런스로서 보관한다. 필요시 추후 완전 삭제 가능.

### 4.2 stock_detail.py 주석 업데이트

**파일**: `backend/app/routes/stock_detail.py`
**위치**: 라인 29

| 변경 전 | 변경 후 |
|--------|--------|
| `시계열 데이터 (krx_timeseries 테이블, 최근 N일)` | `시계열 데이터 (stock_price_daily 테이블, 최근 N일)` |

### 4.3 load_market_data.py 스크립트 수정

**파일**: `backend/scripts/load_market_data.py`
**위치**: 라인 290

| 변경 전 | 변경 후 |
|--------|--------|
| `Table("stocks_daily_prices", meta, autoload_with=engine)` | `Table("stock_price_daily", meta, autoload_with=engine)` |

아울러 `on_conflict_do_nothing(index_elements=["code", "date"])` → `on_conflict_do_nothing(constraint='uq_stock_price_daily')` 변경, 컬럼 매핑(`code`→`ticker`, `date`→`trade_date`) 적용.

> **주의**: 이 스크립트가 실제 운영에서 사용되는지 확인 필요. 현재 주요 적재는 `admin.py` 엔드포인트를 통해 수행되므로, 사용하지 않는 경우 DEPRECATED 주석만 추가하는 것도 가능.

---

## 5. DB 테이블 DROP

마이그레이션 검증(섹션 2.6)이 **완전히 완료**된 후에만 실행한다.

### 5.1 레거시 테이블 삭제

```sql
-- 마이그레이션 검증 완료 후 실행
DROP TABLE IF EXISTS stocks_daily_prices CASCADE;
DROP TABLE IF EXISTS krx_timeseries CASCADE;
```

### 5.2 백업 테이블 정리

마이그레이션 데이터 정합성이 충분히 확인된 후 (최소 1주일 운영 후) 백업 테이블을 삭제한다.

```sql
-- 충분한 검증 기간 후 실행
DROP TABLE IF EXISTS stocks_daily_prices_backup;
DROP TABLE IF EXISTS krx_timeseries_backup;
```

### 5.3 DROP 순서

```
1. 마이그레이션 검증 (섹션 2.6) 완료 ← 필수 선행
2. 레거시 코드 제거 (섹션 3, 4) 완료 ← 필수 선행
3. 전체 테스트 통과 확인 (섹션 6.1) ← 필수 선행
4. DROP TABLE stocks_daily_prices, krx_timeseries
5. 서버 재기동 + API 검증
6. (1주 후) DROP TABLE 백업 테이블
```

---

## 6. 검증 계획

### 6.1 전체 테스트 스위트

```bash
cd backend
pytest -v
```

**기대 결과**: 638+ passed 유지 (pre-existing 2건 제외)

- `StocksDailyPrice`, `KrxTimeSeries` 참조가 완전히 제거되었으므로 import 오류 없어야 함
- Phase 1에서 이미 모든 테스트가 `StockPriceDaily`를 사용하도록 전환됨

### 6.2 DB 검증

```sql
-- 마이그레이션 후 stock_price_daily 레코드 수 확인
SELECT COUNT(*) FROM stock_price_daily;
-- 기대: ≥ 2,575건 (420 + 2,155)

-- 레거시 테이블 DROP 후 존재 여부 확인
SELECT tablename FROM pg_tables
WHERE tablename IN ('stocks_daily_prices', 'krx_timeseries');
-- 기대: 0건 (테이블 없음)
```

### 6.3 서버 기동 검증

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**확인 항목**:
- 서버 정상 기동 (import 오류 없음)
- `krx_timeseries` 라우터 미등록 확인 (Swagger UI에서 관련 엔드포인트 미표시)

### 6.4 API 엔드포인트 검증

Swagger UI (`http://localhost:8000/docs`)에서 아래 엔드포인트 호출 확인:

| 엔드포인트 | 확인 내용 |
|-----------|----------|
| `POST /admin/pykrx/load-daily-prices` | pykrx 적재 → `stock_price_daily` 저장 |
| `GET /stock-detail/{ticker}` | 시계열 데이터 조회 → `stock_price_daily`에서 반환 |
| `POST /admin/batch-jobs/run` | 배치 적재 → `stock_price_daily` 저장 |

### 6.5 프론트엔드 검증

- 데이터 관리 페이지에서 "일별 시세 적재" 버튼 동작 확인
- ProgressModal 정상 표시 (Phase 1/2 배지)
- 종목 상세 페이지 시계열 차트 정상 렌더링

---

## 7. 구현 순서

### Step 1: 데이터 마이그레이션 실행

1. `data_source` 레코드 등록 확인
2. `migrate_price_tables.sql` 실행
3. 사후 검증 쿼리 실행 (섹션 2.6)
4. 레코드 수 정합성 확인

### Step 2: 레거시 모델 제거

1. `real_data.py`에서 `StocksDailyPrice` 클래스 삭제 (라인 527-561)
2. `securities.py`에서 `KrxTimeSeries` 클래스 삭제 (라인 531-552)
3. `models/__init__.py`에서 import/export 정리

### Step 3: 라우트 및 스크립트 정리

1. `main.py`에서 `krx_timeseries` import 및 라우터 등록 제거
2. `stock_detail.py:29` 주석 업데이트
3. `scripts/load_market_data.py:290` 테이블 참조 수정

### Step 4: 테스트 및 서버 검증

1. `pytest -v` 전체 통과 확인
2. 서버 기동 확인 (import 오류 없음)
3. Swagger UI 엔드포인트 검증

### Step 5: DB 테이블 DROP

1. 레거시 테이블 DROP (`stocks_daily_prices`, `krx_timeseries`)
2. 서버 재기동 + API 검증
3. (1주 후) 백업 테이블 DROP

---

## 8. 롤백 전략

### 8.1 데이터 롤백

마이그레이션 전 백업 테이블이 자동 생성되므로 데이터 복원 가능:

```sql
-- stock_price_daily에서 마이그레이션 데이터만 삭제
DELETE FROM stock_price_daily WHERE source_id IN ('PYKRX', 'KRX_TS');

-- 원본 테이블 복원
DROP TABLE IF EXISTS stocks_daily_prices;
ALTER TABLE stocks_daily_prices_backup RENAME TO stocks_daily_prices;

DROP TABLE IF EXISTS krx_timeseries;
ALTER TABLE krx_timeseries_backup RENAME TO krx_timeseries;
```

### 8.2 코드 롤백

```bash
git revert <phase2-commit-hash>
```

### 8.3 주의사항

- 백업 테이블은 Step 5 완료 후 최소 **1주일** 보관
- 롤백 시 `models/__init__.py`의 import 복원 필수
- 롤백 시 `main.py`의 `krx_timeseries` 라우터 등록 복원 필수

---

## 9. 리스크 평가

| 리스크 | 영향 | 확률 | 완화 방안 |
|--------|------|------|----------|
| **마이그레이션 데이터 누락** | High | Low | 사후 검증 쿼리(섹션 2.6.3)로 누락 0건 확인. 백업 테이블 보존 |
| **모델 삭제 후 import 오류** | High | Medium | `grep -r "StocksDailyPrice\|KrxTimeSeries" backend/` 전수 검사로 잔여 참조 확인 |
| **krx_timeseries 라우터 제거 후 외부 연동 깨짐** | Medium | Low | Swagger UI에서 해당 엔드포인트 사용 현황 확인. `admin.py`의 pykrx 엔드포인트가 동일 기능 제공 |
| **DROP TABLE 후 복원 불가** | High | Very Low | 백업 테이블 1주 보관. 마이그레이션 검증 완전 완료 후에만 DROP 실행 |
| **Float→Numeric 정밀도 변환 오류** | Medium | Low | `ROUND(float::numeric, 2)` 안전 변환. 마이그레이션 후 샘플 데이터 비교 검증 |
