# Phase 3-C / Epic C-3 상세 설계
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

## 목차
1. 목적 (Purpose)
2. 기본 원칙 (Design Principles)
3. 성과 분석 범위
4. 성과 데이터 분류
5. 성과 지표 정의
6. 성과 산출 기준
7. 벤치마크 비교
8. 성과 저장 및 버전 관리
9. API 제공 기준
10. 오류·통제·면책
11. 완료 기준 (Definition of Done)
12. 다음 단계
13. 관련 문서

## Epic ID
- **Epic**: C-3
- **명칭**: 성과 분석 고도화 (Performance Analytics)
- **Phase**: Phase 3-C

---

## 1. 목적 (Purpose)

Epic C-3의 목적은 포트폴리오 및 계정 단위의 성과를 **운영 환경에서 신뢰 가능하고, 재현 가능하며, 오해의 소지가 없도록** 제공하는 것이다.

본 Epic은 **투자 권유·추천이 아닌 정보 제공**에 한정하며, 백테스트·시뮬레이션과 실운영 성과를 엄격히 분리한다.

---

## 2. 기본 원칙 (Design Principles)

1. **실운영 vs 시뮬레이션 완전 분리**
2. **성과 산식·기준일 명문화** (모호성 제거)
3. **성과 결과보다 산출 근거를 우선 저장**
4. **사용자 노출용 지표와 내부 분석 지표 분리**
5. **C-1, C-2와의 강결합(Execution / Snapshot / Version 기반)**

---

## 3. 성과 분석 범위

### 3.1 분석 대상
- 포트폴리오 단위
- 계정 단위
- 자산군 단위(주식/채권/현금성 등)

### 3.2 분석 기간
- 일간(Daily)
- 월간(Monthly)
- 누적(Cumulative)

---

## 4. 성과 데이터 분류

### 4.1 성과 타입

| 구분 | 코드 | 설명 |
|---|---|---|
| 실운영 | LIVE | 실제 계정/포트 성과 |
| 시뮬레이션 | SIM | 가상 포트 성과 |
| 백테스트 | BACK | 과거 데이터 기반 결과 |

> 사용자 화면에는 LIVE만 기본 노출

---

## 5. 성과 지표 정의

### 5.1 수익률 지표

| 지표 | 설명 |
|---|---|
| Period Return | 기간 수익률 |
| Cumulative Return | 누적 수익률 |
| Annualized Return | 연환산 수익률 |

### 5.2 리스크 지표

| 지표 | 설명 |
|---|---|
| Volatility | 변동성 |
| MDD | 최대 낙폭 |
| Sharpe Ratio | 위험조정 수익률 |
| Sortino Ratio | 하방위험 기준 |

---

## 6. 성과 산출 기준

### 6.1 가격 기준
- 종가(Close) 기준
- 거래 정지 시 최근 유효 가격 사용

### 6.2 반영 요소
- 수수료: 반영(명시)
- 세금: 기본 미반영(주석 처리)
- 배당/이자: 선택 반영(플래그)
- 환율: FX snapshot 기준

---

## 7. 벤치마크 비교

### 7.1 벤치마크 유형
- 시장 지수(KOSPI, S&P500 등)
- 혼합 벤치마크(자산군 가중 평균)
- 현금성 기준

### 7.2 비교 지표
- 초과 수익률
- 동일 기간 수익률 차이

---

## 8. 성과 저장 및 버전 관리

### 8.1 저장 원칙
- 성과 결과는 **불변(Immutable)**
- 재계산 시 신규 결과 버전 생성
- active 버전 1개만 사용자 노출

### 8.2 참조 키
- execution_id (C-1)
- input snapshot_id (C-2)
- result_version_id

---

## 9. API 제공 기준

### 9.1 내부 분석 API
- 모든 성과 타입(LIVE/SIM/BACK) 조회 가능
- 상세 산출 근거 포함

### 9.2 사용자 노출 API
- LIVE 성과만 제공
- 산식 요약 + 면책 문구 포함

---

## 10. 오류·통제·면책

- 성과 미산출 시 오류 코드 반환(C3-PF-XXX)
- 데이터 부족/지연 시 "참고용" 표기
- 투자 성과 보장 표현 금지

---

## 11. 완료 기준 (Definition of Done)

- [ ] LIVE/SIM/BACK 성과 분리 저장
- [ ] 성과 산식/기준 문서화
- [ ] 벤치마크 비교 가능
- [ ] 사용자/내부 API 분리
- [ ] C-1/C-2와 연계된 재현성 확보

---

## 12. 다음 단계

- C-3 DDL 설계
- 성과 계산 엔진 상세 설계
- C-3 구현 작업 티켓 분해

---

## 13. 관련 문서
- `docs/phase3/c3_ddl_schema.md`
- `docs/phase3/c3_ddl_schema.sql`
- `docs/phase3/c3_performance_engine_spec.md`
- `docs/phase3/c3_implementation_tickets.md`
- `docs/phase3/c1_c3_go_live_checklist.md`
- `20260118_phase3c_epic_c1_operations_stability_detailed_design.md`
- `20260118_phase3c_epic_c2_data_quality_lineage_reproducibility_detailed_design.md`

---

*본 문서는 Phase 3-C Epic C-3의 기준 설계 문서이며, 성과 분석 기능의 단일 기준으로 사용된다.*
