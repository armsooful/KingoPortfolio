# Phase 3-C / Epic C-2 DDL 설계 요약
최초작성일자: 2026-01-18
최종수정일자: 2026-01-18

- 문서명: C-2 DDL 설계 요약
- 대상: 데이터 품질 · 계보 · 재현성
- 기준 DDL: `docs/phase3/c2_ddl_schema.sql`

## 1. 스냅샷(Snapshot)
- 테이블: `data_snapshot`
- 목적: 원천 데이터 버전 식별
- 주요 키: `vendor`, `dataset_type`, `asof_date`, `snapshot_id`
- 핵심 필드: `record_count`, `checksum`, `source_uri`, `collected_at`, `is_active`

## 2. 계보(Lineage)
- 테이블: `data_lineage_node`, `data_lineage_edge`
- 목적: SOURCE → SNAPSHOT → TRANSFORM → AGGREGATION → RESULT 추적
- 규칙: 모든 결과는 상위 노드 참조, 삭제 금지(is_active=false)
- 인덱스: `ref_type/ref_id`, `from_node_id`, `to_node_id`

## 3. 정합성(Validation)
- 테이블: `validation_rule_master`, `validation_rule_version`, `validation_result`
- 목적: 규칙 정의/버전 관리 및 실행 결과 저장
- 상태: `PASS/WARN/FAIL`
- 규칙 분류: `REQ/RNG/UNQ/REF/CST`

## 4. 실행 컨텍스트(재현성)
- 테이블: `execution_context`
- 목적: 동일 결과 재현을 위한 실행 정보 저장
- 포함 항목: `execution_id`, `snapshot_ids`, `rule_version_ids`, `calc_params`, `code_version`, `started_at/ended_at`

## 5. 데이터 품질 리포트
- 테이블: `data_quality_report`, `data_quality_report_item`
- 목적: 일별/재처리 품질 리포트 생성
- 요약: `summary_json` (PASS/WARN/FAIL 집계)
- 항목: dataset 단위 상세 상태

## 6. C-1 연계 지점
- Validation FAIL → `execution FAILED` + 알림
- WARN 누적 → 운영 점검 대상

## 7. 완료 기준 매핑
- 결과 데이터 → snapshot_id 참조: `execution_context.snapshot_ids`
- 규칙 버전 추적: `validation_rule_version` + `execution_context.rule_version_ids`
- 품질 리포트 자동화: `data_quality_report*`
