# C-3 DDL 설계 (성과 분석)
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

## 개요
- 대상: 성과 분석 고도화 (Performance Analytics)
- 성과 타입: LIVE / SIM / BACK
- 목적: 성과 결과, 산출 근거, 벤치마크 비교, 사용자 노출 요약 저장
- 기준 SQL: `docs/phase3/c3_ddl_schema.sql`

---

## 1. performance_result
성과 결과(불변).

### 주요 컬럼
- `performance_id` (PK, UUID)
- `performance_type` (LIVE/SIM/BACK)
- `entity_type` (PORTFOLIO/ACCOUNT/ASSET_CLASS)
- `entity_id`
- `period_type` (DAILY/MONTHLY/CUMULATIVE)
- `period_start`, `period_end`
- 지표: `period_return`, `cumulative_return`, `annualized_return`, `volatility`, `mdd`, `sharpe_ratio`, `sortino_ratio`
- 재현성: `execution_id`, `snapshot_ids`, `result_version_id`, `calc_params`
- `created_at`

### 참조/제약
- `execution_id` → `batch_execution.execution_id`
- `result_version_id` → `result_version.version_id`
- `snapshot_ids`는 JSONB 배열

### 인덱스
- `idx_performance_entity (entity_type, entity_id)`
- `idx_performance_type (performance_type, period_type)`
- `idx_performance_period (period_start, period_end)`

---

## 2. performance_basis
성과 산출 근거(가격 기준, 비용 반영 여부 등).

### 주요 컬럼
- `basis_id` (PK, UUID)
- `performance_id` (FK)
- `price_basis` (CLOSE/LAST_VALID)
- `include_fee`, `include_tax`, `include_dividend`
- `fx_snapshot_id` (환율 스냅샷)
- `notes`
- `created_at`

### 참조/제약
- `performance_id` → `performance_result.performance_id` (ON DELETE CASCADE)
- `fx_snapshot_id` → `data_snapshot.snapshot_id`

### 인덱스
- `idx_performance_basis_perf (performance_id)`

---

## 3. benchmark_result
벤치마크 비교 결과.

### 주요 컬럼
- `benchmark_id` (PK, UUID)
- `performance_id` (FK)
- `benchmark_type` (INDEX/MIX/CASH)
- `benchmark_code`
- `benchmark_return`, `excess_return`
- `created_at`

### 참조/제약
- `performance_id` → `performance_result.performance_id` (ON DELETE CASCADE)

### 인덱스
- `idx_benchmark_perf (performance_id)`

---

## 4. performance_public_view
사용자 노출용 요약(LIVE 전용).

### 주요 컬럼
- `public_id` (PK, UUID)
- `performance_id` (FK)
- `headline_json` (요약 문구/포맷)
- `disclaimer_text`
- `created_at`

### 참조/제약
- `performance_id` → `performance_result.performance_id` (ON DELETE CASCADE)

---

## 참고
- 성과 결과는 불변 저장(immutable).
- 재계산 시 신규 `performance_result` + `result_version` 연계.
