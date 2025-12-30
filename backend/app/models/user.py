# app/models/user.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base

class User(Base):
    """사용자 모델"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    # 기본 정보
    name = Column(String(50), nullable=True)  # 사용자 이름
    phone = Column(String(20), nullable=True)  # 전화번호
    birth_date = Column(Date, nullable=True)  # 생년월일

    # 직업 및 재무 정보
    occupation = Column(String(100), nullable=True)  # 직업
    company = Column(String(100), nullable=True)  # 회사명
    annual_income = Column(Integer, nullable=True)  # 연봉 (만원 단위)
    total_assets = Column(Integer, nullable=True)  # 총 자산 (만원 단위)

    # 주소 정보
    city = Column(String(50), nullable=True)  # 거주 도시
    district = Column(String(50), nullable=True)  # 구/군

    # 투자 성향 정보
    investment_experience = Column(String(20), nullable=True)  # '초보', '중급', '고급', '전문가'
    investment_goal = Column(String(100), nullable=True)  # 투자 목표
    risk_tolerance = Column(String(20), nullable=True)  # '보수적', '중립적', '공격적'

    # 시스템 필드
    is_admin = Column(Boolean, default=False)  # 하위 호환성 유지
    role = Column(String(20), default='user')  # 'user', 'premium', 'admin'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계
    diagnoses = relationship("Diagnosis", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(email='{self.email}', name='{self.name}')>"
