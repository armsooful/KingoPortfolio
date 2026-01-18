"""
관리자 데이터 품질 리포트 API
"""

from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import date

from app.auth import require_admin_permission
from app.database import get_db
from app.models.user import User
from app.services.data_quality_report_service import DataQualityReportService
from app.utils.request_meta import request_meta, require_idempotency


router = APIRouter(
    prefix="/admin/data-quality",
    tags=["Admin Data Quality"],
    dependencies=[Depends(require_idempotency)],
)


class DataQualityReportCreate(BaseModel):
    execution_id: str = Field(..., min_length=1)
    report_date: date | None = None


@router.post("/reports")
def create_report(
    payload: DataQualityReportCreate,
    current_user: User = Depends(require_admin_permission("ADMIN_RUN")),
    db: Session = Depends(get_db),
    meta: Dict[str, Optional[str]] = Depends(request_meta(require_idempotency=True)),
):
    """리포트 생성"""
    service = DataQualityReportService(db)
    report = service.create_report(payload.execution_id, payload.report_date)
    return {
        "success": True,
        "data": {"report_id": report.report_id},
        "request_id": meta["request_id"],
    }


@router.get("/reports")
def list_reports(
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW")),
    db: Session = Depends(get_db),
):
    """리포트 목록 조회"""
    service = DataQualityReportService(db)
    reports = service.list_reports(limit=limit, offset=offset)
    return {
        "success": True,
        "data": [
            {
                "report_id": r.report_id,
                "execution_id": r.execution_id,
                "report_date": r.report_date,
                "summary": r.summary_json,
                "created_at": r.created_at,
            }
            for r in reports
        ],
    }


@router.get("/reports/{report_id}")
def get_report(
    report_id: str,
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW")),
    db: Session = Depends(get_db),
):
    """리포트 상세 조회"""
    service = DataQualityReportService(db)
    report = service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    items = service.list_report_items(report_id)
    return {
        "success": True,
        "data": {
            "report_id": report.report_id,
            "execution_id": report.execution_id,
            "report_date": report.report_date,
            "summary": report.summary_json,
            "items": [
                {
                    "item_id": i.item_id,
                    "dataset_type": i.dataset_type,
                    "status": i.status,
                    "detail": i.detail_json,
                }
                for i in items
            ],
        },
    }
