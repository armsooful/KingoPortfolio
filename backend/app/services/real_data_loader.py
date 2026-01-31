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
    DataSource,
    StockPriceDaily,
    IndexPriceDaily,
    StockInfo,
    DividendHistory,
    CorporateAction,
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
from app.services.fetchers.base_fetcher import DataType, FetcherError
from app.services.fetchers.dart_fetcher import DartFetcher
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
        self.dart_fetcher: Optional[DartFetcher] = None
        self.batch_manager = BatchManager(db)
        self.validator = DataQualityValidator(db)

    def _ensure_data_source(
        self,
        source_id: str,
        source_name: str,
        source_type: str = "VENDOR",
        api_type: Optional[str] = None,
        update_frequency: Optional[str] = None,
        license_type: Optional[str] = None,
        base_url: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        existing = (
            self.db.query(DataSource)
            .filter(DataSource.source_id == source_id)
            .first()
        )
        if existing:
            if not existing.is_active:
                existing.is_active = True
                self.db.commit()
            return

        self.db.add(
            DataSource(
                source_id=source_id,
                source_name=source_name,
                source_type=source_type,
                api_type=api_type,
                update_frequency=update_frequency,
                license_type=license_type,
                base_url=base_url,
                description=description,
                is_active=True,
            )
        )
        self.db.commit()

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

    def load_dividend_history(
        self,
        tickers: List[str],
        fiscal_year: int,
        as_of_date: date,
        operator_id: Optional[str] = None,
        operator_reason: Optional[str] = None,
    ) -> LoadResult:
        """
        배당 이력 적재 (DART)

        Args:
            tickers: 종목 코드 리스트
            fiscal_year: 기준 사업연도
            as_of_date: 데이터 기준일
        """
        if not self.dart_fetcher:
            self.dart_fetcher = DartFetcher()
        self._ensure_data_source(
            self.dart_fetcher.source_id,
            self.dart_fetcher.source_name,
            source_type="VENDOR",
            api_type="REST",
            update_frequency="MANUAL",
            license_type="PUBLIC",
            base_url=self.dart_fetcher.BASE_URL,
            description="DART OpenAPI",
        )

        target_start = date(fiscal_year, 1, 1)
        target_end = date(fiscal_year, 12, 31)

        batch = self.batch_manager.create_batch(
            batch_type=BatchType.DIVIDEND,
            source_id=self.dart_fetcher.source_id,
            as_of_date=as_of_date,
            target_start=target_start,
            target_end=target_end,
            operator_id=operator_id,
            operator_reason=operator_reason or f"배당 이력 적재: {len(tickers)}종목",
        )

        logger.info(
            "배당 이력 적재 시작",
            {"batch_id": batch.batch_id, "tickers": len(tickers), "fiscal_year": fiscal_year},
        )

        self.batch_manager.start_batch(batch.batch_id)
        stats = BatchStats()

        try:
            for ticker in tickers:
                try:
                    result = self.dart_fetcher.fetch(
                        DataType.DIVIDEND_HISTORY,
                        {
                            "ticker": ticker,
                            "fiscal_year": fiscal_year,
                            "as_of_date": as_of_date,
                        },
                    )
                    if not result.success:
                        logger.warning(
                            "배당 이력 조회 실패",
                            {"ticker": ticker, "error": result.error_message},
                        )
                        stats.failed_records += 1
                        continue

                    if not result.data:
                        stats.skipped_records += 1
                        continue

                    for record in result.data:
                        stats.total_records += 1
                        inserted = self._insert_dividend_history(
                            record=record,
                            batch_id=batch.batch_id,
                            as_of_date=as_of_date,
                            source_id=result.source_id,
                        )
                        if inserted:
                            stats.success_records += 1
                        else:
                            stats.skipped_records += 1
                except FetcherError as e:
                    logger.warning(
                        "배당 이력 조회 실패",
                        {"ticker": ticker, "error": str(e)},
                    )
                    stats.failed_records += 1

            self.batch_manager.complete_batch(batch.batch_id, stats)

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
                "배당 이력 적재 실패",
                {"batch_id": batch.batch_id, "error": str(e)},
            )
            self.batch_manager.fail_batch(batch.batch_id, str(e), stats)
            raise DataLoadError(
                f"배당 이력 적재 실패: {e}",
                batch_id=batch.batch_id,
            ) from e

    def load_corporate_actions(
        self,
        start_date: date,
        end_date: date,
        as_of_date: date,
        corp_cls: Optional[str] = None,
        operator_id: Optional[str] = None,
        operator_reason: Optional[str] = None,
    ) -> LoadResult:
        """
        기업 액션 적재 (DART 공시 기반)
        """
        if not self.dart_fetcher:
            self.dart_fetcher = DartFetcher()
        self._ensure_data_source(
            self.dart_fetcher.source_id,
            self.dart_fetcher.source_name,
            source_type="VENDOR",
            api_type="REST",
            update_frequency="MANUAL",
            license_type="PUBLIC",
            base_url=self.dart_fetcher.BASE_URL,
            description="DART OpenAPI",
        )

        batch = self.batch_manager.create_batch(
            batch_type=BatchType.ACTION,
            source_id=self.dart_fetcher.source_id,
            as_of_date=as_of_date,
            target_start=start_date,
            target_end=end_date,
            operator_id=operator_id,
            operator_reason=operator_reason or "기업 액션 적재",
        )

        logger.info(
            "기업 액션 적재 시작",
            {"batch_id": batch.batch_id, "start": str(start_date), "end": str(end_date)},
        )

        self.batch_manager.start_batch(batch.batch_id)
        stats = BatchStats()

        try:
            result = self.dart_fetcher.fetch(
                DataType.DISCLOSURE,
                {
                    "start_date": start_date,
                    "end_date": end_date,
                    "as_of_date": as_of_date,
                    "corp_cls": corp_cls,
                },
            )
            if not result.success:
                raise DataLoadError(result.error_message or "기업 액션 조회 실패", batch_id=batch.batch_id)

            action_keywords = {
                "주식분할": "SPLIT",
                "액면분할": "SPLIT",
                "감자": "REVERSE_SPLIT",
                "합병": "MERGER",
                "분할": "SPINOFF",
            }

            for record in result.data:
                report_name = record.get("report_nm", "") or ""
                action_type = None
                for keyword, mapped in action_keywords.items():
                    if keyword in report_name:
                        action_type = mapped
                        break
                if not action_type:
                    continue

                stats.total_records += 1
                inserted = self._insert_corporate_action(
                    record=record,
                    action_type=action_type,
                    batch_id=batch.batch_id,
                    as_of_date=as_of_date,
                    source_id=result.source_id,
                )
                if inserted:
                    stats.success_records += 1
                else:
                    stats.skipped_records += 1

            self.batch_manager.complete_batch(batch.batch_id, stats)

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
                "기업 액션 적재 실패",
                {"batch_id": batch.batch_id, "error": str(e)},
            )
            self.batch_manager.fail_batch(batch.batch_id, str(e), stats)
            raise DataLoadError(
                f"기업 액션 적재 실패: {e}",
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
            # KRX 기본 소스는 수정종가가 없으므로 종가를 기본값으로 사용
            adj_close_price=record.adj_close_price or record.close_price,
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

    def _insert_dividend_history(
        self,
        record: Dict[str, any],
        batch_id: int,
        as_of_date: date,
        source_id: str,
    ) -> bool:
        """배당 이력 레코드 삽입 (중복 시 스킵)"""
        existing = (
            self.db.query(DividendHistory)
            .filter(
                DividendHistory.ticker == record.get("ticker"),
                DividendHistory.fiscal_year == record.get("fiscal_year"),
                DividendHistory.dividend_type == record.get("dividend_type"),
                DividendHistory.source_id == source_id,
            )
            .first()
        )
        if existing:
            return False

        dividend_data = DividendHistory(
            ticker=record.get("ticker"),
            fiscal_year=record.get("fiscal_year"),
            rcept_no=record.get("rcept_no"),
            corp_cls=record.get("corp_cls"),
            corp_code=record.get("corp_code"),
            corp_name=record.get("corp_name"),
            se=record.get("se"),
            stock_knd=record.get("stock_knd"),
            thstrm=record.get("thstrm"),
            frmtrm=record.get("frmtrm"),
            lwfr=record.get("lwfr"),
            stlm_dt=record.get("stlm_dt"),
            dividend_type=record.get("dividend_type"),
            dividend_per_share=record.get("dividend_per_share"),
            dividend_rate=record.get("dividend_rate"),
            dividend_yield=record.get("dividend_yield"),
            record_date=record.get("record_date"),
            payment_date=record.get("payment_date"),
            ex_dividend_date=record.get("ex_dividend_date"),
            source_id=source_id,
            batch_id=batch_id,
            as_of_date=as_of_date,
        )
        self.db.add(dividend_data)
        try:
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def _insert_corporate_action(
        self,
        record: Dict[str, any],
        action_type: str,
        batch_id: int,
        as_of_date: date,
        source_id: str,
    ) -> bool:
        """기업 액션 레코드 삽입 (중복 시 스킵)"""
        ticker = record.get("stock_code") or record.get("ticker")
        if not ticker:
            return False
        report_date = record.get("rcept_dt")
        effective_date = None
        if report_date:
            try:
                if "-" in report_date or "." in report_date:
                    effective_date = date.fromisoformat(report_date.replace(".", "-"))
                else:
                    effective_date = date.fromisoformat(
                        f"{report_date[0:4]}-{report_date[4:6]}-{report_date[6:8]}"
                    )
            except Exception:
                effective_date = None

        existing = (
            self.db.query(CorporateAction)
            .filter(
                CorporateAction.ticker == ticker,
                CorporateAction.action_type == action_type,
                CorporateAction.effective_date == effective_date,
                CorporateAction.reference_doc == record.get("rcept_no"),
                CorporateAction.source_id == source_id,
            )
            .first()
        )
        if existing:
            return False

        action = CorporateAction(
            ticker=ticker,
            action_type=action_type,
            ratio=None,
            effective_date=effective_date,
            report_name=record.get("report_nm"),
            reference_doc=record.get("rcept_no"),
            source_id=source_id,
            batch_id=batch_id,
            as_of_date=as_of_date,
        )
        self.db.add(action)
        self.db.commit()
        return True

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
