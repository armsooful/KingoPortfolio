# Epic 3: 로그·감사·재처리 최종 검증 보고서

작성일: 2026-01-23

---

## 1. 검증 개요

### 1.1 검증 범위
- Story 3.1: 필수 로그 검증
- Story 3.2: 재처리(Replay) 검증

### 1.2 검증 대상 파일

| 파일 | 역할 |
|------|------|
| `app/models/phase7_evaluation.py` | 평가 이력 모델 정의 |
| `app/services/phase7_evaluation.py` | 평가 로직 및 해시 생성 |
| `app/routes/phase7_evaluation.py` | API 엔드포인트 및 로깅 |
| `tests/e2e/test_phase9_audit_log.py` | 감사 로그 E2E 테스트 |
| `tests/e2e/test_phase9_reproducibility.py` | 재현성 E2E 테스트 |

---

## 2. Story 3.1: 필수 로그 검증

### 2.1 Task 3.1.1: 입력 스냅샷 해시 로깅

| 항목 | 결과 |
|------|------|
| 구현 위치 | `phase7_evaluation.py:90-91` |
| 해시 알고리즘 | SHA-256 |
| 저장 필드 | `Phase7EvaluationRun.result_hash` (VARCHAR 64) |
| 상태 | ✅ PASS |

**구현 코드:**
```python
def hash_result(serialized_result: str) -> str:
    return hashlib.sha256(serialized_result.encode("utf-8")).hexdigest()
```

**E2E 테스트:** `TestTC6_1_EvaluationAuditLog.test_evaluation_records_result_hash`

---

### 2.2 Task 3.1.2: 평가 버전 로깅

| 항목 | 결과 |
|------|------|
| 구현 위치 | `phase7_evaluation.py:72` |
| 버전 필드 | `disclaimer_version: "v2"` |
| 저장 위치 | `result_json` 내부 |
| 상태 | ✅ PASS |

**구현 코드:**
```python
result = {
    ...
    "disclaimer_version": "v2",
}
```

**E2E 테스트:** `TestTC6_DataIntegrity.test_stored_result_matches_api_response`

---

### 2.3 Task 3.1.3: 결과 요약 로깅

| 항목 | 결과 |
|------|------|
| 저장 필드 | `Phase7EvaluationRun.result_json` (TEXT) |
| 포함 내용 | period, metrics, disclaimer_version, extensions |
| 형식 | JSON 직렬화 |
| 상태 | ✅ PASS |

**저장되는 metrics:**
- `cumulative_return`: 누적 수익률
- `cagr`: 연평균 수익률
- `volatility`: 변동성
- `max_drawdown`: 최대 낙폭

**E2E 테스트:** `TestTC6_1_EvaluationAuditLog.test_evaluation_stores_complete_result`

---

### 2.4 Task 3.1.4: 사용자 액션 이벤트 로깅

| 항목 | 결과 |
|------|------|
| 사용자 ID | `owner_user_id` (FK → users.id) |
| 타임스탬프 | `created_at` (DATETIME, UTC) |
| 포트폴리오 ID | `portfolio_id` (FK) |
| 기간 정보 | `period_start`, `period_end` |
| 상태 | ✅ PASS |

**DB 스키마:**
```sql
CREATE TABLE phase7_evaluation_run (
    evaluation_id INTEGER PRIMARY KEY,
    portfolio_id INTEGER NOT NULL,
    owner_user_id VARCHAR(36) NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    rebalance VARCHAR(20) NOT NULL,
    result_json TEXT NOT NULL,
    result_hash VARCHAR(64) NOT NULL,
    created_at DATETIME NOT NULL
);
```

**E2E 테스트:**
- `TestTC6_2_UserActionEvents.test_portfolio_creation_tracked`
- `TestTC6_2_UserActionEvents.test_evaluation_history_tracked`
- `TestTC6_2_UserActionEvents.test_evaluation_timestamp_recorded`

---

## 3. Story 3.2: 재처리(Replay) 검증

### 3.1 Task 3.2.1: 동일 입력 재처리 시 결과 불변성

| 항목 | 결과 |
|------|------|
| 테스트 케이스 | TC-5.1, TC-5.3 |
| 검증 방법 | 동일 입력 5회 반복 실행 후 결과 비교 |
| 상태 | ✅ PASS |

**검증 항목:**
- 동일 입력 → 동일 `metrics` 값
- 동일 입력 → 동일 `result_hash`
- 여러 번 재처리해도 결과 일관성 유지

**E2E 테스트:**
- `TestTC5_1_SameInputSameResult.test_identical_results_for_same_input`
- `TestTC5_1_SameInputSameResult.test_result_hash_consistency`
- `TestTC5_3_ReplayResultImmutability.test_replay_produces_same_result`
- `TestTC5_3_ReplayResultImmutability.test_multiple_replays_consistent`

---

### 3.2 Task 3.2.2: 버전 변경 시 결과 분리 저장

| 항목 | 결과 |
|------|------|
| 현재 버전 | `disclaimer_version: "v2"` |
| 저장 방식 | 각 평가마다 별도 레코드 생성 |
| 버전 추적 | `result_json` 내 `disclaimer_version` 포함 |
| 상태 | ✅ PASS |

**동작 방식:**
- 평가 실행마다 새로운 `Phase7EvaluationRun` 레코드 생성
- 각 레코드에 평가 시점의 버전 정보 포함
- 버전 변경 시에도 기존 이력 불변 (이력 수정 없음)

---

## 4. E2E 테스트 결과 요약

### 4.1 감사 로그 테스트 (`test_phase9_audit_log.py`)

| 테스트 클래스 | 테스트 수 | 결과 |
|--------------|----------|------|
| TestTC6_1_EvaluationAuditLog | 3 | ✅ PASS |
| TestTC6_2_UserActionEvents | 3 | ✅ PASS |
| TestTC6_QueryAuditTrail | 2 | ✅ PASS |
| TestTC6_DataIntegrity | 1 | ✅ PASS |
| **합계** | **9** | **✅ ALL PASS** |

### 4.2 재현성 테스트 (`test_phase9_reproducibility.py`)

| 테스트 클래스 | 테스트 수 | 결과 |
|--------------|----------|------|
| TestTC5_1_SameInputSameResult | 2 | ✅ PASS |
| TestTC5_2_StoredResultImmutability | 2 | ✅ PASS |
| TestTC5_3_ReplayResultImmutability | 2 | ✅ PASS |
| TestTC5_DifferentInputDifferentResult | 2 | ✅ PASS |
| TestTC5_HashAlgorithmConsistency | 1 | ✅ PASS |
| **합계** | **9** | **✅ ALL PASS** |

---

## 5. 로깅 아키텍처 요약

```
┌─────────────────────────────────────────────────────────────┐
│                    API Request                               │
│  POST /api/v1/phase7/evaluations                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                phase7_evaluation.py                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ evaluate_phase7_portfolio()                          │    │
│  │ - 입력 검증                                          │    │
│  │ - NAV 시리즈 계산                                    │    │
│  │ - metrics 산출                                       │    │
│  │ - disclaimer_version 포함                            │    │
│  └─────────────────────────────────────────────────────┘    │
│                       │                                      │
│                       ▼                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ serialize_result() → hash_result()                   │    │
│  │ - JSON 직렬화                                        │    │
│  │ - SHA-256 해시 생성                                  │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Phase7EvaluationRun (DB)                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ evaluation_id    │ PRIMARY KEY                       │    │
│  │ portfolio_id     │ FK → phase7_portfolio             │    │
│  │ owner_user_id    │ FK → users (사용자 추적)          │    │
│  │ period_start     │ DATE (입력 기간)                  │    │
│  │ period_end       │ DATE (입력 기간)                  │    │
│  │ rebalance        │ VARCHAR (리밸런싱 옵션)           │    │
│  │ result_json      │ TEXT (전체 결과 + 버전)           │    │
│  │ result_hash      │ VARCHAR(64) (SHA-256)             │    │
│  │ created_at       │ DATETIME (타임스탬프)             │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. 결론

### 6.1 Story 3.1: 필수 로그 검증
- **상태: ✅ PASS**
- 모든 필수 로그 항목이 구현되어 있음
- E2E 테스트로 검증 완료

### 6.2 Story 3.2: 재처리 검증
- **상태: ✅ PASS**
- 동일 입력 재처리 시 결과 불변성 검증 완료
- 버전 정보가 각 레코드에 포함되어 추적 가능

### 6.3 Epic 3 최종 결과
- **상태: ✅ 완료**

---

## 7. 버전 이력

| 버전 | 일자 | 변경 내용 |
|------|------|-----------|
| v1.0 | 2026-01-23 | 최초 작성 |
