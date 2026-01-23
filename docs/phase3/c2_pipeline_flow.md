# C-2 파이프라인 흐름 (수집 → 검증 → 계보 → 리포트)
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

## 1. 수집
- 입력 데이터 수집 및 스냅샷 기록
- 테이블: `data_snapshot`
- 핵심 산출물: snapshot_id 목록

## 2. 검증
- Validation Rule 적용
- 테이블: `validation_rule_master`, `validation_rule_version`, `validation_result`
- 정책: FAIL 시 실행 중단, WARN 시 경고 기록

## 3. 계보
- SOURCE → SNAPSHOT → TRANSFORM → AGGREGATION → RESULT 노드/엣지 생성
- 테이블: `data_lineage_node`, `data_lineage_edge`

## 4. 실행 컨텍스트
- 재현성 보장을 위한 컨텍스트 저장
- 테이블: `execution_context`
- 포함 항목: snapshot_ids, rule_version_ids, calc_params, code_version

## 5. 리포트
- 데이터 품질 리포트 생성
- 테이블: `data_quality_report`, `data_quality_report_item`

## 6. C-1 연계
- Validation FAIL → execution FAILED + 알림
- WARN 누적 → 운영 점검 알림
