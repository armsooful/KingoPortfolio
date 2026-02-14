# bonds ← bond_basic_info 통합 구현 및 테스트 결과

**작성일:** 2026-02-05
**관련 설계 문서:** `docs/manuals/table_consolidation_design.md` (Phase A)
**대상 DB:** PostgreSQL `kingo.public`

---

## 1. 변경 파일 목록

| 파일 | 변경 종류 | 요약 |
|------|-----------|------|
| `app/models/securities.py` | 수정 | Bond 클래스에 27개 컬럼 추가 + `__table_args__` |
| `app/models/real_data.py` | 수정 | BondBasicInfo 클래스 제거 (NOTE 주석으로 대체) |
| `app/models/__init__.py` | 수정 | BondBasicInfo 임포트 및 `__all__` 제거 |
| `app/services/real_data_loader.py` | 수정 | `_insert_bond_basic_info` → `_upsert_bond` 교체, 매핑 로직 추가 |
| PostgreSQL DDL | 실행 | ALTER TABLE bonds: 27컬럼 + 3인덱스 |
| 마이그레이션 스크립트 | 실행 | bond_basic_info 5건 → bonds 이동 |

---

## 2. 세부 변경 내용

### 2.1 `models/securities.py` — Bond 클래스

**임포트 추가:**
```python
from sqlalchemy import ..., Numeric, ForeignKey, UniqueConstraint, Index
```

**추가된 컬럼 (27개, 모두 nullable):**

| 그룹 | 컬럼 | 타입 | 설명 |
|------|------|------|------|
| 식별 | `isin_cd` | String(12) | ISIN 코드 (unique) |
| 식별 | `bas_dt` | String(8) | API 조회 기준일 |
| 식별 | `crno` | String(13) | 법인등록번호 |
| 종목 | `scrs_itms_kcd` | String(4) | 유가증권종목종류코드 |
| 종목 | `scrs_itms_kcd_nm` | String(100) | 유가증권종목종류코드명 |
| 발행 | `bond_issu_dt` | Date | 발행일 |
| 발행 | `bond_expr_dt` | Date | 만기일 |
| 금액 | `bond_issu_amt` | Numeric(22,3) | 발행금액 |
| 금액 | `bond_bal` | Numeric(22,3) | 잔액 |
| 금리세부 | `irt_chng_dcd` | String(1) | 금리변동구분 Y/N |
| 금리세부 | `bond_int_tcd` | String(1) | 이자유형코드 |
| 금리세부 | `int_pay_cycl_ctt` | String(100) | 이자지급주기 |
| 이표 | `nxtm_copn_dt` | Date | 차기이표일 |
| 이표 | `rbf_copn_dt` | Date | 직전이표일 |
| 보증/순위 | `grn_dcd` | String(1) | 보증구분코드 |
| 보증/순위 | `bond_rnkn_dcd` | String(1) | 순위구분코드 |
| 신용등급코드 | `kis_scrs_itms_kcd` | String(4) | KIS 등급 코드 |
| 신용등급코드 | `kbp_scrs_itms_kcd` | String(4) | KBP 등급 코드 |
| 신용등급코드 | `nice_scrs_itms_kcd` | String(4) | NICE 등급 코드 |
| 신용등급코드 | `fn_scrs_itms_kcd` | String(4) | FN 등급 코드 |
| 모집/상장 | `bond_offr_mcd` | String(2) | 모집방법코드 |
| 모집/상장 | `lstg_dt` | Date | 상장일 |
| 특이 | `prmnc_bond_yn` | String(1) | 영구채권여부 |
| 특이 | `strips_psbl_yn` | String(1) | 스트립스가능여부 |
| 거버넌스 | `source_id` | String(20) FK→data_source | 마지막 갱신 소스 |
| 거버넌스 | `batch_id` | Integer FK→data_load_batch | 마지막 갱신 배치 |
| 거버넌스 | `as_of_date` | Date | 데이터 기준일 |

**추가된 `__table_args__`:**
```python
__table_args__ = (
    UniqueConstraint('isin_cd', name='uq_bond_isin'),   # NULL 허용, 중복 NULL OK
    Index('idx_bond_isin', 'isin_cd'),
    Index('idx_bond_expr_dt', 'bond_expr_dt'),
)
```

### 2.2 `services/real_data_loader.py` — 핵심 로직 변경

**모듈 상수 추가:**
```python
_CREDIT_CODE_MAP = {
    "100": "AAA", "110": "AA", "120": "A",
    "130": "BBB", "140": "BB", "150": "B", "160": "CCC",
}
```

**추가된 정적 메서드:**

- `_map_credit_rating(record)` — KIS > KBP > NICE > FN 우선 순서로 코드 조회, `_CREDIT_CODE_MAP`으로 텍스트 변환
- `_derive_bond_fields(record)` — 실데이터 레코드에서 교육용 컬럼 유도 (아래 매핑 규칙)

**교체된 메서드:**

| 기존 | 변경 후 | 차이점 |
|------|---------|--------|
| `_insert_bond_basic_info()` | `_upsert_bond()` | INSERT-only → INSERT+UPDATE (isin_cd 기준) |

`_upsert_bond` 동작:
1. `isin_cd`로 기존 행 조회
2. 존재하면 → 교육용 컬럼 + 실데이터 컬럼 UPDATE, `last_updated` 갱신
3. 없으면 → 새 행 INSERT (name = isin_cd_nm)

`load_bond_basic_info()` 루프 내 호출 변경:
```python
# 기존: self._insert_bond_basic_info(record=..., ...)
# 변경: self._upsert_bond(record=..., ...)
```

### 2.3 DDL (PostgreSQL)

```sql
-- 27개 컬럼 추가 (ALTER TABLE ... ADD COLUMN IF NOT EXISTS)
-- 인덱스 3개
CREATE UNIQUE INDEX IF NOT EXISTS uq_bond_isin ON bonds(isin_cd) WHERE isin_cd IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_bond_isin ON bonds(isin_cd);
CREATE INDEX IF NOT EXISTS idx_bond_expr_dt ON bonds(bond_expr_dt);
```

통합 후 bonds 테이블: **컬럼 42개**, 기존 15개 + 추가 27개.

---

## 3. 매핑 규칙

### 3.1 신용등급 코드 → 텍스트

FSC API는 숫자 코드를 반환합니다. 실제 적재 데이터에서 확인된 코드:

| 코드 | 등급 | 실제 출현 종목 |
|------|------|----------------|
| 100 | AAA | — |
| 110 | AA | 한국주택금융공사 MBS (4건) |
| 120 | A | — |
| 130 | BBB | — |
| 140 | BB | — |
| (blank) | None | 제이스텍 CB (등급 미부여) |

### 3.2 bond_type 결정

`scrs_itms_kcd` 첫 글자로 판별:

| 첫 글자 | 종류 | bond_type | 실제 출현 |
|---------|------|-----------|-----------|
| 2 | 국채 | government | — |
| 3 | 특수채/MBS | government | 한국주택금융공사 MBS (kcd=3201) |
| 4 | 지방정부채 | government | — |
| 1 | 회사채/CB | corporate 또는 high_yield | 제이스텍 CB (kcd=1108) |

회사채(1xxx) 내 `high_yield` 판별: credit_rating ∈ {BBB, BB, B, CCC, CC, C, D}

> **참고:** BBB를 high_yield로 분류하는 것은 기존 교육용 시드 패턴("하이일드 채권 펀드": BBB등급)과의 일치를 위함. 실금융 기준(BBB = investment grade)과는 다름.

### 3.3 risk_level + investment_type 유도

| credit_rating | risk_level | investment_type | 기존 시드 대응 |
|---------------|------------|-----------------|----------------|
| AAA, AA | low | conservative,moderate,aggressive | 국고채 3년물 |
| A | low | conservative,moderate | 회사채(A등급) 펀드 |
| BBB | high | aggressive | 하이일드 채권 펀드 |
| BB, B, CCC… | high | aggressive | — |
| None (등급 미부여) | medium | moderate,aggressive | — |

### 3.4 interest_rate + maturity_years

- `interest_rate` = `bond_srfc_inrt` (백분율 기준, 직접 사용. 예: 1.81 = 1.81%)
- `maturity_years` = `round((bond_expr_dt - bond_issu_dt).days / 365)`, 최소 1년

---

## 4. 마이그레이션 결과

`bond_basic_info` 5건을 `bonds`로 이동:

| id | name | bond_type | credit_rating | risk_level | investment_type | rate | mat | isin |
|----|------|-----------|---------------|------------|-----------------|------|-----|------|
| 1 | 제이스텍1CB(사모/전환/풋) | corporate | — | medium | moderate,aggressive | 0.0 | 5yr | KR6090471B78 |
| 2 | 한국주택금융공사 MBS2019-18… | government | AA | low | conservative,moderate,aggressive | 1.81 | 7yr | KR354410G992 |
| 3 | 한국주택금융공사MBS2020-30… | government | AA | low | conservative,moderate,aggressive | 1.743 | 10yr | KR354410GA91 |
| 4 | 한국주택금융공사 MBS2020-36… | government | AA | low | conservative,moderate,aggressive | 1.847 | 10yr | KR354410GAB6 |
| 5 | 한국주택금융공사 MBS2021-15… | government | AA | low | conservative,moderate,aggressive | 2.435 | 30yr | KR354410GB74 |

`bond_basic_info` 테이블은 백업용으로 유지 중 (5행, 변경 없음).

---

## 5. 테스트 결과

### 5.1 UPDATE 경로 테스트

기존 isin_cd `KR354410G992`에 갱신된 값으로 `_upsert_bond` 호출:

| 검증 항목 | 기존 값 | 갱신 후 값 | 결과 |
|-----------|---------|------------|------|
| bond_bal | 200000000000.000 | 12345678.999 | OK |
| last_updated | None | 2026-02-05 11:01:44 | OK |
| bas_dt | (기존) | 20260205 | OK |
| crno | (기존) | 1234567890123 | OK |
| bonds 행 수 | 5 | 5 (변화 없음) | OK |
| bond_basic_info 행 수 | 5 | 5 (오염 없음) | OK |

테스트 후 원본 값 복원됨.

### 5.2 INSERT 경로 테스트 — A등급 회사채

새 isin_cd `KR123456789A`로 INSERT:

| 컬럼 | 기대값 | 실제값 | 결과 |
|------|--------|--------|------|
| bond_type | corporate | corporate | OK |
| credit_rating | A | A | OK |
| risk_level | low | low | OK |
| investment_type | conservative,moderate | conservative,moderate | OK |
| interest_rate | 3.75 | 3.75 | OK |
| maturity_years | 3 | 3 | OK |
| kis_scrs_itms_kcd | 120 | 120 | OK |

테스트 후 삭제됨.

### 5.3 INSERT 경로 테스트 — BBB 등급 (high_yield)

새 isin_cd `KR999888777C`로 INSERT:

| 컬럼 | 기대값 | 실제값 | 결과 |
|------|--------|--------|------|
| bond_type | high_yield | high_yield | OK |
| credit_rating | BBB | BBB | OK |
| risk_level | high | high | OK |
| investment_type | aggressive | aggressive | OK |
| interest_rate | 7.2 | 7.2 | OK |
| maturity_years | 5 | 5 | OK |
| irt_chng_dcd | Y (변동금리) | Y | OK |

> **수정 사항:** 초기 구현에서 BBB가 `corporate`로 분류되었음. `_derive_bond_fields`의 high_yield 판별 조건에 "BBB"를 추가하여 수정.

테스트 후 삭제됨.

### 5.4 매핑 로직 단위 테스트

`_derive_bond_fields` 직접 호출로 6가지 케이스 검증 (DB 접속 없이):

| 케이스 | bond_type | credit_rating | risk_level | investment_type | 결과 |
|--------|-----------|---------------|------------|-----------------|------|
| AAA 국채 (kcd=2011) | government | AAA | low | conservative,moderate,aggressive | OK |
| AA MBS (kcd=3201) | government | AA | low | conservative,moderate,aggressive | OK |
| A 회사채 (kcd=1108) | corporate | A | low | conservative,moderate | OK |
| BBB 하이일드 (kcd=1108) | high_yield | BBB | high | aggressive | OK |
| BB 하이일드 (kcd=1108) | high_yield | BB | high | aggressive | OK |
| 등급 없음 (kcd=1108) | corporate | None | medium | moderate,aggressive | OK |

### 5.5 portfolio_engine 패턴 회귀 검증

통합된 bonds 테이블에서 `investment_type.contains()` + `is_active == True` 쿼리:

| 필터 | 반환 건수 | 정상 여부 |
|------|-----------|-----------|
| conservative | 4건 (AA MBS 4건) | OK |
| moderate | 5건 (전체) | OK |
| aggressive | 5건 (전체) | OK |

`portfolio_engine._select_bonds()` 기존 쿼리 패턴 변경 없이 정상 동작.

---

## 6. 남은 작업

| 항목 | 우선순위 | 비고 |
|------|----------|------|
| `bond_basic_info` 테이블 DROP | 낮음 | 백업용으로 유지 중, Phase C에서 제거 |
| `data_loader.py` 수동 시드 3건 deprecation | 중간 | bonds에 실데이터 충분히 적재되면 불필요 |
| stocks 테이블과 stock_info/fdr_stock_listing 동일 패턴 통합 | 높음 | 설계 문서 참조 |
| FSC API 타임아웃 처리 개선 | 중간 | 테스트 중 apis.data.go.kr 30s timeout 발생 |
