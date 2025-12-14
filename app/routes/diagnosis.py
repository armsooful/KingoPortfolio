from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    DiagnosisSubmitRequest,
    DiagnosisResponse,
    DiagnosisMeResponse,
    DiagnosisHistoryResponse,
    DiagnosisSummaryResponse,
)
from app.auth import get_current_user
from app.crud import (
    create_diagnosis,
    get_diagnosis_by_id,
    get_user_diagnoses,
    get_user_latest_diagnosis,
)
from app.diagnosis import calculate_diagnosis, build_diagnosis_response

router = APIRouter(prefix="/api/diagnosis", tags=["Diagnosis"])


@router.post("/submit", response_model=DiagnosisResponse)
async def submit_diagnosis(
    diagnosis_request: DiagnosisSubmitRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    설문 제출 및 투자성향 진단
    
    Args:
        diagnosis_request: 진단 요청 (설문 답변 및 월 투자액)
        current_user: 현재 로그인한 사용자
        db: 데이터베이스 세션
    
    Returns:
        DiagnosisResponse: 진단 결과
    """
    
    # 답변 검증
    if not diagnosis_request.answers or len(diagnosis_request.answers) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one answer is required"
        )
    
    # 답변 유효성 검사
    for answer in diagnosis_request.answers:
        if answer.answer_value < 1 or answer.answer_value > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Answer value must be between 1 and 5"
            )
    
    try:
        # 진단 계산
        investment_type, score, confidence = calculate_diagnosis(diagnosis_request.answers)
        
        # 데이터베이스에 저장
        db_diagnosis = create_diagnosis(
            db=db,
            user_id=current_user.id,
            investment_type=investment_type,
            score=score,
            confidence=confidence,
            answers=diagnosis_request.answers,
            monthly_investment=diagnosis_request.monthly_investment,
        )
        
        # 응답 빌더
        response = build_diagnosis_response(
            diagnosis_id=db_diagnosis.id,
            investment_type=investment_type,
            score=score,
            confidence=confidence,
            monthly_investment=diagnosis_request.monthly_investment,
            created_at=db_diagnosis.created_at,
        )
        
        return response
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during diagnosis"
        )


@router.get("/me", response_model=DiagnosisMeResponse)
async def get_my_latest_diagnosis(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    현재 사용자의 최근 진단 결과 조회
    
    Args:
        current_user: 현재 로그인한 사용자
        db: 데이터베이스 세션
    
    Returns:
        DiagnosisMeResponse: 최근 진단 결과
    """
    
    diagnosis = get_user_latest_diagnosis(db, current_user.id)
    
    if not diagnosis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No diagnosis found for this user"
        )
    
    response = build_diagnosis_response(
        diagnosis_id=diagnosis.id,
        investment_type=diagnosis.investment_type,
        score=diagnosis.score,
        confidence=diagnosis.confidence,
        monthly_investment=diagnosis.monthly_investment,
        created_at=diagnosis.created_at,
    )
    
    return response


@router.get("/{diagnosis_id}", response_model=DiagnosisResponse)
async def get_diagnosis(
    diagnosis_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    특정 진단 결과 조회
    
    Args:
        diagnosis_id: 진단 ID
        current_user: 현재 로그인한 사용자
        db: 데이터베이스 세션
    
    Returns:
        DiagnosisResponse: 진단 결과
    """
    
    diagnosis = get_diagnosis_by_id(db, diagnosis_id)
    
    if not diagnosis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnosis with id {diagnosis_id} not found"
        )
    
    # 권한 확인 (본인의 진단만 조회 가능)
    if diagnosis.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this diagnosis"
        )
    
    response = build_diagnosis_response(
        diagnosis_id=diagnosis.id,
        investment_type=diagnosis.investment_type,
        score=diagnosis.score,
        confidence=diagnosis.confidence,
        monthly_investment=diagnosis.monthly_investment,
        created_at=diagnosis.created_at,
    )
    
    return response


@router.get("/history/all", response_model=DiagnosisHistoryResponse)
async def get_diagnosis_history(
    limit: int = 10,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    현재 사용자의 진단 이력 조회
    
    Args:
        limit: 조회 최대 개수 (기본값: 10)
        current_user: 현재 로그인한 사용자
        db: 데이터베이스 세션
    
    Returns:
        DiagnosisHistoryResponse: 진단 이력
    """
    
    diagnoses = get_user_diagnoses(db, current_user.id, limit=limit)
    
    if not diagnoses:
        return {
            "total": 0,
            "diagnoses": []
        }
    
    summary_list = [
        DiagnosisSummaryResponse(
            diagnosis_id=d.id,
            investment_type=d.investment_type,
            score=d.score,
            confidence=d.confidence,
            monthly_investment=d.monthly_investment,
            created_at=d.created_at,
        )
        for d in diagnoses
    ]
    
    return {
        "total": len(summary_list),
        "diagnoses": summary_list
    }