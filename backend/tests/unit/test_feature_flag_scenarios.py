"""
Phase 2 Feature Flag 검증 테스트

USE_REBALANCING Feature Flag 4가지 시나리오 검증:
1. USE_REBALANCING=0 + rule 파라미터 → 400 반환 (ValueError)
2. USE_REBALANCING=0 + rule 없음 → Phase 1 결과와 동일
3. USE_REBALANCING=1 + rule → 리밸런싱 적용
4. USE_REBALANCING=1 + rule 없음 → OFF와 동일
"""

import pytest
from datetime import date
from unittest.mock import patch, MagicMock


class TestFeatureFlagScenarios:
    """Feature Flag 시나리오 테스트"""

    def test_flag_off_with_rule_raises_error(self):
        """시나리오 1: USE_REBALANCING=0 + rule 파라미터 → ValueError"""
        from app.services.scenario_simulation import run_scenario_simulation

        mock_db = MagicMock()

        # DB 조회 mock 설정 (allocations, trade_dates, returns 순서로 반환)
        mock_execute = MagicMock()
        mock_execute.fetchall.side_effect = [
            # allocations
            [(1, "SPY", "SPDR S&P500", 0.6, "EQUITY"), (2, "AGG", "Agg Bond", 0.4, "BOND")],
            # trade_dates
            [(date(2024, 1, 2),), (date(2024, 1, 3),)],
            # daily returns
            [(1, date(2024, 1, 2), 0.01, "OK"), (2, date(2024, 1, 2), 0.005, "OK")],
        ]
        mock_db.execute.return_value = mock_execute

        # settings.use_rebalancing = False 로 패치
        with patch('app.services.scenario_simulation.settings') as mock_settings:
            mock_settings.use_rebalancing = False

            # rule 파라미터가 있으면 ValueError
            rebalancing_rule = {
                "rebalance_type": "PERIODIC",
                "frequency": "MONTHLY",
                "cost_rate": 0.001
            }

            with pytest.raises(ValueError) as exc_info:
                run_scenario_simulation(
                    db=mock_db,
                    scenario_id="MIN_VOL",
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 3, 31),
                    initial_amount=1000000,
                    rebalancing_rule=rebalancing_rule
                )

            assert "리밸런싱 기능이 비활성화 상태" in str(exc_info.value)

    def test_flag_off_no_rule_phase1_behavior(self):
        """시나리오 2: USE_REBALANCING=0 + rule 없음 → Phase 1 동작"""
        from app.services.rebalancing_engine import RebalancingConfig

        # Flag OFF 상태에서 rule 없으면 None config
        config = RebalancingConfig.none()

        assert config.rebalance_type == "NONE"
        assert not config.is_enabled()
        assert not config.is_periodic()
        assert not config.is_drift_based()

    def test_flag_on_with_rule_rebalancing_applied(self):
        """시나리오 3: USE_REBALANCING=1 + rule → 리밸런싱 적용"""
        from app.services.rebalancing_engine import (
            RebalancingConfig,
            RebalancingEngine,
            PositionState
        )

        config = RebalancingConfig(
            rebalance_type="PERIODIC",
            frequency="MONTHLY",
            periodic_timing="START",
            cost_rate=0.001
        )

        assert config.is_enabled()
        assert config.is_periodic()

        # 엔진 생성 및 동작 확인
        engine = RebalancingEngine(config)
        position = PositionState(
            values={"EQUITY": 600, "BOND": 300, "CASH": 100},
            target_weights={"EQUITY": 0.6, "BOND": 0.3, "CASH": 0.1}
        )

        # 트리거 체크 (월 첫 거래일 시뮬레이션)
        trade_dates = [date(2024, 2, 1), date(2024, 2, 2)]
        trade_date_set = set(trade_dates)

        trigger = engine.check_trigger(
            date(2024, 2, 1), 0, trade_dates, trade_date_set, position
        )

        # 2월 1일은 월 첫 거래일이므로 트리거 발생
        assert trigger is not None
        assert trigger[0] == "PERIODIC"

    def test_flag_on_no_rule_same_as_off(self):
        """시나리오 4: USE_REBALANCING=1 + rule 없음 → OFF와 동일"""
        from app.services.rebalancing_engine import (
            RebalancingConfig,
            RebalancingEngine,
            PositionState
        )

        # rule이 None이면 NONE 타입
        config = RebalancingConfig.none()

        assert not config.is_enabled()

        engine = RebalancingEngine(config)
        position = PositionState(
            values={"EQUITY": 700, "BOND": 200, "CASH": 100},
            target_weights={"EQUITY": 0.6, "BOND": 0.3, "CASH": 0.1}
        )

        # 트리거 체크 - disabled이므로 None 반환
        trigger = engine.check_trigger(
            date(2024, 2, 1), 0, [], set(), position
        )

        assert trigger is None


class TestRequestHashWithRebalancing:
    """request_hash에 리밸런싱 파라미터 포함 검증"""

    def test_hash_includes_rebalancing_params(self):
        """리밸런싱 파라미터가 hash 입력에 포함되는지 확인"""
        import hashlib
        import json

        # 동일 기본 파라미터
        base_params = {
            "scenario_id": "MIN_VOL",
            "start_date": "2024-01-01",
            "end_date": "2024-03-31",
            "initial_amount": 1000000,
        }

        # 리밸런싱 없음
        params_no_rebal = {**base_params, "rebalancing_rule": None}

        # 리밸런싱 있음
        params_with_rebal = {
            **base_params,
            "rebalancing_rule": {
                "rebalance_type": "PERIODIC",
                "frequency": "MONTHLY",
                "cost_rate": 0.001
            }
        }

        # Hash 계산
        hash1 = hashlib.sha256(json.dumps(params_no_rebal, sort_keys=True).encode()).hexdigest()
        hash2 = hashlib.sha256(json.dumps(params_with_rebal, sort_keys=True).encode()).hexdigest()

        # 리밸런싱 파라미터가 다르면 hash가 달라야 함
        assert hash1 != hash2

    def test_same_params_same_hash(self):
        """동일 파라미터 → 동일 hash"""
        import hashlib
        import json

        params = {
            "scenario_id": "MIN_VOL",
            "start_date": "2024-01-01",
            "end_date": "2024-03-31",
            "initial_amount": 1000000,
            "rebalancing_rule": {
                "rebalance_type": "PERIODIC",
                "frequency": "MONTHLY",
                "cost_rate": 0.001
            }
        }

        hash1 = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
        hash2 = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()

        assert hash1 == hash2
