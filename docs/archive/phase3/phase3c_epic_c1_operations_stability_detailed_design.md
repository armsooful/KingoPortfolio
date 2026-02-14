# Phase 3-C / Epic C-1 상세 설계
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

## Epic ID
- **Epic**: C-1
- **명칭**: 운영 안정성 · 복구 체계 (Ops Reliability)
- **Phase**: Phase 3-C

## 관련 문서
- docs/phase3/c1_ddl_schema.sql
- docs/phase3/c1_implementation_tickets.md
- docs/phase3/c1_risk_control_checklist.md
- docs/phase3/c1_c2_integration_checklist.md
- docs/phase3/c1_c2_boundary.md
- docs/phase3/c1_c3_go_live_checklist.md
- 20260118_phase3c_epic_c2_data_quality_lineage_reproducibility_detailed_design.md
- 20260118_phase3c_epic_c3_performance_analysis_advanced_detailed_design.md

---

## 1. 목적 (Purpose)

Epic C-1의 목적은 시스템 장애·오류·데이터 불일치 상황에서도 **운영자가 통제 가능한 방식으로 탐지, 중단, 재처리, 복구**할 수 있는 구조를 제공하는 것이다.

> 핵심 원칙: *자동 복구보다 수동 통제 가능한 복구*

---

## 2. 범위 (In-Scope / Out-of-Scope)

### In-Scope
- 배치 실행 상태 관리
- 재처리(Replay) / 롤백(Rollback) 설계
- 오류 분류 및 표준 대응 체계
- 운영 로그 및 감사 추적
- 최소 수준의 모니터링·알림

### Out-of-Scope
- 완전 자동 복구(Self-healing)
- 실시간 고가용성(HA) 아키텍처
- 성능 튜닝 및 속도 최적화

---

## 3. 운영 장애 분류 체계

### 3.1 장애 유형 분류

| 구분 | 코드 | 설명 | 예시 |
|---|---|---|---|
| 입력 데이터 | INP | 원천 데이터 오류 | NULL, 포맷 오류 |
| 외부 연동 | EXT | API/시세 수신 실패 | 타임아웃 |
| 배치 실행 | BAT | 배치 비정상 종료 | 중간 실패 |
| 데이터 무결성 | DQ | 정합성 위반 | 중복/누락 |
| 로직 오류 | LOG | 계산/분기 오류 | 산식 오류 |
| 시스템 | SYS | DB/서버 장애 | 커넥션 실패 |

---

## 4. 배치 실행 상태 관리 설계

### 4.1 실행 단위 정의
- **Execution ID**: 모든 배치 실행의 고유 식별자
- **Job ID**: 논리적 배치 단위
- **Run Type**: AUTO / MANUAL / REPLAY

### 4.2 상태 전이 모델

```
READY → RUNNING → SUCCESS
           ↘ FAILED
           ↘ STOPPED
```

### 4.3 멱등성(Idempotency) 원칙
- 동일 Execution ID는 **1회만 결과 반영**
- 재처리는 신규 Execution ID로 수행

---

## 5. 재처리(Replay) 전략

### 5.1 재처리 유형

| 유형 | 설명 | 사용 시점 |
|---|---|---|
| 전체 재처리 | 기간 전체 재실행 | 원천 오류 |
| 구간 재처리 | 특정 날짜 범위 | 부분 장애 |
| 단건 재처리 | 계정/포트 단위 | 국소 오류 |

### 5.2 재처리 원칙
- 기존 결과 **덮어쓰기 금지**
- 이전 결과는 `is_active = false` 처리
- 재처리 이력은 감사 로그에 필수 기록

---

## 6. 롤백 및 보정(Compensation)

### 6.1 롤백 전략
- 트랜잭션 단위 롤백 불가 시 논리적 롤백 사용
- 결과 데이터 비활성화 방식 적용

### 6.2 보정 처리
- 운영자 승인 하에 수동 보정 가능
- 보정 사유, 근거 데이터 필수 기록

---

## 7. 오류 코드 및 메시지 표준

### 7.1 오류 코드 체계

```
C1-INP-001 : Input data missing
C1-EXT-002 : External API timeout
C1-BAT-003 : Batch execution failed
C1-DQ-004  : Data validation failed
```

### 7.2 운영 메시지 원칙
- 사용자 노출 메시지 ≠ 운영 메시지
- 운영 메시지는 원인·조치 가이드 포함

---

## 8. 운영 로그 및 감사 추적

### 8.1 필수 로그 항목
- execution_id
- job_id
- run_type
- start_time / end_time
- status
- error_code
- operator_id (수동 개입 시)

### 8.2 감사 요구사항
- 모든 수동 실행/중단/재처리는 감사 대상
- 삭제 금지, 상태 변경 방식만 허용

---

## 9. 모니터링 · 알림 (Minimal)

### 9.1 알림 대상 이벤트
- 배치 실패
- 재처리 실행
- 수동 중단/재개

### 9.2 알림 채널
- Email (필수)
- Slack/Webhook (옵션)

---

## 10. 운영 점검 체크리스트

### 일일
- 전일 배치 SUCCESS 여부
- FAILED/STOPPED 건 존재 여부

### 월간
- 재처리 발생 빈도 분석
- 반복 오류 유형 정리

---

## 11. 완료 기준 (Definition of Done)

- [ ] 모든 배치 실행 상태가 DB로 추적 가능
- [ ] 재처리 실행 시 기존 결과 보존
- [ ] 운영자가 수동으로 중단·재개 가능
- [ ] 장애 발생 시 원인 추적 가능
- [ ] 감사 로그 누락 없음

---

## 12. 다음 단계

- C-1 DDL 설계
- C-1 구현 작업 티켓 분해
- 운영자 Runbook 문서화

---

*본 문서는 Phase 3-C Epic C-1의 기준 설계 문서이며, 이후 모든 운영·복구 구현의 기준으로 사용된다.*
