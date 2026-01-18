# Phase 3-C / Epic C-2 상세 설계
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

## 목차
- [1. 목적 (Purpose)](#1-목적-purpose)
- [2. 범위 정의 (Scope)](#2-범위-정의-scope)
- [3. 데이터 버전 관리 전략](#3-데이터-버전-관리-전략)
- [4. 데이터 계보(Lineage) 모델](#4-데이터-계보lineage-모델)
- [5. 정합성(Validation) 규칙 체계](#5-정합성validation-규칙-체계)
- [6. 실행 컨텍스트 저장](#6-실행-컨텍스트-저장)
- [7. 데이터 품질 리포트](#7-데이터-품질-리포트)
- [8. C-1(운영 안정성) 연계 지점](#8-c-1운영-안정성-연계-지점)
- [9. 감사·추적 요구사항](#9-감사추적-요구사항)
- [10. 완료 기준 (Definition of Done)](#10-완료-기준-definition-of-done)
- [11. 다음 단계](#11-다음-단계)

## 관련 문서
- docs/phase3/c2_ddl_schema.sql
- docs/phase3/20260118_20260118_c2_ddl_schema.md
- docs/phase3/20260118_20260118_c2_validation_rule_model.md
- docs/phase3/20260118_20260118_c2_implementation_tickets.md
- docs/phase3/20260118_20260118_c2_pipeline_flow.md
- docs/phase3/20260118_20260118_c1_c2_integration_checklist.md
- docs/phase3/20260118_20260118_c1_c2_boundary.md
- docs/phase3/20260118_20260118_c1_c3_go_live_checklist.md
- 20260118_phase3c_epic_c1_operations_stability_detailed_design.md
- 20260118_phase3c_epic_c3_performance_analysis_advanced_detailed_design.md


## Epic ID
- **Epic**: C-2
- **명칭**: 데이터 품질 · 계보 · 재현성 (Data Quality & Lineage)
- **Phase**: Phase 3-C

---

## 1. 목적 (Purpose)

Epic C-2의 목적은 모든 데이터 산출물(성과·지표·리포트)이 **언제, 어떤 원천 데이터로, 어떤 규칙과 파라미터로 계산되었는지**를 사후에 100% 재현 가능하도록 만드는 것이다.

> 핵심 원칙: *결과보다 과정이 더 중요하다*

---

## 2. 범위 정의 (Scope)

### In-Scope
- 원천 데이터 스냅샷/버전 관리
- 데이터 변환 계보(Lineage) 추적
- 정합성(Validation) 규칙 정의 및 실행
- 실행 컨텍스트(파라미터/룰/코드버전) 저장
- 데이터 품질 리포트 자동 생성

### Out-of-Scope
- 데이터 정제/보정의 자동화(운영자 승인 없는 자동 수정)
- 실시간 스트리밍 품질 관리
- 외부 BI 도구 연계

---

## 3. 데이터 버전 관리 전략

### 3.1 원천 데이터 식별자

모든 입력 데이터는 다음 조합으로 **유일하게 식별**되어야 한다.

- `vendor` : 데이터 제공자 식별자
- `dataset_type` : PRICE / FX / DIVIDEND / BENCHMARK 등
- `asof_date` : 기준 일자
- `snapshot_id` : 수집 시점 식별자

> 동일 asof_date라도 snapshot_id가 다르면 **다른 데이터 버전**으로 취급

---

## 4. 데이터 계보(Lineage) 모델

### 4.1 계보 단계 정의

```
SOURCE → SNAPSHOT → TRANSFORM → AGGREGATION → RESULT
```

### 4.2 계보 추적 원칙
- 모든 결과 데이터는 **직전 단계의 ID를 참조**
- 다대다(M:N) 변환도 중간 매핑 테이블로 추적
- 삭제 금지, 비활성화(is_active=false)만 허용

---

## 5. 정합성(Validation) 규칙 체계

### 5.1 규칙 분류

| 구분 | 코드 | 예시 |
|---|---|---|
| 필수값 | REQ | 가격 NULL 금지 |
| 범위 | RNG | 수익률 -100% ~ +1000% |
| 유일성 | UNQ | (종목,일자) 중복 금지 |
| 참조 | REF | 외래키 존재 여부 |
| 일관성 | CST | 합계=구성요소 합 |

---

### 5.2 규칙 실행 정책

| 결과 | 처리 정책 |
|---|---|
| PASS | 정상 진행 |
| WARN | 결과 생성 + 경고 기록 |
| FAIL | 실행 중단 + C-1 오류 처리 연계 |

- FAIL 발생 시 execution.status = FAILED
- 오류코드는 `C2-DQ-XXX` 규칙으로 통일

---

## 6. 실행 컨텍스트 저장

### 6.1 필수 저장 항목
- execution_id (C-1 연계)
- 입력 데이터 snapshot_id 목록
- 적용된 validation rule version
- 계산 파라미터(JSON)
- 코드 버전(git commit hash)
- 실행 시각(start/end)

> 이 정보만으로 **동일 결과 재현**이 가능해야 함

---

## 7. 데이터 품질 리포트

### 7.1 리포트 생성 주기
- 일별(기본)
- 재처리 발생 시 추가 생성

### 7.2 포함 내용
- 처리된 dataset 목록
- validation 결과 요약(PASS/WARN/FAIL)
- 실패 규칙 Top N
- 데이터 누락/지연 현황

---

## 8. C-1(운영 안정성) 연계 지점

| C-2 이벤트 | C-1 처리 |
|---|---|
| Validation FAIL | execution FAILED + 알림 |
| Snapshot 누락 | 재처리(REPLAY) 유도 |
| WARN 누적 | 운영 점검 대상 등록 |

---

## 9. 감사·추적 요구사항

- 결과 데이터 → 실행 컨텍스트 → 입력 스냅샷 → 원천 데이터까지 추적 가능
- 운영자 수동 보정 발생 시 lineage에 보정 노드 추가
- 감사 로그와 execution_id로 상호 참조 가능

---

## 10. 완료 기준 (Definition of Done)

- [ ] 모든 결과 데이터가 입력 snapshot_id를 참조
- [ ] 동일 입력/파라미터로 결과 재현 가능
- [ ] Validation FAIL 시 자동 차단
- [ ] 데이터 품질 리포트 자동 생성
- [ ] C-1 실행/오류/알림과 연계 완료

---

## 11. 다음 단계

- C-2 DDL 설계
- Validation Rule 메타 스키마 정의
- C-2 구현 작업 티켓 분해

---

*본 문서는 Phase 3-C Epic C-2의 기준 설계 문서이며, 데이터 신뢰성의 단일 기준으로 사용된다.*
