# C-1 + C-2 통합 관점 점검표
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

## 1. 실행/상태 연계
- [ ] Validation FAIL 시 `batch_execution.status=FAILED`
- [ ] FAIL 발생 시 오류 코드(C2-DQ-XXX) 기록
- [ ] FAIL 발생 시 운영 알림 발송
- [ ] WARN 누적 시 운영 점검 대상 등록

## 2. 감사/알림 연계
- [ ] 수동 재처리 실행 시 감사 로그 기록
- [ ] 재처리 실행 시 알림 발송
- [ ] 데이터 보정 시 lineage에 보정 노드 추가

## 3. 재현성
- [ ] execution_context에 snapshot_ids 기록
- [ ] execution_context에 rule_version_ids 기록
- [ ] code_version 기록

## 4. 계보 추적
- [ ] 결과 → 스냅샷 역추적 가능
- [ ] lineage 노드/엣지 삭제 금지 (비활성화만 허용)

## 5. 리포트
- [ ] 리포트 생성 주기(일별/재처리) 확인
- [ ] PASS/WARN/FAIL 요약 제공
- [ ] 실패 규칙 Top N 산출 가능
