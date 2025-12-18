from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base


class User(Base):
    """사용자 모델"""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password  = Column(String(255), nullable=False)
    name = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계
    diagnoses = relationship("Diagnosis", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"


class Diagnosis(Base):
    """진단 결과 모델"""
    __tablename__ = "diagnoses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    investment_type = Column(String(20), nullable=False)  # 'conservative', 'moderate', 'aggressive'
    score = Column(Float, nullable=False)  # 0-10
    confidence = Column(Float, nullable=False)  # 0-1
    monthly_investment = Column(Integer, nullable=True)  # 월 투자액 (만원)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계
    user = relationship("User", back_populates="diagnoses")
    answers = relationship("DiagnosisAnswer", back_populates="diagnosis", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Diagnosis {self.investment_type} ({self.score})>"


class DiagnosisAnswer(Base):
    """진단 답변 모델"""
    __tablename__ = "diagnosis_answers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    diagnosis_id = Column(String, ForeignKey("diagnoses.id"), nullable=False, index=True)
    question_id = Column(Integer, nullable=False)
    answer_value = Column(Integer, nullable=False)  # 1-5
    created_at = Column(DateTime, default=datetime.utcnow)

    # 관계
    diagnosis = relationship("Diagnosis", back_populates="answers")

    def __repr__(self):
        return f"<DiagnosisAnswer Q{self.question_id}={self.answer_value}>"


class SurveyQuestion(Base):
    """설문 문항 모델"""
    __tablename__ = "survey_questions"

    id = Column(Integer, primary_key=True)
    category = Column(String(50), nullable=False, index=True)
    question = Column(String(255), nullable=False)
    option_a = Column(String(100), nullable=False)
    option_b = Column(String(100), nullable=False)
    option_c = Column(String(100), nullable=True)
    weight_a = Column(Float, nullable=False)
    weight_b = Column(Float, nullable=False)
    weight_c = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<SurveyQuestion {self.id}: {self.question[:30]}...>"