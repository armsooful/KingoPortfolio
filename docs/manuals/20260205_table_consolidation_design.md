# 테이블 통합 설계 문서

**작성일:** 2026-02-05
**작성자:** Phase 11 Data Extension
**대상 DB:** PostgreSQL (`kingo`, `public` 스키마)

---

## 1. 현재 상태

### 1.1 테이블 분류

현재 테이블은 **교육용(Educational)** 과 **실데이터(Real-Data)** 두 레이어로 분리되어 있습니다.

| 레이어 | 테이블 | 행 수 | 역할 |
|--------|--------|------:|------|
| 교육용 | `stocks` | 2,773 | 주식 마스터 (종목정보 + 분류 + 현재가) |
| 교육용 | `etfs` | 1,067 | ETF 마스터 |
| 교육용 | `bonds` | 0 | 채권 마스터 (수동 3건 시드 대기) |
| 교육용 | `deposit_products` | 0 | 예금 마스터 (수동 4건 시드 대기) |
| 실데이터 | `fdr_stock_listing` | 2,886 | FDR 종목 리스팅 스냅샷 |
| 실데이터 | `stock_info` | 0 | KRX 종목 기본정보 |
| 실데이터 | `bond_basic_info` | 5 | FSC 채권기본정보 |
| 실데이터 | `dividend_history` | 209 | FSC 배당이력 |
| 실데이터 | `stocks_daily_prices` | 400 | pykrx 일별 시세 |
| 실데이터 | `krx_timeseries` | 2,155 | KRX 일별 시세 (레거시) |
| 실데이터 | `stock_financials` | 20 | 재무제표 (레거시) |
| 실데이터 | `stock_price_daily` | 0 | Phase 11 일별 시세 |
| 실데이터 | `index_price_daily` | 0 | 지수 일별 시세 |
| 실데이터 | `corporate_action` | 0 | 기업액션 이력 |
| 실데이터 | `institution_trade` | 0 | 기관/외국인 매매 |
| 실데이터 | `financial_statement` | 0 | DART 재무제표 |
| 거버넌스 | `data_source` | 3 | 데이터 소스 마스터 |
| 거버넌스 | `data_load_batch` | 28 | 적재 배치 이력 |

### 1.2 현재 이분 구조의 문제

```
주식:  stocks (교육) ←→ stock_info / fdr_stock_listing / stock_price_daily (실데이터)
ETF:   etfs   (교육) ←→ 실데이터 없음
채권:  bonds  (교육) ←→ bond_basic_info (실데이터)
예금:  deposit_products (교육) ←→ 실데이터 없음
```

- 동일 종목이 두 테이블에 분산 → 조인 없이 시뮬레이션과 실데이터를 연결할 수 없음
- 실데이터 적재 시 교육용 테이블의 `investment_type`, `risk_level` 등이 갱신되지 않음
- 교육용 테이블만 직접 쿼리되어, 실데이터가 적재되더라도 시뮬레이션 결과는 변하지 않음

---

## 2. 통합 원칙

### 2.1 마스터 테이블만 통합, 시계열·이벤트 테이블은 유지

```
통합 대상 (마스터):     stocks, etfs, bonds, deposits
유지 대상 (시계열):     stock_price_daily, stocks_daily_prices, index_price_daily, krx_timeseries
유지 대상 (이벤트):     dividend_history, corporate_action, institution_trade
유지 대상 (재무보고서): financial_statement, stock_financials
유지 대상 (거버넌스):   data_source, data_load_batch, data_quality_log
제거 대상 (마스터 중복): stock_info, fdr_stock_listing, bond_basic_info
```

마스터 테이블은 종목당 **1행**을 유지하며, 실데이터 적재 시 해당 행을 UPDATE하여 갱신합니다.
시계열 테이블은 날짜당 1행의 구조를 유지하므로 별도 테이블이 적절합니다.

### 2.2 테이블 명명 규칙

| 자산종류 | 통합 테이블명 | 기존 교육용 | 기존 실데이터 (통합 후 제거) |
|----------|--------------|-------------|-------------------------------|
| 주식 | `stocks` | `stocks` | `stock_info`, `fdr_stock_listing` |
| ETF | `etfs` | `etfs` | 없음 |
| 채권 | `bonds` | `bonds` | `bond_basic_info` |
| 예금 | `deposits` | `deposit_products` | 없음 |

> `deposit_products` → `deposits`로 테이블명 변경. ORM 클래스명은 `Deposit`으로 단순화.

### 2.3 컬럼 설계 원칙

1. 교육용 컬럼 (`investment_type`, `risk_level`, `is_active`) — **유지**. 시뮬레이션 엔진의 직접 조건
2. 실데이터 컬럼 — 기존 실데이터 테이블의 컬럼을 그대로 추가
3. 거버넌스 컬럼 (`source_id`, `batch_id`, `as_of_date`) — 추가. 마스터 갱신 시 적재 이력 추적용
4. 중복 컬럼 — 실데이터와 교육용이 같은 개념이면 하나로 통합 (예: `interest_rate` ↔ `bond_srfc_inrt`)

---

## 3. 통합 후 테이블 구조

### 3.1 `stocks` (주식 마스터)

현재 `stocks` 컬럼을 기본으로, `stock_info`·`fdr_stock_listing`의 마스터 컬럼을 추가합니다.

| 컬럼 | 타입 | 출처 | 비고 |
|------|------|------|------|
| **ticker** | String(10) PK | stocks | 종목코드 |
| name | String(100) | stocks | 종목명 |
| company | String(100) | stocks | 영문 회사명 |
| crno | String(13) | stocks | 법인등록번호 (배당 조회용) |
| sector | String(50) | stocks | 업종명 (= stock_info.sector_name) |
| market | String(20) | stocks | KOSPI / KOSDAQ / KONEX |
| current_price | Float | stocks | 현재가 (실시간 갱신 대상) |
| market_cap | Float | stocks | 시가총액 |
| pe_ratio | Float | stocks | PER |
| pb_ratio | Float | stocks | PBR |
| dividend_yield | Float | stocks | 배당수익률 (%) |
| ytd_return | Float | stocks | YTD 수익률 |
| one_year_return | Float | stocks | 1년 수익률 |
| risk_level | String(20) | stocks | low / medium / high (DataClassifier 계산) |
| investment_type | String(100) | stocks | CSV: conservative,moderate,aggressive |
| category | String(50) | stocks | 배당주 / 기술주 / 대형주 |
| description | String(500) | stocks | |
| logo_url | String(300) | stocks | |
| is_active | Boolean | stocks | |
| **sector_code** | String(10) | stock_info | 업종코드 (추가) |
| **industry_code** | String(10) | stock_info | 세분업종코드 (추가) |
| **industry_name** | String(50) | stock_info | 세분업종명 (추가) |
| **listing_date** | Date | stock_info / fdr | 상장일 (추가) |
| **fiscal_month** | Integer | stock_info | 결산월 (추가) |
| **face_value** | Integer | stock_info / fdr | 액면가 (추가) |
| **shares_listed** | BigInteger | stock_info / fdr | 상장주식수 (추가) |
| **shares_outstanding** | BigInteger | stock_info | 발행주식수 (추가) |
| **ceo_name** | String(100) | stock_info | 대표이사 (추가) |
| **headquarters** | String(200) | stock_info | 본사 주소 (추가) |
| **website** | String(300) | stock_info | 홈페이지 (추가) |
| **source_id** | String(20) FK | 거버넌스 | 마지막 갱신 소스 (추가, nullable) |
| **batch_id** | Integer FK | 거버넌스 | 마지막 갱신 배치 (추가, nullable) |
| **as_of_date** | Date | 거버넌스 | 데이터 기준일 (추가, nullable) |
| last_updated | DateTime | stocks | |
| created_at | DateTime | stocks | |

### 3.2 `etfs` (ETF 마스터)

현재 구조 유지. 실데이터 카운터파트가 없으므로 변경 없음.
향후 실데이터 적재 시 `source_id`, `batch_id`, `as_of_date` 컬럼을 추가합니다.

### 3.3 `bonds` (채권 마스터)

현재 `bonds`의 교육용 컬럼과 `bond_basic_info`의 실데이터 컬럼을 합치며, 중복 컬럼은 통합합니다.

| 컬럼 | 타입 | 출처 | 비고 |
|------|------|------|------|
| **id** | Integer PK | bonds | 자증증가 |
| name | String(100) | bonds | 채권명 (= bond_basic_info.isin_cd_nm으로 갱신 가능) |
| bond_type | String(50) | bonds | government / corporate / high_yield (scrs_itms_kcd로부터 매핑) |
| issuer | String(100) | bonds | 발행인명 (= bond_isur_nm) |
| interest_rate | Float | bonds | 표면이율 (= bond_srfc_inrt) — 통합 컬럼 |
| coupon_rate | Float | bonds | 이표율 (bond_srfc_inrt와 동일시 제거 가능) |
| maturity_years | Integer | bonds | 만기연수 (= (bond_expr_dt - bond_issu_dt).days / 365로 계산) |
| credit_rating | String(10) | bonds | AAA / AA / A / BBB (kis_scrs_itms_kcd 코드로부터 매핑) |
| risk_level | String(20) | bonds | low / medium / high (credit_rating으로부터 유도) |
| investment_type | String(100) | bonds | CSV (risk_level + bond_type으로부터 유도) |
| minimum_investment | Integer | bonds | |
| description | String(500) | bonds | |
| is_active | Boolean | bonds | 만기일 기준 자동 갱신 가능 |
| **isin_cd** | String(12) | bond_basic_info | ISIN 코드 (추가, unique) |
| **bas_dt** | String(8) | bond_basic_info | API 조회 기준일 (추가) |
| **crno** | String(13) | bond_basic_info | 법인등록번호 (추가) |
| **scrs_itms_kcd** | String(4) | bond_basic_info | 유가증권종목종류코드 (추가) |
| **scrs_itms_kcd_nm** | String(100) | bond_basic_info | 유가증권종목종류코드명 (추가) |
| **bond_issu_dt** | Date | bond_basic_info | 발행일 (추가) |
| **bond_expr_dt** | Date | bond_basic_info | 만기일 (추가) |
| **bond_issu_amt** | Numeric(22,3) | bond_basic_info | 발행금액 (추가) |
| **bond_bal** | Numeric(22,3) | bond_basic_info | 잔액 (추가) |
| **irt_chng_dcd** | String(1) | bond_basic_info | 금리변동구분 Y/N (추가) |
| **bond_int_tcd** | String(1) | bond_basic_info | 이자유형코드 (추가) |
| **int_pay_cycl_ctt** | String(100) | bond_basic_info | 이자지급주기 (추가) |
| **nxtm_copn_dt** | Date | bond_basic_info | 차기이표일 (추가) |
| **rbf_copn_dt** | Date | bond_basic_info | 직전이표일 (추가) |
| **grn_dcd** | String(1) | bond_basic_info | 보증구분코드 (추가) |
| **bond_rnkn_dcd** | String(1) | bond_basic_info | 순위구분코드 (추가) |
| **kis_scrs_itms_kcd** | String(4) | bond_basic_info | KIS 신용등급 코드 (추가) |
| **kbp_scrs_itms_kcd** | String(4) | bond_basic_info | KBP 신용등급 코드 (추가) |
| **nice_scrs_itms_kcd** | String(4) | bond_basic_info | NICE 신용등급 코드 (추가) |
| **fn_scrs_itms_kcd** | String(4) | bond_basic_info | FN 신용등급 코드 (추가) |
| **bond_offr_mcd** | String(2) | bond_basic_info | 모집방법코드 (추가) |
| **lstg_dt** | Date | bond_basic_info | 상장일 (추가) |
| **prmnc_bond_yn** | String(1) | bond_basic_info | 영구채권여부 (추가) |
| **strips_psbl_yn** | String(1) | bond_basic_info | 스트립스가능여부 (추가) |
| **source_id** | String(20) FK | 거버넌스 | (추가) |
| **batch_id** | Integer FK | 거버넌스 | (추가) |
| **as_of_date** | Date | 거버넌스 | (추가) |
| last_updated | DateTime | bonds | |
| created_at | DateTime | bonds | |

### 3.4 `deposits` (예금 마스터)

`deposit_products` → `deposits`로 테이블명 변경. 컬럼 구조는 동일.
실데이터 카운터파트가 없으므로 추가 컬럼 없음.

---

## 4. 핵심 매핑 로직

통합 테이블의 교육용 컬럼을 실데이터로부터 자동 유도하기 위한 매핑 로직입니다.
이 로직은 별도 서비스 모듈(`mapping_service.py`)로 구현합니다.

### 4.1 채권 신용등급 코드 → 텍스트 매핑

FSC API의 신용등급 컬럼은 숫자 코드입니다. 아래는 KIS 기준 매핑 예시:

| 코드 | 등급 | risk_level |
|------|------|------------|
| 100 | AAA | low |
| 110 | AA+, AA, AA- | low |
| 120 | A+, A, A- | low |
| 130 | BBB+, BBB, BBB- | medium |
| 140 | BB+, BB, BB- | high |
| 150 이상 | B 이하 | high |

> 실제 코드-등급 매핑은 FSC 공개 코드표를 기준으로 검증 필요. 초기 구현 시 KIS 등급만 사용하고, 다른 등급 기관과 비교·검증 단계를 추가합니다.

### 4.2 채권종류 코드 → bond_type 매핑

| scrs_itms_kcd | 종류명 | bond_type |
|---------------|--------|-----------|
| 0301, 0302 | 국debt | government |
| 0303, 0304 | 지방정부 | government |
| 0401~0499 | 회사채 | corporate |
| 기타 (하이일드 판별) | — | high_yield (credit_rating ≤ BBB로 판별) |

### 4.3 investment_type 유도 규칙

현재 시뮬레이션 엔진은 `investment_type.contains("conservative")` 등으로 필터링합니다.
유도 규칙은 기존 `DataClassifier`와 동일한 논리로:

```
risk_level = low   → conservative, moderate, aggressive (모두 포함)
risk_level = low   + bond_type = government → conservative, moderate, aggressive
risk_level = medium → moderate, aggressive
risk_level = high  → aggressive
```

주식도 동일하게 `DataClassifier.classify_investment_type()` 기존 로직 재사용.

---

## 5. 모듈 영향도 분석

### 5.1 영향받는 모듈 (수정 필요)

| 모듈 | 파일 | 영향 내용 |
|------|------|-----------|
| 포트폴리오 엔진 | `services/portfolio_engine.py` | `Bond` 쿼리 변경 없음 (컬럼명 유지). `DepositProduct` → `Deposit` 클래스명 변경 |
| 추천 엔진 | `db_recommendation_engine.py` | 동일. `DepositProduct` → `Deposit` 클래스명 변경 |
| 데이터 로더 | `services/data_loader.py` | bonds 시드 3건: 실데이터 적재 후 불필요 (deprecated). deposits 시드 유지 |
| Admin 라우트 | `routes/admin.py` | `GET /bonds` — ORM 클래스명 변경. `GET /deposits` — 테이블명·클래스명 변경 |
| Portfolio Admin | `routes/admin_portfolio.py` | `Bond`, `DepositProduct` → `Deposit` 클래스명 변경 |
| ORM 모델 | `models/securities.py` | `Bond` 클래스에 컬럼 추가. `DepositProduct` → `Deposit` + `__tablename__ = "deposits"` |
| ORM 모델 | `models/real_data.py` | `BondBasicInfo` 클래스 제거 (통합 후) |
| Real Data Loader | `services/real_data_loader.py` | `load_bond_basic_info()` → `bonds` 테이블에 직접 upsert로 변경 |
| Fetcher | `fetchers/bond_basic_info_fetcher.py` | Fetcher 자체는 유지 (API 통신 책임). 로더 쪽에서 대상 테이블 변경 |
| Seed 스크립트 | `scripts/seed_data_sources.py` | 변경 없음 |

### 5.2 영향 없는 모듈

| 모듈 | 사유 |
|------|------|
| `routes/securities.py` | Bond, DepositProduct 직접 참조 없음 |
| `services/fetchers/base_fetcher.py` | DataType enum은 API 레벨, 테이블 구조 무관 |
| `services/fetchers/fetcher_factory.py` | 동일 |
| `services/batch_manager.py` | BatchType은 적재 작업 분류, 테이블 구조 무관 |
| Frontend | API 응답 스키마가 변하지 않으면 변경 불필요 |

### 5.3 Pydantic 스키마 영향

현재 응답 스키마는 교육용 컬럼만 반환합니다. 실데이터 컬럼을 추가적으로 반환하려면 스키마 확장이 필요합니다. 이는 Phase 별로 점진적으로 진행합니다.

---

## 6. 마이그레이션 단계 (단계별 구현 계획)

### Phase A — 기본 통합 준비 (현재 → 다음 단계)

**목표:** ORM 모델 컬럼 추가 + DDL migration + 테이블명 변경

작업:
1. `models/securities.py`의 `Bond` 클래스에 bond_basic_info 컬럼들을 추가 (nullable)
2. `models/securities.py`의 `DepositProduct` → `Deposit`, `__tablename__` → `"deposits"`로 변경
3. PostgreSQL에 ALTER TABLE DDL 실행 (컬럼 추가, 테이블명 변경)
4. 기존 `bond_basic_info` 테이블의 5건 데이터를 `bonds`로 마이그레이션 (매핑 로직 적용)
5. 모든 `DepositProduct` 참조를 `Deposit`으로 변경

검증:
- 기존 bonds 시드 3건과 마이그레이션된 bond_basic_info 5건이 모두 bonds에 존재
- 포트폴리오 엔진 시뮬레이션 정상 동작
- `GET /admin/bonds`, `GET /admin/deposits` 정상 응답

### Phase B — 실데이터 적재 대상 전환

**목표:** Fetcher → unified table 직접 적재

작업:
1. `real_data_loader.py`의 `load_bond_basic_info()` 대상을 `bonds` 테이블로 변경
   - 기존: `BondBasicInfo` ORM → `bond_basic_info` 테이블
   - 변경: `Bond` ORM → `bonds` 테이블 (upsert: isin_cd 기준)
2. 적재 시 매핑 로직 실행: 신용등급 코드 → `credit_rating`, `risk_level`, `investment_type` 자동 계산
3. `stocks` 테이블도 동일한 패턴으로 `stock_info` / `fdr_stock_listing` 컬럼 적재 전환
4. `bond_basic_info`, `stock_info`, `fdr_stock_listing` 테이블을 deprecated로 표시

검증:
- FSC API 적재 후 `bonds` 테이블에 isin_cd, credit_rating, investment_type 모두 채워짐
- 포트폴리오 엔진이 실제 FSC 채권 데이터로 시뮬레이션 실행

### Phase C — 하위 호환 정리 및 레거시 제거

**목표:** 제거 대상 테이블 삭제, 시드 스크립트 정리

작업:
1. `bond_basic_info` 테이블과 `BondBasicInfo` ORM 클래스 제거
2. `stock_info`, `fdr_stock_listing` 테이블과 ORM 클래스 제거
3. `data_loader.py`의 `load_bonds()` 시드 3건을 deprecated 주석으로 표시 또는 제거
   - Phase A·B에서 실데이터로 채워지면 수동 시드 불필요
4. `krx_timeseries`, `stock_financials` (레거시 시계열) 제거 여부 평가
   - `stock_price_daily` 또는 `stocks_daily_prices`로 대체 가능하면 제거

---

## 7. 향후 진행 방향

### 7.1 단기 (Phase A·B)
- bonds 통합 구현 (가장 구체적인 실데이터가 있음: bond_basic_info 5건, dividend_history 209건)
- stocks 통합 구현 (fdr_stock_listing 2,886건 활용)
- 신용등급 코드 매핑 테이블 구현 및 검증

### 7.2 중기
- ETF 실데이터 적재 구현 (현재 실데이터 카운터파트 없음)
- 예금 실데이터 적재 구현 (은행 API 연동 평가)
- `current_price` 갱신: stock_price_daily → stocks.current_price 배치 갱신
- 시계열 테이블 통일 평가: `krx_timeseries` + `stocks_daily_prices` + `stock_price_daily` 중 하나로 통합

### 7.3 장기
- 레거시 테이블 (`krx_timeseries`, `stock_financials`, `bond_basic_info`, `stock_info`, `fdr_stock_listing`) 제거
- API 응답 스키마에 실데이터 컬럼 단계별 추가
- 프론트엔드 UI에서 실데이터 기반 정보 표시 (예: 실제 신용등급, 발행금액, 만기일)

---

## 8. 참고: 현재 쿼리 패턴 (변경 대상 파악용)

통합 후 이 쿼리들이 정상 동작하는지 회귀 검증의 핵심입니다.

```python
# portfolio_engine.py — _select_bonds()
Bond.is_active == True
Bond.investment_type.contains(investment_type)  # e.g. "conservative"
Bond.interest_rate.desc()  # 정렬

# portfolio_engine.py — _select_stocks()
Stock.is_active == True
Stock.investment_type.contains(investment_type)
Stock.current_price > 0

# portfolio_engine.py — _select_etfs()
ETF.is_active == True
ETF.investment_type.contains(investment_type)
ETF.current_price > 0

# portfolio_engine.py — _select_deposits()
DepositProduct.is_active == True  # → Deposit.is_active
DepositProduct.interest_rate.desc()  # → Deposit.interest_rate

# db_recommendation_engine.py — 동일 패턴
Bond.investment_type.contains(investment_type)
Bond.is_active == True

# admin_portfolio.py — 건수 집계
Bond.is_active == True, Bond.investment_type.contains(inv_type)
```

---

*이 문서는 living document로 각 Phase 구현 후 실제 결과를 반영하여 갱신합니다.*
