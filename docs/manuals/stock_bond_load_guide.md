# 주식·채권·ETF 종목정보 적재 가이드

**작성일:** 2026-02-05 (최종 갱신)
**대상 DB:** PostgreSQL `kingo.public`
**관련 서비스:** `app/services/real_data_loader.py`, `app/services/data_loader.py`, `app/services/pykrx_loader.py`

---

## 1. 개요

세 종목의 적재 파이프라인 개요와 프론트엔드–백엔드 연결:

| 종목 | 데이터 소스 | 백엔드 엔드포인트 | 프론트엔드 트리거 | upsert 키 | 배치 추적 |
|------|------------|------------------|------------------|-----------|----------|
| 주식 | FDR + yfinance | `POST /admin/fdr/load-stock-listing`<br>`POST /admin/load-stocks` | "📈 주식 데이터" 버튼 | `ticker` | 있음 |
| PER/PBR | DART OpenAPI | `POST /admin/dart/load-financials` | "재무제표 적재 (DART)" 버튼 | `ticker` | 있음 |
| 채권 | FSC OpenAPI | `POST /admin/fsc/load-bonds` | "채권 기본정보 적재" 버튼 | `isin_cd` | 있음 |
| ETF (경로 A) | FDR + yfinance | `POST /admin/load-etfs` | "📊 ETF 데이터" 버튼 | `ticker` | 없음 |

모든 엔드포인트는 `ADMIN_RUN` 권한이 필요하며, `x-idempotency-key` 헤더가 필수입니다 (frontend `api.js` interceptor에서 자동 부여).

---

## 2. 주식 파이프라인

```
POST /admin/fdr/load-stock-listing  ─→  fdr_stock_listing (종목 마스터)
                                              │
                                              ▼
POST /admin/load-stocks             ─→  stocks (실 데이터 upsert)
                                        yfinance 호출 + crno 조회
```

### 2.1 적재 방법

주식은 **2단계 파이프라인**으로 구성됩니다.

**Stage 1 — 종목 마스터 수집 (`load_fdr_stock_listing`)**

- `FinanceDataReader.StockListing(market)` 호출 → 종목명·시장·섹터·상장일·주식수·액면가
- `fdr_stock_listing` 테이블에 bulk INSERT
- UniqueConstraint `(ticker, as_of_date, source_id)`로 중복 방지
- `crno` 컬럼은 이 단계에서 채우지 않음 (Stage 2 시점에 backfill)

**Stage 2 — 실 데이터 적재 (`load_stocks_from_fdr`)**

`fdr_stock_listing`을 읽어 yfinance로 실시간 데이터를 수집하여 `stocks` 테이블에 upsert합니다.

```
Phase 1: 병렬 Fetch (ThreadPoolExecutor, max_workers=5)
  └─ _fetch_stock_data(ticker, name, market)  ← 스레드 안전, DB 접근 없음
       ├─ yfinance 호출 (history + info)
       │    └─ rate limit 시 exponential backoff retry (2s → 4s → 8s, 최대 3회)
       └─ DataCollector.get_crno()  ← 캐시 우선, 미스 시 FSC API

Phase 2: 순차 Upsert (단일 스레드)
  └─ _apply_stock(listing, fetched_data)
       ├─ crno 정규화 ("" → None) + fdr_stock_listing backfill
       ├─ DataClassifier로 risk_level·investment_type·category 유도
       └─ stocks 테이블 UPDATE or INSERT
  └─ 100건씩 batch commit
```

### 2.2 백엔드 엔드포인트

**Stage 1: `POST /admin/fdr/load-stock-listing`** — 동기 실행

파일: `app/routes/admin.py` → 서비스: `real_data_loader.py:load_fdr_stock_listing()`

| 파라미터 | 위치 | 타입 | 기본값 | 설명 |
|----------|------|------|--------|------|
| `market` | body | string | `KRX` | `KRX`면 KOSPI·KOSDAQ·KONEX로 분할 처리 |
| `as_of_date` | body | date | 오늘 | 적재 기준일 |

**Stage 2: `POST /admin/load-stocks`** — 백그라운드 실행

파일: `app/routes/admin.py` → 서비스: `real_data_loader.py:load_stocks_from_fdr()`

| 파라미터 | 위치 | 타입 | 기본값 | 설명 |
|----------|------|------|--------|------|
| `as_of_date` | query | date | `None` | `None`이면 `fdr_stock_listing`의 최신 `as_of_date` 자동 조회 |
| `limit` | query | int | `None` | 테스트용 종목 수 제한 (1~5000) |

- 즉시 `task_id`를 반환하고 백그라운드에서 적재 실행
- `progress_tracker`와 연동 → ProgressModal에서 진행·완료 상태 표시
- prerequisite: Stage 1 실행 완료 필수

### 2.3 프론트엔드 호출

```
DataManagementPage
  ├─ "📈 주식 데이터" 버튼 (yfinance 데이터 수집 섹션)
  │    └─ handleLoadData('stocks')
  │         └─ api.loadStocks()                          → POST /admin/load-stocks
  │              └─ ProgressModal (task_id로 진행 추적)
  │
  └─ "FDR 종목 마스터 적재" 버튼 (FinanceDataReader 섹션)
       └─ api.loadFdrStockListing({market, as_of_date})  → POST /admin/fdr/load-stock-listing
```

- `frontend/src/services/api.js` — `loadStocks()`, `loadFdrStockListing()`
- `frontend/src/pages/DataManagementPage.jsx` — `handleLoadData`, FDR 종목 마스터 섹션

### 2.4 해당 테이블

**`fdr_stock_listing`** (종목 마스터) — 모델: `app/models/real_data.py`

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `listing_id` | BigInteger PK | 내부 키 (auto) |
| `ticker` | String(10) NOT NULL | 종목코드 |
| `name` | String(100) NOT NULL | 종목명 |
| `market` | String(20) NOT NULL | KOSPI·KOSDAQ·KONEX |
| `sector` | String(100) | 섹터 (KRX 공식) |
| `industry` | String(100) | 업종 |
| `listing_date` | Date | 상장일 |
| `shares` | BigInteger | 발행주식수 |
| `par_value` | Numeric(18,2) | 액면가 |
| `crno` | String(13) | 법인등록번호 (Stage 2 backfill) |
| `as_of_date` | Date NOT NULL | 적재 기준일 |
| `source_id` | String(20) FK → data_source | `FDR` |
| `batch_id` | Integer FK → data_load_batch | |

UniqueConstraint: `(ticker, as_of_date, source_id)`
인덱스: `idx_fdr_stock_ticker`, `idx_fdr_stock_market`, `idx_fdr_stock_asof`, `idx_fdr_stock_crno`

**`stocks`** (주식 종목 정보) — 모델: `app/models/securities.py`

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `ticker` | String(10) PK | 종목코드 |
| `name` | String(100) | 종목명 |
| `crno` | String(13) | 법인등록번호 (FSC 배당 조회용) |
| `sector` | String(50) | 섹터 (fdr sector 우선) |
| `market` | String(20) | KOSPI·KOSDAQ·KONEX |
| `current_price` | Float | 현재가 |
| `market_cap` | Float | 시가총액 |
| `pe_ratio` | Float | PER — DART 재무제표 적재 시 `market_cap / net_income`으로 계산 저장 |
| `pb_ratio` | Float | PBR — DART 재무제표 적재 시 `market_cap / total_equity`로 계산 저장 |
| `dividend_yield` | Float | 배당수익률 (%) |
| `ytd_return` | Float | YTD 수익률 (%) |
| `one_year_return` | Float | 1년 수익률 (%) |
| `risk_level` | String(20) | low·medium·high |
| `investment_type` | String(100) | `,` 구분 문자열 (conservative·moderate·aggressive) |
| `category` | String(50) | 배당주·기술주·금융주 등 |
| `is_active` | Boolean | UPDATE 시 변경 안 함 (상장폐지 복활 방지) |
| `last_updated` | DateTime | onupdate=kst_now |
| `created_at` | DateTime | default=kst_now |

---

## 3. 채권 파이프라인

```
POST /admin/fsc/load-bonds  ─→  FSC OpenAPI 호출  ─→  bonds (isin_cd 기준 upsert)
```

### 3.1 적재 방법

단일 단계로 구성됩니다.

```
1. BondBasicInfoFetcher.fetch()  →  FSC 금융위원회_채권기본정보 OpenAPI 호출
2. 결과 레코드마다 _upsert_bond() 실행:
     ├─ isin_cd 검증 (빈값이면 스킵)
     ├─ _derive_bond_fields()  →  유도 컬럼 계산
     │    ├─ bond_type   : scrs_itms_kcd_nm에서 분류 (government / corporate / high_yield)
     │    ├─ credit_rating: scrs_itms_kcd에서 등급 텍스트로 변환
     │    ├─ risk_level  : credit_rating 기준 (AAA~A→low, BBB→medium, BB~→high)
     │    ├─ investment_type: risk_level 기준 (low→conservative, medium→moderate, high→aggressive)
     │    ├─ interest_rate: coupon_rate 또는 bond_bal/bond_issu_amt 역산
     │    └─ maturity_years: bond_expr_dt - today
     ├─ isin_cd로 기존 행 조회
     │    ├─ 있으면 → UPDATE (유도 컬럼 + 실데이터 컬럼 갱신)
     │    └─ 없으면 → INSERT
     └─ 건별 commit
```

### 3.2 백엔드 엔드포인트

**`POST /admin/fsc/load-bonds`** — 동기 실행

파일: `app/routes/admin.py` → 서비스: `real_data_loader.py:load_bond_basic_info()`

| 파라미터 | 위치 | 타입 | 필수 | 설명 |
|----------|------|------|------|------|
| `bas_dt` | body | string (YYYYMMDD) | 셋 중 하나 이상 | 기준일자 |
| `crno` | body | string (13자리) | 셋 중 하나 이상 | 법인등록번호 필터 |
| `bond_isur_nm` | body | string | 셋 중 하나 이상 | 발행사명 필터 |
| `limit` | body | int (1~10000) | 선택 | 최대 조회 건수 |
| `as_of_date` | body | date | 선택 | 적재 기준일 (기본: 오늘) |

`bas_dt`, `crno`, `bond_isur_nm` 중 **하나 이상** 반드시 포함해야 합니다 (422 검증).

### 3.3 프론트엔드 호출

```
DataManagementPage (📦 배당/기업액션/채권 적재 섹션)
  └─ "채권 기본정보 적재" 버튼
       ├─ 입력 검증: bas_dt(8자리) / crno(13자리) / bond_isur_nm 중 하나 이상
       └─ api.loadFscBonds({bas_dt, crno, bond_isur_nm, limit})  → POST /admin/fsc/load-bonds
            └─ 완료 시 alert 표시 + fetchDataStatus() 갱신
```

- `frontend/src/services/api.js` — `loadFscBonds()`
- `frontend/src/pages/DataManagementPage.jsx` — 채권 기본정보 카드 (배당/기업액션/채권 섹션)

### 3.4 해당 테이블

**`bonds`** — 모델: `app/models/securities.py`

| 그룹 | 컬럼 | 타입 | 설명 |
|------|------|------|------|
| 기본 | `id` | Integer PK | 내부 키 |
| 기본 | `name` | String(100) unique | 채권명 (isin_cd_nm) |
| 기본 | `bond_type` | String(50) | government·corporate·high_yield |
| 기본 | `issuer` | String(100) | 발행사 |
| 금리 | `interest_rate` | Float | 금리 (%) |
| 금리 | `coupon_rate` | Float | 쿠폰율 |
| 금리 | `maturity_years` | Integer | 잔존만기 (년) |
| 신용 | `credit_rating` | String(10) | AAA·AA·A·BBB·BB·B·CCC |
| 신용 | `risk_level` | String(20) | low·medium·high |
| 분류 | `investment_type` | String(100) | conservative·moderate·aggressive |
| 분류 | `is_active` | Boolean | |
| 실데이터 | `isin_cd` | String(12) unique | ISIN 코드 (**upsert 키**) |
| 실데이터 | `bas_dt` | String(8) | API 조회 기준일 |
| 실데이터 | `crno` | String(13) | 법인등록번호 |
| 실데이터 | `bond_issu_dt` | Date | 발행일 |
| 실데이터 | `bond_expr_dt` | Date | 만기일 |
| 실데이터 | `bond_issu_amt` | Numeric(22,3) | 발행금액 |
| 실데이터 | `bond_bal` | Numeric(22,3) | 잔액 |
| 실데이터 | `nxtm_copn_dt` | Date | 차기이표일 |
| 실데이터 | `rbf_copn_dt` | Date | 직전이표일 |
| 거버넌스 | `source_id` | String(20) FK → data_source | `FSC_BOND_INFO` |
| 거버넌스 | `batch_id` | Integer FK → data_load_batch | |
| 거버넌스 | `as_of_date` | Date | 적재 기준일 |

---

## 4. ETF 파이프라인

ETF 적재는 **2가지 경로**가 존재합니다.

```
경로 A (yfinance — 기본)
  POST /admin/load-etfs              ─→  FDR StockListing("ETF/KR") → yfinance → etfs upsert

경로 B (pykrx — KRX 공식 데이터)
```

### 4.1 적재 방법

**경로 A — yfinance (`DataLoaderService.load_etfs`)**

파일: `app/services/data_loader.py`

```
1. fdr.StockListing("ETF/KR")  →  전체 한국 ETF 종목 목록 (Symbol, Name)
2. 종목당 DataCollector.fetch_etf_data(ticker, name)
     ├─ yf.Ticker(f"{ticker}.KS")  ← .KS 접미사 (KOSPI 시장만)
     ├─ history(period="1y")  →  현재가, YTD·1년 수익률 계산
     └─ info  →  aum, expenseRatio
3. etfs 테이블에 ticker 기준 upsert (건별 commit)
4. 분류 로직:
     ├─ etf_type: "주식" in name → equity, "채권" in name → bond, 그 외 → balanced
     ├─ risk_level: balanced → medium, bond → low, equity → high
     └─ investment_type: INSERT 시 고정값 "conservative,moderate,aggressive"
```

**경로 B — pykrx (`PyKrxDataLoader`)**

파일: `app/services/pykrx_loader.py`

```
1. stock.get_market_ticker_list(today, market="ETF")  →  KRX 전체 ETF 종목 코드
2. 종목당 load_etf_data(db, ticker, name)
     ├─ stock.get_market_ohlcv()  →  현재가
     ├─ 1년간·YTD 가격 시계열로 수익률 계산
     └─ aum, expense_ratio은 수집하지 않음 (기존 값 유지)
3. etfs 테이블에 ticker 기준 upsert
4. 분류 로직 (키워드 기반, 경로 A보다 정밀):
     ├─ etf_type: "채권"/"bond"→bond, "원자재"/"금"→commodity, "리츠"/"reit"→reits, 그 외→equity
     ├─ risk_level: "레버리지"/"2X"/"인버스"→high, "채권"→low, 그 외→medium
     ├─ category: "200"→KOSPI200 추종, "코스닥"→코스닥 추종, "레버리지"→레버리지, "반도체"→반도체, 등
     └─ investment_type: risk_level에서 유도
```

### 4.2 백엔드 엔드포인트

| 엔드포인트 | 경로 | 실행 방식 | 설명 |
|-----------|------|----------|------|
| `POST /admin/load-etfs` | A | 백그라운드 (BackgroundTasks) | yfinance로 FDR 조회 종목 전체 적재 |
| `POST /admin/load-data` | A | 동기 | ETF + 예금 전체 적재 (load_etfs 포함) |

파라미터는 모두 없음. 종목 목록은 내부에서 자동 조회됩니다.

### 4.3 프론트엔드 호출

```
DataManagementPage
  ├─ "📊 ETF 데이터" 버튼 (yfinance 데이터 수집 섹션)
  │    └─ handleLoadData('etfs')
  │         └─ api.loadETFs()                          → POST /admin/load-etfs
  │              └─ ProgressModal (task_id로 진행 추적)
  │
  ├─ "📦 전체 데이터" 버튼 (yfinance 데이터 수집 섹션)
  │    └─ handleLoadData('all')
  │         └─ api.loadAllData()                       → POST /admin/load-data  (ETF+예금)
  │
  ├─ "🇰🇷 한국 ETF 전체 수집" 버튼 (pykrx 한국 주식 기본 정보 섹션)
  │
  └─ "📊 ETF 수집" 버튼 (pykrx 특정 종목 검색 섹션)
```

- `frontend/src/services/api.js` — `loadETFs()`, `loadAllData()`
- `frontend/src/pages/DataManagementPage.jsx` — yfinance 데이터 수집 섹션, pykrx 한국 주식 기본 정보 섹션

### 4.4 해당 테이블

**`etfs`** — 모델: `app/models/securities.py`

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `ticker` | String(10) PK | 종목코드 (**upsert 키**) |
| `name` | String(100) | ETF명 |
| `etf_type` | String(50) | equity·bond·commodity·reits·balanced |
| `current_price` | Float | 현재가 |
| `aum` | Float | 운용자산 (백만원) — 경로 A에서만 수집 |
| `expense_ratio` | Float | 수수료율 (%) — 경로 A에서만 수집 |
| `ytd_return` | Float | YTD 수익률 (%) |
| `one_year_return` | Float | 1년 수익률 (%) |
| `risk_level` | String(20) | low·medium·high |
| `investment_type` | String(100) | conservative·moderate·aggressive |
| `category` | String(50) | KOSPI200 추종·레버리지·인버스·반도체 등 |
| `description` | String(500) | |
| `is_active` | Boolean | |
| `last_updated` | DateTime | onupdate=kst_now |
| `created_at` | DateTime | default=kst_now |

`etfs` 테이블은 `source_id`·`batch_id` 컬럼이 없어 배치 추적 시스템에 참여하지 않습니다.

---

## 5. PER/PBR 파이프라인

```
POST /admin/dart/load-financials  ─→  DART 재무제표 API  ─→  financial_statement (원본)
                                                                     │
                                                                     ▼
                                                              stocks.pe_ratio / pb_ratio 갱신
                                                              (market_cap 기반 계산)
```

**prerequisite:** `stocks` 테이블에 종목과 `market_cap`이 적재되어 있어야 합니다 (주식 파이프라인 Stage 2 완료).

### 5.1 적재 방법

```
1. stocks 테이블에서 대상 종목 조회 (is_active=True, market_cap > 0, 시가총액 내림차순)
2. 종목당 DartFetcher.fetch(FINANCIAL_STATEMENT) 호출:
     ├─ ticker → corp_code 변환 (corpCode.xml, 내부 캐시)
     ├─ fnlttSinglAcntAll.json API 호출 (CFS 연결 → OFS 개별 폴백)
     ├─ 파싱: "당기순이익", "자본총계" 등 계정과목명으로 추출
     │    └─ 중복 계정과목(자본변동표 등)은 첫 번째 등장값만 사용
     └─ Rate limit: 초당 1건 (DartFetcher 내부 대기)
3. _upsert_financials() 실행:
     ├─ financial_statement 테이블 upsert (unique: ticker, fiscal_year, fiscal_quarter, source_id)
     └─ stocks 테이블 PER/PBR 계산 + 업데이트:
          ├─ pe_ratio = market_cap / net_income    (net_income <= 0이면 NULL)
          └─ pb_ratio = market_cap / total_equity  (total_equity <= 0이면 NULL)
4. 50건씩 배치 commit
```

### 5.2 백엔드 엔드포인트

**`POST /admin/dart/load-financials`** — 백그라운드 실행

파일: `app/routes/admin.py` → 서비스: `real_data_loader.py:load_financials_from_dart()`

| 파라미터 | 위치 | 타입 | 기본값 | 설명 |
|----------|------|------|--------|------|
| `fiscal_year` | query | int | `2024` | 회계연도. 사업보고서는 해당 연도 다음 3월에 제출됨 |
| `report_type` | query | string | `ANNUAL` | `ANNUAL` · `Q1` · `Q2` · `Q3` |
| `limit` | query | int | `None` | 테스트용 종목 수 제한 (1~5000, 시가총액 내림차순) |

- 즉시 `task_id`를 반환하고 백그라운드에서 적재 실행
- `progress_tracker`와 연동 → 종목당 실시간 진행 상황 표시
- 종목당 ~1초 소요 (DART rate limit). 전체 종목(2,676건)은 약 45분

### 5.3 프론트엔드 호출

```
DataManagementPage (📦 배당/기업액션/채권/재무제표 적재 섹션)
  └─ "재무제표 적재 (DART)" 버튼
       ├─ 입력: 회계연도, 보고서 종류(select), 종목 수 제한
       └─ api.loadDartFinancials({fiscal_year, report_type, limit})  → POST /admin/dart/load-financials
            └─ task_id 반환 + ProgressModal에서 진행 추적
```

- `frontend/src/services/api.js` — `loadDartFinancials()`
- `frontend/src/pages/DataManagementPage.jsx` — 재무제표 카드 (배당/기업액션/채권/재무제표 섹션)

### 5.4 해당 테이블

**`financial_statement`** (재무제표 원본) — 모델: `app/models/real_data.py`

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `statement_id` | BigInteger PK | 내부 키 (auto) |
| `ticker` | String(10) NOT NULL | 종목코드 |
| `fiscal_year` | Integer NOT NULL | 회계연도 |
| `fiscal_quarter` | Integer NOT NULL | 분기 (1~4, ANNUAL=4) |
| `report_type` | String(20) NOT NULL | ANNUAL · Q1 · Q2 · Q3 |
| `revenue` | BigInteger | 매출액 |
| `operating_income` | BigInteger | 영업이익 |
| `net_income` | BigInteger | 당기순이익 (**PER 계산 분모**) |
| `total_assets` | BigInteger | 자산총계 |
| `total_liabilities` | BigInteger | 부채총계 |
| `total_equity` | BigInteger | 자본총계 (**PBR 계산 분모**) |
| `operating_cash_flow` | BigInteger | 영업활동현금흐름 |
| `investing_cash_flow` | BigInteger | 투자활동현금흐름 |
| `financing_cash_flow` | BigInteger | 재무활동현금흐름 |
| `roe` | Numeric(8,4) | ROE (%) |
| `roa` | Numeric(8,4) | ROA (%) |
| `debt_ratio` | Numeric(8,4) | 부채비율 (%) |
| `dart_rcept_no` | String(20) | DART 접수번호 |
| `source_id` | String(20) FK → data_source | `DART` |
| `batch_id` | Integer FK → data_load_batch | |
| `as_of_date` | Date NOT NULL | 적재 기준일 |

UniqueConstraint: `(ticker, fiscal_year, fiscal_quarter, source_id)`

**`stocks.pe_ratio` / `stocks.pb_ratio`** — 계산 저장

| 컬럼 | 계산식 | NULL 조건 |
|------|--------|-----------|
| `pe_ratio` | `stocks.market_cap / financial_statement.net_income` | `net_income` ≤ 0 또는 None |
| `pb_ratio` | `stocks.market_cap / financial_statement.total_equity` | `total_equity` ≤ 0 또는 None |

> **주의:** `stocks.market_cap`은 yfinance에서 보통주·우선주 합산 시가총액을 반환합니다. 우선주가 있는 종목에서 PER/PBR이 실제보다 약간 높아질 수 있습니다.

---

## 6. 공통 테이블

### 6.1 `data_source` — 외부 데이터 소스 등록

| source_id | source_name | source_type | api_type | 사용 파이프라인 |
|-----------|-------------|-------------|----------|----------------|
| `FDR` | FinanceDataReader | VENDOR | LIB | 주식 Stage 1, ETF 종목 목록 조회 |
| `DART` | DART OpenAPI | GOV | REST | PER/PBR 재무제표 적재 |
| `FSC_BOND_INFO` | 금융위원회_채권기본정보 | GOV | REST | 채권 적재 |
| `FSC_DATA_GO_KR` | 금융위원회_주식배당정보 | GOV | REST | 배당 이력 적재 |

### 6.2 `data_load_batch` — 적재 배치 로그

주식·채권 적재는 배치를 생성하여 추적됩니다. ETF는 배치 추적 없음.

| 컬럼 | 설명 |
|------|------|
| `batch_id` | PK (auto) |
| `batch_type` | INFO·PRICE·INDEX·DIVIDEND·ACTION·BOND_INFO |
| `source_id` | FK → data_source |
| `status` | PENDING → RUNNING → SUCCESS / FAILED |
| `total_records` / `success_records` / `failed_records` | 처리 통계 |
| `error_message` | 실패 시 에러 메시지 |
| `operator_id` | 실행 사용자 ID |
| `created_at` / `completed_at` | 시작·종료 시각 |

---

## 7. 주의사항

### 7.1 Yahoo Finance rate limit (주식·ETF 경로 A)

종목당 초당 요청 수가 초과되면 `Too Many Requests` 응답이 발생합니다.

- **주식:** `_fetch_stock_data`에 retry (2·4·8s exponential backoff, 최대 3회) 구현됨.
- **ETF 경로 A:** `DataCollector.fetch_etf_data`에는 retry가 구현되지 않음. 대량 적재 시 실패율이 높을 수 있습니다.
- IP 기준 차단 발생 시 약 5~10분 대기 후 재시도 권장.

### 7.2 PER / PBR (주식)

PER·PBR은 DART 재무제표를 소스로 계산 저장됩니다 (Section 5 참조). 아래 주의사항이 있습니다.

- **market_cap 오차:** yfinance는 보통주·우선주 합산 시가총액을 반환합니다. 우선주가 있는 종목에서 PER/PBR이 실제보다 약간 높아질 수 있습니다.
- **종목별 DART 미등록:** 일부 종목은 해당 연도 사업보고서가 DART에 등록되지 않아 skipped됩니다. 해당 종목의 PER/PBR은 NULL로 남습니다.
- **순이익 기준:** 현재 연결 전체 당기순이익을 사용합니다. 엄밀하면 지배기업 소유주지분 순이익을 사용해야 하지만, DART 응답 구조상 분리 추출이 복잡합니다.
- **DART rate limit:** 초당 1건 제한으로 전체 종목(~2,676건) 적재는 약 45분 소요됩니다.

### 7.3 ETF 분류 정밀도 차이 (경로 A vs B)

| 항목 | 경로 A (yfinance) | 경로 B (pykrx) |
|------|-------------------|----------------|
| `etf_type` | "주식"·"채권" 키워드만 → 나머지 모두 `balanced` | 금·원자재·리츠 등 추가 키워드로 분류 |
| `risk_level` | etf_type에서 단순 유도 | "레버리지"·"인버스" 키워드로 직접 판별 |
| `investment_type` | INSERT 시 고정값 `"conservative,moderate,aggressive"` | risk_level에서 적절히 유도 |
| `category` | 설정 없음 | KOSPI200 추종·코스닥 추종·반도체 등 |

→ 분류 정밀도가 중요하면 **경로 B (pykrx)**를 사용하거나, 경로 B 후 경로 A 순서로 실행하여 가격·AUM만 갱신하는 것을 권장합니다.

### 7.4 ETF `.KS` 접미사 제한 (경로 A)

경로 A의 yfinance 호출에서 `yf.Ticker(f"{ticker}.KS")`로 KOSPI 시장만 대상입니다. KOSDAQ 상장 ETF는 가격 수집에 실패합니다.

### 7.5 batch 상태 고정 (주식·채권)

프로세스가 외부로 종료되면(OOM·타임아웃·수동 종료) batch가 `RUNNING`에 고정됩니다. 수동 정리:

```sql
UPDATE data_load_batch
SET status = 'FAILED', completed_at = now(),
    error_message = 'stale — process terminated'
WHERE status = 'RUNNING';
```

### 7.6 `investment_type` 형식

`portfolio_engine`이 `LIKE '%conservative%'` 패턴으로 조회하므로, 반드시 `,` 구분 문자열로 저장해야 합니다.
예: `"conservative,moderate"`, `"moderate,aggressive"`

### 7.7 `is_active` 규칙 (주식)

stocks의 `is_active`는 UPDATE 시 변경하지 않습니다. 상장폐지된 종목이 잘못 활성화될 수 있습니다.

### 7.8 `sector` 우선순위 (주식)

`fdr_stock_listing.sector`(KRX 공식 분류)가 yfinance `sector`(영어)보다 우선됩니다.

---

## 8. 기타참조사항

### 8.1 현재 적재 현황

| 테이블 | 행수 | 비고 |
|--------|------|------|
| `fdr_stock_listing` | 2,886 | as_of_date = 2026-02-05 |
| `stocks` | 2,886 | 가격 정보: 2,877건 (9건은 delisted/신상장) |
| `bonds` | 15 | isin_cd·crno 모두 포함 |
| `etfs` | 1,067 | 전체 가격 정보 포함 |
| `financial_statement` | DART 적재 시에 생성 | source_id = DART |
| `data_load_batch` | 41건 | 최근은 batch_id 33~41 |

**stocks 상세:**

| 항목 | 건수 |
|------|------|
| 가격 정보 있음 | 2,877 |
| crno (법인등록번호) | 2,315 |
| 배당수익률 | 1,092 |
| investment_type 분류 | 2,886 (전체) |
| PER / PBR | DART 적재 후 갱신됨 (Section 5). 검증: 삼성전자 PER=30.92, PBR=2.65 |

**etfs 상세:**

| 항목 | 건수 |
|------|------|
| etf_type = balanced | 999 |
| etf_type = bond | 55 |
| etf_type = equity | 13 |
| risk_level = medium | 1,003 |
| risk_level = low | 55 |
| risk_level = high | 9 |

### 8.2 관련 파일

| 파일 | 역할 |
|------|------|
| `app/routes/admin.py` | 모든 적재 엔드포인트 정의 |
| `app/services/real_data_loader.py` | 주식·채권·재무제표 적재 서비스 (RealDataLoader) |
| `app/services/data_loader.py` | ETF·예금 적재 서비스 (DataLoaderService) |
| `app/services/pykrx_loader.py` | pykrx 경로 주식·ETF 적재 (PyKrxDataLoader) |
| `app/services/fetchers/dart_fetcher.py` | DART OpenAPI 클라이언트 (재무제표 조회·파싱) |
| `app/data_collector.py` | yfinance 호출 래퍼 (DataCollector) |
| `app/models/securities.py` | Stock·ETF·Bond·DepositProduct 모델 |
| `app/models/real_data.py` | FdrStockListing·FinancialStatement 모델 |
| `app/progress_tracker.py` | 백그라운드 작업 진행 추적 |
| `frontend/src/services/api.js` | 백엔드 API 호출 함수 |
| `frontend/src/pages/DataManagementPage.jsx` | 적재 관리 UI |

### 8.3 엔드포인트 종합 참고

| 종목 | 엔드포인트 | 메서드 | 실행 방식 | 설명 |
|------|-----------|--------|----------|------|
| 주식 | `/admin/fdr/load-stock-listing` | POST | 동기 | FDR 종목 마스터 수집 (Stage 1) |
| 주식 | `/admin/load-stocks` | POST | 백그라운드 | yfinance → stocks upsert (Stage 2) |
| PER/PBR | `/admin/dart/load-financials` | POST | 백그라운드 | DART 재무제표 → financial_statement + stocks PER/PBR |
| 채권 | `/admin/fsc/load-bonds` | POST | 동기 | FSC API → bonds upsert |
| ETF | `/admin/load-etfs` | POST | 백그라운드 | yfinance → etfs (경로 A) |
| ETF | `/admin/load-data` | POST | 동기 | ETF + 예금 전체 (경로 A 포함) |
| 배당 | `/admin/fsc/load-dividends` | POST | 동기 | FSC 배당정보 → dividend_history |
| 배당 | `/admin/dart/load-dividends` | POST | 동기 | DART 배당 공시 |
| 기타 | `/admin/dart/load-corporate-actions` | POST | 동기 | DART 기업 액션 |
