"""
Phase 11: 데이터 품질 검증 단위 테스트
"""

from datetime import date
from decimal import Decimal

import pytest

from app.services.data_quality_validator import (
    DataQualityValidator,
    Severity,
    ValidationResult,
)
from app.services.pykrx_fetcher import OHLCVRecord, IndexOHLCVRecord


class TestDataQualityValidator:
    """DataQualityValidator 테스트"""

    @pytest.fixture
    def validator(self, db):
        return DataQualityValidator(db)

    # =========================================================================
    # OHLCV 검증 테스트
    # =========================================================================

    def test_validate_ohlcv_valid_record(self, validator):
        """정상 OHLCV 레코드 검증"""
        record = OHLCVRecord(
            ticker="005930",
            trade_date=date(2024, 1, 15),
            open_price=Decimal("70000"),
            high_price=Decimal("71000"),
            low_price=Decimal("69000"),
            close_price=Decimal("70500"),
            volume=1000000,
        )

        result = validator.validate_ohlcv(record)

        assert result.is_valid is True
        assert result.has_warnings is False
        assert result.quality_flag == "NORMAL"
        assert len(result.issues) == 0

    def test_validate_ohlcv_negative_close_price(self, validator):
        """음수 종가 검증 (ERROR)"""
        record = OHLCVRecord(
            ticker="005930",
            trade_date=date(2024, 1, 15),
            open_price=Decimal("70000"),
            high_price=Decimal("71000"),
            low_price=Decimal("69000"),
            close_price=Decimal("-100"),  # ERROR
            volume=1000000,
        )

        result = validator.validate_ohlcv(record)

        assert result.is_valid is False
        assert result.quality_flag == "ERROR"
        assert any(i.rule_id == "DQ-001" for i in result.issues)

    def test_validate_ohlcv_zero_close_price(self, validator):
        """0 종가 검증 (ERROR)"""
        record = OHLCVRecord(
            ticker="005930",
            trade_date=date(2024, 1, 15),
            open_price=Decimal("70000"),
            high_price=Decimal("71000"),
            low_price=Decimal("69000"),
            close_price=Decimal("0"),  # ERROR
            volume=1000000,
        )

        result = validator.validate_ohlcv(record)

        assert result.is_valid is False
        assert any(i.rule_id == "DQ-001" for i in result.issues)

    def test_validate_ohlcv_negative_volume(self, validator):
        """음수 거래량 검증 (ERROR)"""
        record = OHLCVRecord(
            ticker="005930",
            trade_date=date(2024, 1, 15),
            open_price=Decimal("70000"),
            high_price=Decimal("71000"),
            low_price=Decimal("69000"),
            close_price=Decimal("70500"),
            volume=-100,  # ERROR
        )

        result = validator.validate_ohlcv(record)

        assert result.is_valid is False
        assert any(i.rule_id == "DQ-002" for i in result.issues)

    def test_validate_ohlcv_high_less_than_low(self, validator):
        """고가 < 저가 검증 (ERROR)"""
        record = OHLCVRecord(
            ticker="005930",
            trade_date=date(2024, 1, 15),
            open_price=Decimal("70000"),
            high_price=Decimal("69000"),  # ERROR: high < low
            low_price=Decimal("71000"),
            close_price=Decimal("70500"),
            volume=1000000,
        )

        result = validator.validate_ohlcv(record)

        assert result.is_valid is False
        assert any(i.rule_id == "DQ-003" for i in result.issues)

    def test_validate_ohlcv_high_less_than_close(self, validator):
        """고가 < 종가 검증 (WARNING)"""
        record = OHLCVRecord(
            ticker="005930",
            trade_date=date(2024, 1, 15),
            open_price=Decimal("70000"),
            high_price=Decimal("70000"),  # WARNING: high < close
            low_price=Decimal("69000"),
            close_price=Decimal("71000"),
            volume=1000000,
        )

        result = validator.validate_ohlcv(record)

        assert result.is_valid is True  # WARNING은 valid
        assert result.has_warnings is True
        assert result.quality_flag == "WARNING"
        assert any(i.rule_id == "DQ-004" for i in result.issues)

    def test_validate_ohlcv_extreme_change_rate(self, validator):
        """극단적 등락률 검증 (WARNING)"""
        record = OHLCVRecord(
            ticker="005930",
            trade_date=date(2024, 1, 15),
            open_price=Decimal("70000"),
            high_price=Decimal("100000"),
            low_price=Decimal("70000"),
            close_price=Decimal("100000"),
            volume=1000000,
            change_rate=Decimal("35.5"),  # WARNING: > 30%
        )

        result = validator.validate_ohlcv(record)

        assert result.is_valid is True
        assert result.has_warnings is True
        assert any(i.rule_id == "DQ-006" for i in result.issues)

    # =========================================================================
    # Index OHLCV 검증 테스트
    # =========================================================================

    def test_validate_index_ohlcv_valid(self, validator):
        """정상 지수 OHLCV 검증"""
        record = IndexOHLCVRecord(
            index_code="KOSPI",
            trade_date=date(2024, 1, 15),
            open_price=Decimal("2500.00"),
            high_price=Decimal("2520.00"),
            low_price=Decimal("2490.00"),
            close_price=Decimal("2510.00"),
        )

        result = validator.validate_index_ohlcv(record)

        assert result.is_valid is True
        assert result.has_warnings is False

    def test_validate_index_ohlcv_invalid_close(self, validator):
        """음수 지수 종가 검증 (ERROR)"""
        record = IndexOHLCVRecord(
            index_code="KOSPI",
            trade_date=date(2024, 1, 15),
            open_price=Decimal("2500.00"),
            high_price=Decimal("2520.00"),
            low_price=Decimal("2490.00"),
            close_price=Decimal("-10.00"),  # ERROR
        )

        result = validator.validate_index_ohlcv(record)

        assert result.is_valid is False
        assert any(i.rule_id == "DQ-001" for i in result.issues)

    # =========================================================================
    # 품질 메트릭 계산 테스트
    # =========================================================================

    def test_calculate_quality_metrics_perfect(self, validator):
        """완벽한 품질 메트릭 계산"""
        metrics = validator.calculate_quality_metrics(
            total_records=100,
            null_counts={"field1": 0, "field2": 0},
            outlier_count=0,
        )

        assert metrics["quality_score"] == Decimal("100.00")
        assert metrics["null_ratio"] == Decimal("0.0000")
        assert metrics["outlier_ratio"] == Decimal("0.0000")

    def test_calculate_quality_metrics_with_nulls(self, validator):
        """NULL 있는 품질 메트릭 계산"""
        metrics = validator.calculate_quality_metrics(
            total_records=100,
            null_counts={"field1": 10, "field2": 5},  # 15 nulls / 200 total = 7.5%
            outlier_count=0,
        )

        assert metrics["null_ratio"] > Decimal("0")
        assert metrics["quality_score"] < Decimal("100")

    def test_calculate_quality_metrics_with_outliers(self, validator):
        """이상치 있는 품질 메트릭 계산"""
        metrics = validator.calculate_quality_metrics(
            total_records=100,
            null_counts={"field1": 0},
            outlier_count=10,  # 10%
        )

        assert metrics["outlier_ratio"] == Decimal("0.1000")
        assert metrics["quality_score"] < Decimal("100")

    def test_calculate_quality_metrics_empty(self, validator):
        """빈 데이터 품질 메트릭"""
        metrics = validator.calculate_quality_metrics(
            total_records=0,
            null_counts={},
            outlier_count=0,
        )

        assert metrics["quality_score"] == Decimal("0")
