"""
Phase 11: Admin 데이터 적재 API

목적: 관리자 전용 실 데이터 적재 엔드포인트
작성일: 2026-01-24

엔드포인트:
- POST /api/v1/admin/data-load/stock-prices: 주식 시세 적재
- POST /api/v1/admin/data-load/index-prices: 지수 시세 적재
- POST /api/v1/admin/data-load/stock-info: 종목 정보 적재
- GET  /api/v1/admin/data-load/batches: 배치 목록 조회
- GET  /api/v1/admin/data-load/batches/{batch_id}: 배치 상세 조회
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from app.auth import require_admin_permission
from app.database import get_db
from app.models import User
from app.services.batch_manager import BatchManager, BatchStatus, BatchType
from app.services.real_data_loader import DataLoadError, RealDataLoader
from app.utils.structured_logging import get_structured_logger, request_context, set_user_id

logger = get_structured_logger(__name__)

router = APIRouter(
    prefix="/api/v1/admin/data-load",
    tags=["Admin Data Load"],
)


# ============================================================================
# Request/Response Schemas
# ============================================================================


class StockPriceLoadRequest(BaseModel):
    """주식 시세 적재 요청"""

    tickers: List[str] = Field(..., description="종목 코드 리스트", min_items=1, max_items=100)
    start_date: date = Field(..., description="조회 시작일")
    end_date: date = Field(..., description="조회 종료일")
    as_of_date: date = Field(..., description="데이터 기준일")
    reason: Optional[str] = Field(None, description="적재 사유", max_length=500)

    @validator("tickers")
    def validate_tickers(cls, v):
        # 종목 코드 형식 검증 (6자리 숫자)
        for ticker in v:
            if not ticker.isdigit() or len(ticker) != 6:
                raise ValueError(f"잘못된 종목 코드 형식: {ticker} (6자리 숫자 필요)")
        return v

    @validator("end_date")
    def validate_end_date(cls, v, values):
        if "start_date" in values and v < values["start_date"]:
            raise ValueError("end_date는 start_date보다 같거나 커야 합니다")
        if v > date.today():
            raise ValueError("end_date는 오늘 이전이어야 합니다")
        return v

    @validator("as_of_date")
    def validate_as_of_date(cls, v, values):
        if "end_date" in values and v < values["end_date"]:
            raise ValueError("as_of_date는 end_date보다 같거나 커야 합니다")
        if v > date.today():
            raise ValueError("as_of_date는 오늘 이전이어야 합니다")
        return v


class IndexPriceLoadRequest(BaseModel):
    """지수 시세 적재 요청"""

    index_codes: List[str] = Field(
        ...,
        description="지수 코드 리스트 (KOSPI, KOSDAQ, KS200, KQ150)",
        min_items=1,
        max_items=10,
    )
    start_date: date = Field(..., description="조회 시작일")
    end_date: date = Field(..., description="조회 종료일")
    as_of_date: date = Field(..., description="데이터 기준일")
    reason: Optional[str] = Field(None, description="적재 사유", max_length=500)

    @validator("index_codes")
    def validate_index_codes(cls, v):
        valid_codes = {"KOSPI", "KOSDAQ", "KS200", "KQ150"}
        for code in v:
            if code.upper() not in valid_codes:
                raise ValueError(f"지원하지 않는 지수 코드: {code}. 지원: {valid_codes}")
        return [c.upper() for c in v]

    @validator("end_date")
    def validate_end_date(cls, v, values):
        if "start_date" in values and v < values["start_date"]:
            raise ValueError("end_date는 start_date보다 같거나 커야 합니다")
        if v > date.today():
            raise ValueError("end_date는 오늘 이전이어야 합니다")
        return v

    @validator("as_of_date")
    def validate_as_of_date(cls, v, values):
        if "end_date" in values and v < values["end_date"]:
            raise ValueError("as_of_date는 end_date보다 같거나 커야 합니다")
        if v > date.today():
            raise ValueError("as_of_date는 오늘 이전이어야 합니다")
        return v


class StockInfoLoadRequest(BaseModel):
    """종목 정보 적재 요청"""

    tickers: List[str] = Field(..., description="종목 코드 리스트", min_items=1, max_items=100)
    as_of_date: date = Field(..., description="데이터 기준일")
    reason: Optional[str] = Field(None, description="적재 사유", max_length=500)

    @validator("tickers")
    def validate_tickers(cls, v):
        for ticker in v:
            if not ticker.isdigit() or len(ticker) != 6:
                raise ValueError(f"잘못된 종목 코드 형식: {ticker} (6자리 숫자 필요)")
        return v

    @validator("as_of_date")
    def validate_as_of_date(cls, v):
        if v > date.today():
            raise ValueError("as_of_date는 오늘 이전이어야 합니다")
        return v


class LoadResultResponse(BaseModel):
    """적재 결과 응답"""

    batch_id: int
    success: bool
    total_records: int
    success_records: int
    failed_records: int
    skipped_records: int
    quality_score: Optional[float] = None
    error_message: Optional[str] = None


class BatchResponse(BaseModel):
    """배치 정보 응답"""

    batch_id: int
    batch_type: str
    source_id: str
    as_of_date: date
    target_start: date
    target_end: date
    status: str
    total_records: int
    success_records: int
    failed_records: int
    skipped_records: int
    quality_score: Optional[float] = None
    operator_id: Optional[str] = None
    operator_reason: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str


class BatchListResponse(BaseModel):
    """배치 목록 응답"""

    count: int
    batches: List[BatchResponse]


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/stock-prices", response_model=LoadResultResponse, status_code=status.HTTP_201_CREATED)
def load_stock_prices(
    payload: StockPriceLoadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN")),
):
    """
    주식 일별 시세 적재 (Admin 전용)

    - 지정된 종목들의 과거 시세 데이터를 pykrx에서 조회하여 DB에 적재
    - 실시간 데이터 적재 불가 (as_of_date <= today)
    """
    with request_context() as req_id:
        set_user_id(str(current_user.id))

        logger.info(
            "주식 시세 적재 API 호출",
            {
                "tickers": len(payload.tickers),
                "start": str(payload.start_date),
                "end": str(payload.end_date),
                "as_of": str(payload.as_of_date),
            },
        )

        try:
            loader = RealDataLoader(db)
            result = loader.load_stock_prices(
                tickers=payload.tickers,
                start_date=payload.start_date,
                end_date=payload.end_date,
                as_of_date=payload.as_of_date,
                operator_id=str(current_user.id),
                operator_reason=payload.reason,
            )

            return LoadResultResponse(
                batch_id=result.batch_id,
                success=result.success,
                total_records=result.total_records,
                success_records=result.success_records,
                failed_records=result.failed_records,
                skipped_records=result.skipped_records,
                quality_score=float(result.quality_score) if result.quality_score else None,
            )

        except DataLoadError as e:
            logger.error("주식 시세 적재 실패", {"error": e.message})
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=e.message,
            ) from e


@router.post("/index-prices", response_model=LoadResultResponse, status_code=status.HTTP_201_CREATED)
def load_index_prices(
    payload: IndexPriceLoadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN")),
):
    """
    지수 일별 시세 적재 (Admin 전용)

    - 지정된 지수들의 과거 시세 데이터를 pykrx에서 조회하여 DB에 적재
    - 지원 지수: KOSPI, KOSDAQ, KS200, KQ150
    """
    with request_context() as req_id:
        set_user_id(str(current_user.id))

        logger.info(
            "지수 시세 적재 API 호출",
            {
                "index_codes": payload.index_codes,
                "start": str(payload.start_date),
                "end": str(payload.end_date),
            },
        )

        try:
            loader = RealDataLoader(db)
            result = loader.load_index_prices(
                index_codes=payload.index_codes,
                start_date=payload.start_date,
                end_date=payload.end_date,
                as_of_date=payload.as_of_date,
                operator_id=str(current_user.id),
                operator_reason=payload.reason,
            )

            return LoadResultResponse(
                batch_id=result.batch_id,
                success=result.success,
                total_records=result.total_records,
                success_records=result.success_records,
                failed_records=result.failed_records,
                skipped_records=result.skipped_records,
                quality_score=float(result.quality_score) if result.quality_score else None,
            )

        except DataLoadError as e:
            logger.error("지수 시세 적재 실패", {"error": e.message})
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=e.message,
            ) from e


@router.post("/stock-info", response_model=LoadResultResponse, status_code=status.HTTP_201_CREATED)
def load_stock_info(
    payload: StockInfoLoadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_RUN")),
):
    """
    종목 기본 정보 적재 (Admin 전용)

    - 지정된 종목들의 기본 정보를 pykrx에서 조회하여 DB에 적재
    """
    with request_context() as req_id:
        set_user_id(str(current_user.id))

        logger.info(
            "종목 정보 적재 API 호출",
            {"tickers": len(payload.tickers), "as_of": str(payload.as_of_date)},
        )

        try:
            loader = RealDataLoader(db)
            result = loader.load_stock_info(
                tickers=payload.tickers,
                as_of_date=payload.as_of_date,
                operator_id=str(current_user.id),
                operator_reason=payload.reason,
            )

            return LoadResultResponse(
                batch_id=result.batch_id,
                success=result.success,
                total_records=result.total_records,
                success_records=result.success_records,
                failed_records=result.failed_records,
                skipped_records=result.skipped_records,
            )

        except DataLoadError as e:
            logger.error("종목 정보 적재 실패", {"error": e.message})
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=e.message,
            ) from e


@router.get("/batches", response_model=BatchListResponse)
def list_batches(
    batch_type: Optional[str] = None,
    source_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW")),
):
    """
    배치 목록 조회 (Admin 전용)
    """
    batch_manager = BatchManager(db)

    # 필터 변환
    bt = BatchType(batch_type.upper()) if batch_type else None
    bs = BatchStatus(status_filter.upper()) if status_filter else None

    batches = batch_manager.list_batches(
        batch_type=bt,
        source_id=source_id,
        status=bs,
        limit=limit,
        offset=offset,
    )

    return BatchListResponse(
        count=len(batches),
        batches=[
            BatchResponse(
                batch_id=b.batch_id,
                batch_type=b.batch_type,
                source_id=b.source_id,
                as_of_date=b.as_of_date,
                target_start=b.target_start,
                target_end=b.target_end,
                status=b.status,
                total_records=b.total_records or 0,
                success_records=b.success_records or 0,
                failed_records=b.failed_records or 0,
                skipped_records=b.skipped_records or 0,
                quality_score=float(b.quality_score) if b.quality_score else None,
                operator_id=b.operator_id,
                operator_reason=b.operator_reason,
                error_message=b.error_message,
                started_at=b.started_at.isoformat() if b.started_at else None,
                completed_at=b.completed_at.isoformat() if b.completed_at else None,
                created_at=b.created_at.isoformat() if b.created_at else "",
            )
            for b in batches
        ],
    )


@router.get("/batches/{batch_id}", response_model=BatchResponse)
def get_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_permission("ADMIN_VIEW")),
):
    """
    배치 상세 조회 (Admin 전용)
    """
    batch_manager = BatchManager(db)
    batch = batch_manager.get_batch(batch_id)

    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"배치를 찾을 수 없습니다: {batch_id}",
        )

    return BatchResponse(
        batch_id=batch.batch_id,
        batch_type=batch.batch_type,
        source_id=batch.source_id,
        as_of_date=batch.as_of_date,
        target_start=batch.target_start,
        target_end=batch.target_end,
        status=batch.status,
        total_records=batch.total_records or 0,
        success_records=batch.success_records or 0,
        failed_records=batch.failed_records or 0,
        skipped_records=batch.skipped_records or 0,
        quality_score=float(batch.quality_score) if batch.quality_score else None,
        operator_id=batch.operator_id,
        operator_reason=batch.operator_reason,
        error_message=batch.error_message,
        started_at=batch.started_at.isoformat() if batch.started_at else None,
        completed_at=batch.completed_at.isoformat() if batch.completed_at else None,
        created_at=batch.created_at.isoformat() if batch.created_at else "",
    )
