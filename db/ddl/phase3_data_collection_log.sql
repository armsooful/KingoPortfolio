-- Phase 3: 데이터 수집 이력 로그 테이블
-- 스케줄러 실행 결과 + 정합성 검증 결과 저장

CREATE TABLE IF NOT EXISTS data_collection_log (
    id SERIAL PRIMARY KEY,
    job_name VARCHAR(50) NOT NULL,
    job_label VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_seconds FLOAT,
    success_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    total_count INTEGER DEFAULT 0,
    detail JSONB,
    error_message TEXT,
    validation_status VARCHAR(20),
    validation_detail JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dcl_job_status ON data_collection_log(job_name, status);
CREATE INDEX IF NOT EXISTS idx_dcl_created_at ON data_collection_log(created_at);
