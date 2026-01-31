"""
Phase 11 Level 2: 데이터 Fetcher 모듈

확장 가능한 데이터 소스 연동 아키텍처

지원 데이터 소스:
- PYKRX: 주식/지수 일별 시세, 기본 지표
- DART: 재무제표, 배당, 공시 정보
- KRX_INFO: 기관/외인 매매, ETF 포트폴리오
"""

import os

from .base_fetcher import BaseFetcher, FetchResult, DataType, FetcherError
from .fetcher_factory import FetcherFactory
from .pykrx_adapter import PykrxFetcher
from .dart_fetcher import DartFetcher, DartApiError
from .krx_info_fetcher import KrxInfoFetcher, KrxApiError

# Fetcher 자동 등록
FetcherFactory.register(PykrxFetcher)
FetcherFactory.register(KrxInfoFetcher)

# DART는 API 키가 있을 때만 등록
if os.getenv("DART_API_KEY"):
    FetcherFactory.register(DartFetcher)

__all__ = [
    # Base
    "BaseFetcher",
    "FetchResult",
    "DataType",
    "FetcherError",
    "FetcherFactory",
    # Fetchers
    "PykrxFetcher",
    "DartFetcher",
    "DartApiError",
    "KrxInfoFetcher",
    "KrxApiError",
]
