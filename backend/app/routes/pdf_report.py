"""
PDF 리포트 생성 API 라우트
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
from io import BytesIO

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.services.pdf_report_generator import PDFReportGenerator
from app.services.portfolio_engine import create_default_portfolio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["PDF Reports"])


@router.get("/portfolio-pdf")
async def generate_portfolio_pdf_report(
    investment_amount: int = 10000000,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    포트폴리오 PDF 리포트 생성

    Args:
        investment_amount: 투자 금액 (기본값: 1000만원)
        current_user: 현재 로그인한 사용자
        db: 데이터베이스 세션

    Returns:
        PDF 파일 (application/pdf)
    """
    try:
        # 1. 사용자의 최근 진단 결과 확인
        from app.models import Diagnosis
        latest_diagnosis = db.query(Diagnosis).filter(
            Diagnosis.user_id == current_user.id
        ).order_by(Diagnosis.created_at.desc()).first()

        if not latest_diagnosis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No diagnosis found. Please complete the investment survey first."
            )

        # 2. 포트폴리오 생성
        portfolio_data = create_default_portfolio(
            db=db,
            investment_type=latest_diagnosis.investment_type,
            investment_amount=investment_amount
        )

        # 3. 사용자 데이터 준비
        user_data = {
            'email': current_user.email,
            'name': current_user.name or 'Valued Investor',
            'investment_type': latest_diagnosis.investment_type,
            'diagnosis_score': latest_diagnosis.score
        }

        # 4. PDF 생성
        generator = PDFReportGenerator()
        pdf_buffer = generator.generate_portfolio_report(
            portfolio_data=portfolio_data,
            user_data=user_data
        )

        # 5. 파일명 생성
        filename = f"portfolio_report_{current_user.email}_{datetime.now().strftime('%Y%m%d')}.pdf"

        # 6. PDF 응답 반환
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("PDF Report Error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF report: {str(e)}"
        )


@router.get("/diagnosis-pdf/{diagnosis_id}")
async def generate_diagnosis_pdf_report(
    diagnosis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    특정 진단 결과의 PDF 리포트 생성

    Args:
        diagnosis_id: 진단 ID
        current_user: 현재 로그인한 사용자
        db: 데이터베이스 세션

    Returns:
        PDF 파일 (application/pdf)
    """
    try:
        # 1. 진단 결과 조회
        from app.models import Diagnosis
        diagnosis = db.query(Diagnosis).filter(
            Diagnosis.id == diagnosis_id,
            Diagnosis.user_id == current_user.id
        ).first()

        if not diagnosis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Diagnosis not found or access denied"
            )

        # 2. 포트폴리오 생성 (진단 결과 기반)
        portfolio_data = create_default_portfolio(
            db=db,
            investment_type=diagnosis.investment_type,
            investment_amount=10000000  # 기본값
        )

        # 3. 사용자 데이터 준비
        user_data = {
            'email': current_user.email,
            'name': current_user.name or 'Valued Investor',
            'investment_type': diagnosis.investment_type,
            'diagnosis_score': diagnosis.score,
            'diagnosis_date': diagnosis.created_at.strftime('%Y-%m-%d')
        }

        # 4. PDF 생성
        generator = PDFReportGenerator()
        pdf_buffer = generator.generate_portfolio_report(
            portfolio_data=portfolio_data,
            user_data=user_data
        )

        # 5. 파일명 생성
        filename = f"diagnosis_report_{diagnosis_id}_{datetime.now().strftime('%Y%m%d')}.pdf"

        # 6. PDF 응답 반환
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("PDF Report Error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF report: {str(e)}"
        )


@router.get("/preview")
async def preview_report_data(
    investment_amount: int = 10000000,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    PDF 리포트 데이터 미리보기 (디버깅용)

    Args:
        investment_amount: 투자 금액
        current_user: 현재 로그인한 사용자
        db: 데이터베이스 세션

    Returns:
        JSON 형식의 리포트 데이터
    """
    try:
        # 1. 사용자의 최근 진단 결과 확인
        from app.models import Diagnosis
        latest_diagnosis = db.query(Diagnosis).filter(
            Diagnosis.user_id == current_user.id
        ).order_by(Diagnosis.created_at.desc()).first()

        if not latest_diagnosis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No diagnosis found"
            )

        # 2. 포트폴리오 생성
        portfolio_data = create_default_portfolio(
            db=db,
            investment_type=latest_diagnosis.investment_type,
            investment_amount=investment_amount
        )

        # 3. 사용자 데이터
        user_data = {
            'email': current_user.email,
            'name': current_user.name or 'Valued Investor',
            'investment_type': latest_diagnosis.investment_type,
            'diagnosis_score': latest_diagnosis.score
        }

        return {
            "success": True,
            "data": {
                "user": user_data,
                "portfolio": portfolio_data,
                "generated_at": datetime.now().isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to preview report: {str(e)}"
        )
