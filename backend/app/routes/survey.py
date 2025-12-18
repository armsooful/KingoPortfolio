from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, SurveyQuestion
from app.schemas import SurveyQuestionResponse, SurveyQuestionOption, SurveyQuestionsListResponse
from app.auth import get_current_user
from app.crud import get_survey_questions, get_survey_question_by_id

router = APIRouter(
    prefix="/survey",
    tags=["Survey"]
)


def format_survey_question(question: SurveyQuestion) -> SurveyQuestionResponse:
    """설문 문항을 응답 형식으로 변환"""
    
    options = [
        SurveyQuestionOption(
            value="A",
            text=question.option_a,
            weight=question.weight_a
        ),
        SurveyQuestionOption(
            value="B",
            text=question.option_b,
            weight=question.weight_b
        )
    ]
    
    # option_c가 있으면 추가
    if question.option_c and question.weight_c:
        options.append(
            SurveyQuestionOption(
                value="C",
                text=question.option_c,
                weight=question.weight_c
            )
        )
    
    return SurveyQuestionResponse(
        id=question.id,
        category=question.category,
        question=question.question,
        options=options
    )


@router.get(
    "/questions",
    response_model=SurveyQuestionsListResponse,
    summary="설문 문항 조회",
    description="투자성향 진단을 위한 모든 설문 문항을 조회합니다."
)
async def get_questions(db: Session = Depends(get_db)):
    """
    설문 문항 조회
    
    모든 설문 문항과 선택지를 반환합니다.
    """
    
    questions = get_survey_questions(db)
    
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Survey questions not found"
        )
    
    formatted_questions = [format_survey_question(q) for q in questions]
    
    return SurveyQuestionsListResponse(
        total=len(formatted_questions),
        questions=formatted_questions
    )


@router.get(
    "/questions/{question_id}",
    response_model=SurveyQuestionResponse,
    summary="특정 설문 문항 조회"
)
async def get_question(
    question_id: int,
    db: Session = Depends(get_db)
):
    """
    특정 설문 문항 조회
    
    - **question_id**: 문항 ID
    """
    
    question = get_survey_question_by_id(db, question_id)
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question {question_id} not found"
        )
    
    return format_survey_question(question)