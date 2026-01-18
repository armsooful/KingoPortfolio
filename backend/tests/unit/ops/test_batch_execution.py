"""
Phase 3-C / Epic C-1: 배치 실행 상태 관리 서비스 테스트
생성일: 2026-01-18
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.ops import BatchJob, BatchExecution, BatchExecutionLog
from app.services.batch_execution import (
    BatchExecutionService,
    RunType,
    ExecutionStatus,
    BatchExecutionError,
    DuplicateExecutionError,
    InvalidStateTransitionError,
)


@pytest.fixture
def db_session():
    """테스트용 인메모리 DB 세션"""
    engine = create_engine("sqlite:///:memory:")

    # ops 테이블만 생성
    BatchJob.__table__.create(bind=engine, checkfirst=True)
    BatchExecution.__table__.create(bind=engine, checkfirst=True)
    BatchExecutionLog.__table__.create(bind=engine, checkfirst=True)

    Session = sessionmaker(bind=engine)
    session = Session()

    # 테스트용 Job 생성
    job = BatchJob(
        job_id="TEST_JOB",
        job_name="Test Job",
        job_description="Test job for unit tests",
        job_type="ON_DEMAND",
        is_active=True,
    )
    session.add(job)
    session.commit()

    yield session

    session.close()


@pytest.fixture
def service(db_session):
    """BatchExecutionService 인스턴스"""
    return BatchExecutionService(db_session)


class TestStartExecution:
    """start_execution 테스트"""

    def test_auto_execution_success(self, service, db_session):
        """AUTO 실행 성공"""
        execution = service.start_execution(
            job_id="TEST_JOB",
            run_type=RunType.AUTO,
            target_date=datetime(2026, 1, 18),
        )

        assert execution.execution_id is not None
        assert execution.job_id == "TEST_JOB"
        assert execution.run_type == "AUTO"
        assert execution.status == "RUNNING"
        assert execution.started_at is not None

    def test_manual_execution_requires_operator(self, service):
        """MANUAL 실행 시 operator_id 필수"""
        with pytest.raises(BatchExecutionError) as exc:
            service.start_execution(
                job_id="TEST_JOB",
                run_type=RunType.MANUAL,
            )
        assert "operator_id is required" in str(exc.value)

    def test_manual_execution_success(self, service):
        """MANUAL 실행 성공"""
        execution = service.start_execution(
            job_id="TEST_JOB",
            run_type=RunType.MANUAL,
            operator_id="admin",
            operator_note="Manual test run",
        )

        assert execution.status == "RUNNING"
        assert execution.operator_id == "admin"
        assert execution.operator_note == "Manual test run"

    def test_replay_requires_reason(self, service):
        """REPLAY 실행 시 replay_reason 필수"""
        with pytest.raises(BatchExecutionError) as exc:
            service.start_execution(
                job_id="TEST_JOB",
                run_type=RunType.REPLAY,
                operator_id="admin",
            )
        assert "replay_reason is required" in str(exc.value)

    def test_replay_execution_success(self, service):
        """REPLAY 실행 성공"""
        # 먼저 원본 실행 생성
        original = service.start_execution(
            job_id="TEST_JOB",
            run_type=RunType.AUTO,
        )
        service.complete_execution(original.execution_id)

        # 재처리 실행
        replay = service.start_execution(
            job_id="TEST_JOB",
            run_type=RunType.REPLAY,
            operator_id="admin",
            parent_execution_id=original.execution_id,
            replay_reason="Data correction",
        )

        assert replay.parent_execution_id == original.execution_id
        assert replay.replay_reason == "Data correction"

    def test_invalid_job_id(self, service):
        """존재하지 않는 Job ID"""
        with pytest.raises(BatchExecutionError) as exc:
            service.start_execution(
                job_id="INVALID_JOB",
                run_type=RunType.AUTO,
            )
        assert "Job not found" in str(exc.value)

    def test_idempotency_duplicate_execution_id(self, service):
        """멱등성: 중복 execution_id 거부"""
        execution = service.start_execution(
            job_id="TEST_JOB",
            run_type=RunType.AUTO,
            execution_id="test-uuid-12345",
        )

        with pytest.raises(DuplicateExecutionError):
            service.start_execution(
                job_id="TEST_JOB",
                run_type=RunType.AUTO,
                execution_id="test-uuid-12345",
            )


class TestUpdateProgress:
    """update_progress 테스트"""

    def test_update_progress_success(self, service):
        """진행 상황 업데이트 성공"""
        execution = service.start_execution(
            job_id="TEST_JOB",
            run_type=RunType.AUTO,
        )

        updated = service.update_progress(
            execution_id=execution.execution_id,
            processed_count=100,
            success_count=95,
            failed_count=5,
        )

        assert updated.processed_count == 100
        assert updated.success_count == 95
        assert updated.failed_count == 5

    def test_update_progress_non_running_fails(self, service):
        """RUNNING 상태가 아닌 경우 진행 업데이트 실패"""
        execution = service.start_execution(
            job_id="TEST_JOB",
            run_type=RunType.AUTO,
        )
        service.complete_execution(execution.execution_id)

        with pytest.raises(BatchExecutionError) as exc:
            service.update_progress(
                execution_id=execution.execution_id,
                processed_count=100,
                success_count=100,
                failed_count=0,
            )
        assert "non-running" in str(exc.value)


class TestCompleteExecution:
    """complete_execution 테스트"""

    def test_complete_success(self, service):
        """성공 완료"""
        execution = service.start_execution(
            job_id="TEST_JOB",
            run_type=RunType.AUTO,
        )

        completed = service.complete_execution(
            execution_id=execution.execution_id,
            processed_count=100,
            success_count=100,
        )

        assert completed.status == "SUCCESS"
        assert completed.ended_at is not None
        assert completed.processed_count == 100

    def test_cannot_complete_non_running(self, service):
        """RUNNING이 아닌 상태에서 완료 불가"""
        execution = service.start_execution(
            job_id="TEST_JOB",
            run_type=RunType.AUTO,
        )
        service.complete_execution(execution.execution_id)

        with pytest.raises(InvalidStateTransitionError):
            service.complete_execution(execution.execution_id)


class TestFailExecution:
    """fail_execution 테스트"""

    def test_fail_success(self, service):
        """실패 기록"""
        execution = service.start_execution(
            job_id="TEST_JOB",
            run_type=RunType.AUTO,
        )

        failed = service.fail_execution(
            execution_id=execution.execution_id,
            error_code="C1-EXT-001",
            error_message="External API timeout",
            error_detail={"api": "price_api", "timeout": 30},
        )

        assert failed.status == "FAILED"
        assert failed.error_code == "C1-EXT-001"
        assert failed.error_message == "External API timeout"
        assert failed.ended_at is not None

    def test_fail_creates_log(self, service, db_session):
        """실패 시 로그 생성"""
        execution = service.start_execution(
            job_id="TEST_JOB",
            run_type=RunType.AUTO,
        )

        service.fail_execution(
            execution_id=execution.execution_id,
            error_code="C1-EXT-001",
            error_message="External API timeout",
        )

        logs = service.get_logs(execution.execution_id, log_level="ERROR")
        assert len(logs) == 1
        assert logs[0].log_code == "C1-EXT-001"


class TestStopExecution:
    """stop_execution 테스트"""

    def test_stop_success(self, service):
        """수동 중단 성공"""
        execution = service.start_execution(
            job_id="TEST_JOB",
            run_type=RunType.AUTO,
        )

        stopped = service.stop_execution(
            execution_id=execution.execution_id,
            operator_id="admin",
            reason="Emergency stop for investigation",
        )

        assert stopped.status == "STOPPED"
        assert "admin" in stopped.error_message
        assert stopped.ended_at is not None

    def test_stop_requires_operator(self, service):
        """중단 시 operator_id 필수"""
        execution = service.start_execution(
            job_id="TEST_JOB",
            run_type=RunType.AUTO,
        )

        with pytest.raises(BatchExecutionError) as exc:
            service.stop_execution(
                execution_id=execution.execution_id,
                operator_id="",
                reason="Test stop",
            )
        assert "operator_id is required" in str(exc.value)

    def test_stop_requires_reason(self, service):
        """중단 시 reason 필수"""
        execution = service.start_execution(
            job_id="TEST_JOB",
            run_type=RunType.AUTO,
        )

        with pytest.raises(BatchExecutionError) as exc:
            service.stop_execution(
                execution_id=execution.execution_id,
                operator_id="admin",
                reason="",
            )
        assert "reason is required" in str(exc.value)


class TestStateTransitions:
    """상태 전이 테스트"""

    def test_valid_transitions(self, service):
        """유효한 상태 전이"""
        # READY -> RUNNING (자동)
        execution = service.start_execution(
            job_id="TEST_JOB",
            run_type=RunType.AUTO,
        )
        assert execution.status == "RUNNING"

        # RUNNING -> SUCCESS
        service.complete_execution(execution.execution_id)
        updated = service.get_execution(execution.execution_id)
        assert updated.status == "SUCCESS"

    def test_invalid_transition_success_to_running(self, service):
        """SUCCESS -> RUNNING 전이 불가"""
        execution = service.start_execution(
            job_id="TEST_JOB",
            run_type=RunType.AUTO,
        )
        service.complete_execution(execution.execution_id)

        # SUCCESS에서 다른 상태로 전이 불가
        with pytest.raises(InvalidStateTransitionError):
            service.complete_execution(execution.execution_id)

    def test_invalid_transition_failed_to_success(self, service):
        """FAILED -> SUCCESS 전이 불가"""
        execution = service.start_execution(
            job_id="TEST_JOB",
            run_type=RunType.AUTO,
        )
        service.fail_execution(
            execution.execution_id,
            error_code="C1-BAT-001",
            error_message="Test failure",
        )

        with pytest.raises(InvalidStateTransitionError):
            service.complete_execution(execution.execution_id)


class TestQueryMethods:
    """조회 메서드 테스트"""

    def test_get_executions_by_job(self, service):
        """Job별 실행 이력 조회"""
        # 여러 실행 생성
        for _ in range(3):
            execution = service.start_execution(
                job_id="TEST_JOB",
                run_type=RunType.AUTO,
            )
            service.complete_execution(execution.execution_id)

        executions = service.get_executions_by_job("TEST_JOB")
        assert len(executions) == 3

    def test_get_executions_by_status(self, service):
        """상태별 실행 이력 조회"""
        # 성공 1건, 실패 1건
        exec1 = service.start_execution(job_id="TEST_JOB", run_type=RunType.AUTO)
        service.complete_execution(exec1.execution_id)

        exec2 = service.start_execution(job_id="TEST_JOB", run_type=RunType.AUTO)
        service.fail_execution(exec2.execution_id, "C1-BAT-001", "Test")

        success_only = service.get_executions_by_job(
            "TEST_JOB", status=ExecutionStatus.SUCCESS
        )
        assert len(success_only) == 1

    def test_get_running_executions(self, service):
        """실행 중인 배치 조회"""
        exec1 = service.start_execution(job_id="TEST_JOB", run_type=RunType.AUTO)
        exec2 = service.start_execution(job_id="TEST_JOB", run_type=RunType.AUTO)

        running = service.get_running_executions()
        assert len(running) == 2

        service.complete_execution(exec1.execution_id)

        running = service.get_running_executions()
        assert len(running) == 1


class TestLogging:
    """로깅 테스트"""

    def test_add_log(self, service):
        """로그 추가"""
        execution = service.start_execution(
            job_id="TEST_JOB",
            run_type=RunType.AUTO,
        )

        log = service.add_log(
            execution_id=execution.execution_id,
            log_level="INFO",
            log_message="Processing started",
            log_category="BAT",
        )

        assert log.log_id is not None
        assert log.log_level == "INFO"

    def test_get_logs(self, service):
        """로그 조회"""
        execution = service.start_execution(
            job_id="TEST_JOB",
            run_type=RunType.AUTO,
        )

        service.add_log(execution.execution_id, "INFO", "Step 1")
        service.add_log(execution.execution_id, "INFO", "Step 2")
        service.add_log(execution.execution_id, "ERROR", "Step 3 failed")

        all_logs = service.get_logs(execution.execution_id)
        assert len(all_logs) == 3

        error_logs = service.get_logs(execution.execution_id, log_level="ERROR")
        assert len(error_logs) == 1
