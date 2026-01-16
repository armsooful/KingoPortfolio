# Foresto Phase 2 전체 백로그

**문서명**: Foresto Phase 2 Product Backlog  
**작성일**: 2026-01-15  
**버전**: 1.0.0  
**상태**: Draft (Phase 2 착수용)  

---

## 1. Phase 2 개요

### 1.1 목적
Phase 2는 Phase 1에서 구축된 시뮬레이션 인프라 위에  
**운영 논리를 갖춘 투자 프로세스 시뮬레이션 계층**을 추가하는 단계이다.

- 투자 “추천”이나 “자동 판단”은 수행하지 않는다.
- 모든 결과는 설명 가능하고 재현 가능한 시뮬레이션 결과로 제한한다.

---

## 2. Phase 2 목표 요약

| 구분 | 목표 |
|----|----|
| 리밸런싱 | 운영 가능한 리밸런싱 규칙 구현 |
| 사용자 개입 | 사용자 정의 포트폴리오 허용 |
| 분석 | 결과 해석 및 비교 가능한 분석 지표 제공 |
| 안정성 | Phase 1 기능·테스트 완전 유지 |

---

## 3. Epic 구조

Phase 2는 총 **5개 Epic**으로 구성된다.

```
Epic A. 리밸런싱 데이터 모델
Epic B. 리밸런싱 엔진
Epic C. 사용자 커스텀 포트폴리오
Epic D. 성과 분석 계층
Epic E. 운영·통제·품질
```

---

## 4. Epic A – 리밸런싱 데이터 모델

### A-1. 리밸런싱 규칙 테이블 설계
- 목적: 리밸런싱 로직의 선언적 정의
- 산출물:
  - `rebalancing_rule` 테이블
- 포함 필드:
  - rule_id
  - rebalance_type (PERIODIC / DRIFT)
  - frequency (M/Q)
  - drift_threshold
  - effective_from / to
- DoD:
  - Phase 1 테이블 변경 없음
  - 단일 시나리오에 다중 규칙 연결 가능

---

### A-2. 리밸런싱 이벤트 로그
- 목적: “언제, 왜 리밸런싱이 발생했는지” 기록
- 산출물:
  - `rebalancing_event` 테이블
- 기록 항목:
  - simulation_run_id
  - event_date
  - trigger_reason
  - before_weights / after_weights
- DoD:
  - 시뮬레이션 재실행 시 동일 이벤트 재현 가능

---

## 5. Epic B – 리밸런싱 엔진

### B-1. 정기 리밸런싱 로직
- 지원 주기: 월간 / 분기
- 처리 흐름:
  ```
  기준일 도달 → 현재 비중 계산 → 목표 비중으로 재조정
  ```
- DoD:
  - 리밸런싱 ON/OFF 결과 차이 검증 가능

---

### B-2. Drift 기반 리밸런싱 로직
- 기준:
  - 자산 비중 ±X% 초과 시
- DoD:
  - Drift 미발생 시 리밸런싱 미실행

---

### B-3. 리밸런싱 비용 가정
- 고정 비용 모델 (Phase 2 한정)
- DoD:
  - 비용 가정값이 결과 지표에 반영됨

---

## 6. Epic C – 사용자 커스텀 포트폴리오

### C-1. 사용자 포트폴리오 정의
- 허용:
  - 자산군 선택
  - 비중 직접 입력
- 제한:
  - 개별 종목 입력 금지
- DoD:
  - 비중 합계 100% 자동 검증

---

### C-2. 시나리오 템플릿 연결
- 사용자 포트폴리오는 기존 시나리오를 “확장”하는 방식
- DoD:
  - 기존 시나리오 삭제·변경 없음

---

## 7. Epic D – 성과 분석 계층

### D-1. 핵심 성과 지표 계산
- 필수 지표:
  - CAGR
  - MDD
  - Volatility
  - Sharpe (단순 기준)
- DoD:
  - 모든 지표는 재계산 가능

---

### D-2. 비교 분석 기능
- 비교 대상:
  - 시나리오 A vs B
  - 리밸런싱 ON vs OFF
- DoD:
  - 동일 조건 재실행 시 동일 결과

---

## 8. Epic E – 운영·통제·품질

### E-1. Feature Flag 확장
- 신규 Flag:
  - USE_REBALANCING
  - ALLOW_CUSTOM_PORTFOLIO
  - USE_ANALYTICS_LAYER
- DoD:
  - 기본값 OFF

---

### E-2. 품질·재현성 테스트
- 테스트 범위:
  - Phase 1 기존 테스트 100% 통과
  - Phase 2 신규 테스트 분리
- DoD:
  - Phase 2 OFF 상태에서 기존 시스템 영향 0

---

## 9. Phase 2 전체 Definition of Done

- [ ] Phase 1 기능 무변경
- [ ] 리밸런싱 ON/OFF 비교 가능
- [ ] 사용자 포트폴리오 시뮬레이션 가능
- [ ] 모든 결과는 설명 가능한 지표만 포함
- [ ] 투자 판단·추천 요소 0%

---

## 10. Phase 3로 이월되는 항목 (명시적 제외)

- 실시간 체결 연동
- 자동 리밸런싱 실행
- 개인 투자 성향 기반 추천
- 주문·계좌 연계

---

**작성자**: ForestoCompass  
**비고**: 본 문서는 Phase 2 개발·리뷰·감사 기준 문서로 사용 가능
