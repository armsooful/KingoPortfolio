# Foresto Phase 2 – Epic B(리밸런싱 엔진) 상세 설계
최초작성일자: 2026-01-16
최종수정일자: 2026-01-18

**문서명**: Foresto_Phase2_EpicB_리밸런싱엔진_상세설계  
**작성일**: 2026-01-16  
**버전**: 1.0.0  
**상태**: Draft (구현 착수용)  

---

## 0. 전제(Phase 1 의존성)

Phase 1에서 이미 존재/사용 중인 요소를 “변경”하지 않고 “확장”만 한다.

- 데이터 입력: `daily_price`, `daily_return`(표준 테이블)
- 결과 저장: `simulation_run`, `simulation_path`, `simulation_summary`
- 캐시: `요청해시(request_hash)` 기반 재사용(동일 입력이면 동일 결과)
- Feature Flag(Phase 1): `USE_SIM_STORE`, `USE_SCENARIO_DB`

Phase 2에서 추가:
- Feature Flag: `USE_REBALANCING` (기본 OFF)

---

## 1. 목적과 범위

### 1.1 목적
시나리오/포트폴리오 기반 시뮬레이션 경로 계산 과정에 **리밸런싱 규칙**을 적용하여,
- 리밸런싱 ON/OFF 비교
- 주기/임계치(Drift) 변화에 따른 비교
- “언제 왜 리밸런싱이 발생했는지” 설명 가능한 로그 제공

을 가능하게 한다.

### 1.2 범위(In-Scope)
- 정기 리밸런싱: Monthly / Quarterly
- Drift 리밸런싱: 목표비중 대비 편차(absolute deviation) 임계치 초과 시
- 비용 가정 모델: 단일 고정 모델(Phase 2 한정)로 NAV 반영
- 이벤트 로그 저장: 리밸런싱 발생 시점/사유/전후비중/비용

### 1.3 제외(Out-of-Scope)
- 실시간 주문/체결/슬리피지/시장충격 모델
- 개별 종목 단위 리밸런싱(자산군 단위만)
- 자동 실행/스케줄러에 의한 실제 운용
- 개인 성향 기반 추천/자동 판단

---

## 2. 개념 정의

### 2.1 용어
- **Target Weights**: 목표 자산 배분 비중(합 1.0)
- **Current Weights**: 특정 일자의 평가금액 기준 비중(합 1.0)
- **Drift**: `|CurrentWeight_i - TargetWeight_i|`
- **Rebalance Action**: 목표비중으로 “재조정”하는 행위(가정상 즉시/완전 체결)

### 2.2 리밸런싱 트리거
- PERIODIC:
  - 월간: 매월 첫 거래일(or 월말, 아래 정책 참조)
  - 분기: 1/4/7/10월 첫 거래일(or 분기말)
- DRIFT:
  - 어떤 자산군이라도 Drift가 `threshold` 이상이면 발생

---

## 3. 입력/출력 및 데이터 흐름

### 3.1 입력
- `scenario_id` 또는 `portfolio_model_id`
- `start_date`, `end_date`
- `initial_nav` (기본 1.0)
- `rebalancing_rule` (없으면 OFF로 처리)
- `cost_model` 파라미터(기본값 제공)

### 3.2 출력
- `simulation_path`: 일자별 NAV 및(옵션) 자산군별 평가금액
- `simulation_summary`: KPI(Phase 2에서 분석 계층과 연동)
- `rebalancing_event`: 발생일/사유/전후비중/비용

### 3.3 데이터 흐름(개요)
```
(1) 입력 수집/정규화
(2) 거래일 캘린더 구성 (price 존재일 기준)
(3) 일자 루프:
    - 수익률 반영 → 평가금액 업데이트
    - 트리거 체크(PERIODIC/DRIFT)
    - 발생 시:
        - before_weights 산출
        - 목표비중으로 재조정(after_weights)
        - 비용 반영(NAV 감소 또는 평가금액 차감)
        - event 저장
(4) path/summary 저장
(5) request_hash 동일 시 캐시 재사용
```

---

## 4. 날짜/거래일 정책(중요)

### 4.1 거래일 정의
- `daily_price` 또는 `daily_return`가 존재하는 날짜만 거래일로 간주
- 일부 자산군 데이터가 결측인 날짜는:
  - 기본 정책: 해당 날짜는 **전체 포트폴리오 계산에서 제외**(스킵) 또는
  - 대안 정책: 결측 자산군은 0수익률로 가정
- Phase 2 기본값(권장): **스킵**(데이터 품질 우선)

> NOTE: 이 정책은 request_hash에 포함되어야 한다(재현성).

### 4.2 PERIODIC 리밸런싱 기준일
두 방식 중 하나를 선택해야 한다(시스템 전역 설정).

- **옵션 A: 월초(첫 거래일) 리밸런싱**
  - 장점: 직관적(운용 관행)
  - 단점: 전월 성과 반영 후 조정 타이밍이 월초로 고정
- **옵션 B: 월말(마지막 거래일) 리밸런싱**
  - 장점: 월 단위 성과를 마감하며 리밸런싱
  - 단점: 월말 거래일 탐색 필요

Phase 2 기본값: **월초/분기초(첫 거래일)**

---

## 5. 리밸런싱 엔진 설계

### 5.1 모듈 구조(권장)
- `backend/app/services/rebalancing_engine.py`
  - `RebalancingEngine.apply(...)`
  - 트리거 판정 + 재조정 + 비용 반영
- `backend/app/services/scenario_simulation.py`
  - 일자 루프에서 `rebalancing_engine` 호출(Feature Flag ON일 때만)

### 5.2 핵심 데이터 구조(런타임)
- `positions_value: Dict[asset_class, float]`
- `target_weights: Dict[asset_class, float]`
- `current_weights: Dict[asset_class, float]`

### 5.3 리밸런싱 계산(재조정)
리밸런싱 발생 시점에 포트폴리오 총액 `V = sum(positions_value)` 에 대해,
각 자산군 평가금액을 다음으로 재설정:
- `new_value_i = V * target_weight_i`

> “즉시/완전 체결” 가정이며, 슬리피지/호가/체결지연은 제외.

---

## 6. Drift 판정 로직

### 6.1 Drift 정의
- `drift_i = abs(current_weight_i - target_weight_i)`

### 6.2 트리거 조건
- `max(drift_i) >= drift_threshold` 이면 리밸런싱 실행

### 6.3 Drift 계산 시점
- **수익률 반영 후**(EOD 기준) drift 계산
- drift 트리거가 발생하면 **동일 일자에 리밸런싱** 적용

> 이 순서도 request_hash에 포함되어야 한다.

---

## 7. 비용 모델(Phase 2 기본)

### 7.1 목적
리밸런싱을 “공짜”로 두지 않기 위한 최소 비용 가정.

### 7.2 기본 모델(단일)
- 거래비용 = `turnover * cost_rate`
- turnover = `0.5 * sum(|after_value_i - before_value_i|) / V`
  - (매수/매도 중복을 고려한 표준적 단순화)
- cost_rate 기본값: `0.001` (10bp)  ※ 시스템 설정으로 관리

### 7.3 비용 반영 방식
- 비용을 현금(단기금융)에서 우선 차감
- 현금 비중이 없거나 부족하면:
  - 전체 포트폴리오에 비례 차감(= NAV를 곱으로 감소)

Phase 2 기본값: **NAV 곱 감소 방식**(단순, 재현성 우수)
- `V_after_cost = V * (1 - turnover * cost_rate)`
- 이후 `after_value_i = V_after_cost * target_weight_i`

---

## 8. 저장/로그 설계(연동 관점)

### 8.1 `rebalancing_event` 저장(신규)
리밸런싱 발생 시 아래를 저장:
- `simulation_run_id`
- `event_date`
- `trigger_type` (PERIODIC/DRIFT)
- `trigger_detail` (예: "MONTHLY", "DRIFT>=0.05")
- `before_weights` (JSON)
- `after_weights` (JSON)
- `turnover`
- `cost_rate`
- `cost_amount` (또는 cost_factor)

### 8.2 `simulation_path` 확장(선택)
- 최소: NAV만 있어도 가능
- 권장: 자산군별 평가금액(또는 비중)을 컬럼/JSON으로 저장
  - Phase 1 파티셔닝 정책을 훼손하지 않도록 “확장 컬럼”은 신중히
  - 안전한 접근: 별도 테이블 `simulation_path_asset` 신설(Phase 2 또는 Phase 3)

Phase 2 기본: **`rebalancing_event`만 확실히 도입**, path는 기존 구조 유지(리스크 최소화)

---

## 9. Request Hash(캐시) 확장 규칙

리밸런싱 관련 파라미터는 모두 request_hash에 포함되어야 한다.

포함 대상:
- rebalancing_rule_id (또는 rule json)
- periodic 기준(월초/월말)
- drift_threshold
- cost_model, cost_rate
- drift 계산 순서(EOD 기준 등)
- 결측 데이터 처리 정책(스킵/0수익률)

---

## 10. 알고리즘(의사코드)

```pseudo
init positions_value by target_weights * initial_nav

for date in trading_dates:
    # 1) apply daily returns
    for asset in assets:
        r = daily_return[asset, date]
        positions_value[asset] *= (1 + r)

    # 2) decide trigger
    trigger = None
    if rule.type == PERIODIC and is_periodic_rebalance_day(date):
        trigger = ("PERIODIC", freq)
    elif rule.type == DRIFT:
        current_weights = normalize(positions_value)
        if max_abs_diff(current_weights, target_weights) >= threshold:
            trigger = ("DRIFT", threshold)

    # 3) rebalance if triggered
    if trigger:
        before_w = normalize(positions_value)
        V = sum(positions_value)

        # compute turnover and cost
        after_values_no_cost = {a: V * target_w[a] for a in assets}
        turnover = 0.5 * sum(|after_values_no_cost[a] - positions_value[a]|) / V
        cost_factor = 1 - turnover * cost_rate
        V2 = V * cost_factor
        positions_value = {a: V2 * target_w[a] for a in assets}

        after_w = normalize(positions_value)
        store_rebalancing_event(run_id, date, trigger, before_w, after_w, turnover, cost_rate, cost_factor)

    # 4) store path
    nav = sum(positions_value)
    store_simulation_path(run_id, date, nav)
```

---

## 11. 엣지 케이스/정책

- 목표비중 합 ≠ 1.0:
  - 입력 단계에서 normalize 또는 reject
  - Phase 2 기본: **reject(400) + 오류 메시지**
- 자산군 중 일부 일자 수익률 결측:
  - Phase 2 기본: **그 날짜 스킵**
- drift_threshold = 0:
  - 매일 리밸런싱(과도) → 입력 검증으로 최소값 강제(예: >= 0.001)
- cost_rate 과도:
  - 상한(예: <= 0.02) 설정
- 음수 NAV:
  - 정상 수익률 기반에서는 발생하지 않음. 발생 시 중단/에러 기록.

---

## 12. API 연동(최소 변경)

### 12.1 기존 API 유지
- `POST /api/v1/backtest/scenario` 요청 body 확장(선택)
  - `rebalancing_rule_id` 또는 `rebalancing: { ... }`

### 12.2 응답 확장
- `rebalancing_enabled`
- `rebalancing_events_count`
- (선택) 이벤트 조회 API 추가:
  - `GET /api/v1/backtest/scenario/{run_id}/rebalancing-events`

> Phase 2 기본: 이벤트 조회 API는 추가하는 것을 권장(운영/디버깅 효율).

---

## 13. Feature Flag 동작

- `USE_REBALANCING=0`:
  - 기존 Phase 1 시뮬레이션 로직 그대로
  - rule 파라미터가 와도 무시(또는 400, 선택)
- `USE_REBALANCING=1`:
  - rebalancing_rule이 존재할 때만 적용
  - rule이 없으면 OFF와 동일

Phase 2 기본 정책:
- flag OFF 상태에서 rule 파라미터가 오면 **400**(명시적 통제)
- flag ON 상태에서만 rule 허용

---

## 14. 테스트 계획(DoD 포함)

### 14.1 단위 테스트
- PERIODIC 월간:
  - 월초 리밸런싱 날짜 정확성
  - ON/OFF 결과 상이(특정 케이스에서)
- DRIFT:
  - 임계치 미만 → 이벤트 0
  - 임계치 이상 → 이벤트 >= 1
- 비용:
  - turnover 계산 검증
  - cost 적용 후 NAV 감소 확인

### 14.2 통합 테스트(스모크)
- 시나리오 3종(MIN_VOL/DEFENSIVE/GROWTH)에 대해
  - 리밸런싱 OFF 실행 성공
  - 리밸런싱 ON 실행 성공
  - 이벤트 로그 조회 성공(0 이상)
- request_hash 재사용
  - 동일 입력 재실행 → run 재사용(또는 결과 동일) 확인

### 14.3 성능
- 파티션 존재/미존재 테스트
- 3년/5년 구간 실행시간 측정(기준치 수립)

---

## 15. Epic B Definition of Done

- [ ] PERIODIC 월간/분기 리밸런싱 구현 및 테스트 통과
- [ ] DRIFT 리밸런싱 구현 및 테스트 통과
- [ ] 비용 모델 적용 및 NAV 반영 검증
- [ ] `rebalancing_event` 저장(발생일/사유/전후비중/비용)
- [ ] request_hash에 리밸런싱 파라미터 포함
- [ ] `USE_REBALANCING` OFF 시 Phase 1과 결과/동작 동일
- [ ] 기존 테스트 100% 통과 유지

---

## 16. 구현 우선순위(권장)

1) `rebalancing_rule` + `rebalancing_event` DDL  
2) PERIODIC 월간 → 분기(확장)  
3) DRIFT  
4) 비용 모델  
5) 이벤트 조회 API + 품질 리포트(quality_report 연동)

---
