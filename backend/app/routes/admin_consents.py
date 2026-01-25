from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import require_admin_permission
from app.database import get_db
from app.models.consent import ConsentAgreement
from app.models.user import User
from app.schemas import AdminConsentItem, AdminConsentListResponse


router = APIRouter(prefix="/admin/consents", tags=["Admin Consents"])


@router.get("", response_model=AdminConsentListResponse)
def list_admin_consents(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW")),
    q: Optional[str] = Query(None, description="사용자 이메일/이름 검색"),
    consent_type: Optional[str] = Query(None, description="동의 유형 필터"),
    start_date: Optional[datetime] = Query(None, description="조회 시작 일시"),
    end_date: Optional[datetime] = Query(None, description="조회 종료 일시"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    query = (
        db.query(ConsentAgreement, User)
        .join(User, ConsentAgreement.owner_user_id == User.id)
        .order_by(ConsentAgreement.agreed_at.desc())
    )

    if q:
        pattern = f"%{q}%"
        query = query.filter((User.email.ilike(pattern)) | (User.name.ilike(pattern)))

    if consent_type:
        query = query.filter(ConsentAgreement.consent_type == consent_type)

    if start_date:
        query = query.filter(ConsentAgreement.agreed_at >= start_date)

    if end_date:
        query = query.filter(ConsentAgreement.agreed_at <= end_date)

    total = query.count()
    rows = query.offset(offset).limit(limit).all()

    return AdminConsentListResponse(
        count=total,
        consents=[
            AdminConsentItem(
                consent_id=consent.consent_id,
                consent_type=consent.consent_type,
                consent_version=consent.consent_version,
                consent_text=consent.consent_text,
                agreed_at=consent.agreed_at,
                ip_address=consent.ip_address,
                user_agent=consent.user_agent,
                user_id=user.id,
                user_email=user.email,
                user_name=user.name,
            )
            for consent, user in rows
        ],
    )
