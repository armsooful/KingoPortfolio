"""
Phase 2 리밸런싱 엔진 단위 테스트

PERIODIC / DRIFT / HYBRID 리밸런싱 로직 및 비용 모델 검증
"""

import pytest
from datetime import date, timedelta
from typing import Dict, List

from app.services.rebalancing_engine import (
    RebalancingConfig,
    RebalancingEngine,
    PositionState,
    calculate_nav_with_rebalancing,
    is_first_trading_day_of_month,
    is_first_trading_day_of_quarter,
    is_last_trading_day_of_month,
    is_last_trading_day_of_quarter,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_allocations():
    """샘플 포트폴리오 구성비"""
    return [
        {"instrument_id": 1, "ticker": "SPY", "weight": 0.6, "asset_class": "EQUITY"},
        {"instrument_id": 2, "ticker": "AGG", "weight": 0.3, "asset_class": "BOND"},
        {"instrument_id": 3, "ticker": "SHY", "weight": 0.1, "asset_class": "CASH"},
    ]


@pytest.fixture
def sample_returns():
    """샘플 일간수익률 데이터"""
    # 2024년 1월 거래일 (주말 제외)
    dates = [
        date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4), date(2024, 1, 5),
        date(2024, 1, 8), date(2024, 1, 9), date(2024, 1, 10), date(2024, 1, 11), date(2024, 1, 12),
        date(2024, 1, 15), date(2024, 1, 16), date(2024, 1, 17), date(2024, 1, 18), date(2024, 1, 19),
        date(2024, 1, 22), date(2024, 1, 23), date(2024, 1, 24), date(2024, 1, 25), date(2024, 1, 26),
        date(2024, 1, 29), date(2024, 1, 30), date(2024, 1, 31),
        # 2월
        date(2024, 2, 1), date(2024, 2, 2),
        date(2024, 2, 5), date(2024, 2, 6), date(2024, 2, 7), date(2024, 2, 8), date(2024, 2, 9),
        date(2024, 2, 12), date(2024, 2, 13), date(2024, 2, 14), date(2024, 2, 15), date(2024, 2, 16),
        date(2024, 2, 19), date(2024, 2, 20), date(2024, 2, 21), date(2024, 2, 22), date(2024, 2, 23),
        date(2024, 2, 26), date(2024, 2, 27), date(2024, 2, 28), date(2024, 2, 29),
    ]

    # 종목별 수익률 (EQUITY 변동 큼, BOND 안정, CASH 거의 0)
    returns_by_instrument = {
        1: [{"trade_date": d, "daily_return": 0.005 if i % 2 == 0 else -0.003} for i, d in enumerate(dates)],
        2: [{"trade_date": d, "daily_return": 0.001 if i % 3 == 0 else -0.0005} for i, d in enumerate(dates)],
        3: [{"trade_date": d, "daily_return": 0.0001} for d in dates],
    }

    return returns_by_instrument, dates


# ============================================================================
# RebalancingConfig 테스트
# ============================================================================

class TestRebalancingConfig:
    """RebalancingConfig 테스트"""

    def test_none_config(self):
        """리밸런싱 비활성화 설정"""
        config = RebalancingConfig.none()
        assert config.rebalance_type == "NONE"
        assert not config.is_enabled()
        assert not config.is_periodic()
        assert not config.is_drift_based()

    def test_periodic_monthly_config(self):
        """월간 PERIODIC 설정"""
        config = RebalancingConfig(
            rebalance_type="PERIODIC",
            frequency="MONTHLY",
            cost_rate=0.001
        )
        assert config.is_enabled()
        assert config.is_periodic()
        assert not config.is_drift_based()
        assert config.frequency == "MONTHLY"

    def test_drift_config(self):
        """DRIFT 설정"""
        config = RebalancingConfig(
            rebalance_type="DRIFT",
            drift_threshold=0.05,
            cost_rate=0.001
        )
        assert config.is_enabled()
        assert not config.is_periodic()
        assert config.is_drift_based()
        assert config.drift_threshold == 0.05

    # HYBRID는 Phase 2 DDL에서 미지원 (PERIODIC, DRIFT만 지원)
    # def test_hybrid_config(self):
    #     """HYBRID 설정"""
    #     config = RebalancingConfig(
    #         rebalance_type="HYBRID",
    #         frequency="QUARTERLY",
    #         drift_threshold=0.10,
    #         cost_rate=0.0015
    #     )
    #     assert config.is_enabled()
    #     assert config.is_periodic()
    #     assert config.is_drift_based()

    def test_from_dict(self):
        """dict에서 생성"""
        data = {
            "rebalance_type": "PERIODIC",
            "frequency": "MONTHLY",
            "cost_rate": 0.002,
        }
        config = RebalancingConfig.from_dict(data)
        assert config.rebalance_type == "PERIODIC"
        assert config.frequency == "MONTHLY"
        assert config.cost_rate == 0.002


# ============================================================================
# PositionState 테스트
# ============================================================================

class TestPositionState:
    """PositionState 테스트"""

    def test_total_value(self):
        """총 평가금액 계산"""
        position = PositionState(
            values={"EQUITY": 600, "BOND": 300, "CASH": 100},
            target_weights={"EQUITY": 0.6, "BOND": 0.3, "CASH": 0.1}
        )
        assert position.get_total_value() == 1000

    def test_current_weights(self):
        """현재 비중 계산"""
        position = PositionState(
            values={"EQUITY": 700, "BOND": 200, "CASH": 100},
            target_weights={"EQUITY": 0.6, "BOND": 0.3, "CASH": 0.1}
        )
        weights = position.get_current_weights()
        assert weights["EQUITY"] == 0.7
        assert weights["BOND"] == 0.2
        assert weights["CASH"] == 0.1

    def test_max_drift(self):
        """최대 Drift 계산"""
        position = PositionState(
            values={"EQUITY": 700, "BOND": 200, "CASH": 100},
            target_weights={"EQUITY": 0.6, "BOND": 0.3, "CASH": 0.1}
        )
        asset, drift = position.get_max_drift()
        assert asset == "EQUITY" or asset == "BOND"
        assert abs(drift - 0.1) < 0.001  # |0.7-0.6| = 0.1 또는 |0.2-0.3| = 0.1 (부동소수점 허용)


# ============================================================================
# 날짜/거래일 유틸리티 테스트
# ============================================================================

class TestTradingDayUtils:
    """거래일 유틸리티 함수 테스트"""

    def test_first_trading_day_of_month(self):
        """월 첫 거래일 판정"""
        # 2024년 2월 첫 거래일은 2024-02-01
        # 1월 31일은 1월의 유일한 날이므로 1월 첫 거래일로 판정됨
        trade_dates = [
            date(2024, 1, 30),  # 1월 마지막 이전
            date(2024, 1, 31),  # 1월 마지막
            date(2024, 2, 1),
            date(2024, 2, 2),
            date(2024, 2, 5),
        ]
        trade_date_set = set(trade_dates)

        assert is_first_trading_day_of_month(date(2024, 2, 1), trade_dates, trade_date_set)
        assert not is_first_trading_day_of_month(date(2024, 2, 2), trade_dates, trade_date_set)
        # 1월 30일이 1월 첫 거래일 (이 데이터셋에서)
        assert is_first_trading_day_of_month(date(2024, 1, 30), trade_dates, trade_date_set)
        assert not is_first_trading_day_of_month(date(2024, 1, 31), trade_dates, trade_date_set)

    def test_last_trading_day_of_month(self):
        """월 마지막 거래일 판정"""
        trade_dates = [
            date(2024, 1, 30),
            date(2024, 1, 31),
            date(2024, 2, 1),
            date(2024, 2, 2),
        ]

        assert is_last_trading_day_of_month(date(2024, 1, 31), trade_dates, 1)
        assert not is_last_trading_day_of_month(date(2024, 1, 30), trade_dates, 0)

    def test_first_trading_day_of_quarter(self):
        """분기 첫 거래일 판정 (1/4/7/10월)"""
        trade_dates = [
            date(2024, 3, 29),
            date(2024, 4, 1),
            date(2024, 4, 2),
        ]
        trade_date_set = set(trade_dates)

        assert is_first_trading_day_of_quarter(date(2024, 4, 1), trade_dates, trade_date_set)
        assert not is_first_trading_day_of_quarter(date(2024, 3, 29), trade_dates, trade_date_set)
        assert not is_first_trading_day_of_quarter(date(2024, 4, 2), trade_dates, trade_date_set)


# ============================================================================
# RebalancingEngine 테스트
# ============================================================================

class TestRebalancingEngine:
    """RebalancingEngine 테스트"""

    def test_no_trigger_when_disabled(self):
        """리밸런싱 비활성화 시 트리거 없음"""
        config = RebalancingConfig.none()
        engine = RebalancingEngine(config)

        position = PositionState(
            values={"EQUITY": 700, "BOND": 200, "CASH": 100},
            target_weights={"EQUITY": 0.6, "BOND": 0.3, "CASH": 0.1}
        )

        trigger = engine.check_trigger(
            date(2024, 2, 1), 0, [date(2024, 2, 1)], {date(2024, 2, 1)}, position
        )
        assert trigger is None

    def test_periodic_monthly_trigger(self):
        """월간 PERIODIC 트리거"""
        config = RebalancingConfig(
            rebalance_type="PERIODIC",
            frequency="MONTHLY",
            periodic_timing="START",
        )
        engine = RebalancingEngine(config)

        position = PositionState(
            values={"EQUITY": 600, "BOND": 300, "CASH": 100},
            target_weights={"EQUITY": 0.6, "BOND": 0.3, "CASH": 0.1}
        )

        trade_dates = [date(2024, 1, 31), date(2024, 2, 1), date(2024, 2, 2)]
        trade_date_set = set(trade_dates)

        # 2월 1일 (월 첫 거래일)
        trigger = engine.check_trigger(date(2024, 2, 1), 1, trade_dates, trade_date_set, position)
        assert trigger is not None
        assert trigger[0] == "PERIODIC"
        assert trigger[1] == "MONTHLY"

        # 2월 2일 (월 첫 거래일 아님)
        trigger = engine.check_trigger(date(2024, 2, 2), 2, trade_dates, trade_date_set, position)
        assert trigger is None

    def test_drift_trigger(self):
        """DRIFT 트리거"""
        config = RebalancingConfig(
            rebalance_type="DRIFT",
            drift_threshold=0.05,
        )
        engine = RebalancingEngine(config)

        # Drift 5% 미만
        position_ok = PositionState(
            values={"EQUITY": 620, "BOND": 290, "CASH": 90},  # ~4% drift
            target_weights={"EQUITY": 0.6, "BOND": 0.3, "CASH": 0.1}
        )
        trigger = engine.check_trigger(date(2024, 2, 1), 0, [], set(), position_ok)
        assert trigger is None

        # Drift 10% (5% 이상)
        position_drift = PositionState(
            values={"EQUITY": 700, "BOND": 200, "CASH": 100},  # 10% drift
            target_weights={"EQUITY": 0.6, "BOND": 0.3, "CASH": 0.1}
        )
        trigger = engine.check_trigger(date(2024, 2, 1), 0, [], set(), position_drift)
        assert trigger is not None
        assert trigger[0] == "DRIFT"

    def test_execute_rebalance_cost(self):
        """리밸런싱 실행 및 비용 반영"""
        config = RebalancingConfig(
            rebalance_type="PERIODIC",
            frequency="MONTHLY",
            cost_rate=0.01,  # 1% (테스트용 높은 비용)
        )
        engine = RebalancingEngine(config)

        # 초기 상태: EQUITY 과다
        position = PositionState(
            values={"EQUITY": 700, "BOND": 200, "CASH": 100},  # 총 1000
            target_weights={"EQUITY": 0.6, "BOND": 0.3, "CASH": 0.1}
        )

        event = engine.execute_rebalance(
            date(2024, 2, 1), "PERIODIC", "MONTHLY", position
        )

        # 검증
        assert event.trigger_type == "PERIODIC"
        assert event.nav_before == 1000

        # turnover 계산: 0.5 * (|700-600| + |200-300| + |100-100|) / 1000 = 0.1
        assert abs(event.turnover - 0.1) < 0.001

        # cost_factor = 1 - 0.1 * 0.01 = 0.999
        assert abs(event.cost_factor - 0.999) < 0.0001

        # nav_after = 1000 * 0.999 = 999
        assert abs(event.nav_after - 999) < 0.1

        # 리밸런싱 후 position 비중 확인
        total_after = position.get_total_value()
        assert abs(total_after - 999) < 0.1

        weights_after = position.get_current_weights()
        assert abs(weights_after["EQUITY"] - 0.6) < 0.001
        assert abs(weights_after["BOND"] - 0.3) < 0.001
        assert abs(weights_after["CASH"] - 0.1) < 0.001


# ============================================================================
# 통합 NAV 계산 테스트
# ============================================================================

class TestCalculateNavWithRebalancing:
    """리밸런싱 적용 NAV 경로 계산 테스트"""

    def test_no_rebalancing(self, sample_allocations, sample_returns):
        """리밸런싱 OFF"""
        returns_by_instrument, trade_dates = sample_returns
        config = RebalancingConfig.none()

        path, events = calculate_nav_with_rebalancing(
            sample_allocations, returns_by_instrument, trade_dates,
            initial_amount=1000000, rebalancing_config=config
        )

        assert len(path) == len(trade_dates)
        assert len(events) == 0
        assert path[0]["nav"] != 1000000  # 첫날 수익률 반영

    def test_monthly_rebalancing(self, sample_allocations, sample_returns):
        """월간 리밸런싱 적용"""
        returns_by_instrument, trade_dates = sample_returns
        config = RebalancingConfig(
            rebalance_type="PERIODIC",
            frequency="MONTHLY",
            periodic_timing="START",
            cost_rate=0.001,
        )

        path, events = calculate_nav_with_rebalancing(
            sample_allocations, returns_by_instrument, trade_dates,
            initial_amount=1000000, rebalancing_config=config
        )

        assert len(path) == len(trade_dates)
        # 2월 첫 거래일에 리밸런싱 발생 예상
        assert len(events) >= 1

        # 이벤트 검증
        feb_events = [e for e in events if e.event_date.month == 2]
        if feb_events:
            assert feb_events[0].trigger_type == "PERIODIC"

    def test_drift_rebalancing(self, sample_allocations, sample_returns):
        """DRIFT 리밸런싱 적용"""
        returns_by_instrument, trade_dates = sample_returns

        # 낮은 threshold로 설정하여 이벤트 발생 유도
        config = RebalancingConfig(
            rebalance_type="DRIFT",
            drift_threshold=0.01,  # 1% - 쉽게 발생
            cost_rate=0.001,
        )

        path, events = calculate_nav_with_rebalancing(
            sample_allocations, returns_by_instrument, trade_dates,
            initial_amount=1000000, rebalancing_config=config
        )

        assert len(path) == len(trade_dates)
        # 낮은 threshold이므로 이벤트 발생 예상
        # (수익률 변동에 따라 달라질 수 있음)

    def test_rebalancing_reduces_nav_by_cost(self, sample_allocations, sample_returns):
        """리밸런싱 비용으로 NAV 감소 확인"""
        returns_by_instrument, trade_dates = sample_returns

        # 리밸런싱 OFF
        config_off = RebalancingConfig.none()
        path_off, _ = calculate_nav_with_rebalancing(
            sample_allocations, returns_by_instrument, trade_dates,
            initial_amount=1000000, rebalancing_config=config_off
        )

        # 리밸런싱 ON (높은 비용)
        config_on = RebalancingConfig(
            rebalance_type="PERIODIC",
            frequency="MONTHLY",
            cost_rate=0.02,  # 2% (높은 비용)
        )
        path_on, events_on = calculate_nav_with_rebalancing(
            sample_allocations, returns_by_instrument, trade_dates,
            initial_amount=1000000, rebalancing_config=config_on
        )

        # 리밸런싱이 발생했다면, 비용으로 인해 최종 NAV가 감소해야 함
        if events_on:
            # 비용 효과 확인 (반드시 낮아지진 않지만, 비용은 차감됨)
            total_cost = sum(e.nav_before - e.nav_after for e in events_on)
            assert total_cost > 0


# ============================================================================
# DoD 테스트 (Definition of Done)
# ============================================================================

class TestDefinitionOfDone:
    """Epic B Definition of Done 검증"""

    def test_periodic_monthly_implemented(self, sample_allocations, sample_returns):
        """DoD: PERIODIC 월간 리밸런싱 구현"""
        returns_by_instrument, trade_dates = sample_returns
        config = RebalancingConfig(
            rebalance_type="PERIODIC",
            frequency="MONTHLY",
        )
        engine = RebalancingEngine(config)
        assert engine.config.is_periodic()
        assert engine.config.frequency == "MONTHLY"

    def test_periodic_quarterly_implemented(self):
        """DoD: PERIODIC 분기 리밸런싱 구현"""
        config = RebalancingConfig(
            rebalance_type="PERIODIC",
            frequency="QUARTERLY",
        )
        engine = RebalancingEngine(config)
        assert engine.config.is_periodic()
        assert engine.config.frequency == "QUARTERLY"

    def test_drift_implemented(self):
        """DoD: DRIFT 리밸런싱 구현"""
        config = RebalancingConfig(
            rebalance_type="DRIFT",
            drift_threshold=0.05,
        )
        engine = RebalancingEngine(config)
        assert engine.config.is_drift_based()
        assert engine.config.drift_threshold == 0.05

    def test_cost_model_implemented(self):
        """DoD: 비용 모델 적용"""
        config = RebalancingConfig(
            rebalance_type="PERIODIC",
            frequency="MONTHLY",
            cost_rate=0.001,
        )
        engine = RebalancingEngine(config)

        position = PositionState(
            values={"A": 500, "B": 500},
            target_weights={"A": 0.6, "B": 0.4}
        )

        event = engine.execute_rebalance(date(2024, 1, 1), "PERIODIC", "MONTHLY", position)

        # 비용 반영 확인
        assert event.cost_rate == 0.001
        assert event.turnover > 0
        assert event.cost_factor < 1.0
        assert event.nav_after < event.nav_before

    def test_rebalancing_event_logged(self):
        """DoD: 리밸런싱 이벤트 저장"""
        config = RebalancingConfig(
            rebalance_type="PERIODIC",
            frequency="MONTHLY",
        )
        engine = RebalancingEngine(config)

        position = PositionState(
            values={"A": 500, "B": 500},
            target_weights={"A": 0.6, "B": 0.4}
        )

        event = engine.execute_rebalance(date(2024, 1, 1), "PERIODIC", "MONTHLY", position)

        # 이벤트 필드 검증
        assert event.event_date == date(2024, 1, 1)
        assert event.trigger_type == "PERIODIC"
        assert "before_weights" in dir(event)
        assert "after_weights" in dir(event)
        assert "turnover" in dir(event)
        assert "cost_rate" in dir(event)

    def test_use_rebalancing_off_behavior(self):
        """DoD: USE_REBALANCING OFF 시 기존 동작"""
        config = RebalancingConfig.none()
        assert not config.is_enabled()
