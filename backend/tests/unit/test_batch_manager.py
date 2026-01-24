"""
Phase 11: 배치 관리 서비스 단위 테스트
"""

from datetime import date, datetime

import pytest

from app.models.real_data import DataSource, DataLoadBatch
from app.services.batch_manager import (
    BatchManager,
    BatchManagerError,
    BatchStats,
    BatchStatus,
    BatchType,
)


class TestBatchManager:
    """BatchManager 테스트"""

    @pytest.fixture
    def batch_manager(self, db):
        return BatchManager(db)

    @pytest.fixture
    def data_source(self, db):
        """테스트용 데이터 소스"""
        source = DataSource(
            source_id="TEST",
            source_name="테스트 소스",
            source_type="VENDOR",
            is_active=True,
        )
        db.add(source)
        db.commit()
        return source

    # =========================================================================
    # 배치 생성 테스트
    # =========================================================================

    def test_create_batch_success(self, batch_manager, data_source):
        """배치 생성 성공"""
        batch = batch_manager.create_batch(
            batch_type=BatchType.PRICE,
            source_id="TEST",
            as_of_date=date(2024, 1, 15),
            target_start=date(2024, 1, 1),
            target_end=date(2024, 1, 15),
            operator_id="admin",
            operator_reason="테스트 적재",
        )

        assert batch.batch_id is not None
        assert batch.batch_type == "PRICE"
        assert batch.source_id == "TEST"
        assert batch.status == "PENDING"
        assert batch.as_of_date == date(2024, 1, 15)

    def test_create_batch_invalid_source(self, batch_manager):
        """존재하지 않는 소스로 배치 생성 실패"""
        with pytest.raises(BatchManagerError) as exc_info:
            batch_manager.create_batch(
                batch_type=BatchType.PRICE,
                source_id="INVALID",
                as_of_date=date(2024, 1, 15),
                target_start=date(2024, 1, 1),
                target_end=date(2024, 1, 15),
            )

        assert "존재하지 않는 데이터 소스" in str(exc_info.value)

    def test_create_batch_inactive_source(self, batch_manager, db):
        """비활성 소스로 배치 생성 실패"""
        # 비활성 소스 생성
        source = DataSource(
            source_id="INACTIVE",
            source_name="비활성 소스",
            source_type="VENDOR",
            is_active=False,
        )
        db.add(source)
        db.commit()

        with pytest.raises(BatchManagerError) as exc_info:
            batch_manager.create_batch(
                batch_type=BatchType.PRICE,
                source_id="INACTIVE",
                as_of_date=date(2024, 1, 15),
                target_start=date(2024, 1, 1),
                target_end=date(2024, 1, 15),
            )

        assert "비활성 데이터 소스" in str(exc_info.value)

    def test_create_batch_invalid_date_range(self, batch_manager, data_source):
        """잘못된 날짜 범위로 배치 생성 실패"""
        with pytest.raises(BatchManagerError) as exc_info:
            batch_manager.create_batch(
                batch_type=BatchType.PRICE,
                source_id="TEST",
                as_of_date=date(2024, 1, 15),
                target_start=date(2024, 1, 20),  # start > end
                target_end=date(2024, 1, 15),
            )

        assert "target_start" in str(exc_info.value)

    # =========================================================================
    # 배치 상태 변경 테스트
    # =========================================================================

    def test_start_batch(self, batch_manager, data_source):
        """배치 시작"""
        batch = batch_manager.create_batch(
            batch_type=BatchType.PRICE,
            source_id="TEST",
            as_of_date=date(2024, 1, 15),
            target_start=date(2024, 1, 1),
            target_end=date(2024, 1, 15),
        )

        started_batch = batch_manager.start_batch(batch.batch_id)

        assert started_batch.status == "RUNNING"
        assert started_batch.started_at is not None

    def test_start_batch_invalid_status(self, batch_manager, data_source):
        """이미 시작된 배치 재시작 실패"""
        batch = batch_manager.create_batch(
            batch_type=BatchType.PRICE,
            source_id="TEST",
            as_of_date=date(2024, 1, 15),
            target_start=date(2024, 1, 1),
            target_end=date(2024, 1, 15),
        )
        batch_manager.start_batch(batch.batch_id)

        with pytest.raises(BatchManagerError) as exc_info:
            batch_manager.start_batch(batch.batch_id)

        assert "시작할 수 없는 배치 상태" in str(exc_info.value)

    def test_complete_batch(self, batch_manager, data_source):
        """배치 완료"""
        batch = batch_manager.create_batch(
            batch_type=BatchType.PRICE,
            source_id="TEST",
            as_of_date=date(2024, 1, 15),
            target_start=date(2024, 1, 1),
            target_end=date(2024, 1, 15),
        )
        batch_manager.start_batch(batch.batch_id)

        stats = BatchStats(
            total_records=100,
            success_records=95,
            failed_records=5,
            skipped_records=0,
        )
        completed_batch = batch_manager.complete_batch(batch.batch_id, stats)

        assert completed_batch.status == "SUCCESS"
        assert completed_batch.total_records == 100
        assert completed_batch.success_records == 95
        assert completed_batch.completed_at is not None

    def test_fail_batch(self, batch_manager, data_source):
        """배치 실패"""
        batch = batch_manager.create_batch(
            batch_type=BatchType.PRICE,
            source_id="TEST",
            as_of_date=date(2024, 1, 15),
            target_start=date(2024, 1, 1),
            target_end=date(2024, 1, 15),
        )
        batch_manager.start_batch(batch.batch_id)

        failed_batch = batch_manager.fail_batch(
            batch.batch_id,
            error_message="테스트 에러",
        )

        assert failed_batch.status == "FAILED"
        assert failed_batch.error_message == "테스트 에러"

    # =========================================================================
    # 배치 조회 테스트
    # =========================================================================

    def test_get_batch(self, batch_manager, data_source):
        """배치 조회"""
        batch = batch_manager.create_batch(
            batch_type=BatchType.PRICE,
            source_id="TEST",
            as_of_date=date(2024, 1, 15),
            target_start=date(2024, 1, 1),
            target_end=date(2024, 1, 15),
        )

        found_batch = batch_manager.get_batch(batch.batch_id)

        assert found_batch is not None
        assert found_batch.batch_id == batch.batch_id

    def test_get_batch_not_found(self, batch_manager):
        """존재하지 않는 배치 조회"""
        batch = batch_manager.get_batch(99999)
        assert batch is None

    def test_list_batches(self, batch_manager, data_source):
        """배치 목록 조회"""
        # 여러 배치 생성
        for i in range(3):
            batch_manager.create_batch(
                batch_type=BatchType.PRICE,
                source_id="TEST",
                as_of_date=date(2024, 1, 15),
                target_start=date(2024, 1, 1),
                target_end=date(2024, 1, 15),
            )

        batches = batch_manager.list_batches()

        assert len(batches) >= 3

    def test_list_batches_with_filter(self, batch_manager, data_source):
        """필터링된 배치 목록 조회"""
        batch = batch_manager.create_batch(
            batch_type=BatchType.PRICE,
            source_id="TEST",
            as_of_date=date(2024, 1, 15),
            target_start=date(2024, 1, 1),
            target_end=date(2024, 1, 15),
        )
        batch_manager.start_batch(batch.batch_id)

        running_batches = batch_manager.list_batches(status=BatchStatus.RUNNING)

        assert all(b.status == "RUNNING" for b in running_batches)
