from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import Depends, HTTPException, status

from app.database import get_db
from app.models import User
from app.schemas import UserCreate
from app.auth import hash_password, verify_password
import app.models as models

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
    print("\n" + "="*60)
    print("🔐 authenticate_user 호출됨")
    print(f"이메일: {email}")
    print(f"입력 비밀번호: {password}")
    print(f"비밀번호 길이: {len(password)}")
    print(f"비밀번호 바이트: {len(password.encode('utf-8'))}")

    user = get_user_by_email(db, email)

    if not user:
        print("❌ 사용자 없음")
        print("="*60 + "\n")
        return None

    print(f"✅ 사용자 발견: {user.email}")
    print(f"DB 해시: {user.hashed_password[:50]}...")

    verification_result = verify_password(password, user.hashed_password)
    print(f"비밀번호 검증 결과: {verification_result}")
    print("="*60 + "\n")

    if not verification_result:
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

# ============ SURVEY QUESTION CRUD ============

def get_survey_questions(db: Session):
    """모든 설문 질문 조회"""
    return db.query(models.SurveyQuestion).all()

def get_all_survey_questions(db: Session):
    """모든 설문 질문 조회 (별칭)"""
    return get_survey_questions(db)

def get_survey_question_by_id(db: Session, question_id: int):
    """ID로 설문 질문 조회"""
    return db.query(models.SurveyQuestion).filter(models.SurveyQuestion.id == question_id).first()

def get_survey_questions_by_category(db: Session, category: str):
    """카테고리별 설문 질문 조회"""
    return db.query(models.SurveyQuestion).filter(models.SurveyQuestion.category == category).all()

def create_survey_question(db: Session, **kwargs):
    """새 설문 질문 생성"""
    question = models.SurveyQuestion(**kwargs)
    
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
    return db.query(models.SurveyQuestion).count()

# ============ DIAGNOSIS CRUD ============

def create_diagnosis(db: Session, user_id: str, investment_type: str, score: float, confidence: float, monthly_investment: int = None, answers: list = None, **kwargs):
    """새 진단 결과 생성
    
    Args:
        db: 데이터베이스 세션
        user_id: 사용자 ID
        investment_type: 투자성향 타입 ('conservative', 'moderate', 'aggressive')
        score: 진단 점수 (0-10)
        confidence: 신뢰도 (0-1)
        monthly_investment: 월 투자액 (만원)
        answers: 설문 답변 리스트
        **kwargs: 추가 필드
    """
    # ✅ FIX 2: personality_type → investment_type (파라미터명)
    # ✅ FIX 3: confidence 파라미터 추가
    diagnosis = models.Diagnosis(
        user_id=user_id,
        investment_type=investment_type,
        score=score,
        confidence=confidence,
        monthly_investment=monthly_investment,
        **kwargs
    )
    
    try:
        db.add(diagnosis)
        db.commit()
        db.refresh(diagnosis)
        
        # 답변 저장 (선택사항)
        if answers:
            for answer in answers:
                diagnosis_answer = models.DiagnosisAnswer(
                    diagnosis_id=diagnosis.id,
                    question_id=answer.question_id,
                    answer_value=answer.answer_value
                )
                db.add(diagnosis_answer)
            db.commit()
        
        return diagnosis
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to create diagnosis: {str(e)}")

def get_diagnosis_by_id(db: Session, diagnosis_id: str):
    """ID로 진단 결과 조회"""
    return db.query(models.Diagnosis).filter(models.Diagnosis.id == diagnosis_id).first()

def get_diagnoses_by_user(db: Session, user_id: str):
    """사용자의 모든 진단 결과 조회"""
    return db.query(models.Diagnosis).filter(models.Diagnosis.user_id == user_id).order_by(
        models.Diagnosis.created_at.desc()
    ).all()

def get_user_diagnoses(db: Session, user_id: str, limit: int = 10):
    """사용자의 진단 결과 조회 (최대 limit개)
    
    Args:
        db: 데이터베이스 세션
        user_id: 사용자 ID
        limit: 조회할 최대 개수 (기본값: 10)
    """
    # ✅ FIX 4: limit 파라미터 추가
    return db.query(models.Diagnosis).filter(models.Diagnosis.user_id == user_id).order_by(
        models.Diagnosis.created_at.desc()
    ).limit(limit).all()

def get_latest_diagnosis(db: Session, user_id: str):
    """사용자의 최신 진단 결과 조회"""
    return db.query(models.Diagnosis).filter(models.Diagnosis.user_id == user_id).order_by(
        models.Diagnosis.created_at.desc()
    ).first()

def get_user_latest_diagnosis(db: Session, user_id: str):
    """사용자의 최신 진단 결과 조회 (별칭)"""
    return get_latest_diagnosis(db, user_id)

def update_diagnosis(db: Session, diagnosis_id: str, **kwargs):
    """진단 결과 업데이트"""
    diagnosis = get_diagnosis_by_id(db, diagnosis_id)
    
    if not diagnosis:
        raise ValueError("Diagnosis not found")
    
    for key, value in kwargs.items():
        if hasattr(diagnosis, key):
            setattr(diagnosis, key, value)
    
    try:
        db.commit()
        db.refresh(diagnosis)
        return diagnosis
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to update diagnosis: {str(e)}")

def delete_diagnosis(db: Session, diagnosis_id: str):
    """진단 결과 삭제"""
    diagnosis = get_diagnosis_by_id(db, diagnosis_id)

    if not diagnosis:
        raise ValueError("Diagnosis not found")

    try:
        db.delete(diagnosis)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to delete diagnosis: {str(e)}")


# ============ SECURITIES CRUD ============

def get_or_create_stock(db: Session, ticker: str, **kwargs):
    """주식 조회 또는 생성"""
    from app.models.securities import Stock

    # Try to find existing stock
    stock = db.query(Stock).filter(Stock.ticker == ticker).first()

    if stock:
        # Update existing stock with new data
        print(f"[CRUD] Updating stock {ticker}")
        updated_fields = []
        for key, value in kwargs.items():
            if value is not None and hasattr(stock, key):
                old_value = getattr(stock, key)
                setattr(stock, key, value)
                updated_fields.append(f"{key}: {old_value} -> {value}")

        if updated_fields:
            print(f"[CRUD] Updated fields: {', '.join(updated_fields)}")

        db.commit()
        db.refresh(stock)
        print(f"[CRUD] Stock {ticker} updated successfully")
        return stock

    # Create new stock
    print(f"[CRUD] Creating new stock {ticker}")
    stock = Stock(ticker=ticker, **kwargs)
    db.add(stock)
    db.commit()
    db.refresh(stock)
    return stock