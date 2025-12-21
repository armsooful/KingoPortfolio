from fastapi import APIRouter, Depends, HTTPException, status
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
async def submit_survey(
    request: DiagnosisSubmitRequest,
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
    if not request.answers or len(request.answers) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one answer is required"
        )
    
    # 답변 값 검증 (1-5 범위)
    for answer in request.answers:
        if answer.answer_value < 1 or answer.answer_value > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Answer value must be between 1 and 5, got {answer.answer_value}"
            )
    
    # 월 투자액 검증
    if request.monthly_investment and request.monthly_investment < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Monthly investment must be greater than 0"
        )
    
    try:
        # 진단 계산
        investment_type, score, confidence = calculate_diagnosis(request.answers)

        # DB에 저장
        diagnosis = create_diagnosis(
            db=db,
            user_id=current_user.id,
            investment_type=investment_type,
            score=score,
            confidence=confidence,
            answers=request.answers,
            monthly_investment=request.monthly_investment
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
                answers=request.answers,
                investment_type=investment_type,
                score=score,
                confidence=confidence,
                monthly_investment=request.monthly_investment
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