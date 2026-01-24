"""
Phase 11 Level 2: 데이터 Fetcher 모듈

확장 가능한 데이터 소스 연동 아키텍처
"""

from .base_fetcher import BaseFetcher, FetchResult, DataType, FetcherError
from .fetcher_factory import FetcherFactory
from .pykrx_adapter import PykrxFetcher

# Fetcher 자동 등록
FetcherFactory.register(PykrxFetcher)

__all__ = [
    "BaseFetcher",
    "FetchResult",
    "DataType",
    "FetcherError",
    "FetcherFactory",
    "PykrxFetcher",
]
