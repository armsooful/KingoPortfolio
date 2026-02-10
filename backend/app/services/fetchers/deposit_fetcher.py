"""
FSS(금융감독원) 정기예금 상품 Fetcher

금융상품 한 눈에 API를 사용하여 정기예금 상품 정보를 조회합니다.
- URL: http://finlife.fss.or.kr/finlifeapi/depositProductsSearch.json
- 응답: baseList(상품 기본정보) + optionList(기간별 금리 옵션)
- 권역코드별 순차 호출 (은행, 여신전문금융, 저축은행, 보험, 금융투자)
"""

import os
import logging
from typing import Any, Dict, List, Optional

import requests

from .base_fetcher import BaseFetcher, DataType, FetcherError, FetchResult


# 권역코드 매핑
SECTOR_CODES = {
    "020000": "은행",
    "030200": "여신전문금융",
    "030300": "저축은행",
    "050000": "보험",
    "060000": "금융투자",
}


class FssDepositFetcher(BaseFetcher):
    """FSS 금융상품 한 눈에 - 정기예금 Fetcher"""

    BASE_URL = "http://finlife.fss.or.kr/finlifeapi/depositProductsSearch.json"

    source_id = "FSS_DEPOSIT"
    source_name = "금융감독원 금융상품 한 눈에 (정기예금)"
    supported_data_types = [DataType.DEPOSIT_PRODUCT]

    logger = logging.getLogger(__name__)

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FSS_API_KEY", "")
        if not self.api_key:
            raise FetcherError(
                "FSS_API_KEY 환경변수가 설정되지 않았습니다.",
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
            if data_type != DataType.DEPOSIT_PRODUCT:
                return FetchResult.error_result(
                    error_message=f"지원하지 않는 데이터 유형: {data_type}",
                    source_id=self.source_id,
                    data_type=data_type,
                    params=params,
                )

            products = self._fetch_all_sectors(params)
            return FetchResult.success_result(
                data=products,
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

    def _fetch_all_sectors(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """모든 권역코드를 순차 호출하여 정기예금 상품을 통합 수집"""
        all_products = []

        for sector_code, sector_name in SECTOR_CODES.items():
            self.logger.info(f"[FSS] 권역 '{sector_name}'({sector_code}) 조회 시작")
            try:
                products = self._fetch_deposit_products(sector_code)
                self.logger.info(
                    f"[FSS] 권역 '{sector_name}'({sector_code}): {len(products)}개 상품 조회됨"
                )
                # 권역 정보를 각 상품에 추가
                for p in products:
                    p["base_info"]["sector_code"] = sector_code
                    p["base_info"]["sector_name"] = sector_name
                all_products.extend(products)
            except FetcherError as e:
                # 특정 권역 실패 시 로그만 남기고 계속 진행
                self.logger.warning(
                    f"[FSS] 권역 '{sector_name}'({sector_code}) 조회 실패: {e.message}"
                )
            except Exception as e:
                self.logger.warning(
                    f"[FSS] 권역 '{sector_name}'({sector_code}) 조회 중 오류: {str(e)}"
                )

        self.logger.info(
            f"[FSS] 전체 권역 조회 완료: 총 {len(all_products)}개 상품, "
            f"{sum(len(p['options']) for p in all_products)}개 금리옵션"
        )
        return all_products

    def _fetch_deposit_products(self, sector_code: str) -> List[Dict[str, Any]]:
        """단일 권역코드에 대해 FSS API를 호출하여 정기예금 상품 조회"""
        api_params = {
            "auth": self.api_key,
            "topFinGrpNo": sector_code,
            "pageNo": 1,
        }

        self.logger.info(
            "FSS 정기예금 API 호출 url=%s topFinGrpNo=%s",
            self.BASE_URL, sector_code,
        )
        response = requests.get(self.BASE_URL, params=api_params, timeout=30)
        response.raise_for_status()
        data = response.json()

        result_section = data.get("result", {})

        # 에러 체크
        err_cd = result_section.get("err_cd")
        if err_cd and err_cd != "000":
            err_msg = result_section.get("err_msg", "알 수 없는 오류")
            raise FetcherError(
                f"FSS API 오류 [{err_cd}]: {err_msg}",
                source_id=self.source_id,
            )

        base_list = result_section.get("baseList", []) or []
        option_list = result_section.get("optionList", []) or []

        self.logger.info(
            "FSS 정기예금 API 응답 (권역 %s): baseList=%d건, optionList=%d건",
            sector_code, len(base_list), len(option_list),
        )

        # 옵션을 (fin_co_no, fin_prdt_cd) 기준으로 그룹핑
        option_map: Dict[str, List[Dict]] = {}
        for opt in option_list:
            key = f"{opt.get('fin_co_no')}_{opt.get('fin_prdt_cd')}"
            option_map.setdefault(key, []).append({
                "save_trm": self._safe_int(opt.get("save_trm")),
                "intr_rate_type": opt.get("intr_rate_type"),
                "intr_rate_type_nm": opt.get("intr_rate_type_nm"),
                "intr_rate": self._safe_float(opt.get("intr_rate")),
                "intr_rate2": self._safe_float(opt.get("intr_rate2")),
            })

        # 상품별로 옵션 매핑
        products = []
        for base in base_list:
            fin_co_no = base.get("fin_co_no", "")
            fin_prdt_cd = base.get("fin_prdt_cd", "")
            key = f"{fin_co_no}_{fin_prdt_cd}"

            product = {
                "base_info": {
                    "fin_co_no": fin_co_no,
                    "fin_prdt_cd": fin_prdt_cd,
                    "kor_co_nm": base.get("kor_co_nm", ""),
                    "fin_prdt_nm": base.get("fin_prdt_nm", ""),
                    "dcls_month": base.get("dcls_month"),
                    "join_way": base.get("join_way"),
                    "mtrt_int": base.get("mtrt_int"),
                    "spcl_cnd": base.get("spcl_cnd"),
                    "join_deny": base.get("join_deny"),
                    "join_member": base.get("join_member"),
                    "etc_note": base.get("etc_note"),
                    "max_limit": self._safe_float(base.get("max_limit")),
                },
                "options": option_map.get(key, []),
            }
            products.append(product)

        return products

    @staticmethod
    def _safe_float(value) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_int(value) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
