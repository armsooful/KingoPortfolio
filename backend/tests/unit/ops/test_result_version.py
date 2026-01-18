"""
Phase 3-C / Epic C-1: 결과 버전 관리 서비스 테스트
생성일: 2026-01-18
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.ops import ResultVersion
from app.services.result_version_service import (
    ResultVersionService,
    ResultType,
    VersionError,
    ActiveVersionNotFoundError,
    DuplicateActiveVersionError,
)


@pytest.fixture
def db_session():
    """테스트용 인메모리 DB 세션"""
    engine = create_engine("sqlite:///:memory:")
    ResultVersion.__table__.create(bind=engine, checkfirst=True)

    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()


@pytest.fixture
def service(db_session):
    """ResultVersionService 인스턴스"""
    return ResultVersionService(db_session)


class TestCreateVersion:
    """create_version 테스트"""

    def test_create_first_version(self, service):
        """첫 번째 버전 생성"""
        version = service.create_version(
            result_type="SIMULATION",
            result_id="sim-123",
            execution_id="exec-456",
        )

        assert version.version_id is not None
        assert version.result_type == "SIMULATION"
        assert version.result_id == "sim-123"
        assert version.version_no == 1
        assert version.is_active is True
        assert version.execution_id == "exec-456"

    def test_create_subsequent_version(self, service):
        """후속 버전 생성"""
        # 첫 번째 버전
        v1 = service.create_version(
            result_type="SIMULATION",
            result_id="sim-123",
        )

        # 두 번째 버전
        v2 = service.create_version(
            result_type="SIMULATION",
            result_id="sim-123",
            deactivated_by="admin",
            deactivate_reason="New version created",
        )

        assert v2.version_no == 2
        assert v2.is_active is True

        # 첫 번째 버전 비활성화 확인
        v1_updated = service.get_version_by_id(v1.version_id)
        assert v1_updated.is_active is False
        assert v1_updated.superseded_by == v2.version_id

    def test_create_version_without_deactivating(self, service):
        """이전 버전 비활성화 없이 생성"""
        v1 = service.create_version(
            result_type="SIMULATION",
            result_id="sim-123",
        )

        v2 = service.create_version(
            result_type="SIMULATION",
            result_id="sim-123",
            deactivate_previous=False,
        )

        # 둘 다 활성 상태
        v1_updated = service.get_version_by_id(v1.version_id)
        assert v1_updated.is_active is True
        assert v2.is_active is True


class TestDeactivateVersion:
    """deactivate_version 테스트"""

    def test_deactivate_version(self, service):
        """버전 비활성화"""
        version = service.create_version(
            result_type="PERFORMANCE",
            result_id="perf-123",
        )

        deactivated = service.deactivate_version(
            result_type="PERFORMANCE",
            result_id="perf-123",
            deactivated_by="admin",
            reason="Manual deactivation",
        )

        assert deactivated is not None
        assert deactivated.is_active is False
        assert deactivated.deactivated_by == "admin"
        assert deactivated.deactivate_reason == "Manual deactivation"
        assert deactivated.deactivated_at is not None

    def test_deactivate_nonexistent_version(self, service):
        """존재하지 않는 버전 비활성화"""
        result = service.deactivate_version(
            result_type="PERFORMANCE",
            result_id="nonexistent",
            deactivated_by="admin",
            reason="Test",
        )

        assert result is None

    def test_deactivate_missing_deactivated_by(self, service):
        """deactivated_by 누락"""
        service.create_version(
            result_type="PERFORMANCE",
            result_id="perf-123",
        )

        with pytest.raises(VersionError) as exc:
            service.deactivate_version(
                result_type="PERFORMANCE",
                result_id="perf-123",
                deactivated_by="",
                reason="Test",
            )
        assert "deactivated_by" in str(exc.value)

    def test_deactivate_missing_reason(self, service):
        """reason 누락"""
        service.create_version(
            result_type="PERFORMANCE",
            result_id="perf-123",
        )

        with pytest.raises(VersionError) as exc:
            service.deactivate_version(
                result_type="PERFORMANCE",
                result_id="perf-123",
                deactivated_by="admin",
                reason="",
            )
        assert "reason" in str(exc.value)


class TestGetActiveVersion:
    """get_active_version 테스트"""

    def test_get_active_version(self, service):
        """활성 버전 조회"""
        service.create_version(
            result_type="EXPLANATION",
            result_id="exp-123",
        )

        active = service.get_active_version("EXPLANATION", "exp-123")
        assert active is not None
        assert active.is_active is True

    def test_get_active_version_none(self, service):
        """활성 버전 없음"""
        active = service.get_active_version("EXPLANATION", "nonexistent")
        assert active is None

    def test_get_active_version_or_raise(self, service):
        """활성 버전 조회 (없으면 예외)"""
        with pytest.raises(ActiveVersionNotFoundError):
            service.get_active_version_or_raise("EXPLANATION", "nonexistent")


class TestGetVersionHistory:
    """get_version_history 테스트"""

    def test_get_version_history(self, service):
        """버전 이력 조회"""
        # 3개 버전 생성
        for _ in range(3):
            service.create_version(
                result_type="SIMULATION",
                result_id="sim-history",
                deactivated_by="admin",
                deactivate_reason="New version",
            )

        history = service.get_version_history("SIMULATION", "sim-history")

        assert len(history) == 3
        # 최신순 정렬 확인
        assert history[0].version_no == 3
        assert history[1].version_no == 2
        assert history[2].version_no == 1

    def test_get_version_history_exclude_active(self, service):
        """활성 버전 제외 이력 조회"""
        for _ in range(3):
            service.create_version(
                result_type="SIMULATION",
                result_id="sim-history",
                deactivated_by="admin",
                deactivate_reason="New version",
            )

        history = service.get_version_history(
            "SIMULATION", "sim-history", include_active=False
        )

        assert len(history) == 2  # 활성 버전 제외


class TestGetVersionByNo:
    """get_version_by_no 테스트"""

    def test_get_version_by_no(self, service):
        """특정 버전 번호로 조회"""
        service.create_version(result_type="SIMULATION", result_id="sim-123")
        service.create_version(
            result_type="SIMULATION",
            result_id="sim-123",
            deactivated_by="admin",
            deactivate_reason="v2",
        )

        v1 = service.get_version_by_no("SIMULATION", "sim-123", 1)
        v2 = service.get_version_by_no("SIMULATION", "sim-123", 2)

        assert v1.version_no == 1
        assert v2.version_no == 2

    def test_get_version_by_no_not_found(self, service):
        """존재하지 않는 버전 번호"""
        result = service.get_version_by_no("SIMULATION", "sim-123", 999)
        assert result is None


class TestCountVersions:
    """count_versions 테스트"""

    def test_count_versions(self, service):
        """버전 수 조회"""
        for _ in range(5):
            service.create_version(
                result_type="PERFORMANCE",
                result_id="perf-count",
                deactivated_by="admin",
                deactivate_reason="test",
            )

        count = service.count_versions("PERFORMANCE", "perf-count")
        assert count == 5


class TestValidateSingleActive:
    """validate_single_active 테스트"""

    def test_single_active_valid(self, service):
        """단일 활성 버전 - 정상"""
        service.create_version(
            result_type="SIMULATION",
            result_id="sim-validate",
        )

        is_valid = service.validate_single_active("SIMULATION", "sim-validate")
        assert is_valid is True

    def test_duplicate_active_invalid(self, service, db_session):
        """중복 활성 버전 - 오류"""
        # 강제로 중복 활성 버전 생성
        v1 = ResultVersion(
            result_type="SIMULATION",
            result_id="sim-dup",
            version_no=1,
            is_active=True,
        )
        v2 = ResultVersion(
            result_type="SIMULATION",
            result_id="sim-dup",
            version_no=2,
            is_active=True,
        )
        db_session.add_all([v1, v2])
        db_session.commit()

        with pytest.raises(DuplicateActiveVersionError):
            service.validate_single_active("SIMULATION", "sim-dup")


class TestGetAllActiveVersions:
    """get_all_active_versions 테스트"""

    def test_get_all_active_versions(self, service):
        """모든 활성 버전 조회"""
        service.create_version(result_type="SIMULATION", result_id="sim-1")
        service.create_version(result_type="PERFORMANCE", result_id="perf-1")
        service.create_version(result_type="EXPLANATION", result_id="exp-1")

        all_active = service.get_all_active_versions()
        assert len(all_active) == 3

    def test_get_all_active_versions_filtered(self, service):
        """결과 유형별 활성 버전 조회"""
        service.create_version(result_type="SIMULATION", result_id="sim-1")
        service.create_version(result_type="SIMULATION", result_id="sim-2")
        service.create_version(result_type="PERFORMANCE", result_id="perf-1")

        sim_active = service.get_all_active_versions(result_type="SIMULATION")
        assert len(sim_active) == 2


class TestGetVersionsByExecution:
    """get_versions_by_execution 테스트"""

    def test_get_versions_by_execution(self, service):
        """배치 실행으로 생성된 버전 조회"""
        exec_id = "exec-test-123"

        service.create_version(
            result_type="SIMULATION",
            result_id="sim-1",
            execution_id=exec_id,
        )
        service.create_version(
            result_type="PERFORMANCE",
            result_id="perf-1",
            execution_id=exec_id,
        )
        service.create_version(
            result_type="EXPLANATION",
            result_id="exp-1",
            execution_id="other-exec",
        )

        versions = service.get_versions_by_execution(exec_id)
        assert len(versions) == 2


class TestReactivateVersion:
    """reactivate_version 테스트"""

    def test_reactivate_version(self, service):
        """이전 버전 재활성화"""
        v1 = service.create_version(result_type="SIMULATION", result_id="sim-react")
        v2 = service.create_version(
            result_type="SIMULATION",
            result_id="sim-react",
            deactivated_by="admin",
            deactivate_reason="v2 created",
        )

        # v1 재활성화
        reactivated = service.reactivate_version(
            version_id=v1.version_id,
            reactivated_by="admin",
            reason="Rollback to v1",
        )

        assert reactivated.is_active is True
        assert reactivated.version_no == 1

        # v2 비활성화 확인
        v2_updated = service.get_version_by_id(v2.version_id)
        assert v2_updated.is_active is False

    def test_reactivate_already_active(self, service):
        """이미 활성인 버전 재활성화 시도"""
        v1 = service.create_version(result_type="SIMULATION", result_id="sim-react")

        with pytest.raises(VersionError) as exc:
            service.reactivate_version(
                version_id=v1.version_id,
                reactivated_by="admin",
                reason="Test",
            )
        assert "already active" in str(exc.value)

    def test_reactivate_nonexistent_version(self, service):
        """존재하지 않는 버전 재활성화"""
        with pytest.raises(VersionError) as exc:
            service.reactivate_version(
                version_id=99999,
                reactivated_by="admin",
                reason="Test",
            )
        assert "not found" in str(exc.value)


class TestResultType:
    """ResultType Enum 테스트"""

    def test_result_type_values(self):
        """ResultType 값 확인"""
        assert ResultType.SIMULATION.value == "SIMULATION"
        assert ResultType.PERFORMANCE.value == "PERFORMANCE"
        assert ResultType.EXPLANATION.value == "EXPLANATION"
