"""
Phase 11 Level 2: 금융위원회_채권기본정보(OpenAPI) Fetcher
"""

import os
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

import logging
import requests

from .base_fetcher import BaseFetcher, DataType, FetcherError, FetchResult
from .fsc_dividend_fetcher import FscApiError


class BondBasicInfoFetcher(BaseFetcher):
    """금융위원회_채권기본정보 OpenAPI Fetcher"""

    BASE_URL = "http://apis.data.go.kr/1160100/service/GetBondIssuInfoService/getBondBasiInfo"

    source_id = "FSC_BOND_INFO"
    source_name = "금융위원회_채권기본정보(OpenAPI)"
    supported_data_types = [DataType.BOND_BASIC_INFO]

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
            if data_type != DataType.BOND_BASIC_INFO:
                return FetchResult.error_result(
                    error_message=f"지원하지 않는 데이터 유형: {data_type}",
                    source_id=self.source_id,
                    data_type=data_type,
                    params=params,
                )

            records = self._fetch_bond_info(params)
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
        if data_type == DataType.BOND_BASIC_INFO:
            if not (params.get("basDt") or params.get("crno") or params.get("bondIsurNm")):
                errors.append("basDt(기준일), crno(법인등록번호), bondIsurNm(발행인명) 중 하나라도 필요합니다.")
        return errors

    def _fetch_bond_info(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        bas_dt = params.get("basDt")
        crno = params.get("crno")
        bond_isur_nm = params.get("bondIsurNm")
        as_of_date = params.get("as_of_date")
        limit = params.get("limit")  # 건수 제한

        page_no = 1
        records: List[Dict[str, Any]] = []
        total_count = None

        while True:
            remaining = None
            if limit is not None:
                remaining = limit - len(records)
                if remaining <= 0:
                    break

            num_rows = 200
            if remaining is not None:
                num_rows = min(200, remaining)

            api_params = {
                "serviceKey": self.api_key,
                "pageNo": page_no,
                "numOfRows": num_rows,
                "resultType": "json",
            }
            if bas_dt:
                api_params["basDt"] = bas_dt
            if crno:
                api_params["crno"] = crno
            if bond_isur_nm:
                api_params["bondIsurNm"] = bond_isur_nm

            self.logger.info("FSC 채권기본정보 API 호출 url=%s params=%s", self.BASE_URL, api_params)
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
                "FSC 채권기본정보 API 응답 items=%d sample=%s",
                len(items),
                items[0] if items else None,
            )
            for item in items:
                record = self._parse_item(item, as_of_date=as_of_date)
                if record:
                    records.append(record)

            if total_count is None or len(records) >= total_count:
                break
            if not items:
                break

            page_no += 1

        if limit is not None:
            records = records[:limit]

        return records

    def _parse_item(
        self,
        item: Dict[str, Any],
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

        return {
            # 식별
            "isin_cd": item.get("isinCd"),
            "bas_dt": item.get("basDt"),
            "crno": item.get("crno"),
            # 종목
            "isin_cd_nm": item.get("isinCdNm"),
            "bond_isur_nm": item.get("bondIsurNm"),
            "scrs_itms_kcd": item.get("scrsItmsKcd"),
            "scrs_itms_kcd_nm": item.get("scrsItmsKcdNm"),
            # 발행
            "bond_issu_dt": parse_date(item.get("bondIssuDt")),
            "bond_expr_dt": parse_date(item.get("bondExprDt")),
            # 금액
            "bond_issu_amt": parse_decimal(item.get("bondIssuAmt")),
            "bond_bal": parse_decimal(item.get("bondBal")),
            # 금리
            "bond_srfc_inrt": parse_decimal(item.get("bondSrfcInrt")),
            "irt_chng_dcd": item.get("irtChngDcd"),
            "bond_int_tcd": item.get("bondIntTcd"),
            "int_pay_cycl_ctt": item.get("intPayCyclCtt"),
            # 이표
            "nxtm_copn_dt": parse_date(item.get("nxtmCopnDt")),
            "rbf_copn_dt": parse_date(item.get("rbfCopnDt")),
            # 보증/순위
            "grn_dcd": item.get("grnDcd"),
            "bond_rnkn_dcd": item.get("bondRnknDcd"),
            # 신용등급
            "kis_scrs_itms_kcd": item.get("kisScrsItmsKcd"),
            "kbp_scrs_itms_kcd": item.get("kbpScrsItmsKcd"),
            "nice_scrs_itms_kcd": item.get("niceScrsItmsKcd"),
            "fn_scrs_itms_kcd": item.get("fnScrsItmsKcd"),
            # 모집/상장
            "bond_offr_mcd": item.get("bondOffrMcd"),
            "lstg_dt": parse_date(item.get("lstgDt")),
            # 특이
            "prmnc_bond_yn": item.get("prmncBondYn"),
            "strips_psbl_yn": item.get("stripsPsblYn"),
            # 거버넌스
            "as_of_date": as_of_date,
        }
