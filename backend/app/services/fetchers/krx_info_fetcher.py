"""
Phase 11 Level 2: KRX 정보데이터시스템 Fetcher

목적: 한국거래소 정보데이터시스템 데이터 연동
작성일: 2026-01-24

지원 데이터:
- 업종 분류 (SECTOR_CLASSIFICATION)
- 기관/외국인 매매 (INSTITUTION_TRADE)
- ETF 포트폴리오 (ETF_PORTFOLIO)
"""

import time
from datetime import date
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .base_fetcher import BaseFetcher, DataType, FetcherError, FetchResult


class KrxApiError(Exception):
    """KRX API 오류"""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


# KRX OTP 생성 URL
OTP_URL = "http://data.krx.co.kr/comm/fileDn/GenerateOTP/generate.cmd"
# KRX 데이터 다운로드 URL
DOWNLOAD_URL = "http://data.krx.co.kr/comm/fileDn/download_csv/download.cmd"
# KRX JSON 데이터 URL
JSON_URL = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"

# 시장 구분
MARKET_CODES = {
    "ALL": "ALL",
    "KOSPI": "STK",
    "KOSDAQ": "KSQ",
    "KONEX": "KNX",
}


class KrxInfoFetcher(BaseFetcher):
    """
    KRX 정보데이터시스템 Fetcher

    한국거래소 정보데이터시스템에서 데이터를 조회합니다.
    - 업종 분류 (KRX, GICS 분류)
    - 기관/외국인 매매 동향
    - ETF 포트폴리오 구성

    특징:
    - OTP 기반 인증
    - CSV/JSON 형식 다운로드
    """

    source_id = "KRX_INFO"
    source_name = "KRX 정보데이터시스템"
    supported_data_types = [
        DataType.SECTOR_CLASSIFICATION,
        DataType.INSTITUTION_TRADE,
        DataType.ETF_PORTFOLIO,
        DataType.STOCK_INFO,
    ]

    def __init__(self):
        """초기화"""
        self._session = self._create_session()

        # Rate limiting
        self._last_call_time: float = 0
        self._call_interval: float = 0.5  # 초당 2회

    def _create_session(self) -> requests.Session:
        """재시도 로직이 포함된 세션 생성"""
        session = requests.Session()

        # 재시도 설정
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # 헤더 설정 (브라우저처럼 보이게)
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": "http://data.krx.co.kr/",
            }
        )

        return session

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
            if data_type == DataType.SECTOR_CLASSIFICATION:
                return self._fetch_sector_classification(params)
            elif data_type == DataType.INSTITUTION_TRADE:
                return self._fetch_institution_trade(params)
            elif data_type == DataType.ETF_PORTFOLIO:
                return self._fetch_etf_portfolio(params)
            elif data_type == DataType.STOCK_INFO:
                return self._fetch_stock_info(params)
            else:
                return FetchResult.error_result(
                    error_message=f"지원하지 않는 데이터 유형: {data_type}",
                    source_id=self.source_id,
                    data_type=data_type,
                    params=params,
                )

        except KrxApiError as e:
            return FetchResult.error_result(
                error_message=f"KRX API 오류: {e.message}",
                source_id=self.source_id,
                data_type=data_type,
                params=params,
            )
        except requests.RequestException as e:
            return FetchResult.error_result(
                error_message=f"네트워크 오류: {str(e)}",
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

        if data_type == DataType.SECTOR_CLASSIFICATION:
            required = ["as_of_date"]
            for key in required:
                if key not in params:
                    errors.append(f"필수 파라미터 누락: {key}")

        elif data_type == DataType.INSTITUTION_TRADE:
            required = ["trade_date", "as_of_date"]
            for key in required:
                if key not in params:
                    errors.append(f"필수 파라미터 누락: {key}")

        elif data_type == DataType.ETF_PORTFOLIO:
            required = ["etf_ticker", "as_of_date"]
            for key in required:
                if key not in params:
                    errors.append(f"필수 파라미터 누락: {key}")

        return errors

    def get_required_params(self, data_type: DataType) -> List[str]:
        """데이터 유형별 필수 파라미터"""
        if data_type == DataType.SECTOR_CLASSIFICATION:
            return ["as_of_date"]
        elif data_type == DataType.INSTITUTION_TRADE:
            return ["trade_date", "as_of_date"]
        elif data_type == DataType.ETF_PORTFOLIO:
            return ["etf_ticker", "as_of_date"]
        elif data_type == DataType.STOCK_INFO:
            return ["as_of_date"]
        return []

    def _rate_limit_wait(self) -> None:
        """Rate limit 대기"""
        elapsed = time.time() - self._last_call_time
        if elapsed < self._call_interval:
            time.sleep(self._call_interval - elapsed)
        self._last_call_time = time.time()

    def _get_otp(self, bld: str, params: Dict[str, Any]) -> str:
        """OTP 토큰 생성"""
        self._rate_limit_wait()

        otp_params = {"bld": bld, "name": "fileDown", "filetype": "csv"}
        otp_params.update(params)

        response = self._session.post(OTP_URL, data=otp_params, timeout=30)
        response.raise_for_status()

        otp = response.text.strip()
        if not otp:
            raise KrxApiError("OTP 생성 실패")

        return otp

    def _call_json_api(self, bld: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """KRX JSON API 호출"""
        self._rate_limit_wait()

        params["bld"] = bld

        response = self._session.post(JSON_URL, data=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        if not data:
            raise KrxApiError("빈 응답")

        return data

    def _fetch_sector_classification(self, params: Dict[str, Any]) -> FetchResult:
        """업종 분류 조회"""
        as_of_date = params["as_of_date"]
        market = params.get("market", "ALL")
        ticker = params.get("ticker")

        # 날짜 형식 변환
        if isinstance(as_of_date, date):
            date_str = as_of_date.strftime("%Y%m%d")
        else:
            date_str = as_of_date.replace("-", "")

        market_code = MARKET_CODES.get(market, "ALL")

        api_params = {
            "mktId": market_code,
            "trdDd": date_str,
        }

        # KOSPI 업종별 시세 조회
        bld = "dbms/MDC/STAT/standard/MDCSTAT03901"
        data = self._call_json_api(bld, api_params)

        items = data.get("OutBlock_1", [])
        records = []

        for item in items:
            stock_code = item.get("ISU_SRT_CD", "")

            # 특정 종목만 필터링
            if ticker and stock_code != ticker:
                continue

            record = {
                "ticker": stock_code,
                "stock_name": item.get("ISU_ABBRV", ""),
                "market_type": "KOSPI" if market_code == "STK" else market,
                "krx_sector_code": item.get("IDX_IND_CD", ""),
                "krx_sector_name": item.get("IDX_IND_NM", ""),
                "as_of_date": as_of_date.isoformat() if isinstance(as_of_date, date) else as_of_date,
            }
            records.append(record)

        # KOSDAQ도 조회
        if market in ["ALL", "KOSDAQ"]:
            api_params["mktId"] = "KSQ"
            data = self._call_json_api(bld, api_params)
            items = data.get("OutBlock_1", [])

            for item in items:
                stock_code = item.get("ISU_SRT_CD", "")
                if ticker and stock_code != ticker:
                    continue

                record = {
                    "ticker": stock_code,
                    "stock_name": item.get("ISU_ABBRV", ""),
                    "market_type": "KOSDAQ",
                    "krx_sector_code": item.get("IDX_IND_CD", ""),
                    "krx_sector_name": item.get("IDX_IND_NM", ""),
                    "as_of_date": as_of_date.isoformat() if isinstance(as_of_date, date) else as_of_date,
                }
                records.append(record)

        return FetchResult.success_result(
            data=records,
            source_id=self.source_id,
            data_type=DataType.SECTOR_CLASSIFICATION,
            params=params,
        )

    def _fetch_institution_trade(self, params: Dict[str, Any]) -> FetchResult:
        """기관/외국인 매매 동향 조회"""
        trade_date = params["trade_date"]
        as_of_date = params["as_of_date"]
        market = params.get("market", "KOSPI")
        ticker = params.get("ticker")

        # 날짜 형식 변환
        if isinstance(trade_date, date):
            date_str = trade_date.strftime("%Y%m%d")
        else:
            date_str = trade_date.replace("-", "")

        market_code = MARKET_CODES.get(market, "STK")

        # 투자자별 거래실적 (개별종목)
        bld = "dbms/MDC/STAT/standard/MDCSTAT02203"
        api_params = {
            "mktId": market_code,
            "trdDd": date_str,
            "inqTpCd": "1",  # 거래량
        }

        data = self._call_json_api(bld, api_params)

        items = data.get("OutBlock_1", [])
        records = []

        for item in items:
            stock_code = item.get("ISU_SRT_CD", "")

            # 특정 종목만 필터링
            if ticker and stock_code != ticker:
                continue

            record = {
                "ticker": stock_code,
                "stock_name": item.get("ISU_ABBRV", ""),
                "trade_date": trade_date.isoformat() if isinstance(trade_date, date) else trade_date,
                # 기관
                "institution_buy": self._parse_int(item.get("TRDVOL1", "0")),
                "institution_sell": self._parse_int(item.get("TRDVOL2", "0")),
                "institution_net": self._parse_int(item.get("NETBID1", "0")),
                # 외국인
                "foreign_buy": self._parse_int(item.get("TRDVOL5", "0")),
                "foreign_sell": self._parse_int(item.get("TRDVOL6", "0")),
                "foreign_net": self._parse_int(item.get("NETBID2", "0")),
                # 개인
                "individual_buy": self._parse_int(item.get("TRDVOL3", "0")),
                "individual_sell": self._parse_int(item.get("TRDVOL4", "0")),
                "individual_net": self._parse_int(item.get("NETBID3", "0")),
                "as_of_date": as_of_date.isoformat() if isinstance(as_of_date, date) else as_of_date,
            }
            records.append(record)

        return FetchResult.success_result(
            data=records,
            source_id=self.source_id,
            data_type=DataType.INSTITUTION_TRADE,
            params=params,
        )

    def _fetch_etf_portfolio(self, params: Dict[str, Any]) -> FetchResult:
        """ETF 포트폴리오 구성 조회"""
        etf_ticker = params["etf_ticker"]
        as_of_date = params["as_of_date"]

        # 날짜 형식 변환
        if isinstance(as_of_date, date):
            date_str = as_of_date.strftime("%Y%m%d")
        else:
            date_str = as_of_date.replace("-", "")

        # ETF PDF (구성종목) 조회
        bld = "dbms/MDC/STAT/standard/MDCSTAT05001"
        api_params = {
            "isuCd": etf_ticker,
            "trdDd": date_str,
        }

        data = self._call_json_api(bld, api_params)

        items = data.get("output", [])
        records = []

        for idx, item in enumerate(items):
            record = {
                "etf_ticker": etf_ticker,
                "component_ticker": item.get("ISU_SRT_CD", ""),
                "component_name": item.get("ISU_NM", ""),
                "holding_quantity": self._parse_int(item.get("SHRS", "0")),
                "holding_value": self._parse_int(item.get("EVAL_AMT", "0")),
                "weight": self._parse_float(item.get("COMPST_RTO", "0")),
                "rank": idx + 1,
                "as_of_date": as_of_date.isoformat() if isinstance(as_of_date, date) else as_of_date,
            }
            records.append(record)

        return FetchResult.success_result(
            data=records,
            source_id=self.source_id,
            data_type=DataType.ETF_PORTFOLIO,
            params=params,
        )

    def _fetch_stock_info(self, params: Dict[str, Any]) -> FetchResult:
        """종목 기본 정보 조회"""
        as_of_date = params["as_of_date"]
        market = params.get("market", "ALL")
        ticker = params.get("ticker")

        # 날짜 형식 변환
        if isinstance(as_of_date, date):
            date_str = as_of_date.strftime("%Y%m%d")
        else:
            date_str = as_of_date.replace("-", "")

        records = []

        # KOSPI
        if market in ["ALL", "KOSPI"]:
            bld = "dbms/MDC/STAT/standard/MDCSTAT01501"
            api_params = {
                "mktId": "STK",
                "trdDd": date_str,
            }
            data = self._call_json_api(bld, api_params)

            for item in data.get("OutBlock_1", []):
                stock_code = item.get("ISU_SRT_CD", "")
                if ticker and stock_code != ticker:
                    continue

                record = {
                    "ticker": stock_code,
                    "stock_name": item.get("ISU_ABBRV", ""),
                    "market_type": "KOSPI",
                    "listing_shares": self._parse_int(item.get("LIST_SHRS", "0")),
                    "market_cap": self._parse_int(item.get("MKTCAP", "0")),
                    "as_of_date": as_of_date.isoformat() if isinstance(as_of_date, date) else as_of_date,
                }
                records.append(record)

        # KOSDAQ
        if market in ["ALL", "KOSDAQ"]:
            bld = "dbms/MDC/STAT/standard/MDCSTAT01501"
            api_params = {
                "mktId": "KSQ",
                "trdDd": date_str,
            }
            data = self._call_json_api(bld, api_params)

            for item in data.get("OutBlock_1", []):
                stock_code = item.get("ISU_SRT_CD", "")
                if ticker and stock_code != ticker:
                    continue

                record = {
                    "ticker": stock_code,
                    "stock_name": item.get("ISU_ABBRV", ""),
                    "market_type": "KOSDAQ",
                    "listing_shares": self._parse_int(item.get("LIST_SHRS", "0")),
                    "market_cap": self._parse_int(item.get("MKTCAP", "0")),
                    "as_of_date": as_of_date.isoformat() if isinstance(as_of_date, date) else as_of_date,
                }
                records.append(record)

        return FetchResult.success_result(
            data=records,
            source_id=self.source_id,
            data_type=DataType.STOCK_INFO,
            params=params,
        )

    @staticmethod
    def _parse_int(value: str) -> int:
        """문자열을 정수로 변환"""
        try:
            return int(value.replace(",", "").replace("-", "0"))
        except (ValueError, AttributeError):
            return 0

    @staticmethod
    def _parse_float(value: str) -> float:
        """문자열을 실수로 변환"""
        try:
            return float(value.replace(",", "").replace("-", "0"))
        except (ValueError, AttributeError):
            return 0.0
