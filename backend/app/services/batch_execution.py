"""
Phase 3-C / Epic C-1: 배치 실행 상태 관리 서비스
생성일: 2026-01-18
목적: 배치 실행의 전체 라이프사이클 관리
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from sqlalchemy.orm import Session

from app.models.ops import BatchJob, BatchExecution, BatchExecutionLog


class RunType(str, Enum):
    """실행 유형"""
    AUTO = "AUTO"
    MANUAL = "MANUAL"
    REPLAY = "REPLAY"


class ExecutionStatus(str, Enum):
    """실행 상태"""
    READY = "READY"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    STOPPED = "STOPPED"


# 허용되는 상태 전이 정의
VALID_TRANSITIONS = {
    ExecutionStatus.READY: [ExecutionStatus.RUNNING],
    ExecutionStatus.RUNNING: [ExecutionStatus.SUCCESS, ExecutionStatus.FAILED, ExecutionStatus.STOPPED],
    ExecutionStatus.SUCCESS: [],  # 최종 상태
    ExecutionStatus.FAILED: [],   # 최종 상태
    ExecutionStatus.STOPPED: [],  # 최종 상태
}


class BatchExecutionError(Exception):
    """배치 실행 관련 예외"""
    def __init__(self, message: str, error_code: str = "C1-BAT-001"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class DuplicateExecutionError(BatchExecutionError):
    """중복 실행 예외"""
    def __init__(self, execution_id: str):
        super().__init__(
            f"Execution ID {execution_id} already exists",
            error_code="C1-BAT-004"
        )


class InvalidStateTransitionError(BatchExecutionError):
    """잘못된 상태 전이 예외"""
    def __init__(self, current: str, target: str):
        super().__init__(
            f"Invalid state transition: {current} -> {target}",
            error_code="C1-BAT-005"
        )


class BatchExecutionService:
    """배치 실행 상태 관리 서비스"""

    def __init__(self, db: Session):
        self.db = db

    def _validate_job_exists(self, job_id: str) -> BatchJob:
        """Job ID 존재 확인"""
        job = self.db.query(BatchJob).filter_by(job_id=job_id).first()
        if not job:
            raise BatchExecutionError(f"Job not found: {job_id}", "C1-BAT-006")
        if not job.is_active:
            raise BatchExecutionError(f"Job is inactive: {job_id}", "C1-BAT-007")
        return job

    def _validate_state_transition(
        self,
        current: ExecutionStatus,
        target: ExecutionStatus
    ) -> bool:
        """상태 전이 유효성 검증"""
        valid_targets = VALID_TRANSITIONS.get(current, [])
        if target not in valid_targets:
            raise InvalidStateTransitionError(current.value, target.value)
        return True

    def start_execution(
        self,
        job_id: str,
        run_type: RunType = RunType.AUTO,
        target_date: Optional[datetime] = None,
        target_start_date: Optional[datetime] = None,
        target_end_date: Optional[datetime] = None,
        operator_id: Optional[str] = None,
        operator_note: Optional[str] = None,
        parent_execution_id: Optional[str] = None,
        replay_reason: Optional[str] = None,
        execution_id: Optional[str] = None,
    ) -> BatchExecution:
        """
        배치 실행 시작 기록

        Args:
            job_id: 배치 작업 ID
            run_type: 실행 유형 (AUTO/MANUAL/REPLAY)
            target_date: 처리 대상 기준일
            target_start_date: 구간 처리 시작일
            target_end_date: 구간 처리 종료일
            operator_id: 운영자 ID (수동 실행 시 필수)
            operator_note: 운영자 메모
            parent_execution_id: 재처리 시 원본 실행 ID
            replay_reason: 재처리 사유
            execution_id: 지정 실행 ID (멱등성 보장)

        Returns:
            BatchExecution: 생성된 실행 레코드
        """
        # Job 유효성 확인
        self._validate_job_exists(job_id)

        # 수동 실행 시 operator_id 필수
        if run_type in [RunType.MANUAL, RunType.REPLAY] and not operator_id:
            raise BatchExecutionError(
                "operator_id is required for MANUAL/REPLAY execution",
                "C1-BAT-008"
            )

        # 재처리 시 replay_reason 필수
        if run_type == RunType.REPLAY and not replay_reason:
            raise BatchExecutionError(
                "replay_reason is required for REPLAY execution",
                "C1-BAT-009"
            )

        # 멱등성: execution_id가 지정된 경우 중복 확인
        if execution_id:
            existing = self.db.query(BatchExecution).filter_by(
                execution_id=execution_id
            ).first()
            if existing:
                raise DuplicateExecutionError(execution_id)

        # 실행 레코드 생성
        execution = BatchExecution(
            job_id=job_id,
            run_type=run_type.value,
            status=ExecutionStatus.READY.value,
            scheduled_at=datetime.utcnow(),
            target_date=target_date,
            target_start_date=target_start_date,
            target_end_date=target_end_date,
            operator_id=operator_id,
            operator_note=operator_note,
            parent_execution_id=parent_execution_id,
            replay_reason=replay_reason,
        )

        if execution_id:
            execution.execution_id = execution_id

        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)

        # 상태를 RUNNING으로 전이
        self._transition_to_running(execution)

        return execution

    def _transition_to_running(self, execution: BatchExecution) -> None:
        """READY -> RUNNING 상태 전이"""
        self._validate_state_transition(
            ExecutionStatus(execution.status),
            ExecutionStatus.RUNNING
        )
        execution.status = ExecutionStatus.RUNNING.value
        execution.started_at = datetime.utcnow()
        execution.updated_at = datetime.utcnow()
        self.db.commit()

    def update_progress(
        self,
        execution_id: str,
        processed_count: int,
        success_count: int,
        failed_count: int,
    ) -> BatchExecution:
        """
        진행 상황 업데이트

        Args:
            execution_id: 실행 ID
            processed_count: 처리된 건수
            success_count: 성공 건수
            failed_count: 실패 건수

        Returns:
            BatchExecution: 업데이트된 실행 레코드
        """
        execution = self._get_execution(execution_id)

        if execution.status != ExecutionStatus.RUNNING.value:
            raise BatchExecutionError(
                f"Cannot update progress for non-running execution: {execution.status}",
                "C1-BAT-010"
            )

        execution.processed_count = processed_count
        execution.success_count = success_count
        execution.failed_count = failed_count
        execution.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(execution)

        return execution

    def complete_execution(
        self,
        execution_id: str,
        processed_count: Optional[int] = None,
        success_count: Optional[int] = None,
    ) -> BatchExecution:
        """
        성공 완료 기록

        Args:
            execution_id: 실행 ID
            processed_count: 최종 처리 건수
            success_count: 최종 성공 건수

        Returns:
            BatchExecution: 완료된 실행 레코드
        """
        execution = self._get_execution(execution_id)

        self._validate_state_transition(
            ExecutionStatus(execution.status),
            ExecutionStatus.SUCCESS
        )

        execution.status = ExecutionStatus.SUCCESS.value
        execution.ended_at = datetime.utcnow()
        execution.updated_at = datetime.utcnow()

        if processed_count is not None:
            execution.processed_count = processed_count
        if success_count is not None:
            execution.success_count = success_count

        self.db.commit()
        self.db.refresh(execution)

        return execution

    def fail_execution(
        self,
        execution_id: str,
        error_code: str,
        error_message: str,
        error_detail: Optional[Dict[str, Any]] = None,
    ) -> BatchExecution:
        """
        실패 기록

        Args:
            execution_id: 실행 ID
            error_code: 오류 코드 (C1-XXX-NNN)
            error_message: 오류 메시지
            error_detail: 오류 상세 정보 (JSON)

        Returns:
            BatchExecution: 실패 처리된 실행 레코드
        """
        execution = self._get_execution(execution_id)

        self._validate_state_transition(
            ExecutionStatus(execution.status),
            ExecutionStatus.FAILED
        )

        execution.status = ExecutionStatus.FAILED.value
        execution.ended_at = datetime.utcnow()
        execution.updated_at = datetime.utcnow()
        execution.error_code = error_code
        execution.error_message = error_message
        execution.error_detail = error_detail

        self.db.commit()
        self.db.refresh(execution)

        # 실패 로그 기록
        self.add_log(
            execution_id=execution_id,
            log_level="ERROR",
            log_category=error_code.split("-")[1] if "-" in error_code else "SYS",
            log_code=error_code,
            log_message=error_message,
            log_detail=error_detail,
        )

        return execution

    def stop_execution(
        self,
        execution_id: str,
        operator_id: str,
        reason: str,
    ) -> BatchExecution:
        """
        수동 중단 기록

        Args:
            execution_id: 실행 ID
            operator_id: 중단 요청 운영자 ID
            reason: 중단 사유

        Returns:
            BatchExecution: 중단된 실행 레코드
        """
        if not operator_id:
            raise BatchExecutionError(
                "operator_id is required for stop_execution",
                "C1-BAT-011"
            )
        if not reason:
            raise BatchExecutionError(
                "reason is required for stop_execution",
                "C1-BAT-012"
            )

        execution = self._get_execution(execution_id)

        self._validate_state_transition(
            ExecutionStatus(execution.status),
            ExecutionStatus.STOPPED
        )

        execution.status = ExecutionStatus.STOPPED.value
        execution.ended_at = datetime.utcnow()
        execution.updated_at = datetime.utcnow()
        execution.error_code = "C1-BAT-002"
        execution.error_message = f"Stopped by {operator_id}: {reason}"

        self.db.commit()
        self.db.refresh(execution)

        # 중단 로그 기록
        self.add_log(
            execution_id=execution_id,
            log_level="WARN",
            log_category="BAT",
            log_code="C1-BAT-002",
            log_message=f"Execution stopped by {operator_id}",
            log_detail={"operator_id": operator_id, "reason": reason},
        )

        return execution

    def _get_execution(self, execution_id: str) -> BatchExecution:
        """실행 레코드 조회"""
        execution = self.db.query(BatchExecution).filter_by(
            execution_id=execution_id
        ).first()
        if not execution:
            raise BatchExecutionError(
                f"Execution not found: {execution_id}",
                "C1-BAT-013"
            )
        return execution

    def get_execution(self, execution_id: str) -> Optional[BatchExecution]:
        """실행 레코드 조회 (public)"""
        return self.db.query(BatchExecution).filter_by(
            execution_id=execution_id
        ).first()

    def get_executions_by_job(
        self,
        job_id: str,
        status: Optional[ExecutionStatus] = None,
        limit: int = 100,
    ) -> List[BatchExecution]:
        """Job별 실행 이력 조회"""
        query = self.db.query(BatchExecution).filter_by(job_id=job_id)
        if status:
            query = query.filter_by(status=status.value)
        return query.order_by(BatchExecution.started_at.desc()).limit(limit).all()

    def get_running_executions(self) -> List[BatchExecution]:
        """현재 실행 중인 배치 조회"""
        return self.db.query(BatchExecution).filter_by(
            status=ExecutionStatus.RUNNING.value
        ).all()

    def add_log(
        self,
        execution_id: str,
        log_level: str,
        log_message: str,
        log_category: Optional[str] = None,
        log_code: Optional[str] = None,
        log_detail: Optional[Dict[str, Any]] = None,
    ) -> BatchExecutionLog:
        """실행 로그 추가"""
        log = BatchExecutionLog(
            execution_id=execution_id,
            log_level=log_level,
            log_category=log_category,
            log_code=log_code,
            log_message=log_message,
            log_detail=log_detail,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_logs(
        self,
        execution_id: str,
        log_level: Optional[str] = None,
    ) -> List[BatchExecutionLog]:
        """실행 로그 조회"""
        query = self.db.query(BatchExecutionLog).filter_by(execution_id=execution_id)
        if log_level:
            query = query.filter_by(log_level=log_level)
        return query.order_by(BatchExecutionLog.logged_at.asc()).all()
