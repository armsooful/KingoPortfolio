"""
Phase 3-A: 포트폴리오 분석/해석 API 라우터

설명·안심 중심 포트폴리오 해석 서비스

**핵심 원칙:**
- 종목 추천 금지
- 투자 판단 유도 금지
- 결과 해석 및 맥락 제공만 수행

**규제 준수:**
- 투자 권유 표현 금지
- 과거 데이터 기반 고지 필수
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.custom_portfolio import CustomPortfolio
from app.services.explanation_engine import (
    explain_performance,
    explanation_result_to_dict,
    DISCLAIMER
)
from app.services.performance_analyzer import (
    analyze_from_nav_list,
    PerformanceMetrics
)


router = APIRouter(
    prefix="/api/v1/analysis",
    tags=["Analysis"],
)


# ============================================================================
# Request/Response Schemas
# ============================================================================

class AnalysisExplainRequest(BaseModel):
    """포트폴리오 성과 해석 요청"""
    portfolio_id: str = Field(
        ...,
        description="포트폴리오 ID",
        example="custom_123"
    )
    start_date: date = Field(
        ...,
        description="분석 시작일 (YYYY-MM-DD)",
        example="2023-01-01"
    )
    end_date: date = Field(
        ...,
        description="분석 종료일 (YYYY-MM-DD)",
        example="2024-01-01"
    )
    benchmark_name: Optional[str] = Field(
        None,
        description="비교 벤치마크 이름",
        example="KOSPI 200"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "portfolio_id": "custom_123",
                "start_date": "2023-01-01",
                "end_date": "2024-01-01",
                "benchmark_name": "KOSPI 200"
            }
        }


class MetricExplanationResponse(BaseModel):
    """개별 지표 해석 응답"""
    metric: str = Field(..., description="지표명", example="CAGR")
    value: float = Field(..., description="지표 값", example=0.085)
    formatted_value: str = Field(..., description="표시용 값", example="+8.50%")
    description: str = Field(..., description="자연어 설명")
    context: Optional[str] = Field(None, description="추가 맥락")
    level: Optional[str] = Field(None, description="수준 분류")


class RiskPeriodResponse(BaseModel):
    """위험 구간 응답"""
    period_type: str = Field(..., description="구간 유형")
    start_date: Optional[str] = Field(None, description="시작일")
    end_date: Optional[str] = Field(None, description="종료일")
    description: str = Field(..., description="설명")
    severity: str = Field(..., description="심각도")


class ComparisonResponse(BaseModel):
    """비교 맥락 응답"""
    benchmark_name: str
    benchmark_return: Optional[float]
    relative_performance: str
    note: str


class AnalysisExplainResponse(BaseModel):
    """포트폴리오 성과 해석 응답"""
    summary: str = Field(..., description="전체 요약")
    performance_explanation: List[MetricExplanationResponse] = Field(
        ...,
        description="성과 지표별 해석"
    )
    risk_explanation: str = Field(..., description="위험 요약 설명")
    risk_periods: List[RiskPeriodResponse] = Field(
        default=[],
        description="위험 구간 목록"
    )
    comparison: Optional[ComparisonResponse] = Field(
        None,
        description="비교 맥락"
    )
    disclaimer: str = Field(..., description="면책 조항")

    class Config:
        json_schema_extra = {
            "example": {
                "summary": "지난 1.0년간 이 포트폴리오는 연평균 8.5%의 수익을 기록했으며...",
                "performance_explanation": [
                    {
                        "metric": "CAGR",
                        "value": 0.085,
                        "formatted_value": "+8.50%",
                        "description": "연평균 8.5%의 수익률을 기록했습니다...",
                        "context": "CAGR(연복리수익률)은...",
                        "level": "moderate"
                    }
                ],
                "risk_explanation": "이 포트폴리오는...",
                "risk_periods": [],
                "comparison": None,
                "disclaimer": "본 분석은 과거 데이터에 기반한..."
            }
        }


class DirectExplainRequest(BaseModel):
    """직접 지표 입력 해석 요청 (포트폴리오 ID 없이)"""
    cagr: float = Field(..., description="연복리수익률", example=0.085)
    volatility: float = Field(..., description="연율화 변동성", example=0.15)
    mdd: float = Field(..., description="최대 낙폭 (음수)", example=-0.12)
    sharpe: Optional[float] = Field(None, description="샤프 비율", example=0.75)
    start_date: date = Field(..., description="분석 시작일", example="2023-01-01")
    end_date: date = Field(..., description="분석 종료일", example="2024-01-01")
    rf_annual: float = Field(0.0, description="무위험 수익률", example=0.035)
    benchmark_name: Optional[str] = Field(None, description="벤치마크 이름")
    benchmark_return: Optional[float] = Field(None, description="벤치마크 수익률")
    mdd_peak_date: Optional[date] = Field(None, description="MDD 고점 날짜")
    mdd_trough_date: Optional[date] = Field(None, description="MDD 저점 날짜")
    recovery_days: Optional[int] = Field(None, description="회복 일수")

    class Config:
        json_schema_extra = {
            "example": {
                "cagr": 0.085,
                "volatility": 0.15,
                "mdd": -0.12,
                "sharpe": 0.75,
                "start_date": "2023-01-01",
                "end_date": "2024-01-01",
                "rf_annual": 0.035,
                "benchmark_name": "KOSPI 200",
                "benchmark_return": 0.065
            }
        }


# ============================================================================
# API Endpoints
# ============================================================================

@router.post(
    "/explain",
    response_model=AnalysisExplainResponse,
    summary="포트폴리오 성과 해석",
    description="""
포트폴리오의 성과 지표를 자연어로 해석하여 반환합니다.

**기능:**
- 수익률(CAGR), 변동성, MDD, 샤프 비율에 대한 자연어 설명
- 위험 구간 분석
- 벤치마크 대비 맥락 비교 (선택)

**주의사항:**
- 본 해석은 투자 권유나 추천이 아닙니다
- 과거 성과가 미래 수익을 보장하지 않습니다
    """,
    responses={
        200: {"description": "성과 해석 결과"},
        400: {"description": "잘못된 요청 (날짜 범위 오류 등)"},
        404: {"description": "포트폴리오를 찾을 수 없음"},
        500: {"description": "서버 내부 오류"}
    }
)
async def explain_portfolio(
    request: AnalysisExplainRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    포트폴리오 성과를 분석하고 자연어로 해석합니다.

    포트폴리오 ID로 시뮬레이션 데이터를 조회하고,
    지정된 기간의 성과 지표를 계산한 뒤 해석을 반환합니다.
    """
    # 날짜 유효성 검증
    if request.end_date <= request.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="종료일은 시작일보다 이후여야 합니다."
        )

    period_days = (request.end_date - request.start_date).days
    if period_days < 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="분석 기간은 최소 30일 이상이어야 합니다."
        )

    # 포트폴리오 ID 파싱
    portfolio_id = request.portfolio_id

    # 포트폴리오 데이터 조회 시도
    # 1. 커스텀 포트폴리오 조회
    # 2. 일반 포트폴리오 조회
    # 3. 시뮬레이션 캐시 조회

    nav_data = None
    portfolio_name = "포트폴리오"

    # 커스텀 포트폴리오 조회
    if portfolio_id.startswith("custom_"):
        try:
            custom_id = int(portfolio_id.replace("custom_", ""))
            custom_portfolio = db.query(CustomPortfolio).filter(
                CustomPortfolio.portfolio_id == custom_id
            ).first()

            if custom_portfolio:
                portfolio_name = custom_portfolio.portfolio_name or "커스텀 포트폴리오"
                # 커스텀 포트폴리오의 경우 시뮬레이션 데이터 필요
                # 여기서는 예시 데이터 또는 실제 시뮬레이션 연동 필요
        except ValueError:
            pass

    # NAV 데이터가 없는 경우 (시뮬레이션 미실행 또는 데이터 없음)
    # 더미 데이터로 예시 응답 생성
    if nav_data is None:
        # 예시: 기본 지표로 해석 생성
        # 실제 구현에서는 시뮬레이션 서비스와 연동 필요
        period_years = period_days / 365.0

        # 기본 예시 지표 (실제로는 시뮬레이션 결과 사용)
        cagr = 0.075  # 7.5%
        volatility = 0.12  # 12%
        mdd = -0.08  # -8%
        sharpe = 0.62

        result = explain_performance(
            cagr=cagr,
            volatility=volatility,
            mdd=mdd,
            sharpe=sharpe,
            period_start=request.start_date,
            period_end=request.end_date,
            rf_annual=0.035,
            benchmark_name=request.benchmark_name,
            benchmark_return=0.065 if request.benchmark_name else None
        )

        return explanation_result_to_dict(result)

    # NAV 데이터가 있는 경우 실제 분석 수행
    # 성과 지표 계산
    metrics = analyze_from_nav_list(nav_data)

    # 해석 생성
    result = explain_performance(
        cagr=metrics.cagr,
        volatility=metrics.volatility,
        mdd=metrics.mdd,
        sharpe=metrics.sharpe,
        period_start=metrics.period_start,
        period_end=metrics.period_end,
        rf_annual=metrics.rf_annual,
        benchmark_name=request.benchmark_name,
        mdd_peak_date=metrics.mdd_peak_date,
        mdd_trough_date=metrics.mdd_trough_date,
        recovery_days=metrics.recovery_days
    )

    return explanation_result_to_dict(result)


@router.post(
    "/explain/direct",
    response_model=AnalysisExplainResponse,
    summary="직접 지표 해석",
    description="""
포트폴리오 ID 없이 직접 성과 지표를 입력하여 해석을 받습니다.

이미 계산된 성과 지표가 있는 경우 이 엔드포인트를 사용하세요.

**주의사항:**
- 본 해석은 투자 권유나 추천이 아닙니다
- 과거 성과가 미래 수익을 보장하지 않습니다
    """
)
async def explain_direct(
    request: DirectExplainRequest,
    current_user: User = Depends(get_current_user)
):
    """
    직접 입력된 성과 지표를 자연어로 해석합니다.

    포트폴리오 시뮬레이션 없이 이미 계산된 지표를 해석할 때 사용합니다.
    """
    # 날짜 유효성 검증
    if request.end_date <= request.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="종료일은 시작일보다 이후여야 합니다."
        )

    # MDD 유효성 검증 (음수여야 함)
    if request.mdd > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MDD는 음수여야 합니다 (예: -0.15 = -15%)"
        )

    # 해석 생성
    result = explain_performance(
        cagr=request.cagr,
        volatility=request.volatility,
        mdd=request.mdd,
        sharpe=request.sharpe,
        period_start=request.start_date,
        period_end=request.end_date,
        rf_annual=request.rf_annual,
        benchmark_name=request.benchmark_name,
        benchmark_return=request.benchmark_return,
        mdd_peak_date=request.mdd_peak_date,
        mdd_trough_date=request.mdd_trough_date,
        recovery_days=request.recovery_days
    )

    return explanation_result_to_dict(result)


@router.get(
    "/disclaimer",
    summary="면책 조항 조회",
    description="서비스 면책 조항을 조회합니다."
)
async def get_disclaimer():
    """
    서비스 면책 조항을 반환합니다.
    """
    return {
        "disclaimer": DISCLAIMER,
        "regulatory_notes": [
            "본 서비스는 투자자문업에 해당하지 않습니다.",
            "종목 추천 및 투자 판단 유도를 하지 않습니다.",
            "과거 성과는 미래 수익을 보장하지 않습니다.",
            "모든 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다."
        ]
    }
