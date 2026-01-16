"""
Phase 2 Epic C: 커스텀 포트폴리오 서비스

커스텀 포트폴리오 CRUD 및 검증 로직

**주요 기능:**
- 포트폴리오 생성/조회/수정/삭제(soft delete)
- 비중 검증 (합계=1, 범위, 허용 자산군)
- 소유자 기반 접근 제어

⚠️ 본 서비스는 시뮬레이션 파라미터 관리용이며,
투자 추천이나 자문을 제공하지 않습니다.
"""

from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.custom_portfolio import (
    CustomPortfolio,
    CustomPortfolioWeight,
    AssetClassMaster,
)


# ============================================================================
# 상수 및 설정
# ============================================================================

# 비중 합계 허용 오차
WEIGHT_SUM_EPSILON = 1e-6

# 기본 허용 자산군 코드 (DB에 없을 경우 폴백)
DEFAULT_ASSET_CLASSES = ["EQUITY", "BOND", "CASH", "GOLD", "ALT"]

# 최소 자산군 수
MIN_ASSET_CLASS_COUNT = 1


# ============================================================================
# 검증 로직
# ============================================================================

class PortfolioValidationError(Exception):
    """포트폴리오 검증 오류"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


def get_allowed_asset_classes(db: Session) -> List[str]:
    """
    허용된 자산군 코드 목록 조회

    Args:
        db: DB 세션

    Returns:
        허용된 asset_class_code 리스트
    """
    try:
        result = db.query(AssetClassMaster.asset_class_code).filter(
            AssetClassMaster.is_active == True
        ).all()
        if result:
            return [r[0] for r in result]
    except Exception:
        pass

    # DB 조회 실패 시 기본값
    return DEFAULT_ASSET_CLASSES


def validate_weights(
    weights: Dict[str, float],
    db: Session = None
) -> Tuple[bool, Optional[str]]:
    """
    비중 검증

    검증 항목:
    1. 합계 = 1.0 (허용 오차 내)
    2. 각 비중 범위: 0 <= weight <= 1
    3. 허용된 자산군 코드만 사용
    4. 최소 자산군 수 충족

    Args:
        weights: {"EQUITY": 0.6, "BOND": 0.4, ...}
        db: DB 세션 (자산군 검증용, 선택)

    Returns:
        (is_valid, error_message)
    """
    if not weights:
        return False, "비중 정보가 비어있습니다."

    # 1. 최소 자산군 수
    if len(weights) < MIN_ASSET_CLASS_COUNT:
        return False, f"최소 {MIN_ASSET_CLASS_COUNT}개 이상의 자산군이 필요합니다."

    # 2. 각 비중 범위 검증
    for code, weight in weights.items():
        if not isinstance(weight, (int, float, Decimal)):
            return False, f"'{code}'의 비중이 숫자가 아닙니다."

        weight_float = float(weight)
        if weight_float < 0 or weight_float > 1:
            return False, f"'{code}'의 비중({weight_float})이 0~1 범위를 벗어났습니다."

    # 3. 합계 검증
    total = sum(float(w) for w in weights.values())
    if abs(total - 1.0) > WEIGHT_SUM_EPSILON:
        return False, f"비중 합계({total:.6f})가 1.0이 아닙니다."

    # 4. 허용된 자산군 코드 검증
    if db:
        allowed_codes = get_allowed_asset_classes(db)
        for code in weights.keys():
            if code not in allowed_codes:
                return False, f"허용되지 않은 자산군 코드입니다: '{code}'"

    return True, None


def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """
    비중 정규화 (합계 = 1.0으로 조정)

    Args:
        weights: 원본 비중

    Returns:
        정규화된 비중
    """
    total = sum(weights.values())
    if total == 0:
        return weights

    return {k: v / total for k, v in weights.items()}


# ============================================================================
# CRUD 서비스
# ============================================================================

def create_portfolio(
    db: Session,
    owner_user_id: int,
    portfolio_name: str,
    weights: Dict[str, float],
    description: str = None,
    base_template_id: str = None
) -> CustomPortfolio:
    """
    커스텀 포트폴리오 생성

    Args:
        db: DB 세션
        owner_user_id: 소유자 사용자 ID
        portfolio_name: 포트폴리오 이름
        weights: 자산군별 비중 {"EQUITY": 0.6, ...}
        description: 설명 (선택)
        base_template_id: 기반 템플릿 ID (선택)

    Returns:
        생성된 CustomPortfolio

    Raises:
        PortfolioValidationError: 검증 실패 시
    """
    # 1. 비중 검증
    is_valid, error_msg = validate_weights(weights, db)
    if not is_valid:
        raise PortfolioValidationError(error_msg)

    # 2. 포트폴리오 생성
    portfolio = CustomPortfolio(
        owner_user_id=owner_user_id,
        portfolio_name=portfolio_name,
        description=description,
        base_template_id=base_template_id,
        is_active=True,
    )
    db.add(portfolio)
    db.flush()  # portfolio_id 생성

    # 3. 비중 저장
    for code, weight in weights.items():
        weight_record = CustomPortfolioWeight(
            portfolio_id=portfolio.portfolio_id,
            asset_class_code=code,
            target_weight=Decimal(str(weight)),
        )
        db.add(weight_record)

    db.commit()
    db.refresh(portfolio)

    return portfolio


def get_portfolio(
    db: Session,
    portfolio_id: int,
    owner_user_id: int = None
) -> Optional[CustomPortfolio]:
    """
    포트폴리오 조회

    Args:
        db: DB 세션
        portfolio_id: 포트폴리오 ID
        owner_user_id: 소유자 ID (권한 검증용, 선택)

    Returns:
        CustomPortfolio 또는 None
    """
    query = db.query(CustomPortfolio).filter(
        CustomPortfolio.portfolio_id == portfolio_id,
        CustomPortfolio.is_active == True,
    )

    if owner_user_id is not None:
        query = query.filter(CustomPortfolio.owner_user_id == owner_user_id)

    return query.first()


def list_portfolios(
    db: Session,
    owner_user_id: int,
    include_inactive: bool = False
) -> List[CustomPortfolio]:
    """
    사용자의 포트폴리오 목록 조회

    Args:
        db: DB 세션
        owner_user_id: 소유자 ID
        include_inactive: 비활성 포함 여부

    Returns:
        CustomPortfolio 리스트
    """
    query = db.query(CustomPortfolio).filter(
        CustomPortfolio.owner_user_id == owner_user_id,
    )

    if not include_inactive:
        query = query.filter(CustomPortfolio.is_active == True)

    return query.order_by(CustomPortfolio.updated_at.desc()).all()


def update_portfolio(
    db: Session,
    portfolio_id: int,
    owner_user_id: int,
    portfolio_name: str = None,
    weights: Dict[str, float] = None,
    description: str = None,
) -> Optional[CustomPortfolio]:
    """
    포트폴리오 수정

    Args:
        db: DB 세션
        portfolio_id: 포트폴리오 ID
        owner_user_id: 소유자 ID (권한 검증)
        portfolio_name: 새 이름 (선택)
        weights: 새 비중 (선택)
        description: 새 설명 (선택)

    Returns:
        수정된 CustomPortfolio 또는 None

    Raises:
        PortfolioValidationError: 비중 검증 실패 시
    """
    portfolio = get_portfolio(db, portfolio_id, owner_user_id)
    if not portfolio:
        return None

    # 이름 수정
    if portfolio_name is not None:
        portfolio.portfolio_name = portfolio_name

    # 설명 수정
    if description is not None:
        portfolio.description = description

    # 비중 수정
    if weights is not None:
        # 검증
        is_valid, error_msg = validate_weights(weights, db)
        if not is_valid:
            raise PortfolioValidationError(error_msg)

        # 기존 비중 삭제
        db.query(CustomPortfolioWeight).filter(
            CustomPortfolioWeight.portfolio_id == portfolio_id
        ).delete()

        # 새 비중 저장
        for code, weight in weights.items():
            weight_record = CustomPortfolioWeight(
                portfolio_id=portfolio_id,
                asset_class_code=code,
                target_weight=Decimal(str(weight)),
            )
            db.add(weight_record)

    db.commit()
    db.refresh(portfolio)

    return portfolio


def delete_portfolio(
    db: Session,
    portfolio_id: int,
    owner_user_id: int,
    hard_delete: bool = False
) -> bool:
    """
    포트폴리오 삭제 (기본: soft delete)

    Args:
        db: DB 세션
        portfolio_id: 포트폴리오 ID
        owner_user_id: 소유자 ID (권한 검증)
        hard_delete: 물리 삭제 여부

    Returns:
        삭제 성공 여부
    """
    portfolio = get_portfolio(db, portfolio_id, owner_user_id)
    if not portfolio:
        return False

    if hard_delete:
        db.delete(portfolio)
    else:
        portfolio.is_active = False

    db.commit()
    return True


# ============================================================================
# 유틸리티
# ============================================================================

def get_weights_for_simulation(
    db: Session,
    portfolio_id: int
) -> Dict[str, float]:
    """
    시뮬레이션용 비중 조회

    Args:
        db: DB 세션
        portfolio_id: 포트폴리오 ID

    Returns:
        {"EQUITY": 0.6, "BOND": 0.4, ...}

    Raises:
        ValueError: 포트폴리오 없음
    """
    portfolio = db.query(CustomPortfolio).filter(
        CustomPortfolio.portfolio_id == portfolio_id,
        CustomPortfolio.is_active == True,
    ).first()

    if not portfolio:
        raise ValueError(f"포트폴리오 ID {portfolio_id}를 찾을 수 없습니다.")

    return portfolio.get_weights_dict()


def get_weights_hash_string(weights: Dict[str, float]) -> str:
    """
    request_hash 계산용 비중 문자열

    정렬하여 일관된 해시 생성

    Args:
        weights: 비중 dict

    Returns:
        "BOND:0.3000|CASH:0.1000|EQUITY:0.6000"
    """
    sorted_weights = sorted(weights.items(), key=lambda x: x[0])
    return "|".join(f"{k}:{v:.4f}" for k, v in sorted_weights)


def get_asset_class_list(db: Session) -> List[dict]:
    """
    허용된 자산군 목록 조회 (API 응답용)

    Args:
        db: DB 세션

    Returns:
        자산군 정보 리스트
    """
    try:
        result = db.query(AssetClassMaster).filter(
            AssetClassMaster.is_active == True
        ).order_by(AssetClassMaster.display_order).all()

        return [r.to_dict() for r in result]
    except Exception:
        # 테이블 없을 경우 기본값
        return [
            {"asset_class_code": code, "asset_class_name": code, "is_active": True}
            for code in DEFAULT_ASSET_CLASSES
        ]
