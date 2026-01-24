"""
Phase 11 Level 2: pykrx Fetcher 어댑터

목적: 기존 pykrx_fetcher를 BaseFetcher 인터페이스로 어댑팅
작성일: 2026-01-24
"""

from datetime import date
from typing import Any, Dict, List

from .base_fetcher import BaseFetcher, DataType, FetcherError, FetchResult
from ..pykrx_fetcher import (
    PykrxFetcher as PykrxFetcherImpl,
    PykrxFetchError,
    OHLCVRecord,
    IndexOHLCVRecord,
    StockInfoRecord,
)


class PykrxFetcher(BaseFetcher):
    """
    pykrx 데이터 소스 Fetcher

    Level 1 데이터:
    - 주식 일별 OHLCV
    - 지수 일별 OHLCV
    - 종목 기본 정보
    - 기본 지표 (PER, PBR, 배당률)
    """

    source_id = "PYKRX"
    source_name = "pykrx 라이브러리"
    supported_data_types = [
        DataType.STOCK_OHLCV,
        DataType.INDEX_OHLCV,
        DataType.STOCK_INFO,
        DataType.FUNDAMENTAL,
    ]

    def __init__(self):
        self._impl = PykrxFetcherImpl()

    def fetch(
        self,
        data_type: DataType,
        params: Dict[str, Any],
    ) -> FetchResult:
        """데이터 조회"""
        # 파라미터 검증
        errors = self.validate_params(data_type, params)
        if errors:
            return FetchResult.error_result(
                error_message="; ".join(errors),
                source_id=self.source_id,
                data_type=data_type,
                params=params,
            )

        try:
            if data_type == DataType.STOCK_OHLCV:
                return self._fetch_stock_ohlcv(params)
            elif data_type == DataType.INDEX_OHLCV:
                return self._fetch_index_ohlcv(params)
            elif data_type == DataType.STOCK_INFO:
                return self._fetch_stock_info(params)
            elif data_type == DataType.FUNDAMENTAL:
                return self._fetch_fundamental(params)
            else:
                return FetchResult.error_result(
                    error_message=f"지원하지 않는 데이터 유형: {data_type}",
                    source_id=self.source_id,
                    data_type=data_type,
                    params=params,
                )

        except PykrxFetchError as e:
            return FetchResult.error_result(
                error_message=e.message,
                source_id=self.source_id,
                data_type=data_type,
                params=params,
            )
        except Exception as e:
            return FetchResult.error_result(
                error_message=f"예상치 못한 오류: {str(e)}",
                source_id=self.source_id,
                data_type=data_type,
                params=params,
            )

    def validate_params(
        self,
        data_type: DataType,
        params: Dict[str, Any],
    ) -> List[str]:
        """파라미터 검증"""
        errors = super().validate_params(data_type, params)

        if data_type == DataType.STOCK_OHLCV:
            required = ["ticker", "start_date", "end_date", "as_of_date"]
            for key in required:
                if key not in params:
                    errors.append(f"필수 파라미터 누락: {key}")

        elif data_type == DataType.INDEX_OHLCV:
            required = ["index_code", "start_date", "end_date", "as_of_date"]
            for key in required:
                if key not in params:
                    errors.append(f"필수 파라미터 누락: {key}")

        elif data_type == DataType.STOCK_INFO:
            required = ["ticker", "as_of_date"]
            for key in required:
                if key not in params:
                    errors.append(f"필수 파라미터 누락: {key}")

        return errors

    def get_required_params(self, data_type: DataType) -> List[str]:
        """데이터 유형별 필수 파라미터"""
        if data_type == DataType.STOCK_OHLCV:
            return ["ticker", "start_date", "end_date", "as_of_date"]
        elif data_type == DataType.INDEX_OHLCV:
            return ["index_code", "start_date", "end_date", "as_of_date"]
        elif data_type == DataType.STOCK_INFO:
            return ["ticker", "as_of_date"]
        elif data_type == DataType.FUNDAMENTAL:
            return ["ticker", "as_of_date"]
        return []

    def _fetch_stock_ohlcv(self, params: Dict[str, Any]) -> FetchResult:
        """주식 OHLCV 조회"""
        ticker = params["ticker"]
        start_date = params["start_date"]
        end_date = params["end_date"]
        as_of_date = params["as_of_date"]

        # date 타입 변환
        if isinstance(start_date, str):
            start_date = date.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)
        if isinstance(as_of_date, str):
            as_of_date = date.fromisoformat(as_of_date)

        records = self._impl.fetch_stock_ohlcv(ticker, start_date, end_date, as_of_date)

        # OHLCVRecord -> Dict 변환
        data = [self._ohlcv_to_dict(r) for r in records]

        return FetchResult.success_result(
            data=data,
            source_id=self.source_id,
            data_type=DataType.STOCK_OHLCV,
            params=params,
        )

    def _fetch_index_ohlcv(self, params: Dict[str, Any]) -> FetchResult:
        """지수 OHLCV 조회"""
        index_code = params["index_code"]
        start_date = params["start_date"]
        end_date = params["end_date"]
        as_of_date = params["as_of_date"]

        if isinstance(start_date, str):
            start_date = date.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)
        if isinstance(as_of_date, str):
            as_of_date = date.fromisoformat(as_of_date)

        records = self._impl.fetch_index_ohlcv(index_code, start_date, end_date, as_of_date)

        data = [self._index_ohlcv_to_dict(r) for r in records]

        return FetchResult.success_result(
            data=data,
            source_id=self.source_id,
            data_type=DataType.INDEX_OHLCV,
            params=params,
        )

    def _fetch_stock_info(self, params: Dict[str, Any]) -> FetchResult:
        """종목 정보 조회"""
        ticker = params["ticker"]
        as_of_date = params["as_of_date"]

        if isinstance(as_of_date, str):
            as_of_date = date.fromisoformat(as_of_date)

        record = self._impl.fetch_stock_info(ticker, as_of_date)

        if not record:
            return FetchResult.success_result(
                data=[],
                source_id=self.source_id,
                data_type=DataType.STOCK_INFO,
                params=params,
            )

        data = [self._stock_info_to_dict(record)]

        return FetchResult.success_result(
            data=data,
            source_id=self.source_id,
            data_type=DataType.STOCK_INFO,
            params=params,
        )

    def _fetch_fundamental(self, params: Dict[str, Any]) -> FetchResult:
        """기본 지표 조회 (PER, PBR 등) - 추후 구현"""
        # pykrx에서 get_market_fundamental로 조회 가능
        # 현재는 stock_info에서 일부 제공
        return FetchResult.error_result(
            error_message="FUNDAMENTAL 조회는 아직 구현되지 않았습니다",
            source_id=self.source_id,
            data_type=DataType.FUNDAMENTAL,
            params=params,
        )

    @staticmethod
    def _ohlcv_to_dict(record: OHLCVRecord) -> Dict[str, Any]:
        """OHLCVRecord를 Dict로 변환"""
        return {
            "ticker": record.ticker,
            "trade_date": record.trade_date.isoformat(),
            "open_price": float(record.open_price),
            "high_price": float(record.high_price),
            "low_price": float(record.low_price),
            "close_price": float(record.close_price),
            "volume": record.volume,
            "trading_value": record.trading_value,
            "market_cap": record.market_cap,
            "shares_outstanding": record.shares_outstanding,
            "change_rate": float(record.change_rate) if record.change_rate else None,
        }

    @staticmethod
    def _index_ohlcv_to_dict(record: IndexOHLCVRecord) -> Dict[str, Any]:
        """IndexOHLCVRecord를 Dict로 변환"""
        return {
            "index_code": record.index_code,
            "trade_date": record.trade_date.isoformat(),
            "open_price": float(record.open_price),
            "high_price": float(record.high_price),
            "low_price": float(record.low_price),
            "close_price": float(record.close_price),
            "volume": record.volume,
            "trading_value": record.trading_value,
            "change_rate": float(record.change_rate) if record.change_rate else None,
        }

    @staticmethod
    def _stock_info_to_dict(record: StockInfoRecord) -> Dict[str, Any]:
        """StockInfoRecord를 Dict로 변환"""
        return {
            "ticker": record.ticker,
            "stock_name": record.stock_name,
            "market_type": record.market_type,
            "sector_name": record.sector_name,
            "listing_date": record.listing_date.isoformat() if record.listing_date else None,
        }
