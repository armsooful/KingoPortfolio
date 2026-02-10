# Priority 1: 테이블 통합 구현 계획

## 전략 요약

`StocksDailyPrice`(stocks_daily_prices)를 한국주식 일별시세의 **표준 테이블**로 채택하고,
`KrxTimeSeries`(krx_timeseries)를 참조하는 모든 코드를 `StocksDailyPrice`로 전환한다.

### 왜 StocksDailyPrice인가?
- 이미 pykrx 병렬+배치 파이프라인이 연결되어 있음 (266배 최적화 완료)
- composite PK `(code, date)`로 중복 방지 (KrxTimeSeries는 중복 허용)
- `StockPriceDaily`는 governance FK(source_id, batch_id) 필수 → 지금 도입하면 복잡도 증가
- `AlphaVantageTimeSeries`는 미국주식 전용이므로 이번 통합 범위 밖

### 컬럼 매핑 (KrxTimeSeries → StocksDailyPrice)
| KrxTimeSeries | StocksDailyPrice | 비고 |
|---------------|-----------------|------|
| ticker | code | 동일 값 (6자리 종목코드) |
| date | date | 동일 |
| open (Float) | open_price (Numeric) | 타입 변환 필요 |
| high (Float) | high_price (Numeric) | |
| low (Float) | low_price (Numeric) | |
| close (Float) | close_price (Numeric) | |
| volume (Integer) | volume (BigInteger) | 호환 |
| - | change_rate | KrxTimeSeries에 없음 (NULL 허용) |

---

## 변경 파일 목록 (14개)

### A. 서비스 레이어 (데이터 소비자) — 3개 파일

1. **`backend/app/services/backtesting.py`**
   - import: `KrxTimeSeries` → `StocksDailyPrice`
   - `_get_historical_price()`: 한국주식 쿼리를 `StocksDailyPrice` 기반으로 변경
   - `.close` → `.close_price`, `.ticker` → `.code`

2. **`backend/app/services/phase7_evaluation.py`**
   - import: `KrxTimeSeries` → `StocksDailyPrice`
   - `_fetch_timeseries()`, `_fetch_multi_timeseries()` 쿼리 변경
   - `.ticker` → `.code`, `.date` 동일, `.close` → `.close_price`

3. **`backend/app/routes/stock_detail.py`**
   - import: `KrxTimeSeries` → `StocksDailyPrice`
   - 시계열 조회 쿼리: `.ticker` → `.code`, `.open/.high/.low/.close` → `.open_price` 등
   - 응답 매핑도 함께 변경

### B. 라우트 레이어 — 2개 파일

4. **`backend/app/routes/krx_timeseries.py`**
   - 전체 라우터를 `StocksDailyPrice` 기반으로 재작성
   - pykrx 데이터 수집 → `StocksDailyPrice`에 직접 저장
   - ON CONFLICT upsert 적용 (기존 N+1 → 배치)
   - `/data-status` 엔드포인트도 `stocks_daily_prices` 기반으로 변경

5. **`backend/app/routes/batch_jobs.py`**
   - `KrxTimeSeries` import → `StocksDailyPrice`
   - 관련 쿼리 업데이트

6. **`backend/app/routes/phase7_evaluation.py`**
   - `KrxTimeSeries` import → `StocksDailyPrice`
   - available period 쿼리: `.ticker` → `.code`

### C. 테스트 파일 — 12개 파일

모든 테스트에서 `_seed_timeseries()` 헬퍼를 `StocksDailyPrice` 기반으로 변경.
`KrxTimeSeries(ticker=..., open=..., close=...)` → `StocksDailyPrice(code=..., open_price=..., close_price=...)`

7-8. `backend/tests/integration/test_phase7_evaluation.py`, `test_phase7_comparison.py`
9-16. `backend/tests/e2e/test_phase9_*.py` (8개 파일)

### D. 모델 (정리)

17. **`backend/app/models/securities.py`**
   - `KrxTimeSeries` 클래스는 **유지** (DB 테이블 자체는 삭제하지 않음, 마이그레이션 후 deprecate)
   - 단, 모든 import 경로가 바뀌므로 실질적 비활성화

---

## 변경하지 않는 것

- **`StockPriceDaily`** (stock_price_daily): 미래 거버넌스 테이블로 보존
- **`AlphaVantageTimeSeries`**: 미국주식 전용, 이번 범위 밖
- **`pykrx_loader.py`**: 이미 `StocksDailyPrice` 기반 → 변경 불필요
- **DB 마이그레이션 (Alembic)**: Alembic 미사용 프로젝트 → DDL 수동 관리
- **테이블 삭제**: `krx_timeseries` 테이블 자체는 삭제하지 않음 (기존 데이터 보존)

---

## 구현 순서

### Step 1: 서비스 레이어 변경 (backtesting, phase7_evaluation)
핵심 소비자 코드를 StocksDailyPrice 기반으로 전환

### Step 2: 라우트 레이어 변경 (krx_timeseries, stock_detail, batch_jobs, phase7_evaluation route)
API 엔드포인트를 StocksDailyPrice 기반으로 전환

### Step 3: 테스트 파일 일괄 변경 (12개)
_seed_timeseries 헬퍼를 StocksDailyPrice 기반으로 전환

### Step 4: 테스트 실행 & 검증
`pytest -m unit -v` + `pytest -m e2e -v` + `pytest -m integration -v`
