from sqlalchemy.orm import Session
from app.models import User, Diagnosis, DiagnosisAnswer, SurveyQuestion
from app.schemas import UserCreate, DiagnosisSubmitRequest
from app.auth import get_password_hash, verify_password
from typing import Optional, List


# ============================================================
# User CRUD
# ============================================================

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """이메일로 사용자 조회"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """ID로 사용자 조회"""
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, user_create: UserCreate) -> User:
    """사용자 생성"""
    # 기존 사용자 확인
    if get_user_by_email(db, user_create.email):
        raise ValueError("Email already registered")
    
    # 새 사용자 생성
    hashed_password = get_password_hash(user_create.password)
    db_user = User(
        email=user_create.email,
        password_hash=hashed_password,
        name=user_create.name
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """사용자 인증"""
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


# ============================================================
# SurveyQuestion CRUD
# ============================================================

def get_survey_questions(db: Session) -> List[SurveyQuestion]:
    """모든 설문 문항 조회"""
    return db.query(SurveyQuestion).order_by(SurveyQuestion.id).all()


def get_survey_question_by_id(db: Session, question_id: int) -> Optional[SurveyQuestion]:
    """설문 문항 조회"""
    return db.query(SurveyQuestion).filter(SurveyQuestion.id == question_id).first()


def create_survey_question(
    db: Session,
    category: str,
    question: str,
    option_a: str,
    option_b: str,
    weight_a: float,
    weight_b: float,
    option_c: Optional[str] = None,
    weight_c: Optional[float] = None
) -> SurveyQuestion:
    """설문 문항 생성"""
    db_question = SurveyQuestion(
        category=category,
        question=question,
        option_a=option_a,
        option_b=option_b,
        option_c=option_c,
        weight_a=weight_a,
        weight_b=weight_b,
        weight_c=weight_c
    )
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question


# ============================================================
# Diagnosis CRUD
# ============================================================

def create_diagnosis(
    db: Session,
    user_id: str,
    investment_type: str,
    score: float,
    confidence: float,
    answers: List[DiagnosisSubmitRequest],
    monthly_investment: Optional[int] = None
) -> Diagnosis:
    """진단 결과 생성"""
    # 진단 생성
    db_diagnosis = Diagnosis(
        user_id=user_id,
        investment_type=investment_type,
        score=score,
        confidence=confidence,
        monthly_investment=monthly_investment
    )
    db.add(db_diagnosis)
    db.flush()  # ID 생성
    
    # 답변 저장
    for answer in answers:
        db_answer = DiagnosisAnswer(
            diagnosis_id=db_diagnosis.id,
            question_id=answer.question_id,
            answer_value=answer.answer_value
        )
        db.add(db_answer)
    
    db.commit()
    db.refresh(db_diagnosis)
    return db_diagnosis


def get_diagnosis_by_id(db: Session, diagnosis_id: str) -> Optional[Diagnosis]:
    """진단 결과 조회"""
    return db.query(Diagnosis).filter(Diagnosis.id == diagnosis_id).first()


def get_user_diagnoses(db: Session, user_id: str, limit: int = 10) -> List[Diagnosis]:
    """사용자의 진단 이력 조회"""
    return db.query(Diagnosis).filter(
        Diagnosis.user_id == user_id
    ).order_by(Diagnosis.created_at.desc()).limit(limit).all()


def get_user_latest_diagnosis(db: Session, user_id: str) -> Optional[Diagnosis]:
    """사용자의 최근 진단 결과 조회"""
    return db.query(Diagnosis).filter(
        Diagnosis.user_id == user_id
    ).order_by(Diagnosis.created_at.desc()).first()


# ============================================================
# DiagnosisAnswer CRUD
# ============================================================

def get_diagnosis_answers(db: Session, diagnosis_id: str) -> List[DiagnosisAnswer]:
    """진단 답변 조회"""
    return db.query(DiagnosisAnswer).filter(
        DiagnosisAnswer.diagnosis_id == diagnosis_id
    ).all()