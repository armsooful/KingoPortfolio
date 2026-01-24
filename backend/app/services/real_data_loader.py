"""
Phase 11: 실 데이터 적재 서비스

목적: 전체 적재 프로세스 조율
작성일: 2026-01-24

주의사항:
- 실시간 데이터 적재 금지
- 자동 스케줄러 연동 금지
- 모든 적재는 명시적 as_of_date 필요
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.real_data import (
    StockPriceDaily,
    IndexPriceDaily,
    StockInfo,
)
from app.services.batch_manager import BatchManager, BatchStats, BatchType
from app.services.data_quality_validator import (
    DataQualityValidator,
    Severity,
)
from app.services.pykrx_fetcher import (
    PykrxFetcher,
    PykrxFetchError,
    OHLCVRecord,
    IndexOHLCVRecord,
)
from app.utils.structured_logging import get_structured_logger

logger = get_structured_logger(__name__)


class DataLoadError(Exception):
    """데이터 적재 예외"""

    def __init__(self, message: str, batch_id: int = None, detail: str = None):
        self.message = message
        self.batch_id = batch_id
        self.detail = detail
        super().__init__(self.message)


@dataclass
class LoadResult:
    """적재 결과"""

    batch_id: int
    success: bool
    total_records: int
    success_records: int
    failed_records: int
    skipped_records: int
    quality_score: Optional[Decimal] = None
    error_message: Optional[str] = None


class RealDataLoader:
    """실 데이터 적재 서비스"""

    # 기본 데이터 소스
    DEFAULT_SOURCE_ID = "PYKRX"

    def __init__(self, db: Session):
        self.db = db
        self.fetcher = PykrxFetcher()
        self.batch_manager = BatchManager(db)
        self.validator = DataQualityValidator(db)

    def load_stock_prices(
        self,
        tickers: List[str],
        start_date: date,
        end_date: date,
        as_of_date: date,
        operator_id: Optional[str] = None,
        operator_reason: Optional[str] = None,
    ) -> LoadResult:
        """
        주식 일별 시세 적재

        Args:
            tickers: 종목 코드 리스트
            start_date: 조회 시작일
            end_date: 조회 종료일
            as_of_date: 데이터 기준일
            operator_id: 운영자 ID
            operator_reason: 적재 사유

        Returns:
            LoadResult
        """
        # 1. 배치 생성
        batch = self.batch_manager.create_batch(
            batch_type=BatchType.PRICE,
            source_id=self.DEFAULT_SOURCE_ID,
            as_of_date=as_of_date,
            target_start=start_date,
            target_end=end_date,
            operator_id=operator_id,
            operator_reason=operator_reason or f"주식 시세 적재: {len(tickers)}종목",
        )

        logger.info(
            "주식 시세 적재 시작",
            {
                "batch_id": batch.batch_id,
                "tickers": len(tickers),
                "start": str(start_date),
                "end": str(end_date),
            },
        )

        # 2. 배치 시작
        self.batch_manager.start_batch(batch.batch_id)

        stats = BatchStats()
        null_counts: Dict[str, int] = {}
        outlier_count = 0

        try:
            for ticker in tickers:
                try:
                    # 3. pykrx에서 데이터 조회
                    records = self.fetcher.fetch_stock_ohlcv(
                        ticker, start_date, end_date, as_of_date
                    )

                    if not records:
                        logger.warning("데이터 없음", {"ticker": ticker})
                        stats.skipped_records += 1
                        continue

                    # 4. 레코드별 검증 및 적재
                    for record in records:
                        stats.total_records += 1

                        # 품질 검증
                        validation = self.validator.validate_ohlcv(record)

                        if not validation.is_valid:
                            # ERROR: 스킵
                            self.validator.log_quality_issues(
                                batch.batch_id,
                                "stock_price_daily",
                                validation.issues,
                            )
                            stats.failed_records += 1
                            continue

                        if validation.has_warnings:
                            self.validator.log_quality_issues(
                                batch.batch_id,
                                "stock_price_daily",
                                [i for i in validation.issues if i.severity == Severity.WARNING],
                            )
                            outlier_count += 1

                        # 5. DB 적재
                        self._insert_stock_price(record, batch.batch_id, as_of_date, validation.quality_flag)
                        stats.success_records += 1

                except PykrxFetchError as e:
                    logger.warning(
                        "종목 조회 실패",
                        {"ticker": ticker, "error": str(e)},
                    )
                    stats.failed_records += 1

            # 6. 품질 메트릭 계산
            if stats.total_records > 0:
                metrics = self.validator.calculate_quality_metrics(
                    stats.total_records, null_counts, outlier_count
                )
                stats.quality_score = metrics["quality_score"]
                stats.null_ratio = metrics["null_ratio"]
                stats.outlier_ratio = metrics["outlier_ratio"]

            # 7. 배치 완료
            self.batch_manager.complete_batch(batch.batch_id, stats)

            logger.info(
                "주식 시세 적재 완료",
                {
                    "batch_id": batch.batch_id,
                    "total": stats.total_records,
                    "success": stats.success_records,
                    "failed": stats.failed_records,
                },
            )

            return LoadResult(
                batch_id=batch.batch_id,
                success=True,
                total_records=stats.total_records,
                success_records=stats.success_records,
                failed_records=stats.failed_records,
                skipped_records=stats.skipped_records,
                quality_score=stats.quality_score,
            )

        except Exception as e:
            logger.error(
                "주식 시세 적재 실패",
                {"batch_id": batch.batch_id, "error": str(e)},
            )
            self.batch_manager.fail_batch(batch.batch_id, str(e), stats)
            raise DataLoadError(
                f"주식 시세 적재 실패: {e}",
                batch_id=batch.batch_id,
                detail=str(e),
            ) from e

    def load_index_prices(
        self,
        index_codes: List[str],
        start_date: date,
        end_date: date,
        as_of_date: date,
        operator_id: Optional[str] = None,
        operator_reason: Optional[str] = None,
    ) -> LoadResult:
        """
        지수 일별 시세 적재

        Args:
            index_codes: 지수 코드 리스트 (예: ['KOSPI', 'KOSDAQ'])
            start_date: 조회 시작일
            end_date: 조회 종료일
            as_of_date: 데이터 기준일
            operator_id: 운영자 ID
            operator_reason: 적재 사유

        Returns:
            LoadResult
        """
        # 1. 배치 생성
        batch = self.batch_manager.create_batch(
            batch_type=BatchType.INDEX,
            source_id=self.DEFAULT_SOURCE_ID,
            as_of_date=as_of_date,
            target_start=start_date,
            target_end=end_date,
            operator_id=operator_id,
            operator_reason=operator_reason or f"지수 시세 적재: {index_codes}",
        )

        logger.info(
            "지수 시세 적재 시작",
            {
                "batch_id": batch.batch_id,
                "index_codes": index_codes,
            },
        )

        self.batch_manager.start_batch(batch.batch_id)

        stats = BatchStats()
        outlier_count = 0

        try:
            for index_code in index_codes:
                try:
                    records = self.fetcher.fetch_index_ohlcv(
                        index_code, start_date, end_date, as_of_date
                    )

                    if not records:
                        logger.warning("지수 데이터 없음", {"index_code": index_code})
                        stats.skipped_records += 1
                        continue

                    for record in records:
                        stats.total_records += 1

                        validation = self.validator.validate_index_ohlcv(record)

                        if not validation.is_valid:
                            self.validator.log_quality_issues(
                                batch.batch_id,
                                "index_price_daily",
                                validation.issues,
                            )
                            stats.failed_records += 1
                            continue

                        if validation.has_warnings:
                            self.validator.log_quality_issues(
                                batch.batch_id,
                                "index_price_daily",
                                [i for i in validation.issues if i.severity == Severity.WARNING],
                            )
                            outlier_count += 1

                        self._insert_index_price(record, batch.batch_id, as_of_date, validation.quality_flag)
                        stats.success_records += 1

                except PykrxFetchError as e:
                    logger.warning(
                        "지수 조회 실패",
                        {"index_code": index_code, "error": str(e)},
                    )
                    stats.failed_records += 1

            if stats.total_records > 0:
                metrics = self.validator.calculate_quality_metrics(
                    stats.total_records, {}, outlier_count
                )
                stats.quality_score = metrics["quality_score"]
                stats.outlier_ratio = metrics["outlier_ratio"]

            self.batch_manager.complete_batch(batch.batch_id, stats)

            logger.info(
                "지수 시세 적재 완료",
                {
                    "batch_id": batch.batch_id,
                    "total": stats.total_records,
                    "success": stats.success_records,
                },
            )

            return LoadResult(
                batch_id=batch.batch_id,
                success=True,
                total_records=stats.total_records,
                success_records=stats.success_records,
                failed_records=stats.failed_records,
                skipped_records=stats.skipped_records,
                quality_score=stats.quality_score,
            )

        except Exception as e:
            logger.error(
                "지수 시세 적재 실패",
                {"batch_id": batch.batch_id, "error": str(e)},
            )
            self.batch_manager.fail_batch(batch.batch_id, str(e), stats)
            raise DataLoadError(
                f"지수 시세 적재 실패: {e}",
                batch_id=batch.batch_id,
            ) from e

    def load_stock_info(
        self,
        tickers: List[str],
        as_of_date: date,
        operator_id: Optional[str] = None,
        operator_reason: Optional[str] = None,
    ) -> LoadResult:
        """
        종목 기본 정보 적재

        Args:
            tickers: 종목 코드 리스트
            as_of_date: 데이터 기준일
            operator_id: 운영자 ID
            operator_reason: 적재 사유

        Returns:
            LoadResult
        """
        batch = self.batch_manager.create_batch(
            batch_type=BatchType.INFO,
            source_id=self.DEFAULT_SOURCE_ID,
            as_of_date=as_of_date,
            target_start=as_of_date,
            target_end=as_of_date,
            operator_id=operator_id,
            operator_reason=operator_reason or f"종목 정보 적재: {len(tickers)}종목",
        )

        logger.info(
            "종목 정보 적재 시작",
            {"batch_id": batch.batch_id, "tickers": len(tickers)},
        )

        self.batch_manager.start_batch(batch.batch_id)

        stats = BatchStats()

        try:
            for ticker in tickers:
                stats.total_records += 1

                try:
                    info = self.fetcher.fetch_stock_info(ticker, as_of_date)

                    if not info:
                        stats.skipped_records += 1
                        continue

                    self._insert_stock_info(info, batch.batch_id, as_of_date)
                    stats.success_records += 1

                except PykrxFetchError as e:
                    logger.warning(
                        "종목 정보 조회 실패",
                        {"ticker": ticker, "error": str(e)},
                    )
                    stats.failed_records += 1

            self.batch_manager.complete_batch(batch.batch_id, stats)

            logger.info(
                "종목 정보 적재 완료",
                {
                    "batch_id": batch.batch_id,
                    "total": stats.total_records,
                    "success": stats.success_records,
                },
            )

            return LoadResult(
                batch_id=batch.batch_id,
                success=True,
                total_records=stats.total_records,
                success_records=stats.success_records,
                failed_records=stats.failed_records,
                skipped_records=stats.skipped_records,
            )

        except Exception as e:
            logger.error(
                "종목 정보 적재 실패",
                {"batch_id": batch.batch_id, "error": str(e)},
            )
            self.batch_manager.fail_batch(batch.batch_id, str(e), stats)
            raise DataLoadError(
                f"종목 정보 적재 실패: {e}",
                batch_id=batch.batch_id,
            ) from e

    def _insert_stock_price(
        self,
        record: OHLCVRecord,
        batch_id: int,
        as_of_date: date,
        quality_flag: str,
    ) -> None:
        """주식 시세 레코드 삽입 (중복 시 스킵)"""
        price_data = StockPriceDaily(
            ticker=record.ticker,
            trade_date=record.trade_date,
            open_price=record.open_price,
            high_price=record.high_price,
            low_price=record.low_price,
            close_price=record.close_price,
            volume=record.volume,
            trading_value=record.trading_value,
            market_cap=record.market_cap,
            shares_outstanding=record.shares_outstanding,
            change_rate=record.change_rate,
            source_id=self.DEFAULT_SOURCE_ID,
            batch_id=batch_id,
            as_of_date=as_of_date,
            is_verified=False,
            quality_flag=quality_flag,
        )

        # 중복 체크 (ticker, trade_date, source_id)
        existing = (
            self.db.query(StockPriceDaily)
            .filter(
                StockPriceDaily.ticker == record.ticker,
                StockPriceDaily.trade_date == record.trade_date,
                StockPriceDaily.source_id == self.DEFAULT_SOURCE_ID,
            )
            .first()
        )

        if not existing:
            self.db.add(price_data)
            self.db.commit()

    def _insert_index_price(
        self,
        record: IndexOHLCVRecord,
        batch_id: int,
        as_of_date: date,
        quality_flag: str,
    ) -> None:
        """지수 시세 레코드 삽입 (중복 시 스킵)"""
        price_data = IndexPriceDaily(
            index_code=record.index_code,
            trade_date=record.trade_date,
            open_price=record.open_price,
            high_price=record.high_price,
            low_price=record.low_price,
            close_price=record.close_price,
            volume=record.volume,
            trading_value=record.trading_value,
            change_rate=record.change_rate,
            source_id=self.DEFAULT_SOURCE_ID,
            batch_id=batch_id,
            as_of_date=as_of_date,
            is_verified=False,
            quality_flag=quality_flag,
        )

        existing = (
            self.db.query(IndexPriceDaily)
            .filter(
                IndexPriceDaily.index_code == record.index_code,
                IndexPriceDaily.trade_date == record.trade_date,
                IndexPriceDaily.source_id == self.DEFAULT_SOURCE_ID,
            )
            .first()
        )

        if not existing:
            self.db.add(price_data)
            self.db.commit()

    def _insert_stock_info(
        self,
        info,
        batch_id: int,
        as_of_date: date,
    ) -> None:
        """종목 정보 레코드 삽입 (중복 시 스킵)"""
        stock_info = StockInfo(
            ticker=info.ticker,
            as_of_date=as_of_date,
            stock_name=info.stock_name,
            market_type=info.market_type,
            sector_name=info.sector_name,
            listing_date=info.listing_date,
            source_id=self.DEFAULT_SOURCE_ID,
            batch_id=batch_id,
            is_active=True,
        )

        existing = (
            self.db.query(StockInfo)
            .filter(
                StockInfo.ticker == info.ticker,
                StockInfo.as_of_date == as_of_date,
                StockInfo.source_id == self.DEFAULT_SOURCE_ID,
            )
            .first()
        )

        if not existing:
            self.db.add(stock_info)
            self.db.commit()
