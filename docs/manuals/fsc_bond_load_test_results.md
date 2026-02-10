# FSC API 채권 실데이터 적재 테스트 결과

**작성일:** 2026-02-05
**관련 문서:** `bonds_consolidation_impl.md` (통합 구현), `table_consolidation_design.md` (설계)
**대상 DB:** PostgreSQL `kingo.public`
**적재 경로:** FSC OpenAPI → `load_bond_basic_info()` → `_upsert_bond()` → `bonds` 테이블

---

## 1. 적재 파라미터

| 파라미터 | 값 | 비고 |
|----------|-----|------|
| `bas_dt` | 20260201 | 20260205(오늘)은 API에서 0건 반환 → 직전 평일 사용 |
| `limit` | 10 | 초기 테스트용 건수 제한 |
| `as_of_date` | 2026-02-01 | batch 기준일 |
| `operator_reason` | FSC 채권 10건 적재 | |

> **참고:** `bas_dt=20260205`로 첫 시도 시 API 응답 건수 0건. `bas_dt=20260201`로 변경 후 정상 반환.

---

## 2. Batch 결과

| 항목 | 값 |
|------|-----|
| `batch_id` | 32 |
| `batch_type` | BOND_INFO |
| `source_id` | FSC_BOND_INFO |
| `status` | SUCCESS |
| `total_records` | 10 |
| `success_records` | 10 |
| `failed_records` | 0 |
| `skipped_records` | 0 |
| `started_at` | 2026-02-05 11:08:48 |
| `completed_at` | 2026-02-05 11:08:48 |

---

## 3. 적재된 10건 세부

### 3.1 종목별 구성

| 발행인 | 건수 | scrs_itms_kcd | kis 코드 | credit_rating |
|--------|------|---------------|----------|---------------|
| 멀리건제오차 | 1건 | 1106 (사모회사채) | (blank) | None |
| 마젠타로보틱스 | 2건 | 1108 (CB) | (blank) | None |
| 메인텍 | 1건 | 1108 (PCBO) | (blank) | None |
| 삼성카드 | 6건 | 1105 (공모회사채) | 121 | None |

### 3.2 건별 상세

| id | name | isin_cd | bond_type | rate(%) | mat | issu_amt (원) | bal (원) | kis | lstg_dt |
|----|------|---------|-----------|---------|-----|---------------|----------|-----|---------|
| 37 | 멀리건제오차 2-2(사모) | KR6416782EA3 | corporate | 3.8235 | 1yr | 241,000,000 | 241,000,000 | — | — |
| 38 | 마젠타로보틱스 1CB(전환) | KR6416991D25 | corporate | 7.0 | 3yr | 299,970,000 | 282,975,000 | — | — |
| 39 | 마젠타로보틱스 3CB(전환) | KR6416991D82 | corporate | 7.0 | 3yr | 611,200,000 | 611,200,000 | — | — |
| 40 | 메인텍2(PCBO사모/콜) | KR6280341F95 | corporate | 4.553 | 3yr | 2,000,000,000 | 2,000,000,000 | — | — |
| 41 | 삼성카드 2645 | KR6029782DB2 | corporate | 4.793 | 4yr | 110,000,000,000 | 110,000,000,000 | 121 | 2023-11-13 |
| 42 | 삼성카드 2650 | KR6029782DC0 | corporate | 4.043 | 3yr | 40,000,000,000 | 40,000,000,000 | 121 | 2023-12-11 |
| 43 | 삼성카드 2653 | KR6029782E36 | corporate | 3.877 | 3yr | 90,000,000,000 | 90,000,000,000 | 121 | 2024-03-07 |
| 44 | 삼성카드 2655 | KR6029782E44 | corporate | 3.709 | 3yr | 90,000,000,000 | 90,000,000,000 | 121 | 2024-04-16 |
| 45 | 삼성카드 2659(녹) | KR6029782E51 | corporate | 3.873 | 3yr | 100,000,000,000 | 100,000,000,000 | 121 | 2024-05-10 |
| 46 | 삼성카드 2670 | KR6029782E69 | corporate | 3.731 | 3yr | 110,000,000,000 | 110,000,000,000 | 121 | 2024-06-11 |

### 3.3 공통 유도 컬럼 (10건 전체 동일)

| 컬럼 | 값 | 근거 |
|------|----|------|
| `bond_type` | corporate | scrs_itms_kcd 첫 글자 "1" |
| `credit_rating` | None | 코드맵에 해당 코드 없음 (아래 관찰 사항 참조) |
| `risk_level` | medium | credit_rating = None → medium |
| `investment_type` | moderate,aggressive | credit_rating = None → moderate,aggressive |
| `is_active` | true | 기본값 |
| `source_id` | FSC_BOND_INFO | |
| `batch_id` | 32 | |

---

## 4. 관찰 사항

### 4.1 삼성카드 신용등급 코드 "121" 미매핑

삼성카드 6건 모두 `kis_scrs_itms_kcd = '121'`을 반환하지만, 현재 `_CREDIT_CODE_MAP`에는 정확한 100 단위 코드만 정의되어 있습니다:

```python
_CREDIT_CODE_MAP = {
    "100": "AAA", "110": "AA", "120": "A",
    "130": "BBB", "140": "BB", "150": "B", "160": "CCC",
}
```

"121"은 "A+" 등급으로 추정됩니다 (120=A, 130=BBB 사이). 현재 정확히 매핑되지 않아 `credit_rating = None`으로 처리됨.

**영향:** 삼성카드 6건이 `risk_level=medium`/`investment_type=moderate,aggressive`로 분류됨. A+ 등급이면 `risk_level=low`/`corporate`가 더 정확한 분류임.

**후속 작업:** `_map_credit_rating()`에 접두사 매핑 로직 추가 필요 (120–129 범위 → "A", 110–119 → "AA" 등).

### 4.2 마젠타로보틱스 잔액 차이

| 종목 | 발행금액 | 잔액 | 차이 |
|------|---------|------|------|
| 마젠타로보틱스 1CB(전환) | 299,970,000 | 282,975,000 | -16,995,000 (부분 전환 후 잔액) |
| 마젠타로보틱스 3CB(전환) | 611,200,000 | 611,200,000 | 0 |

→ CB(전환사채)의 부분 전환으로 인한 잔액 감소. 정상 데이터.

### 4.3 ID 시퀀스 간격

적재된 행의 ID가 37–46입니다. 기존 5건(id 1–5)과 사이에 간격이 있는 이유는 통합 테스트 단계에서 INSERT/DELETE 테스트를 수행한 후 PostgreSQL SERIAL 시퀀스가 되돌리지 않기 때문입니다. 기능적 영향 없음.

---

## 5. 검증

### 5.1 bonds 테이블 행 수

| 구간 | 행 수 | 세부 |
|------|-------|------|
| 적재 전 | 5건 | bond_basic_info 마이그레이션 분 |
| 적재 후 | 15건 | +10건 (batch_id=32) |

### 5.2 bond_basic_info 오염 검증

적재 전후 `bond_basic_info` 테이블 행 수 **5건 → 5건**. 변경 없음. 기존 테이블은 백업용으로 유지되며 `_upsert_bond()`는 `bonds` 테이블에만 작용.

### 5.3 portfolio_engine 회귀 검증

`investment_type LIKE '%<filter>%' AND is_active = true` 패턴으로 15건 기준 조회:

| 필터 | 반환 건수 | 구성 |
|------|-----------|------|
| conservative | 4건 | AA MBS 4건 (id 2–5) |
| moderate | 15건 | 전체 (기존 5건 + 신규 10건 모두 포함) |
| aggressive | 15건 | 전체 |

`portfolio_engine._select_bonds()` 기존 쿼리 패턴 변경 없이 정상 동작.

### 5.4 upsert 경로 확인

10건 모두 신규 `isin_cd`이므로 **INSERT 경로**를 통과했습니다. `last_updated` 값이 적재 시각(2026-02-05 11:08:48)으로 설정되어 있어 INSERT 시도 후 즉시 갱신됨을 확인.

---

## 6. 후속 작업

| 항목 | 우선순위 | 비고 |
|------|----------|------|
| `_CREDIT_CODE_MAP` 접두사 매핑 (121→A+, 111→AA+ 등) | 높음 | 삼성카드 6건 분류 정확성 영향 |
| `bond_basic_info` 테이블 DROP | 낮음 | Phase C 예정, 현재 백업용 유지 |
| `data_loader.py` 수동 시드 3건 deprecation | 중간 | 실데이터 충분히 적재되면 불필요 |
| stocks 테이블 통합 (stock_info/fdr_stock_listing) | 높음 | 동일 패턴, 설계 문서 참조 |
