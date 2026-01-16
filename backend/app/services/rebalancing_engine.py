"""
Phase 2 리밸런싱 엔진 (Epic B)

시뮬레이션 경로 계산 과정에 리밸런싱 규칙을 적용하여,
- PERIODIC (월간/분기) 리밸런싱
- DRIFT (편차 기반) 리밸런싱
- 비용 모델 적용
- 이벤트 로그 생성

을 수행합니다.

⚠️ 교육 목적: 과거 데이터 기반 시뮬레이션이며, 미래 수익을 보장하지 않습니다.
"""

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import math

from app.config import settings


# ============================================================================
# 데이터 클래스 정의
# ============================================================================

@dataclass
class RebalancingConfig:
    """리밸런싱 설정"""
    # 리밸런싱 타입
    rebalance_type: str = "NONE"  # NONE, PERIODIC, DRIFT, HYBRID

    # PERIODIC 설정
    frequency: Optional[str] = None  # MONTHLY, QUARTERLY
    periodic_timing: str = "START"  # START (월초/분기초), END (월말/분기말)

    # DRIFT 설정
    drift_threshold: Optional[float] = None  # 예: 0.05 = 5%

    # 비용 모델 설정
    cost_rate: float = 0.001  # 기본 10bp

    # 규칙 ID (DB 참조용)
    rule_id: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict) -> "RebalancingConfig":
        """dict에서 생성"""
        return cls(
            rebalance_type=data.get("rebalance_type", "NONE"),
            frequency=data.get("frequency"),
            periodic_timing=data.get("periodic_timing", "START"),
            drift_threshold=data.get("drift_threshold"),
            cost_rate=data.get("cost_rate", settings.default_cost_rate),
            rule_id=data.get("rule_id"),
        )

    @classmethod
    def none(cls) -> "RebalancingConfig":
        """리밸런싱 OFF 설정"""
        return cls(rebalance_type="NONE")

    def is_enabled(self) -> bool:
        """리밸런싱 활성화 여부"""
        return self.rebalance_type != "NONE"

    def is_periodic(self) -> bool:
        """정기 리밸런싱 여부"""
        return self.rebalance_type in ("PERIODIC", "HYBRID")

    def is_drift_based(self) -> bool:
        """Drift 기반 리밸런싱 여부"""
        return self.rebalance_type in ("DRIFT", "HYBRID")


@dataclass
class RebalancingEvent:
    """리밸런싱 발생 이벤트"""
    event_date: date
    event_order: int
    trigger_type: str  # PERIODIC, DRIFT
    trigger_detail: str  # 예: MONTHLY, DRIFT>=0.05
    before_weights: Dict[str, float]
    after_weights: Dict[str, float]
    turnover: float
    cost_rate: float
    cost_factor: float
    nav_before: float
    nav_after: float
    rule_id: Optional[int] = None


@dataclass
class PositionState:
    """포지션 상태"""
    values: Dict[str, float]  # asset_class -> value
    target_weights: Dict[str, float]  # asset_class -> target weight

    def get_total_value(self) -> float:
        """총 평가금액"""
        return sum(self.values.values())

    def get_current_weights(self) -> Dict[str, float]:
        """현재 비중 계산"""
        total = self.get_total_value()
        if total <= 0:
            return {k: 0.0 for k in self.values}
        return {k: v / total for k, v in self.values.items()}

    def get_max_drift(self) -> Tuple[str, float]:
        """최대 Drift 반환 (자산군, drift값)"""
        current_weights = self.get_current_weights()
        max_asset = None
        max_drift = 0.0

        for asset, target_w in self.target_weights.items():
            current_w = current_weights.get(asset, 0.0)
            drift = abs(current_w - target_w)
            if drift > max_drift:
                max_drift = drift
                max_asset = asset

        return max_asset, max_drift


# ============================================================================
# 날짜/거래일 유틸리티
# ============================================================================

def get_month_start(d: date) -> date:
    """해당 월의 첫 번째 날"""
    return date(d.year, d.month, 1)


def get_month_end(d: date) -> date:
    """해당 월의 마지막 날"""
    if d.month == 12:
        return date(d.year, 12, 31)
    return date(d.year, d.month + 1, 1) - timedelta(days=1)


def get_quarter_start_month(d: date) -> int:
    """분기 시작 월 (1, 4, 7, 10)"""
    return ((d.month - 1) // 3) * 3 + 1


def is_first_trading_day_of_month(
    trade_date: date,
    trade_dates: List[date],
    trade_date_set: set
) -> bool:
    """해당 월의 첫 거래일인지 확인"""
    month_start = get_month_start(trade_date)

    # 현재 날짜가 해당 월의 첫 번째 거래일인지 확인
    for d in trade_dates:
        if d.year == month_start.year and d.month == month_start.month:
            return d == trade_date
        if d > trade_date:
            break

    return False


def is_last_trading_day_of_month(
    trade_date: date,
    trade_dates: List[date],
    trade_date_idx: int
) -> bool:
    """해당 월의 마지막 거래일인지 확인"""
    current_month = trade_date.month
    current_year = trade_date.year

    # 다음 거래일이 없거나 다른 월이면 마지막 거래일
    if trade_date_idx >= len(trade_dates) - 1:
        return True

    next_date = trade_dates[trade_date_idx + 1]
    return next_date.month != current_month or next_date.year != current_year


def is_first_trading_day_of_quarter(
    trade_date: date,
    trade_dates: List[date],
    trade_date_set: set
) -> bool:
    """해당 분기의 첫 거래일인지 확인 (1/4/7/10월 첫 거래일)"""
    quarter_start_month = get_quarter_start_month(trade_date)

    # 현재 월이 분기 시작 월이 아니면 False
    if trade_date.month != quarter_start_month:
        return False

    # 해당 월의 첫 거래일인지 확인
    return is_first_trading_day_of_month(trade_date, trade_dates, trade_date_set)


def is_last_trading_day_of_quarter(
    trade_date: date,
    trade_dates: List[date],
    trade_date_idx: int
) -> bool:
    """해당 분기의 마지막 거래일인지 확인 (3/6/9/12월 마지막 거래일)"""
    quarter_end_months = {3, 6, 9, 12}

    if trade_date.month not in quarter_end_months:
        return False

    return is_last_trading_day_of_month(trade_date, trade_dates, trade_date_idx)


# ============================================================================
# 리밸런싱 엔진
# ============================================================================

class RebalancingEngine:
    """
    리밸런싱 엔진

    시뮬레이션 경로 계산 과정에서 리밸런싱을 적용합니다.
    """

    def __init__(self, config: RebalancingConfig):
        """
        Args:
            config: 리밸런싱 설정
        """
        self.config = config
        self.events: List[RebalancingEvent] = []
        self._event_order = 0

    def check_trigger(
        self,
        trade_date: date,
        trade_date_idx: int,
        trade_dates: List[date],
        trade_date_set: set,
        position: PositionState
    ) -> Optional[Tuple[str, str]]:
        """
        리밸런싱 트리거 체크

        Args:
            trade_date: 현재 거래일
            trade_date_idx: 거래일 인덱스
            trade_dates: 전체 거래일 목록
            trade_date_set: 거래일 집합 (빠른 조회용)
            position: 현재 포지션 상태

        Returns:
            (trigger_type, trigger_detail) 또는 None
        """
        if not self.config.is_enabled():
            return None

        # 1. PERIODIC 체크 (HYBRID에서도 PERIODIC 우선)
        if self.config.is_periodic():
            periodic_trigger = self._check_periodic_trigger(
                trade_date, trade_date_idx, trade_dates, trade_date_set
            )
            if periodic_trigger:
                return periodic_trigger

        # 2. DRIFT 체크
        if self.config.is_drift_based():
            drift_trigger = self._check_drift_trigger(position)
            if drift_trigger:
                return drift_trigger

        return None

    def _check_periodic_trigger(
        self,
        trade_date: date,
        trade_date_idx: int,
        trade_dates: List[date],
        trade_date_set: set
    ) -> Optional[Tuple[str, str]]:
        """PERIODIC 리밸런싱 트리거 체크"""
        frequency = self.config.frequency
        timing = self.config.periodic_timing

        if frequency == "MONTHLY":
            if timing == "START":
                if is_first_trading_day_of_month(trade_date, trade_dates, trade_date_set):
                    return ("PERIODIC", "MONTHLY")
            else:  # END
                if is_last_trading_day_of_month(trade_date, trade_dates, trade_date_idx):
                    return ("PERIODIC", "MONTHLY")

        elif frequency == "QUARTERLY":
            if timing == "START":
                if is_first_trading_day_of_quarter(trade_date, trade_dates, trade_date_set):
                    return ("PERIODIC", "QUARTERLY")
            else:  # END
                if is_last_trading_day_of_quarter(trade_date, trade_dates, trade_date_idx):
                    return ("PERIODIC", "QUARTERLY")

        return None

    def _check_drift_trigger(
        self,
        position: PositionState
    ) -> Optional[Tuple[str, str]]:
        """DRIFT 리밸런싱 트리거 체크"""
        threshold = self.config.drift_threshold
        if threshold is None:
            return None

        _, max_drift = position.get_max_drift()
        if max_drift >= threshold:
            return ("DRIFT", f"DRIFT>={threshold:.2%}")

        return None

    def execute_rebalance(
        self,
        trade_date: date,
        trigger_type: str,
        trigger_detail: str,
        position: PositionState
    ) -> RebalancingEvent:
        """
        리밸런싱 실행

        Args:
            trade_date: 리밸런싱 일자
            trigger_type: 트리거 타입 (PERIODIC/DRIFT)
            trigger_detail: 트리거 상세
            position: 현재 포지션 상태 (in-place 수정됨)

        Returns:
            리밸런싱 이벤트
        """
        self._event_order += 1

        # 1. Before 상태 기록
        nav_before = position.get_total_value()
        before_weights = position.get_current_weights()

        # 2. Turnover 계산
        turnover = self._calculate_turnover(position)

        # 3. 비용 팩터 계산
        cost_factor = 1.0 - turnover * self.config.cost_rate

        # 4. 비용 반영 후 NAV
        nav_after = nav_before * cost_factor

        # 5. 포지션 재조정 (목표 비중으로)
        for asset in position.values:
            target_weight = position.target_weights.get(asset, 0.0)
            position.values[asset] = nav_after * target_weight

        # 6. After 상태 기록
        after_weights = position.get_current_weights()

        # 7. 이벤트 생성
        event = RebalancingEvent(
            event_date=trade_date,
            event_order=self._event_order,
            trigger_type=trigger_type,
            trigger_detail=trigger_detail,
            before_weights=before_weights,
            after_weights=after_weights,
            turnover=turnover,
            cost_rate=self.config.cost_rate,
            cost_factor=cost_factor,
            nav_before=nav_before,
            nav_after=nav_after,
            rule_id=self.config.rule_id,
        )

        self.events.append(event)
        return event

    def _calculate_turnover(self, position: PositionState) -> float:
        """
        회전율 계산

        turnover = 0.5 * sum(|after_value - before_value|) / V
        """
        total_value = position.get_total_value()
        if total_value <= 0:
            return 0.0

        current_weights = position.get_current_weights()
        target_weights = position.target_weights

        total_change = 0.0
        for asset in set(current_weights.keys()) | set(target_weights.keys()):
            current_w = current_weights.get(asset, 0.0)
            target_w = target_weights.get(asset, 0.0)
            total_change += abs(target_w - current_w) * total_value

        # 매수/매도 중복 고려하여 0.5 곱
        turnover = 0.5 * total_change / total_value

        return turnover

    def get_events(self) -> List[RebalancingEvent]:
        """발생한 리밸런싱 이벤트 목록"""
        return self.events

    def reset(self):
        """엔진 상태 초기화"""
        self.events = []
        self._event_order = 0


# ============================================================================
# 리밸런싱 적용 NAV 경로 계산
# ============================================================================

def calculate_nav_with_rebalancing(
    allocations: List[Dict],
    returns_by_instrument: Dict[int, List[Dict]],
    trade_dates: List[date],
    initial_amount: float,
    rebalancing_config: RebalancingConfig
) -> Tuple[List[Dict], List[RebalancingEvent]]:
    """
    리밸런싱을 적용한 NAV 경로 계산

    Args:
        allocations: 포트폴리오 구성비 [{"instrument_id", "ticker", "weight", "asset_class"}, ...]
        returns_by_instrument: 종목별 일간수익률 {instrument_id: [{"trade_date", "daily_return"}, ...]}
        trade_dates: 거래일 목록
        initial_amount: 초기 투자금액
        rebalancing_config: 리밸런싱 설정

    Returns:
        (NAV 경로, 리밸런싱 이벤트 목록)
    """
    if not allocations or not trade_dates:
        return [], []

    # 종목별 수익률을 날짜 인덱스로 변환
    returns_lookup: Dict[int, Dict[date, float]] = {}
    for inst_id, returns in returns_by_instrument.items():
        returns_lookup[inst_id] = {
            r["trade_date"]: r["daily_return"]
            for r in returns
        }

    # 자산군별 종목 그룹핑 및 목표 비중 계산
    asset_class_instruments: Dict[str, List[Dict]] = {}
    target_weights: Dict[str, float] = {}

    for alloc in allocations:
        asset_class = alloc.get("asset_class") or "OTHER"
        if asset_class not in asset_class_instruments:
            asset_class_instruments[asset_class] = []
            target_weights[asset_class] = 0.0
        asset_class_instruments[asset_class].append(alloc)
        target_weights[asset_class] += alloc["weight"]

    # 초기 포지션 설정
    position = PositionState(
        values={ac: initial_amount * w for ac, w in target_weights.items()},
        target_weights=target_weights
    )

    # 리밸런싱 엔진 초기화
    engine = RebalancingEngine(rebalancing_config)

    # 거래일 집합 (빠른 조회용)
    trade_date_set = set(trade_dates)

    # NAV 경로 계산
    path = []
    high_water_mark = initial_amount

    for idx, trade_date in enumerate(trade_dates):
        # 1. 일간 수익률 반영
        for asset_class, instruments in asset_class_instruments.items():
            asset_return = 0.0
            total_weight_in_class = sum(a["weight"] for a in instruments)

            for alloc in instruments:
                inst_id = alloc["instrument_id"]
                inst_weight = alloc["weight"] / total_weight_in_class if total_weight_in_class > 0 else 0.0
                inst_return = returns_lookup.get(inst_id, {}).get(trade_date, 0.0)
                asset_return += inst_weight * inst_return

            # 자산군 평가금액 업데이트
            position.values[asset_class] *= (1 + asset_return)

        # 2. 리밸런싱 트리거 체크
        trigger = engine.check_trigger(
            trade_date, idx, trade_dates, trade_date_set, position
        )

        # 3. 리밸런싱 실행
        if trigger:
            trigger_type, trigger_detail = trigger
            engine.execute_rebalance(trade_date, trigger_type, trigger_detail, position)

        # 4. NAV 및 지표 계산
        nav = position.get_total_value()
        prev_nav = path[-1]["nav"] if path else initial_amount
        daily_return = (nav - prev_nav) / prev_nav if prev_nav > 0 else 0.0

        if nav > high_water_mark:
            high_water_mark = nav
        drawdown = (nav - high_water_mark) / high_water_mark if high_water_mark > 0 else 0.0
        cumulative_return = (nav - initial_amount) / initial_amount if initial_amount > 0 else 0.0

        path.append({
            "path_date": trade_date,
            "nav": round(nav, 4),
            "daily_return": round(daily_return, 8),
            "cumulative_return": round(cumulative_return, 8),
            "drawdown": round(drawdown, 8),
            "high_water_mark": round(high_water_mark, 4),
        })

    return path, engine.get_events()


def create_rebalancing_config_for_hash(config: RebalancingConfig) -> Dict:
    """
    request_hash 생성을 위한 리밸런싱 설정 dict

    캐시 키에 포함될 리밸런싱 관련 파라미터
    """
    return {
        "rebalance_type": config.rebalance_type,
        "frequency": config.frequency,
        "periodic_timing": config.periodic_timing,
        "drift_threshold": config.drift_threshold,
        "cost_rate": config.cost_rate,
        "rule_id": config.rule_id,
    }
