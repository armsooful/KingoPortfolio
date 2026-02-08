"""
Phase 11 Level 2: 금융위원회_주식배당정보(OpenAPI) Fetcher
"""

import os
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

import logging
import requests

from .base_fetcher import BaseFetcher, DataType, FetcherError, FetchResult


class FscApiError(Exception):
    """금융위원회 OpenAPI 오류"""

    def __init__(self, message: str, status_code: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class FscDividendFetcher(BaseFetcher):
    """금융위원회_주식배당정보 OpenAPI Fetcher"""

    BASE_URL = "http://apis.data.go.kr/1160100/service/GetStocDiviInfoService/getDiviInfo"

    source_id = "FSC_DATA_GO_KR"
    source_name = "금융위원회_주식배당정보(OpenAPI)"
    supported_data_types = [DataType.DIVIDEND_HISTORY]

    logger = logging.getLogger(__name__)

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (
            api_key
            or os.getenv("FSC_DATA_GO_KR_API_KEY", "")
            or os.getenv("DATA_GO_KR_API_KEY", "")
        )
        if not self.api_key:
            raise FetcherError(
                "FSC_DATA_GO_KR_API_KEY 환경변수가 설정되지 않았습니다.",
                source_id=self.source_id,
            )

    def fetch(self, data_type: DataType, params: Dict[str, Any]) -> FetchResult:
        errors = self.validate_params(data_type, params)
        if errors:
            return FetchResult.error_result(
                error_message="; ".join(errors),
                source_id=self.source_id,
                data_type=data_type,
                params=params,
            )

        try:
            if data_type != DataType.DIVIDEND_HISTORY:
                return FetchResult.error_result(
                    error_message=f"지원하지 않는 데이터 유형: {data_type}",
                    source_id=self.source_id,
                    data_type=data_type,
                    params=params,
                )

            records = self._fetch_dividends(params)
            return FetchResult.success_result(
                data=records,
                source_id=self.source_id,
                data_type=data_type,
                params=params,
            )
        except FscApiError as e:
            return FetchResult.error_result(
                error_message=f"FSC API 오류: {e.message}",
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

    def validate_params(self, data_type: DataType, params: Dict[str, Any]) -> List[str]:
        errors = super().validate_params(data_type, params)
        if data_type == DataType.DIVIDEND_HISTORY:
            # 회사명 또는 법인등록번호 중 하나는 필요
            if not (params.get("stckIssuCmpyNm") or params.get("crno")):
                errors.append("stckIssuCmpyNm(회사명) 또는 crno(법인등록번호)가 필요합니다.")
        return errors

    def _fetch_dividends(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        bas_dt = params.get("basDt")
        crno = params.get("crno")
        company_name = params.get("stckIssuCmpyNm")
        as_of_date = params.get("as_of_date")
        ticker = params.get("ticker")

        page_no = 1
        num_rows = 200
        records: List[Dict[str, Any]] = []
        total_count = None

        while True:
            api_params = {
                "serviceKey": self.api_key,
                "pageNo": page_no,
                "numOfRows": num_rows,
                "resultType": "json",
            }
            if crno:
                api_params["crno"] = crno
            if company_name:
                api_params["stckIssuCmpyNm"] = company_name

            self.logger.info("FSC 배당 API 호출 url=%s params=%s", self.BASE_URL, api_params)
            response = requests.get(self.BASE_URL, params=api_params, timeout=30)
            response.raise_for_status()
            data = response.json()

            header = data.get("response", {}).get("header", {})
            result_code = header.get("resultCode")
            if result_code not in ("00", 0, "0", None):
                raise FscApiError(header.get("resultMsg", "알 수 없는 오류"), str(result_code))

            body = data.get("response", {}).get("body", {})
            if total_count is None:
                total_count = int(body.get("totalCount", 0) or 0)
            items = body.get("items", {}).get("item", [])
            if isinstance(items, dict):
                items = [items]

            self.logger.info(
                "FSC 배당 API 응답 items=%d sample=%s",
                len(items),
                items[0] if items else None,
            )
            for item in items:
                record = self._parse_item(item, ticker=ticker, as_of_date=as_of_date)
                if record:
                    records.append(record)

            if total_count is None or len(records) >= total_count:
                break
            if not items:
                break

            page_no += 1

        return records

    def _parse_item(
        self,
        item: Dict[str, Any],
        ticker: Optional[str],
        as_of_date: Optional[Any],
    ) -> Optional[Dict[str, Any]]:
        def parse_date(value: Optional[str]) -> Optional[date]:
            if not value:
                return None
            try:
                return date.fromisoformat(f"{value[0:4]}-{value[4:6]}-{value[6:8]}")
            except Exception:
                return None

        def parse_decimal(value: Optional[str]) -> Optional[Decimal]:
            if value is None:
                return None
            cleaned = str(value).replace(",", "").strip()
            if cleaned in ("", "-"):
                return None
            try:
                return Decimal(cleaned)
            except Exception:
                return None

        bas_dt = item.get("basDt")
        dvdn_bas_dt = item.get("dvdnBasDt")
        cash_pay_dt = item.get("cashDvdnPayDt")
        stock_handover_dt = item.get("stckHndvDt")

        cash_amt = parse_decimal(item.get("stckGenrDvdnAmt"))
        cash_rate = parse_decimal(item.get("stckGenrCashDvdnRt"))
        stock_rate = parse_decimal(item.get("stckGenrDvdnRt"))

        dividend_type = None
        if cash_pay_dt or (cash_rate and cash_rate > 0):
            dividend_type = "CASH"
        elif stock_handover_dt or (stock_rate and stock_rate > 0):
            dividend_type = "STOCK"
        else:
            dividend_type = "CASH"

        fiscal_year = None
        for candidate in (dvdn_bas_dt, bas_dt):
            if candidate:
                try:
                    fiscal_year = int(candidate[0:4])
                    break
                except Exception:
                    pass

        dvdn_bas_dt_parsed = parse_date(dvdn_bas_dt)
        cash_pay_dt_parsed = parse_date(cash_pay_dt)

        return {
            "ticker": ticker,
            "fiscal_year": fiscal_year,
            "bas_dt": bas_dt,
            "crno": item.get("crno"),
            "isin_cd": item.get("isinCd"),
            "isin_cd_nm": item.get("isinCdNm"),
            "stck_dvdn_rcd": item.get("stckDvdnRcd"),
            "stck_dvdn_rcd_nm": item.get("stckDvdnRcdNm"),
            "trsnm_dpty_dcd": item.get("trsnmDptyDcd"),
            "trsnm_dpty_dcd_nm": item.get("trsnmDptyDcdNm"),
            "scrs_itms_kcd": item.get("scrsItmsKcd"),
            "scrs_itms_kcd_nm": item.get("scrsItmsKcdNm"),
            "stck_genr_dvdn_amt": parse_decimal(item.get("stckGenrDvdnAmt")),
            "stck_grdn_dvdn_amt": parse_decimal(item.get("stckGrdnDvdnAmt")),
            "stck_genr_cash_dvdn_rt": parse_decimal(item.get("stckGenrCashDvdnRt")),
            "stck_genr_dvdn_rt": parse_decimal(item.get("stckGenrDvdnRt")),
            "cash_grdn_dvdn_rt": parse_decimal(item.get("cashGrdnDvdnRt")),
            "stck_grdn_dvdn_rt": parse_decimal(item.get("stckGrdnDvdnRt")),
            "stck_par_prc": parse_decimal(item.get("stckParPrc")),
            "stck_stac_md": item.get("stckStacMd"),
            "corp_code": item.get("crno"),
            "corp_name": item.get("stckIssuCmpyNm"),
            "se": item.get("stckDvdnRcdNm"),
            "stock_knd": item.get("scrsItmsKcdNm") or item.get("scrsItmsKcd"),
            "dividend_type": dividend_type,
            "dividend_per_share": float(cash_amt) if cash_amt is not None else None,
            "dividend_rate": float(cash_rate) if cash_rate is not None else (float(stock_rate) if stock_rate is not None else None),
            "dividend_yield": None,
            "currency": "KRW",
            "dvdn_bas_dt": dvdn_bas_dt_parsed,
            "cash_dvdn_pay_dt": cash_pay_dt_parsed,
            "record_date": dvdn_bas_dt_parsed,
            "payment_date": cash_pay_dt_parsed,
            "ex_dividend_date": None,
            "as_of_date": as_of_date,
        }
