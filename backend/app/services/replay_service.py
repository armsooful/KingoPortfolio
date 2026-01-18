"""
Phase 3-C / Epic C-1: 재처리(Replay) 서비스
생성일: 2026-01-18
목적: 과거 배치 결과를 안전하게 재처리
"""

from datetime import datetime, date
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from sqlalchemy.orm import Session

from app.models.ops import BatchExecution, ResultVersion
from app.services.batch_execution import (
    BatchExecutionService,
    RunType,
    ExecutionStatus,
    BatchExecutionError,
)
from app.services.audit_log_service import (
    AuditLogService,
    AuditType,
    AuditAction,
    TargetType,
)


class ReplayType(str, Enum):
    """재처리 유형"""
    FULL = "FULL"           # 전체 재처리
    RANGE = "RANGE"         # 구간 재처리
    SINGLE = "SINGLE"       # 단건 재처리


class ReplayError(Exception):
    """재처리 관련 예외"""
    def __init__(self, message: str, error_code: str = "C1-BAT-020"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class InvalidReplayTargetError(ReplayError):
    """유효하지 않은 재처리 대상"""
    def __init__(self, execution_id: str, reason: str):
        super().__init__(
            f"Invalid replay target {execution_id}: {reason}",
            error_code="C1-BAT-021"
        )


class ReplayInProgressError(ReplayError):
    """이미 재처리 진행 중"""
    def __init__(self, job_id: str):
        super().__init__(
            f"Replay already in progress for job {job_id}",
            error_code="C1-BAT-022"
        )


class ReplayService:
    """재처리 서비스"""

    def __init__(self, db: Session):
        self.db = db
        self.batch_service = BatchExecutionService(db)
        self.audit_service = AuditLogService(db)

    def _validate_replay_target(
        self,
        parent_execution_id: str
    ) -> BatchExecution:
        """재처리 대상 유효성 검증"""
        parent = self.batch_service.get_execution(parent_execution_id)

        if not parent:
            raise InvalidReplayTargetError(
                parent_execution_id,
                "Execution not found"
            )

        # 완료된 실행만 재처리 가능
        if parent.status not in [
            ExecutionStatus.SUCCESS.value,
            ExecutionStatus.FAILED.value,
        ]:
            raise InvalidReplayTargetError(
                parent_execution_id,
                f"Cannot replay execution with status {parent.status}"
            )

        return parent

    def _check_no_running_replay(self, job_id: str) -> None:
        """동일 Job에 대해 진행 중인 재처리가 없는지 확인"""
        running = self.db.query(BatchExecution).filter(
            BatchExecution.job_id == job_id,
            BatchExecution.run_type == RunType.REPLAY.value,
            BatchExecution.status == ExecutionStatus.RUNNING.value,
        ).first()

        if running:
            raise ReplayInProgressError(job_id)

    def replay_full(
        self,
        job_id: str,
        target_date: date,
        operator_id: str,
        replay_reason: str,
        parent_execution_id: Optional[str] = None,
        processor: Optional[Callable] = None,
    ) -> BatchExecution:
        """
        전체 재처리

        Args:
            job_id: 배치 작업 ID
            target_date: 처리 대상 기준일
            operator_id: 운영자 ID (필수)
            replay_reason: 재처리 사유 (필수)
            parent_execution_id: 원본 실행 ID (선택)
            processor: 실제 처리 함수 (선택)

        Returns:
            BatchExecution: 재처리 실행 레코드
        """
        if not operator_id:
            raise ReplayError("operator_id is required", "C1-BAT-023")
        if not replay_reason:
            raise ReplayError("replay_reason is required", "C1-BAT-024")

        # 원본 실행 검증 (지정된 경우)
        if parent_execution_id:
            self._validate_replay_target(parent_execution_id)

        # 진행 중인 재처리 확인
        self._check_no_running_replay(job_id)

        # 기존 결과 비활성화
        self._deactivate_existing_results(
            job_id=job_id,
            target_date=target_date,
            operator_id=operator_id,
            reason=replay_reason,
        )

        # 재처리 실행 시작
        execution = self.batch_service.start_execution(
            job_id=job_id,
            run_type=RunType.REPLAY,
            target_date=datetime.combine(target_date, datetime.min.time()),
            operator_id=operator_id,
            operator_note=f"Full replay: {replay_reason}",
            parent_execution_id=parent_execution_id,
            replay_reason=replay_reason,
        )

        # 감사 로그 기록
        self.audit_service.log_batch_action(
            audit_type=AuditType.BATCH_REPLAY,
            execution_id=execution.execution_id,
            action=AuditAction.REPLAY,
            operator_id=operator_id,
            operator_reason=replay_reason,
            after_state={
                "replay_type": ReplayType.FULL.value,
                "target_date": str(target_date),
                "parent_execution_id": parent_execution_id,
            },
        )

        # 실제 처리 수행 (processor가 제공된 경우)
        if processor:
            try:
                result = processor(execution)
                self.batch_service.complete_execution(
                    execution_id=execution.execution_id,
                    processed_count=result.get('processed', 0),
                    success_count=result.get('success', 0),
                )
            except Exception as e:
                self.batch_service.fail_execution(
                    execution_id=execution.execution_id,
                    error_code="C1-BAT-001",
                    error_message=str(e),
                )
                raise

        return execution

    def replay_range(
        self,
        job_id: str,
        start_date: date,
        end_date: date,
        operator_id: str,
        replay_reason: str,
        parent_execution_id: Optional[str] = None,
        processor: Optional[Callable] = None,
    ) -> BatchExecution:
        """
        구간 재처리

        Args:
            job_id: 배치 작업 ID
            start_date: 시작일
            end_date: 종료일
            operator_id: 운영자 ID (필수)
            replay_reason: 재처리 사유 (필수)
            parent_execution_id: 원본 실행 ID (선택)
            processor: 실제 처리 함수 (선택)

        Returns:
            BatchExecution: 재처리 실행 레코드
        """
        if not operator_id:
            raise ReplayError("operator_id is required", "C1-BAT-023")
        if not replay_reason:
            raise ReplayError("replay_reason is required", "C1-BAT-024")

        if start_date > end_date:
            raise ReplayError(
                f"Invalid date range: {start_date} > {end_date}",
                "C1-BAT-025"
            )

        # 원본 실행 검증 (지정된 경우)
        if parent_execution_id:
            self._validate_replay_target(parent_execution_id)

        # 진행 중인 재처리 확인
        self._check_no_running_replay(job_id)

        # 기존 결과 비활성화 (구간)
        self._deactivate_existing_results_range(
            job_id=job_id,
            start_date=start_date,
            end_date=end_date,
            operator_id=operator_id,
            reason=replay_reason,
        )

        # 재처리 실행 시작
        execution = self.batch_service.start_execution(
            job_id=job_id,
            run_type=RunType.REPLAY,
            target_start_date=datetime.combine(start_date, datetime.min.time()),
            target_end_date=datetime.combine(end_date, datetime.min.time()),
            operator_id=operator_id,
            operator_note=f"Range replay ({start_date} ~ {end_date}): {replay_reason}",
            parent_execution_id=parent_execution_id,
            replay_reason=replay_reason,
        )

        # 감사 로그 기록
        self.audit_service.log_batch_action(
            audit_type=AuditType.BATCH_REPLAY,
            execution_id=execution.execution_id,
            action=AuditAction.REPLAY,
            operator_id=operator_id,
            operator_reason=replay_reason,
            after_state={
                "replay_type": ReplayType.RANGE.value,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "parent_execution_id": parent_execution_id,
            },
        )

        # 실제 처리 수행
        if processor:
            try:
                result = processor(execution)
                self.batch_service.complete_execution(
                    execution_id=execution.execution_id,
                    processed_count=result.get('processed', 0),
                    success_count=result.get('success', 0),
                )
            except Exception as e:
                self.batch_service.fail_execution(
                    execution_id=execution.execution_id,
                    error_code="C1-BAT-001",
                    error_message=str(e),
                )
                raise

        return execution

    def replay_single(
        self,
        job_id: str,
        target_id: str,
        target_type: str,
        operator_id: str,
        replay_reason: str,
        parent_execution_id: Optional[str] = None,
        processor: Optional[Callable] = None,
    ) -> BatchExecution:
        """
        단건 재처리

        Args:
            job_id: 배치 작업 ID
            target_id: 재처리 대상 ID (예: 포트폴리오 ID)
            target_type: 재처리 대상 유형 (예: PORTFOLIO)
            operator_id: 운영자 ID (필수)
            replay_reason: 재처리 사유 (필수)
            parent_execution_id: 원본 실행 ID (선택)
            processor: 실제 처리 함수 (선택)

        Returns:
            BatchExecution: 재처리 실행 레코드
        """
        if not operator_id:
            raise ReplayError("operator_id is required", "C1-BAT-023")
        if not replay_reason:
            raise ReplayError("replay_reason is required", "C1-BAT-024")

        # 원본 실행 검증 (지정된 경우)
        if parent_execution_id:
            self._validate_replay_target(parent_execution_id)

        # 진행 중인 재처리 확인
        self._check_no_running_replay(job_id)

        # 단건 결과 비활성화
        self._deactivate_single_result(
            target_type=target_type,
            target_id=target_id,
            operator_id=operator_id,
            reason=replay_reason,
        )

        # 재처리 실행 시작
        execution = self.batch_service.start_execution(
            job_id=job_id,
            run_type=RunType.REPLAY,
            operator_id=operator_id,
            operator_note=f"Single replay ({target_type}:{target_id}): {replay_reason}",
            parent_execution_id=parent_execution_id,
            replay_reason=replay_reason,
        )

        # 감사 로그 기록
        self.audit_service.log_batch_action(
            audit_type=AuditType.BATCH_REPLAY,
            execution_id=execution.execution_id,
            action=AuditAction.REPLAY,
            operator_id=operator_id,
            operator_reason=replay_reason,
            after_state={
                "replay_type": ReplayType.SINGLE.value,
                "target_type": target_type,
                "target_id": target_id,
                "parent_execution_id": parent_execution_id,
            },
        )

        # 실제 처리 수행
        if processor:
            try:
                result = processor(execution, target_id, target_type)
                self.batch_service.complete_execution(
                    execution_id=execution.execution_id,
                    processed_count=1,
                    success_count=1,
                )
            except Exception as e:
                self.batch_service.fail_execution(
                    execution_id=execution.execution_id,
                    error_code="C1-BAT-001",
                    error_message=str(e),
                )
                raise

        return execution

    def _deactivate_existing_results(
        self,
        job_id: str,
        target_date: date,
        operator_id: str,
        reason: str,
    ) -> int:
        """기존 결과 비활성화 (단일 날짜)"""
        # result_type을 job_id로 매핑
        result_type = self._job_to_result_type(job_id)
        if not result_type:
            return 0

        # 해당 날짜의 active 결과 조회
        results = self.db.query(ResultVersion).filter(
            ResultVersion.result_type == result_type,
            ResultVersion.is_active == True,
        ).all()

        count = 0
        for result in results:
            result.is_active = False
            result.deactivated_at = datetime.utcnow()
            result.deactivated_by = operator_id
            result.deactivate_reason = reason
            count += 1

        if count > 0:
            self.db.commit()

        return count

    def _deactivate_existing_results_range(
        self,
        job_id: str,
        start_date: date,
        end_date: date,
        operator_id: str,
        reason: str,
    ) -> int:
        """기존 결과 비활성화 (구간)"""
        result_type = self._job_to_result_type(job_id)
        if not result_type:
            return 0

        results = self.db.query(ResultVersion).filter(
            ResultVersion.result_type == result_type,
            ResultVersion.is_active == True,
        ).all()

        count = 0
        for result in results:
            result.is_active = False
            result.deactivated_at = datetime.utcnow()
            result.deactivated_by = operator_id
            result.deactivate_reason = reason
            count += 1

        if count > 0:
            self.db.commit()

        return count

    def _deactivate_single_result(
        self,
        target_type: str,
        target_id: str,
        operator_id: str,
        reason: str,
    ) -> bool:
        """단건 결과 비활성화"""
        result = self.db.query(ResultVersion).filter(
            ResultVersion.result_type == target_type,
            ResultVersion.result_id == target_id,
            ResultVersion.is_active == True,
        ).first()

        if result:
            result.is_active = False
            result.deactivated_at = datetime.utcnow()
            result.deactivated_by = operator_id
            result.deactivate_reason = reason
            self.db.commit()
            return True

        return False

    def _job_to_result_type(self, job_id: str) -> Optional[str]:
        """Job ID를 결과 유형으로 매핑"""
        mapping = {
            'DAILY_SIMULATION': 'SIMULATION',
            'DAILY_EXPLANATION': 'EXPLANATION',
            'MONTHLY_REPORT': 'PERFORMANCE',
        }
        return mapping.get(job_id)

    def get_replay_history(
        self,
        job_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[BatchExecution]:
        """재처리 이력 조회"""
        query = self.db.query(BatchExecution).filter(
            BatchExecution.run_type == RunType.REPLAY.value
        )

        if job_id:
            query = query.filter(BatchExecution.job_id == job_id)

        return query.order_by(
            BatchExecution.started_at.desc()
        ).limit(limit).all()

    def get_replay_chain(
        self,
        execution_id: str
    ) -> List[BatchExecution]:
        """재처리 체인 조회 (원본 -> 재처리1 -> 재처리2 ...)"""
        chain = []
        current = self.batch_service.get_execution(execution_id)

        if not current:
            return chain

        # 원본으로 거슬러 올라가기
        while current.parent_execution_id:
            parent = self.batch_service.get_execution(current.parent_execution_id)
            if parent:
                chain.insert(0, parent)
                current = parent
            else:
                break

        # 현재 실행 추가
        chain.append(self.batch_service.get_execution(execution_id))

        # 자식 재처리 찾기
        current_id = execution_id
        while True:
            child = self.db.query(BatchExecution).filter(
                BatchExecution.parent_execution_id == current_id
            ).first()
            if child:
                chain.append(child)
                current_id = child.execution_id
            else:
                break

        return chain
