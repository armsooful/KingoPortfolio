"""
복합 등급 체계 권한 관리 유틸리티

VIP 등급과 멤버십 플랜에 따른 권한을 관리합니다.
"""
import logging
from typing import Dict, Any
from datetime import datetime
from app.models.user import User

logger = logging.getLogger(__name__)


# ============================================================
# 등급별 권한 정의
# ============================================================

# VIP 등급별 권한
VIP_TIER_PERMISSIONS = {
    'bronze': {
        'max_portfolios': 3,  # 최대 포트폴리오 개수
        'historical_data_months': 3,  # 과거 데이터 조회 가능 기간 (개월)
        'activity_point_multiplier': 1.0,  # 활동 점수 배율
    },
    'silver': {
        'max_portfolios': 5,
        'historical_data_months': 6,
        'activity_point_multiplier': 1.2,
    },
    'gold': {
        'max_portfolios': 10,
        'historical_data_months': 12,
        'activity_point_multiplier': 1.5,
    },
    'platinum': {
        'max_portfolios': 20,
        'historical_data_months': 24,
        'activity_point_multiplier': 2.0,
    },
    'diamond': {
        'max_portfolios': 100,  # 사실상 무제한
        'historical_data_months': 60,  # 5년
        'activity_point_multiplier': 3.0,
    },
}

# 멤버십 플랜별 권한
MEMBERSHIP_PERMISSIONS = {
    'free': {
        'monthly_ai_requests': 10,  # 월 AI 요청 제한
        'monthly_reports': 2,  # 월 리포트 생성 제한
        'advanced_charts': False,  # 고급 차트 접근
        'export_reports': False,  # 리포트 내보내기 (PDF 등)
        'real_time_data': False,  # 실시간 데이터
        'custom_alerts': False,  # 맞춤 알림
    },
    'starter': {
        'monthly_ai_requests': 50,
        'monthly_reports': 10,
        'advanced_charts': True,
        'export_reports': True,
        'real_time_data': False,
        'custom_alerts': False,
    },
    'pro': {
        'monthly_ai_requests': 200,
        'monthly_reports': 50,
        'advanced_charts': True,
        'export_reports': True,
        'real_time_data': True,
        'custom_alerts': True,
    },
    'enterprise': {
        'monthly_ai_requests': 1000,  # 사실상 무제한
        'monthly_reports': 500,
        'advanced_charts': True,
        'export_reports': True,
        'real_time_data': True,
        'custom_alerts': True,
    },
}

# VIP 등급 업그레이드 기준
VIP_TIER_THRESHOLDS = {
    'silver': {'activity_points': 100, 'total_assets_만원': 5000},
    'gold': {'activity_points': 500, 'total_assets_만원': 10000},
    'platinum': {'activity_points': 1000, 'total_assets_만원': 50000},
    'diamond': {'activity_points': 3000, 'total_assets_만원': 100000},
}


# ============================================================
# 권한 체크 함수
# ============================================================

def get_user_permissions(user: User) -> Dict[str, Any]:
    """
    사용자의 전체 권한을 반환합니다.

    Args:
        user: User 모델 인스턴스

    Returns:
        dict: 사용자의 모든 권한 정보
    """
    vip_perms = VIP_TIER_PERMISSIONS.get(user.vip_tier, VIP_TIER_PERMISSIONS['bronze'])
    membership_perms = MEMBERSHIP_PERMISSIONS.get(user.membership_plan, MEMBERSHIP_PERMISSIONS['free'])

    return {
        'vip_tier': user.vip_tier,
        'membership_plan': user.membership_plan,
        'vip_permissions': vip_perms,
        'membership_permissions': membership_perms,
        'combined_permissions': {
            # VIP 등급 권한
            'max_portfolios': vip_perms['max_portfolios'],
            'historical_data_months': vip_perms['historical_data_months'],
            'activity_point_multiplier': vip_perms['activity_point_multiplier'],

            # 멤버십 권한
            'monthly_ai_requests': membership_perms['monthly_ai_requests'],
            'monthly_reports': membership_perms['monthly_reports'],
            'advanced_charts': membership_perms['advanced_charts'],
            'export_reports': membership_perms['export_reports'],
            'real_time_data': membership_perms['real_time_data'],
            'custom_alerts': membership_perms['custom_alerts'],

            # 현재 사용량
            'current_ai_requests': user.monthly_ai_requests,
            'current_reports': user.monthly_reports_generated,
        }
    }


def can_create_portfolio(user: User, current_portfolio_count: int) -> tuple[bool, str]:
    """
    사용자가 포트폴리오를 생성할 수 있는지 확인합니다.

    Args:
        user: User 모델 인스턴스
        current_portfolio_count: 현재 포트폴리오 개수

    Returns:
        tuple: (가능 여부, 메시지)
    """
    perms = VIP_TIER_PERMISSIONS.get(user.vip_tier, VIP_TIER_PERMISSIONS['bronze'])
    max_portfolios = perms['max_portfolios']

    if current_portfolio_count >= max_portfolios:
        return False, f"포트폴리오 생성 한도에 도달했습니다. (최대 {max_portfolios}개, 현재 VIP 등급: {user.vip_tier.upper()})"

    return True, "포트폴리오 생성 가능"


def can_request_ai_analysis(user: User) -> tuple[bool, str]:
    """
    사용자가 AI 분석을 요청할 수 있는지 확인합니다.

    Args:
        user: User 모델 인스턴스

    Returns:
        tuple: (가능 여부, 메시지)
    """
    perms = MEMBERSHIP_PERMISSIONS.get(user.membership_plan, MEMBERSHIP_PERMISSIONS['free'])
    monthly_limit = perms['monthly_ai_requests']

    if user.monthly_ai_requests >= monthly_limit:
        return False, f"이번 달 AI 요청 한도에 도달했습니다. ({user.monthly_ai_requests}/{monthly_limit}, 현재 플랜: {user.membership_plan.upper()})"

    return True, f"AI 분석 요청 가능 (남은 횟수: {monthly_limit - user.monthly_ai_requests})"


def can_generate_report(user: User) -> tuple[bool, str]:
    """
    사용자가 리포트를 생성할 수 있는지 확인합니다.

    Args:
        user: User 모델 인스턴스

    Returns:
        tuple: (가능 여부, 메시지)
    """
    perms = MEMBERSHIP_PERMISSIONS.get(user.membership_plan, MEMBERSHIP_PERMISSIONS['free'])
    monthly_limit = perms['monthly_reports']

    if user.monthly_reports_generated >= monthly_limit:
        return False, f"이번 달 리포트 생성 한도에 도달했습니다. ({user.monthly_reports_generated}/{monthly_limit}, 현재 플랜: {user.membership_plan.upper()})"

    return True, f"리포트 생성 가능 (남은 횟수: {monthly_limit - user.monthly_reports_generated})"


def can_access_advanced_charts(user: User) -> tuple[bool, str]:
    """
    사용자가 고급 차트에 접근할 수 있는지 확인합니다.

    Args:
        user: User 모델 인스턴스

    Returns:
        tuple: (가능 여부, 메시지)
    """
    perms = MEMBERSHIP_PERMISSIONS.get(user.membership_plan, MEMBERSHIP_PERMISSIONS['free'])

    if not perms['advanced_charts']:
        return False, f"고급 차트는 Starter 이상 플랜에서 사용 가능합니다. (현재 플랜: {user.membership_plan.upper()})"

    return True, "고급 차트 접근 가능"


def can_export_report(user: User) -> tuple[bool, str]:
    """
    사용자가 리포트를 내보낼 수 있는지 확인합니다.

    Args:
        user: User 모델 인스턴스

    Returns:
        tuple: (가능 여부, 메시지)
    """
    perms = MEMBERSHIP_PERMISSIONS.get(user.membership_plan, MEMBERSHIP_PERMISSIONS['free'])

    if not perms['export_reports']:
        return False, f"리포트 내보내기는 Starter 이상 플랜에서 사용 가능합니다. (현재 플랜: {user.membership_plan.upper()})"

    return True, "리포트 내보내기 가능"


def can_access_real_time_data(user: User) -> tuple[bool, str]:
    """
    사용자가 실시간 데이터에 접근할 수 있는지 확인합니다.

    Args:
        user: User 모델 인스턴스

    Returns:
        tuple: (가능 여부, 메시지)
    """
    perms = MEMBERSHIP_PERMISSIONS.get(user.membership_plan, MEMBERSHIP_PERMISSIONS['free'])

    if not perms['real_time_data']:
        return False, f"실시간 데이터는 Pro 이상 플랜에서 사용 가능합니다. (현재 플랜: {user.membership_plan.upper()})"

    return True, "실시간 데이터 접근 가능"


def get_historical_data_limit_months(user: User) -> int:
    """
    사용자가 조회할 수 있는 과거 데이터 기간을 반환합니다.

    Args:
        user: User 모델 인스턴스

    Returns:
        int: 조회 가능한 개월 수
    """
    perms = VIP_TIER_PERMISSIONS.get(user.vip_tier, VIP_TIER_PERMISSIONS['bronze'])
    return perms['historical_data_months']


# ============================================================
# VIP 등급 자동 업데이트
# ============================================================

def calculate_vip_tier(activity_points: int, total_assets_만원: int = 0) -> str:
    """
    활동 점수와 총 자산을 기준으로 VIP 등급을 계산합니다.

    Args:
        activity_points: 활동 점수
        total_assets_만원: 총 자산 (만원 단위)

    Returns:
        str: VIP 등급 ('bronze', 'silver', 'gold', 'platinum', 'diamond')
    """
    # 다이아몬드 체크
    if (activity_points >= VIP_TIER_THRESHOLDS['diamond']['activity_points'] or
        total_assets_만원 >= VIP_TIER_THRESHOLDS['diamond']['total_assets_만원']):
        return 'diamond'

    # 플래티넘 체크
    if (activity_points >= VIP_TIER_THRESHOLDS['platinum']['activity_points'] or
        total_assets_만원 >= VIP_TIER_THRESHOLDS['platinum']['total_assets_만원']):
        return 'platinum'

    # 골드 체크
    if (activity_points >= VIP_TIER_THRESHOLDS['gold']['activity_points'] or
        total_assets_만원 >= VIP_TIER_THRESHOLDS['gold']['total_assets_만원']):
        return 'gold'

    # 실버 체크
    if (activity_points >= VIP_TIER_THRESHOLDS['silver']['activity_points'] or
        total_assets_만원 >= VIP_TIER_THRESHOLDS['silver']['total_assets_만원']):
        return 'silver'

    # 기본값: 브론즈
    return 'bronze'


def update_vip_tier(user: User) -> tuple[str, bool]:
    """
    사용자의 VIP 등급을 업데이트합니다.

    Args:
        user: User 모델 인스턴스

    Returns:
        tuple: (새 등급, 등급이 변경되었는지 여부)
    """
    total_assets = user.total_assets or 0
    new_tier = calculate_vip_tier(user.activity_points, total_assets)

    tier_changed = new_tier != user.vip_tier
    user.vip_tier = new_tier

    return new_tier, tier_changed


def add_activity_points(user: User, points: int, activity_type: str = '') -> int:
    """
    사용자에게 활동 점수를 추가합니다.

    Args:
        user: User 모델 인스턴스
        points: 추가할 점수
        activity_type: 활동 유형 (로깅용)

    Returns:
        int: 업데이트된 총 점수
    """
    # VIP 등급별 점수 배율 적용
    perms = VIP_TIER_PERMISSIONS.get(user.vip_tier, VIP_TIER_PERMISSIONS['bronze'])
    multiplier = perms['activity_point_multiplier']

    bonus_points = int(points * multiplier)
    user.activity_points += bonus_points

    logger.info("활동 점수 획득: %s +%d (배율 %sx = +%d), 총 %d",
                activity_type, points, multiplier, bonus_points, user.activity_points)

    # VIP 등급 자동 업데이트
    new_tier, tier_changed = update_vip_tier(user)
    if tier_changed:
        logger.info("VIP 등급 상승! %s → %s", user.vip_tier, new_tier)

    return user.activity_points


# ============================================================
# 멤버십 관리
# ============================================================

def is_membership_active(user: User) -> bool:
    """
    사용자의 멤버십이 활성 상태인지 확인합니다.

    Args:
        user: User 모델 인스턴스

    Returns:
        bool: 멤버십 활성 여부
    """
    if user.membership_plan == 'free':
        return True

    if not user.membership_end_date:
        return False

    return datetime.utcnow() < user.membership_end_date


def get_membership_status(user: User) -> Dict[str, Any]:
    """
    사용자의 멤버십 상태 정보를 반환합니다.

    Args:
        user: User 모델 인스턴스

    Returns:
        dict: 멤버십 상태 정보
    """
    is_active = is_membership_active(user)

    status = {
        'plan': user.membership_plan,
        'is_active': is_active,
        'start_date': user.membership_start_date,
        'end_date': user.membership_end_date,
    }

    if user.membership_end_date and is_active:
        days_remaining = (user.membership_end_date - datetime.utcnow()).days
        status['days_remaining'] = days_remaining

    return status


# ============================================================
# 사용량 추적
# ============================================================

def reset_monthly_usage_if_needed(user: User) -> bool:
    """
    필요한 경우 월별 사용량을 리셋합니다.

    Args:
        user: User 모델 인스턴스

    Returns:
        bool: 리셋 여부
    """
    if not user.last_usage_reset:
        user.last_usage_reset = datetime.utcnow()
        return False

    # 마지막 리셋 이후 한 달이 지났는지 확인
    now = datetime.utcnow()
    days_since_reset = (now - user.last_usage_reset).days

    if days_since_reset >= 30:
        user.monthly_ai_requests = 0
        user.monthly_reports_generated = 0
        user.last_usage_reset = now
        logger.info("월별 사용량 리셋: %s", user.email)
        return True

    return False


def increment_ai_requests(user: User) -> int:
    """
    AI 요청 횟수를 증가시킵니다.

    Args:
        user: User 모델 인스턴스

    Returns:
        int: 업데이트된 AI 요청 횟수
    """
    reset_monthly_usage_if_needed(user)
    user.monthly_ai_requests += 1
    return user.monthly_ai_requests


def increment_report_generation(user: User) -> int:
    """
    리포트 생성 횟수를 증가시킵니다.

    Args:
        user: User 모델 인스턴스

    Returns:
        int: 업데이트된 리포트 생성 횟수
    """
    reset_monthly_usage_if_needed(user)
    user.monthly_reports_generated += 1
    return user.monthly_reports_generated
