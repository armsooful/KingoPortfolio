"""
Phase 3-C / Epic C-1: 감사 로그 서비스 테스트
생성일: 2026-01-18
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.ops import OpsAuditLog
from app.utils.kst_now import kst_now
from app.services.audit_log_service import (
    AuditLogService,
    AuditType,
    TargetType,
    AuditAction,
    AuditLogError,
    MissingOperatorError,
    MissingReasonError,
)


@pytest.fixture
def db_session():
    """테스트용 인메모리 DB 세션"""
    engine = create_engine("sqlite:///:memory:")
    OpsAuditLog.__table__.create(bind=engine, checkfirst=True)

    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()


@pytest.fixture
def service(db_session):
    """AuditLogService 인스턴스"""
    return AuditLogService(db_session)


class TestLogBatchAction:
    """log_batch_action 테스트"""

    def test_log_batch_start(self, service):
        """배치 시작 로그 기록"""
        log = service.log_batch_action(
            audit_type=AuditType.BATCH_START,
            execution_id="exec-123",
            action=AuditAction.START,
            operator_id="admin",
            operator_reason="Manual execution for testing",
            operator_ip="192.168.1.1",
        )

        assert log.audit_id is not None
        assert log.audit_type == "BATCH_START"
        assert log.target_type == "BATCH_EXECUTION"
        assert log.target_id == "exec-123"
        assert log.action == "START"
        assert log.operator_id == "admin"
        assert log.operator_reason == "Manual execution for testing"

    def test_log_batch_stop(self, service):
        """배치 중단 로그 기록"""
        log = service.log_batch_action(
            audit_type=AuditType.BATCH_STOP,
            execution_id="exec-123",
            action=AuditAction.STOP,
            operator_id="admin",
            operator_reason="Emergency stop due to data issue",
            before_state={"status": "RUNNING"},
            after_state={"status": "STOPPED"},
        )

        assert log.audit_type == "BATCH_STOP"
        assert log.action == "STOP"
        assert log.before_state["status"] == "RUNNING"
        assert log.after_state["status"] == "STOPPED"

    def test_log_batch_replay(self, service):
        """배치 재처리 로그 기록"""
        log = service.log_batch_action(
            audit_type=AuditType.BATCH_REPLAY,
            execution_id="exec-456",
            action=AuditAction.REPLAY,
            operator_id="data_admin",
            operator_reason="Price data correction",
        )

        assert log.audit_type == "BATCH_REPLAY"
        assert log.action == "REPLAY"

    def test_missing_operator_id_raises(self, service):
        """operator_id 누락 시 예외 발생"""
        with pytest.raises(MissingOperatorError):
            service.log_batch_action(
                audit_type=AuditType.BATCH_START,
                execution_id="exec-123",
                action=AuditAction.START,
                operator_id="",
                operator_reason="Test reason",
            )

    def test_missing_reason_raises(self, service):
        """reason 누락 시 예외 발생"""
        with pytest.raises(MissingReasonError):
            service.log_batch_action(
                audit_type=AuditType.BATCH_START,
                execution_id="exec-123",
                action=AuditAction.START,
                operator_id="admin",
                operator_reason="",
            )

    def test_whitespace_only_operator_id_raises(self, service):
        """공백만 있는 operator_id 시 예외 발생"""
        with pytest.raises(MissingOperatorError):
            service.log_batch_action(
                audit_type=AuditType.BATCH_START,
                execution_id="exec-123",
                action=AuditAction.START,
                operator_id="   ",
                operator_reason="Test reason",
            )


class TestLogDataCorrection:
    """log_data_correction 테스트"""

    def test_log_data_correction(self, service):
        """데이터 보정 로그 기록"""
        log = service.log_data_correction(
            target_type=TargetType.PORTFOLIO,
            target_id="port-123",
            operator_id="data_team",
            operator_reason="Fix incorrect weight calculation",
            before_state={"weight_a": 0.3, "weight_b": 0.7},
            after_state={"weight_a": 0.4, "weight_b": 0.6},
        )

        assert log.audit_type == "DATA_CORRECTION"
        assert log.target_type == "PORTFOLIO"
        assert log.action == "UPDATE"
        assert log.before_state["weight_a"] == 0.3
        assert log.after_state["weight_a"] == 0.4

    def test_log_data_correction_with_approval(self, service):
        """승인이 있는 데이터 보정 로그"""
        log = service.log_data_correction(
            target_type=TargetType.SIMULATION,
            target_id="sim-456",
            operator_id="analyst",
            operator_reason="Simulation parameter fix",
            before_state={"param": "old"},
            after_state={"param": "new"},
            approved_by="supervisor",
        )

        assert log.approved_by == "supervisor"
        assert log.approved_at is not None

    def test_missing_before_state_raises(self, service):
        """before_state 누락 시 예외 발생"""
        with pytest.raises(AuditLogError):
            service.log_data_correction(
                target_type=TargetType.PORTFOLIO,
                target_id="port-123",
                operator_id="admin",
                operator_reason="Test",
                before_state=None,
                after_state={"new": "state"},
            )

    def test_missing_after_state_raises(self, service):
        """after_state 누락 시 예외 발생"""
        with pytest.raises(AuditLogError):
            service.log_data_correction(
                target_type=TargetType.PORTFOLIO,
                target_id="port-123",
                operator_id="admin",
                operator_reason="Test",
                before_state={"old": "state"},
                after_state=None,
            )


class TestLogConfigChange:
    """log_config_change 테스트"""

    def test_log_config_change(self, service):
        """설정 변경 로그 기록"""
        log = service.log_config_change(
            config_key="batch.timeout_seconds",
            operator_id="sys_admin",
            operator_reason="Increase timeout for large batches",
            before_value=300,
            after_value=600,
        )

        assert log.audit_type == "CONFIG_CHANGE"
        assert log.target_type == "SYSTEM_CONFIG"
        assert log.target_id == "batch.timeout_seconds"
        assert log.before_state["value"] == 300
        assert log.after_state["value"] == 600


class TestLogGeneric:
    """log_generic 테스트"""

    def test_log_generic(self, service):
        """범용 감사 로그 기록"""
        log = service.log_generic(
            audit_type="CUSTOM_ACTION",
            target_type="CUSTOM_TARGET",
            target_id="custom-123",
            action="CUSTOM",
            operator_id="admin",
            operator_reason="Custom audit action",
        )

        assert log.audit_type == "CUSTOM_ACTION"
        assert log.target_type == "CUSTOM_TARGET"


class TestGetAuditLogs:
    """감사 로그 조회 테스트"""

    @pytest.fixture
    def sample_logs(self, service):
        """샘플 로그 생성"""
        logs = []
        # 배치 시작 로그 3건
        for i in range(3):
            log = service.log_batch_action(
                audit_type=AuditType.BATCH_START,
                execution_id=f"exec-{i}",
                action=AuditAction.START,
                operator_id="admin",
                operator_reason=f"Test batch {i}",
            )
            logs.append(log)

        # 데이터 보정 로그 2건
        for i in range(2):
            log = service.log_data_correction(
                target_type=TargetType.PORTFOLIO,
                target_id=f"port-{i}",
                operator_id="data_team",
                operator_reason=f"Data fix {i}",
                before_state={"old": i},
                after_state={"new": i + 1},
            )
            logs.append(log)

        return logs

    def test_get_all_logs(self, service, sample_logs):
        """전체 로그 조회"""
        logs = service.get_audit_logs()
        assert len(logs) == 5

    def test_get_logs_by_audit_type(self, service, sample_logs):
        """감사 유형별 조회"""
        logs = service.get_audit_logs(audit_type="BATCH_START")
        assert len(logs) == 3

    def test_get_logs_by_target_type(self, service, sample_logs):
        """대상 유형별 조회"""
        logs = service.get_audit_logs(target_type="PORTFOLIO")
        assert len(logs) == 2

    def test_get_logs_by_operator(self, service, sample_logs):
        """운영자별 조회"""
        logs = service.get_audit_logs(operator_id="admin")
        assert len(logs) == 3

    def test_get_logs_with_limit(self, service, sample_logs):
        """limit 적용 조회"""
        logs = service.get_audit_logs(limit=2)
        assert len(logs) == 2

    def test_get_logs_with_offset(self, service, sample_logs):
        """offset 적용 조회"""
        logs = service.get_audit_logs(limit=2, offset=3)
        assert len(logs) == 2

    def test_get_audit_log_by_id(self, service, sample_logs):
        """단일 로그 조회"""
        first_log = sample_logs[0]
        log = service.get_audit_log(first_log.audit_id)
        assert log is not None
        assert log.audit_id == first_log.audit_id

    def test_get_audit_logs_by_target(self, service, sample_logs):
        """대상별 로그 조회"""
        logs = service.get_audit_logs_by_target("BATCH_EXECUTION", "exec-0")
        assert len(logs) == 1
        assert logs[0].target_id == "exec-0"

    def test_get_recent_logs_by_operator(self, service, sample_logs):
        """운영자별 최근 로그 조회"""
        logs = service.get_recent_logs_by_operator("admin", limit=2)
        assert len(logs) == 2

    def test_count_logs(self, service, sample_logs):
        """로그 건수 조회"""
        total = service.count_logs()
        assert total == 5

        batch_count = service.count_logs(audit_type="BATCH_START")
        assert batch_count == 3


class TestDateFilter:
    """날짜 필터 테스트"""

    def test_filter_by_date_range(self, service, db_session):
        """날짜 범위 필터"""
        # 로그 생성
        log = service.log_batch_action(
            audit_type=AuditType.BATCH_START,
            execution_id="exec-date-test",
            action=AuditAction.START,
            operator_id="admin",
            operator_reason="Date test",
        )

        # 오늘 포함 범위로 조회 (created_at이 kst_now 사용)
        now = kst_now()
        start = now - timedelta(hours=1)
        end = now + timedelta(hours=1)

        logs = service.get_audit_logs(start_date=start, end_date=end)
        assert len(logs) >= 1

        # 과거 날짜로 조회 (결과 없음)
        old_start = now - timedelta(days=30)
        old_end = now - timedelta(days=29)

        logs = service.get_audit_logs(start_date=old_start, end_date=old_end)
        assert len(logs) == 0


class TestEnumValues:
    """Enum 값 테스트"""

    def test_audit_type_values(self):
        """AuditType 값 확인"""
        assert AuditType.BATCH_START.value == "BATCH_START"
        assert AuditType.BATCH_STOP.value == "BATCH_STOP"
        assert AuditType.BATCH_REPLAY.value == "BATCH_REPLAY"
        assert AuditType.DATA_CORRECTION.value == "DATA_CORRECTION"
        assert AuditType.CONFIG_CHANGE.value == "CONFIG_CHANGE"

    def test_target_type_values(self):
        """TargetType 값 확인"""
        assert TargetType.BATCH_EXECUTION.value == "BATCH_EXECUTION"
        assert TargetType.PORTFOLIO.value == "PORTFOLIO"
        assert TargetType.SIMULATION.value == "SIMULATION"

    def test_audit_action_values(self):
        """AuditAction 값 확인"""
        assert AuditAction.CREATE.value == "CREATE"
        assert AuditAction.UPDATE.value == "UPDATE"
        assert AuditAction.DEACTIVATE.value == "DEACTIVATE"
        assert AuditAction.REPLAY.value == "REPLAY"
