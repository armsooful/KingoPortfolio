"""
Phase 3-C / Epic C-1: 운영 알림 서비스 테스트
생성일: 2026-01-18
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.ops import OpsAlert, ErrorCodeMaster
from app.services.ops_alert_service import (
    OpsAlertService,
    AlertType,
    AlertLevel,
    AlertChannel,
    AlertError,
)


@pytest.fixture
def db_session():
    """테스트용 인메모리 DB 세션"""
    engine = create_engine("sqlite:///:memory:")
    OpsAlert.__table__.create(bind=engine, checkfirst=True)
    ErrorCodeMaster.__table__.create(bind=engine, checkfirst=True)

    Session = sessionmaker(bind=engine)
    session = Session()

    # 테스트용 오류 코드 생성
    error_codes = [
        ErrorCodeMaster(
            error_code='C1-BAT-001', category='BAT', severity='HIGH',
            user_message='처리 중 오류가 발생했습니다.',
            ops_message='배치 실행 중 예외 발생',
            action_guide='로그 확인 후 원인 분석',
            auto_alert=True, alert_level='ERROR'
        ),
        ErrorCodeMaster(
            error_code='C1-SYS-001', category='SYS', severity='CRITICAL',
            user_message='시스템 점검 중입니다.',
            ops_message='DB 연결 실패',
            action_guide='DB 서버 상태 확인',
            auto_alert=True, alert_level='CRITICAL'
        ),
        ErrorCodeMaster(
            error_code='C1-INP-003', category='INP', severity='LOW',
            user_message='데이터 처리 중 오류가 발생했습니다.',
            ops_message='입력 데이터 범위 오류',
            action_guide='데이터 정합성 확인',
            auto_alert=False, alert_level='INFO'
        ),
    ]

    for ec in error_codes:
        session.add(ec)
    session.commit()

    yield session

    session.close()


@pytest.fixture
def service(db_session):
    """OpsAlertService 인스턴스"""
    return OpsAlertService(db_session)


class TestSendAlert:
    """send_alert 테스트"""

    def test_send_alert_basic(self, service):
        """기본 알림 발송"""
        alert = service.send_alert(
            alert_type=AlertType.BATCH_FAILED,
            alert_level=AlertLevel.ERROR,
            title="Test Alert",
            message="This is a test alert",
        )

        assert alert.alert_id is not None
        assert alert.alert_type == "BATCH_FAILED"
        assert alert.alert_level == "ERROR"
        assert alert.alert_title == "Test Alert"
        assert alert.sent_at is not None

    def test_send_alert_with_execution(self, service):
        """배치 실행 연관 알림"""
        alert = service.send_alert(
            alert_type=AlertType.BATCH_FAILED,
            alert_level=AlertLevel.ERROR,
            title="Batch Failed",
            message="Error message",
            execution_id="exec-123",
            error_code="C1-BAT-001",
        )

        assert alert.execution_id == "exec-123"
        assert alert.related_error_code == "C1-BAT-001"

    def test_send_alert_with_detail(self, service):
        """상세 정보 포함 알림"""
        alert = service.send_alert(
            alert_type=AlertType.SYSTEM_ERROR,
            alert_level=AlertLevel.CRITICAL,
            title="System Error",
            message="Critical error",
            detail={"server": "app-01", "cpu": 95.5},
        )

        assert alert.alert_detail["server"] == "app-01"
        assert alert.alert_detail["cpu"] == 95.5

    def test_send_alert_with_channels(self, service):
        """채널 지정 알림"""
        alert = service.send_alert(
            alert_type=AlertType.BATCH_FAILED,
            alert_level=AlertLevel.ERROR,
            title="Test",
            message="Test",
            channels=[AlertChannel.EMAIL, AlertChannel.SLACK],
        )

        assert "email" in alert.channels_sent
        assert "slack" in alert.channels_sent


class TestBatchAlerts:
    """배치 관련 알림 테스트"""

    def test_send_batch_failed_alert(self, service):
        """배치 실패 알림"""
        alert = service.send_batch_failed_alert(
            execution_id="exec-456",
            job_id="DAILY_SIMULATION",
            error_code="C1-BAT-001",
            error_message="Unexpected error occurred",
        )

        assert alert.alert_type == "BATCH_FAILED"
        assert "DAILY_SIMULATION" in alert.alert_title
        assert alert.related_error_code == "C1-BAT-001"
        assert "action_guide" in alert.alert_detail

    def test_send_batch_stopped_alert(self, service):
        """배치 중단 알림"""
        alert = service.send_batch_stopped_alert(
            execution_id="exec-789",
            job_id="DAILY_PRICE_LOAD",
            operator_id="admin",
            reason="Emergency maintenance",
        )

        assert alert.alert_type == "BATCH_STOPPED"
        assert alert.alert_level == "WARN"
        assert "admin" in alert.alert_message

    def test_send_replay_alert(self, service):
        """재처리 알림"""
        alert = service.send_replay_alert(
            execution_id="exec-replay",
            job_id="DAILY_SIMULATION",
            operator_id="data_team",
            replay_reason="Price correction",
            replay_type="FULL",
        )

        assert alert.alert_type == "REPLAY_EXECUTED"
        assert alert.alert_level == "INFO"
        assert alert.alert_detail["replay_type"] == "FULL"


class TestAutoAlert:
    """자동 알림 테스트"""

    def test_send_auto_alert_enabled(self, service):
        """auto_alert=True인 경우"""
        alert = service.send_auto_alert_by_error_code(
            execution_id="exec-auto",
            error_code="C1-BAT-001",
            additional_message="Additional context",
        )

        assert alert is not None
        assert alert.related_error_code == "C1-BAT-001"

    def test_send_auto_alert_disabled(self, service):
        """auto_alert=False인 경우"""
        alert = service.send_auto_alert_by_error_code(
            execution_id="exec-auto",
            error_code="C1-INP-003",
        )

        assert alert is None


class TestAcknowledgeAlert:
    """알림 확인 테스트"""

    def test_acknowledge_alert(self, service):
        """알림 확인"""
        alert = service.send_alert(
            alert_type=AlertType.BATCH_FAILED,
            alert_level=AlertLevel.ERROR,
            title="Test",
            message="Test",
        )

        acked = service.acknowledge_alert(
            alert_id=alert.alert_id,
            acknowledged_by="admin",
        )

        assert acked.acknowledged_by == "admin"
        assert acked.acknowledged_at is not None

    def test_acknowledge_nonexistent_alert(self, service):
        """존재하지 않는 알림 확인"""
        with pytest.raises(AlertError) as exc:
            service.acknowledge_alert(
                alert_id=99999,
                acknowledged_by="admin",
            )
        assert "not found" in str(exc.value)

    def test_acknowledge_already_acknowledged(self, service):
        """이미 확인된 알림 재확인"""
        alert = service.send_alert(
            alert_type=AlertType.BATCH_FAILED,
            alert_level=AlertLevel.ERROR,
            title="Test",
            message="Test",
        )
        service.acknowledge_alert(alert.alert_id, "admin")

        with pytest.raises(AlertError) as exc:
            service.acknowledge_alert(alert.alert_id, "other_admin")
        assert "already acknowledged" in str(exc.value)


class TestGetAlerts:
    """알림 조회 테스트"""

    @pytest.fixture
    def sample_alerts(self, service):
        """샘플 알림 생성"""
        alerts = []

        # 다양한 유형의 알림 생성
        alerts.append(service.send_alert(
            alert_type=AlertType.BATCH_FAILED,
            alert_level=AlertLevel.ERROR,
            title="Error 1",
            message="Error message 1",
        ))

        alerts.append(service.send_alert(
            alert_type=AlertType.BATCH_FAILED,
            alert_level=AlertLevel.CRITICAL,
            title="Critical 1",
            message="Critical message 1",
        ))

        alerts.append(service.send_alert(
            alert_type=AlertType.REPLAY_EXECUTED,
            alert_level=AlertLevel.INFO,
            title="Info 1",
            message="Info message 1",
        ))

        # 하나는 확인 처리
        service.acknowledge_alert(alerts[0].alert_id, "admin")

        return alerts

    def test_get_all_alerts(self, service, sample_alerts):
        """전체 알림 조회"""
        alerts = service.get_alerts()
        assert len(alerts) == 3

    def test_get_alerts_by_type(self, service, sample_alerts):
        """유형별 알림 조회"""
        alerts = service.get_alerts(alert_type="BATCH_FAILED")
        assert len(alerts) == 2

    def test_get_alerts_by_level(self, service, sample_alerts):
        """레벨별 알림 조회"""
        alerts = service.get_alerts(alert_level="CRITICAL")
        assert len(alerts) == 1

    def test_get_unacknowledged_alerts(self, service, sample_alerts):
        """미확인 알림 조회"""
        unacked = service.get_unacknowledged_alerts()
        assert len(unacked) == 2

    def test_get_alerts_acknowledged_only(self, service, sample_alerts):
        """확인된 알림만 조회"""
        acked = service.get_alerts(acknowledged=True)
        assert len(acked) == 1

    def test_get_alert_by_id(self, service, sample_alerts):
        """단일 알림 조회"""
        first_alert = sample_alerts[0]
        alert = service.get_alert(first_alert.alert_id)
        assert alert is not None
        assert alert.alert_id == first_alert.alert_id


class TestGetAlertsByExecution:
    """배치 실행별 알림 조회"""

    def test_get_alerts_by_execution(self, service):
        """배치 실행별 알림"""
        exec_id = "exec-test-123"

        service.send_alert(
            alert_type=AlertType.BATCH_FAILED,
            alert_level=AlertLevel.ERROR,
            title="Alert 1",
            message="Message 1",
            execution_id=exec_id,
        )

        service.send_alert(
            alert_type=AlertType.BATCH_STOPPED,
            alert_level=AlertLevel.WARN,
            title="Alert 2",
            message="Message 2",
            execution_id=exec_id,
        )

        service.send_alert(
            alert_type=AlertType.SYSTEM_ERROR,
            alert_level=AlertLevel.ERROR,
            title="Other Alert",
            message="Other message",
            execution_id="other-exec",
        )

        alerts = service.get_alerts_by_execution(exec_id)
        assert len(alerts) == 2


class TestCountUnacknowledged:
    """미확인 알림 건수 테스트"""

    def test_count_unacknowledged(self, service):
        """미확인 알림 건수"""
        for i in range(5):
            service.send_alert(
                alert_type=AlertType.BATCH_FAILED,
                alert_level=AlertLevel.ERROR,
                title=f"Alert {i}",
                message=f"Message {i}",
            )

        count = service.count_unacknowledged()
        assert count == 5

    def test_count_unacknowledged_by_level(self, service):
        """레벨별 미확인 알림 건수"""
        service.send_alert(
            alert_type=AlertType.BATCH_FAILED,
            alert_level=AlertLevel.ERROR,
            title="Error",
            message="Error",
        )
        service.send_alert(
            alert_type=AlertType.SYSTEM_ERROR,
            alert_level=AlertLevel.CRITICAL,
            title="Critical",
            message="Critical",
        )

        error_count = service.count_unacknowledged(alert_level="ERROR")
        critical_count = service.count_unacknowledged(alert_level="CRITICAL")

        assert error_count == 1
        assert critical_count == 1


class TestConfiguration:
    """설정 테스트"""

    def test_configure_channels(self, service):
        """채널 설정"""
        service.configure(
            email_enabled=True,
            slack_enabled=True,
            webhook_url="https://webhook.example.com",
        )

        assert service._email_enabled is True
        assert service._slack_enabled is True
        assert service._webhook_url == "https://webhook.example.com"


class TestEnumValues:
    """Enum 값 테스트"""

    def test_alert_type_values(self):
        """AlertType 값"""
        assert AlertType.BATCH_FAILED.value == "BATCH_FAILED"
        assert AlertType.BATCH_STOPPED.value == "BATCH_STOPPED"
        assert AlertType.REPLAY_EXECUTED.value == "REPLAY_EXECUTED"

    def test_alert_level_values(self):
        """AlertLevel 값"""
        assert AlertLevel.INFO.value == "INFO"
        assert AlertLevel.WARN.value == "WARN"
        assert AlertLevel.ERROR.value == "ERROR"
        assert AlertLevel.CRITICAL.value == "CRITICAL"

    def test_alert_channel_values(self):
        """AlertChannel 값"""
        assert AlertChannel.EMAIL.value == "email"
        assert AlertChannel.SLACK.value == "slack"
        assert AlertChannel.WEBHOOK.value == "webhook"
