from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.consent import ConsentAgreement
from app.schemas import ConsentCreateRequest, ConsentListResponse, ConsentResponse, ConsentHistoryItem


router = APIRouter(prefix="/api/v1/consents", tags=["Consents"])


@router.post("", response_model=ConsentResponse, status_code=status.HTTP_201_CREATED)
def create_consent(
    payload: ConsentCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    consent = ConsentAgreement(
        owner_user_id=current_user.id,
        consent_type=payload.consent_type,
        consent_version=payload.consent_version,
        consent_text=payload.consent_text,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)

    return ConsentResponse(
        consent_id=consent.consent_id,
        consent_type=consent.consent_type,
        consent_version=consent.consent_version,
        consent_text=consent.consent_text,
        agreed_at=consent.agreed_at,
    )


@router.get("", response_model=ConsentListResponse)
def list_consents(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
):
    query = (
        db.query(ConsentAgreement)
        .filter(ConsentAgreement.owner_user_id == current_user.id)
        .order_by(ConsentAgreement.agreed_at.desc())
    )
    total = query.count()
    consents = query.offset(offset).limit(limit).all()
    return ConsentListResponse(
        count=total,
        consents=[
            ConsentHistoryItem(
                consent_id=c.consent_id,
                consent_type=c.consent_type,
                consent_version=c.consent_version,
                consent_text=c.consent_text,
                agreed_at=c.agreed_at,
                ip_address=c.ip_address,
                user_agent=c.user_agent,
            )
            for c in consents
        ],
    )
