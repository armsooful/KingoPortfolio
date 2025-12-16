from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import Depends, HTTPException, status

from app.database import get_db
from app.models import User, SurveyQuestion
from app.schemas import UserCreate
from app.auth import hash_password, verify_password, verify_token


# ============ USER CRUD ============

def get_user_by_email(db: Session, email: str):
    """이메일로 사용자 조회"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int):
    """ID로 사용자 조회"""
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, user_create: UserCreate):
    """새 사용자 생성"""
    existing_user = get_user_by_email(db, user_create.email)
    if existing_user:
        raise ValueError("Email already registered")
    
    hashed_password = hash_password(user_create.password)
    
    db_user = User(
        email=user_create.email,
        hashed_password=hashed_password,
        full_name=user_create.full_name if hasattr(user_create, 'full_name') else None,
    )
    
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        db.rollback()
        raise ValueError("Email already registered")
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to create user: {str(e)}")


def authenticate_user(db: Session, email: str, password: str):
    """사용자 인증 (로그인)"""
    user = get_user_by_email(db, email)
    
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    return user


def update_user(db: Session, user_id: int, **kwargs):
    """사용자 정보 업데이트"""
    user = get_user_by_id(db, user_id)
    
    if not user:
        raise ValueError("User not found")
    
    for key, value in kwargs.items():
        if hasattr(user, key) and key != "id" and key != "hashed_password":
            setattr(user, key, value)
    
    try:
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to update user: {str(e)}")


def delete_user(db: Session, user_id: int):
    """사용자 삭제"""
    user = get_user_by_id(db, user_id)
    
    if not user:
        raise ValueError("User not found")
    
    try:
        db.delete(user)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to delete user: {str(e)}")


# ============ AUTHENTICATION ============

async def get_current_user(
    token: str = Depends(lambda: None),
    db: Session = Depends(get_db)
):
    """JWT 토큰으로 현재 사용자 조회"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token",
        )
    
    try:
        email = verify_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    
    user = get_user_by_email(db, email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    return user


# ============ SURVEY QUESTION CRUD ============

def get_survey_questions(db: Session):
    """모든 설문 질문 조회"""
    return db.query(SurveyQuestion).all()


def get_all_survey_questions(db: Session):
    """모든 설문 질문 조회 (별칭)"""
    return get_survey_questions(db)


def get_survey_question_by_id(db: Session, question_id: int):
    """ID로 설문 질문 조회"""
    return db.query(SurveyQuestion).filter(SurveyQuestion.id == question_id).first()


def get_survey_questions_by_category(db: Session, category: str):
    """카테고리별 설문 질문 조회"""
    return db.query(SurveyQuestion).filter(SurveyQuestion.category == category).all()


def create_survey_question(db: Session, **kwargs):
    """새 설문 질문 생성"""
    question = SurveyQuestion(**kwargs)
    
    try:
        db.add(question)
        db.commit()
        db.refresh(question)
        return question
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to create question: {str(e)}")


def update_survey_question(db: Session, question_id: int, **kwargs):
    """설문 질문 업데이트"""
    question = get_survey_question_by_id(db, question_id)
    
    if not question:
        raise ValueError("Question not found")
    
    for key, value in kwargs.items():
        if hasattr(question, key):
            setattr(question, key, value)
    
    try:
        db.commit()
        db.refresh(question)
        return question
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to update question: {str(e)}")


def delete_survey_question(db: Session, question_id: int):
    """설문 질문 삭제"""
    question = get_survey_question_by_id(db, question_id)
    
    if not question:
        raise ValueError("Question not found")
    
    try:
        db.delete(question)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to delete question: {str(e)}")


# ============ HELPER FUNCTIONS ============

def count_users(db: Session):
    """총 사용자 수"""
    return db.query(User).count()


def count_survey_questions(db: Session):
    """총 설문 질문 수"""
    return db.query(SurveyQuestion).count()