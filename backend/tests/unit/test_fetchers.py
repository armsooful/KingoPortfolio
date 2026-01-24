"""
Phase 11 Level 2: Fetcher 단위 테스트

Fetcher 인터페이스 및 팩토리 테스트
"""

import pytest
from datetime import date
from unittest.mock import Mock, patch, MagicMock
import os

from app.services.fetchers import (
    BaseFetcher,
    FetchResult,
    DataType,
    FetcherError,
    FetcherFactory,
    PykrxFetcher,
)


class TestFetchResult:
    """FetchResult 테스트"""

    def test_success_result(self):
        """성공 결과 생성"""
        data = [{"ticker": "005930", "close": 70000}]
        result = FetchResult.success_result(
            data=data,
            source_id="PYKRX",
            data_type=DataType.STOCK_OHLCV,
            params={"ticker": "005930"},
        )

        assert result.success is True
        assert result.data == data
        assert result.source_id == "PYKRX"
        assert result.data_type == DataType.STOCK_OHLCV
        assert result.total_count == 1
        assert result.error_message is None

    def test_error_result(self):
        """에러 결과 생성"""
        result = FetchResult.error_result(
            error_message="데이터 없음",
            source_id="PYKRX",
            data_type=DataType.STOCK_OHLCV,
            params={"ticker": "000000"},
        )

        assert result.success is False
        assert result.error_message == "데이터 없음"
        assert result.data == []
        assert result.total_count == 0


class TestFetcherFactory:
    """FetcherFactory 테스트"""

    def setup_method(self):
        """각 테스트 전 팩토리 상태 저장"""
        self._original_registry = FetcherFactory._registry.copy()
        self._original_instances = FetcherFactory._instances.copy()

    def teardown_method(self):
        """각 테스트 후 팩토리 상태 복원"""
        FetcherFactory._registry = self._original_registry
        FetcherFactory._instances = self._original_instances

    def test_register_fetcher(self):
        """Fetcher 등록"""

        class TestFetcher(BaseFetcher):
            source_id = "TEST"
            source_name = "Test Fetcher"
            supported_data_types = [DataType.STOCK_OHLCV]

            def fetch(self, data_type, params):
                return FetchResult.success_result([], "TEST", data_type)

        FetcherFactory.register(TestFetcher)

        assert "TEST" in FetcherFactory._registry
        assert FetcherFactory._registry["TEST"] == TestFetcher

    def test_get_fetcher(self):
        """등록된 Fetcher 조회"""
        # PykrxFetcher는 이미 등록되어 있음
        fetcher = FetcherFactory.get_fetcher("PYKRX")

        assert fetcher is not None
        assert fetcher.source_id == "PYKRX"

    def test_get_fetcher_not_found(self):
        """등록되지 않은 Fetcher 조회 시 예외"""
        with pytest.raises(FetcherError) as exc_info:
            FetcherFactory.get_fetcher("UNKNOWN")

        assert "등록되지 않은 데이터 소스" in str(exc_info.value)

    def test_get_fetcher_singleton(self):
        """Fetcher 싱글톤 패턴"""
        fetcher1 = FetcherFactory.get_fetcher("PYKRX")
        fetcher2 = FetcherFactory.get_fetcher("PYKRX")

        assert fetcher1 is fetcher2

    def test_list_registered_sources(self):
        """등록된 소스 목록"""
        sources = FetcherFactory.list_registered_sources()

        assert "PYKRX" in sources
        assert "KRX_INFO" in sources

    def test_get_supported_data_types(self):
        """소스별 지원 데이터 유형"""
        types = FetcherFactory.get_supported_data_types("PYKRX")

        assert DataType.STOCK_OHLCV in types
        assert DataType.INDEX_OHLCV in types

    def test_get_fetcher_for_data_type(self):
        """데이터 유형별 Fetcher 조회"""
        fetcher = FetcherFactory.get_fetcher_for_data_type(DataType.STOCK_OHLCV)

        assert fetcher is not None
        assert fetcher.supports(DataType.STOCK_OHLCV)

    def test_get_all_fetchers_for_data_type(self):
        """데이터 유형을 지원하는 모든 Fetcher 조회"""
        fetchers = FetcherFactory.get_all_fetchers_for_data_type(DataType.STOCK_OHLCV)

        assert len(fetchers) >= 1
        for f in fetchers:
            assert f.supports(DataType.STOCK_OHLCV)


class TestPykrxFetcher:
    """PykrxFetcher 테스트"""

    def test_source_info(self):
        """소스 정보 확인"""
        fetcher = PykrxFetcher()

        assert fetcher.source_id == "PYKRX"
        assert fetcher.source_name == "pykrx 라이브러리"

    def test_supported_data_types(self):
        """지원 데이터 유형"""
        fetcher = PykrxFetcher()

        assert DataType.STOCK_OHLCV in fetcher.supported_data_types
        assert DataType.INDEX_OHLCV in fetcher.supported_data_types
        assert DataType.STOCK_INFO in fetcher.supported_data_types
        assert DataType.FUNDAMENTAL in fetcher.supported_data_types

    def test_validate_params_stock_ohlcv(self):
        """STOCK_OHLCV 파라미터 검증"""
        fetcher = PykrxFetcher()

        # 필수 파라미터 누락
        errors = fetcher.validate_params(DataType.STOCK_OHLCV, {})
        assert len(errors) > 0
        assert any("ticker" in e for e in errors)

        # 모든 파라미터 제공
        params = {
            "ticker": "005930",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "as_of_date": "2024-02-01",
        }
        errors = fetcher.validate_params(DataType.STOCK_OHLCV, params)
        assert len(errors) == 0

    def test_validate_params_unsupported_type(self):
        """지원하지 않는 데이터 유형"""
        fetcher = PykrxFetcher()

        errors = fetcher.validate_params(DataType.FINANCIAL_STATEMENT, {})
        assert len(errors) > 0
        assert any("지원하지 않" in e for e in errors)

    def test_get_required_params(self):
        """필수 파라미터 목록"""
        fetcher = PykrxFetcher()

        params = fetcher.get_required_params(DataType.STOCK_OHLCV)
        assert "ticker" in params
        assert "start_date" in params
        assert "end_date" in params
        assert "as_of_date" in params


class TestDartFetcher:
    """DartFetcher 테스트"""

    @pytest.fixture
    def mock_dart_fetcher(self):
        """DART API 키가 설정된 Mock Fetcher"""
        with patch.dict(os.environ, {"DART_API_KEY": "test_api_key"}):
            from app.services.fetchers.dart_fetcher import DartFetcher

            fetcher = DartFetcher()
            return fetcher

    def test_source_info(self, mock_dart_fetcher):
        """소스 정보 확인"""
        assert mock_dart_fetcher.source_id == "DART"
        assert mock_dart_fetcher.source_name == "DART OpenAPI"

    def test_supported_data_types(self, mock_dart_fetcher):
        """지원 데이터 유형"""
        assert DataType.FINANCIAL_STATEMENT in mock_dart_fetcher.supported_data_types
        assert DataType.DIVIDEND_HISTORY in mock_dart_fetcher.supported_data_types
        assert DataType.DISCLOSURE in mock_dart_fetcher.supported_data_types

    def test_validate_params_financial_statement(self, mock_dart_fetcher):
        """FINANCIAL_STATEMENT 파라미터 검증"""
        # 필수 파라미터 누락
        errors = mock_dart_fetcher.validate_params(DataType.FINANCIAL_STATEMENT, {})
        assert len(errors) > 0

        # 잘못된 report_type
        params = {
            "ticker": "005930",
            "fiscal_year": 2024,
            "report_type": "INVALID",
            "as_of_date": date.today(),
        }
        errors = mock_dart_fetcher.validate_params(DataType.FINANCIAL_STATEMENT, params)
        assert any("report_type" in e for e in errors)

        # 올바른 파라미터
        params["report_type"] = "ANNUAL"
        errors = mock_dart_fetcher.validate_params(DataType.FINANCIAL_STATEMENT, params)
        assert len(errors) == 0

    def test_api_key_required(self):
        """API 키 없으면 예외"""
        with patch.dict(os.environ, {}, clear=True):
            # 환경변수에서 DART_API_KEY 제거
            if "DART_API_KEY" in os.environ:
                del os.environ["DART_API_KEY"]

            from app.services.fetchers.dart_fetcher import DartFetcher

            with pytest.raises(FetcherError) as exc_info:
                DartFetcher()

            assert "API 키" in str(exc_info.value)


class TestKrxInfoFetcher:
    """KrxInfoFetcher 테스트"""

    @pytest.fixture
    def fetcher(self):
        """KrxInfoFetcher 인스턴스"""
        from app.services.fetchers.krx_info_fetcher import KrxInfoFetcher

        return KrxInfoFetcher()

    def test_source_info(self, fetcher):
        """소스 정보 확인"""
        assert fetcher.source_id == "KRX_INFO"
        assert fetcher.source_name == "KRX 정보데이터시스템"

    def test_supported_data_types(self, fetcher):
        """지원 데이터 유형"""
        assert DataType.SECTOR_CLASSIFICATION in fetcher.supported_data_types
        assert DataType.INSTITUTION_TRADE in fetcher.supported_data_types
        assert DataType.ETF_PORTFOLIO in fetcher.supported_data_types

    def test_validate_params_sector(self, fetcher):
        """SECTOR_CLASSIFICATION 파라미터 검증"""
        # 필수 파라미터 누락
        errors = fetcher.validate_params(DataType.SECTOR_CLASSIFICATION, {})
        assert len(errors) > 0
        assert any("as_of_date" in e for e in errors)

        # 올바른 파라미터
        params = {"as_of_date": date.today()}
        errors = fetcher.validate_params(DataType.SECTOR_CLASSIFICATION, params)
        assert len(errors) == 0

    def test_validate_params_institution(self, fetcher):
        """INSTITUTION_TRADE 파라미터 검증"""
        # 필수 파라미터 누락
        errors = fetcher.validate_params(DataType.INSTITUTION_TRADE, {})
        assert len(errors) > 0

        # 올바른 파라미터
        params = {"trade_date": date.today(), "as_of_date": date.today()}
        errors = fetcher.validate_params(DataType.INSTITUTION_TRADE, params)
        assert len(errors) == 0

    def test_validate_params_etf(self, fetcher):
        """ETF_PORTFOLIO 파라미터 검증"""
        # 필수 파라미터 누락
        errors = fetcher.validate_params(DataType.ETF_PORTFOLIO, {})
        assert len(errors) > 0

        # 올바른 파라미터
        params = {"etf_ticker": "069500", "as_of_date": date.today()}
        errors = fetcher.validate_params(DataType.ETF_PORTFOLIO, params)
        assert len(errors) == 0

    def test_parse_int(self, fetcher):
        """정수 파싱"""
        assert fetcher._parse_int("1,234") == 1234
        assert fetcher._parse_int("-") == 0
        assert fetcher._parse_int("") == 0
        assert fetcher._parse_int("abc") == 0

    def test_parse_float(self, fetcher):
        """실수 파싱"""
        assert fetcher._parse_float("1,234.56") == 1234.56
        assert fetcher._parse_float("-") == 0.0
        assert fetcher._parse_float("") == 0.0


class TestDataType:
    """DataType Enum 테스트"""

    def test_level1_types(self):
        """Level 1 데이터 유형"""
        assert DataType.STOCK_OHLCV.value == "STOCK_OHLCV"
        assert DataType.INDEX_OHLCV.value == "INDEX_OHLCV"
        assert DataType.STOCK_INFO.value == "STOCK_INFO"
        assert DataType.FUNDAMENTAL.value == "FUNDAMENTAL"

    def test_level2_types(self):
        """Level 2 데이터 유형"""
        assert DataType.FINANCIAL_STATEMENT.value == "FINANCIAL_STATEMENT"
        assert DataType.DIVIDEND_HISTORY.value == "DIVIDEND_HISTORY"
        assert DataType.DISCLOSURE.value == "DISCLOSURE"
        assert DataType.SECTOR_CLASSIFICATION.value == "SECTOR_CLASSIFICATION"
        assert DataType.INSTITUTION_TRADE.value == "INSTITUTION_TRADE"
        assert DataType.ETF_PORTFOLIO.value == "ETF_PORTFOLIO"


class TestSourcePriority:
    """소스 우선순위 테스트"""

    def test_stock_ohlcv_priority(self):
        """STOCK_OHLCV 소스 우선순위"""
        priority = FetcherFactory._source_priority.get(DataType.STOCK_OHLCV, [])

        assert "PYKRX" in priority
        # PYKRX가 첫 번째 우선순위
        assert priority.index("PYKRX") == 0

    def test_financial_statement_priority(self):
        """FINANCIAL_STATEMENT 소스 우선순위"""
        priority = FetcherFactory._source_priority.get(DataType.FINANCIAL_STATEMENT, [])

        assert "DART" in priority

    def test_sector_priority(self):
        """SECTOR_CLASSIFICATION 소스 우선순위"""
        priority = FetcherFactory._source_priority.get(DataType.SECTOR_CLASSIFICATION, [])

        assert "KRX_INFO" in priority
