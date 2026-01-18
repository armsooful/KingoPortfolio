# Foresto Phase 2 – Epic B 실행 패키지
최초작성일자: 2026-01-16
최종수정일자: 2026-01-18

**구성**: (2) Seed SQL + (3) 리밸런싱 엔진 구현 작업 티켓  
**작성일**: 2026-01-16  
**버전**: 1.0.0  
**상태**: Ready  

---

## 0. 전제 및 원칙
- Phase 1 테이블/동작 **무변경**
- `USE_REBALANCING` Feature Flag **기본 OFF**
- Flag OFF 상태에서 리밸런싱 파라미터 유입 시 **400 반환(명시적 통제)** 권장
- 리밸런싱은 **자산군 단위**(주식/채권/단기/금/기타 등)로만 처리
- 비용 모델은 Phase 2 범위에서 **고정 cost_rate**만 사용

---

# Part A) Seed SQL

## A-1. Seed SQL 파일
### 파일명(권장)
- `Foresto_Phase2_EpicB_Rebalancing_Seed.sql`

### 실행 순서
1) DDL 적용 완료(이미 완료)
2) 아래 Seed SQL 실행
3) API/배치에서 rule_id 참조하여 테스트

---

## A-2. Seed SQL 본문

```sql
-- =====================================================================
-- File: Foresto_Phase2_EpicB_Rebalancing_Seed.sql
-- Purpose:
--   Phase 2 Epic B rebalancing_rule 초기 데이터(seed)
-- Notes:
--   - 기존 데이터가 있을 수 있으므로, rule_name 기준 UPSERT로 처리
--   - 운영에서는 effective_from/to, is_active 정책에 맞게 조정
-- =====================================================================

BEGIN;
SET search_path TO foresto;

-- 1) PERIODIC / MONTHLY / 월초(첫 거래일) / 10bp
INSERT INTO rebalancing_rule (
    rule_name, rule_type, frequency, base_day_policy,
    drift_threshold, cost_rate, effective_from, effective_to, is_active
)
VALUES (
    'P2_PERIODIC_MONTHLY_FTD_10BP', 'PERIODIC', 'MONTHLY', 'FIRST_TRADING_DAY',
    NULL, 0.001, CURRENT_DATE, NULL, TRUE
)
ON CONFLICT (rule_name) DO UPDATE SET
    rule_type = EXCLUDED.rule_type,
    frequency = EXCLUDED.frequency,
    base_day_policy = EXCLUDED.base_day_policy,
    drift_threshold = EXCLUDED.drift_threshold,
    cost_rate = EXCLUDED.cost_rate,
    effective_from = EXCLUDED.effective_from,
    effective_to = EXCLUDED.effective_to,
    is_active = EXCLUDED.is_active,
    updated_at = CURRENT_TIMESTAMP;

-- 2) PERIODIC / QUARTERLY / 월초(첫 거래일) / 10bp
INSERT INTO rebalancing_rule (
    rule_name, rule_type, frequency, base_day_policy,
    drift_threshold, cost_rate, effective_from, effective_to, is_active
)
VALUES (
    'P2_PERIODIC_QUARTERLY_FTD_10BP', 'PERIODIC', 'QUARTERLY', 'FIRST_TRADING_DAY',
    NULL, 0.001, CURRENT_DATE, NULL, TRUE
)
ON CONFLICT (rule_name) DO UPDATE SET
    rule_type = EXCLUDED.rule_type,
    frequency = EXCLUDED.frequency,
    base_day_policy = EXCLUDED.base_day_policy,
    drift_threshold = EXCLUDED.drift_threshold,
    cost_rate = EXCLUDED.cost_rate,
    effective_from = EXCLUDED.effective_from,
    effective_to = EXCLUDED.effective_to,
    is_active = EXCLUDED.is_active,
    updated_at = CURRENT_TIMESTAMP;

-- 3) DRIFT / threshold=5% / 10bp
INSERT INTO rebalancing_rule (
    rule_name, rule_type, frequency, base_day_policy,
    drift_threshold, cost_rate, effective_from, effective_to, is_active
)
VALUES (
    'P2_DRIFT_5PCT_10BP', 'DRIFT', NULL, 'FIRST_TRADING_DAY',
    0.05, 0.001, CURRENT_DATE, NULL, TRUE
)
ON CONFLICT (rule_name) DO UPDATE SET
    rule_type = EXCLUDED.rule_type,
    frequency = EXCLUDED.frequency,
    base_day_policy = EXCLUDED.base_day_policy,
    drift_threshold = EXCLUDED.drift_threshold,
    cost_rate = EXCLUDED.cost_rate,
    effective_from = EXCLUDED.effective_from,
    effective_to = EXCLUDED.effective_to,
    is_active = EXCLUDED.is_active,
    updated_at = CURRENT_TIMESTAMP;

COMMIT;

-- 확인:
-- SELECT rule_id, rule_name, rule_type, frequency, drift_threshold, cost_rate, is_active
--   FROM foresto.rebalancing_rule
--  ORDER BY rule_id;
```

### ⚠️ 주의(DDL 보완 필요 여부)
위 Seed SQL은 `ON CONFLICT (rule_name)`을 사용하므로,
**`rebalancing_rule.rule_name`에 UNIQUE 제약이 필요**하다.

- 만약 현재 DDL에 UNIQUE가 없다면 아래 중 하나를 택한다:
  1) **권장**: UNIQUE 인덱스 추가
     ```sql
     CREATE UNIQUE INDEX IF NOT EXISTS ux_rebalancing_rule_name
         ON foresto.rebalancing_rule(rule_name);
     ```
  2) (대안) ON CONFLICT 제거하고 INSERT-only로 운영

---

# Part B) 엔진 구현 작업 티켓 (JIRA 스타일)

## Epic B 목표
- 리밸런싱 규칙(PERIODIC/DRIFT)을 시뮬레이션 경로 계산에 적용
- 발생 이벤트를 `rebalancing_event`에 저장
- Flag OFF 시 Phase 1과 **동일 동작/동일 결과** 보장

---

## B-0. 공통 DoD (모든 티켓 공통)
- [ ] `USE_REBALANCING=0`에서 기존 테스트 100% 통과
- [ ] 신규 테스트는 Phase 2로 분리
- [ ] request_hash에 리밸런싱 파라미터 포함
- [ ] 실패/예외는 명확한 에러 코드 + 메시지 반환(400/500 구분)

---

## P2-B1 (DB) Seed 적용을 위한 UNIQUE 제약 추가
**타입**: Task / DB  
**우선순위**: P0  
**설명**: Seed SQL의 UPSERT를 위해 `rule_name` UNIQUE 보장

**작업**
- [ ] `ux_rebalancing_rule_name` UNIQUE 인덱스 추가
- [ ] 마이그레이션 스크립트/DDL 반영

**DoD**
- [ ] 동일 rule_name으로 Seed 재실행 시 중복 없이 update 수행

---

## P2-B2 (Service) RebalancingEngine 스켈레톤 추가
**타입**: Story / Backend  
**우선순위**: P0  
**대상 파일**
- [ ] `backend/app/services/rebalancing_engine.py` (신규)

**요구사항**
- [ ] 입력: positions_value, target_weights, date, rule, cost_rate 등
- [ ] 출력: (updated positions_value, optional event payload)
- [ ] 순수 함수 성격(테스트 용이), DB 저장은 상위 레이어에서 수행 가능하도록 분리

**DoD**
- [ ] 최소 더미 구현 + 단위 테스트 뼈대 추가

---

## P2-B3 (Logic) PERIODIC 월간 리밸런싱 구현
**타입**: Story  
**우선순위**: P0  
**요구사항**
- [ ] base_day_policy=FIRST_TRADING_DAY 기준, 월간 리밸런싱 트리거 판정
- [ ] 월간 리밸런싱 발생 시 목표 비중으로 재조정
- [ ] turnover/cost 적용(Phase2 고정 모델)

**테스트**
- [ ] 특정 기간에서 월별 1회 발생 확인
- [ ] ON/OFF 결과 차이 검증(적어도 1개 케이스)

**DoD**
- [ ] `rebalancing_event`가 월별로 생성됨

---

## P2-B4 (Logic) PERIODIC 분기 리밸런싱 구현
**타입**: Story  
**우선순위**: P1  
**요구사항**
- [ ] 1/4/7/10월 첫 거래일 기준 트리거 판정
- [ ] 로직은 월간과 동일 프레임 사용(중복 최소화)

**DoD**
- [ ] 분기 기준 이벤트 발생 검증

---

## P2-B5 (Logic) DRIFT 리밸런싱 구현
**타입**: Story  
**우선순위**: P1  
**요구사항**
- [ ] EOD 수익률 반영 후 현재 비중 산출
- [ ] max(|cw - tw|) >= threshold 시 트리거
- [ ] 비용 적용 포함

**테스트**
- [ ] threshold 미만 케이스: 이벤트 0
- [ ] threshold 초과 케이스: 이벤트 >= 1

**DoD**
- [ ] drift 조건에 따라 이벤트가 재현 가능하게 발생

---

## P2-B6 (Integration) scenario_simulation에 Feature Flag 게이트 연결
**타입**: Story  
**우선순위**: P0  
**대상 파일**
- [ ] `backend/app/services/scenario_simulation.py`

**요구사항**
- [ ] `USE_REBALANCING=0`이면 리밸런싱 로직 미호출
- [ ] `USE_REBALANCING=1` + rule 존재 시에만 적용
- [ ] Flag OFF인데 rule 파라미터가 오면 400(명시적 통제)

**DoD**
- [ ] 기존 Phase 1 시뮬레이션 결과가 완전히 동일(회귀 테스트)

---

## P2-B7 (Persistence) rebalancing_event 저장 로직 추가
**타입**: Task  
**우선순위**: P0  
**요구사항**
- [ ] 리밸런싱 발생 시 `rebalancing_event` INSERT
- [ ] before/after weights JSON schema 통일(자산군 키 표준화)
- [ ] simulation_run_id FK 연결

**DoD**
- [ ] 시뮬레이션 1회 실행에 대해 이벤트 조회 가능

---

## P2-B8 (Hash) request_hash 구성 항목 확장
**타입**: Task  
**우선순위**: P0  
**요구사항**
- [ ] hash input에 포함:
  - rule_id 또는 rule 파라미터(rule_type, frequency/base_day_policy, drift_threshold)
  - cost_rate
  - 결측 처리 정책(스킵/0수익률) 및 drift 계산 순서(EOD)
- [ ] 동일 입력 → 동일 hash → 결과 재사용

**DoD**
- [ ] 파라미터 변경 시 hash가 달라짐
- [ ] 동일 파라미터 재실행 시 run 재사용(또는 결과 동일)

---

## P2-B9 (API) backtest 요청에 rebalancing_rule_id 지원
**타입**: Story / API  
**우선순위**: P1  
**요구사항**
- [ ] `POST /api/v1/backtest/scenario` body에 `rebalancing_rule_id` 추가
- [ ] Flag OFF 시 400
- [ ] rule_id 유효성 검사(존재/active/effective 기간)

**DoD**
- [ ] API로 ON/OFF 시뮬레이션 실행 가능

---

## P2-B10 (API) 리밸런싱 이벤트 조회 API 추가(권장)
**타입**: Story / API  
**우선순위**: P2  
**요구사항**
- [ ] `GET /api/v1/backtest/scenario/{run_id}/rebalancing-events`
- [ ] 정렬: event_date asc
- [ ] 출력: event_date, trigger_type, trigger_detail, turnover, cost_rate, before/after weights

**DoD**
- [ ] 운영/디버깅을 위해 이벤트 확인 가능

---

## P2-B11 (Ops) quality_report 리밸런싱 스모크 추가
**타입**: Task / Ops  
**우선순위**: P2  
**요구사항**
- [ ] 리밸런싱 OFF 실행 + ON 실행 스모크 케이스 추가
- [ ] 이벤트 건수 출력

**DoD**
- [ ] quality_report에서 리밸런싱 관련 항목 확인 가능

---

# 1차 스프린트 권장 범위(최소 가동)
- P2-B1, P2-B2, P2-B3, P2-B6, P2-B7, P2-B8
- (선택) P2-B9

---

## 부록: 구현 체크포인트(리스크)
- JSON 키 표준(자산군 코드) 통일 안 하면 비교/분석이 깨짐
- 결측 데이터 정책(스킵/0수익률)은 hash에 반드시 포함
- PERIODIC 기준일(월초/월말)도 hash에 포함

---
