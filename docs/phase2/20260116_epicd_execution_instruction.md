# Foresto Phase 2 – Epic D 수행 지시서
최초작성일자: 2026-01-16
최종수정일자: 2026-01-18

**문서명**: Foresto_Phase2_EpicD_수행지시서  
**작성일**: 2026-01-16  
**대상**: 백엔드 개발자 / 데이터 엔지니어  
**상태**: Epic D DDL 완료 이후 즉시 수행용  

---

## 1. 목적

본 지시서는 **Epic D(성과 분석 계층)** 구현을 위해  
이미 완료된 DDL(`analysis_result`)을 기준으로  
개발자가 수행해야 할 작업을 **순서·범위·완료 기준(DoD)**까지 명확히 지시하는 문서이다.

본 Epic은:
- 투자 판단/추천을 하지 않으며
- 시뮬레이션 결과에 대한 **정량적 해석과 비교**만 제공한다.

---

## 2. 현재 전제 상태 (반드시 확인)

아래 항목이 모두 충족되어야 본 지시서의 작업을 수행한다.

- [x] Phase 1 전체 완료
- [x] Phase 2 Epic B(리밸런싱 엔진) 완료
- [x] Epic D DDL (`analysis_result`) 적용 완료
- [x] Phase 1 테스트 전부 통과 상태

---

## 3. 수행 범위 요약

Epic D 구현은 다음 4단계로 진행한다.

```
1단계. KPI 계산 엔진 구현 (필수)
2단계. 분석 결과 저장/재사용 로직 (필수)
3단계. KPI 조회 API 연결 (필수)
4단계. 리밸런싱 정보 결합 + 품질 검증 (권장)
```

---

## 4. 1단계 – KPI 계산 엔진 구현 (필수)

### 4.1 작업 목표
`simulation_run_id`를 입력받아,
- 시뮬레이션 경로(NAV 시계열) 기반 KPI를 계산하는 **순수 계산 모듈**을 구현한다.

### 4.2 대상 파일
- `backend/app/services/performance_analyzer.py` (신규)

### 4.3 구현 내용
아래 지표를 **정확한 수학 정의**에 따라 구현한다.

- CAGR
- Volatility (연율화)
- Sharpe Ratio (단순, rf=0 기본)
- Maximum Drawdown(MDD)
  - MDD 값
  - peak_date
  - trough_date

### 4.4 구현 규칙
- NAV → 일간 수익률은 **항상 재계산**
- 거래일 수 = `simulation_path`에 존재하는 날짜 기준
- 변동성 0일 경우 Sharpe는 **NULL**
- 부동소수점 오차는 round(1e-8) 또는 NUMERIC 사용

### 4.5 완료 기준 (DoD)
- [x] 단순 NAV 케이스에서 손계산 결과와 일치
- [x] 변동성 0 → Sharpe NULL
- [x] 단위 테스트 최소 3케이스 통과 (27개 테스트 구현)

---

## 5. 2단계 – 분석 결과 저장/재사용 로직 (필수)

### 5.1 작업 목표
KPI 계산 결과를 `analysis_result` 테이블에 저장하여
**동일 요청 시 재계산 없이 재사용**한다.

### 5.2 대상
- ORM 모델: `analysis_result`
- Service/Store 레이어 추가

### 5.3 구현 내용
- 조회 키:
  - `(simulation_run_id, rf_annual, annualization_factor)`
- 처리 흐름:
  1. 기존 row 존재 → 즉시 반환
  2. 미존재 → KPI 계산 → INSERT → 반환

### 5.4 완료 기준 (DoD)
- [x] 동일 파라미터 재호출 시 재계산 없음 (cache_hit 반환)
- [x] 파라미터 변경 시 신규 row 생성 (unique index 적용)
- [x] FK(CASCADE) 정상 동작 (ondelete="CASCADE" 설정)

---

## 6. 3단계 – KPI 조회 API 연결 (필수)

### 6.1 작업 목표
Epic D의 분석 결과를 외부에서 조회 가능하도록 API를 제공한다.

### 6.2 엔드포인트
```
GET /api/v1/analysis/run/{run_id}
```

### 6.3 요청 파라미터
- `rf_annual` (optional, default 0.0)
- `annualization_factor` (optional, default 252)

### 6.4 응답 포함 항목
- KPI 전체(metrics_json)
- 분석 가정(rf, 연율화)
- 기간 정보(period_start, period_end)

❗ **금지**
- “추천”, “유리”, “최적” 등 판단적 표현

### 6.5 완료 기준 (DoD)
- [x] 정상 run_id에 대해 KPI 조회 가능 (GET /backtest/analysis/run/{run_id})
- [x] 잘못된 run_id → 404 (ValueError → HTTPException 404)
- [x] 동일 요청 재호출 시 동일 결과 (캐시 로직 적용)

---

## 7. 4단계 – 리밸런싱 정보 결합 및 품질 검증 (권장)

### 7.1 결합 대상
`rebalancing_event` 테이블

### 7.2 포함할 요약 정보
- rebalancing_events_count
- total_turnover
- estimated_cost (sum)

### 7.3 완료 기준 (DoD)
- [x] KPI 응답에 리밸런싱 요약 포함 (get_analysis_with_rebalancing)
- [x] ON/OFF 시 KPI 차이 확인 가능 (compare_runs API)

---

## 8. 품질 및 회귀 테스트 (필수)

### 8.1 회귀 테스트
- Phase 1 테스트 전부 통과
- Epic B 리밸런싱 결과 영향 없음

### 8.2 quality_report 연동 (권장)
- KPI 계산 스모크 테스트 추가
- 리밸런싱 ON/OFF KPI 출력

---

## 9. Epic D 완료 판정 기준

아래 항목이 모두 충족되면 Epic D는 **DONE**으로 판정한다.

- [x] KPI 계산 정확성 검증 완료 (CAGR, Volatility, Sharpe, MDD)
- [x] analysis_result 캐시 정상 동작 (unique index + cache_hit 로직)
- [x] KPI 조회 API 제공 (GET /backtest/analysis/run/{run_id})
- [x] 리밸런싱 요약 결합 (get_rebalancing_summary 함수)
- [x] 추천/자동 판단 요소 0% (note 필드에 면책 문구만 포함)
- [x] Phase 1~2 기존 기능 무영향 (기존 API 변경 없음)

**Epic D 상태: DONE** (2026-01-16 완료)

---

## 10. 산출물 목록

- `performance_analyzer.py`
- `analysis_result` ORM / Store
- KPI 조회 API
- 단위 테스트 코드
- (선택) quality_report 확장

---

**본 지시서는 Epic D 구현의 공식 기준 문서로 사용한다.**
