"""
시뮬레이션 API 스모크 테스트
- POST /backtest/run 200 + top-level KPI 존재 (MDD/Recovery)
- POST /backtest/compare 200 + 비교 결과 스키마 검증
- GET /backtest/metrics/{type} 200 + 스키마 검증

Note: 이 테스트는 API 계약 검증에 초점을 맞춤
      실제 백테스팅 로직은 unit 테스트에서 별도로 검증
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


# 백테스트 모킹용 결과 데이터
MOCK_BACKTEST_RESULT = {
    "start_date": "2024-01-01T00:00:00",
    "end_date": "2025-01-01T00:00:00",
    "initial_investment": 10000000,
    "final_value": 10500000,
    "risk_metrics": {
        "max_drawdown": 8.5,
        "max_recovery_days": 45,
        "worst_1m_return": -5.2,
        "worst_3m_return": -7.8,
        "volatility": 12.3,
    },
    "historical_observation": {
        "total_return": 5.0,
        "cagr": 5.0,
        "sharpe_ratio": 0.85,
    },
    "total_return": 5.0,
    "annualized_return": 5.0,
    "volatility": 12.3,
    "sharpe_ratio": 0.85,
    "max_drawdown": 8.5,
    "daily_values": [],
    "rebalance_frequency": "quarterly",
    "number_of_rebalances": 4,
}


class TestBacktestAuthAndValidation:
    """백테스트 API 인증 및 입력 검증"""

    def test_backtest_run_requires_auth(self, client: TestClient):
        """백테스트는 인증이 필요함"""
        response = client.post(
            "/backtest/run",
            json={
                "investment_type": "conservative",
                "investment_amount": 10000000,
                "period_years": 1
            }
        )
        assert response.status_code == 401

    def test_backtest_run_validates_investment_type(self, client: TestClient, auth_headers: dict):
        """잘못된 investment_type은 400 반환"""
        response = client.post(
            "/backtest/run",
            json={
                "investment_type": "invalid_type",
                "investment_amount": 10000000,
                "period_years": 1
            },
            headers=auth_headers
        )
        assert response.status_code == 400

    def test_backtest_run_validates_investment_amount(self, client: TestClient, auth_headers: dict):
        """최소 투자금액 미만은 422 반환"""
        response = client.post(
            "/backtest/run",
            json={
                "investment_type": "conservative",
                "investment_amount": 1000,  # 최소 10만원
                "period_years": 1
            },
            headers=auth_headers
        )
        assert response.status_code == 422

    def test_backtest_run_requires_investment_type_or_portfolio(self, client: TestClient, auth_headers: dict):
        """investment_type 또는 portfolio 중 하나는 필수"""
        response = client.post(
            "/backtest/run",
            json={
                "investment_amount": 10000000,
                "period_years": 1
            },
            headers=auth_headers
        )
        assert response.status_code == 400

    def test_compare_requires_auth(self, client: TestClient):
        """비교 API는 인증이 필요함"""
        response = client.post(
            "/backtest/compare",
            json={
                "investment_types": ["conservative", "moderate"],
                "investment_amount": 10000000,
                "period_years": 1
            }
        )
        assert response.status_code == 401

    def test_metrics_requires_auth(self, client: TestClient):
        """메트릭 조회는 인증이 필요함"""
        response = client.get("/backtest/metrics/conservative")
        assert response.status_code == 401


class TestBacktestAPIContract:
    """백테스트 API 응답 계약 검증 (모킹 사용)"""

    @patch("app.routes.backtesting.get_or_compute")
    def test_backtest_run_response_schema(
        self, mock_get_or_compute, client: TestClient, auth_headers: dict
    ):
        """백테스트 응답 스키마 검증"""
        # 캐시 모킹
        mock_get_or_compute.return_value = (
            MOCK_BACKTEST_RESULT,  # result
            "abc123" * 10 + "abcd",  # request_hash (64자)
            False,  # cache_hit
            "1.0.0"  # engine_version
        )

        response = client.post(
            "/backtest/run",
            json={
                "investment_type": "moderate",
                "investment_amount": 10000000,
                "period_years": 1
            },
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()

        # 필수 최상위 필드
        required_fields = ["success", "data", "request_hash", "cache_hit", "engine_version", "message"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        assert data["success"] is True
        assert isinstance(data["request_hash"], str)
        assert len(data["request_hash"]) == 64  # SHA-256 해시
        assert isinstance(data["cache_hit"], bool)
        assert isinstance(data["engine_version"], str)

    @patch("app.routes.backtesting.get_or_compute")
    def test_backtest_run_contains_risk_metrics(
        self, mock_get_or_compute, client: TestClient, auth_headers: dict
    ):
        """백테스트 응답에 risk_metrics (MDD/Recovery) 포함 확인"""
        mock_get_or_compute.return_value = (
            MOCK_BACKTEST_RESULT,
            "abc123" * 10 + "abcd",
            False,
            "1.0.0"
        )

        response = client.post(
            "/backtest/run",
            json={
                "investment_type": "aggressive",
                "investment_amount": 10000000,
                "period_years": 1
            },
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        result_data = data["data"]

        # B-1 스펙: risk_metrics가 top-level에 있어야 함
        assert "risk_metrics" in result_data, "risk_metrics must exist in response"

        risk_metrics = result_data["risk_metrics"]

        # 핵심 KPI: MDD (Maximum Drawdown)
        assert "max_drawdown" in risk_metrics, "MDD (max_drawdown) must exist in risk_metrics"

        # 핵심 KPI: Recovery 관련 지표
        assert "max_recovery_days" in risk_metrics, "max_recovery_days must exist in risk_metrics"

    @patch("app.routes.backtesting.get_or_compute")
    def test_backtest_run_contains_historical_observation(
        self, mock_get_or_compute, client: TestClient, auth_headers: dict
    ):
        """백테스트 응답에 historical_observation 포함 확인"""
        mock_get_or_compute.return_value = (
            MOCK_BACKTEST_RESULT,
            "abc123" * 10 + "abcd",
            False,
            "1.0.0"
        )

        response = client.post(
            "/backtest/run",
            json={
                "investment_type": "conservative",
                "investment_amount": 10000000,
                "period_years": 1
            },
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        result_data = data["data"]

        # B-1 스펙: 수익률 지표는 historical_observation에 있어야 함
        assert "historical_observation" in result_data, \
            "historical_observation must exist in response"

        historical = result_data["historical_observation"]
        assert "total_return" in historical or "cagr" in historical, \
            "historical_observation must contain return metrics"

    @patch("app.routes.backtesting.get_or_compute")
    def test_compare_response_schema(
        self, mock_get_or_compute, client: TestClient, auth_headers: dict
    ):
        """비교 응답 스키마 검증"""
        mock_compare_result = {
            "comparison": [
                {**MOCK_BACKTEST_RESULT, "portfolio_name": "보수적"},
                {**MOCK_BACKTEST_RESULT, "portfolio_name": "공격적"},
            ],
            "best_return": "공격적",
            "best_risk_adjusted": "보수적",
            "lowest_risk": "보수적"
        }

        mock_get_or_compute.return_value = (
            mock_compare_result,
            "def456" * 10 + "defg",
            False,
            "1.0.0"
        )

        response = client.post(
            "/backtest/compare",
            json={
                "investment_types": ["conservative", "aggressive"],
                "investment_amount": 10000000,
                "period_years": 1
            },
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()

        # 필수 최상위 필드
        required_fields = ["success", "data", "request_hash", "cache_hit", "engine_version", "message"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        assert data["success"] is True


class TestBacktestMetricsAPI:
    """백테스트 메트릭 API 검증"""

    @patch("app.routes.backtesting.run_simple_backtest")
    @patch("app.routes.backtesting.get_engine_version")
    def test_metrics_response_schema(
        self, mock_engine_version, mock_backtest, client: TestClient, auth_headers: dict
    ):
        """메트릭 응답 스키마 검증"""
        mock_engine_version.return_value = "1.0.0"
        mock_backtest.return_value = MOCK_BACKTEST_RESULT

        response = client.get(
            "/backtest/metrics/moderate",
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()

        # 필수 필드
        required_fields = ["investment_type", "period_years", "engine_version", "risk_metrics", "historical_observation"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        # B-1 스펙: risk_metrics가 top-level
        assert "risk_metrics" in data
        # B-1 스펙: 수익률은 historical_observation에
        assert "historical_observation" in data

    def test_metrics_invalid_type_returns_400(self, client: TestClient, auth_headers: dict):
        """잘못된 투자 성향은 400 반환"""
        response = client.get(
            "/backtest/metrics/invalid_type",
            headers=auth_headers
        )
        assert response.status_code == 400


class TestCachingBehavior:
    """캐싱 동작 검증"""

    @patch("app.routes.backtesting.get_or_compute")
    def test_cache_hit_flag_in_response(
        self, mock_get_or_compute, client: TestClient, auth_headers: dict
    ):
        """응답에 cache_hit 플래그가 포함됨"""
        # 첫 요청 - cache miss
        mock_get_or_compute.return_value = (
            MOCK_BACKTEST_RESULT,
            "hash1" * 12 + "abcd",
            False,  # cache_hit = False
            "1.0.0"
        )

        response1 = client.post(
            "/backtest/run",
            json={
                "investment_type": "conservative",
                "investment_amount": 10000000,
                "period_years": 1
            },
            headers=auth_headers
        )
        assert response1.status_code == 200
        assert response1.json()["cache_hit"] is False

        # 두 번째 요청 - cache hit
        mock_get_or_compute.return_value = (
            MOCK_BACKTEST_RESULT,
            "hash1" * 12 + "abcd",
            True,  # cache_hit = True
            "1.0.0"
        )

        response2 = client.post(
            "/backtest/run",
            json={
                "investment_type": "conservative",
                "investment_amount": 10000000,
                "period_years": 1
            },
            headers=auth_headers
        )
        assert response2.status_code == 200
        assert response2.json()["cache_hit"] is True

    @patch("app.routes.backtesting.get_or_compute")
    def test_request_hash_in_response(
        self, mock_get_or_compute, client: TestClient, auth_headers: dict
    ):
        """응답에 request_hash가 포함됨 (64자리 SHA-256)"""
        expected_hash = "a" * 64
        mock_get_or_compute.return_value = (
            MOCK_BACKTEST_RESULT,
            expected_hash,
            False,
            "1.0.0"
        )

        response = client.post(
            "/backtest/run",
            json={
                "investment_type": "conservative",
                "investment_amount": 10000000,
                "period_years": 1
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["request_hash"] == expected_hash
        assert len(response.json()["request_hash"]) == 64

    @patch("app.routes.backtesting.get_or_compute")
    def test_engine_version_in_response(
        self, mock_get_or_compute, client: TestClient, auth_headers: dict
    ):
        """응답에 engine_version이 포함됨"""
        mock_get_or_compute.return_value = (
            MOCK_BACKTEST_RESULT,
            "b" * 64,
            False,
            "2.1.0"
        )

        response = client.post(
            "/backtest/run",
            json={
                "investment_type": "aggressive",
                "investment_amount": 10000000,
                "period_years": 1
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["engine_version"] == "2.1.0"
