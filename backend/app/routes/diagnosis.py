from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import DiagnosisSubmitRequest, DiagnosisResponse, DiagnosisMeResponse, DiagnosisHistoryResponse, DiagnosisSummaryResponse
from app.auth import get_current_user
import app.models as models
from app.crud import (
    create_diagnosis,
    get_user_diagnoses,
    get_user_latest_diagnosis,
    get_diagnosis_by_id
)
from app.diagnosis import calculate_diagnosis, build_diagnosis_response
from app.services.claude_service import get_claude_service
from app.utils.export import generate_diagnosis_csv, generate_diagnosis_excel
from app.rate_limiter import limiter, RateLimits
from datetime import datetime

router = APIRouter(
    prefix="/diagnosis",
    tags=["Diagnosis"]
)

@router.post(
    "/submit",
    response_model=DiagnosisResponse,
    status_code=201,
    summary="설문 제출 및 진단",
    description="사용자의 설문 답변을 제출하여 투자성향 진단을 수행합니다."
)
@limiter.limit(RateLimits.DIAGNOSIS_SUBMIT)
async def submit_survey(
    request: Request,
    diagnosis_request: DiagnosisSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    설문 제출 및 진단 수행
    
    - **answers**: 설문 답변 목록 (question_id, answer_value)
    - **monthly_investment**: 월 투자 가능액 (만원, 선택)
    
    Returns: 진단 결과 (투자성향, 점수, 신뢰도 등)
    
    **권한**: 로그인 필수
    """
    
    # 입력 유효성 검증
    if not diagnosis_request.answers or len(diagnosis_request.answers) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one answer is required"
        )

    # 답변 값 검증 (1-5 범위)
    for answer in diagnosis_request.answers:
        if answer.answer_value < 1 or answer.answer_value > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Answer value must be between 1 and 5, got {answer.answer_value}"
            )

    # 월 투자액 검증
    if diagnosis_request.monthly_investment and diagnosis_request.monthly_investment < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Monthly investment must be greater than 0"
        )

    try:
        # 진단 계산
        investment_type, score, confidence = calculate_diagnosis(diagnosis_request.answers)

        # DB에 저장
        diagnosis = create_diagnosis(
            db=db,
            user_id=current_user.id,
            investment_type=investment_type,
            score=score,
            confidence=confidence,
            answers=diagnosis_request.answers,
            monthly_investment=diagnosis_request.monthly_investment
        )

        # 응답 빌드
        response_data = build_diagnosis_response(
            diagnosis_id=diagnosis.id,
            investment_type=diagnosis.investment_type,
            score=diagnosis.score,
            confidence=diagnosis.confidence,
            monthly_investment=diagnosis.monthly_investment,
            created_at=diagnosis.created_at
        )

        # Claude AI 분석 추가 (선택적 - API 키가 있을 때만)
        try:
            claude_service = get_claude_service()
            ai_analysis = claude_service.analyze_investment_profile(
                answers=diagnosis_request.answers,
                investment_type=investment_type,
                score=score,
                confidence=confidence,
                monthly_investment=diagnosis_request.monthly_investment
            )
            response_data["ai_analysis"] = ai_analysis
        except Exception as ai_error:
            # AI 분석 실패 시 로그만 남기고 계속 진행
            print(f"Claude AI 분석 실패 (무시됨): {str(ai_error)}")
            response_data["ai_analysis"] = None

        return DiagnosisResponse(**response_data)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Diagnosis failed: {str(e)}"
        )

@router.get(
    "/me",
    response_model=DiagnosisMeResponse,
    summary="최근 진단 결과 조회",
    description="현재 사용자의 가장 최근 진단 결과를 조회합니다."
)
async def get_latest_diagnosis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    최근 진단 결과 조회
    
    현재 사용자의 가장 최근 진단 결과를 반환합니다.
    
    **권한**: 로그인 필수
    """
    
    diagnosis = get_user_latest_diagnosis(db, current_user.id)
    
    if not diagnosis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No diagnosis found. Please submit survey first."
        )
    
    response_data = build_diagnosis_response(
        diagnosis_id=diagnosis.id,
        investment_type=diagnosis.investment_type,
        score=diagnosis.score,
        confidence=diagnosis.confidence,
        monthly_investment=diagnosis.monthly_investment,
        created_at=diagnosis.created_at
    )
    
    return DiagnosisMeResponse(**response_data)

@router.get(
    "/{diagnosis_id}",
    response_model=DiagnosisMeResponse,
    summary="특정 진단 결과 조회"
)
async def get_diagnosis(
    diagnosis_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    특정 진단 결과 조회
    
    - **diagnosis_id**: 진단 ID
    
    **권한**: 로그인 필수 (자신의 진단만 조회 가능)
    """
    
    diagnosis = get_diagnosis_by_id(db, diagnosis_id)
    
    if not diagnosis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnosis {diagnosis_id} not found"
        )
    
    # 자신의 진단만 조회 가능
    if diagnosis.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this diagnosis"
        )
    
    response_data = build_diagnosis_response(
        diagnosis_id=diagnosis.id,
        investment_type=diagnosis.investment_type,
        score=diagnosis.score,
        confidence=diagnosis.confidence,
        monthly_investment=diagnosis.monthly_investment,
        created_at=diagnosis.created_at
    )
    
    return DiagnosisMeResponse(**response_data)

@router.get(
    "/history/all",
    response_model=DiagnosisHistoryResponse,
    summary="진단 이력 조회",
    description="현재 사용자의 모든 진단 이력을 조회합니다."
)
async def get_diagnosis_history(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    진단 이력 조회
    
    - **limit**: 조회할 최대 개수 (기본값: 10)
    
    **권한**: 로그인 필수
    """
    
    diagnoses = get_user_diagnoses(db, current_user.id, limit)
    
    summary_list = [
        DiagnosisSummaryResponse(
            diagnosis_id=d.id,
            investment_type=d.investment_type,
            score=d.score,
            confidence=d.confidence,
            monthly_investment=d.monthly_investment,
            created_at=d.created_at
        )
        for d in diagnoses
    ]
    
    return DiagnosisHistoryResponse(
        total=len(summary_list),
        diagnoses=summary_list
    )

# 기존 GET /diagnosis/me/products에 추가

@router.get("/me/products")
async def get_recommended_products(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """DB 기반 추천 종목 조회"""
    
    diagnosis = db.query(models.Diagnosis).filter(
        models.Diagnosis.user_id == current_user.id
    ).order_by(models.Diagnosis.created_at.desc()).first()
    
    if not diagnosis:
        raise HTTPException(
            status_code=404,
            detail="진단 결과가 없습니다"
        )
    
    # DB 기반 추천
    from app.db_recommendation_engine import DBRecommendationEngine
    
    recommendations = DBRecommendationEngine.get_all_recommendations(
        db,
        diagnosis.investment_type
    )
    
    return {
        "diagnosis_id": str(diagnosis.id),
        "investment_type": diagnosis.investment_type,
        "portfolio": diagnosis.portfolio_recommendation,
        **recommendations
    }

@router.get(
    "/{diagnosis_id}/export/csv",
    summary="진단 결과 CSV 다운로드",
    description="특정 진단 결과를 CSV 파일로 다운로드합니다.",
    response_class=Response
)
@limiter.limit(RateLimits.DATA_EXPORT)
async def export_diagnosis_csv(
    request: Request,
    diagnosis_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    진단 결과 CSV 다운로드

    - **diagnosis_id**: 진단 ID

    Returns: CSV 파일 다운로드

    **권한**: 로그인 필수 (자신의 진단만 다운로드 가능)
    """
    # 진단 결과 조회
    diagnosis = get_diagnosis_by_id(db, diagnosis_id)

    if not diagnosis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnosis {diagnosis_id} not found"
        )

    # 권한 확인
    if diagnosis.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to export this diagnosis"
        )

    # 응답 데이터 빌드
    response_data = build_diagnosis_response(
        diagnosis_id=diagnosis.id,
        investment_type=diagnosis.investment_type,
        score=diagnosis.score,
        confidence=diagnosis.confidence,
        monthly_investment=diagnosis.monthly_investment,
        created_at=diagnosis.created_at
    )

    # CSV 생성
    csv_content = generate_diagnosis_csv(response_data)

    # 파일명 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"diagnosis_{diagnosis_id[:8]}_{timestamp}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "text/csv; charset=utf-8"
        }
    )

@router.get(
    "/{diagnosis_id}/export/excel",
    summary="진단 결과 Excel 다운로드",
    description="특정 진단 결과를 Excel 파일로 다운로드합니다.",
    response_class=Response
)
@limiter.limit(RateLimits.DATA_EXPORT)
async def export_diagnosis_excel(
    request: Request,
    diagnosis_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    진단 결과 Excel 다운로드

    - **diagnosis_id**: 진단 ID

    Returns: Excel 파일 다운로드 (여러 시트 포함)

    **권한**: 로그인 필수 (자신의 진단만 다운로드 가능)
    """
    # 진단 결과 조회
    diagnosis = get_diagnosis_by_id(db, diagnosis_id)

    if not diagnosis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnosis {diagnosis_id} not found"
        )

    # 권한 확인
    if diagnosis.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to export this diagnosis"
        )

    # 응답 데이터 빌드
    response_data = build_diagnosis_response(
        diagnosis_id=diagnosis.id,
        investment_type=diagnosis.investment_type,
        score=diagnosis.score,
        confidence=diagnosis.confidence,
        monthly_investment=diagnosis.monthly_investment,
        created_at=diagnosis.created_at
    )

    # Excel 생성
    excel_content = generate_diagnosis_excel(response_data)

    # 파일명 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"diagnosis_{diagnosis_id[:8]}_{timestamp}.xlsx"

    return Response(
        content=excel_content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )

@router.get(
    "/history/export/csv",
    summary="진단 이력 CSV 다운로드",
    description="현재 사용자의 모든 진단 이력을 CSV 파일로 다운로드합니다.",
    response_class=Response
)
async def export_history_csv(
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    진단 이력 CSV 다운로드

    - **limit**: 조회할 최대 개수 (기본값: 100)

    Returns: CSV 파일 다운로드

    **권한**: 로그인 필수
    """
    from app.utils.export import generate_csv

    # 진단 이력 조회
    diagnoses = get_user_diagnoses(db, current_user.id, limit)

    # 빈 리스트도 None으로 평가되지 않으므로 길이 체크
    if not diagnoses or len(diagnoses) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No diagnosis history found"
        )

    # 데이터 변환
    data = [
        {
            "진단 ID": d.id,
            "투자 성향": d.investment_type,
            "점수": d.score,
            "신뢰도": f"{d.confidence * 100:.1f}%",
            "월 투자액": f"{d.monthly_investment:,}만원" if d.monthly_investment else "미입력",
            "진단일시": d.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        for d in diagnoses
    ]

    # CSV 생성
    csv_content = generate_csv(data)

    # 파일명 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"diagnosis_history_{timestamp}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "text/csv; charset=utf-8"
        }
    )