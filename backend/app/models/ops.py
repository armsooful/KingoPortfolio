"""
Phase 3-C / Epic C-1: 운영 안정성 ORM 모델
생성일: 2026-01-18
목적: 배치 실행 상태 관리, 재처리 이력, 감사 로그
"""

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, ForeignKey,
    Index, UniqueConstraint, JSON
)
from sqlalchemy.orm import relationship
import uuid

from app.database import Base
from app.utils.kst_now import kst_now


def generate_uuid():
    """UUID 문자열 생성"""
    return str(uuid.uuid4())


class BatchJob(Base):
    """배치 작업 마스터 정의"""
    __tablename__ = "batch_job"

    job_id = Column(String(50), primary_key=True)
    job_name = Column(String(100), nullable=False)
    job_description = Column(Text, nullable=True)
    job_type = Column(String(20), nullable=False)  # 'DAILY', 'WEEKLY', 'MONTHLY', 'ON_DEMAND'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=kst_now)
    updated_at = Column(DateTime, default=kst_now, onupdate=kst_now)

    # 관계
    executions = relationship("BatchExecution", back_populates="job")

    def __repr__(self):
        return f"<BatchJob {self.job_id}: {self.job_name}>"


class BatchExecution(Base):
    """배치 실행 이력 (모든 실행의 상태 추적)"""
    __tablename__ = "batch_execution"

    execution_id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(50), ForeignKey("batch_job.job_id"), nullable=False)
    run_type = Column(String(20), nullable=False)  # 'AUTO', 'MANUAL', 'REPLAY'
    status = Column(String(20), nullable=False, default='READY')  # 'READY', 'RUNNING', 'SUCCESS', 'FAILED', 'STOPPED'

    # 실행 시간 정보
    scheduled_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)

    # 처리 범위
    target_date = Column(DateTime, nullable=True)  # 처리 대상 기준일
    target_start_date = Column(DateTime, nullable=True)  # 구간 처리 시 시작일
    target_end_date = Column(DateTime, nullable=True)  # 구간 처리 시 종료일

    # 처리 결과
    processed_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)

    # 오류 정보
    error_code = Column(String(20), nullable=True)
    error_message = Column(Text, nullable=True)
    error_detail = Column(JSON, nullable=True)

    # 운영자 정보
    operator_id = Column(String(50), nullable=True)  # 수동 실행 시 운영자 ID
    operator_note = Column(Text, nullable=True)  # 수동 실행 사유

    # 재처리 연관
    parent_execution_id = Column(String(36), ForeignKey("batch_execution.execution_id"), nullable=True)
    replay_reason = Column(Text, nullable=True)  # 재처리 사유

    # 메타
    created_at = Column(DateTime, default=kst_now)
    updated_at = Column(DateTime, default=kst_now, onupdate=kst_now)

    # 관계
    job = relationship("BatchJob", back_populates="executions")
    logs = relationship("BatchExecutionLog", back_populates="execution")
    parent_execution = relationship("BatchExecution", remote_side=[execution_id], backref="child_executions")

    __table_args__ = (
        Index('idx_batch_execution_job_id', 'job_id'),
        Index('idx_batch_execution_status', 'status'),
        Index('idx_batch_execution_target_date', 'target_date'),
        Index('idx_batch_execution_started_at', 'started_at'),
    )

    def __repr__(self):
        return f"<BatchExecution {self.execution_id[:8]}... [{self.status}]>"


class BatchExecutionLog(Base):
    """배치 실행 중 발생하는 상세 로그"""
    __tablename__ = "batch_execution_log"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String(36), ForeignKey("batch_execution.execution_id"), nullable=False)
    log_level = Column(String(10), nullable=False)  # 'INFO', 'WARN', 'ERROR'
    log_category = Column(String(20), nullable=True)  # 'INP', 'EXT', 'BAT', 'DQ', 'LOG', 'SYS'
    log_code = Column(String(20), nullable=True)  # 'C1-INP-001' 형식
    log_message = Column(Text, nullable=False)
    log_detail = Column(JSON, nullable=True)
    logged_at = Column(DateTime, default=kst_now)

    # 관계
    execution = relationship("BatchExecution", back_populates="logs")

    __table_args__ = (
        Index('idx_batch_execution_log_execution_id', 'execution_id'),
        Index('idx_batch_execution_log_level', 'log_level'),
        Index('idx_batch_execution_log_logged_at', 'logged_at'),
    )

    def __repr__(self):
        return f"<BatchExecutionLog [{self.log_level}] {self.log_message[:30]}...>"


class OpsAuditLog(Base):
    """운영 감사 추적 로그 (삭제 금지)"""
    __tablename__ = "ops_audit_log"

    audit_id = Column(Integer, primary_key=True, autoincrement=True)
    audit_type = Column(String(30), nullable=False)  # 'BATCH_START', 'BATCH_STOP', 'BATCH_REPLAY', 'DATA_CORRECTION', 'CONFIG_CHANGE'
    target_type = Column(String(30), nullable=False)  # 'BATCH_EXECUTION', 'PORTFOLIO', 'SIMULATION', etc.
    target_id = Column(String(100), nullable=False)  # 대상 레코드 ID

    # 변경 내용
    action = Column(String(30), nullable=False)  # 'CREATE', 'UPDATE', 'DEACTIVATE', 'REPLAY'
    before_state = Column(JSON, nullable=True)  # 변경 전 상태
    after_state = Column(JSON, nullable=True)  # 변경 후 상태

    # 운영자 정보
    operator_id = Column(String(50), nullable=False)
    operator_ip = Column(String(45), nullable=True)
    operator_reason = Column(Text, nullable=False)  # 필수: 수행 사유

    # 승인 정보 (필요시)
    approved_by = Column(String(50), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=kst_now)

    __table_args__ = (
        Index('idx_ops_audit_log_audit_type', 'audit_type'),
        Index('idx_ops_audit_log_target', 'target_type', 'target_id'),
        Index('idx_ops_audit_log_operator', 'operator_id'),
        Index('idx_ops_audit_log_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<OpsAuditLog [{self.audit_type}] {self.target_type}/{self.target_id}>"


class ResultVersion(Base):
    """결과 데이터 버전 관리 (덮어쓰기 방지)"""
    __tablename__ = "result_version"

    version_id = Column(Integer, primary_key=True, autoincrement=True)
    result_type = Column(String(30), nullable=False)  # 'SIMULATION', 'PERFORMANCE', 'EXPLANATION'
    result_id = Column(String(100), nullable=False)  # 원본 결과 ID
    execution_id = Column(String(36), ForeignKey("batch_execution.execution_id"), nullable=True)

    # 버전 상태
    version_no = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)

    # 비활성화 정보
    deactivated_at = Column(DateTime, nullable=True)
    deactivated_by = Column(String(50), nullable=True)
    deactivate_reason = Column(Text, nullable=True)
    superseded_by = Column(Integer, ForeignKey("result_version.version_id"), nullable=True)

    created_at = Column(DateTime, default=kst_now)

    # 관계
    superseding_version = relationship("ResultVersion", remote_side=[version_id], backref="previous_versions")

    __table_args__ = (
        # SQLite doesn't support partial unique index, handle in application layer
        Index('idx_result_version_execution', 'execution_id'),
        Index('idx_result_version_active', 'result_type', 'result_id', 'is_active'),
    )

    def __repr__(self):
        return f"<ResultVersion {self.result_type}/{self.result_id} v{self.version_no} active={self.is_active}>"


class OpsAlert(Base):
    """운영 알림 발송 이력"""
    __tablename__ = "ops_alert"

    alert_id = Column(Integer, primary_key=True, autoincrement=True)
    alert_type = Column(String(30), nullable=False)  # 'BATCH_FAILED', 'REPLAY_EXECUTED', 'MANUAL_STOP'
    alert_level = Column(String(10), nullable=False)  # 'INFO', 'WARN', 'ERROR', 'CRITICAL'

    # 알림 대상
    execution_id = Column(String(36), ForeignKey("batch_execution.execution_id"), nullable=True)
    related_error_code = Column(String(20), nullable=True)

    # 알림 내용
    alert_title = Column(String(200), nullable=False)
    alert_message = Column(Text, nullable=False)
    alert_detail = Column(JSON, nullable=True)

    # 발송 정보
    channels_sent = Column(JSON, nullable=True)  # ['email', 'slack']
    sent_at = Column(DateTime, nullable=True)

    # 확인 정보
    acknowledged_by = Column(String(50), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=kst_now)

    __table_args__ = (
        Index('idx_ops_alert_type', 'alert_type'),
        Index('idx_ops_alert_level', 'alert_level'),
        Index('idx_ops_alert_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<OpsAlert [{self.alert_level}] {self.alert_title[:30]}...>"


class ErrorCodeMaster(Base):
    """오류 코드 마스터 (C1-XXX-NNN 체계)"""
    __tablename__ = "error_code_master"

    error_code = Column(String(20), primary_key=True)  # 'C1-INP-001'
    category = Column(String(10), nullable=False)  # 'INP', 'EXT', 'BAT', 'DQ', 'LOG', 'SYS'
    severity = Column(String(10), nullable=False)  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'

    # 메시지
    user_message = Column(String(200), nullable=False)  # 사용자 노출용
    ops_message = Column(String(500), nullable=False)  # 운영자용 (원인 포함)
    action_guide = Column(Text, nullable=True)  # 조치 가이드

    # 알림 설정
    auto_alert = Column(Boolean, default=False)
    alert_level = Column(String(10), nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=kst_now)
    updated_at = Column(DateTime, default=kst_now, onupdate=kst_now)

    def __repr__(self):
        return f"<ErrorCodeMaster {self.error_code}: {self.ops_message[:30]}...>"