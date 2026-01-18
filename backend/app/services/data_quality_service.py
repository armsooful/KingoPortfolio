"""
Phase 3-C / Epic C-2: 데이터 품질/계보/재현성 서비스
"""

from datetime import datetime
import uuid
from typing import Dict, Any, Optional, List
from enum import Enum
from sqlalchemy.orm import Session

from app.models.data_quality import (
    ValidationRuleMaster,
    ValidationRuleVersion,
    ValidationResult,
)
from app.services.batch_execution import BatchExecutionService
from app.services.ops_alert_service import OpsAlertService, AlertType, AlertLevel


class ValidationStatus(str, Enum):
    """정합성 결과 상태"""
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class DataQualityService:
    """데이터 품질 서비스"""

    def __init__(self, db: Session):
        self.db = db
        self.batch_service = BatchExecutionService(db)

    def register_rule(
        self,
        rule_code: str,
        rule_type: str,
        rule_name: str,
        severity: str,
        scope_type: str = "GLOBAL",
        scope_key: Optional[str] = None,
        scope_value: Optional[str] = None,
        scope_json: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
    ) -> ValidationRuleMaster:
        """정합성 규칙 등록"""
        rule = self.db.query(ValidationRuleMaster).filter_by(rule_code=rule_code).first()
        if rule:
            return rule

        rule = ValidationRuleMaster(
            rule_code=rule_code,
            rule_type=rule_type,
            rule_name=rule_name,
            severity=severity,
            scope_type=scope_type,
            scope_key=scope_key,
            scope_value=scope_value,
            scope_json=scope_json or {},
            description=description,
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def add_rule_version(
        self,
        rule_code: str,
        version_no: int,
        rule_params: Dict[str, Any],
        effective_from: datetime,
        effective_to: Optional[datetime] = None,
    ) -> ValidationRuleVersion:
        """정합성 규칙 버전 등록"""
        version = ValidationRuleVersion(
            rule_version_id=None,
            rule_code=rule_code,
            version_no=version_no,
            rule_params=rule_params,
            effective_from=effective_from.date(),
            effective_to=effective_to.date() if effective_to else None,
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version

    def record_result(
        self,
        execution_id: str,
        rule_code: str,
        status: ValidationStatus,
        target_ref_type: str,
        target_ref_id: str,
        rule_version_id: Optional[str] = None,
        violation_count: int = 0,
        sample_detail: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """정합성 결과 기록"""
        result = ValidationResult(
            result_id=str(uuid.uuid4()),
            execution_id=execution_id,
            rule_code=rule_code,
            rule_version_id=rule_version_id,
            target_ref_type=target_ref_type,
            target_ref_id=target_ref_id,
            status=status.value,
            violation_count=violation_count,
            sample_detail=sample_detail,
        )
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        return result

    def summarize_results(self, execution_id: str) -> Dict[str, int]:
        """정합성 결과 요약"""
        summary = {s.value: 0 for s in ValidationStatus}
        results = self.db.query(ValidationResult).filter_by(execution_id=execution_id).all()
        for result in results:
            summary[result.status] = summary.get(result.status, 0) + 1
        return summary

    def enforce_policy(
        self,
        execution_id: str,
        fail_error_code: str = "C2-DQ-001",
        warn_threshold: Optional[int] = None,
        alert_on_fail: bool = True,
        alert_on_warn: bool = True,
    ) -> Dict[str, Any]:
        """
        결과 상태에 따른 처리 정책 적용

        - FAIL 존재: 실행 FAILED 처리
        - WARN 존재: 정상 진행
        """
        summary = self.summarize_results(execution_id)
        fail_count = summary.get(ValidationStatus.FAIL.value, 0)
        warn_count = summary.get(ValidationStatus.WARN.value, 0)
        alert_service = OpsAlertService(self.db)

        if fail_count > 0:
            self.batch_service.fail_execution(
                execution_id=execution_id,
                error_code=fail_error_code,
                error_message=f"Validation FAIL: {fail_count} rule(s)",
            )
            if alert_on_fail:
                alert_service.send_alert(
                    alert_type=AlertType.SYSTEM_ERROR,
                    alert_level=AlertLevel.ERROR,
                    title=f"[DQ FAIL] execution={execution_id}",
                    message=f"Validation FAIL: {fail_count} rule(s)",
                    execution_id=execution_id,
                    error_code=fail_error_code,
                    detail={"summary": summary},
                )
            return {
                "status": ValidationStatus.FAIL.value,
                "summary": summary,
            }

        if warn_count > 0:
            if alert_on_warn and (warn_threshold is None or warn_count >= warn_threshold):
                alert_service.send_alert(
                    alert_type=AlertType.SYSTEM_ERROR,
                    alert_level=AlertLevel.WARN,
                    title=f"[DQ WARN] execution={execution_id}",
                    message=f"Validation WARN: {warn_count} rule(s)",
                    execution_id=execution_id,
                    error_code="C2-DQ-WARN",
                    detail={"summary": summary},
                )
            return {
                "status": ValidationStatus.WARN.value,
                "summary": summary,
            }

        return {
            "status": ValidationStatus.PASS.value,
            "summary": summary,
        }
