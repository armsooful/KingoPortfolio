# Epic C-1 구현 티켓
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

---
생성일자: 2026-01-18
Epic: C-1 (운영 안정성)
---

# Epic C-1 구현 티켓

## 티켓 개요

| 티켓 ID | 제목 | 우선순위 | 예상 복잡도 |
|---------|------|----------|-------------|
| C1-T01 | DDL 스키마 적용 | P0 | Low |
| C1-T02 | 배치 실행 상태 관리 모듈 | P0 | Medium |
| C1-T03 | 오류 코드 및 예외 처리 체계 | P0 | Medium |
| C1-T04 | 감사 로그 모듈 | P0 | Medium |
| C1-T05 | 재처리(Replay) 서비스 | P1 | High |
| C1-T06 | 결과 버전 관리 서비스 | P1 | Medium |
| C1-T07 | 운영 알림 서비스 | P2 | Medium |
| C1-T08 | 관리자 API 엔드포인트 | P1 | Medium |
| C1-T09 | 통합 테스트 | P1 | Medium |

---

## C1-T01: DDL 스키마 적용

### 설명
Phase 3-C 운영 안정성을 위한 DB 스키마를 적용한다.

### 작업 내용
- [ ] `c1_ddl_schema.sql` 리뷰 및 수정
- [ ] 개발 DB에 스키마 적용
- [ ] 초기 데이터 (오류 코드, 배치 작업) 적재 확인
- [ ] 인덱스 생성 확인

### 산출물
- DB 스키마 적용 완료
- 마이그레이션 스크립트 (필요시)

### 완료 기준
- 모든 테이블 생성 확인
- 초기 데이터 조회 가능

---

## C1-T02: 배치 실행 상태 관리 모듈

### 설명
배치 실행의 전체 라이프사이클을 관리하는 서비스를 구현한다.

### 작업 내용
- [ ] `BatchExecutionService` 클래스 구현
  - `start_execution()`: 실행 시작 기록
  - `update_progress()`: 진행 상황 업데이트
  - `complete_execution()`: 성공 완료 기록
  - `fail_execution()`: 실패 기록 (오류 코드 포함)
  - `stop_execution()`: 수동 중단 기록
- [ ] 상태 전이 검증 로직 (READY→RUNNING→SUCCESS/FAILED/STOPPED)
- [ ] 멱등성 보장 로직 (동일 execution_id 중복 처리 방지)

### 산출물
- `backend/app/services/batch_execution.py`
- 단위 테스트

### 완료 기준
- 상태 전이가 정상 동작
- 중복 실행 방지 확인

---

## C1-T03: 오류 코드 및 예외 처리 체계

### 설명
표준화된 오류 코드 체계와 예외 처리 클래스를 구현한다.

### 작업 내용
- [ ] `OpsException` 기본 예외 클래스
- [ ] 카테고리별 예외 클래스
  - `InputDataException` (INP)
  - `ExternalApiException` (EXT)
  - `BatchExecutionException` (BAT)
  - `DataQualityException` (DQ)
  - `LogicException` (LOG)
  - `SystemException` (SYS)
- [ ] 오류 코드 조회 서비스 (`ErrorCodeService`)
- [ ] 사용자 메시지 vs 운영 메시지 분리

### 산출물
- `backend/app/exceptions/ops_exceptions.py`
- `backend/app/services/error_code_service.py`

### 완료 기준
- 오류 발생 시 표준 코드로 기록
- 사용자/운영자 메시지 분리 확인

---

## C1-T04: 감사 로그 모듈

### 설명
모든 수동 개입 및 중요 변경을 추적하는 감사 로그 시스템을 구현한다.

### 작업 내용
- [ ] `AuditLogService` 클래스 구현
  - `log_batch_action()`: 배치 관련 감사 로그
  - `log_data_correction()`: 데이터 보정 감사 로그
  - `log_config_change()`: 설정 변경 감사 로그
- [ ] 운영자 ID 필수 검증
- [ ] 사유(reason) 필수 검증
- [ ] before/after 상태 자동 캡처

### 산출물
- `backend/app/services/audit_log_service.py`
- 단위 테스트

### 완료 기준
- 수동 실행 시 감사 로그 자동 기록
- 필수 필드 누락 시 오류 발생

---

## C1-T05: 재처리(Replay) 서비스

### 설명
과거 배치 결과를 안전하게 재처리하는 서비스를 구현한다.

### 작업 내용
- [ ] `ReplayService` 클래스 구현
  - `replay_full()`: 전체 재처리
  - `replay_range()`: 구간 재처리
  - `replay_single()`: 단건 재처리
- [ ] 재처리 전 기존 결과 비활성화 처리
- [ ] `parent_execution_id` 연결
- [ ] 재처리 사유 필수 기록
- [ ] 감사 로그 연동

### 산출물
- `backend/app/services/replay_service.py`
- 단위 테스트

### 완료 기준
- 재처리 시 기존 결과 보존 (is_active=false)
- 재처리 이력 추적 가능

---

## C1-T06: 결과 버전 관리 서비스

### 설명
시뮬레이션/성과/설명 등 결과 데이터의 버전을 관리한다.

### 작업 내용
- [ ] `ResultVersionService` 클래스 구현
  - `create_version()`: 신규 버전 생성
  - `deactivate_version()`: 기존 버전 비활성화
  - `get_active_version()`: 현재 유효 버전 조회
  - `get_version_history()`: 버전 이력 조회
- [ ] 동시에 하나의 active 버전만 유지 보장

### 산출물
- `backend/app/services/result_version_service.py`
- 단위 테스트

### 완료 기준
- 결과 덮어쓰기 방지 확인
- 버전 이력 조회 가능

---

## C1-T07: 운영 알림 서비스

### 설명
배치 실패, 재처리 등 운영 이벤트 발생 시 알림을 발송한다.

### 작업 내용
- [ ] `OpsAlertService` 클래스 구현
  - `send_alert()`: 알림 발송
  - `acknowledge_alert()`: 알림 확인 처리
- [ ] 알림 채널 구현
  - Email (필수)
  - Slack webhook (옵션)
- [ ] 알림 발송 이력 기록
- [ ] 오류 코드 기반 자동 알림 (auto_alert=true)

### 산출물
- `backend/app/services/ops_alert_service.py`
- 알림 템플릿

### 완료 기준
- 배치 실패 시 알림 발송
- 발송 이력 조회 가능

---

## C1-T08: 관리자 API 엔드포인트

### 설명
운영자가 배치를 제어하고 모니터링할 수 있는 API를 구현한다.

### 작업 내용
- [ ] 배치 조회 API
  - `GET /admin/batch/executions` - 실행 이력 조회
  - `GET /admin/batch/executions/{id}` - 실행 상세 조회
- [ ] 배치 제어 API
  - `POST /admin/batch/executions/{job_id}/start` - 수동 실행
  - `POST /admin/batch/executions/{id}/stop` - 수동 중단
  - `POST /admin/batch/replay` - 재처리 실행
- [ ] 감사 로그 조회 API
  - `GET /admin/audit-logs` - 감사 로그 조회
- [ ] 알림 조회/확인 API
  - `GET /admin/alerts` - 알림 목록
  - `POST /admin/alerts/{id}/acknowledge` - 알림 확인

### 산출물
- `backend/app/routes/admin_batch.py`
- API 문서 (OpenAPI)

### 완료 기준
- 운영자가 웹에서 배치 제어 가능
- 권한 검증 동작

---

## C1-T09: 통합 테스트

### 설명
Epic C-1 전체 기능의 통합 테스트를 수행한다.

### 작업 내용
- [ ] 배치 실행 → 실패 → 재처리 시나리오 테스트
- [ ] 감사 로그 생성 검증
- [ ] 알림 발송 검증
- [ ] 결과 버전 관리 검증
- [ ] 멱등성 검증

### 산출물
- `backend/tests/integration/test_ops_reliability.py`

### 완료 기준
- 모든 통합 테스트 통과
- Definition of Done 체크리스트 충족

---

## 우선순위 및 의존관계

```
C1-T01 (DDL) ─────────────────────────────────────────┐
     │                                                 │
     ▼                                                 │
C1-T02 (배치 상태) ──┬──► C1-T05 (재처리) ──► C1-T09  │
     │               │          │                      │
     ▼               │          ▼                      │
C1-T03 (오류 코드) ──┤    C1-T06 (버전관리)           │
     │               │                                 │
     ▼               │                                 │
C1-T04 (감사 로그) ──┴──► C1-T07 (알림) ──► C1-T08 ──►┘
```

---

## C2-T01: DDL 스키마 설계

### 설명
Epic C-2 데이터 품질/계보/재현성 스키마를 설계한다.

### 작업 내용
- [ ] 스냅샷/계보/검증/컨텍스트/리포트 테이블 정의
- [ ] 인덱스 및 제약조건 명세

### 산출물
- `docs/phase3/c2_ddl_schema.sql`

### 완료 기준
- C-2 핵심 엔티티 DDL 확정

---

## C2-T02: Validation Rule 메타 스키마/정책

### 설명
정합성 규칙 및 실행 결과를 저장하고 정책을 적용한다.

### 작업 내용
- [ ] 규칙/버전/결과 모델 및 서비스 구현
- [ ] FAIL/WARN 정책 적용 로직

### 산출물
- `backend/app/models/data_quality.py`
- `backend/app/services/data_quality_service.py`

### 완료 기준
- FAIL 시 실행 차단 가능
- WARN/PASS 집계 가능

---

## C2-T03: 실행 컨텍스트 저장

### 설명
재현 가능한 실행 컨텍스트를 저장한다.

### 작업 내용
- [ ] execution_context 저장 서비스 구현
- [ ] snapshot_id/룰 버전/파라미터/코드버전 기록

### 산출물
- `backend/app/services/execution_context_service.py`

### 완료 기준
- execution_id 기준으로 컨텍스트 조회 가능

---

## C2-T04: Lineage 추적

### 설명
SOURCE → SNAPSHOT → TRANSFORM → AGGREGATION → RESULT 계보 추적을 구현한다.

### 작업 내용
- [ ] lineage 노드/엣지 생성 API
- [ ] 결과 → 스냅샷 역추적 조회 API

### 산출물
- `backend/app/services/lineage_service.py`
- `backend/app/routes/admin_lineage.py`

### 완료 기준
- 결과 기준으로 입력 스냅샷 추적 가능

---

## C2-T05: 데이터 품질 리포트 생성

### 설명
일별/재처리 시 품질 리포트를 생성한다.

### 작업 내용
- [ ] 품질 요약/항목 생성 로직
- [ ] 리포트 조회 API

### 산출물
- `backend/app/services/data_quality_report_service.py`
- `backend/app/routes/admin_data_quality.py`

### 완료 기준
- PASS/WARN/FAIL 요약 리포트 확인 가능

---

## C2-T06: C-1 연계

### 설명
C-2 이벤트를 C-1 실행/알림 체계와 연계한다.

### 작업 내용
- [ ] FAIL → execution FAILED 처리
- [ ] WARN 누적 알림 정책 정의

### 산출물
- `backend/app/services/data_quality_service.py` (정책 연계)
- `backend/app/services/ops_alert_service.py`

### 완료 기준
- Validation FAIL 발생 시 자동 차단 및 알림 가능

## 일정 (권장)

| 주차 | 티켓 |
|------|------|
| Week 1 | C1-T01, C1-T02, C1-T03 |
| Week 2 | C1-T04, C1-T05, C1-T06 |
| Week 3 | C1-T07, C1-T08 |
| Week 4 | C1-T09, 검증 및 문서화 |

---

*문서 끝*
