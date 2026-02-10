# FSS 금융상품 한 눈에 API 구현 가이드

## 개요

금융감독원(FSS) '금융상품 한 눈에' OpenAPI 전체 상품 유형 6종에 대한 데이터 적재 파이프라인 구현을 완료하였다.
본 문서는 각 API별 구현 내역, DB 모델, 파이프라인 구조, 적재 결과를 정리한다.

**데이터 소스**: `http://finlife.fss.or.kr/finlifeapi/`
**인증 키**: `.env` 파일의 `FSS_API_KEY`
**API 목록 참조**: [finlife_open_api.md](../finlife_open_api.md)

---

## 구현 완료 상품 요약

| # | 상품 유형 | API Endpoint | 적재 건수(상품) | 적재 건수(옵션) | 권역 수 |
|---|----------|-------------|----------------|----------------|---------|
| 1 | 정기예금 | `depositProductsSearch.json` | 137 | ~600+ | 5 |
| 2 | 적금 | `savingProductsSearch.json` | 328 | 1,537 | 5 |
| 3 | 연금저축 | `annuitySavingProductsSearch.json` | 343 | 17,888 | 5 |
| 4 | 주택담보대출 | `mortgageLoanProductsSearch.json` | 113 | 298 | 5 |
| 5 | 전세자금대출 | `rentHouseLoanProductsSearch.json` | 57 | 106 | 5 |
| 6 | 개인신용대출 | `creditLoanProductsSearch.json` | 112 | 276 | 5 |

**합계**: 1,090개 상품, 20,705개 옵션

---

## 공통 아키텍처

### 권역코드 (topFinGrpNo)

모든 API는 아래 5개 권역을 순차 호출하여 데이터를 수집한다.

| 코드 | 권역명 |
|------|--------|
| `020000` | 은행 |
| `030200` | 여신전문금융 |
| `030300` | 저축은행 |
| `050000` | 보험 |
| `060000` | 금융투자 |

### 파이프라인 구조

모든 상품 유형이 동일한 4계층 구조를 따른다.

```
[Fetcher] → [Loader] → [Admin Route] → [Frontend UI]
```

| 계층 | 역할 | 위치 |
|------|------|------|
| **Fetcher** | FSS API 호출, JSON 파싱, 상품+옵션 매핑 | `backend/app/services/fetchers/` |
| **Loader** | DB upsert (상품) + delete/insert (옵션) | `backend/app/services/real_data_loader.py` |
| **Admin Route** | BackgroundTasks 실행, progress_tracker 연동 | `backend/app/routes/admin.py` |
| **Frontend** | 적재 버튼, ProgressModal 실시간 진행률 | `frontend/src/pages/DataManagementPage.jsx` |

### DB 모델 패턴

모든 상품은 **정규화 방식**(상품 + 옵션 분리)으로 구현하였다.

- **상품 테이블**: Unique key = `(fin_co_no, fin_prdt_cd)`
- **옵션 테이블**: FK → 상품 테이블 (CASCADE delete-orphan)
- **Upsert**: 기존 상품은 UPDATE, 신규 상품은 INSERT
- **옵션 갱신**: 기존 옵션 DELETE 후 재 INSERT (옵션 변동 시 정확도 보장)

### Progress Tracker 패턴

FSS 상품은 단일 단계로 처리되므로 Phase 1/2 배지를 숨긴다.

```python
# 직접 초기화 (start_task 대신)
progress_tracker._progress[task_id] = {
    "status": "running", "total": 0, "current": 0,
    "phase": "", ...  # phase 비워서 Phase 배지 숨김
}

# [TOTAL] 콜백으로 동적 total 설정
progress_callback(-1, f"[TOTAL]{total_count}", True)
```

---

## 상품별 구현 상세

### 1. 정기예금 (Deposit)

**API**: `depositProductsSearch.json`

#### DB 모델

| 테이블 | 모델 클래스 | 설명 |
|--------|------------|------|
| `deposit_products` | `DepositProduct` | 상품 기본정보 |
| `deposit_rate_options` | `DepositRateOption` | 기간별 금리 옵션 |

#### 옵션 구조

| 필드 | 설명 | 예시 |
|------|------|------|
| `save_trm` | 저축기간 (개월) | 6, 12, 24, 36 |
| `intr_rate_type` | 금리유형 | S(단리), M(복리) |
| `intr_rate` | 기본금리 (%) | 2.80 |
| `intr_rate2` | 최고우대금리 (%) | 2.80 |

#### 구현 파일

| 파일 | 내용 |
|------|------|
| `backend/app/services/fetchers/deposit_fetcher.py` | `FssDepositFetcher` |
| `backend/app/services/real_data_loader.py` | `load_deposit_products()` |
| `backend/app/routes/admin.py` | `POST /admin/load-deposits` |

---

### 2. 적금 (Savings)

**API**: `savingProductsSearch.json`

#### DB 모델

| 테이블 | 모델 클래스 | 설명 |
|--------|------------|------|
| `savings_products` | `SavingsProduct` | 상품 기본정보 |
| `savings_rate_options` | `SavingsRateOption` | 기간별/적립유형별 금리 옵션 |

#### 옵션 구조 (예금 대비 추가 필드)

| 필드 | 설명 | 예시 |
|------|------|------|
| `rsrv_type` | 적립유형 | S(정액적립식), F(자유적립식) |
| `rsrv_type_nm` | 적립유형명 | 정액적립식 |

#### 다중 페이지 지원

적금은 저축은행 권역에서 274건(3페이지)이 발생하므로 `_fetch_all_pages()` 루프를 도입하였다.
이후 구현된 모든 상품 유형에 동일하게 적용하였다.

#### 구현 파일

| 파일 | 내용 |
|------|------|
| `backend/app/services/fetchers/savings_fetcher.py` | `FssSavingsFetcher` |
| `backend/app/services/real_data_loader.py` | `load_savings_products()` |
| `backend/app/routes/admin.py` | `POST /admin/load-savings` |

---

### 3. 연금저축 (Annuity Savings)

**API**: `annuitySavingProductsSearch.json`

#### DB 모델

| 테이블 | 모델 클래스 | 설명 |
|--------|------------|------|
| `annuity_savings_products` | `AnnuitySavingsProduct` | 상품 기본정보 (연금 특화) |
| `annuity_savings_options` | `AnnuitySavingsOption` | 연금수령 조건별 옵션 |

#### 상품 고유 필드

| 필드 | 설명 | 예시 |
|------|------|------|
| `pnsn_kind` / `pnsn_kind_nm` | 연금종류 | 연금저축보험, 연금저축펀드 |
| `prdt_type` / `prdt_type_nm` | 상품유형 | 주식형, 채권형, 혼합형 |
| `avg_prft_rate` | 평균수익률 (%) | 12.53 |
| `dcls_rate` | 공시이율 (%) | 2.50 |
| `guar_rate` | 최저보증이율 (%) | 1.00 |

#### 옵션 구조 (다른 상품과 완전히 다름)

| 필드 | 설명 | 예시 |
|------|------|------|
| `pnsn_recp_trm_nm` | 연금수령기간 | 10년 확정, 20년 확정 |
| `pnsn_entr_age_nm` | 가입나이 | 30세, 40세 |
| `mon_paym_atm_nm` | 월납입금 | 100,000원 |
| `paym_prd_nm` | 납입기간 | 10년, 20년 |
| `pnsn_strt_age_nm` | 연금개시나이 | 55세, 60세 |
| `pnsn_recp_amt` | 연금수령액 (원) | 201,304 |

#### 대량 페이지 처리

금융투자 권역에서 최대 60페이지(297건)가 발생한다. `_fetch_all_pages()` 루프로 처리.

#### 구현 파일

| 파일 | 내용 |
|------|------|
| `backend/app/services/fetchers/annuity_savings_fetcher.py` | `FssAnnuitySavingsFetcher` |
| `backend/app/services/real_data_loader.py` | `load_annuity_savings_products()` |
| `backend/app/routes/admin.py` | `POST /admin/load-annuity-savings` |

---

### 4. 주택담보대출 (Mortgage Loan)

**API**: `mortgageLoanProductsSearch.json`

#### DB 모델

| 테이블 | 모델 클래스 | 설명 |
|--------|------------|------|
| `mortgage_loan_products` | `MortgageLoanProduct` | 상품 기본정보 (대출 특화) |
| `mortgage_loan_options` | `MortgageLoanOption` | 담보유형/상환방식/금리유형별 옵션 |

#### 상품 고유 필드 (대출 공통)

| 필드 | 설명 |
|------|------|
| `loan_inci_expn` | 대출 부대비용 |
| `erly_rpay_fee` | 중도상환 수수료 |
| `dly_rate` | 연체이율 |
| `loan_lmt` | 대출한도 |

#### 옵션 구조

| 필드 | 설명 | 예시 |
|------|------|------|
| `mrtg_type` / `mrtg_type_nm` | 담보유형 | A(아파트), E(아파트외) |
| `rpay_type` / `rpay_type_nm` | 상환방식 | D(분할상환) |
| `lend_rate_type` / `lend_rate_type_nm` | 금리유형 | F(고정), C(변동) |
| `lend_rate_min` | 최저금리 (%) | 3.41 |
| `lend_rate_max` | 최고금리 (%) | 5.62 |
| `lend_rate_avg` | 평균금리 (%) | 4.29 |

#### 구현 파일

| 파일 | 내용 |
|------|------|
| `backend/app/services/fetchers/mortgage_loan_fetcher.py` | `FssMortgageLoanFetcher` |
| `backend/app/services/real_data_loader.py` | `load_mortgage_loan_products()` |
| `backend/app/routes/admin.py` | `POST /admin/load-mortgage-loans` |

---

### 5. 전세자금대출 (Rent House Loan)

**API**: `rentHouseLoanProductsSearch.json`

#### DB 모델

| 테이블 | 모델 클래스 | 설명 |
|--------|------------|------|
| `rent_house_loan_products` | `RentHouseLoanProduct` | 상품 기본정보 |
| `rent_house_loan_options` | `RentHouseLoanOption` | 상환방식/금리유형별 옵션 |

#### 옵션 구조 (주담대와 유사하나 mrtg_type 없음)

| 필드 | 설명 | 예시 |
|------|------|------|
| `rpay_type` / `rpay_type_nm` | 상환방식 | S(만기일시), D(분할) |
| `lend_rate_type` / `lend_rate_type_nm` | 금리유형 | F(고정), C(변동) |
| `lend_rate_min` / `lend_rate_max` / `lend_rate_avg` | 금리 범위 | 4.25 ~ 4.35 |

#### 구현 파일

| 파일 | 내용 |
|------|------|
| `backend/app/services/fetchers/rent_house_loan_fetcher.py` | `FssRentHouseLoanFetcher` |
| `backend/app/services/real_data_loader.py` | `load_rent_house_loan_products()` |
| `backend/app/routes/admin.py` | `POST /admin/load-rent-house-loans` |

---

### 6. 개인신용대출 (Credit Loan)

**API**: `creditLoanProductsSearch.json`

#### DB 모델

| 테이블 | 모델 클래스 | 설명 |
|--------|------------|------|
| `credit_loan_products` | `CreditLoanProduct` | 상품 기본정보 (신용대출 특화) |
| `credit_loan_options` | `CreditLoanOption` | 신용등급별/금리유형별 옵션 |

#### 상품 고유 필드

| 필드 | 설명 | 값 |
|------|------|----|
| `crdt_prdt_type` | 상품유형코드 | 1(일반신용), 2(마이너스한도), 3(장기카드대출) |
| `crdt_prdt_type_nm` | 상품유형명 | 일반신용대출, 마이너스한도대출, 장기카드대출(카드론) |
| `cb_name` | CB 기관명 | KCB, NICE, NICE/KCB |

#### 옵션 구조 (다른 상품과 완전히 다른 구조)

기간별 금리가 아닌 **신용등급별 금리**를 제공한다.

| 필드 | 설명 | 예시 |
|------|------|------|
| `crdt_lend_rate_type` | 금리유형 | A(대출금리), B(기준금리), C(가산금리), D(가감조정) |
| `crdt_grad_1` | 1등급 금리 | 5.19 |
| `crdt_grad_4` | 4등급 금리 | 6.01 |
| `crdt_grad_5` | 5등급 금리 | 6.68 |
| `crdt_grad_6` | 6등급 금리 | 7.45 |
| `crdt_grad_10` | 10등급 금리 | 7.97 |
| `crdt_grad_11` | 11등급 금리 | 10.18 |
| `crdt_grad_12` | 12등급 금리 | 11.87 |
| `crdt_grad_13` | 13등급 금리 | 11.67 |
| `crdt_grad_avg` | 평균 금리 | 5.81 |

> 금리 관계: A(대출금리) = B(기준금리) + C(가산금리) + D(가감조정금리)

#### 구현 파일

| 파일 | 내용 |
|------|------|
| `backend/app/services/fetchers/credit_loan_fetcher.py` | `FssCreditLoanFetcher` |
| `backend/app/services/real_data_loader.py` | `load_credit_loan_products()` |
| `backend/app/routes/admin.py` | `POST /admin/load-credit-loans` |

---

## 전체 파일 변경 목록

### Backend

| 파일 | 변경 내용 |
|------|----------|
| `app/models/securities.py` | 12개 모델 추가 (상품 6 + 옵션 6) |
| `app/services/fetchers/base_fetcher.py` | DataType enum 6종 추가 |
| `app/services/batch_manager.py` | BatchType enum 6종 추가 |
| `app/services/fetchers/deposit_fetcher.py` | 신규: `FssDepositFetcher` |
| `app/services/fetchers/savings_fetcher.py` | 신규: `FssSavingsFetcher` |
| `app/services/fetchers/annuity_savings_fetcher.py` | 신규: `FssAnnuitySavingsFetcher` |
| `app/services/fetchers/mortgage_loan_fetcher.py` | 신규: `FssMortgageLoanFetcher` |
| `app/services/fetchers/rent_house_loan_fetcher.py` | 신규: `FssRentHouseLoanFetcher` |
| `app/services/fetchers/credit_loan_fetcher.py` | 신규: `FssCreditLoanFetcher` |
| `app/services/real_data_loader.py` | 6개 loader 메서드 추가 |
| `app/routes/admin.py` | 6개 POST 엔드포인트 + data-status 확장 |

### Frontend

| 파일 | 변경 내용 |
|------|----------|
| `src/services/api.js` | 6개 API 함수 추가 |
| `src/components/ProgressModal.jsx` | Phase 배지 숨김 조건 확장 |
| `src/pages/DataManagementPage.jsx` | 6개 적재 카드 + 6개 스코어 카드 추가 |

---

## API 엔드포인트 목록

| HTTP Method | Path | 설명 | Task ID Prefix |
|-------------|------|------|----------------|
| `POST` | `/admin/load-deposits` | 정기예금 적재 | `deposits_` |
| `POST` | `/admin/load-savings` | 적금 적재 | `savings_` |
| `POST` | `/admin/load-annuity-savings` | 연금저축 적재 | `annuity_` |
| `POST` | `/admin/load-mortgage-loans` | 주택담보대출 적재 | `mortgage_` |
| `POST` | `/admin/load-rent-house-loans` | 전세자금대출 적재 | `rentloan_` |
| `POST` | `/admin/load-credit-loans` | 개인신용대출 적재 | `creditloan_` |
| `GET` | `/admin/data-status` | 전체 데이터 현황 | - |

---

## DB 테이블 목록

| 테이블명 | Unique Key | 옵션 테이블 | 옵션 Unique Key |
|----------|-----------|------------|----------------|
| `deposit_products` | `(fin_co_no, fin_prdt_cd)` | `deposit_rate_options` | `(product_id, save_trm, intr_rate_type)` |
| `savings_products` | `(fin_co_no, fin_prdt_cd)` | `savings_rate_options` | `(product_id, save_trm, intr_rate_type, rsrv_type)` |
| `annuity_savings_products` | `(fin_co_no, fin_prdt_cd)` | `annuity_savings_options` | index only |
| `mortgage_loan_products` | `(fin_co_no, fin_prdt_cd)` | `mortgage_loan_options` | `(product_id, mrtg_type, rpay_type, lend_rate_type)` |
| `rent_house_loan_products` | `(fin_co_no, fin_prdt_cd)` | `rent_house_loan_options` | `(product_id, rpay_type, lend_rate_type)` |
| `credit_loan_products` | `(fin_co_no, fin_prdt_cd)` | `credit_loan_options` | `(product_id, crdt_lend_rate_type)` |

---

## Frontend UI

### 데이터 현황 스코어 카드

| 아이콘 | 레이블 | data-status 필드 |
|--------|--------|-----------------|
| 🏦 | 예금 | `deposits` |
| 💰 | 적금 | `savings` |
| 🏛️ | 연금저축 | `annuity_savings` |
| 🏠 | 주담대 | `mortgage_loans` |
| 🏠 | 전세대출 | `rent_house_loans` |
| 💳 | 신용대출 | `credit_loans` |

### ProgressModal Phase 배지 숨김

아래 task_id prefix에 해당하는 작업은 단일 단계이므로 Phase 1/2 배지를 숨긴다.

```javascript
const isBondTask = taskId && (
  taskId.startsWith('bonds_') ||
  taskId.startsWith('deposits_') ||
  taskId.startsWith('savings_') ||
  taskId.startsWith('annuity_') ||
  taskId.startsWith('mortgage_') ||
  taskId.startsWith('rentloan_') ||
  taskId.startsWith('creditloan_')
);
```

---

## 주의사항

1. **FSS_API_KEY**: `.env` 파일에 반드시 설정해야 한다. 미설정 시 Fetcher 초기화에서 `FetcherError` 발생.
2. **권역별 데이터 없음**: 금융투자(060000) 권역은 대부분 API에서 0건을 반환한다 (연금저축 제외).
3. **다중 페이지**: 적금(저축은행 3p), 연금저축(금융투자 60p)에서 다중 페이지가 발생한다.
4. **신용등급 NULL**: 개인신용대출의 `crdt_grad_10`~`crdt_grad_13`은 비은행 권역에서 대부분 NULL이다.
5. **compound unique key**: 모든 상품은 `(fin_co_no, fin_prdt_cd)` 복합 키로 식별한다. 동일 금융사의 동일 상품코드가 다른 권역에서 중복 등장하지 않는다.
6. **옵션 갱신 전략**: 재적재 시 기존 옵션을 DELETE 후 재 INSERT한다. 옵션 구성이 변경되더라도 정확한 데이터를 보장한다.
