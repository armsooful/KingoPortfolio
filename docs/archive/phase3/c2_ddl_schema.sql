-- =============================================================================
-- Phase 3-C / Epic C-2: Data Quality · Lineage · Reproducibility DDL
-- 생성일: 2026-01-18
-- 목적: 데이터 스냅샷/계보/검증/실행 컨텍스트/품질 리포트 저장
-- 대상 DB: PostgreSQL
-- =============================================================================

BEGIN;

SET search_path TO foresto;

-- -----------------------------------------------------------------------------
-- 1. 원천 데이터 스냅샷
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS data_snapshot (
    snapshot_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor             VARCHAR(50) NOT NULL,              -- 데이터 제공자
    dataset_type       VARCHAR(50) NOT NULL,              -- PRICE/FX/DIVIDEND/BENCHMARK 등
    asof_date          DATE NOT NULL,                     -- 기준 일자
    snapshot_label     VARCHAR(100),                      -- 수집 배치/태그
    source_uri         TEXT,                              -- 원천 위치
    record_count       INTEGER DEFAULT 0,
    checksum           VARCHAR(128),                      -- 무결성 검증용 해시
    collected_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active          BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_data_snapshot_key ON data_snapshot(vendor, dataset_type, asof_date);
CREATE INDEX idx_data_snapshot_active ON data_snapshot(is_active);

COMMENT ON TABLE data_snapshot IS '원천 데이터 스냅샷';

-- -----------------------------------------------------------------------------
-- 2. 데이터 계보(Lineage)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS data_lineage_node (
    node_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_type          VARCHAR(30) NOT NULL,              -- SOURCE/SNAPSHOT/TRANSFORM/AGGREGATION/RESULT
    ref_type           VARCHAR(50) NOT NULL,              -- 참조 대상 타입
    ref_id             VARCHAR(100) NOT NULL,             -- 참조 대상 ID
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active          BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_lineage_node_ref ON data_lineage_node(ref_type, ref_id);

CREATE TABLE IF NOT EXISTS data_lineage_edge (
    edge_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_node_id       UUID NOT NULL REFERENCES data_lineage_node(node_id) ON DELETE CASCADE,
    to_node_id         UUID NOT NULL REFERENCES data_lineage_node(node_id) ON DELETE CASCADE,
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_lineage_edge_from ON data_lineage_edge(from_node_id);
CREATE INDEX idx_lineage_edge_to ON data_lineage_edge(to_node_id);

COMMENT ON TABLE data_lineage_node IS '계보 노드';
COMMENT ON TABLE data_lineage_edge IS '계보 엣지';

-- -----------------------------------------------------------------------------
-- 3. Validation Rule 메타
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS validation_rule_master (
    rule_code          VARCHAR(30) PRIMARY KEY,           -- C2-DQ-XXX
    rule_type          VARCHAR(10) NOT NULL,              -- REQ/RNG/UNQ/REF/CST
    rule_name          VARCHAR(100) NOT NULL,
    description        TEXT,
    severity           VARCHAR(10) NOT NULL,              -- WARN/FAIL
    scope_type         VARCHAR(20) NOT NULL DEFAULT 'GLOBAL', -- GLOBAL/DATASET/JOB/RESULT
    scope_key          VARCHAR(50),                       -- dataset_type/vendor/job_id 등
    scope_value        VARCHAR(100),                      -- scope_key 값
    scope_json         JSONB NOT NULL DEFAULT '{}'::JSONB,
    is_active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_validation_rule_type ON validation_rule_master(rule_type);
CREATE INDEX idx_validation_rule_scope ON validation_rule_master(scope_type, scope_key, scope_value);

CREATE TABLE IF NOT EXISTS validation_rule_version (
    rule_version_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_code          VARCHAR(30) NOT NULL REFERENCES validation_rule_master(rule_code),
    version_no         INTEGER NOT NULL,
    rule_params        JSONB NOT NULL DEFAULT '{}'::JSONB,
    effective_from     DATE NOT NULL DEFAULT CURRENT_DATE,
    effective_to       DATE,
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (rule_code, version_no)
);

COMMENT ON TABLE validation_rule_master IS '정합성 규칙 마스터';
COMMENT ON TABLE validation_rule_version IS '정합성 규칙 버전';

-- -----------------------------------------------------------------------------
-- 4. Validation 실행 결과
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS validation_result (
    result_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id       UUID NOT NULL REFERENCES batch_execution(execution_id) ON DELETE CASCADE,
    rule_code          VARCHAR(30) NOT NULL REFERENCES validation_rule_master(rule_code),
    rule_version_id    UUID REFERENCES validation_rule_version(rule_version_id),
    target_ref_type    VARCHAR(50) NOT NULL,              -- 대상 데이터 타입
    target_ref_id      VARCHAR(100) NOT NULL,             -- 대상 데이터 ID
    status             VARCHAR(10) NOT NULL,              -- PASS/WARN/FAIL
    violation_count    INTEGER DEFAULT 0,
    sample_detail      JSONB,                             -- 위반 샘플
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_validation_result_exec ON validation_result(execution_id);
CREATE INDEX idx_validation_result_rule ON validation_result(rule_code, status);

COMMENT ON TABLE validation_result IS '정합성 실행 결과';

-- -----------------------------------------------------------------------------
-- 5. 실행 컨텍스트 (재현성)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS execution_context (
    context_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id       UUID NOT NULL REFERENCES batch_execution(execution_id) ON DELETE CASCADE,
    snapshot_ids       JSONB NOT NULL,                    -- 사용된 스냅샷 ID 목록
    rule_version_ids   JSONB NOT NULL,                    -- 적용된 규칙 버전 목록
    calc_params        JSONB NOT NULL DEFAULT '{}'::JSONB,
    code_version       VARCHAR(50),                       -- git commit hash
    started_at         TIMESTAMP,
    ended_at           TIMESTAMP,
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX ux_execution_context_execution ON execution_context(execution_id);

COMMENT ON TABLE execution_context IS '실행 컨텍스트(재현성)';

-- -----------------------------------------------------------------------------
-- 6. 데이터 품질 리포트
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS data_quality_report (
    report_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id       UUID NOT NULL REFERENCES batch_execution(execution_id) ON DELETE CASCADE,
    report_date        DATE NOT NULL,
    summary_json       JSONB NOT NULL,                    -- PASS/WARN/FAIL 요약
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS data_quality_report_item (
    item_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id          UUID NOT NULL REFERENCES data_quality_report(report_id) ON DELETE CASCADE,
    dataset_type       VARCHAR(50) NOT NULL,
    status             VARCHAR(10) NOT NULL,              -- PASS/WARN/FAIL
    detail_json        JSONB,
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dq_report_date ON data_quality_report(report_date);
CREATE INDEX idx_dq_item_report ON data_quality_report_item(report_id);

COMMENT ON TABLE data_quality_report IS '데이터 품질 리포트';
COMMENT ON TABLE data_quality_report_item IS '데이터 품질 리포트 항목';

COMMIT;
