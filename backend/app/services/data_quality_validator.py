"""
Phase 11: 데이터 품질 검증 서비스

목적: 적재 전 데이터 품질 검증 및 로깅
작성일: 2026-01-24

검증 규칙:
- DQ-001: close_price > 0 (ERROR)
- DQ-002: volume >= 0 (ERROR)
- DQ-003: high_price >= low_price (ERROR)
- DQ-004: high_price >= open, close (WARNING)
- DQ-005: low_price <= open, close (WARNING)
- DQ-006: |change_rate| <= 30 (WARNING)
- DQ-007: market_cap > 0 if not NULL (WARNING)
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.real_data import DataQualityLog
from app.services.pykrx_fetcher import OHLCVRecord, IndexOHLCVRecord
from app.utils.structured_logging import get_structured_logger

logger = get_structured_logger(__name__)


class Severity(str, Enum):
    """검증 심각도"""

    ERROR = "ERROR"  # 적재 불가
    WARNING = "WARNING"  # 적재하되 플래그 표시
    INFO = "INFO"  # 정보성


@dataclass
class QualityIssue:
    """품질 이슈"""

    rule_id: str
    rule_name: str
    severity: Severity
    field_name: str
    field_value: Any
    expected_condition: str
    record_id: Optional[int] = None


@dataclass
class ValidationResult:
    """검증 결과"""

    is_valid: bool  # ERROR 없음
    has_warnings: bool  # WARNING 있음
    issues: List[QualityIssue] = field(default_factory=list)
    quality_flag: str = "NORMAL"

    @property
    def error_count(self) -> int:
        return len([i for i in self.issues if i.severity == Severity.ERROR])

    @property
    def warning_count(self) -> int:
        return len([i for i in self.issues if i.severity == Severity.WARNING])


class DataQualityValidator:
    """데이터 품질 검증기"""

    # 상한가/하한가 기준 (30%)
    MAX_CHANGE_RATE = Decimal("30.0")

    def __init__(self, db: Session):
        self.db = db

    def validate_ohlcv(self, record: OHLCVRecord) -> ValidationResult:
        """
        OHLCV 레코드 검증

        Args:
            record: OHLCVRecord

        Returns:
            ValidationResult
        """
        issues: List[QualityIssue] = []

        # DQ-001: close_price > 0
        if record.close_price <= 0:
            issues.append(
                QualityIssue(
                    rule_id="DQ-001",
                    rule_name="종가 양수 검증",
                    severity=Severity.ERROR,
                    field_name="close_price",
                    field_value=record.close_price,
                    expected_condition="close_price > 0",
                )
            )

        # DQ-002: volume >= 0
        if record.volume < 0:
            issues.append(
                QualityIssue(
                    rule_id="DQ-002",
                    rule_name="거래량 비음수 검증",
                    severity=Severity.ERROR,
                    field_name="volume",
                    field_value=record.volume,
                    expected_condition="volume >= 0",
                )
            )

        # DQ-003: high_price >= low_price
        if record.high_price < record.low_price:
            issues.append(
                QualityIssue(
                    rule_id="DQ-003",
                    rule_name="고가/저가 관계 검증",
                    severity=Severity.ERROR,
                    field_name="high_price, low_price",
                    field_value=f"H:{record.high_price}, L:{record.low_price}",
                    expected_condition="high_price >= low_price",
                )
            )

        # DQ-004: high >= open and high >= close
        if record.high_price < record.open_price or record.high_price < record.close_price:
            issues.append(
                QualityIssue(
                    rule_id="DQ-004",
                    rule_name="고가 최대값 검증",
                    severity=Severity.WARNING,
                    field_name="high_price",
                    field_value=f"H:{record.high_price}, O:{record.open_price}, C:{record.close_price}",
                    expected_condition="high_price >= max(open_price, close_price)",
                )
            )

        # DQ-005: low <= open and low <= close
        if record.low_price > record.open_price or record.low_price > record.close_price:
            issues.append(
                QualityIssue(
                    rule_id="DQ-005",
                    rule_name="저가 최소값 검증",
                    severity=Severity.WARNING,
                    field_name="low_price",
                    field_value=f"L:{record.low_price}, O:{record.open_price}, C:{record.close_price}",
                    expected_condition="low_price <= min(open_price, close_price)",
                )
            )

        # DQ-006: |change_rate| <= 30 (상한가/하한가)
        if record.change_rate is not None:
            if abs(record.change_rate) > self.MAX_CHANGE_RATE:
                issues.append(
                    QualityIssue(
                        rule_id="DQ-006",
                        rule_name="등락률 범위 검증",
                        severity=Severity.WARNING,
                        field_name="change_rate",
                        field_value=record.change_rate,
                        expected_condition=f"|change_rate| <= {self.MAX_CHANGE_RATE}",
                    )
                )

        # DQ-007: market_cap > 0 if not NULL
        if record.market_cap is not None and record.market_cap <= 0:
            issues.append(
                QualityIssue(
                    rule_id="DQ-007",
                    rule_name="시가총액 양수 검증",
                    severity=Severity.WARNING,
                    field_name="market_cap",
                    field_value=record.market_cap,
                    expected_condition="market_cap > 0 OR NULL",
                )
            )

        # 결과 생성
        has_errors = any(i.severity == Severity.ERROR for i in issues)
        has_warnings = any(i.severity == Severity.WARNING for i in issues)

        quality_flag = "NORMAL"
        if has_errors:
            quality_flag = "ERROR"
        elif has_warnings:
            quality_flag = "WARNING"

        return ValidationResult(
            is_valid=not has_errors,
            has_warnings=has_warnings,
            issues=issues,
            quality_flag=quality_flag,
        )

    def validate_index_ohlcv(self, record: IndexOHLCVRecord) -> ValidationResult:
        """
        지수 OHLCV 레코드 검증

        Args:
            record: IndexOHLCVRecord

        Returns:
            ValidationResult
        """
        issues: List[QualityIssue] = []

        # DQ-001: close_price > 0
        if record.close_price <= 0:
            issues.append(
                QualityIssue(
                    rule_id="DQ-001",
                    rule_name="지수 종가 양수 검증",
                    severity=Severity.ERROR,
                    field_name="close_price",
                    field_value=record.close_price,
                    expected_condition="close_price > 0",
                )
            )

        # DQ-003: high_price >= low_price
        if record.high_price < record.low_price:
            issues.append(
                QualityIssue(
                    rule_id="DQ-003",
                    rule_name="지수 고가/저가 관계 검증",
                    severity=Severity.ERROR,
                    field_name="high_price, low_price",
                    field_value=f"H:{record.high_price}, L:{record.low_price}",
                    expected_condition="high_price >= low_price",
                )
            )

        # DQ-004: high >= open and high >= close
        if record.high_price < record.open_price or record.high_price < record.close_price:
            issues.append(
                QualityIssue(
                    rule_id="DQ-004",
                    rule_name="지수 고가 최대값 검증",
                    severity=Severity.WARNING,
                    field_name="high_price",
                    field_value=f"H:{record.high_price}, O:{record.open_price}, C:{record.close_price}",
                    expected_condition="high_price >= max(open_price, close_price)",
                )
            )

        # DQ-005: low <= open and low <= close
        if record.low_price > record.open_price or record.low_price > record.close_price:
            issues.append(
                QualityIssue(
                    rule_id="DQ-005",
                    rule_name="지수 저가 최소값 검증",
                    severity=Severity.WARNING,
                    field_name="low_price",
                    field_value=f"L:{record.low_price}, O:{record.open_price}, C:{record.close_price}",
                    expected_condition="low_price <= min(open_price, close_price)",
                )
            )

        has_errors = any(i.severity == Severity.ERROR for i in issues)
        has_warnings = any(i.severity == Severity.WARNING for i in issues)

        quality_flag = "NORMAL"
        if has_errors:
            quality_flag = "ERROR"
        elif has_warnings:
            quality_flag = "WARNING"

        return ValidationResult(
            is_valid=not has_errors,
            has_warnings=has_warnings,
            issues=issues,
            quality_flag=quality_flag,
        )

    def log_quality_issues(
        self,
        batch_id: int,
        table_name: str,
        issues: List[QualityIssue],
        record_id: Optional[int] = None,
    ) -> None:
        """
        품질 이슈 DB 로깅

        Args:
            batch_id: 배치 ID
            table_name: 대상 테이블명
            issues: 품질 이슈 목록
            record_id: 관련 레코드 ID
        """
        for issue in issues:
            log_entry = DataQualityLog(
                batch_id=batch_id,
                table_name=table_name,
                rule_id=issue.rule_id,
                rule_name=issue.rule_name,
                severity=issue.severity.value,
                record_id=record_id or issue.record_id,
                field_name=issue.field_name,
                field_value=str(issue.field_value)[:200],  # 최대 200자
                expected_condition=issue.expected_condition,
            )
            self.db.add(log_entry)

        if issues:
            self.db.commit()
            logger.debug(
                "품질 이슈 로깅 완료",
                {"batch_id": batch_id, "issue_count": len(issues)},
            )

    def calculate_quality_metrics(
        self,
        total_records: int,
        null_counts: Dict[str, int],
        outlier_count: int,
    ) -> Dict[str, Decimal]:
        """
        품질 메트릭 계산

        Args:
            total_records: 전체 레코드 수
            null_counts: 필드별 NULL 수
            outlier_count: 이상치 수

        Returns:
            품질 메트릭 딕셔너리
        """
        if total_records == 0:
            return {
                "quality_score": Decimal("0"),
                "null_ratio": Decimal("0"),
                "outlier_ratio": Decimal("0"),
            }

        # NULL 비율 (전체 필드 기준)
        total_null = sum(null_counts.values())
        null_ratio = Decimal(str(total_null / (total_records * len(null_counts))))

        # 이상치 비율
        outlier_ratio = Decimal(str(outlier_count / total_records))

        # 품질 점수 (100 - 페널티)
        # NULL 페널티: 최대 20점
        # 이상치 페널티: 최대 30점
        null_penalty = min(float(null_ratio) * 100, 20)
        outlier_penalty = min(float(outlier_ratio) * 100, 30)
        quality_score = max(Decimal("0"), Decimal(str(100 - null_penalty - outlier_penalty)))

        return {
            "quality_score": quality_score.quantize(Decimal("0.01")),
            "null_ratio": null_ratio.quantize(Decimal("0.0001")),
            "outlier_ratio": outlier_ratio.quantize(Decimal("0.0001")),
        }
