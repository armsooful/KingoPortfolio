"""
Phase 11 Level 2: 데이터 Fetcher 기본 인터페이스

목적: 다양한 데이터 소스를 일관된 인터페이스로 연동
작성일: 2026-01-24
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type


class DataType(str, Enum):
    """지원하는 데이터 유형"""

    # Level 1: 가격 데이터
    STOCK_OHLCV = "STOCK_OHLCV"
    INDEX_OHLCV = "INDEX_OHLCV"
    STOCK_INFO = "STOCK_INFO"
    FUNDAMENTAL = "FUNDAMENTAL"  # PER, PBR, 배당률

    # Level 2: 재무/공시 데이터
    FINANCIAL_STATEMENT = "FINANCIAL_STATEMENT"
    DIVIDEND_HISTORY = "DIVIDEND_HISTORY"
    DISCLOSURE = "DISCLOSURE"
    CORP_CODE = "CORP_CODE"

    # Level 2: 시장 데이터
    SECTOR_CLASSIFICATION = "SECTOR_CLASSIFICATION"
    INSTITUTION_TRADE = "INSTITUTION_TRADE"
    ETF_PORTFOLIO = "ETF_PORTFOLIO"


@dataclass
class FetchResult:
    """데이터 조회 결과"""

    success: bool
    data: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None
    source_id: str = ""
    data_type: Optional[DataType] = None
    fetched_at: datetime = field(default_factory=datetime.utcnow)

    # 메타 정보
    total_count: int = 0
    params: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success_result(
        cls,
        data: List[Dict[str, Any]],
        source_id: str,
        data_type: DataType,
        params: Optional[Dict[str, Any]] = None,
    ) -> "FetchResult":
        """성공 결과 생성"""
        return cls(
            success=True,
            data=data,
            source_id=source_id,
            data_type=data_type,
            total_count=len(data),
            params=params or {},
        )

    @classmethod
    def error_result(
        cls,
        error_message: str,
        source_id: str,
        data_type: Optional[DataType] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> "FetchResult":
        """에러 결과 생성"""
        return cls(
            success=False,
            error_message=error_message,
            source_id=source_id,
            data_type=data_type,
            params=params or {},
        )


class FetcherError(Exception):
    """Fetcher 예외"""

    def __init__(
        self,
        message: str,
        source_id: str = "",
        data_type: Optional[DataType] = None,
        detail: Optional[str] = None,
    ):
        self.message = message
        self.source_id = source_id
        self.data_type = data_type
        self.detail = detail
        super().__init__(self.message)


class BaseFetcher(ABC):
    """
    데이터 소스 Fetcher 기본 클래스

    새로운 데이터 소스 추가 시 이 클래스를 상속하여 구현합니다.

    Example:
        class MyFetcher(BaseFetcher):
            source_id = "MY_SOURCE"
            supported_data_types = [DataType.STOCK_OHLCV]

            def fetch(self, data_type, params):
                # 구현
                pass
    """

    # 하위 클래스에서 정의해야 하는 속성
    source_id: str = ""
    source_name: str = ""
    supported_data_types: List[DataType] = []

    @abstractmethod
    def fetch(
        self,
        data_type: DataType,
        params: Dict[str, Any],
    ) -> FetchResult:
        """
        데이터 조회

        Args:
            data_type: 조회할 데이터 유형
            params: 조회 파라미터 (데이터 유형별 상이)

        Returns:
            FetchResult

        Raises:
            FetcherError: 조회 실패 시
        """
        pass

    def validate_params(
        self,
        data_type: DataType,
        params: Dict[str, Any],
    ) -> List[str]:
        """
        파라미터 검증

        Args:
            data_type: 데이터 유형
            params: 검증할 파라미터

        Returns:
            에러 메시지 목록 (빈 리스트면 유효)
        """
        errors = []

        if data_type not in self.supported_data_types:
            errors.append(
                f"{self.source_id}는 {data_type.value}을 지원하지 않습니다. "
                f"지원: {[dt.value for dt in self.supported_data_types]}"
            )

        return errors

    def supports(self, data_type: DataType) -> bool:
        """특정 데이터 유형 지원 여부"""
        return data_type in self.supported_data_types

    def get_required_params(self, data_type: DataType) -> List[str]:
        """
        데이터 유형별 필수 파라미터 목록

        하위 클래스에서 오버라이드하여 구현
        """
        return []

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} source_id={self.source_id}>"
