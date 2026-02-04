"""
Phase 11 Level 2: Fetcher 팩토리

목적: 데이터 소스별 Fetcher 인스턴스 생성 및 관리
작성일: 2026-01-24
"""

from typing import Dict, List, Optional, Type

from .base_fetcher import BaseFetcher, DataType, FetcherError


class FetcherFactory:
    """
    Fetcher 팩토리

    데이터 소스별 Fetcher를 등록하고 인스턴스를 생성합니다.

    Example:
        # 등록
        FetcherFactory.register(PykrxFetcher)
        FetcherFactory.register(DartFetcher)

        # 사용
        fetcher = FetcherFactory.get_fetcher("PYKRX")
        result = fetcher.fetch(DataType.STOCK_OHLCV, params)
    """

    _registry: Dict[str, Type[BaseFetcher]] = {}
    _instances: Dict[str, BaseFetcher] = {}

    # 데이터 유형별 소스 우선순위
    _source_priority: Dict[DataType, List[str]] = {
        DataType.STOCK_OHLCV: ["PYKRX", "KRX_INFO", "NAVER"],
        DataType.INDEX_OHLCV: ["PYKRX", "KRX_INFO"],
        DataType.STOCK_INFO: ["PYKRX", "KRX_INFO"],
        DataType.FUNDAMENTAL: ["PYKRX", "DART"],
        DataType.FINANCIAL_STATEMENT: ["DART"],
        DataType.DIVIDEND_HISTORY: ["FSC_DATA_GO_KR", "DART"],
        DataType.DISCLOSURE: ["DART"],
        DataType.BOND_BASIC_INFO: ["FSC_BOND_INFO"],
        DataType.INSTITUTION_TRADE: ["KRX_INFO"],
        DataType.ETF_PORTFOLIO: ["KRX_INFO"],
    }

    @classmethod
    def register(cls, fetcher_class: Type[BaseFetcher]) -> None:
        """
        Fetcher 클래스 등록

        Args:
            fetcher_class: BaseFetcher를 상속한 클래스
        """
        if not fetcher_class.source_id:
            raise ValueError(f"{fetcher_class.__name__}에 source_id가 정의되지 않았습니다")

        cls._registry[fetcher_class.source_id] = fetcher_class

    @classmethod
    def unregister(cls, source_id: str) -> None:
        """Fetcher 등록 해제"""
        cls._registry.pop(source_id, None)
        cls._instances.pop(source_id, None)

    @classmethod
    def get_fetcher(cls, source_id: str, **kwargs) -> BaseFetcher:
        """
        Fetcher 인스턴스 반환

        Args:
            source_id: 데이터 소스 ID
            **kwargs: Fetcher 생성자 인자

        Returns:
            BaseFetcher 인스턴스

        Raises:
            FetcherError: 등록되지 않은 소스
        """
        if source_id not in cls._registry:
            raise FetcherError(
                f"등록되지 않은 데이터 소스: {source_id}. "
                f"등록된 소스: {list(cls._registry.keys())}",
                source_id=source_id,
            )

        # 싱글톤 패턴 (kwargs가 없을 때만)
        if not kwargs and source_id in cls._instances:
            return cls._instances[source_id]

        fetcher = cls._registry[source_id](**kwargs)

        if not kwargs:
            cls._instances[source_id] = fetcher

        return fetcher

    @classmethod
    def get_fetcher_for_data_type(
        cls,
        data_type: DataType,
        **kwargs,
    ) -> Optional[BaseFetcher]:
        """
        특정 데이터 유형에 대한 우선순위 높은 Fetcher 반환

        Args:
            data_type: 데이터 유형
            **kwargs: Fetcher 생성자 인자

        Returns:
            BaseFetcher 또는 None (지원하는 Fetcher 없음)
        """
        priority_sources = cls._source_priority.get(data_type, [])

        for source_id in priority_sources:
            if source_id in cls._registry:
                fetcher = cls.get_fetcher(source_id, **kwargs)
                if fetcher.supports(data_type):
                    return fetcher

        # 우선순위에 없는 소스 중 지원하는 것 찾기
        for source_id, fetcher_class in cls._registry.items():
            if data_type in fetcher_class.supported_data_types:
                return cls.get_fetcher(source_id, **kwargs)

        return None

    @classmethod
    def get_all_fetchers_for_data_type(
        cls,
        data_type: DataType,
        **kwargs,
    ) -> List[BaseFetcher]:
        """
        특정 데이터 유형을 지원하는 모든 Fetcher 반환 (우선순위 순)

        Args:
            data_type: 데이터 유형
            **kwargs: Fetcher 생성자 인자

        Returns:
            BaseFetcher 리스트
        """
        fetchers = []
        seen_sources = set()

        # 우선순위 순서대로
        priority_sources = cls._source_priority.get(data_type, [])
        for source_id in priority_sources:
            if source_id in cls._registry:
                fetcher = cls.get_fetcher(source_id, **kwargs)
                if fetcher.supports(data_type):
                    fetchers.append(fetcher)
                    seen_sources.add(source_id)

        # 나머지
        for source_id, fetcher_class in cls._registry.items():
            if source_id not in seen_sources:
                if data_type in fetcher_class.supported_data_types:
                    fetchers.append(cls.get_fetcher(source_id, **kwargs))

        return fetchers

    @classmethod
    def list_registered_sources(cls) -> List[str]:
        """등록된 모든 데이터 소스 ID 반환"""
        return list(cls._registry.keys())

    @classmethod
    def get_supported_data_types(cls, source_id: str) -> List[DataType]:
        """특정 소스가 지원하는 데이터 유형 반환"""
        if source_id not in cls._registry:
            return []
        return cls._registry[source_id].supported_data_types

    @classmethod
    def set_source_priority(
        cls,
        data_type: DataType,
        source_ids: List[str],
    ) -> None:
        """데이터 유형별 소스 우선순위 설정"""
        cls._source_priority[data_type] = source_ids

    @classmethod
    def clear(cls) -> None:
        """모든 등록 초기화 (테스트용)"""
        cls._registry.clear()
        cls._instances.clear()
