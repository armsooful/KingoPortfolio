# app/models/user.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date
from sqlalchemy.orm import relationship
import uuid
from app.database import Base
from app.utils.kst_now import kst_now

class User(Base):
    """사용자 모델"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    # 기본 정보
    name = Column(String(50), nullable=True)  # 사용자 이름
    phone = Column(String(20), nullable=True)  # 전화번호
    birth_date = Column(Date, nullable=True)  # 생년월일 (레거시, 신규 사용자는 age_group 사용)
    age_group = Column(String(10), nullable=True)  # 연령대 (10s, 20s, 30s, 40s, 50s, 60s_plus)

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

    # 이메일 인증 필드
    is_email_verified = Column(Boolean, default=False)  # 이메일 인증 여부
    email_verification_token = Column(String(100), nullable=True)  # 이메일 인증 토큰
    email_verification_sent_at = Column(DateTime, nullable=True)  # 인증 이메일 발송 시간

    # 복합 등급 체계
    # 1. VIP 등급 (활동 기반, 자동 계산)
    vip_tier = Column(String(20), default='bronze')  # 'bronze', 'silver', 'gold', 'platinum', 'diamond'
    activity_points = Column(Integer, default=0)  # 활동 점수 (포트폴리오 생성, 진단 등으로 획득)

    # 2. 멤버십 플랜 (유료 구독)
    membership_plan = Column(String(20), default='free')  # 'free', 'starter', 'pro', 'enterprise'
    membership_start_date = Column(DateTime, nullable=True)  # 멤버십 시작일
    membership_end_date = Column(DateTime, nullable=True)  # 멤버십 만료일

    # 사용량 추적 (월별 리셋)
    monthly_ai_requests = Column(Integer, default=0)  # 이번 달 AI 요청 횟수
    monthly_reports_generated = Column(Integer, default=0)  # 이번 달 리포트 생성 횟수
    last_usage_reset = Column(DateTime, default=kst_now)  # 마지막 사용량 리셋 시간

    created_at = Column(DateTime, default=kst_now)
    updated_at = Column(DateTime, default=kst_now, onupdate=kst_now)

    # 관계
    diagnoses = relationship("Diagnosis", back_populates="user", cascade="all, delete-orphan")
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(email='{self.email}', name='{self.name}')>"