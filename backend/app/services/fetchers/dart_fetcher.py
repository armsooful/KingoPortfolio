"""
Phase 11 Level 2: DART OpenAPI Fetcher

목적: 금융감독원 DART 전자공시시스템 데이터 연동
작성일: 2026-01-24

지원 데이터:
- 재무제표 (FINANCIAL_STATEMENT)
- 배당 정보 (DIVIDEND_HISTORY)
- 공시 정보 (DISCLOSURE)
- 기업 고유번호 (CORP_CODE)
"""

import os
import time
import zipfile
import io
import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

import logging
import requests

from .base_fetcher import BaseFetcher, DataType, FetcherError, FetchResult


class DartApiError(Exception):
    """DART API 오류"""

    def __init__(self, message: str, status_code: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


# DART API 응답 상태 코드
DART_STATUS_CODES = {
    "000": "정상",
    "010": "등록되지 않은 키입니다.",
    "011": "사용할 수 없는 키입니다.",
    "012": "접근할 수 없는 IP입니다.",
    "013": "조회된 데이타가 없습니다.",
    "014": "파일이 존재하지 않습니다.",
    "020": "요청 제한을 초과하였습니다.",
    "100": "필드의 부적절한 값입니다.",
    "800": "원활한 공시서비스를 위하여 오픈API , 다운로드 서비스는 매일 01:00 ~ 02:00 사이에 잠시 중단됩니다.",
    "900": "정의되지 않은 오류입니다.",
}

# 보고서 코드
REPORT_CODES = {
    "ANNUAL": "11011",  # 사업보고서
    "Q1": "11013",  # 1분기보고서
    "Q2": "11012",  # 반기보고서
    "Q3": "11014",  # 3분기보고서
}


class DartFetcher(BaseFetcher):
    """
    DART OpenAPI Fetcher

    금융감독원 DART 전자공시시스템에서 데이터를 조회합니다.
    - 재무제표 (단일회사 전체 재무제표)
    - 배당 정보
    - 공시 목록
    - 기업 고유번호

    API 제한:
    - 일일 10,000건 호출 제한
    - 초당 1건 권장
    """

    BASE_URL = "https://opendart.fss.or.kr/api"

    source_id = "DART"
    source_name = "DART OpenAPI"
    supported_data_types = [
        DataType.FINANCIAL_STATEMENT,
        DataType.DIVIDEND_HISTORY,
        DataType.DISCLOSURE,
        DataType.CORP_CODE,
    ]

    logger = logging.getLogger(__name__)

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: DART API 키. 없으면 환경변수 DART_API_KEY 사용
        """
        self.api_key = api_key or os.getenv("DART_API_KEY", "")
        if not self.api_key:
            raise FetcherError(
                "DART API 키가 설정되지 않았습니다. DART_API_KEY 환경변수를 설정하세요.",
                source_id=self.source_id,
            )

        # ticker -> corp_code 캐시
        self._corp_code_cache: Dict[str, str] = {}

        # Rate limiting
        self._last_call_time: float = 0
        self._call_interval: float = 1.0  # 초당 1회

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
            if data_type == DataType.FINANCIAL_STATEMENT:
                return self._fetch_financial_statement(params)
            elif data_type == DataType.DIVIDEND_HISTORY:
                return self._fetch_dividend(params)
            elif data_type == DataType.DISCLOSURE:
                return self._fetch_disclosure(params)
            elif data_type == DataType.CORP_CODE:
                return self._fetch_corp_codes(params)
            else:
                return FetchResult.error_result(
                    error_message=f"지원하지 않는 데이터 유형: {data_type}",
                    source_id=self.source_id,
                    data_type=data_type,
                    params=params,
                )

        except DartApiError as e:
            return FetchResult.error_result(
                error_message=f"DART API 오류: {e.message}",
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

        if data_type == DataType.FINANCIAL_STATEMENT:
            required = ["ticker", "fiscal_year", "report_type", "as_of_date"]
            for key in required:
                if key not in params:
                    errors.append(f"필수 파라미터 누락: {key}")

            if "report_type" in params and params["report_type"] not in REPORT_CODES:
                errors.append(
                    f"잘못된 report_type: {params['report_type']}. "
                    f"허용값: {list(REPORT_CODES.keys())}"
                )

        elif data_type == DataType.DIVIDEND_HISTORY:
            required = ["ticker", "fiscal_year", "as_of_date"]
            for key in required:
                if key not in params:
                    errors.append(f"필수 파라미터 누락: {key}")

        elif data_type == DataType.DISCLOSURE:
            required = ["start_date", "end_date", "as_of_date"]
            for key in required:
                if key not in params:
                    errors.append(f"필수 파라미터 누락: {key}")
            corp_cls = params.get("corp_cls")
            if corp_cls and corp_cls not in ["Y", "K", "N", "E"]:
                errors.append("corp_cls는 Y, K, N, E 중 하나여야 합니다.")

        return errors

    def get_required_params(self, data_type: DataType) -> List[str]:
        """데이터 유형별 필수 파라미터"""
        if data_type == DataType.FINANCIAL_STATEMENT:
            return ["ticker", "fiscal_year", "report_type", "as_of_date"]
        elif data_type == DataType.DIVIDEND_HISTORY:
            return ["ticker", "fiscal_year", "as_of_date"]
        elif data_type == DataType.DISCLOSURE:
            return ["start_date", "end_date", "as_of_date"]
        elif data_type == DataType.CORP_CODE:
            return ["as_of_date"]
        return []

    def _rate_limit_wait(self) -> None:
        """Rate limit 대기"""
        elapsed = time.time() - self._last_call_time
        if elapsed < self._call_interval:
            time.sleep(self._call_interval - elapsed)
        self._last_call_time = time.time()

    def _call_api(
        self,
        endpoint: str,
        params: Dict[str, Any],
        is_binary: bool = False,
    ) -> Dict[str, Any]:
        """DART API 호출"""
        self._rate_limit_wait()

        params["crtfc_key"] = self.api_key
        url = f"{self.BASE_URL}/{endpoint}"

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        if is_binary:
            return {"content": response.content}

        data = response.json()

        # DART 응답 상태 확인
        status = data.get("status", "900")
        if status != "000":
            message = DART_STATUS_CODES.get(status, f"알 수 없는 오류 (코드: {status})")
            raise DartApiError(message, status_code=status)

        return data

    def _get_corp_code(self, ticker: str) -> str:
        """
        종목코드(ticker) → DART 고유번호(corp_code) 변환

        DART API는 종목코드가 아닌 고유번호를 사용합니다.
        """
        if ticker in self._corp_code_cache:
            return self._corp_code_cache[ticker]

        # 캐시에 없으면 전체 목록 로드
        if not self._corp_code_cache:
            self._load_corp_codes()

        if ticker not in self._corp_code_cache:
            raise DartApiError(f"종목코드 {ticker}에 해당하는 고유번호를 찾을 수 없습니다.")

        return self._corp_code_cache[ticker]

    def _load_corp_codes(self) -> None:
        """DART 고유번호 전체 목록 로드"""
        try:
            result = self._call_api("corpCode.xml", {}, is_binary=True)
            content = result["content"]

            # ZIP 파일 압축 해제
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                xml_filename = zf.namelist()[0]
                xml_content = zf.read(xml_filename)

            # XML 파싱
            root = ET.fromstring(xml_content)
            for item in root.findall(".//list"):
                corp_code = item.findtext("corp_code", "")
                stock_code = item.findtext("stock_code", "")

                if stock_code and stock_code.strip():
                    self._corp_code_cache[stock_code.strip()] = corp_code

        except Exception as e:
            raise DartApiError(f"고유번호 목록 로드 실패: {str(e)}")

    def _fetch_financial_statement(self, params: Dict[str, Any]) -> FetchResult:
        """재무제표 조회"""
        ticker = params["ticker"]
        fiscal_year = params["fiscal_year"]
        report_type = params["report_type"]
        as_of_date = params["as_of_date"]

        corp_code = self._get_corp_code(ticker)
        reprt_code = REPORT_CODES[report_type]

        api_params = {
            "corp_code": corp_code,
            "bsns_year": str(fiscal_year),
            "reprt_code": reprt_code,
            "fs_div": "CFS",  # 연결재무제표 (없으면 개별)
        }

        try:
            data = self._call_api("fnlttSinglAcntAll.json", api_params)
        except DartApiError as e:
            if e.status_code == "013":
                # 조회된 데이터 없음 - 개별재무제표로 재시도
                api_params["fs_div"] = "OFS"
                data = self._call_api("fnlttSinglAcntAll.json", api_params)
            else:
                raise

        # 응답 파싱
        records = self._parse_financial_statement(data, ticker, fiscal_year, report_type, as_of_date)

        return FetchResult.success_result(
            data=records,
            source_id=self.source_id,
            data_type=DataType.FINANCIAL_STATEMENT,
            params=params,
        )

    def _parse_financial_statement(
        self,
        data: Dict[str, Any],
        ticker: str,
        fiscal_year: int,
        report_type: str,
        as_of_date: date,
    ) -> List[Dict[str, Any]]:
        """재무제표 응답 파싱"""
        items = data.get("list", [])
        if not items:
            return []

        # 계정과목별 금액 추출
        accounts: Dict[str, int] = {}
        for item in items:
            account_nm = item.get("account_nm", "")
            # 당기 금액 (thstrm_amount)
            amount_str = item.get("thstrm_amount", "").replace(",", "")
            if amount_str and amount_str not in ["-", ""]:
                try:
                    accounts[account_nm] = int(amount_str)
                except ValueError:
                    pass

        # 분기 추출
        fiscal_quarter = {"ANNUAL": 4, "Q1": 1, "Q2": 2, "Q3": 3}.get(report_type, 4)

        # 정규화된 레코드 생성
        record = {
            "ticker": ticker,
            "fiscal_year": fiscal_year,
            "fiscal_quarter": fiscal_quarter,
            "report_type": report_type,
            # 손익계산서
            "revenue": accounts.get("매출액") or accounts.get("영업수익"),
            "operating_income": accounts.get("영업이익") or accounts.get("영업손익"),
            "net_income": accounts.get("당기순이익") or accounts.get("당기순손익"),
            # 재무상태표
            "total_assets": accounts.get("자산총계"),
            "total_liabilities": accounts.get("부채총계"),
            "total_equity": accounts.get("자본총계"),
            # 현금흐름표
            "operating_cash_flow": accounts.get("영업활동으로인한현금흐름")
            or accounts.get("영업활동현금흐름"),
            "investing_cash_flow": accounts.get("투자활동으로인한현금흐름")
            or accounts.get("투자활동현금흐름"),
            "financing_cash_flow": accounts.get("재무활동으로인한현금흐름")
            or accounts.get("재무활동현금흐름"),
            # 주요 비율 (계산)
            "roe": self._calc_roe(accounts),
            "roa": self._calc_roa(accounts),
            "debt_ratio": self._calc_debt_ratio(accounts),
            # 메타데이터
            "as_of_date": as_of_date.isoformat() if isinstance(as_of_date, date) else as_of_date,
            "dart_rcept_no": data.get("list", [{}])[0].get("rcept_no", ""),
        }

        return [record]

    def _calc_roe(self, accounts: Dict[str, int]) -> Optional[float]:
        """ROE 계산"""
        net_income = accounts.get("당기순이익") or accounts.get("당기순손익")
        equity = accounts.get("자본총계")
        if net_income and equity and equity != 0:
            return round((net_income / equity) * 100, 4)
        return None

    def _calc_roa(self, accounts: Dict[str, int]) -> Optional[float]:
        """ROA 계산"""
        net_income = accounts.get("당기순이익") or accounts.get("당기순손익")
        assets = accounts.get("자산총계")
        if net_income and assets and assets != 0:
            return round((net_income / assets) * 100, 4)
        return None

    def _calc_debt_ratio(self, accounts: Dict[str, int]) -> Optional[float]:
        """부채비율 계산"""
        liabilities = accounts.get("부채총계")
        equity = accounts.get("자본총계")
        if liabilities and equity and equity != 0:
            return round((liabilities / equity) * 100, 4)
        return None

    def _fetch_dividend(self, params: Dict[str, Any]) -> FetchResult:
        """배당 정보 조회"""
        ticker = params["ticker"]
        fiscal_year = params["fiscal_year"]
        as_of_date = params["as_of_date"]

        corp_code = self._get_corp_code(ticker)

        api_params = {
            "corp_code": corp_code,
            "bsns_year": str(fiscal_year),
            "reprt_code": "11011",  # 사업보고서
        }

        request_url = (
            f"{self.BASE_URL}/alotMatter.json?"
            f"crtfc_key={self.api_key}&corp_code={corp_code}"
            f"&bsns_year={fiscal_year}&reprt_code=11011"
        )
        self.logger.info(request_url)

        data = self._call_api("alotMatter.json", api_params)

        # 응답 파싱
        records = self._parse_dividend(data, ticker, fiscal_year, as_of_date)

        return FetchResult.success_result(
            data=records,
            source_id=self.source_id,
            data_type=DataType.DIVIDEND_HISTORY,
            params=params,
        )

    def _parse_dividend(
        self,
        data: Dict[str, Any],
        ticker: str,
        fiscal_year: int,
        as_of_date: date,
    ) -> List[Dict[str, Any]]:
        """배당 정보 파싱"""
        items = data.get("list", [])
        if not items:
            return []

        records = []

        for item in items:
            se = item.get("se", "")
            stock_kind = item.get("stock_knd", "보통주")
            dividend_type = "CASH"
            if "주식" in se:
                dividend_type = "STOCK"

            def _parse_decimal(value: str) -> Optional[Decimal]:
                if not value:
                    return None
                cleaned = str(value).replace(",", "").replace("-", "").strip()
                if not cleaned:
                    return None
                try:
                    return Decimal(cleaned)
                except Exception:
                    return None

            thstrm = _parse_decimal(item.get("thstrm", ""))
            frmtrm = _parse_decimal(item.get("frmtrm", ""))
            lwfr = _parse_decimal(item.get("lwfr", ""))

            stlm_raw = item.get("stlm_dt")
            stlm_dt = None
            if stlm_raw:
                try:
                    stlm_dt = date.fromisoformat(stlm_raw)
                except Exception:
                    stlm_dt = None

            record = {
                "ticker": ticker,
                "fiscal_year": fiscal_year,
                "rcept_no": item.get("rcept_no"),
                "corp_cls": item.get("corp_cls"),
                "corp_code": item.get("corp_code"),
                "corp_name": item.get("corp_name"),
                "se": se,
                "stock_knd": stock_kind,
                "thstrm": thstrm,
                "frmtrm": frmtrm,
                "lwfr": lwfr,
                "stlm_dt": stlm_dt,
                "dividend_type": dividend_type,
                "dividend_per_share": float(thstrm) if thstrm is not None else None,
                "as_of_date": as_of_date.isoformat() if isinstance(as_of_date, date) else as_of_date,
            }
            records.append(record)

        return records

    def _fetch_disclosure(self, params: Dict[str, Any]) -> FetchResult:
        """공시 목록 조회"""
        start_date = params["start_date"]
        end_date = params["end_date"]
        as_of_date = params["as_of_date"]
        ticker = params.get("ticker")

        # 날짜 형식 변환
        if isinstance(start_date, date):
            start_date = start_date.strftime("%Y%m%d")
        if isinstance(end_date, date):
            end_date = end_date.strftime("%Y%m%d")

        api_params = {
            "bgn_de": start_date.replace("-", ""),
            "end_de": end_date.replace("-", ""),
            "page_no": 1,
            "page_count": 100,
        }

        # DART 공시 목록 호출 URL 로그 (디버그/검증용)
        request_url_parts = [
            f"crtfc_key={self.api_key}",
            f"bgn_de={api_params['bgn_de']}",
            f"end_de={api_params['end_de']}",
            "page_no=1",
            f"page_count={api_params['page_count']}",
        ]

        if ticker:
            corp_code = self._get_corp_code(ticker)
            api_params["corp_code"] = corp_code

        corp_cls = params.get("corp_cls")
        if corp_cls:
            api_params["corp_cls"] = corp_cls
            request_url_parts.append(f"corp_cls={corp_cls}")

        request_url = f"{self.BASE_URL}/list.json?" + "&".join(request_url_parts)
        self.logger.info(request_url)

        data = self._call_api("list.json", api_params)

        # 응답 파싱
        items = data.get("list", [])
        records = []

        for item in items:
            record = {
                "corp_code": item.get("corp_code", ""),
                "corp_name": item.get("corp_name", ""),
                "stock_code": item.get("stock_code", ""),
                "report_nm": item.get("report_nm", ""),
                "rcept_no": item.get("rcept_no", ""),
                "flr_nm": item.get("flr_nm", ""),
                "rcept_dt": item.get("rcept_dt", ""),
                "rm": item.get("rm", ""),
                "as_of_date": as_of_date.isoformat() if isinstance(as_of_date, date) else as_of_date,
            }
            records.append(record)

        return FetchResult.success_result(
            data=records,
            source_id=self.source_id,
            data_type=DataType.DISCLOSURE,
            params=params,
        )

    def _fetch_corp_codes(self, params: Dict[str, Any]) -> FetchResult:
        """기업 고유번호 목록 조회"""
        as_of_date = params["as_of_date"]

        # 캐시가 비어있으면 로드
        if not self._corp_code_cache:
            self._load_corp_codes()

        records = [
            {
                "ticker": ticker,
                "corp_code": corp_code,
                "as_of_date": as_of_date.isoformat() if isinstance(as_of_date, date) else as_of_date,
            }
            for ticker, corp_code in self._corp_code_cache.items()
        ]

        return FetchResult.success_result(
            data=records,
            source_id=self.source_id,
            data_type=DataType.CORP_CODE,
            params=params,
        )
