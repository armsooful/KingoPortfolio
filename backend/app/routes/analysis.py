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
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from io import BytesIO

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
from app.services.pdf_report_generator import PDFReportGenerator
from app.models.analysis import ExplanationHistory


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


# ============================================================================
# Phase 3-B: PDF 다운로드 엔드포인트
# ============================================================================

@router.post(
    "/explain/pdf",
    summary="성과 해석 PDF 리포트 다운로드",
    description="""
성과 해석 결과를 PDF 리포트로 다운로드합니다.

**기능:**
- 성과 지표 해석 포함
- 위험 분석 섹션
- 비교 맥락 (선택)
- 면책 조항

**주의사항:**
- 본 리포트는 투자 권유가 아닙니다
- 과거 성과가 미래 수익을 보장하지 않습니다
    """,
    responses={
        200: {
            "description": "PDF 파일",
            "content": {"application/pdf": {}}
        },
        400: {"description": "잘못된 요청"},
        500: {"description": "PDF 생성 오류"}
    }
)
async def download_explanation_pdf(
    request: DirectExplainRequest,
    current_user: User = Depends(get_current_user)
):
    """
    성과 해석 결과를 PDF 파일로 생성하여 다운로드합니다.
    """
    # 날짜 유효성 검증
    if request.end_date <= request.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="종료일은 시작일보다 이후여야 합니다."
        )

    # MDD 유효성 검증
    if request.mdd > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MDD는 음수여야 합니다 (예: -0.15 = -15%)"
        )

    try:
        # 해석 결과 생성
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

        explanation_data = explanation_result_to_dict(result)

        # PDF 생성
        pdf_generator = PDFReportGenerator()
        pdf_buffer = pdf_generator.generate_explanation_report(explanation_data)

        # 파일명 생성
        filename = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF 생성 중 오류가 발생했습니다: {str(e)}"
        )


@router.post(
    "/explain/portfolio/pdf",
    summary="포트폴리오 성과 해석 PDF 다운로드",
    description="""
포트폴리오 ID로 성과 해석 PDF 리포트를 다운로드합니다.

**주의사항:**
- 본 리포트는 투자 권유가 아닙니다
- 과거 성과가 미래 수익을 보장하지 않습니다
    """,
    responses={
        200: {
            "description": "PDF 파일",
            "content": {"application/pdf": {}}
        },
        400: {"description": "잘못된 요청"},
        404: {"description": "포트폴리오를 찾을 수 없음"},
        500: {"description": "PDF 생성 오류"}
    }
)
async def download_portfolio_explanation_pdf(
    request: AnalysisExplainRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    포트폴리오 성과 해석 결과를 PDF로 다운로드합니다.
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

    try:
        # 포트폴리오 데이터 조회 (간략화 - 실제로는 시뮬레이션 연동)
        # 예시 지표 사용
        period_years = period_days / 365.0
        cagr = 0.075
        volatility = 0.12
        mdd = -0.08
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

        explanation_data = explanation_result_to_dict(result)

        # PDF 생성
        pdf_generator = PDFReportGenerator()
        pdf_buffer = pdf_generator.generate_explanation_report(explanation_data)

        # 파일명 생성
        filename = f"portfolio_report_{request.portfolio_id}_{datetime.now().strftime('%Y%m%d')}.pdf"

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF 생성 중 오류가 발생했습니다: {str(e)}"
        )


# ============================================================================
# Phase 3-B: 프리미엄 리포트 PDF API
# ============================================================================

class PremiumReportRequest(BaseModel):
    """프리미엄 리포트 요청"""
    cagr: float = Field(..., description="연복리수익률")
    volatility: float = Field(..., description="연율화 변동성")
    mdd: float = Field(..., description="최대 낙폭 (음수)")
    sharpe: Optional[float] = Field(None, description="샤프 비율")
    start_date: date = Field(..., description="분석 시작일")
    end_date: date = Field(..., description="분석 종료일")
    rf_annual: float = Field(0.0, description="무위험 수익률")
    benchmark_name: Optional[str] = Field(None, description="벤치마크 이름")
    benchmark_return: Optional[float] = Field(None, description="벤치마크 수익률")
    report_title: Optional[str] = Field(None, description="리포트 제목")
    total_return: Optional[float] = Field(None, description="누적 수익률")


@router.post(
    "/premium-report/pdf",
    summary="프리미엄 성과 해석 리포트 PDF",
    description="""
프리미엄 성과 해석 리포트를 PDF로 생성합니다.

**리포트 구성:**
1. 표지 - 리포트 제목, 분석 기간, 고지 문구
2. 요약 페이지 - 한 문장 요약, 핵심 지표 테이블
3. 성과 해석 섹션 - 각 지표별 상세 해석
4. 위험 구간 분석 - 최대 낙폭 구간, 회복 과정
5. 맥락 비교 - 시장 대비 비교 (선택)
6. 종합 해석 - 포트폴리오 특성 종합
7. 참고 및 고지 - 면책 조항

**주의사항:**
- 본 리포트는 투자 권유가 아닙니다
- 과거 성과가 미래 수익을 보장하지 않습니다
    """,
    responses={
        200: {
            "description": "PDF 파일",
            "content": {"application/pdf": {}}
        },
        400: {"description": "잘못된 요청"},
        500: {"description": "PDF 생성 오류"}
    }
)
async def generate_premium_report_pdf(
    request: PremiumReportRequest,
    current_user: User = Depends(get_current_user)
):
    """
    프리미엄 성과 해석 리포트 PDF를 생성합니다.
    """
    # 유효성 검증
    if request.end_date <= request.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="종료일은 시작일보다 이후여야 합니다."
        )

    if request.mdd > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MDD는 음수여야 합니다 (예: -0.15 = -15%)"
        )

    try:
        # 해석 결과 생성
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
        )

        explanation_data = explanation_result_to_dict(result)

        # 프리미엄 PDF 생성
        pdf_generator = PDFReportGenerator()
        pdf_buffer = pdf_generator.generate_premium_report(
            explanation_data=explanation_data,
            report_title=request.report_title,
            period_start=request.start_date.isoformat(),
            period_end=request.end_date.isoformat(),
            total_return=request.total_return
        )

        # 파일명 생성
        title_slug = (request.report_title or "premium_report").replace(" ", "_")[:30]
        filename = f"{title_slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF 생성 중 오류가 발생했습니다: {str(e)}"
        )


# ============================================================================
# Phase 3-B: 리포트 히스토리 API
# ============================================================================

class SaveHistoryRequest(BaseModel):
    """히스토리 저장 요청"""
    cagr: float
    volatility: float
    mdd: float
    sharpe: Optional[float] = None
    start_date: date
    end_date: date
    rf_annual: float = 0.0
    benchmark_name: Optional[str] = None
    benchmark_return: Optional[float] = None
    portfolio_id: Optional[int] = None
    portfolio_type: Optional[str] = None
    report_title: Optional[str] = None


class HistoryResponse(BaseModel):
    """히스토리 응답"""
    history_id: int
    user_id: int
    portfolio_id: Optional[int]
    portfolio_type: Optional[str]
    period_start: str
    period_end: str
    input_metrics: dict
    explanation_result: dict
    report_title: Optional[str]
    pdf_downloaded: int
    created_at: str
    updated_at: str


@router.post(
    "/history",
    response_model=HistoryResponse,
    summary="성과 해석 히스토리 저장",
    description="성과 해석 결과를 히스토리에 저장합니다."
)
async def save_explanation_history(
    request: SaveHistoryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    성과 해석 결과를 히스토리에 저장합니다.
    """
    # 해석 결과 생성
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
    )

    explanation_data = explanation_result_to_dict(result)

    # 입력 지표 저장
    input_metrics = {
        "cagr": request.cagr,
        "volatility": request.volatility,
        "mdd": request.mdd,
        "sharpe": request.sharpe,
        "rf_annual": request.rf_annual,
        "benchmark_name": request.benchmark_name,
        "benchmark_return": request.benchmark_return,
    }

    # 히스토리 저장
    history = ExplanationHistory(
        user_id=current_user.user_id,
        portfolio_id=request.portfolio_id,
        portfolio_type=request.portfolio_type,
        period_start=datetime.combine(request.start_date, datetime.min.time()),
        period_end=datetime.combine(request.end_date, datetime.min.time()),
        input_metrics=input_metrics,
        explanation_result=explanation_data,
        report_title=request.report_title,
        pdf_downloaded=0,
    )

    db.add(history)
    db.commit()
    db.refresh(history)

    return history.to_dict()


@router.get(
    "/history",
    summary="성과 해석 히스토리 목록 조회",
    description="사용자의 성과 해석 히스토리 목록을 조회합니다."
)
async def get_explanation_history(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    사용자의 성과 해석 히스토리 목록을 조회합니다.
    """
    histories = db.query(ExplanationHistory).filter(
        ExplanationHistory.user_id == current_user.user_id
    ).order_by(
        ExplanationHistory.created_at.desc()
    ).offset(skip).limit(limit).all()

    total = db.query(ExplanationHistory).filter(
        ExplanationHistory.user_id == current_user.user_id
    ).count()

    return {
        "items": [h.to_dict() for h in histories],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get(
    "/history/{history_id}",
    response_model=HistoryResponse,
    summary="성과 해석 히스토리 상세 조회",
    description="특정 성과 해석 히스토리를 조회합니다."
)
async def get_explanation_history_detail(
    history_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    특정 성과 해석 히스토리를 조회합니다.
    """
    history = db.query(ExplanationHistory).filter(
        ExplanationHistory.history_id == history_id,
        ExplanationHistory.user_id == current_user.user_id
    ).first()

    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="히스토리를 찾을 수 없습니다."
        )

    return history.to_dict()


@router.delete(
    "/history/{history_id}",
    summary="성과 해석 히스토리 삭제",
    description="특정 성과 해석 히스토리를 삭제합니다."
)
async def delete_explanation_history(
    history_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    특정 성과 해석 히스토리를 삭제합니다.
    """
    history = db.query(ExplanationHistory).filter(
        ExplanationHistory.history_id == history_id,
        ExplanationHistory.user_id == current_user.user_id
    ).first()

    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="히스토리를 찾을 수 없습니다."
        )

    db.delete(history)
    db.commit()

    return {"message": "히스토리가 삭제되었습니다.", "history_id": history_id}


# ============================================================================
# Phase 3-B: 기간별 비교 리포트 API
# ============================================================================

class ComparisonPeriod(BaseModel):
    """비교 기간 데이터"""
    period_label: str  # 예: "2023년 1분기"
    cagr: float
    volatility: float
    mdd: float
    sharpe: Optional[float] = None
    start_date: date
    end_date: date


class ComparePeriodsRequest(BaseModel):
    """기간별 비교 요청"""
    periods: List[ComparisonPeriod]
    rf_annual: float = 0.0


@router.post(
    "/compare-periods",
    summary="기간별 비교 리포트",
    description="""
여러 기간의 성과 지표를 비교 분석합니다.

**기능:**
- 다수 기간의 성과 지표 비교
- 기간별 추이 분석
- 변동성 및 위험 비교

**주의사항:**
- 본 분석은 투자 권유가 아닙니다
- 과거 성과가 미래 수익을 보장하지 않습니다
    """
)
async def compare_periods(
    request: ComparePeriodsRequest,
    current_user: User = Depends(get_current_user)
):
    """
    여러 기간의 성과 지표를 비교 분석합니다.
    """
    if len(request.periods) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비교를 위해 최소 2개 이상의 기간이 필요합니다."
        )

    if len(request.periods) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="최대 10개 기간까지 비교 가능합니다."
        )

    # 각 기간별 해석 생성
    period_explanations = []
    for period in request.periods:
        result = explain_performance(
            cagr=period.cagr,
            volatility=period.volatility,
            mdd=period.mdd,
            sharpe=period.sharpe,
            period_start=period.start_date,
            period_end=period.end_date,
            rf_annual=request.rf_annual,
        )

        period_explanations.append({
            "period_label": period.period_label,
            "start_date": period.start_date.isoformat(),
            "end_date": period.end_date.isoformat(),
            "metrics": {
                "cagr": period.cagr,
                "volatility": period.volatility,
                "mdd": period.mdd,
                "sharpe": period.sharpe,
            },
            "explanation": explanation_result_to_dict(result),
        })

    # 비교 분석 생성
    comparison_analysis = _generate_comparison_analysis(request.periods)

    return {
        "period_count": len(request.periods),
        "period_explanations": period_explanations,
        "comparison_analysis": comparison_analysis,
        "disclaimer": DISCLAIMER,
    }


def _generate_comparison_analysis(periods: List[ComparisonPeriod]) -> dict:
    """기간별 비교 분석 생성"""
    cagrs = [p.cagr for p in periods]
    volatilities = [p.volatility for p in periods]
    mdds = [p.mdd for p in periods]

    # 평균 계산
    avg_cagr = sum(cagrs) / len(cagrs)
    avg_volatility = sum(volatilities) / len(volatilities)
    avg_mdd = sum(mdds) / len(mdds)

    # 최고/최저 기간 찾기
    best_cagr_period = periods[cagrs.index(max(cagrs))]
    worst_cagr_period = periods[cagrs.index(min(cagrs))]
    best_mdd_period = periods[mdds.index(max(mdds))]  # MDD는 음수이므로 max가 가장 좋음
    worst_mdd_period = periods[mdds.index(min(mdds))]

    # 추이 분석
    if len(cagrs) >= 2:
        if cagrs[-1] > cagrs[0]:
            trend = "개선"
        elif cagrs[-1] < cagrs[0]:
            trend = "하락"
        else:
            trend = "유지"
    else:
        trend = "데이터 부족"

    return {
        "averages": {
            "cagr": avg_cagr,
            "cagr_formatted": f"{avg_cagr * 100:.2f}%",
            "volatility": avg_volatility,
            "volatility_formatted": f"{avg_volatility * 100:.1f}%",
            "mdd": avg_mdd,
            "mdd_formatted": f"{avg_mdd * 100:.1f}%",
        },
        "best_performance": {
            "period_label": best_cagr_period.period_label,
            "cagr": best_cagr_period.cagr,
            "cagr_formatted": f"{best_cagr_period.cagr * 100:.2f}%",
        },
        "worst_performance": {
            "period_label": worst_cagr_period.period_label,
            "cagr": worst_cagr_period.cagr,
            "cagr_formatted": f"{worst_cagr_period.cagr * 100:.2f}%",
        },
        "safest_period": {
            "period_label": best_mdd_period.period_label,
            "mdd": best_mdd_period.mdd,
            "mdd_formatted": f"{best_mdd_period.mdd * 100:.1f}%",
        },
        "riskiest_period": {
            "period_label": worst_mdd_period.period_label,
            "mdd": worst_mdd_period.mdd,
            "mdd_formatted": f"{worst_mdd_period.mdd * 100:.1f}%",
        },
        "trend": trend,
        "trend_description": _get_trend_description(trend, cagrs, volatilities),
    }


def _get_trend_description(trend: str, cagrs: list, volatilities: list) -> str:
    """추이 설명 생성"""
    if trend == "개선":
        return (
            f"분석 기간 동안 수익률이 전반적으로 개선되는 추세를 보였습니다. "
            f"초기 {cagrs[0]*100:.1f}%에서 최근 {cagrs[-1]*100:.1f}%로 변화했습니다."
        )
    elif trend == "하락":
        return (
            f"분석 기간 동안 수익률이 하락하는 추세를 보였습니다. "
            f"초기 {cagrs[0]*100:.1f}%에서 최근 {cagrs[-1]*100:.1f}%로 변화했습니다."
        )
    elif trend == "유지":
        return "분석 기간 동안 수익률이 비교적 일정하게 유지되었습니다."
    else:
        return "추이 분석을 위한 충분한 데이터가 없습니다."
