from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, date
from typing import List, Optional, Dict, Literal


# ============================================================
# Auth Schemas
# ============================================================

class UserCreate(BaseModel):
    """사용자 생성 요청"""
    email: EmailStr = Field(..., description="사용자 이메일 주소 (고유값)", example="user@example.com")
    password: str = Field(..., min_length=8, max_length=72, description="비밀번호 (최소 8자, 최대 72바이트)", example="securePassword123!")

    # 기본 정보
    name: Optional[str] = Field(None, max_length=50, description="사용자 이름", example="홍길동")
    phone: Optional[str] = Field(None, max_length=20, description="전화번호", example="010-1234-5678")
    birth_date: Optional[date] = Field(None, description="생년월일", example="1990-01-01")

    # 직업 및 재무 정보
    occupation: Optional[str] = Field(None, max_length=100, description="직업", example="소프트웨어 엔지니어")
    company: Optional[str] = Field(None, max_length=100, description="회사명", example="테크컴퍼니")
    annual_income: Optional[int] = Field(None, ge=0, description="연봉 (만원 단위)", example=5000)
    total_assets: Optional[int] = Field(None, ge=0, description="총 자산 (만원 단위)", example=10000)

    # 주소 정보
    city: Optional[str] = Field(None, max_length=50, description="거주 도시", example="서울")
    district: Optional[str] = Field(None, max_length=50, description="구/군", example="강남구")

    # 투자 성향 정보
    investment_experience: Optional[str] = Field(None, description="투자 경험", example="중급")
    investment_goal: Optional[str] = Field(None, max_length=100, description="투자 목표", example="노후 준비")
    risk_tolerance: Optional[str] = Field(None, description="위험 감수 성향", example="중립적")

    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securePassword123!",
                "name": "홍길동",
                "phone": "010-1234-5678",
                "birth_date": "1990-01-01",
                "occupation": "소프트웨어 엔지니어",
                "company": "테크컴퍼니",
                "annual_income": 5000,
                "total_assets": 10000,
                "city": "서울",
                "district": "강남구",
                "investment_experience": "중급",
                "investment_goal": "노후 준비",
                "risk_tolerance": "중립적"
            }
        }


class UserLogin(BaseModel):
    """로그인 요청"""
    email: EmailStr = Field(
        ...,
        description="등록된 이메일 주소",
        example="user@example.com"
    )
    password: str = Field(
        ...,
        description="비밀번호",
        example="securePassword123!"
    )

    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securePassword123!"
            }
        }


class UserResponse(BaseModel):
    """사용자 응답"""
    id: str = Field(..., description="사용자 고유 ID", example="usr_abc123xyz")
    email: str = Field(..., description="이메일 주소", example="user@example.com")
    name: Optional[str] = Field(None, description="사용자 이름", example="홍길동")
    role: str = Field(..., description="사용자 역할", example="user")
    created_at: datetime = Field(..., description="계정 생성 일시", example="2025-12-29T10:00:00Z")

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "usr_abc123xyz",
                "email": "user@example.com",
                "name": "홍길동",
                "role": "user",
                "created_at": "2025-12-29T10:00:00Z"
            }
        }


class Token(BaseModel):
    """토큰 응답"""
    access_token: str = Field(
        ...,
        description="JWT 액세스 토큰",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyQGV4YW1wbGUuY29tIiwiZXhwIjoxNzM1NDcwMDAwfQ.example"
    )
    token_type: str = Field(
        ...,
        description="토큰 타입 (항상 'bearer')",
        example="bearer"
    )
    user: UserResponse = Field(..., description="사용자 정보")

    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "id": "usr_abc123xyz",
                    "email": "user@example.com",
                    "name": "홍길동",
                    "created_at": "2025-12-29T10:00:00Z"
                }
            }
        }


class TokenData(BaseModel):
    """토큰 데이터 (내부 사용)"""
    email: str = Field(..., description="토큰에 포함된 사용자 이메일")


class ForgotPasswordRequest(BaseModel):
    """비밀번호 재설정 요청"""
    email: EmailStr = Field(
        ...,
        description="등록된 이메일 주소",
        example="user@example.com"
    )

    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }


class ResetPasswordRequest(BaseModel):
    """비밀번호 재설정"""
    token: str = Field(
        ...,
        description="재설정 토큰 (이메일로 전송됨)",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="새 비밀번호 (최소 8자, 최대 72바이트)",
        example="newSecurePassword123!"
    )

    class Config:
        schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "new_password": "newSecurePassword123!"
            }
        }


class MessageResponse(BaseModel):
    """일반 메시지 응답"""
    message: str = Field(
        ...,
        description="응답 메시지",
        example="비밀번호 재설정 링크가 이메일로 전송되었습니다"
    )

    class Config:
        schema_extra = {
            "example": {
                "message": "작업이 성공적으로 완료되었습니다"
            }
        }


class UpdateProfileRequest(BaseModel):
    """프로필 수정 요청 (확장)"""
    name: Optional[str] = Field(
        None,
        max_length=50,
        description="사용자 이름 (선택사항)",
        example="홍길동"
    )
    email: Optional[str] = Field(
        None,
        max_length=255,
        description="이메일 주소 (선택사항)",
        example="newemail@example.com"
    )
    phone: Optional[str] = Field(None, max_length=20, description="전화번호")
    birth_date: Optional[date] = Field(None, description="생년월일")
    occupation: Optional[str] = Field(None, max_length=100, description="직업")
    company: Optional[str] = Field(None, max_length=100, description="회사명")
    annual_income: Optional[int] = Field(None, description="연봉 (만원 단위)")
    total_assets: Optional[int] = Field(None, description="총 자산 (만원 단위)")
    city: Optional[str] = Field(None, max_length=50, description="거주 도시")
    district: Optional[str] = Field(None, max_length=50, description="구/군")
    investment_experience: Optional[str] = Field(None, max_length=20, description="투자 경험")
    investment_goal: Optional[str] = Field(None, max_length=100, description="투자 목표")
    risk_tolerance: Optional[str] = Field(None, max_length=20, description="위험 감수 성향")

    class Config:
        schema_extra = {
            "example": {
                "name": "김철수",
                "phone": "010-1234-5678",
                "occupation": "소프트웨어 엔지니어"
            }
        }


class ChangePasswordRequest(BaseModel):
    """비밀번호 변경 요청"""
    current_password: str = Field(
        ...,
        description="현재 비밀번호",
        example="currentPassword123!"
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="새 비밀번호 (최소 8자, 최대 72바이트)",
        example="newPassword456!"
    )

    class Config:
        schema_extra = {
            "example": {
                "current_password": "currentPassword123!",
                "new_password": "newPassword456!"
            }
        }


class ProfileResponse(BaseModel):
    """프로필 응답 (확장된 사용자 정보)"""
    id: str = Field(..., description="사용자 고유 ID", example="usr_abc123xyz")
    email: str = Field(..., description="이메일 주소", example="user@example.com")
    name: Optional[str] = Field(None, description="사용자 이름", example="홍길동")
    phone: Optional[str] = Field(None, description="전화번호")
    birth_date: Optional[date] = Field(None, description="생년월일")
    occupation: Optional[str] = Field(None, description="직업")
    company: Optional[str] = Field(None, description="회사명")
    annual_income: Optional[int] = Field(None, description="연봉 (만원 단위)")
    total_assets: Optional[int] = Field(None, description="총 자산 (만원 단위)")
    city: Optional[str] = Field(None, description="거주 도시")
    district: Optional[str] = Field(None, description="구/군")
    investment_experience: Optional[str] = Field(None, description="투자 경험")
    investment_goal: Optional[str] = Field(None, description="투자 목표")
    risk_tolerance: Optional[str] = Field(None, description="위험 감수 성향")
    role: str = Field(..., description="사용자 역할 (user/premium/admin)", example="user")
    is_email_verified: bool = Field(default=False, description="이메일 인증 여부", example=False)

    # 복합 등급 체계
    vip_tier: str = Field(default="bronze", description="VIP 등급 (bronze/silver/gold/platinum/diamond)", example="bronze")
    activity_points: int = Field(default=0, description="활동 점수", example=0)
    membership_plan: str = Field(default="free", description="멤버십 플랜 (free/starter/pro/enterprise)", example="free")

    created_at: datetime = Field(..., description="계정 생성 일시", example="2025-12-29T10:00:00Z")

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "usr_abc123xyz",
                "email": "user@example.com",
                "name": "홍길동",
                "role": "user",
                "created_at": "2025-12-29T10:00:00Z"
            }
        }


# ============================================================
# Portfolio Schemas
# ============================================================

class PortfolioGenerateRequest(BaseModel):
    """포트폴리오 생성 요청"""
    investment_amount: int = Field(..., ge=10000, description="투자 금액 (최소 1만원)")
    risk_tolerance: Optional[str] = Field(None, description="리스크 허용도 (low, medium, high)")
    sector_preferences: Optional[List[str]] = Field(None, description="선호 섹터")
    dividend_preference: Optional[bool] = Field(False, description="배당 선호 여부")

    class Config:
        json_schema_extra = {
            "example": {
                "investment_amount": 10000000,
                "risk_tolerance": "medium",
                "sector_preferences": ["전자", "금융"],
                "dividend_preference": True
            }
        }


class PortfolioAssetItem(BaseModel):
    """포트폴리오 자산 항목"""
    id: int
    name: str
    invested_amount: int
    weight: float
    expected_return: Optional[float]
    risk_level: Optional[str]
    rationale: str


class PortfolioStockItem(PortfolioAssetItem):
    """포트폴리오 주식 항목"""
    ticker: str
    sector: Optional[str]
    current_price: float
    shares: int
    dividend_yield: Optional[float]
    pe_ratio: Optional[float]
    pb_ratio: Optional[float]
    score: float


class PortfolioETFItem(PortfolioAssetItem):
    """포트폴리오 ETF 항목"""
    ticker: str
    etf_type: str
    current_price: float
    shares: int
    expense_ratio: Optional[float]
    aum: Optional[float]
    score: float


class PortfolioBondItem(PortfolioAssetItem):
    """포트폴리오 채권 항목"""
    bond_type: str
    issuer: Optional[str]
    interest_rate: float
    maturity_years: int
    credit_rating: str


class PortfolioDepositItem(PortfolioAssetItem):
    """포트폴리오 예금 항목"""
    bank: str
    product_type: str
    interest_rate: float
    term_months: int


class AllocationDetail(BaseModel):
    """자산 배분 상세"""
    ratio: float
    amount: int
    min_ratio: float
    max_ratio: float


class PortfolioAllocation(BaseModel):
    """포트폴리오 자산 배분"""
    stocks: AllocationDetail
    etfs: AllocationDetail
    bonds: AllocationDetail
    deposits: AllocationDetail


class PortfolioStatistics(BaseModel):
    """포트폴리오 통계"""
    total_investment: int
    actual_invested: int
    cash_reserve: int
    expected_annual_return: float
    portfolio_risk: str
    diversification_score: int
    total_items: int
    asset_breakdown: Dict[str, int]


class PortfolioResponse(BaseModel):
    """포트폴리오 시뮬레이션 응답"""
    investment_type: str
    total_investment: int
    allocation: PortfolioAllocation
    portfolio: Dict[str, List[Dict]]
    statistics: PortfolioStatistics
    simulation_notes: List[str]

    class Config:
        json_schema_extra = {
            "example": {
                "investment_type": "moderate",
                "total_investment": 10000000,
                "allocation": {
                    "stocks": {"ratio": 40, "amount": 4000000, "min_ratio": 30, "max_ratio": 50},
                    "etfs": {"ratio": 20, "amount": 2000000, "min_ratio": 15, "max_ratio": 25},
                    "bonds": {"ratio": 25, "amount": 2500000, "min_ratio": 20, "max_ratio": 30},
                    "deposits": {"ratio": 15, "amount": 1500000, "min_ratio": 10, "max_ratio": 20}
                },
                "portfolio": {
                    "stocks": [],
                    "etfs": [],
                    "bonds": [],
                    "deposits": []
                },
                "statistics": {
                    "total_investment": 10000000,
                    "actual_invested": 9800000,
                    "cash_reserve": 200000,
                    "expected_annual_return": 7.5,
                    "portfolio_risk": "medium",
                    "diversification_score": 80,
                    "total_items": 8,
                    "asset_breakdown": {"stocks_count": 3, "etfs_count": 2, "bonds_count": 2, "deposits_count": 1}
                },
                "simulation_notes": ["시나리오 기반 포트폴리오 구성 예시입니다."]
            }
        }


# ============================================================
# Phase 7 Schemas
# ============================================================

class Phase7PortfolioItemInput(BaseModel):
    """Phase 7 포트폴리오 구성 항목"""
    id: str = Field(..., description="종목 또는 섹터 ID")
    name: str = Field(..., description="종목 또는 섹터 이름")
    weight: float = Field(..., ge=0, le=1, description="비중 (0~1)")


class Phase7PortfolioCreateRequest(BaseModel):
    """Phase 7 포트폴리오 생성 요청"""
    portfolio_type: Literal["SECURITY", "SECTOR"] = Field(..., description="SECURITY | SECTOR")
    portfolio_name: str = Field(..., max_length=100, description="포트폴리오 이름")
    description: Optional[str] = Field(None, description="메모")
    items: List[Phase7PortfolioItemInput] = Field(..., min_items=1)


class Phase7PortfolioResponse(BaseModel):
    """Phase 7 포트폴리오 응답"""
    portfolio_id: int
    portfolio_type: str
    portfolio_name: str
    description: Optional[str]
    items: List[Phase7PortfolioItemInput]
    created_at: Optional[str]
    updated_at: Optional[str]


class Phase7PortfolioListResponse(BaseModel):
    """Phase 7 포트폴리오 목록"""
    count: int
    portfolios: List[Phase7PortfolioResponse]


class Phase7Period(BaseModel):
    """Phase 7 평가 기간"""
    start: date
    end: date


class Phase8InputExtensions(BaseModel):
    """Phase 8-B 입력 확장"""
    asset_class: Optional[Literal["EQUITY", "BOND", "COMMODITY", "GOLD", "REIT", "ETF"]] = None
    currency: Optional[Literal["KRW", "USD"]] = None
    return_type: Optional[Literal["PRICE", "TOTAL_RETURN"]] = None


class Phase7EvaluationRequest(BaseModel):
    """Phase 7 평가 요청"""
    portfolio_id: int
    period: Phase7Period
    rebalance: Literal["NONE", "MONTHLY", "QUARTERLY"] = Field("NONE")
    extensions: Optional["Phase8InputExtensions"] = None


class Phase7MetricsResponse(BaseModel):
    """Phase 7 평가 지표"""
    cumulative_return: float
    cagr: float
    volatility: float
    max_drawdown: float


class Phase8RollingPoint(BaseModel):
    """Phase 8-A 확장 지표 포인트"""
    end_date: date
    value: float


# ============================================================
# Consent Schemas
# ============================================================


class ConsentCreateRequest(BaseModel):
    """동의 기록 생성 요청"""
    consent_type: str = Field(..., max_length=50, description="동의 유형")
    consent_version: str = Field(..., max_length=20, description="동의 버전")
    consent_text: Optional[str] = Field(None, description="동의 문구 원문")


class ConsentResponse(BaseModel):
    """동의 기록 응답"""
    consent_id: int
    consent_type: str
    consent_version: str
    consent_text: Optional[str]
    agreed_at: datetime


class ConsentHistoryItem(BaseModel):
    """동의 기록 상세"""
    consent_id: int
    consent_type: str
    consent_version: str
    consent_text: Optional[str]
    agreed_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class ConsentListResponse(BaseModel):
    """동의 기록 목록"""
    count: int
    consents: List[ConsentHistoryItem]


class AdminConsentItem(BaseModel):
    """관리자용 동의 기록"""
    consent_id: int
    consent_type: str
    consent_version: str
    consent_text: Optional[str]
    agreed_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    user_id: str
    user_email: Optional[str] = None
    user_name: Optional[str] = None


class AdminConsentListResponse(BaseModel):
    """관리자용 동의 기록 목록"""
    count: int
    consents: List[AdminConsentItem]


class Phase8YearlyReturn(BaseModel):
    """Phase 8-A 연도별 성과"""
    year: int
    value: float


class Phase8Contribution(BaseModel):
    """Phase 8-A 기여도"""
    item_id: str
    item_name: str
    value: float


class Phase8DrawdownSegment(BaseModel):
    """Phase 8-A 드로다운 구간"""
    start: date
    end: date
    drawdown: float


class Phase8Extensions(BaseModel):
    """Phase 8-A 확장 블록"""
    rolling_returns: Optional[Dict[str, List[Phase8RollingPoint]]]
    rolling_volatility: Optional[Dict[str, List[Phase8RollingPoint]]]
    yearly_returns: Optional[List[Phase8YearlyReturn]]
    contributions: Optional[List[Phase8Contribution]]
    drawdown_segments: Optional[List[Phase8DrawdownSegment]]




class Phase7EvaluationResponse(BaseModel):
    """Phase 7 평가 응답"""
    period: Phase7Period
    metrics: Phase7MetricsResponse
    disclaimer_version: str
    extensions: Optional[Phase8Extensions] = None


class Phase7EvaluationHistoryItem(BaseModel):
    """Phase 7 평가 이력 항목"""
    evaluation_id: int
    portfolio_id: int
    period: Phase7Period
    rebalance: str
    result_hash: str
    created_at: Optional[str]


class Phase7EvaluationHistoryResponse(BaseModel):
    """Phase 7 평가 이력 목록"""
    count: int
    evaluations: List[Phase7EvaluationHistoryItem]


class Phase7EvaluationDetailResponse(BaseModel):
    """Phase 7 평가 이력 상세"""
    evaluation_id: int
    portfolio_id: int
    period: Phase7Period
    rebalance: str
    created_at: Optional[str]
    result_hash: str
    result: Phase7EvaluationResponse


class Phase7AvailablePeriodResponse(BaseModel):
    """Phase 7 평가 가능 기간"""
    start: Optional[date]
    end: Optional[date]
    has_overlap: bool
    item_count: int
    ticker_count: int


class Phase7ComparisonRequest(BaseModel):
    """Phase 7 비교 요청"""
    portfolio_ids: List[int] = Field(..., min_items=2)


class Phase7ComparisonItem(BaseModel):
    """Phase 7 비교 항목"""
    portfolio_id: int
    period: Phase7Period
    metrics: Phase7MetricsResponse
    disclaimer_version: str


class Phase7ComparisonResponse(BaseModel):
    """Phase 7 비교 응답"""
    count: int
    portfolios: List[Phase7ComparisonItem]

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


class ReferenceOnlyData(BaseModel):
    """참고용 데이터 (과거 실적 기반, 미래 보장 아님)"""
    historical_avg_return: str
    disclaimer: str


class DiagnosisCharacteristics(BaseModel):
    """투자성향 특징"""
    title: str
    description: str
    characteristics: List[str]
    scenario_ratio: dict
    reference_only: ReferenceOnlyData


class DiagnosisResponse(BaseModel):
    """진단 결과 응답"""
    diagnosis_id: str
    investment_type: str  # 'conservative', 'moderate', 'aggressive'
    score: float  # 0-10
    confidence: float  # 0-1
    monthly_investment: Optional[int] = None
    description: str
    characteristics: List[str]
    scenario_ratio: dict
    reference_only: ReferenceOnlyData
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
    scenario_ratio: dict
    expected_annual_return: str
    created_at: datetime
    # AI 분석 필드 (선택)
    ai_analysis: Optional[dict] = None

    class Config:
        orm_mode = True


# ============================================================
# Error Response Schemas
# ============================================================

class ErrorDetail(BaseModel):
    """에러 상세 정보"""
    code: str = Field(..., description="에러 코드", example="INVALID_TOKEN")
    message: str = Field(..., description="사용자 친화적인 에러 메시지", example="유효하지 않은 토큰입니다")
    status: int = Field(..., description="HTTP 상태 코드", example=401)
    extra: Optional[dict] = Field(None, description="추가 컨텍스트 정보", example={"symbol": "AAPL"})

    class Config:
        schema_extra = {
            "example": {
                "code": "INVALID_TOKEN",
                "message": "유효하지 않은 토큰입니다",
                "status": 401,
                "extra": {}
            }
        }


class ErrorResponse(BaseModel):
    """에러 응답 (전역 에러 핸들러 형식)"""
    error: ErrorDetail = Field(..., description="에러 정보")

    class Config:
        schema_extra = {
            "example": {
                "error": {
                    "code": "INVALID_TOKEN",
                    "message": "유효하지 않은 토큰입니다",
                    "status": 401,
                    "extra": {}
                }
            }
        }


class LegacyErrorResponse(BaseModel):
    """에러 응답 (레거시 형식, 일부 엔드포인트에서 사용)"""
    detail: str = Field(..., description="에러 메시지", example="이메일 또는 비밀번호가 올바르지 않습니다")
    status_code: int = Field(400, description="HTTP 상태 코드", example=400)
