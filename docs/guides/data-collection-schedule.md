# Foresto Compass 데이터 수집 스케줄 운영 보고서

> **작성일**: 2026-02-15
> **대상 환경**: MacBook 8GB RAM / 4 CPU cores, PostgreSQL (kingo DB)
> **운영자**: 1인 관리자
> **목적**: 데이터 수집 파이프라인 현황 정리 + 자동화 스케줄 권장안 + 장애 대응 절차

---

## 목차

- [Part 1: 현행 시스템 현황](#part-1-현행-시스템-현황)
- [Part 2: 권장 운영 스케줄](#part-2-권장-운영-스케줄)
- [Part 3: 자동화 구현 제안](#part-3-자동화-구현-제안)
- [Part 4: 장애 대응 & 운영 절차](#part-4-장애-대응--운영-절차)
- [Part 5: 로드맵](#part-5-로드맵)

---

# Part 1: 현행 시스템 현황

## 1.1 데이터 소스 총괄표

| # | 데이터 | 소스 | 대상 테이블 | 예상 건수 | API 제약 | 예상 소요시간 |
|---|--------|------|-------------|-----------|----------|---------------|
| 1 | 종목 마스터 | FinanceDataReader (FDR) | `fdr_stock_listing` | ~2,900건 | 없음 | 10~20초 |
| 2 | 한국 주식 | FDR → yfinance → FSC CRNO | `stocks` | ~2,900건 | FSC API 1req/sec | 3~5분 |
| 3 | ETF | pykrx KRX ETF 마켓 | `etfs` | ~800건 | KRX 서버 부하 | 5~10분 |
| 4 | 일별 시세 | pykrx | `stock_price_daily` | 수백만건 | KRX 서버 부하 | 10~40분 (증분) |
| 5 | 재무제표 | DART API | `financial_statement` | ~2,900건/년 | **1 req/sec**, 일 10,000건 | 40~60분 |
| 6 | 배당 이력 (DART) | DART API | `dividend_history` | 종목별 | 1 req/sec | 종목 수 의존 |
| 7 | 배당 이력 (FSC) | 금융위원회 API | `dividend_history` | 종목별 | 제한 없음 | 종목 수 의존 |
| 8 | 채권 | FSC 채권기본정보 | `bonds` | ~19,000건 | 페이지당 1,000건 | 2~5분 |
| 9 | 정기예금 | FSS 금융상품 한눈에 | `deposit_products` + `deposit_rate_options` | ~37건 | 없음 | 10~30초 |
| 10 | 적금 | FSS 금융상품 한눈에 | `savings_products` + `savings_rate_options` | ~100건 | 없음 | 10~30초 |
| 11 | 연금저축 | FSS 금융상품 한눈에 | `annuity_savings_products` + `annuity_savings_options` | ~200건 | 다중 페이지 | 30초~1분 |
| 12 | 주택담보대출 | FSS 금융상품 한눈에 | `mortgage_loan_products` + `mortgage_loan_options` | ~100건 | 없음 | 10~30초 |
| 13 | 전세자금대출 | FSS 금융상품 한눈에 | `rent_house_loan_products` + options | ~50건 | 없음 | 10~30초 |
| 14 | 개인신용대출 | FSS 금융상품 한눈에 | `credit_loan_products` + options | ~50건 | 없음 | 10~30초 |
| 15 | 기업 액션 | DART API | `corporate_actions` | 분기별 | 1 req/sec | 종목 수 의존 |
| 16 | Compass Score | 내부 계산 (4축 엔진) | `stocks` (compass_* 컬럼) | ~2,900건 | CPU bound | 10~30분 |

> **참고**: Alpha Vantage (미국 주식/ETF/시계열) API는 구현되어 있으나, 미국 시장 데이터는 **추후 제공 예정**이므로 현재 운영 스케줄에서 제외한다. 엔드포인트: `POST /admin/alpha-vantage/*` (6개)

## 1.2 자동화 스케줄 현황

APScheduler로 자동화된 작업 **4건** (데이터 수집 2건 + 이메일 발송 2건):

| 시간 (KST) | Job ID | 작업 | 함수 | 비고 |
|---|---|---|---|---|
| 16:30 (월~금) | `daily_incremental_prices` | 일별 시세 증분 적재 | `scheduled_incremental_load` | pykrx → stock_price_daily ✅ Phase 1 |
| 17:00 (월~금) | `daily_compass_score` | Compass Score 일괄 계산 | `scheduled_compass_batch_compute` | stocks compass_* 갱신 ✅ Phase 1 |
| 07:30 (매일) | `daily_market_email` | 일일 시장 요약 이메일 | `scheduled_daily_email` | yfinance 4개 지수 + pykrx 등락 + 뉴스 |
| 08:00 (매일) | `watchlist_score_alerts` | 관심 종목 점수 변동 알림 | `scheduled_watchlist_alerts` | ±5점 변동 시 발송 |

**소스 위치**:
- 스케줄 등록: `backend/app/main.py:86-130`
- 수집 서비스: `backend/app/services/scheduled_data_collection.py`

> **Phase 1 완료 (2026-02-15)**: 16:30 시세 적재 + 17:00 Compass Score 계산이 자동화되어,
> 07:30 이메일이 항상 최신 데이터를 참조하게 됨. 동시 실행 방지 Lock + OpsAlert 실패 알림 포함.

## 1.3 수동 수집 엔드포인트 전체 목록

모든 엔드포인트는 `POST /admin/...` 경로이며 `ADMIN_RUN` 권한이 필요하다.

### 한국 주식 파이프라인

| # | 엔드포인트 | 설명 | 실행 방식 | 소스 위치 |
|---|---|---|---|---|
| 1 | `POST /admin/fdr/load-stock-listing` | FDR 종목 마스터 적재 | 동기 | `admin.py:1238` |
| 2 | `POST /admin/load-stocks` | 주식 데이터 적재 (FDR → yfinance → pykrx) | 백그라운드 | `admin.py:79` |
| 3 | `POST /admin/load-etfs` | ETF 데이터 적재 | 백그라운드 | `admin.py:207` |
| 4 | `POST /admin/pykrx/load-daily-prices` | 일별 시세 적재 (기간 지정) | 백그라운드 | `admin.py:2731` |
| 5 | `POST /admin/pykrx/load-stocks-incremental` | 증분 시계열 적재 (자동 기간 계산) | 백그라운드 | `admin.py:2833` |

### 재무 & 밸류에이션

| # | 엔드포인트 | 설명 | 실행 방식 | 소스 위치 |
|---|---|---|---|---|
| 6 | `POST /admin/dart/load-financials` | DART 재무제표 + PER/PBR 계산 | 백그라운드 | `admin.py:1312` |
| 7 | `POST /admin/dart/load-dividends` | DART 배당 이력 | 동기 | `admin.py:240` |
| 8 | `POST /admin/fsc/load-dividends` | FSC 배당 이력 | 동기 | `admin.py:265` |
| 9 | `POST /admin/dart/load-corporate-actions` | DART 기업 액션 | 동기 | `admin.py:1262` |
| 10 | `POST /admin/pykrx/load-all-financials` | pykrx 재무 지표 (인기주 20종목) | 백그라운드 | `admin.py:2015` |
| 11 | `POST /admin/pykrx/load-financials/{ticker}` | pykrx 재무 지표 (개별 종목) | 백그라운드 | `admin.py:2055` |

### 채권 & 금융상품

| # | 엔드포인트 | 설명 | 실행 방식 | 소스 위치 |
|---|---|---|---|---|
| 12 | `POST /admin/fsc/load-bonds` | FSC 채권 기본정보 (개별 조회) | 동기 | `admin.py:290` |
| 13 | `POST /admin/load-bonds` | 채권 전체 조회 (quality_filter) | 백그라운드 | `admin.py:322` |
| 14 | `POST /admin/load-deposits` | FSS 정기예금 | 백그라운드 | `admin.py:502` |
| 15 | `POST /admin/load-savings` | FSS 적금 | 백그라운드 | `admin.py:626` |
| 16 | `POST /admin/load-annuity-savings` | FSS 연금저축 | 백그라운드 | `admin.py:751` |
| 17 | `POST /admin/load-mortgage-loans` | FSS 주택담보대출 | 백그라운드 | `admin.py:876` |
| 18 | `POST /admin/load-rent-house-loans` | FSS 전세자금대출 | 백그라운드 | `admin.py:1000` |
| 19 | `POST /admin/load-credit-loans` | FSS 개인신용대출 | 백그라운드 | `admin.py:1119` |

### Compass Score

| # | 엔드포인트 | 설명 | 실행 방식 | 소스 위치 |
|---|---|---|---|---|
| 20 | `POST /admin/scoring/batch-compute` | Compass Score 일괄 계산 | 백그라운드 | `admin.py:2956` |
| 21 | `GET /admin/scoring/compass/{ticker}` | 개별 Compass Score 조회/계산 | 동기 | `admin.py:2941` |

### v1 Data Load API (별도 라우터)

| # | 엔드포인트 | 설명 | 실행 방식 | 소스 위치 |
|---|---|---|---|---|
| 22 | `POST /api/v1/admin/data-load/stock-prices` | 주식 시세 적재 (v1) | 동기 | `admin_data_load.py:184` |
| 23 | `POST /api/v1/admin/data-load/index-prices` | 지수 시세 적재 (v1) | 동기 | `admin_data_load.py:238` |
| 24 | `POST /api/v1/admin/data-load/stock-info` | 종목 정보 적재 (v1) | 동기 | `admin_data_load.py:291` |

## 1.4 데이터 의존성 그래프

수집 순서가 중요한 데이터 간의 의존 관계:

```
[1] fdr_stock_listing (종목 마스터)
 │
 ├──▶ [2] stocks (한국 주식 기본 정보)
 │     │
 │     ├──▶ [4/5] stock_price_daily (일별 시세 — ticker 참조)
 │     │
 │     ├──▶ [6] financial_statement (재무제표 — ticker + crno 참조)
 │     │     │
 │     │     └──▶ [20] Compass Score 계산 (재무 점수 = financial_statement 기반)
 │     │
 │     ├──▶ [7/8] dividend_history (배당 이력 — ticker 참조)
 │     │
 │     └──▶ [20] Compass Score 계산 (기술 + 리스크 점수 = stock_price_daily 기반)
 │
 └──▶ [3] etfs (ETF — 독립적이지만 stock_listing 후 실행 권장)

[8~14] 채권 & 금융상품 → 독립 (주식 데이터와 무관)

[20] Compass Score → [2] stocks + [4] stock_price_daily + [6] financial_statement 필수
 │
 └──▶ [07:30] 시장 이메일 (Compass Score 참조)
      [08:00] 워치리스트 알림 (Compass Score 참조)
```

**핵심 의존 체인 (이메일 발송 전 필수)**:
```
fdr_stock_listing → stocks → stock_price_daily + financial_statement → Compass Score → 이메일
```

---

# Part 2: 권장 운영 스케줄

## 2.1 일일 스케줄 (매 영업일)

한국 주식시장 마감(15:30) 후 데이터가 확정되므로, **16:00~07:00** 사이에 수집을 완료해야 한다.

| 시간 (KST) | 작업 | 엔드포인트 | 예상 소요 | 우선순위 |
|---|---|---|---|---|
| 16:30 | 증분 시계열 적재 | `POST /admin/pykrx/load-stocks-incremental` | 10~30분 | **필수** |
| 17:00 | Compass Score 일괄 계산 | `POST /admin/scoring/batch-compute` | 10~30분 | **필수** |
| — | *(대기)* | — | — | — |
| 07:30 | 시장 이메일 발송 (자동) | APScheduler `daily_market_email` | 1~2분 | 자동 |
| 08:00 | 워치리스트 알림 (자동) | APScheduler `watchlist_score_alerts` | 1~2분 | 자동 |

### 일일 실행 curl 명령

```bash
# 1. 증분 시계열 적재 (장 마감 후)
curl -X POST "http://localhost:8000/admin/pykrx/load-stocks-incremental" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: $(uuidgen)" \
  -d '{"default_days": 1825, "num_workers": 4}'

# 2. Compass Score 일괄 계산 (시계열 적재 완료 후)
curl -X POST "http://localhost:8000/admin/scoring/batch-compute?limit=3000" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "X-Idempotency-Key: $(uuidgen)"
```

## 2.2 주간 스케줄 (매주 토요일 또는 일요일)

시장이 쉬는 주말에 시간이 오래 걸리는 대량 수집 작업을 실행한다.

| 작업 | 엔드포인트 | 예상 소요 | 빈도 |
|---|---|---|---|
| 종목 마스터 갱신 | `POST /admin/fdr/load-stock-listing` | 10~20초 | 주 1회 |
| 주식 기본 정보 갱신 | `POST /admin/load-stocks` | 3~5분 | 주 1회 |
| ETF 기본 정보 갱신 | `POST /admin/load-etfs` | 5~10분 | 주 1회 |
| DART 재무제표 (최신 연도) | `POST /admin/dart/load-financials?fiscal_year=2024` | 40~60분 | 주 1회 |

### 주간 실행 curl 명령

```bash
# 1. 종목 마스터 갱신
curl -X POST "http://localhost:8000/admin/fdr/load-stock-listing" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: $(uuidgen)" \
  -d '{"market": "KRX"}'

# 2. 주식 기본 정보 갱신 (종목 마스터 완료 후)
curl -X POST "http://localhost:8000/admin/load-stocks" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "X-Idempotency-Key: $(uuidgen)"

# 3. ETF 기본 정보 갱신
curl -X POST "http://localhost:8000/admin/load-etfs" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "X-Idempotency-Key: $(uuidgen)"

# 4. DART 재무제표
curl -X POST "http://localhost:8000/admin/dart/load-financials?fiscal_year=2024&report_type=ANNUAL" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "X-Idempotency-Key: $(uuidgen)"
```

## 2.3 월간/분기별 스케줄

변동이 적은 데이터는 월 1회 또는 분기 1회로 충분하다.

| 작업 | 엔드포인트 | 빈도 | 비고 |
|---|---|---|---|
| 채권 전체 조회 | `POST /admin/load-bonds` | 월 1회 | ~19,000건, 2~5분 |
| 정기예금 | `POST /admin/load-deposits` | 월 1회 | ~37건, 30초 이하 |
| 적금 | `POST /admin/load-savings` | 월 1회 | ~100건, 30초 이하 |
| 연금저축 | `POST /admin/load-annuity-savings` | 월 1회 | ~200건, 1분 이하 |
| 주택담보대출 | `POST /admin/load-mortgage-loans` | 월 1회 | ~100건, 30초 이하 |
| 전세자금대출 | `POST /admin/load-rent-house-loans` | 월 1회 | ~50건, 30초 이하 |
| 개인신용대출 | `POST /admin/load-credit-loans` | 월 1회 | ~50건, 30초 이하 |
| 기업 액션 (분할/합병) | `POST /admin/dart/load-corporate-actions` | 분기 1회 | 분기별 조회 |

## 2.4 Compass Score 재계산 타이밍

Compass Score는 3가지 데이터에 의존하므로, 모든 데이터가 갱신된 후 계산해야 한다.

| 트리거 | 재계산 범위 | 이유 |
|---|---|---|
| 일별 시세 적재 완료 후 | 전체 (batch-compute) | 기술 점수 + 리스크 점수 변동 |
| 재무제표 적재 완료 후 | 전체 (batch-compute) | 재무 점수 + 밸류에이션 점수 변동 |
| 개별 종목 조회 시 | 해당 종목만 (on-demand) | 실시간 점수 필요 시 |

**중요**: 일별 시세 적재 없이 Compass Score를 계산하면, 이전 시세 데이터 기반으로 기술/리스크 점수가 계산되어 부정확한 결과가 나온다.

## 2.5 시간대별 타임라인 다이어그램

```
영업일 기준 (월~금)
═══════════════════════════════════════════════════════════

 09:00 ┃ 한국 주식시장 개장
       ┃
 15:30 ┃ 한국 주식시장 폐장
       ┃
 16:00 ┃ KRX 데이터 확정 (pykrx 조회 가능)
       ┃
 16:30 ┃ ⚡ [자동] 증분 시계열 적재 시작 ─────────── ~2분 (실측)
       ┃
 17:00 ┃ ⚡ [자동] Compass Score 일괄 계산 시작 ──── ~2분 (실측)
       ┃
 17:05 ┃ (일일 수집 완료)
       ┃
       ┃  ... (야간 유휴 시간) ...
       ┃
 07:30 ┃ ⚡ [자동] 일일 시장 이메일 발송
       ┃
 08:00 ┃ ⚡ [자동] 워치리스트 점수 알림 발송
       ┃

주말 (토/일)
═══════════════════════════════════════════════════════════

 10:00 ┃ [주간] 종목 마스터 갱신 ─────────────────── 20초
       ┃
 10:01 ┃ [주간] 주식 기본 정보 갱신 ─────────────── 3~5분
       ┃
 10:10 ┃ [주간] ETF 기본 정보 갱신 ──────────────── 5~10분
       ┃
 10:20 ┃ [주간] DART 재무제표 적재 ──────────────── 40~60분
       ┃
 11:30 ┃ (주간 수집 완료)
       ┃

매월 첫째 주말
═══════════════════════════════════════════════════════════

 13:00 ┃ [월간] 채권 전체 조회 ──────────────────── 2~5분
       ┃
 13:10 ┃ [월간] 금융상품 6종 일괄 적재 ──────────── 5분 이하
       ┃   (예금 → 적금 → 연금저축 → 주담대 → 전세대 → 신용대)
       ┃
 13:20 ┃ (월간 수집 완료)
```

---

# Part 3: 자동화 구현

## 3.1 Phase 1 — 일일 수집 자동화 ✅ 구현 완료 (2026-02-15)

### 구현 파일

- **`backend/app/services/scheduled_data_collection.py`** (신규)
- **`backend/app/main.py`** lifespan에 CronTrigger 2개 추가

### 등록된 스케줄 (main.py)

```python
# Phase 1: 데이터 수집 자동화
scheduler.add_job(
    scheduled_incremental_load,
    CronTrigger(hour=16, minute=30, day_of_week="mon-fri", timezone="Asia/Seoul"),
    id="daily_incremental_prices",
    replace_existing=True,
)
scheduler.add_job(
    scheduled_compass_batch_compute,
    CronTrigger(hour=17, minute=0, day_of_week="mon-fri", timezone="Asia/Seoul"),
    id="daily_compass_score",
    replace_existing=True,
)
```

### 실측 결과 (2026-02-15)

| 함수 | 대상 | 결과 | 소요 시간 |
|---|---|---|---|
| `scheduled_incremental_load` | 2,886종목 | success=2,884, failed=2, inserted=8,641 | ~2분 20초 |
| `scheduled_compass_batch_compute` | 2,886종목 | success=2,872, fail=14 (0.5%) | ~2분 18초 |

### 주요 기능

- **동시 실행 방지**: `_running_tasks` set + `threading.Lock` — 동일 작업 중복 실행 시 즉시 스킵 (검증 완료)
- **OpsAlert 연동**: 실패 시 `BATCH_FAILED` 알림 자동 생성
  - 증분 적재: failed > 0 → WARN, 전체 실패 → CRITICAL
  - Compass Score: 실패율 > 30% → WARN, 전체 실패 → CRITICAL
- **progress_tracker 미사용**: 스케줄 작업은 UI 모니터링 불필요

### Phase 2에서 추가할 스케줄 (미구현)

```python
# 3. 종목 마스터 + 주식 정보 갱신 — 매주 토요일 10:00 KST
scheduler.add_job(
    scheduled_weekly_stock_refresh,
    CronTrigger(hour=10, minute=0, day_of_week="sat", timezone="Asia/Seoul"),
    id="weekly_stock_refresh",
)

# 4. DART 재무제표 — 매주 토요일 11:00 KST
scheduler.add_job(
    scheduled_dart_financials,
    CronTrigger(hour=11, minute=0, day_of_week="sat", timezone="Asia/Seoul"),
    id="weekly_dart_financials",
)

# 5. 채권 + 금융상품 — 매월 1일 13:00 KST
scheduler.add_job(
    scheduled_monthly_financial_products,
    CronTrigger(day=1, hour=13, minute=0, timezone="Asia/Seoul"),
    id="monthly_financial_products",
)
```

## 3.2 수집 순서 오케스트레이션 (의존성 기반)

복합 수집 작업(주간 등)은 의존 체인을 지켜야 한다.

```python
async def scheduled_weekly_stock_refresh():
    """주간 종목 마스터 + 주식 정보 + ETF 순차 갱신"""
    db = SessionLocal()
    try:
        loader = RealDataLoader(db)

        # Step 1: 종목 마스터
        logger.info("[WEEKLY] Step 1: FDR 종목 마스터 적재")
        loader.load_fdr_stock_listing(
            market="KRX",
            as_of_date=date.today(),
            operator_id="system",
            operator_reason="주간 자동 갱신",
        )

        # Step 2: 주식 기본 정보 (Step 1 완료 후)
        logger.info("[WEEKLY] Step 2: 주식 기본 정보 적재")
        loader.load_stocks_from_fdr(
            operator_id="system",
            operator_reason="주간 자동 갱신",
        )

        # Step 3: ETF (독립적이지만 순차 실행으로 부하 분산)
        logger.info("[WEEKLY] Step 3: ETF 적재")
        # ... ETF 적재 로직
    except Exception as e:
        logger.error(f"[WEEKLY] Stock refresh failed: {e}", exc_info=True)
    finally:
        db.close()
```

## 3.3 실패 처리 & 재시도 전략

| 에러 유형 | 대응 전략 | 재시도 횟수 | 대기 시간 |
|---|---|---|---|
| API 일시 장애 (5xx, timeout) | 지수 백오프 재시도 | 3회 | 30초, 60초, 120초 |
| API 호출 제한 초과 (429, DART 020) | 대기 후 재시도 | 2회 | 60초 고정 |
| 네트워크 오류 | 재시도 | 3회 | 10초 간격 |
| 인증 오류 (401, DART 010/011) | 즉시 중단 + 알림 | 0회 | — |
| 데이터 없음 (DART 013) | 스킵 (정상) | 0회 | — |
| DB 커넥션 오류 | 세션 재생성 후 재시도 | 2회 | 5초 |

### APScheduler 재시도 데코레이터

```python
import functools
import asyncio

def with_retry(max_retries=3, base_delay=30):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        logger.error(f"[RETRY] {func.__name__} failed after {max_retries} retries: {e}")
                        raise
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"[RETRY] {func.__name__} attempt {attempt+1} failed, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
        return wrapper
    return decorator
```

## 3.4 모니터링 & 알림 (OpsAlert 활용)

기존 `OpsAlert` 모델을 활용하여 수집 실패 시 알림을 생성한다.

```python
from app.models.ops import OpsAlert
from app.utils.kst_now import kst_now

def create_collection_alert(db, job_name: str, error_message: str, severity: str = "warning"):
    """데이터 수집 실패 알림 생성"""
    alert = OpsAlert(
        alert_type="data_collection_failure",
        severity=severity,
        title=f"[데이터 수집 실패] {job_name}",
        message=error_message[:500],
        source="scheduler",
        created_at=kst_now(),
    )
    db.add(alert)
    db.commit()
```

### 알림이 필요한 상황

| 상황 | severity | 설명 |
|---|---|---|
| 일별 시세 적재 실패 | **critical** | 이메일에 부정확한 데이터 포함 위험 |
| Compass Score 계산 실패율 > 30% | **warning** | 스크리너/이메일 데이터 품질 저하 |
| DART API 키 만료 | **critical** | 재무제표 수집 불가 |
| pykrx KRX 서버 응답 없음 | **warning** | 일시적 장애 (보통 자동 복구) |
| DB 커넥션 풀 고갈 | **critical** | 전체 서비스 장애 위험 |

## 3.5 8GB RAM 환경 최적화

| 항목 | 제한 설정 | 이유 |
|---|---|---|
| `num_workers` (pykrx 병렬) | **4** (기본 8 → 4로 축소) | 스레드당 DB 세션 + pykrx 메모리 |
| 동시 백그라운드 작업 | **1개** | 두 작업 동시 실행 시 OOM 위험 |
| DART API 동시 호출 | **1** (rate limit 겸용) | 1 req/sec 제한 |
| DB 커넥션 풀 | `pool_size=5, max_overflow=10` | 8GB RAM에서 적절 |
| Compass Score 배치 크기 | `limit=500` (한 번에) | 대량 계산 시 메모리 사용 급증 방지 |

### 동시 실행 방지 전략

```python
# 전역 실행 상태 관리
_running_collections = set()
_collection_lock = threading.Lock()

async def safe_scheduled_task(task_name: str, task_func):
    """동시 실행 방지 래퍼"""
    with _collection_lock:
        if task_name in _running_collections:
            logger.warning(f"[SKIP] {task_name} already running, skipping")
            return
        _running_collections.add(task_name)
    try:
        await task_func()
    finally:
        with _collection_lock:
            _running_collections.discard(task_name)
```

---

# Part 4: 장애 대응 & 운영 절차

## 4.1 소스별 장애 시나리오 & 대응

### pykrx (KRX 시세)

| 장애 유형 | 증상 | 대응 |
|---|---|---|
| KRX 서버 점검 | `get_market_ohlcv` 빈 DataFrame | 장외시간/공휴일 확인 → 다음 영업일 재시도 |
| HTTP 404 (get_market_fundamental) | 빈 응답 | **알려진 이슈** — 이 함수는 사용 불가 |
| 데이터 지연 | 당일 시세가 없음 | 16:00 이후에 재시도 (확정 시간 대기) |
| rate limit | Connection reset | `num_workers` 줄이고, `time.sleep(0.2)` 추가 |

### DART API

| 장애 유형 | 증상 | 대응 |
|---|---|---|
| 키 만료 (010/011) | `등록되지 않은 키` | .env DART_API_KEY 재발급 |
| 호출 한도 초과 (020) | `요청 제한을 초과` | 1시간 대기 또는 다음날 재시도 |
| 데이터 없음 (013) | `조회된 데이타가 없습니다` | 정상 — 해당 종목/기간 데이터 미존재 |
| 점검 시간 (800) | 매일 01:00~02:00 | 해당 시간 수집 금지 |
| corpCode.xml 파싱 오류 | ticker → corp_code 매핑 실패 | corpCode.xml 재다운로드 |

### FSC/FSS API

| 장애 유형 | 증상 | 대응 |
|---|---|---|
| API 서버 장애 | 500 에러 | 1시간 후 재시도 |
| 기준일자 데이터 없음 | 빈 응답 | 전 영업일로 재시도 (코드에 이미 구현됨) |
| FSS API 키 만료 | 401 | .env FSS_API_KEY 확인 |

### PostgreSQL

| 장애 유형 | 증상 | 대응 |
|---|---|---|
| 커넥션 풀 고갈 | `too many connections` | 앱 재시작 또는 idle 커넥션 kill |
| 디스크 부족 | INSERT 실패 | `VACUUM FULL` + 불필요 데이터 정리 |
| Lock timeout | 장시간 쿼리 블로킹 | `pg_stat_activity`에서 blocking 쿼리 확인 |

## 4.2 데이터 정합성 검증 체크리스트

수집 후 다음 항목을 확인한다.

### 일별 체크

- [ ] `stock_price_daily` 오늘 날짜 데이터 존재 여부
  ```sql
  SELECT COUNT(*) FROM stock_price_daily WHERE trade_date = CURRENT_DATE;
  ```
- [ ] 주요 종목 시세 정상 여부 (삼성전자 005930)
  ```sql
  SELECT * FROM stock_price_daily WHERE ticker = '005930' ORDER BY trade_date DESC LIMIT 3;
  ```
- [ ] Compass Score 갱신 여부
  ```sql
  SELECT COUNT(*) FROM stocks WHERE compass_updated_at::date = CURRENT_DATE;
  ```

### 주간 체크

- [ ] `stocks` 테이블 총 건수 확인 (예상: ~2,900건)
  ```sql
  SELECT COUNT(*) FROM stocks;
  ```
- [ ] 비활성 종목 비율 확인
  ```sql
  SELECT is_active, COUNT(*) FROM stocks GROUP BY is_active;
  ```
- [ ] `financial_statement` 최신 연도 건수
  ```sql
  SELECT fiscal_year, COUNT(*) FROM financial_statement GROUP BY fiscal_year ORDER BY fiscal_year DESC;
  ```

### 월간 체크

- [ ] 전체 데이터 통계 (`GET /admin/data-status`)
- [ ] 금융상품 데이터 건수 확인
  ```sql
  SELECT 'deposits' as type, COUNT(*) FROM deposit_products
  UNION ALL SELECT 'savings', COUNT(*) FROM savings_products
  UNION ALL SELECT 'bonds', COUNT(*) FROM bonds;
  ```
- [ ] `stock_price_daily` 테이블 크기 확인
  ```sql
  SELECT pg_size_pretty(pg_total_relation_size('stock_price_daily'));
  ```

## 4.3 수동 복구 절차

### 시나리오 1: 일별 시세 적재 누락 (특정 날짜)

```bash
# 누락된 날짜를 지정하여 적재
curl -X POST "http://localhost:8000/admin/pykrx/load-daily-prices" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: $(uuidgen)" \
  -d '{
    "start_date": "20260213",
    "end_date": "20260213",
    "parallel": true,
    "num_workers": 4
  }'
```

### 시나리오 2: Compass Score 특정 종목 재계산

```bash
# 개별 종목 재계산
curl "http://localhost:8000/admin/scoring/compass/005930" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### 시나리오 3: 전체 초기 적재 (신규 환경 구축)

순서가 매우 중요하다. 아래 순서를 반드시 지킨다.

```bash
# Step 1: 종목 마스터 (동기, 10~20초)
curl -X POST "http://localhost:8000/admin/fdr/load-stock-listing" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: $(uuidgen)" \
  -d '{"market": "KRX"}'

# Step 2: 주식 기본 정보 (백그라운드, 3~5분) — Step 1 완료 확인 후
curl -X POST "http://localhost:8000/admin/load-stocks" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "X-Idempotency-Key: $(uuidgen)"
# → task_id 확인 후 진행률 모니터링
# curl "http://localhost:8000/admin/progress/{task_id}" -H "Authorization: Bearer $ADMIN_TOKEN"

# Step 3: 일별 시세 증분 적재 (백그라운드, 10~40분) — Step 2 완료 확인 후
curl -X POST "http://localhost:8000/admin/pykrx/load-stocks-incremental" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: $(uuidgen)" \
  -d '{"default_days": 1825, "num_workers": 4}'

# Step 4: DART 재무제표 (백그라운드, 40~60분) — Step 2 완료 확인 후 (Step 3과 병렬 가능하지만 8GB 환경에서는 순차 권장)
curl -X POST "http://localhost:8000/admin/dart/load-financials?fiscal_year=2024&report_type=ANNUAL" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "X-Idempotency-Key: $(uuidgen)"

# Step 5: ETF (백그라운드, 5~10분)
curl -X POST "http://localhost:8000/admin/load-etfs" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "X-Idempotency-Key: $(uuidgen)"

# Step 6: Compass Score 일괄 계산 (백그라운드, 10~30분) — Step 3 + Step 4 완료 후
curl -X POST "http://localhost:8000/admin/scoring/batch-compute?limit=3000" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "X-Idempotency-Key: $(uuidgen)"

# Step 7: 채권 + 금융상품 (Step 2~6과 독립적, 언제든 실행 가능)
curl -X POST "http://localhost:8000/admin/load-bonds?quality_filter=all" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "X-Idempotency-Key: $(uuidgen)"

curl -X POST "http://localhost:8000/admin/load-deposits" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "X-Idempotency-Key: $(uuidgen)"

curl -X POST "http://localhost:8000/admin/load-savings" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "X-Idempotency-Key: $(uuidgen)"
```

### 시나리오 4: 진행 중인 작업 상태 확인

```bash
# 모든 작업 진행 상황 조회
curl "http://localhost:8000/admin/progress" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 특정 작업 진행 상황 조회
curl "http://localhost:8000/admin/progress/{task_id}" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 완료된 작업 정리
curl -X DELETE "http://localhost:8000/admin/progress/{task_id}" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

# Part 5: 로드맵

## ~~Phase 1: 핵심 자동화~~ ✅ 완료 (2026-02-15)

| 항목 | 작업 내용 | 상태 |
|---|---|---|
| 1-1 | `scheduled_data_collection.py` 서비스 파일 생성 | ✅ |
| 1-2 | `scheduled_incremental_load()` 구현 — 일별 시세 증분 적재 | ✅ 2,884종목/~2분 |
| 1-3 | `scheduled_compass_batch_compute()` 구현 — Compass Score 계산 | ✅ 2,872종목/~2분 |
| 1-4 | `main.py` lifespan에 2개 CronTrigger 추가 (16:30, 17:00) | ✅ |
| 1-5 | 동시 실행 방지 Lock 추가 | ✅ 스레드 테스트 통과 |
| 1-6 | OpsAlert 연동 (실패 시 알림 생성) | ✅ WARN/CRITICAL |

### Phase 1 완료 검증 결과

- ✅ 서버 시작 시 APScheduler 4개 job 등록 로그 확인
- ✅ `scheduled_incremental_load` 수동 실행 — success=2,884, inserted=8,641
- ✅ `scheduled_compass_batch_compute` 수동 실행 — success=2,872, fail=14 (0.5%)
- ✅ 동시 실행 방지 — 2개 스레드 동시 호출 시 두 번째 즉시 스킵
- ✅ OpsAlert 테이블에 WARN 알림 4건 정상 기록

## Phase 2: 전체 자동화 (예상 공수: 2~3일)

주간/월간 수집까지 자동화한다.

| 항목 | 작업 내용 | 우선순위 |
|---|---|---|
| 2-1 | `scheduled_weekly_stock_refresh()` 구현 — 종목 마스터 + 주식 정보 + ETF | 높음 |
| 2-2 | `scheduled_dart_financials()` 구현 — DART 재무제표 | 높음 |
| 2-3 | `scheduled_monthly_financial_products()` 구현 — 채권 + 금융상품 6종 | 중간 |
| 2-4 | main.py에 3개 CronTrigger 추가 (토 10:00, 토 11:00, 1일 13:00) | 중간 |
| 2-5 | 의존성 기반 순차 실행 로직 (weekly는 3단계 순차) | 중간 |
| 2-6 | 재시도 데코레이터 (`with_retry`) 적용 | 낮음 |

### Phase 2 완료 기준

- 주간/월간 수집이 자동으로 실행됨
- 수동 curl 실행이 불필요해짐
- 의존 순서가 보장됨

## Phase 3: 모니터링 대시보드 + 알림 고도화 (예상 공수: 3~5일)

운영 가시성을 높인다.

| 항목 | 작업 내용 | 우선순위 |
|---|---|---|
| 3-1 | 관리자 대시보드에 "수집 스케줄" 탭 추가 | 중간 |
| 3-2 | 스케줄 실행 이력 테이블 (`data_collection_log`) | 중간 |
| 3-3 | 실행 이력 조회 API (`GET /admin/collection-logs`) | 중간 |
| 3-4 | 프론트엔드: 스케줄 상태 카드 (최근 실행, 다음 실행, 상태) | 낮음 |
| 3-5 | Slack/이메일 알림 연동 (OpsAlert → 외부 알림) | 낮음 |
| 3-6 | 수집 간 데이터 정합성 자동 검증 | 낮음 |

### Phase 3 완료 기준

- 관리자가 웹에서 수집 상태를 실시간으로 확인할 수 있음
- 실패 시 Slack 또는 이메일로 즉시 알림
- 수집 이력이 DB에 기록되어 추후 분석 가능

---

## 부록: 참조 파일 경로

| 파일 | 설명 |
|---|---|
| `backend/app/main.py:86-130` | APScheduler 설정 (수집 2개 + 이메일 2개) |
| `backend/app/services/scheduled_data_collection.py` | 데이터 수집 스케줄 서비스 (Phase 1) |
| `backend/app/routes/admin.py` | 전체 수집 엔드포인트 (27개+) |
| `backend/app/services/pykrx_loader.py` | pykrx 병렬 + 배치 로더 |
| `backend/app/services/real_data_loader.py` | 마스터 데이터 로더 |
| `backend/app/services/fetchers/dart_fetcher.py` | DART API 클라이언트 |
| `backend/app/services/scoring_engine.py` | Compass Score 4축 계산 |
| `backend/app/services/market_email_service.py` | 07:30 시장 이메일 |
| `backend/app/services/watchlist_alert_service.py` | 08:00 워치리스트 알림 |
| `backend/app/progress_tracker.py` | 진행률 추적 시스템 |
| `backend/app/routes/admin_data_load.py` | v1 데이터 적재 API |
| `backend/app/models/ops.py` | OpsAlert, OpsAuditLog 모델 |
