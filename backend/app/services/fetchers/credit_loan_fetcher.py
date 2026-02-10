"""
FSS(금융감독원) 개인신용대출 상품 Fetcher

금융상품 한 눈에 API를 사용하여 개인신용대출 상품 정보를 조회합니다.
- URL: http://finlife.fss.or.kr/finlifeapi/creditLoanProductsSearch.json
- 응답: baseList(상품 기본정보) + optionList(신용등급별/금리유형별 금리)
- 권역코드별 순차 호출 + 다중 페이지 지원
- 주요 권역: 은행(020000), 여신전문금융(030200), 저축은행(030300), 보험(050000)
"""

import os
import logging
from typing import Any, Dict, List, Optional, Tuple

import requests

from .base_fetcher import BaseFetcher, DataType, FetcherError, FetchResult


SECTOR_CODES = {
    "020000": "은행",
    "030200": "여신전문금융",
    "030300": "저축은행",
    "050000": "보험",
    "060000": "금융투자",
}


class FssCreditLoanFetcher(BaseFetcher):
    """FSS 금융상품 한 눈에 - 개인신용대출 Fetcher"""

    BASE_URL = "http://finlife.fss.or.kr/finlifeapi/creditLoanProductsSearch.json"

    source_id = "FSS_CREDIT_LOAN"
    source_name = "금융감독원 금융상품 한 눈에 (개인신용대출)"
    supported_data_types = [DataType.CREDIT_LOAN_PRODUCT]

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
            if data_type != DataType.CREDIT_LOAN_PRODUCT:
                return FetchResult.error_result(
                    error_message=f"지원하지 않는 데이터 유형: {data_type}",
                    source_id=self.source_id,
                    data_type=data_type,
                    params=params,
                )

            products = self._fetch_all_sectors()
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

    def _fetch_all_sectors(self) -> List[Dict[str, Any]]:
        """모든 권역코드를 순차 호출하여 개인신용대출 상품을 통합 수집"""
        all_products = []

        for sector_code, sector_name in SECTOR_CODES.items():
            self.logger.info(f"[FSS 신용대출] 권역 '{sector_name}'({sector_code}) 조회 시작")
            try:
                products = self._fetch_all_pages(sector_code)
                self.logger.info(
                    f"[FSS 신용대출] 권역 '{sector_name}'({sector_code}): {len(products)}개 상품 조회됨"
                )
                for p in products:
                    p["base_info"]["sector_code"] = sector_code
                    p["base_info"]["sector_name"] = sector_name
                all_products.extend(products)
            except FetcherError as e:
                self.logger.warning(
                    f"[FSS 신용대출] 권역 '{sector_name}'({sector_code}) 조회 실패: {e.message}"
                )
            except Exception as e:
                self.logger.warning(
                    f"[FSS 신용대출] 권역 '{sector_name}'({sector_code}) 조회 중 오류: {str(e)}"
                )

        self.logger.info(
            f"[FSS 신용대출] 전체 권역 조회 완료: 총 {len(all_products)}개 상품, "
            f"{sum(len(p['options']) for p in all_products)}개 금리옵션"
        )
        return all_products

    def _fetch_all_pages(self, sector_code: str) -> List[Dict[str, Any]]:
        all_products = []
        page_no = 1
        while True:
            products, max_page_no = self._fetch_credit_loan_products(sector_code, page_no)
            all_products.extend(products)
            if page_no >= max_page_no:
                break
            page_no += 1
        return all_products

    def _fetch_credit_loan_products(self, sector_code: str, page_no: int = 1) -> Tuple[List[Dict[str, Any]], int]:
        api_params = {
            "auth": self.api_key,
            "topFinGrpNo": sector_code,
            "pageNo": page_no,
        }

        self.logger.info(
            "FSS 개인신용대출 API 호출 url=%s topFinGrpNo=%s pageNo=%d",
            self.BASE_URL, sector_code, page_no,
        )
        response = requests.get(self.BASE_URL, params=api_params, timeout=30)
        response.raise_for_status()
        data = response.json()

        result_section = data.get("result", {})

        err_cd = result_section.get("err_cd")
        if err_cd and err_cd != "000":
            err_msg = result_section.get("err_msg", "알 수 없는 오류")
            raise FetcherError(
                f"FSS API 오류 [{err_cd}]: {err_msg}",
                source_id=self.source_id,
            )

        max_page_no = int(result_section.get("max_page_no", 1) or 1)
        base_list = result_section.get("baseList", []) or []
        option_list = result_section.get("optionList", []) or []

        self.logger.info(
            "FSS 개인신용대출 API 응답 (권역 %s, 페이지 %d/%d): baseList=%d건, optionList=%d건",
            sector_code, page_no, max_page_no, len(base_list), len(option_list),
        )

        # 옵션 그룹핑: fin_co_no + fin_prdt_cd + crdt_prdt_type 으로 매핑
        option_map: Dict[str, List[Dict]] = {}
        for opt in option_list:
            key = f"{opt.get('fin_co_no')}_{opt.get('fin_prdt_cd')}_{opt.get('crdt_prdt_type')}"
            option_map.setdefault(key, []).append({
                "crdt_lend_rate_type": opt.get("crdt_lend_rate_type"),
                "crdt_lend_rate_type_nm": opt.get("crdt_lend_rate_type_nm"),
                "crdt_grad_1": self._safe_float(opt.get("crdt_grad_1")),
                "crdt_grad_4": self._safe_float(opt.get("crdt_grad_4")),
                "crdt_grad_5": self._safe_float(opt.get("crdt_grad_5")),
                "crdt_grad_6": self._safe_float(opt.get("crdt_grad_6")),
                "crdt_grad_10": self._safe_float(opt.get("crdt_grad_10")),
                "crdt_grad_11": self._safe_float(opt.get("crdt_grad_11")),
                "crdt_grad_12": self._safe_float(opt.get("crdt_grad_12")),
                "crdt_grad_13": self._safe_float(opt.get("crdt_grad_13")),
                "crdt_grad_avg": self._safe_float(opt.get("crdt_grad_avg")),
            })

        products = []
        for base in base_list:
            fin_co_no = base.get("fin_co_no", "")
            fin_prdt_cd = base.get("fin_prdt_cd", "")
            crdt_prdt_type = base.get("crdt_prdt_type", "")
            key = f"{fin_co_no}_{fin_prdt_cd}_{crdt_prdt_type}"

            product = {
                "base_info": {
                    "fin_co_no": fin_co_no,
                    "fin_prdt_cd": fin_prdt_cd,
                    "kor_co_nm": base.get("kor_co_nm", ""),
                    "fin_prdt_nm": base.get("fin_prdt_nm", ""),
                    "dcls_month": base.get("dcls_month"),
                    "join_way": base.get("join_way"),
                    "crdt_prdt_type": crdt_prdt_type,
                    "crdt_prdt_type_nm": base.get("crdt_prdt_type_nm"),
                    "cb_name": base.get("cb_name"),
                },
                "options": option_map.get(key, []),
            }
            products.append(product)

        return products, max_page_no

    @staticmethod
    def _safe_float(value) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
