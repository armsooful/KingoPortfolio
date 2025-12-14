from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import SurveyQuestionResponse, SurveyQuestionsListResponse, SurveyQuestionOption
from app.crud import get_survey_questions, get_survey_question_by_id

router = APIRouter(prefix="/api/survey", tags=["Survey"])


def format_question(question) -> SurveyQuestionResponse:
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
        ),
    ]
    
    # 옵션 C 추가 (있으면)
    if question.option_c:
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


@router.get("/questions", response_model=SurveyQuestionsListResponse)
async def get_all_questions(db: Session = Depends(get_db)):
    """
    모든 설문 문항 조회
    
    Returns:
        SurveyQuestionsListResponse: 설문 문항 목록
    """
    questions = get_survey_questions(db)
    
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No survey questions found"
        )
    
    formatted_questions = [format_question(q) for q in questions]
    
    return {
        "total": len(formatted_questions),
        "questions": formatted_questions
    }


@router.get("/questions/{question_id}", response_model=SurveyQuestionResponse)
async def get_question(question_id: int, db: Session = Depends(get_db)):
    """
    특정 설문 문항 조회
    
    Args:
        question_id: 설문 문항 ID
        db: 데이터베이스 세션
    
    Returns:
        SurveyQuestionResponse: 설문 문항
    """
    question = get_survey_question_by_id(db, question_id)
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with id {question_id} not found"
        )
    
    return format_question(question)