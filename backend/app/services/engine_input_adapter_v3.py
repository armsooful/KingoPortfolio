"""
Phase 8-B 입력 어댑터 (v3)

확장 입력을 기존 평가 엔진에 안전하게 전달한다.
지원되지 않는 입력은 중립 오류로 처리한다.
"""

from dataclasses import dataclass
from typing import Optional

from app.services.phase7_errors import Phase7EvaluationError


@dataclass
class InputContext:
    asset_class: Optional[str]
    currency: Optional[str]
    return_type: Optional[str]


def build_input_context(extensions: Optional[dict]) -> InputContext:
    if not extensions:
        return InputContext(asset_class=None, currency=None, return_type=None)

    asset_class = extensions.get("asset_class")
    currency = extensions.get("currency")
    return_type = extensions.get("return_type")

    if asset_class not in (None, "EQUITY", "ETF"):
        raise Phase7EvaluationError("선택한 기간의 과거 데이터를 불러올 수 없습니다.")

    if currency not in (None, "KRW", "USD"):
        raise Phase7EvaluationError("선택한 기간의 과거 데이터를 불러올 수 없습니다.")

    if currency == "USD":
        raise Phase7EvaluationError("선택한 기간의 과거 데이터를 불러올 수 없습니다.")

    if return_type not in (None, "PRICE", "TOTAL_RETURN"):
        raise Phase7EvaluationError("선택한 기간의 과거 데이터를 불러올 수 없습니다.")

    if return_type == "TOTAL_RETURN":
        raise Phase7EvaluationError("선택한 기간의 과거 데이터를 불러올 수 없습니다.")

    return InputContext(
        asset_class=asset_class,
        currency=currency,
        return_type=return_type,
    )
