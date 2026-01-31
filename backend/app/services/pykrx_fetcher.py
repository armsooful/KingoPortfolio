"""
Phase 11: pykrx 연동 래퍼

목적: pykrx 라이브러리를 감싸서 일관된 인터페이스 제공
작성일: 2026-01-24

주의사항:
- 실시간 데이터 조회 금지
- 모든 조회는 과거 데이터만
- as_of_date 명시적 전달
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from pykrx import stock

from app.utils.structured_logging import get_structured_logger

logger = get_structured_logger(__name__)


class PykrxFetchError(Exception):
    """pykrx 조회 실패 예외"""

    def __init__(self, message: str, ticker: str = None, detail: str = None):
        self.message = message
        self.ticker = ticker
        self.detail = detail
        super().__init__(self.message)


@dataclass
class OHLCVRecord:
    """일별 OHLCV 레코드"""

    ticker: str
    trade_date: date
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: int
    adj_close_price: Optional[Decimal] = None
    trading_value: Optional[int] = None
    market_cap: Optional[int] = None
    shares_outstanding: Optional[int] = None
    prev_close: Optional[Decimal] = None
    price_change: Optional[Decimal] = None
    change_rate: Optional[Decimal] = None


@dataclass
class IndexOHLCVRecord:
    """지수 일별 OHLCV 레코드"""

    index_code: str
    trade_date: date
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Optional[int] = None
    trading_value: Optional[int] = None
    prev_close: Optional[Decimal] = None
    price_change: Optional[Decimal] = None
    change_rate: Optional[Decimal] = None


@dataclass
class StockInfoRecord:
    """종목 기본 정보 레코드"""

    ticker: str
    stock_name: str
    market_type: str  # KOSPI, KOSDAQ
    sector_name: Optional[str] = None
    listing_date: Optional[date] = None


class PykrxFetcher:
    """pykrx 데이터 조회 래퍼"""

    # 지원 지수 코드 매핑
    INDEX_CODES = {
        "KOSPI": "1001",  # 코스피
        "KOSDAQ": "2001",  # 코스닥
        "KS200": "1028",  # 코스피 200
        "KQ150": "2203",  # 코스닥 150
    }

    def __init__(self):
        self._today = date.today()

    def _validate_date_range(
        self, start: date, end: date, as_of: date, operation: str
    ) -> None:
        """날짜 범위 검증"""
        if start > end:
            raise PykrxFetchError(
                f"{operation}: start_date({start})가 end_date({end})보다 큽니다"
            )
        if end > as_of:
            raise PykrxFetchError(
                f"{operation}: end_date({end})가 as_of_date({as_of})보다 큽니다"
            )
        if as_of > self._today:
            raise PykrxFetchError(
                f"{operation}: as_of_date({as_of})가 오늘({self._today})보다 큽니다"
            )

    def _format_date(self, d: date) -> str:
        """날짜를 pykrx 형식(YYYYMMDD)으로 변환"""
        return d.strftime("%Y%m%d")

    def _parse_date(self, date_str: str) -> date:
        """pykrx 날짜 문자열을 date로 변환"""
        return datetime.strptime(date_str, "%Y%m%d").date()

    def fetch_stock_ohlcv(
        self,
        ticker: str,
        start: date,
        end: date,
        as_of: date,
    ) -> List[OHLCVRecord]:
        """
        주식 일별 OHLCV 조회

        Args:
            ticker: 종목 코드 (예: '005930')
            start: 조회 시작일
            end: 조회 종료일
            as_of: 데이터 기준일 (end보다 같거나 커야 함)

        Returns:
            OHLCVRecord 리스트
        """
        self._validate_date_range(start, end, as_of, "fetch_stock_ohlcv")

        try:
            logger.debug(
                "주식 OHLCV 조회",
                {"ticker": ticker, "start": str(start), "end": str(end)},
            )

            # OHLCV 조회
            df_ohlcv = stock.get_market_ohlcv(
                self._format_date(start), self._format_date(end), ticker
            )

            if df_ohlcv.empty:
                logger.warning("OHLCV 데이터 없음", {"ticker": ticker})
                return []

            # 시가총액/상장주식수 조회
            df_cap = stock.get_market_cap(
                self._format_date(start), self._format_date(end), ticker
            )

            records = []
            for idx in df_ohlcv.index:
                trade_date = idx.date() if hasattr(idx, "date") else idx

                # OHLCV 데이터
                row = df_ohlcv.loc[idx]
                open_price = Decimal(str(row["시가"]))
                high_price = Decimal(str(row["고가"]))
                low_price = Decimal(str(row["저가"]))
                close_price = Decimal(str(row["종가"]))
                volume = int(row["거래량"])

                # 시가총액 데이터 (있으면)
                market_cap = None
                shares = None
                trading_value = None

                if not df_cap.empty and idx in df_cap.index:
                    cap_row = df_cap.loc[idx]
                    market_cap = int(cap_row.get("시가총액", 0)) or None
                    shares = int(cap_row.get("상장주식수", 0)) or None

                # 거래대금 계산 (있으면)
                if "거래대금" in row:
                    trading_value = int(row["거래대금"]) or None

                # 등락률 계산 (변동 컬럼이 있는 경우)
                change_rate = None
                if "등락률" in row:
                    change_rate = Decimal(str(row["등락률"]))

                records.append(
                    OHLCVRecord(
                        ticker=ticker,
                        trade_date=trade_date,
                        open_price=open_price,
                        high_price=high_price,
                        low_price=low_price,
                        close_price=close_price,
                        adj_close_price=close_price,
                        volume=volume,
                        trading_value=trading_value,
                        market_cap=market_cap,
                        shares_outstanding=shares,
                        change_rate=change_rate,
                    )
                )

            logger.info(
                "주식 OHLCV 조회 완료",
                {"ticker": ticker, "count": len(records)},
            )
            return records

        except Exception as e:
            logger.error(
                "주식 OHLCV 조회 실패",
                {"ticker": ticker, "error": str(e)},
            )
            raise PykrxFetchError(
                f"주식 OHLCV 조회 실패: {ticker}",
                ticker=ticker,
                detail=str(e),
            ) from e

    def fetch_index_ohlcv(
        self,
        index_code: str,
        start: date,
        end: date,
        as_of: date,
    ) -> List[IndexOHLCVRecord]:
        """
        지수 일별 OHLCV 조회

        Args:
            index_code: 지수 코드 (예: 'KOSPI', 'KS200')
            start: 조회 시작일
            end: 조회 종료일
            as_of: 데이터 기준일

        Returns:
            IndexOHLCVRecord 리스트
        """
        self._validate_date_range(start, end, as_of, "fetch_index_ohlcv")

        # 지수 코드 변환
        pykrx_code = self.INDEX_CODES.get(index_code.upper())
        if not pykrx_code:
            raise PykrxFetchError(
                f"지원하지 않는 지수 코드: {index_code}. "
                f"지원 코드: {list(self.INDEX_CODES.keys())}"
            )

        try:
            logger.debug(
                "지수 OHLCV 조회",
                {"index_code": index_code, "start": str(start), "end": str(end)},
            )

            df = stock.get_index_ohlcv(
                self._format_date(start), self._format_date(end), pykrx_code
            )

            if df.empty:
                logger.warning("지수 OHLCV 데이터 없음", {"index_code": index_code})
                return []

            records = []
            for idx in df.index:
                trade_date = idx.date() if hasattr(idx, "date") else idx
                row = df.loc[idx]

                records.append(
                    IndexOHLCVRecord(
                        index_code=index_code.upper(),
                        trade_date=trade_date,
                        open_price=Decimal(str(row["시가"])),
                        high_price=Decimal(str(row["고가"])),
                        low_price=Decimal(str(row["저가"])),
                        close_price=Decimal(str(row["종가"])),
                        volume=int(row.get("거래량", 0)) or None,
                        trading_value=int(row.get("거래대금", 0)) or None,
                    )
                )

            logger.info(
                "지수 OHLCV 조회 완료",
                {"index_code": index_code, "count": len(records)},
            )
            return records

        except Exception as e:
            logger.error(
                "지수 OHLCV 조회 실패",
                {"index_code": index_code, "error": str(e)},
            )
            raise PykrxFetchError(
                f"지수 OHLCV 조회 실패: {index_code}",
                detail=str(e),
            ) from e

    def fetch_stock_info(self, ticker: str, as_of: date) -> Optional[StockInfoRecord]:
        """
        종목 기본 정보 조회

        Args:
            ticker: 종목 코드
            as_of: 기준일

        Returns:
            StockInfoRecord 또는 None
        """
        if as_of > self._today:
            raise PykrxFetchError(
                f"as_of_date({as_of})가 오늘({self._today})보다 큽니다"
            )

        try:
            logger.debug("종목 정보 조회", {"ticker": ticker, "as_of": str(as_of)})

            # 종목명 조회
            name = stock.get_market_ticker_name(ticker)
            if not name or not isinstance(name, str):
                logger.warning("종목명 조회 실패", {"ticker": ticker})
                return None

            # 시장 구분
            as_of_str = self._format_date(as_of)
            market_type = "UNKNOWN"

            try:
                kospi_tickers = stock.get_market_ticker_list(as_of_str, market="KOSPI")
                if ticker in kospi_tickers:
                    market_type = "KOSPI"
                else:
                    kosdaq_tickers = stock.get_market_ticker_list(
                        as_of_str, market="KOSDAQ"
                    )
                    if ticker in kosdaq_tickers:
                        market_type = "KOSDAQ"
            except Exception:
                pass

            logger.info(
                "종목 정보 조회 완료",
                {"ticker": ticker, "name": name, "market": market_type},
            )

            return StockInfoRecord(
                ticker=ticker,
                stock_name=name,
                market_type=market_type,
            )

        except Exception as e:
            logger.error(
                "종목 정보 조회 실패",
                {"ticker": ticker, "error": str(e)},
            )
            raise PykrxFetchError(
                f"종목 정보 조회 실패: {ticker}",
                ticker=ticker,
                detail=str(e),
            ) from e

    def fetch_market_tickers(self, market: str, as_of: date) -> List[str]:
        """
        시장별 종목 코드 목록 조회

        Args:
            market: 시장 코드 ('KOSPI', 'KOSDAQ', 'ALL')
            as_of: 기준일

        Returns:
            종목 코드 리스트
        """
        if as_of > self._today:
            raise PykrxFetchError(
                f"as_of_date({as_of})가 오늘({self._today})보다 큽니다"
            )

        try:
            as_of_str = self._format_date(as_of)
            market_upper = market.upper()

            if market_upper == "ALL":
                kospi = stock.get_market_ticker_list(as_of_str, market="KOSPI")
                kosdaq = stock.get_market_ticker_list(as_of_str, market="KOSDAQ")
                return list(set(kospi + kosdaq))
            elif market_upper in ("KOSPI", "KOSDAQ"):
                return stock.get_market_ticker_list(as_of_str, market=market_upper)
            else:
                raise PykrxFetchError(f"지원하지 않는 시장: {market}")

        except PykrxFetchError:
            raise
        except Exception as e:
            raise PykrxFetchError(
                f"시장 종목 목록 조회 실패: {market}",
                detail=str(e),
            ) from e
