-- =============================================================================
-- Phase 3-C / Epic C-1: 운영 안정성 DDL 스키마
-- 생성일: 2026-01-18
-- 목적: 배치 실행 상태 관리, 재처리 이력, 감사 로그
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. 배치 작업 정의 테이블 (Job Master)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS batch_job (
    job_id VARCHAR(50) PRIMARY KEY,
    job_name VARCHAR(100) NOT NULL,
    job_description TEXT,
    job_type VARCHAR(20) NOT NULL,  -- 'DAILY', 'WEEKLY', 'MONTHLY', 'ON_DEMAND'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE batch_job IS '배치 작업 마스터 정의';
COMMENT ON COLUMN batch_job.job_id IS '논리적 배치 작업 ID';
COMMENT ON COLUMN batch_job.job_type IS 'DAILY/WEEKLY/MONTHLY/ON_DEMAND';

-- -----------------------------------------------------------------------------
-- 2. 배치 실행 이력 테이블 (Execution History)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS batch_execution (
    execution_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id VARCHAR(50) NOT NULL REFERENCES batch_job(job_id),
    run_type VARCHAR(20) NOT NULL,  -- 'AUTO', 'MANUAL', 'REPLAY'
    status VARCHAR(20) NOT NULL DEFAULT 'READY',  -- 'READY', 'RUNNING', 'SUCCESS', 'FAILED', 'STOPPED'

    -- 실행 시간 정보
    scheduled_at TIMESTAMP,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,

    -- 처리 범위
    target_date DATE,  -- 처리 대상 기준일
    target_start_date DATE,  -- 구간 처리 시 시작일
    target_end_date DATE,  -- 구간 처리 시 종료일

    -- 처리 결과
    processed_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,

    -- 오류 정보
    error_code VARCHAR(20),
    error_message TEXT,
    error_detail JSONB,

    -- 운영자 정보
    operator_id VARCHAR(50),  -- 수동 실행 시 운영자 ID
    operator_note TEXT,  -- 수동 실행 사유

    -- 재처리 연관
    parent_execution_id UUID REFERENCES batch_execution(execution_id),  -- 재처리 시 원본 실행 ID
    replay_reason TEXT,  -- 재처리 사유

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_batch_execution_job_id ON batch_execution(job_id);
CREATE INDEX idx_batch_execution_status ON batch_execution(status);
CREATE INDEX idx_batch_execution_target_date ON batch_execution(target_date);
CREATE INDEX idx_batch_execution_started_at ON batch_execution(started_at);

COMMENT ON TABLE batch_execution IS '배치 실행 이력 (모든 실행의 상태 추적)';
COMMENT ON COLUMN batch_execution.execution_id IS '실행 고유 ID (멱등성 보장 키)';
COMMENT ON COLUMN batch_execution.run_type IS 'AUTO=자동, MANUAL=수동, REPLAY=재처리';
COMMENT ON COLUMN batch_execution.status IS 'READY→RUNNING→SUCCESS/FAILED/STOPPED';

-- -----------------------------------------------------------------------------
-- 3. 배치 실행 상세 로그 테이블 (Execution Detail Log)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS batch_execution_log (
    log_id BIGSERIAL PRIMARY KEY,
    execution_id UUID NOT NULL REFERENCES batch_execution(execution_id),
    log_level VARCHAR(10) NOT NULL,  -- 'INFO', 'WARN', 'ERROR'
    log_category VARCHAR(20),  -- 'INP', 'EXT', 'BAT', 'DQ', 'LOG', 'SYS'
    log_code VARCHAR(20),  -- 'C1-INP-001' 형식
    log_message TEXT NOT NULL,
    log_detail JSONB,
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_batch_execution_log_execution_id ON batch_execution_log(execution_id);
CREATE INDEX idx_batch_execution_log_level ON batch_execution_log(log_level);
CREATE INDEX idx_batch_execution_log_logged_at ON batch_execution_log(logged_at);

COMMENT ON TABLE batch_execution_log IS '배치 실행 중 발생하는 상세 로그';
COMMENT ON COLUMN batch_execution_log.log_category IS 'INP/EXT/BAT/DQ/LOG/SYS (장애 분류)';
COMMENT ON COLUMN batch_execution_log.log_code IS 'C1-XXX-NNN 형식 오류 코드';

-- -----------------------------------------------------------------------------
-- 4. 감사 추적 테이블 (Audit Trail)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ops_audit_log (
    audit_id BIGSERIAL PRIMARY KEY,
    audit_type VARCHAR(30) NOT NULL,  -- 'BATCH_START', 'BATCH_STOP', 'BATCH_REPLAY', 'DATA_CORRECTION', 'CONFIG_CHANGE'
    target_type VARCHAR(30) NOT NULL,  -- 'BATCH_EXECUTION', 'PORTFOLIO', 'SIMULATION', etc.
    target_id VARCHAR(100) NOT NULL,  -- 대상 레코드 ID

    -- 변경 내용
    action VARCHAR(30) NOT NULL,  -- 'CREATE', 'UPDATE', 'DEACTIVATE', 'REPLAY'
    before_state JSONB,  -- 변경 전 상태
    after_state JSONB,  -- 변경 후 상태

    -- 운영자 정보
    operator_id VARCHAR(50) NOT NULL,
    operator_ip VARCHAR(45),
    operator_reason TEXT NOT NULL,  -- 필수: 수행 사유

    -- 승인 정보 (필요시)
    approved_by VARCHAR(50),
    approved_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ops_audit_log_audit_type ON ops_audit_log(audit_type);
CREATE INDEX idx_ops_audit_log_target ON ops_audit_log(target_type, target_id);
CREATE INDEX idx_ops_audit_log_operator ON ops_audit_log(operator_id);
CREATE INDEX idx_ops_audit_log_created_at ON ops_audit_log(created_at);

COMMENT ON TABLE ops_audit_log IS '운영 감사 추적 로그 (삭제 금지)';
COMMENT ON COLUMN ops_audit_log.operator_reason IS '필수: 모든 수동 개입은 사유 기록';

-- -----------------------------------------------------------------------------
-- 5. 결과 데이터 버전 관리 테이블 (Result Version Control)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS result_version (
    version_id BIGSERIAL PRIMARY KEY,
    result_type VARCHAR(30) NOT NULL,  -- 'SIMULATION', 'PERFORMANCE', 'EXPLANATION'
    result_id VARCHAR(100) NOT NULL,  -- 원본 결과 ID
    execution_id UUID REFERENCES batch_execution(execution_id),

    -- 버전 상태
    version_no INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- 비활성화 정보
    deactivated_at TIMESTAMP,
    deactivated_by VARCHAR(50),
    deactivate_reason TEXT,
    superseded_by BIGINT REFERENCES result_version(version_id),  -- 대체된 버전

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_result_version_active ON result_version(result_type, result_id) WHERE is_active = TRUE;
CREATE INDEX idx_result_version_execution ON result_version(execution_id);

COMMENT ON TABLE result_version IS '결과 데이터 버전 관리 (덮어쓰기 방지)';
COMMENT ON COLUMN result_version.is_active IS 'TRUE=현재 유효 버전, FALSE=이전 버전';

-- -----------------------------------------------------------------------------
-- 6. 운영 알림 이력 테이블 (Alert History)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ops_alert (
    alert_id BIGSERIAL PRIMARY KEY,
    alert_type VARCHAR(30) NOT NULL,  -- 'BATCH_FAILED', 'REPLAY_EXECUTED', 'MANUAL_STOP'
    alert_level VARCHAR(10) NOT NULL,  -- 'INFO', 'WARN', 'ERROR', 'CRITICAL'

    -- 알림 대상
    execution_id UUID REFERENCES batch_execution(execution_id),
    related_error_code VARCHAR(20),

    -- 알림 내용
    alert_title VARCHAR(200) NOT NULL,
    alert_message TEXT NOT NULL,
    alert_detail JSONB,

    -- 발송 정보
    channels_sent JSONB,  -- ['email', 'slack']
    sent_at TIMESTAMP,

    -- 확인 정보
    acknowledged_by VARCHAR(50),
    acknowledged_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ops_alert_type ON ops_alert(alert_type);
CREATE INDEX idx_ops_alert_level ON ops_alert(alert_level);
CREATE INDEX idx_ops_alert_created_at ON ops_alert(created_at);

COMMENT ON TABLE ops_alert IS '운영 알림 발송 이력';

-- -----------------------------------------------------------------------------
-- 7. 오류 코드 마스터 테이블 (Error Code Master)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS error_code_master (
    error_code VARCHAR(20) PRIMARY KEY,  -- 'C1-INP-001'
    category VARCHAR(10) NOT NULL,  -- 'INP', 'EXT', 'BAT', 'DQ', 'LOG', 'SYS'
    severity VARCHAR(10) NOT NULL,  -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'

    -- 메시지
    user_message VARCHAR(200) NOT NULL,  -- 사용자 노출용
    ops_message VARCHAR(500) NOT NULL,  -- 운영자용 (원인 포함)
    action_guide TEXT,  -- 조치 가이드

    -- 알림 설정
    auto_alert BOOLEAN DEFAULT FALSE,
    alert_level VARCHAR(10),

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE error_code_master IS '오류 코드 마스터 (C1-XXX-NNN 체계)';

-- -----------------------------------------------------------------------------
-- 8. 초기 데이터: 오류 코드 마스터
-- -----------------------------------------------------------------------------
INSERT INTO error_code_master (error_code, category, severity, user_message, ops_message, action_guide, auto_alert, alert_level) VALUES
-- 입력 데이터 오류 (INP)
('C1-INP-001', 'INP', 'MEDIUM', '데이터 처리 중 오류가 발생했습니다.', '입력 데이터 누락: 필수 필드가 NULL', '원천 데이터 확인 후 재처리 필요', TRUE, 'WARN'),
('C1-INP-002', 'INP', 'MEDIUM', '데이터 처리 중 오류가 발생했습니다.', '입력 데이터 포맷 오류: 날짜/숫자 형식 불일치', '데이터 포맷 검증 후 재처리', TRUE, 'WARN'),
('C1-INP-003', 'INP', 'LOW', '데이터 처리 중 오류가 발생했습니다.', '입력 데이터 범위 오류: 값이 허용 범위 초과', '데이터 정합성 확인', FALSE, 'INFO'),

-- 외부 연동 오류 (EXT)
('C1-EXT-001', 'EXT', 'HIGH', '일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.', '외부 API 연결 실패: 타임아웃', 'API 상태 확인 후 재시도', TRUE, 'ERROR'),
('C1-EXT-002', 'EXT', 'HIGH', '일시적인 오류가 발생했습니다.', '외부 API 응답 오류: HTTP 5xx', 'API 서버 상태 확인', TRUE, 'ERROR'),
('C1-EXT-003', 'EXT', 'MEDIUM', '데이터 수신 지연이 발생했습니다.', '시세 데이터 수신 지연', '데이터 제공사 확인', TRUE, 'WARN'),

-- 배치 실행 오류 (BAT)
('C1-BAT-001', 'BAT', 'HIGH', '처리 중 오류가 발생했습니다.', '배치 실행 중 예외 발생', '로그 확인 후 원인 분석', TRUE, 'ERROR'),
('C1-BAT-002', 'BAT', 'MEDIUM', '처리가 중단되었습니다.', '배치 실행 수동 중단', '운영자 중단 사유 확인', TRUE, 'WARN'),
('C1-BAT-003', 'BAT', 'HIGH', '처리 시간이 초과되었습니다.', '배치 실행 시간 초과', '처리량 확인 및 분할 실행 검토', TRUE, 'ERROR'),

-- 데이터 무결성 오류 (DQ)
('C1-DQ-001', 'DQ', 'HIGH', '데이터 검증 중 오류가 발생했습니다.', '데이터 정합성 위반: 중복 레코드', '중복 데이터 정리 후 재처리', TRUE, 'ERROR'),
('C1-DQ-002', 'DQ', 'HIGH', '데이터 검증 중 오류가 발생했습니다.', '데이터 정합성 위반: 참조 무결성 오류', '관련 데이터 확인', TRUE, 'ERROR'),
('C1-DQ-003', 'DQ', 'MEDIUM', '데이터 검증 중 오류가 발생했습니다.', '데이터 누락: 필수 기간 데이터 없음', '누락 기간 데이터 적재 필요', TRUE, 'WARN'),

-- 로직 오류 (LOG)
('C1-LOG-001', 'LOG', 'CRITICAL', '시스템 오류가 발생했습니다.', '계산 로직 오류: 산식 결과 이상', '로직 검토 및 수정 필요', TRUE, 'CRITICAL'),
('C1-LOG-002', 'LOG', 'HIGH', '시스템 오류가 발생했습니다.', '분기 로직 오류: 예상치 못한 조건', '로직 검토 필요', TRUE, 'ERROR'),

-- 시스템 오류 (SYS)
('C1-SYS-001', 'SYS', 'CRITICAL', '시스템 점검 중입니다.', 'DB 연결 실패', 'DB 서버 상태 확인', TRUE, 'CRITICAL'),
('C1-SYS-002', 'SYS', 'CRITICAL', '시스템 점검 중입니다.', '서버 리소스 부족: 메모리/디스크', '서버 리소스 확인', TRUE, 'CRITICAL'),
('C1-SYS-003', 'SYS', 'HIGH', '시스템 오류가 발생했습니다.', '파일 I/O 오류', '파일 시스템 확인', TRUE, 'ERROR')

ON CONFLICT (error_code) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 9. 초기 데이터: 배치 작업 마스터
-- -----------------------------------------------------------------------------
INSERT INTO batch_job (job_id, job_name, job_description, job_type) VALUES
('DAILY_PRICE_LOAD', '일간 시세 적재', '일봉 시세 데이터 수집 및 적재', 'DAILY'),
('DAILY_RETURN_CALC', '일간 수익률 계산', '일간 수익률 계산 및 저장', 'DAILY'),
('DAILY_SIMULATION', '일간 시뮬레이션', '포트폴리오 시뮬레이션 실행', 'DAILY'),
('DAILY_EXPLANATION', '일간 설명 생성', 'Phase A 설명 자동 생성', 'DAILY'),
('MONTHLY_REPORT', '월간 리포트', '월간 성과 리포트 생성', 'MONTHLY'),
('ON_DEMAND_REPLAY', '수동 재처리', '운영자 수동 재처리 작업', 'ON_DEMAND')

ON CONFLICT (job_id) DO NOTHING;
