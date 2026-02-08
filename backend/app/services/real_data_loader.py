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
from typing import Callable, Dict, List, Optional

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
    FdrStockListing,
    FinancialStatement,
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
from app.services.fetchers.fsc_dividend_fetcher import FscDividendFetcher
from app.services.fetchers.bond_basic_info_fetcher import BondBasicInfoFetcher
from app.utils.structured_logging import get_structured_logger

logger = get_structured_logger(__name__)

# 신용등급 코드 → 텍스트 등급 매핑 (FSC API 기준)
_CREDIT_CODE_MAP = {
    "100": "AAA",
    "110": "AA",
    "120": "A",
    "130": "BBB",
    "140": "BB",
    "150": "B",
    "160": "CCC",
}


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
        self.fsc_dividend_fetcher: Optional[FscDividendFetcher] = None
        self.bond_basic_info_fetcher: Optional[BondBasicInfoFetcher] = None
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

    def load_dividend_history_fsc(
        self,
        tickers: List[str],
        bas_dt: Optional[str],
        as_of_date: date,
        operator_id: Optional[str] = None,
        operator_reason: Optional[str] = None,
    ) -> LoadResult:
        """
        배당 이력 적재 (금융위원회_주식배당정보 OpenAPI)

        Args:
            tickers: 종목 코드 리스트
            bas_dt: 기준일자(YYYYMMDD). None이면 회사명 기준 전체 조회
            as_of_date: 데이터 기준일
        """
        if not self.fsc_dividend_fetcher:
            self.fsc_dividend_fetcher = FscDividendFetcher()
        self._ensure_data_source(
            self.fsc_dividend_fetcher.source_id,
            self.fsc_dividend_fetcher.source_name,
            source_type="GOV",
            api_type="REST",
            update_frequency="DAILY",
            license_type="PUBLIC",
            base_url=self.fsc_dividend_fetcher.BASE_URL,
            description="금융위원회_주식배당정보(OpenAPI)",
        )

        batch = self.batch_manager.create_batch(
            batch_type=BatchType.DIVIDEND,
            source_id=self.fsc_dividend_fetcher.source_id,
            as_of_date=as_of_date,
            target_start=as_of_date,
            target_end=as_of_date,
            operator_id=operator_id,
            operator_reason=operator_reason or f"FSC 배당 이력 적재 ({bas_dt or 'company'})",
        )

        logger.info(
            "FSC 배당 이력 적재 시작",
            {"batch_id": batch.batch_id, "bas_dt": bas_dt, "tickers": len(tickers)},
        )

        self.batch_manager.start_batch(batch.batch_id)
        stats = BatchStats()

        from app.models.securities import Stock

        try:
            for ticker in tickers:
                stock = self.db.query(Stock).filter(Stock.ticker == ticker).first()
                base_params = {
                    "basDt": bas_dt,
                    "as_of_date": as_of_date,
                    "ticker": ticker,
                }

                if not stock:
                    logger.warning(
                        "종목 정보 없음 - FSC 배당 조회 스킵",
                        {"ticker": ticker},
                    )
                    stats.skipped_records += 1
                    continue

                if stock.name:
                    result = self.fsc_dividend_fetcher.fetch(
                        DataType.DIVIDEND_HISTORY,
                        {**base_params, "stckIssuCmpyNm": stock.name},
                    )

                    # 회사명 조회 결과가 없으면 crno로 재시도
                    if result.success and not result.data and stock.crno:
                        logger.info(
                            "FSC 배당 회사명 조회 결과 없음 - crno 재시도",
                            {"ticker": ticker, "crno": stock.crno},
                        )
                        result = self.fsc_dividend_fetcher.fetch(
                            DataType.DIVIDEND_HISTORY,
                            {**base_params, "crno": stock.crno},
                        )
                elif stock.crno:
                    logger.info(
                        "종목명 없음 - crno로 FSC 배당 조회",
                        {"ticker": ticker, "crno": stock.crno},
                    )
                    result = self.fsc_dividend_fetcher.fetch(
                        DataType.DIVIDEND_HISTORY,
                        {**base_params, "crno": stock.crno},
                    )
                else:
                    logger.warning(
                        "종목명/법인번호 없음 - FSC 배당 조회 스킵",
                        {"ticker": ticker},
                    )
                    stats.skipped_records += 1
                    continue
                if not result.success:
                    raise DataLoadError(
                        result.error_message or "배당 이력 조회 실패",
                        batch_id=batch.batch_id,
                    )

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
                "FSC 배당 이력 적재 실패",
                {"batch_id": batch.batch_id, "error": str(e)},
            )
            self.batch_manager.fail_batch(batch.batch_id, str(e), stats)
            raise DataLoadError(
                f"FSC 배당 이력 적재 실패: {e}",
                batch_id=batch.batch_id,
            ) from e

    def load_bond_basic_info(
        self,
        crno: Optional[str] = None,
        bond_isur_nm: Optional[str] = None,
        bas_dt: Optional[str] = None,
        limit: Optional[int] = None,
        as_of_date: Optional[date] = None,
        operator_id: Optional[str] = None,
        operator_reason: Optional[str] = None,
    ) -> LoadResult:
        """
        채권기본정보 적재 (금융위원회 OpenAPI)

        Args:
            crno: 법인등록번호
            bond_isur_nm: 발행인명
            bas_dt: 기준일자(YYYYMMDD)
            limit: 조회 건수 제한
            as_of_date: 데이터 기준일
        """
        if as_of_date is None:
            as_of_date = date.today()

        if not self.bond_basic_info_fetcher:
            self.bond_basic_info_fetcher = BondBasicInfoFetcher()

        self._ensure_data_source(
            self.bond_basic_info_fetcher.source_id,
            self.bond_basic_info_fetcher.source_name,
            source_type="GOV",
            api_type="REST",
            update_frequency="DAILY",
            license_type="PUBLIC",
            base_url=self.bond_basic_info_fetcher.BASE_URL,
            description="금융위원회 채권기본정보 OpenAPI",
        )

        batch = self.batch_manager.create_batch(
            batch_type=BatchType.BOND_INFO,
            source_id=self.bond_basic_info_fetcher.source_id,
            as_of_date=as_of_date,
            target_start=as_of_date,
            target_end=as_of_date,
            operator_id=operator_id,
            operator_reason=operator_reason or "FSC 채권기본정보 적재",
        )

        logger.info(
            "채권기본정보 적재 시작",
            {"batch_id": batch.batch_id, "bas_dt": bas_dt, "crno": crno, "bond_isur_nm": bond_isur_nm, "limit": limit},
        )

        self.batch_manager.start_batch(batch.batch_id)
        stats = BatchStats()

        try:
            fetch_params: Dict[str, any] = {"as_of_date": as_of_date}
            if bas_dt:
                fetch_params["basDt"] = bas_dt
            if crno:
                fetch_params["crno"] = crno
            if bond_isur_nm:
                fetch_params["bondIsurNm"] = bond_isur_nm
            if limit is not None:
                fetch_params["limit"] = limit

            result = self.bond_basic_info_fetcher.fetch(
                DataType.BOND_BASIC_INFO,
                fetch_params,
            )

            if not result.success:
                raise DataLoadError(
                    result.error_message or "채권기본정보 조회 실패",
                    batch_id=batch.batch_id,
                )

            logger.info(
                "[BOND] FSC API에서 받은 데이터: 총 %d건",
                len(result.data) if result.data else 0,
            )

            for record in result.data:
                stats.total_records += 1
                inserted = self._upsert_bond(
                    record=record,
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
                "채권기본정보 적재 실패",
                {"batch_id": batch.batch_id, "error": str(e)},
            )
            self.batch_manager.fail_batch(batch.batch_id, str(e), stats)
            raise DataLoadError(
                f"채권기본정보 적재 실패: {e}",
                batch_id=batch.batch_id,
            ) from e

    def load_fdr_stock_listing(
        self,
        market: str,
        as_of_date: date,
        operator_id: Optional[str] = None,
        operator_reason: Optional[str] = None,
    ) -> LoadResult:
        """
        FinanceDataReader 종목 마스터 적재
        """
        try:
            import FinanceDataReader as fdr
        except Exception as e:
            raise DataLoadError(f"FinanceDataReader import 실패: {e}")

        source_id = "FDR"
        self._ensure_data_source(
            source_id,
            "FinanceDataReader",
            source_type="VENDOR",
            api_type="LIB",
            update_frequency="DAILY",
            license_type="OPEN",
            base_url="https://github.com/FinanceData/FinanceDataReader",
            description="FinanceDataReader 종목 마스터",
        )

        batch = self.batch_manager.create_batch(
            batch_type=BatchType.INFO,
            source_id=source_id,
            as_of_date=as_of_date,
            target_start=as_of_date,
            target_end=as_of_date,
            operator_id=operator_id,
            operator_reason=operator_reason or f"FDR 종목 마스터 적재 ({market})",
        )

        logger.info(
            "FDR 종목 마스터 적재 시작",
            {"batch_id": batch.batch_id, "market": market},
        )

        self.batch_manager.start_batch(batch.batch_id)
        stats = BatchStats()

        try:
            markets = [market]
            if market.upper() == "KRX":
                markets = ["KOSPI", "KOSDAQ", "KONEX"]

            import pandas as pd

            def normalize_str(value):
                if value is None:
                    return None
                if isinstance(value, float) and pd.isna(value):
                    return None
                text = str(value).strip()
                if not text or text.lower() == "nan":
                    return None
                return text

            for mkt in markets:
                df = fdr.StockListing(mkt)
                if df is None or df.empty:
                    logger.warning("FDR 종목 목록 비어있음", {"market": mkt})
                    continue

                for _, row in df.iterrows():
                    ticker = normalize_str(row.get("Code"))
                    name = normalize_str(row.get("Name"))
                    if not ticker or not name:
                        continue

                    stats.total_records += 1
                    existing = (
                        self.db.query(FdrStockListing)
                        .filter(
                            FdrStockListing.ticker == ticker,
                            FdrStockListing.as_of_date == as_of_date,
                            FdrStockListing.source_id == source_id,
                        )
                        .first()
                    )
                    if existing:
                        stats.skipped_records += 1
                        continue

                    listing_date = row.get("ListingDate")
                    if hasattr(listing_date, "date"):
                        listing_date = listing_date.date()
                    elif isinstance(listing_date, str):
                        try:
                            listing_date = date.fromisoformat(listing_date.strip())
                        except Exception:
                            listing_date = None

                    shares = row.get("Stocks")
                    try:
                        if shares is None or (isinstance(shares, float) and pd.isna(shares)):
                            shares = None
                        else:
                            shares = int(float(shares))
                    except Exception:
                        shares = None

                    par_value = row.get("ParValue")
                    try:
                        if par_value is None or (isinstance(par_value, float) and pd.isna(par_value)):
                            par_value = None
                        else:
                            par_value = Decimal(str(par_value))
                    except Exception:
                        par_value = None

                    marcap = row.get("Marcap")
                    try:
                        if marcap is None or (isinstance(marcap, float) and pd.isna(marcap)):
                            marcap = None
                        else:
                            marcap = float(marcap)
                    except Exception:
                        marcap = None

                    record = FdrStockListing(
                        ticker=ticker,
                        name=name,
                        market=normalize_str(row.get("Market")) or mkt,
                        sector=normalize_str(row.get("Sector")),
                        industry=normalize_str(row.get("Industry")),
                        listing_date=listing_date,
                        shares=shares,
                        par_value=par_value,
                        marcap=marcap,
                        as_of_date=as_of_date,
                        source_id=source_id,
                        batch_id=batch.batch_id,
                    )
                    self.db.add(record)
                    stats.success_records += 1

            self.db.commit()
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
            self.db.rollback()
            logger.error(
                "FDR 종목 마스터 적재 실패",
                {"batch_id": batch.batch_id, "error": str(e)},
            )
            self.batch_manager.fail_batch(batch.batch_id, str(e), stats)
            raise DataLoadError(
                f"FDR 종목 마스터 적재 실패: {e}",
                batch_id=batch.batch_id,
            ) from e

    def load_stocks_from_fdr(
        self,
        as_of_date: Optional[date] = None,
        limit: Optional[int] = None,
        operator_id: Optional[str] = None,
        operator_reason: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str, Optional[bool], Optional[str]], None]] = None,
    ) -> LoadResult:
        """fdr_stock_listing → pykrx → stocks 단일 파이프라인

        Prerequisites: load_fdr_stock_listing() 실행 완료 (Stage 1)
        """
        source_id = "FDR"
        self._ensure_data_source(
            source_id,
            "FinanceDataReader",
            source_type="VENDOR",
            api_type="LIB",
            update_frequency="DAILY",
            license_type="OPEN",
            base_url="https://github.com/FinanceData/FinanceDataReader",
            description="FinanceDataReader 종목 마스터",
        )

        # as_of_date가 None이면 fdr_stock_listing의 최신 날짜 자동 조회
        if as_of_date is None:
            from sqlalchemy import func as sa_func

            latest = (
                self.db.query(sa_func.max(FdrStockListing.as_of_date))
                .filter(FdrStockListing.source_id == source_id)
                .scalar()
            )
            if latest is None:
                raise DataLoadError(
                    "fdr_stock_listing에 데이터 없음. "
                    "Stage 1(load-stock-listing) 먼저 실행해야 합니다."
                )
            as_of_date = latest

        batch = self.batch_manager.create_batch(
            batch_type=BatchType.INFO,
            source_id=source_id,
            as_of_date=as_of_date,
            target_start=as_of_date,
            target_end=as_of_date,
            operator_id=operator_id,
            operator_reason=operator_reason or "stocks 적재 (fdr → pykrx)",
        )
        self.batch_manager.start_batch(batch.batch_id)
        stats = BatchStats()

        try:
            listings = (
                self.db.query(FdrStockListing)
                .filter(
                    FdrStockListing.as_of_date == as_of_date,
                    FdrStockListing.source_id == source_id,
                )
                .order_by(FdrStockListing.ticker)
                .all()
            )

            if limit:
                listings = listings[:limit]

            # Phase 1: pykrx를 ThreadPoolExecutor로 동시 호출
            # ORM 객체 자체는 스레드에 전달하지 않고 단순 값만 전달
            from concurrent.futures import ThreadPoolExecutor, as_completed

            fetched: Dict[str, Optional[Dict]] = {}
            completed_count = 0
            with ThreadPoolExecutor(max_workers=5) as pool:
                future_to_ticker = {
                    pool.submit(
                        RealDataLoader._fetch_stock_data,
                        lst.ticker, lst.name, lst.marcap or 0,
                    ): lst.ticker
                    for lst in listings
                }
                for future in as_completed(future_to_ticker):
                    ticker = future_to_ticker[future]
                    completed_count += 1
                    try:
                        fetched[ticker] = future.result()
                        # Phase 1: 데이터 수집 완료 로그
                        if progress_callback:
                            progress_callback(completed_count, f"[Phase 1] {ticker} 데이터 수집 완료", True, None)
                    except Exception as e:
                        logger.error(
                            "pykrx fetch 실패",
                            {"ticker": ticker, "error": str(e)},
                        )
                        fetched[ticker] = None
                        # Phase 1: 데이터 수집 실패 로그
                        if progress_callback:
                            progress_callback(completed_count, f"[Phase 1] {ticker} 데이터 수집 실패", False, str(e))

            # Phase 2: 단일 스레드로 DB upsert (100건씩 batch commit)
            _BATCH_SIZE = 100
            pending = 0
            for idx, listing in enumerate(listings, start=1):
                stats.total_records += 1
                data = fetched.get(listing.ticker)
                if data is None:
                    stats.failed_records += 1
                    if progress_callback:
                        progress_callback(idx, f"[Phase 2] {listing.ticker}", False, "데이터 없음")
                    continue
                try:
                    self._apply_stock(listing, data)
                    stats.success_records += 1
                    pending += 1
                    if progress_callback:
                        progress_callback(idx, f"[Phase 2] {listing.ticker}", True, None)
                except Exception as e:
                    logger.error(
                        "stocks upsert 실패",
                        {"ticker": listing.ticker, "error": str(e)},
                    )
                    self.db.rollback()
                    stats.failed_records += 1
                    pending = 0
                    if progress_callback:
                        progress_callback(idx, f"[Phase 2] {listing.ticker}", False, str(e))
                    continue

                if pending >= _BATCH_SIZE:
                    self.db.commit()
                    pending = 0

            if pending > 0:
                self.db.commit()

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
            self.db.rollback()
            self.batch_manager.fail_batch(batch.batch_id, str(e), stats)
            if isinstance(e, DataLoadError):
                raise
            raise DataLoadError(
                f"stocks 적재 실패: {e}",
                batch_id=batch.batch_id,
            ) from e

    @staticmethod
    def _fetch_stock_data(ticker: str, name: str, marcap: float) -> Optional[Dict]:
        """pykrx ohlcv + FDR marcap으로 종목 데이터 수집 (스레드 안전, DB 접근 없음)."""
        from pykrx import stock as krx_stock
        from datetime import datetime, timedelta
        from app.data_collector import DataCollector

        today = datetime.now().strftime('%Y%m%d')
        one_year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        year_start = datetime.now().replace(month=1, day=1).strftime('%Y%m%d')

        try:
            df = krx_stock.get_market_ohlcv(one_year_ago, today, ticker)
            if df.empty:
                yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
                df = krx_stock.get_market_ohlcv(one_year_ago, yesterday, ticker)
            if df.empty:
                return None
        except Exception as e:
            logger.warning("pykrx ohlcv 호출 실패", {"ticker": ticker, "error": str(e)})
            return None

        current_price = float(df['종가'].iloc[-1])

        # 1년 수익률
        one_year_return = None
        if len(df) > 1:
            one_year_return = float(((df['종가'].iloc[-1] - df['종가'].iloc[0]) / df['종가'].iloc[0]) * 100)

        # YTD 수익률 (연초 이후 데이터만)
        ytd_return = None
        ytd_df = df.loc[year_start:]
        if len(ytd_df) > 1:
            ytd_return = float(((ytd_df['종가'].iloc[-1] - ytd_df['종가'].iloc[0]) / ytd_df['종가'].iloc[0]) * 100)

        # crno 조회 (캐시 우선, 스레드 안전)
        crno = DataCollector.get_crno(ticker, name)

        return {
            "ticker": ticker,
            "crno": crno,
            "current_price": current_price,
            "market_cap": marcap or 0,
            "pe_ratio": None,            # DART 파이프라인에서 별도 처리
            "pb_ratio": None,            # DART 파이프라인에서 별도 처리
            "dividend_yield": None,      # FSC/DART 파이프라인에서 별도 처리
            "ytd_return": ytd_return,
            "one_year_return": one_year_return,
            "sector": None,              # fdr_stock_listing.sector 사용
        }

    def _apply_stock(self, listing: FdrStockListing, data: Dict) -> None:
        """stocks 테이블 upsert (단일 스레드). commit은 호출측에서 batch 단위로 수행."""
        from app.models.securities import Stock
        from app.data_collector import DataClassifier

        ticker = listing.ticker
        name = listing.name

        crno = data.get("crno") or None  # 빈 문자열 → None 정규화
        if crno and not listing.crno:
            listing.crno = crno  # fdr_stock_listing backfill

        risk_level = DataClassifier.classify_risk(data.get("pe_ratio"), data.get("dividend_yield"))
        investment_types = DataClassifier.classify_investment_type(risk_level, data.get("dividend_yield"))
        category = DataClassifier.classify_category(name, data.get("sector"))
        investment_type = ",".join(investment_types) if investment_types else "moderate"

        existing = self.db.query(Stock).filter(Stock.ticker == ticker).first()

        if existing:
            existing.current_price = data.get("current_price")
            existing.market_cap = data.get("market_cap")
            if data.get("pe_ratio") is not None:
                existing.pe_ratio = data.get("pe_ratio")
            if data.get("pb_ratio") is not None:
                existing.pb_ratio = data.get("pb_ratio")
            if data.get("dividend_yield") is not None:
                existing.dividend_yield = data.get("dividend_yield")
            existing.ytd_return = data.get("ytd_return")
            existing.one_year_return = data.get("one_year_return")
            existing.risk_level = risk_level
            existing.investment_type = investment_type
            existing.category = category
            if listing.sector:
                existing.sector = listing.sector  # fdr sector 우선 (KRX 공식 분류)
            if crno and not existing.crno:
                existing.crno = crno
            return

        self.db.add(Stock(
            ticker=ticker,
            name=name,
            crno=crno,
            sector=listing.sector or data.get("sector"),
            market=listing.market,
            current_price=data.get("current_price"),
            market_cap=data.get("market_cap"),
            pe_ratio=data.get("pe_ratio"),
            pb_ratio=data.get("pb_ratio"),
            dividend_yield=data.get("dividend_yield"),
            ytd_return=data.get("ytd_return"),
            one_year_return=data.get("one_year_return"),
            risk_level=risk_level,
            investment_type=investment_type,
            category=category,
            description=f"{name} ({category})",
            is_active=True,
        ))

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

    def load_financials_from_dart(
        self,
        fiscal_year: int = 2024,
        report_type: str = "ANNUAL",
        limit: Optional[int] = None,
        operator_id: Optional[str] = None,
        operator_reason: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> "LoadResult":
        """DART 재무제표 적재 + PER/PBR 계산 (stocks 업데이트)

        Pipeline:
          stocks (is_active, market_cap > 0)
            → DART fnlttSinglAcntAll (당기순이익, 자본총계)
            → financial_statement upsert
            → PER = market_cap / net_income
            → PBR = market_cap / total_equity
            → stocks.pe_ratio / pb_ratio 업데이트
        """
        from app.models.securities import Stock

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

        as_of_date = date.today()

        batch = self.batch_manager.create_batch(
            batch_type=BatchType.INFO,
            source_id=self.dart_fetcher.source_id,
            as_of_date=as_of_date,
            target_start=date(fiscal_year, 1, 1),
            target_end=date(fiscal_year, 12, 31),
            operator_id=operator_id,
            operator_reason=operator_reason or f"DART 재무제표 적재 (FY{fiscal_year} {report_type})",
        )

        logger.info(
            "DART 재무제표 적재 시작",
            {"batch_id": batch.batch_id, "fiscal_year": fiscal_year, "report_type": report_type},
        )

        self.batch_manager.start_batch(batch.batch_id)
        stats = BatchStats()

        try:
            # 대상 종목: stocks 테이블 (is_active=True, market_cap > 0), 시가총액 내림차순
            targets = (
                self.db.query(Stock.ticker, Stock.market_cap)
                .filter(Stock.is_active == True, Stock.market_cap > 0)
                .order_by(Stock.market_cap.desc())
                .all()
            )

            if limit:
                targets = targets[:limit]

            _BATCH_SIZE = 50
            pending = 0

            for idx, (ticker, market_cap) in enumerate(targets):
                stats.total_records += 1
                try:
                    result = self.dart_fetcher.fetch(
                        DataType.FINANCIAL_STATEMENT,
                        {
                            "ticker": ticker,
                            "fiscal_year": fiscal_year,
                            "report_type": report_type,
                            "as_of_date": as_of_date,
                        },
                    )

                    if not result.success or not result.data:
                        stats.skipped_records += 1
                        if progress_callback:
                            progress_callback(idx + 1, ticker)
                        continue

                    record = result.data[0]
                    upserted = self._upsert_financials(
                        ticker=ticker,
                        record=record,
                        batch_id=batch.batch_id,
                        as_of_date=as_of_date,
                        source_id=self.dart_fetcher.source_id,
                        market_cap=market_cap,
                    )

                    if upserted:
                        stats.success_records += 1
                        pending += 1
                    else:
                        stats.skipped_records += 1

                    if progress_callback:
                        progress_callback(idx + 1, ticker)

                except Exception as e:
                    logger.error("DART 재무제표 조회 실패", {"ticker": ticker, "error": str(e)})
                    stats.failed_records += 1
                    self.db.rollback()
                    pending = 0
                    if progress_callback:
                        progress_callback(idx + 1, ticker)
                    continue

                if pending >= _BATCH_SIZE:
                    self.db.commit()
                    pending = 0

            if pending > 0:
                self.db.commit()

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
            self.batch_manager.fail_batch(batch.batch_id, str(e), stats)
            raise DataLoadError(
                f"DART 재무제표 적재 실패: {e}",
                batch_id=batch.batch_id,
            ) from e

    def _upsert_financials(
        self,
        ticker: str,
        record: Dict,
        batch_id: int,
        as_of_date: date,
        source_id: str,
        market_cap: float,
    ) -> bool:
        """financial_statement upsert + stocks PER/PBR 업데이트. commit은 caller에서 수행."""
        from app.models.securities import Stock

        fiscal_year = record.get("fiscal_year")
        fiscal_quarter = record.get("fiscal_quarter", 4)
        net_income = record.get("net_income")
        total_equity = record.get("total_equity")

        if net_income is None and total_equity is None:
            return False

        # 1. financial_statement upsert (unique: ticker, fiscal_year, fiscal_quarter, source_id)
        existing = (
            self.db.query(FinancialStatement)
            .filter(
                FinancialStatement.ticker == ticker,
                FinancialStatement.fiscal_year == fiscal_year,
                FinancialStatement.fiscal_quarter == fiscal_quarter,
                FinancialStatement.source_id == source_id,
            )
            .first()
        )

        if existing:
            existing.revenue = record.get("revenue")
            existing.operating_income = record.get("operating_income")
            existing.net_income = net_income
            existing.total_assets = record.get("total_assets")
            existing.total_liabilities = record.get("total_liabilities")
            existing.total_equity = total_equity
            existing.operating_cash_flow = record.get("operating_cash_flow")
            existing.investing_cash_flow = record.get("investing_cash_flow")
            existing.financing_cash_flow = record.get("financing_cash_flow")
            existing.roe = record.get("roe")
            existing.roa = record.get("roa")
            existing.debt_ratio = record.get("debt_ratio")
            existing.dart_rcept_no = record.get("dart_rcept_no")
        else:
            stmt = FinancialStatement(
                ticker=ticker,
                fiscal_year=fiscal_year,
                fiscal_quarter=fiscal_quarter,
                report_type=record.get("report_type", "ANNUAL"),
                revenue=record.get("revenue"),
                operating_income=record.get("operating_income"),
                net_income=net_income,
                total_assets=record.get("total_assets"),
                total_liabilities=record.get("total_liabilities"),
                total_equity=total_equity,
                operating_cash_flow=record.get("operating_cash_flow"),
                investing_cash_flow=record.get("investing_cash_flow"),
                financing_cash_flow=record.get("financing_cash_flow"),
                roe=record.get("roe"),
                roa=record.get("roa"),
                debt_ratio=record.get("debt_ratio"),
                source_id=source_id,
                batch_id=batch_id,
                as_of_date=as_of_date,
                dart_rcept_no=record.get("dart_rcept_no"),
            )
            self.db.add(stmt)

        # 2. PER / PBR 계산 + stocks 업데이트
        stock = self.db.query(Stock).filter(Stock.ticker == ticker).first()
        if stock and market_cap and market_cap > 0:
            stock.pe_ratio = round(market_cap / net_income, 2) if net_income and net_income > 0 else None
            stock.pb_ratio = round(market_cap / total_equity, 2) if total_equity and total_equity > 0 else None

        return True

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
        dvdn_bas_dt = record.get("dvdn_bas_dt") or record.get("record_date")
        existing = (
            self.db.query(DividendHistory)
            .filter(
                DividendHistory.isin_cd == record.get("isin_cd"),
                DividendHistory.dvdn_bas_dt == dvdn_bas_dt,
                DividendHistory.scrs_itms_kcd == record.get("scrs_itms_kcd"),
                DividendHistory.source_id == source_id,
            )
            .first()
        )
        if existing:
            return False

        dividend_data = DividendHistory(
            isin_cd=record.get("isin_cd"),
            isin_cd_nm=record.get("isin_cd_nm"),
            crno=record.get("crno"),
            ticker=record.get("ticker"),
            dvdn_bas_dt=record.get("dvdn_bas_dt") or record.get("record_date"),
            cash_dvdn_pay_dt=record.get("cash_dvdn_pay_dt") or record.get("payment_date"),
            stck_stac_md=record.get("stck_stac_md"),
            scrs_itms_kcd=record.get("scrs_itms_kcd"),
            scrs_itms_kcd_nm=record.get("scrs_itms_kcd_nm"),
            stck_dvdn_rcd=record.get("stck_dvdn_rcd"),
            stck_dvdn_rcd_nm=record.get("stck_dvdn_rcd_nm"),
            stck_genr_dvdn_amt=record.get("stck_genr_dvdn_amt"),
            stck_grdn_dvdn_amt=record.get("stck_grdn_dvdn_amt"),
            stck_genr_cash_dvdn_rt=record.get("stck_genr_cash_dvdn_rt"),
            stck_genr_dvdn_rt=record.get("stck_genr_dvdn_rt"),
            cash_grdn_dvdn_rt=record.get("cash_grdn_dvdn_rt"),
            stck_grdn_dvdn_rt=record.get("stck_grdn_dvdn_rt"),
            stck_par_prc=record.get("stck_par_prc"),
            trsnm_dpty_dcd=record.get("trsnm_dpty_dcd"),
            trsnm_dpty_dcd_nm=record.get("trsnm_dpty_dcd_nm"),
            bas_dt=record.get("bas_dt"),
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

    @staticmethod
    def _map_credit_rating(record: Dict) -> Optional[str]:
        """신용등급 코드 → 텍스트 등급 (KIS > KBP > NICE > FN 우선)"""
        for field in ('kis_scrs_itms_kcd', 'kbp_scrs_itms_kcd', 'nice_scrs_itms_kcd', 'fn_scrs_itms_kcd'):
            code = (record.get(field) or "").strip()
            if not code:
                continue
            if code.isdigit():
                return _CREDIT_CODE_MAP.get(code)
            return code  # 텍스트 등급이면 그대로
        return None

    @staticmethod
    def _derive_bond_fields(record: Dict) -> Dict:
        """실데이터 레코드 → 교육용 컬럼 유도 (bond_type, credit_rating, risk_level, investment_type, interest_rate, maturity_years)"""
        credit_rating = RealDataLoader._map_credit_rating(record)

        # bond_type: scrs_itms_kcd 첫 글자로 판별
        #   1xxx = 회사채/CB, 2xxx = 국채, 3xxx = 특수채(MBS), 4xxx = 지방정부채
        kcd = (record.get("scrs_itms_kcd") or "").strip()
        if kcd and kcd[0] in ("2", "3", "4"):
            bond_type = "government"
        else:
            base = (credit_rating or "").upper().rstrip("+-")
            bond_type = "high_yield" if base in ("BBB", "BB", "B", "CCC", "CC", "C", "D") else "corporate"

        # risk_level + investment_type (기존 시드 패턴과 일치)
        base = (credit_rating or "").upper().rstrip("+-")
        if base in ("AAA", "AA"):
            risk_level, investment_type = "low", "conservative,moderate,aggressive"
        elif base == "A":
            risk_level, investment_type = "low", "conservative,moderate"
        elif base == "BBB":
            risk_level, investment_type = "high", "aggressive"
        elif base in ("BB", "B", "CCC", "CC", "C", "D"):
            risk_level, investment_type = "high", "aggressive"
        else:  # 등급 정보 없음
            risk_level, investment_type = "medium", "moderate,aggressive"

        # interest_rate: FSC API는 백분율 기준 (1.81 = 1.81%)
        interest_rate = None
        raw_rate = record.get("bond_srfc_inrt")
        if raw_rate is not None:
            interest_rate = float(raw_rate)

        # maturity_years: 발행일~만기일 차이로 계산
        maturity_years = None
        issu_dt = record.get("bond_issu_dt")
        expr_dt = record.get("bond_expr_dt")
        if issu_dt and expr_dt:
            maturity_years = max(1, round((expr_dt - issu_dt).days / 365))

        return {
            "bond_type": bond_type,
            "credit_rating": credit_rating,
            "risk_level": risk_level,
            "investment_type": investment_type,
            "interest_rate": interest_rate,
            "maturity_years": maturity_years,
        }

    def _upsert_bond(
        self,
        record: Dict[str, any],
        batch_id: int,
        as_of_date: date,
        source_id: str,
    ) -> bool:
        """채권 upsert (isin_cd 기준). 기존 행이면 실데이터 컬럼 갱신, 없으면 신규 삽입."""
        from app.models.securities import Bond

        isin_cd = record.get("isin_cd")
        if not isin_cd:
            return False

        mapped = self._derive_bond_fields(record)

        # 공통: 실데이터 컬럼 값 준비
        real_data_fields = dict(
            bas_dt=record.get("bas_dt"),
            crno=record.get("crno"),
            scrs_itms_kcd=record.get("scrs_itms_kcd"),
            scrs_itms_kcd_nm=record.get("scrs_itms_kcd_nm"),
            bond_issu_dt=record.get("bond_issu_dt"),
            bond_expr_dt=record.get("bond_expr_dt"),
            bond_issu_amt=record.get("bond_issu_amt"),
            bond_bal=record.get("bond_bal"),
            irt_chng_dcd=record.get("irt_chng_dcd"),
            bond_int_tcd=record.get("bond_int_tcd"),
            int_pay_cycl_ctt=record.get("int_pay_cycl_ctt"),
            nxtm_copn_dt=record.get("nxtm_copn_dt"),
            rbf_copn_dt=record.get("rbf_copn_dt"),
            grn_dcd=record.get("grn_dcd"),
            bond_rnkn_dcd=record.get("bond_rnkn_dcd"),
            kis_scrs_itms_kcd=record.get("kis_scrs_itms_kcd"),
            kbp_scrs_itms_kcd=record.get("kbp_scrs_itms_kcd"),
            nice_scrs_itms_kcd=record.get("nice_scrs_itms_kcd"),
            fn_scrs_itms_kcd=record.get("fn_scrs_itms_kcd"),
            bond_offr_mcd=record.get("bond_offr_mcd"),
            lstg_dt=record.get("lstg_dt"),
            prmnc_bond_yn=record.get("prmnc_bond_yn"),
            strips_psbl_yn=record.get("strips_psbl_yn"),
            source_id=source_id,
            batch_id=batch_id,
            as_of_date=as_of_date,
        )

        existing = self.db.query(Bond).filter(Bond.isin_cd == isin_cd).first()

        if existing:
            # UPDATE: 유도 컬럼 + 실데이터 컬럼 갱신
            existing.name = record.get("isin_cd_nm") or existing.name
            existing.issuer = record.get("bond_isur_nm") or existing.issuer
            existing.bond_type = mapped["bond_type"]
            existing.credit_rating = mapped["credit_rating"] or existing.credit_rating
            existing.risk_level = mapped["risk_level"]
            existing.investment_type = mapped["investment_type"]
            if mapped["interest_rate"] is not None:
                existing.interest_rate = mapped["interest_rate"]
            if mapped["maturity_years"] is not None:
                existing.maturity_years = mapped["maturity_years"]
            existing.is_active = True
            for col, val in real_data_fields.items():
                setattr(existing, col, val)
            self.db.commit()
            return True

        # INSERT: 신규 행
        bond = Bond(
            name=record.get("isin_cd_nm") or isin_cd,
            bond_type=mapped["bond_type"],
            issuer=record.get("bond_isur_nm"),
            interest_rate=mapped["interest_rate"] or 0.0,
            maturity_years=mapped["maturity_years"] or 0,
            credit_rating=mapped["credit_rating"],
            risk_level=mapped["risk_level"],
            investment_type=mapped["investment_type"],
            is_active=True,
            isin_cd=isin_cd,
            **real_data_fields,
        )
        self.db.add(bond)
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
