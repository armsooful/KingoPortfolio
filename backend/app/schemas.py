from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional


# ============================================================
# Auth Schemas
# ============================================================

class UserCreate(BaseModel):
    """사용자 생성 요청"""
    email: EmailStr
    password: str
    name: Optional[str] = None


class UserLogin(BaseModel):
    """로그인 요청"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """사용자 응답"""
    id: str
    email: str
    name: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True


class Token(BaseModel):
    """토큰 응답"""
    access_token: str
    token_type: str
    user: UserResponse


class TokenData(BaseModel):
    """토큰 데이터"""
    email: str


# ============================================================
# Survey Schemas
# ============================================================

class SurveyQuestionOption(BaseModel):
    """설문 선택지"""
    value: str  # 'A', 'B', 'C'
    text: str
    weight: float


class SurveyQuestionResponse(BaseModel):
    """설문 문항 응답"""
    id: int
    category: str
    question: str
    options: List[SurveyQuestionOption]

    class Config:
        orm_mode = True


class SurveyQuestionsListResponse(BaseModel):
    """설문 목록 응답"""
    total: int
    questions: List[SurveyQuestionResponse]


# ============================================================
# Diagnosis Schemas
# ============================================================

class DiagnosisAnswerRequest(BaseModel):
    """진단 답변 요청"""
    question_id: int
    answer_value: int  # 1-5


class DiagnosisSubmitRequest(BaseModel):
    """설문 제출 및 진단 요청"""
    answers: List[DiagnosisAnswerRequest]
    monthly_investment: Optional[int] = None  # 월 투자액 (만원)


class DiagnosisCharacteristics(BaseModel):
    """투자성향 특징"""
    title: str
    description: str
    characteristics: List[str]
    recommended_ratio: dict
    expected_annual_return: str


class DiagnosisResponse(BaseModel):
    """진단 결과 응답"""
    diagnosis_id: str
    investment_type: str  # 'conservative', 'moderate', 'aggressive'
    score: float  # 0-10
    confidence: float  # 0-1
    monthly_investment: Optional[int] = None
    description: str
    characteristics: List[str]
    recommended_ratio: dict
    expected_annual_return: str
    created_at: datetime
    # AI 분석 필드 (선택)
    ai_analysis: Optional[dict] = None

    class Config:
        orm_mode = True


class DiagnosisSummaryResponse(BaseModel):
    """진단 요약 응답"""
    diagnosis_id: str
    investment_type: str
    score: float
    confidence: float
    monthly_investment: Optional[int] = None
    created_at: datetime

    class Config:
        orm_mode = True


class DiagnosisHistoryResponse(BaseModel):
    """진단 이력 응답"""
    total: int
    diagnoses: List[DiagnosisSummaryResponse]


class DiagnosisMeResponse(BaseModel):
    """현재 사용자의 최근 진단 결과"""
    diagnosis_id: str
    investment_type: str
    score: float
    confidence: float
    monthly_investment: Optional[int] = None
    description: str
    characteristics: List[str]
    recommended_ratio: dict
    expected_annual_return: str
    created_at: datetime
    # AI 분석 필드 (선택)
    ai_analysis: Optional[dict] = None

    class Config:
        orm_mode = True


# ============================================================
# Error Response Schemas
# ============================================================

class ErrorResponse(BaseModel):
    """에러 응답"""
    detail: str
    status_code: int = 400