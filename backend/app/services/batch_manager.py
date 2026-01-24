"""
Phase 11: 배치 관리 서비스

목적: 데이터 적재 배치 생성, 상태 관리, 완료 처리
작성일: 2026-01-24
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.real_data import DataLoadBatch, DataSource
from app.utils.structured_logging import get_structured_logger

logger = get_structured_logger(__name__)


class BatchStatus(str, Enum):
    """배치 상태"""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class BatchType(str, Enum):
    """배치 유형"""

    PRICE = "PRICE"  # 주식 가격
    INDEX = "INDEX"  # 지수 가격
    INFO = "INFO"  # 종목 정보


@dataclass
class BatchStats:
    """배치 처리 통계"""

    total_records: int = 0
    success_records: int = 0
    failed_records: int = 0
    skipped_records: int = 0
    quality_score: Optional[Decimal] = None
    null_ratio: Optional[Decimal] = None
    outlier_ratio: Optional[Decimal] = None


class BatchManagerError(Exception):
    """배치 관리 예외"""

    def __init__(self, message: str, batch_id: int = None):
        self.message = message
        self.batch_id = batch_id
        super().__init__(self.message)


class BatchManager:
    """데이터 적재 배치 관리자"""

    def __init__(self, db: Session):
        self.db = db

    def create_batch(
        self,
        batch_type: BatchType,
        source_id: str,
        as_of_date: date,
        target_start: date,
        target_end: date,
        operator_id: Optional[str] = None,
        operator_reason: Optional[str] = None,
    ) -> DataLoadBatch:
        """
        새 배치 생성

        Args:
            batch_type: 배치 유형 (PRICE, INDEX, INFO)
            source_id: 데이터 소스 ID (예: 'PYKRX')
            as_of_date: 데이터 기준일
            target_start: 적재 대상 기간 시작
            target_end: 적재 대상 기간 종료
            operator_id: 운영자 ID
            operator_reason: 적재 사유

        Returns:
            생성된 DataLoadBatch
        """
        # 소스 검증
        source = (
            self.db.query(DataSource)
            .filter(DataSource.source_id == source_id)
            .first()
        )
        if not source:
            raise BatchManagerError(f"존재하지 않는 데이터 소스: {source_id}")

        if not source.is_active:
            raise BatchManagerError(f"비활성 데이터 소스: {source_id}")

        # 날짜 검증
        today = date.today()
        if as_of_date > today:
            raise BatchManagerError(
                f"as_of_date({as_of_date})가 오늘({today})보다 큽니다"
            )
        if target_start > target_end:
            raise BatchManagerError(
                f"target_start({target_start})가 target_end({target_end})보다 큽니다"
            )
        if target_end > as_of_date:
            raise BatchManagerError(
                f"target_end({target_end})가 as_of_date({as_of_date})보다 큽니다"
            )

        batch = DataLoadBatch(
            batch_type=batch_type.value,
            source_id=source_id,
            as_of_date=as_of_date,
            target_start=target_start,
            target_end=target_end,
            status=BatchStatus.PENDING.value,
            operator_id=operator_id,
            operator_reason=operator_reason,
        )

        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)

        logger.info(
            "배치 생성 완료",
            {
                "batch_id": batch.batch_id,
                "batch_type": batch_type.value,
                "source_id": source_id,
                "as_of_date": str(as_of_date),
            },
        )

        return batch

    def start_batch(self, batch_id: int) -> DataLoadBatch:
        """
        배치 시작 (PENDING -> RUNNING)

        Args:
            batch_id: 배치 ID

        Returns:
            업데이트된 DataLoadBatch
        """
        batch = self._get_batch(batch_id)

        if batch.status != BatchStatus.PENDING.value:
            raise BatchManagerError(
                f"시작할 수 없는 배치 상태: {batch.status} (PENDING 필요)",
                batch_id=batch_id,
            )

        batch.status = BatchStatus.RUNNING.value
        batch.started_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(batch)

        logger.info("배치 시작", {"batch_id": batch_id})
        return batch

    def complete_batch(self, batch_id: int, stats: BatchStats) -> DataLoadBatch:
        """
        배치 성공 완료 (RUNNING -> SUCCESS)

        Args:
            batch_id: 배치 ID
            stats: 처리 통계

        Returns:
            업데이트된 DataLoadBatch
        """
        batch = self._get_batch(batch_id)

        if batch.status != BatchStatus.RUNNING.value:
            raise BatchManagerError(
                f"완료할 수 없는 배치 상태: {batch.status} (RUNNING 필요)",
                batch_id=batch_id,
            )

        batch.status = BatchStatus.SUCCESS.value
        batch.completed_at = datetime.utcnow()

        # 통계 업데이트
        batch.total_records = stats.total_records
        batch.success_records = stats.success_records
        batch.failed_records = stats.failed_records
        batch.skipped_records = stats.skipped_records
        batch.quality_score = stats.quality_score
        batch.null_ratio = stats.null_ratio
        batch.outlier_ratio = stats.outlier_ratio

        self.db.commit()
        self.db.refresh(batch)

        logger.info(
            "배치 완료",
            {
                "batch_id": batch_id,
                "total": stats.total_records,
                "success": stats.success_records,
                "failed": stats.failed_records,
            },
        )
        return batch

    def fail_batch(
        self, batch_id: int, error_message: str, stats: Optional[BatchStats] = None
    ) -> DataLoadBatch:
        """
        배치 실패 (RUNNING -> FAILED)

        Args:
            batch_id: 배치 ID
            error_message: 에러 메시지
            stats: 처리 통계 (부분 처리된 경우)

        Returns:
            업데이트된 DataLoadBatch
        """
        batch = self._get_batch(batch_id)

        if batch.status not in (
            BatchStatus.PENDING.value,
            BatchStatus.RUNNING.value,
        ):
            raise BatchManagerError(
                f"실패 처리할 수 없는 배치 상태: {batch.status}",
                batch_id=batch_id,
            )

        batch.status = BatchStatus.FAILED.value
        batch.completed_at = datetime.utcnow()
        batch.error_message = error_message

        if stats:
            batch.total_records = stats.total_records
            batch.success_records = stats.success_records
            batch.failed_records = stats.failed_records
            batch.skipped_records = stats.skipped_records

        self.db.commit()
        self.db.refresh(batch)

        logger.warning(
            "배치 실패",
            {"batch_id": batch_id, "error": error_message},
        )
        return batch

    def get_batch(self, batch_id: int) -> Optional[DataLoadBatch]:
        """배치 조회"""
        return (
            self.db.query(DataLoadBatch)
            .filter(DataLoadBatch.batch_id == batch_id)
            .first()
        )

    def _get_batch(self, batch_id: int) -> DataLoadBatch:
        """배치 조회 (필수)"""
        batch = self.get_batch(batch_id)
        if not batch:
            raise BatchManagerError(f"배치를 찾을 수 없습니다: {batch_id}", batch_id)
        return batch

    def list_batches(
        self,
        batch_type: Optional[BatchType] = None,
        source_id: Optional[str] = None,
        status: Optional[BatchStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[DataLoadBatch]:
        """
        배치 목록 조회

        Args:
            batch_type: 배치 유형 필터
            source_id: 소스 ID 필터
            status: 상태 필터
            limit: 최대 조회 수
            offset: 오프셋

        Returns:
            DataLoadBatch 리스트
        """
        query = self.db.query(DataLoadBatch)

        if batch_type:
            query = query.filter(DataLoadBatch.batch_type == batch_type.value)
        if source_id:
            query = query.filter(DataLoadBatch.source_id == source_id)
        if status:
            query = query.filter(DataLoadBatch.status == status.value)

        return (
            query.order_by(DataLoadBatch.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_latest_successful_batch(
        self, batch_type: BatchType, source_id: str
    ) -> Optional[DataLoadBatch]:
        """가장 최근 성공 배치 조회"""
        return (
            self.db.query(DataLoadBatch)
            .filter(
                DataLoadBatch.batch_type == batch_type.value,
                DataLoadBatch.source_id == source_id,
                DataLoadBatch.status == BatchStatus.SUCCESS.value,
            )
            .order_by(DataLoadBatch.as_of_date.desc())
            .first()
        )
