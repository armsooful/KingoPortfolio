"""
시나리오 API 스모크 테스트
- GET /scenarios 200 + 스키마 검증
- GET /scenarios/{id} 200 + 스키마 검증
"""

import pytest
from fastapi.testclient import TestClient


class TestScenariosAPI:
    """시나리오 API 계약 검증"""

    def test_get_scenarios_returns_200(self, client: TestClient):
        """GET /scenarios는 200을 반환해야 함"""
        response = client.get("/scenarios")
        assert response.status_code == 200

    def test_get_scenarios_returns_list(self, client: TestClient):
        """GET /scenarios는 리스트를 반환해야 함"""
        response = client.get("/scenarios")
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0  # 최소 하나의 시나리오 존재

    def test_scenarios_list_schema(self, client: TestClient):
        """시나리오 목록 스키마 검증"""
        response = client.get("/scenarios")
        data = response.json()

        required_fields = ["id", "name", "name_ko", "short_description"]

        for scenario in data:
            for field in required_fields:
                assert field in scenario, f"Missing field: {field}"
                assert scenario[field] is not None, f"Field is None: {field}"

    def test_get_scenario_detail_returns_200(self, client: TestClient):
        """GET /scenarios/{id}는 200을 반환해야 함"""
        # 먼저 목록에서 ID 가져오기
        list_response = client.get("/scenarios")
        scenarios = list_response.json()
        scenario_id = scenarios[0]["id"]

        response = client.get(f"/scenarios/{scenario_id}")
        assert response.status_code == 200

    def test_scenario_detail_schema(self, client: TestClient):
        """시나리오 상세 스키마 검증"""
        response = client.get("/scenarios/MIN_VOL")
        assert response.status_code == 200

        data = response.json()

        # 필수 최상위 필드
        required_fields = [
            "id", "name", "name_ko", "description", "objective",
            "target_investor", "allocation", "risk_metrics",
            "disclaimer", "learning_points"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        # allocation 스키마 검증
        allocation = data["allocation"]
        allocation_fields = ["stocks", "bonds", "money_market", "gold", "other"]
        for field in allocation_fields:
            assert field in allocation, f"Missing allocation field: {field}"
            assert isinstance(allocation[field], (int, float))
            assert 0 <= allocation[field] <= 100

        # risk_metrics 스키마 검증
        risk_metrics = data["risk_metrics"]
        risk_fields = ["expected_volatility", "historical_max_drawdown", "recovery_expectation"]
        for field in risk_fields:
            assert field in risk_metrics, f"Missing risk_metrics field: {field}"
            assert isinstance(risk_metrics[field], str)

        # learning_points는 리스트
        assert isinstance(data["learning_points"], list)
        assert len(data["learning_points"]) > 0

    def test_invalid_scenario_returns_404(self, client: TestClient):
        """존재하지 않는 시나리오는 404 반환"""
        response = client.get("/scenarios/INVALID_SCENARIO")
        assert response.status_code == 404

    def test_allocation_sums_to_100(self, client: TestClient):
        """자산 배분 합계가 100%인지 검증"""
        response = client.get("/scenarios")
        scenarios = response.json()

        for scenario_summary in scenarios:
            detail_response = client.get(f"/scenarios/{scenario_summary['id']}")
            detail = detail_response.json()

            allocation = detail["allocation"]
            total = sum([
                allocation["stocks"],
                allocation["bonds"],
                allocation["money_market"],
                allocation["gold"],
                allocation["other"]
            ])
            assert total == 100, f"Allocation doesn't sum to 100 for {scenario_summary['id']}: {total}"

    def test_disclaimer_exists(self, client: TestClient):
        """모든 시나리오에 면책조항이 있어야 함"""
        response = client.get("/scenarios")
        scenarios = response.json()

        for scenario_summary in scenarios:
            detail_response = client.get(f"/scenarios/{scenario_summary['id']}")
            detail = detail_response.json()

            assert "disclaimer" in detail
            assert len(detail["disclaimer"]) > 0
            # 면책조항에 핵심 문구가 포함되어야 함
            assert "교육" in detail["disclaimer"] or "학습" in detail["disclaimer"]
