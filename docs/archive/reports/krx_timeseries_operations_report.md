# KRX 시계열 데이터 수집/운용 분석 보고서

## 1. 요약 (Executive Summary)

| 항목 | 현황 |
|------|------|
| **전체 판정** | 수집 인프라 구축 완료, **운용 사실상 중단 상태** |
| **종목 커버리지** | 20~34종목 / 2,886종목 (**0.7~1.2%**) |
| **최신 데이터** | 2026-01-30 (약 **10일+ 미갱신**, 자동 스케줄 없음) |
| **테이블 분산** | 4개 테이블에 동일 목적 데이터 분산 저장 |
| **백테스팅 연결** | `BacktestingEngine`이 참조하는 테이블과 실제 적재 테이블 불일치 |
| **성능 최적화** | 266배 개선 달성 (80초 → 0.3초), 테스트 17개 통과 |

> **결론**: 수집 파이프라인과 성능 최적화는 우수하나, 적재 대상이 POPULAR_STOCKS 20종목으로 하드코딩되어 있고 자동 갱신 메커니즘이 없어 백테스팅 실운용에 부적합하다.

---

## 2. 시스템 아키텍처 현황

### 2.1 데이터 흐름도

```
[pykrx API] ──→ PyKrxDataLoader ──→ stocks_daily_prices (420건)
                 (병렬 8스레드)        ↑ ON CONFLICT batch upsert
                 (배치 500건)          ⚠ BacktestingEngine이 참조하지 않음

[pykrx API] ──→ krx_timeseries 라우터 ──→ krx_timeseries (2,155건)
                 (단건 종목별)               ↑ BacktestingEngine 실제 참조

[Alpha Vantage] ──→ alpha_vantage_timeseries (미국주식 전용)

                                ┌──────────────────────────────────┐
                                │ [적재 경로]     [백테스팅 참조]    │
                                │ stocks_daily_prices  ← 미참조 ⚠  │
[BacktestingEngine] ──참조──→   │ krx_timeseries       ← 실제 참조 │
                                │ AlphaVantageTimeSeries← 미국 전용 │
                                │ stock_price_daily    ← 미사용     │
                                └──────────────────────────────────┘
```

> **핵심 단절**: pykrx_loader가 최적화된 배치로 `stocks_daily_prices`에 적재하지만, `BacktestingEngine._get_price_on_date()` (backtesting.py:228-264)는 `KrxTimeSeries` 테이블만 조회. 두 테이블은 동기화되지 않음.

### 2.2 테이블 분산 현황 (4개)

| 테이블명 | 모델 클래스 | PK | 특징 |
|----------|------------|-----|------|
| `stocks_daily_prices` | StocksDailyPrice | (code, date) | pykrx_loader 주 적재 대상. OHLCV + change_rate |
| `krx_timeseries` | KrxTimeSeries | id (auto) | 단건 종목 적재용. OHLCV만. Float 타입 |
| `stock_price_daily` | StockPriceDaily | price_id (auto) | Phase 3 설계. adj_close, market_cap, quality_flag, batch_id, CheckConstraint(H>=L, V>=0) 포함. **미사용** |
| `alpha_vantage_timeseries` | AlphaVantageTimeSeries | - | 미국주식 전용 |

**문제점**: `stock_price_daily`가 가장 완성도 높은 스키마(수정종가, 품질 플래그, 배치 추적)이나 실제 적재에 사용되지 않음.

### 2.3 API 엔드포인트 구조

| 엔드포인트 | 메서드 | 대상 테이블 | 병렬 지원 | 배치 지원 |
|-----------|--------|------------|----------|----------|
| `POST /admin/pykrx/load-daily-prices` | PyKrxDataLoader | stocks_daily_prices | O (8스레드) | O (500건) |
| `POST /admin/krx-timeseries/load-stock/{ticker}` | krx_timeseries 라우터 | krx_timeseries | X | X |

---

## 3. 데이터 현황 (DB 실사)

### 3.1 레코드 수

| 테이블 | 레코드 수 | 종목 수 | 비고 |
|--------|----------|---------|------|
| `stocks_daily_prices` | ~420건 | ~20종목 | POPULAR_STOCKS 하드코딩 |
| `krx_timeseries` | ~2,155건 | ~34종목 | 수동 단건 적재 |
| `stock_price_daily` | 0건 | 0종목 | 미사용 (스키마만 존재) |
| **합계** | **~2,575건** | **~34종목** | 전체 2,886종목 대비 **1.2%** |

### 3.2 날짜 범위

| 항목 | 값 |
|------|-----|
| 최초 데이터 | 2025-01-01 |
| 최신 데이터 | 2026-01-30 |
| 미갱신 기간 | 10일+ (보고서 기준 2026-02-09) |
| 영업일 기준 공백 | 약 7~8 영업일 |

### 3.3 데이터 품질

| 지표 | 결과 |
|------|------|
| NULL 값 | 0건 (존재하는 데이터는 깨끗함) |
| 중복 레코드 | 0건 (ON CONFLICT로 자동 처리) |
| OHLCV 정합성 검증 | **미구현** (H>=L, H>=O, H>=C 등 미검증) |
| 수정종가 (Adjusted Close) | **미지원** (stocks_daily_prices 스키마에 없음) |

---

## 4. 발견된 문제점

### 4.1 Critical (5건)

#### [C1] 종목 커버리지 심각 부족 (1.2%)

- **현황**: 20~34종목만 적재 (전체 2,886종목 대비 1.2%)
- **원인**: `POPULAR_STOCKS` 리스트 20종목으로 하드코딩
  ```
  POPULAR_STOCKS = ["005930", "000660", "069500", ...]  # 20종목
  ```
- **영향**: 백테스팅 시 대다수 종목의 과거 가격 데이터 조회 불가
- **위치**: `pykrx_loader.py` POPULAR_STOCKS 상수

#### [C2] 데이터 미갱신 (수동 트리거만 가능)

- **현황**: 최신 데이터 2026-01-30, 이후 갱신 없음
- **원인**: 자동 스케줄링 미구현. 관리자가 직접 API 호출 필요
- **영향**: 백테스팅 결과에 최근 시세 미반영
- **비고**: `admin_batch.py`에 BatchExecution 모델이 있으나 `run_type: SCHEDULED` 실행 로직 미구현

#### [C3] 테이블 분산 및 백테스팅 연결 단절

- **현황**: 동일 목적 데이터가 4개 테이블에 분산
- **문제**: `BacktestingEngine._get_price_on_date()` (backtesting.py:228-264)는 `KrxTimeSeries`만 조회하나, 최적화된 pykrx_loader는 `stocks_daily_prices`에 적재. **두 경로가 완전히 단절됨**
  ```python
  # backtesting.py:232-237 — KrxTimeSeries만 참조
  krx_data = self.db.query(KrxTimeSeries).filter(
      and_(KrxTimeSeries.ticker == ticker,
           KrxTimeSeries.date == query_date)
  ).first()
  ```
- **위치**: `backend/app/services/backtesting.py`
- **영향**: `/admin/pykrx/load-daily-prices`로 적재한 데이터가 백테스팅에 전혀 사용되지 않음. 데이터 미조회 시 랜덤 워크 시뮬레이션으로 대체 (backtesting.py:253-264)

#### [C4] 자동 스케줄링 프레임워크 부재

- **현황**: APScheduler, Celery, cron 등 스케줄링 프레임워크 미도입
- **구현체**: FastAPI `BackgroundTasks`만 사용 (요청 시 1회 실행)
- **영향**: 매일 장 마감 후 데이터 자동 갱신 불가
- **비고**: `BatchExecution` 모델에 `scheduled_at` 필드가 있으나 트리거 메커니즘 없음

#### [C5] 수정종가(Adjusted Close) 미지원

- **현황**: `stocks_daily_prices` 테이블에 `adj_close_price` 컬럼 없음
- **비고**: `stock_price_daily` 테이블에는 존재하나 해당 테이블은 미사용
- **영향**: 액면분할, 무상증자 등 권리조정 미반영 시 백테스팅 수익률 왜곡
- **pykrx 지원 여부**: `get_market_ohlcv()` 자체는 수정종가 미제공 (별도 계산 필요)

### 4.2 Medium (3건)

#### [M1] 데이터 품질 메트릭 미수집

- **현황**: `DataLoadBatch` 모델에 `quality_score`, `null_ratio`, `outlier_ratio` 컬럼이 있으나 실제 적재 시 미활용
- **위치**: `backend/app/models/real_data.py` DataLoadBatch 클래스
- **영향**: 데이터 품질 이슈 발생 시 사후 추적 불가

#### [M2] OHLCV 정합성 검증 없음

- **현황**: `stocks_daily_prices` (실제 적재 테이블) 적재 시 다음 규칙 미검증
  - `high >= low`
  - `high >= open`, `high >= close`
  - `low <= open`, `low <= close`
  - `volume >= 0`
- **비고**: `stock_price_daily` 모델에는 `CheckConstraint('high_price >= low_price')`, `CheckConstraint('volume >= 0')` 등이 정의되어 있으나 해당 테이블은 미사용
- **영향**: 이상 데이터 유입 시 감지 불가

#### [M3] 프론트엔드 전용 API 함수 미등록

- **현황**: `api.js`에 `loadDailyPrices()` 함수 미정의
- **비고**: `DataManagementPage.jsx`에서 직접 `fetch()` 호출로 대체 사용
- **영향**: API 호출 패턴 불일치, JWT 토큰 관리 이중화

---

## 5. 성능 최적화 현황 (긍정적 요소)

### 5.1 최적화 달성 현황

| 최적화 단계 | 기법 | 성능 | 대비 |
|------------|------|------|------|
| 원본 (Phase 0) | 순차 + N+1 쿼리 | 80초 / 500건 | 기준선 |
| Phase 1 | ThreadPoolExecutor (8 workers) | 10초 / 500건 | **8배** |
| Phase 2 | PostgreSQL ON CONFLICT 배치 | 0.3초 / 500건 | **266배** |

### 5.2 구현 세부사항

| 항목 | 값 |
|------|-----|
| 병렬 스레드 수 | 8 (기본, 1~16 설정 가능) |
| 배치 크기 | 500건 / upsert |
| 스레드별 DB 세션 | 독립 `SessionLocal()` |
| 스레드 안전성 | `threading.Lock` 결과 누적 |
| 진행률 업데이트 | 5건마다 1회 (오버헤드 감소) |

### 5.3 테스트 커버리지

| 테스트 파일 | 테스트 수 | 라인 수 |
|------------|----------|---------|
| `test_pykrx_parallel.py` | 7개 | 256줄 |
| `test_pykrx_batch.py` | 10개 | 304줄 |
| **합계** | **17개** | **560줄** |

테스트 대상: 기본 적재, upsert 멱등성, 대용량 청크 분할, NULL 값 처리, 예외 처리, 스레드 안전성, 워커 수 설정, 데이터 무결성.

---

## 6. 개선 권고사항

### Priority 1: 테이블 통합 (단기)

**목표**: 4개 분산 테이블을 1개 표준 테이블로 통합

| 작업 | 상세 |
|------|------|
| 표준 테이블 선정 | `stock_price_daily` (adj_close, batch_id, quality_flag 포함) |
| 데이터 마이그레이션 | stocks_daily_prices + krx_timeseries → stock_price_daily |
| 적재 로직 변경 | `pykrx_loader.py`가 stock_price_daily에 직접 적재 |
| 백테스팅 연결 | `BacktestingEngine`이 stock_price_daily만 참조 |
| 레거시 제거 | stocks_daily_prices, krx_timeseries 테이블 deprecate |

### Priority 2: 자동 일배치 스케줄링 (단기)

**목표**: 매일 장 마감 후 자동으로 전 종목 시세 갱신

| 작업 | 상세 |
|------|------|
| 스케줄러 도입 | APScheduler 또는 Celery Beat |
| 일배치 작업 정의 | 매일 18:00 KST, 전 종목 당일 OHLCV 적재 |
| 실패 재시도 | 3회 재시도, 지수 백오프 |
| 모니터링 | BatchExecution 기존 모델 활용 (status, error_message) |
| 휴장일 처리 | KRX 휴장 캘린더 연동 (pykrx 제공) |

### Priority 3: 전 종목 백필 (중기)

**목표**: 2,886종목 전체에 대해 과거 시세 적재

| 작업 | 상세 |
|------|------|
| POPULAR_STOCKS 제거 | stocks 테이블에서 전 종목 ticker 동적 조회 |
| 백필 범위 | 최근 3년 (2023-01-01 ~ 현재) |
| 예상 데이터량 | 2,886종목 x 750영업일 = ~2,164,500건 |
| 실행 전략 | 100종목씩 배치 + 병렬 8스레드 |
| 예상 소요 | ~15분 (배치 최적화 기준) |

### Priority 4: 수정종가 지원 (중기)

| 작업 | 상세 |
|------|------|
| 데이터 소스 | 권리락일/분할비율은 pykrx `get_market_ohlcv`에서 미제공 |
| 대안 1 | yfinance 한국주식 수정종가 조회 (`.KS` 접미사) |
| 대안 2 | KRX 권리조정계수 직접 계산 (corporate actions 활용) |
| 저장 | stock_price_daily.adj_close_price 컬럼 활용 |

### Priority 5: 데이터 품질 강화 (장기)

| 작업 | 상세 |
|------|------|
| OHLCV 정합성 검증 | 적재 시 H>=L, H>=O 등 자동 검증 |
| 품질 메트릭 기록 | DataLoadBatch에 quality_score, null_ratio 실제 계산 |
| 이상치 탐지 | 전일 대비 ±30% 이상 변동 시 플래그 |
| 프론트엔드 통합 | api.js에 loadDailyPrices() 표준 함수 등록 |

---

## 7. 참조 파일 목록

| 구분 | 파일 경로 |
|------|----------|
| 모델 정의 | `backend/app/models/real_data.py` (StocksDailyPrice, StockPriceDaily, DataLoadBatch) |
| 모델 정의 | `backend/app/models/securities.py` (KrxTimeSeries) |
| pykrx 로더 | `backend/app/services/pykrx_loader.py` (1,375줄) |
| 실데이터 로더 | `backend/app/services/real_data_loader.py` (1,800+줄) |
| 관리자 라우트 | `backend/app/routes/admin.py` (load-daily-prices 엔드포인트) |
| KRX 시계열 라우트 | `backend/app/routes/krx_timeseries.py` (load-stock 엔드포인트) |
| 배치 관리 | `backend/app/routes/admin_batch.py` (BatchExecution 모델) |
| 백테스팅 | `backend/app/services/backtesting.py` (BacktestingEngine) |
| 진행률 추적 | `backend/app/progress_tracker.py` (ProgressTracker) |
| 프론트엔드 API | `frontend/src/services/api.js` |
| 프론트엔드 관리 | `frontend/src/pages/DataManagementPage.jsx` |
| 테스트 (병렬) | `backend/tests/unit/test_pykrx_parallel.py` (7개 테스트) |
| 테스트 (배치) | `backend/tests/unit/test_pykrx_batch.py` (10개 테스트) |

---

*보고서 작성일: 2026-02-09*
*분석 대상: KingoPortfolio Phase 3-C KRX 시계열 데이터 수집 시스템*
