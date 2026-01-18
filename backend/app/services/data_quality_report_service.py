"""
Phase 3-C / Epic C-2: 데이터 품질 리포트 서비스
"""

from datetime import date
import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.data_quality import (
    DataQualityReport,
    DataQualityReportItem,
    ValidationResult,
)


class DataQualityReportService:
    """데이터 품질 리포트 서비스"""

    def __init__(self, db: Session):
        self.db = db

    def _summarize_results(self, execution_id: str) -> Dict[str, int]:
        summary = {"PASS": 0, "WARN": 0, "FAIL": 0}
        results = self.db.query(ValidationResult).filter_by(execution_id=execution_id).all()
        for result in results:
            summary[result.status] = summary.get(result.status, 0) + 1
        return summary

    def create_report(
        self,
        execution_id: str,
        report_date: Optional[date] = None,
    ) -> DataQualityReport:
        """리포트 생성"""
        report_date = report_date or date.today()
        summary = self._summarize_results(execution_id)

        report = DataQualityReport(
            report_id=str(uuid.uuid4()),
            execution_id=execution_id,
            report_date=report_date,
            summary_json=summary,
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)

        # dataset_type별 결과 집계
        grouped: Dict[str, Dict[str, int]] = {}
        results = self.db.query(ValidationResult).filter_by(execution_id=execution_id).all()
        for result in results:
            dataset = result.target_ref_type
            grouped.setdefault(dataset, {"PASS": 0, "WARN": 0, "FAIL": 0})
            grouped[dataset][result.status] = grouped[dataset].get(result.status, 0) + 1

        for dataset_type, stats in grouped.items():
            item = DataQualityReportItem(
                item_id=str(uuid.uuid4()),
                report_id=report.report_id,
                dataset_type=dataset_type,
                status="FAIL" if stats.get("FAIL", 0) > 0 else ("WARN" if stats.get("WARN", 0) > 0 else "PASS"),
                detail_json=stats,
            )
            self.db.add(item)

        self.db.commit()
        return report

    def get_report(self, report_id: str) -> Optional[DataQualityReport]:
        """리포트 조회"""
        return self.db.query(DataQualityReport).filter_by(report_id=report_id).first()

    def list_reports(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[DataQualityReport]:
        """리포트 목록"""
        return (
            self.db.query(DataQualityReport)
            .order_by(DataQualityReport.report_date.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def list_report_items(self, report_id: str) -> List[DataQualityReportItem]:
        """리포트 항목 조회"""
        return (
            self.db.query(DataQualityReportItem)
            .filter_by(report_id=report_id)
            .order_by(DataQualityReportItem.created_at.asc())
            .all()
        )
