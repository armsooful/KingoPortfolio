# Foresto Phase 2 – Epic D 실행 패키지
**구성**: Epic D DDL + 성과 분석 구현 작업 티켓  
**작성일**: 2026-01-16  
**버전**: 1.0.0  
**상태**: Ready for Implementation  

---

## 0. 범위 요약

Epic D는 **성과 해석/비교 계층**으로, 투자 판단이나 추천을 수행하지 않는다.  
입력은 이미 확정된 `simulation_run_id`이며, 결과는 **설명 가능한 지표(KPI)**만 제공한다.

---

# Part A) Epic D DDL

## A-1. 설계 원칙
- Phase 1 테이블 변경 금지
- 성과 분석 결과는 캐시 성격 → 별도 테이블 저장
- 동일 run + 동일 가정(rf, 연율화) → 동일 결과 재사용

---

## A-2. DDL 파일

### 파일명(권장)
`Foresto_Phase2_EpicD_Analysis_DDL.sql`

```sql
-- =====================================================================
-- File: Foresto_Phase2_EpicD_Analysis_DDL.sql
-- Purpose:
--   Phase 2 Epic D 성과 분석 결과 저장용 테이블
-- =====================================================================

BEGIN;
SET search_path TO foresto;

-- --------------------------------------------------
-- analysis_result
-- --------------------------------------------------
-- 시뮬레이션 실행(run_id) 기준 KPI 결과 캐시
-- --------------------------------------------------

CREATE TABLE IF NOT EXISTS analysis_result (
    analysis_id             BIGSERIAL PRIMARY KEY,

    simulation_run_id       BIGINT NOT NULL
                            REFERENCES simulation_run(id)
                            ON DELETE CASCADE,

    rf_annual               NUMERIC(8,6) NOT NULL DEFAULT 0.0,
    annualization_factor    INT NOT NULL DEFAULT 252,

    metrics_json            JSONB NOT NULL,

    calculated_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE analysis_result IS
'성과 분석 결과 캐시 (Phase 2 / Epic D)';

COMMENT ON COLUMN analysis_result.metrics_json IS
'CAGR, Volatility, Sharpe, MDD 등 KPI JSON';

-- 동일 run + 동일 가정이면 결과 1건
CREATE UNIQUE INDEX IF NOT EXISTS ux_analysis_result_run_params
    ON analysis_result (simulation_run_id, rf_annual, annualization_factor);

-- 조회 최적화
CREATE INDEX IF NOT EXISTS idx_analysis_result_run
    ON analysis_result (simulation_run_id);

COMMIT;
```

---

# Part B) Epic D 구현 작업 티켓 (JIRA 스타일)

## Epic D 목표
- 시뮬레이션 결과에 대한 **정량적 성과 해석**
- 리밸런싱 ON/OFF, 시나리오 간 **비교 가능**
- Phase 2 범위 내에서 **완전한 설명 가능성 확보**

---

## D-0. 공통 DoD (모든 티켓 공통)
- [ ] “추천 / 유리 / 최적” 표현 또는 로직 0%
- [ ] 동일 run + 동일 파라미터 → 동일 KPI
- [ ] Phase 1 테스트 전부 통과 유지
- [ ] KPI 계산 로직 단위 테스트 포함

---

## P2-D1 (Service) KPI 계산 핵심 모듈 구현
**타입**: Story / Backend  
**우선순위**: P0  

**대상 파일**
- `backend/app/services/performance_analyzer.py`

**요구사항**
- [ ] NAV 시계열 → 일간 수익률 재계산
- [ ] CAGR, Volatility, Sharpe, MDD 계산
- [ ] MDD peak/trough 날짜 산출
- [ ] 변동성 0 → Sharpe NULL 처리

**DoD**
- [ ] 단순 NAV 케이스 단위 테스트 통과

---

## P2-D2 (Persistence) analysis_result 저장/조회
**타입**: Task  
**우선순위**: P0  

**대상**
- ORM 모델 추가
- store/service 레이어 추가

**요구사항**
- [ ] (run_id, rf, annualization) 기준 조회
- [ ] 존재 시 재계산 없이 반환
- [ ] 미존재 시 계산 후 저장

**DoD**
- [ ] 캐시 히트/미스 케이스 테스트

---

## P2-D3 (Integration) 리밸런싱 정보 요약 결합
**타입**: Story  
**우선순위**: P1  

**요구사항**
- [ ] rebalancing_event 조인
- [ ] events_count
- [ ] total_turnover
- [ ] estimated_cost 합계

**DoD**
- [ ] KPI 응답에 rebalancing 요약 포함

---

## P2-D4 (API) 성과 KPI 조회 API
**타입**: Story / API  
**우선순위**: P1  

**엔드포인트**
- `GET /api/v1/analysis/run/{run_id}`

**요구사항**
- [ ] rf_annual, annualization_factor query 지원
- [ ] 내부적으로 D2 로직 사용

**DoD**
- [ ] run_id 기준 KPI 조회 가능

---

## P2-D5 (API) 성과 비교 API
**타입**: Story / API  
**우선순위**: P2  

**엔드포인트**
- `GET /api/v1/analysis/compare`

**요구사항**
- [ ] run_id_1, run_id_2 입력
- [ ] KPI delta 계산
- [ ] 설명용 note 포함(비추천 문구)

**DoD**
- [ ] 비교 결과 정상 반환

---

## P2-D6 (Ops) quality_report 성과 분석 항목 추가
**타입**: Task / Ops  
**우선순위**: P2  

**요구사항**
- [ ] KPI 계산 스모크
- [ ] 리밸런싱 ON/OFF KPI 차이 출력

**DoD**
- [ ] quality_report에서 Epic D 결과 확인

---

## 1차 구현 권장 범위 (최소 완성)
- P2-D1
- P2-D2
- (선택) P2-D4

→ 이 세 개만으로도 **Epic D 최소 기능 세트** 충족

---

## 부록: metrics_json 권장 키
- `cagr`
- `volatility`
- `sharpe`
- `mdd`
- `mdd_peak_date`
- `mdd_trough_date`
- `recovery_days` (optional)
- `total_return`
- `period_start`, `period_end`

---
