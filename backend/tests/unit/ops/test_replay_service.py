"""
Phase 3-C / Epic C-1: 재처리(Replay) 서비스 테스트
생성일: 2026-01-18
"""

import pytest
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.ops import BatchJob, BatchExecution, ResultVersion, OpsAuditLog
from app.services.replay_service import (
    ReplayService,
    ReplayType,
    ReplayError,
    InvalidReplayTargetError,
    ReplayInProgressError,
)
from app.services.batch_execution import RunType, ExecutionStatus


@pytest.fixture
def db_session():
    """테스트용 인메모리 DB 세션"""
    engine = create_engine("sqlite:///:memory:")

    BatchJob.__table__.create(bind=engine, checkfirst=True)
    BatchExecution.__table__.create(bind=engine, checkfirst=True)
    ResultVersion.__table__.create(bind=engine, checkfirst=True)
    OpsAuditLog.__table__.create(bind=engine, checkfirst=True)

    Session = sessionmaker(bind=engine)
    session = Session()

    # 테스트용 Job 생성
    jobs = [
        BatchJob(job_id="DAILY_SIMULATION", job_name="일간 시뮬레이션", job_type="DAILY"),
        BatchJob(job_id="DAILY_EXPLANATION", job_name="일간 설명 생성", job_type="DAILY"),
        BatchJob(job_id="MONTHLY_REPORT", job_name="월간 리포트", job_type="MONTHLY"),
    ]
    for job in jobs:
        session.add(job)
    session.commit()

    yield session

    session.close()


@pytest.fixture
def service(db_session):
    """ReplayService 인스턴스"""
    return ReplayService(db_session)


@pytest.fixture
def completed_execution(db_session, service):
    """완료된 실행 fixture"""
    execution = service.batch_service.start_execution(
        job_id="DAILY_SIMULATION",
        run_type=RunType.AUTO,
        target_date=datetime(2026, 1, 15),
    )
    service.batch_service.complete_execution(
        execution_id=execution.execution_id,
        processed_count=100,
        success_count=100,
    )
    return service.batch_service.get_execution(execution.execution_id)


class TestReplayFull:
    """replay_full 테스트"""

    def test_replay_full_success(self, service, completed_execution):
        """전체 재처리 성공"""
        replay = service.replay_full(
            job_id="DAILY_SIMULATION",
            target_date=date(2026, 1, 15),
            operator_id="admin",
            replay_reason="Price data correction",
            parent_execution_id=completed_execution.execution_id,
        )

        assert replay.run_type == "REPLAY"
        assert replay.status == "RUNNING"
        assert replay.parent_execution_id == completed_execution.execution_id
        assert replay.replay_reason == "Price data correction"

    def test_replay_full_without_parent(self, service):
        """원본 없이 재처리"""
        replay = service.replay_full(
            job_id="DAILY_SIMULATION",
            target_date=date(2026, 1, 15),
            operator_id="admin",
            replay_reason="Initial data load",
        )

        assert replay.run_type == "REPLAY"
        assert replay.parent_execution_id is None

    def test_replay_full_creates_audit_log(self, service, db_session, completed_execution):
        """재처리 시 감사 로그 생성"""
        replay = service.replay_full(
            job_id="DAILY_SIMULATION",
            target_date=date(2026, 1, 15),
            operator_id="admin",
            replay_reason="Audit test",
            parent_execution_id=completed_execution.execution_id,
        )

        # 감사 로그 확인
        audit = db_session.query(OpsAuditLog).filter(
            OpsAuditLog.target_id == replay.execution_id
        ).first()

        assert audit is not None
        assert audit.audit_type == "BATCH_REPLAY"
        assert audit.operator_id == "admin"

    def test_replay_full_missing_operator(self, service):
        """operator_id 누락"""
        with pytest.raises(ReplayError) as exc:
            service.replay_full(
                job_id="DAILY_SIMULATION",
                target_date=date(2026, 1, 15),
                operator_id="",
                replay_reason="Test",
            )
        assert "operator_id" in str(exc.value)

    def test_replay_full_missing_reason(self, service):
        """replay_reason 누락"""
        with pytest.raises(ReplayError) as exc:
            service.replay_full(
                job_id="DAILY_SIMULATION",
                target_date=date(2026, 1, 15),
                operator_id="admin",
                replay_reason="",
            )
        assert "replay_reason" in str(exc.value)

    def test_replay_full_with_processor(self, service, completed_execution):
        """processor 함수와 함께 재처리"""
        def mock_processor(execution):
            return {"processed": 50, "success": 50}

        replay = service.replay_full(
            job_id="DAILY_SIMULATION",
            target_date=date(2026, 1, 15),
            operator_id="admin",
            replay_reason="Test with processor",
            processor=mock_processor,
        )

        # 완료 상태 확인
        updated = service.batch_service.get_execution(replay.execution_id)
        assert updated.status == "SUCCESS"
        assert updated.processed_count == 50


class TestReplayRange:
    """replay_range 테스트"""

    def test_replay_range_success(self, service):
        """구간 재처리 성공"""
        replay = service.replay_range(
            job_id="DAILY_SIMULATION",
            start_date=date(2026, 1, 10),
            end_date=date(2026, 1, 15),
            operator_id="admin",
            replay_reason="Range correction",
        )

        assert replay.run_type == "REPLAY"
        assert replay.target_start_date.date() == date(2026, 1, 10)
        assert replay.target_end_date.date() == date(2026, 1, 15)

    def test_replay_range_invalid_dates(self, service):
        """잘못된 날짜 범위"""
        with pytest.raises(ReplayError) as exc:
            service.replay_range(
                job_id="DAILY_SIMULATION",
                start_date=date(2026, 1, 20),
                end_date=date(2026, 1, 15),
                operator_id="admin",
                replay_reason="Invalid range",
            )
        assert "Invalid date range" in str(exc.value)


class TestReplaySingle:
    """replay_single 테스트"""

    def test_replay_single_success(self, service):
        """단건 재처리 성공"""
        replay = service.replay_single(
            job_id="DAILY_SIMULATION",
            target_id="portfolio-123",
            target_type="PORTFOLIO",
            operator_id="admin",
            replay_reason="Single item fix",
        )

        assert replay.run_type == "REPLAY"
        assert "portfolio-123" in replay.operator_note


class TestInvalidReplayTarget:
    """잘못된 재처리 대상 테스트"""

    def test_replay_running_execution(self, service, db_session):
        """실행 중인 배치는 재처리 불가"""
        execution = service.batch_service.start_execution(
            job_id="DAILY_SIMULATION",
            run_type=RunType.AUTO,
        )

        with pytest.raises(InvalidReplayTargetError):
            service.replay_full(
                job_id="DAILY_SIMULATION",
                target_date=date(2026, 1, 15),
                operator_id="admin",
                replay_reason="Test",
                parent_execution_id=execution.execution_id,
            )

    def test_replay_nonexistent_execution(self, service):
        """존재하지 않는 실행"""
        with pytest.raises(InvalidReplayTargetError):
            service.replay_full(
                job_id="DAILY_SIMULATION",
                target_date=date(2026, 1, 15),
                operator_id="admin",
                replay_reason="Test",
                parent_execution_id="nonexistent-id",
            )


class TestReplayInProgress:
    """재처리 중복 방지 테스트"""

    def test_prevent_duplicate_replay(self, service, completed_execution):
        """동일 Job에 대한 중복 재처리 방지"""
        # 첫 번째 재처리 시작
        service.replay_full(
            job_id="DAILY_SIMULATION",
            target_date=date(2026, 1, 15),
            operator_id="admin",
            replay_reason="First replay",
        )

        # 두 번째 재처리 시도 - 실패해야 함
        with pytest.raises(ReplayInProgressError):
            service.replay_full(
                job_id="DAILY_SIMULATION",
                target_date=date(2026, 1, 16),
                operator_id="admin",
                replay_reason="Second replay",
            )


class TestResultDeactivation:
    """결과 비활성화 테스트"""

    def test_deactivate_existing_results(self, service, db_session):
        """재처리 시 기존 결과 비활성화"""
        # 기존 결과 생성
        result = ResultVersion(
            result_type="SIMULATION",
            result_id="sim-123",
            version_no=1,
            is_active=True,
        )
        db_session.add(result)
        db_session.commit()

        # 재처리 실행
        service.replay_full(
            job_id="DAILY_SIMULATION",
            target_date=date(2026, 1, 15),
            operator_id="admin",
            replay_reason="Deactivation test",
        )

        # 기존 결과 비활성화 확인
        db_session.refresh(result)
        assert result.is_active is False
        assert result.deactivated_by == "admin"


class TestReplayHistory:
    """재처리 이력 조회 테스트"""

    def test_get_replay_history(self, service):
        """재처리 이력 조회"""
        # 재처리 3건 생성
        for i in range(3):
            replay = service.replay_full(
                job_id="DAILY_SIMULATION",
                target_date=date(2026, 1, 10 + i),
                operator_id="admin",
                replay_reason=f"Test replay {i}",
            )
            # 완료 처리
            service.batch_service.complete_execution(replay.execution_id)

        history = service.get_replay_history(job_id="DAILY_SIMULATION")
        assert len(history) == 3

    def test_get_replay_history_limit(self, service):
        """재처리 이력 limit"""
        for i in range(5):
            replay = service.replay_full(
                job_id="DAILY_SIMULATION",
                target_date=date(2026, 1, 10 + i),
                operator_id="admin",
                replay_reason=f"Test {i}",
            )
            service.batch_service.complete_execution(replay.execution_id)

        history = service.get_replay_history(limit=3)
        assert len(history) == 3


class TestReplayChain:
    """재처리 체인 테스트"""

    def test_get_replay_chain(self, service, completed_execution):
        """재처리 체인 조회"""
        # 첫 번째 재처리
        replay1 = service.replay_full(
            job_id="DAILY_SIMULATION",
            target_date=date(2026, 1, 15),
            operator_id="admin",
            replay_reason="First replay",
            parent_execution_id=completed_execution.execution_id,
        )
        service.batch_service.complete_execution(replay1.execution_id)

        # 두 번째 재처리 (첫 번째 재처리 기반)
        replay2 = service.replay_full(
            job_id="DAILY_SIMULATION",
            target_date=date(2026, 1, 15),
            operator_id="admin",
            replay_reason="Second replay",
            parent_execution_id=replay1.execution_id,
        )
        service.batch_service.complete_execution(replay2.execution_id)

        # 체인 조회
        chain = service.get_replay_chain(replay2.execution_id)

        assert len(chain) == 3
        assert chain[0].execution_id == completed_execution.execution_id
        assert chain[1].execution_id == replay1.execution_id
        assert chain[2].execution_id == replay2.execution_id


class TestReplayType:
    """ReplayType Enum 테스트"""

    def test_replay_type_values(self):
        """ReplayType 값 확인"""
        assert ReplayType.FULL.value == "FULL"
        assert ReplayType.RANGE.value == "RANGE"
        assert ReplayType.SINGLE.value == "SINGLE"
