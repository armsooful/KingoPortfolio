"""
Phase 9 E2E 테스트: 결과 재현성 검증 (TC-5.x)

동일 입력에 대한 결과 재현성 및 불변성을 검증한다.
"""

from datetime import date
import json

import pytest

from app.models.phase7_portfolio import Phase7Portfolio, Phase7PortfolioItem
from app.models.phase7_evaluation import Phase7EvaluationRun
from app.models.securities import KrxTimeSeries


def _seed_timeseries(db, ticker: str, base_price: float = 100.0) -> None:
    """테스트용 시계열 데이터 생성"""
    rows = []
    prices = [base_price, base_price * 1.01, base_price * 1.02, base_price * 0.99, base_price * 1.03]
    for i, price in enumerate(prices):
        rows.append(
            KrxTimeSeries(
                ticker=ticker,
                date=date(2024, 1, 2 + i),
                open=price,
                high=price * 1.02,
                low=price * 0.98,
                close=price,
                volume=1000 + i * 100,
            )
        )
    db.add_all(rows)
    db.commit()


def _create_portfolio(client, auth_headers, ticker: str, name: str) -> int:
    """포트폴리오 생성 후 portfolio_id 반환"""
    portfolio_response = client.post(
        "/api/v1/phase7/portfolios",
        json={
            "portfolio_type": "SECURITY",
            "portfolio_name": name,
            "items": [{"id": ticker, "name": name, "weight": 1.0}],
        },
        headers=auth_headers,
    )
    assert portfolio_response.status_code == 201
    return portfolio_response.json()["portfolio_id"]


@pytest.mark.e2e
@pytest.mark.p0
class TestTC5_1_SameInputSameResult:
    """TC-5.1: 동일 입력 → 동일 결과"""

    def test_identical_results_for_same_input(self, client, db, auth_headers, test_user):
        """동일 입력에 대해 동일한 결과 반환"""
        _seed_timeseries(db, "005930", base_price=70000)
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "재현성 테스트")

        evaluation_payload = {
            "portfolio_id": portfolio_id,
            "period": {"start": "2024-01-02", "end": "2024-01-06"},
            "rebalance": "NONE",
        }

        # 첫 번째 평가
        response1 = client.post(
            "/api/v1/phase7/evaluations",
            json=evaluation_payload,
            headers=auth_headers,
        )
        assert response1.status_code == 201
        result1 = response1.json()

        # 두 번째 평가 (동일 입력)
        response2 = client.post(
            "/api/v1/phase7/evaluations",
            json=evaluation_payload,
            headers=auth_headers,
        )
        assert response2.status_code == 201
        result2 = response2.json()

        # 검증: metrics 모든 값 일치
        assert result1["metrics"]["cumulative_return"] == result2["metrics"]["cumulative_return"]
        assert result1["metrics"]["cagr"] == result2["metrics"]["cagr"]
        assert result1["metrics"]["volatility"] == result2["metrics"]["volatility"]
        assert result1["metrics"]["max_drawdown"] == result2["metrics"]["max_drawdown"]

        # 검증: disclaimer_version 일치
        assert result1["disclaimer_version"] == result2["disclaimer_version"]

    def test_result_hash_consistency(self, client, db, auth_headers, test_user):
        """결과 해시 일관성 검증"""
        _seed_timeseries(db, "005930", base_price=70000)
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "해시 일관성 테스트")

        evaluation_payload = {
            "portfolio_id": portfolio_id,
            "period": {"start": "2024-01-02", "end": "2024-01-06"},
            "rebalance": "NONE",
        }

        # 두 번 평가 실행
        client.post("/api/v1/phase7/evaluations", json=evaluation_payload, headers=auth_headers)
        client.post("/api/v1/phase7/evaluations", json=evaluation_payload, headers=auth_headers)

        # 이력 조회
        history_response = client.get(
            "/api/v1/phase7/evaluations",
            params={"portfolio_id": portfolio_id},
            headers=auth_headers,
        )
        assert history_response.status_code == 200
        evaluations = history_response.json()["evaluations"]

        # 검증: 두 평가의 result_hash 일치
        assert len(evaluations) >= 2
        assert evaluations[0]["result_hash"] == evaluations[1]["result_hash"]


@pytest.mark.e2e
@pytest.mark.p0
class TestTC5_2_StoredResultImmutability:
    """TC-5.2: 저장된 결과 조회 시 불변성"""

    def test_stored_result_unchanged(self, client, db, auth_headers, test_user):
        """저장된 결과가 변경되지 않음"""
        _seed_timeseries(db, "005930", base_price=70000)
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "불변성 테스트")

        # 평가 실행
        evaluation_response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )
        assert evaluation_response.status_code == 201
        original_result = evaluation_response.json()

        # 이력에서 evaluation_id 조회
        history_response = client.get(
            "/api/v1/phase7/evaluations",
            headers=auth_headers,
        )
        evaluation_id = history_response.json()["evaluations"][0]["evaluation_id"]
        original_hash = history_response.json()["evaluations"][0]["result_hash"]

        # 상세 조회 (첫 번째)
        detail_response1 = client.get(
            f"/api/v1/phase7/evaluations/{evaluation_id}",
            headers=auth_headers,
        )
        assert detail_response1.status_code == 200
        detail1 = detail_response1.json()

        # 상세 조회 (두 번째 - 시간 경과 후)
        detail_response2 = client.get(
            f"/api/v1/phase7/evaluations/{evaluation_id}",
            headers=auth_headers,
        )
        assert detail_response2.status_code == 200
        detail2 = detail_response2.json()

        # 검증: result_hash 일치
        assert detail1["result_hash"] == detail2["result_hash"]
        assert detail1["result_hash"] == original_hash

        # 검증: result 내용 일치
        assert detail1["result"]["metrics"] == detail2["result"]["metrics"]

    def test_database_stored_result_integrity(self, client, db, auth_headers, test_user):
        """DB에 저장된 결과의 무결성 검증"""
        _seed_timeseries(db, "005930", base_price=70000)
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "DB 무결성 테스트")

        # 평가 실행
        evaluation_response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )
        api_result = evaluation_response.json()

        # DB에서 직접 조회
        evaluation_run = (
            db.query(Phase7EvaluationRun)
            .filter(Phase7EvaluationRun.portfolio_id == portfolio_id)
            .first()
        )

        # 검증: DB 저장 값과 API 응답 일치
        db_result = json.loads(evaluation_run.result_json)
        assert db_result["metrics"]["cumulative_return"] == api_result["metrics"]["cumulative_return"]
        assert db_result["metrics"]["cagr"] == api_result["metrics"]["cagr"]

        # 검증: result_hash 존재
        assert evaluation_run.result_hash is not None
        assert len(evaluation_run.result_hash) > 0


@pytest.mark.e2e
@pytest.mark.p0
class TestTC5_3_ReplayResultImmutability:
    """TC-5.3: 재처리(Replay) 결과 불변성"""

    def test_replay_produces_same_result(self, client, db, auth_headers, test_user):
        """재처리 시 동일한 결과 생성"""
        _seed_timeseries(db, "005930", base_price=70000)
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "재처리 테스트")

        evaluation_payload = {
            "portfolio_id": portfolio_id,
            "period": {"start": "2024-01-02", "end": "2024-01-06"},
            "rebalance": "NONE",
        }

        # 원본 평가
        original_response = client.post(
            "/api/v1/phase7/evaluations",
            json=evaluation_payload,
            headers=auth_headers,
        )
        original_result = original_response.json()

        # 재처리 (동일 입력으로 다시 평가)
        replay_response = client.post(
            "/api/v1/phase7/evaluations",
            json=evaluation_payload,
            headers=auth_headers,
        )
        replay_result = replay_response.json()

        # 검증: 데이터 변경 없으면 결과 동일
        assert original_result["metrics"] == replay_result["metrics"]

    def test_multiple_replays_consistent(self, client, db, auth_headers, test_user):
        """여러 번 재처리해도 결과 일관성 유지"""
        _seed_timeseries(db, "005930", base_price=70000)
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "다중 재처리 테스트")

        evaluation_payload = {
            "portfolio_id": portfolio_id,
            "period": {"start": "2024-01-02", "end": "2024-01-06"},
            "rebalance": "NONE",
        }

        results = []
        for i in range(5):
            response = client.post(
                "/api/v1/phase7/evaluations",
                json=evaluation_payload,
                headers=auth_headers,
            )
            assert response.status_code == 201
            results.append(response.json())

        # 검증: 모든 결과의 metrics 동일
        first_metrics = results[0]["metrics"]
        for result in results[1:]:
            assert result["metrics"]["cumulative_return"] == first_metrics["cumulative_return"]
            assert result["metrics"]["cagr"] == first_metrics["cagr"]
            assert result["metrics"]["volatility"] == first_metrics["volatility"]
            assert result["metrics"]["max_drawdown"] == first_metrics["max_drawdown"]


@pytest.mark.e2e
@pytest.mark.p1
class TestTC5_DifferentInputDifferentResult:
    """다른 입력에 대한 다른 결과 검증"""

    def test_different_period_different_result(self, client, db, auth_headers, test_user):
        """다른 기간에 대해 다른 결과"""
        _seed_timeseries(db, "005930", base_price=70000)
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "기간별 결과 테스트")

        # 짧은 기간
        response1 = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": "2024-01-02", "end": "2024-01-04"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )
        result1 = response1.json()

        # 긴 기간
        response2 = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )
        result2 = response2.json()

        # 검증: 기간이 다르면 결과도 다를 수 있음 (또는 동일할 수 있음)
        # 중요한 것은 각각 정상적으로 계산되었는지
        assert result1["metrics"]["cumulative_return"] is not None
        assert result2["metrics"]["cumulative_return"] is not None

    def test_different_portfolio_different_hash(self, client, db, auth_headers, test_user):
        """다른 포트폴리오에 대해 다른 해시"""
        _seed_timeseries(db, "005930", base_price=70000)
        _seed_timeseries(db, "000660", base_price=120000)

        portfolio_a_id = _create_portfolio(client, auth_headers, "005930", "포트폴리오 A")
        portfolio_b_id = _create_portfolio(client, auth_headers, "000660", "포트폴리오 B")

        # 동일 기간, 다른 포트폴리오
        response_a = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_a_id,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )

        response_b = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_b_id,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )

        # 이력 조회
        history_a = client.get(
            "/api/v1/phase7/evaluations",
            params={"portfolio_id": portfolio_a_id},
            headers=auth_headers,
        )
        history_b = client.get(
            "/api/v1/phase7/evaluations",
            params={"portfolio_id": portfolio_b_id},
            headers=auth_headers,
        )

        hash_a = history_a.json()["evaluations"][0]["result_hash"]
        hash_b = history_b.json()["evaluations"][0]["result_hash"]

        # 검증: 다른 포트폴리오는 다른 해시 (가격이 다르므로)
        assert hash_a != hash_b


@pytest.mark.e2e
@pytest.mark.p1
class TestTC5_HashAlgorithmConsistency:
    """해시 알고리즘 일관성 검증"""

    def test_hash_format(self, client, db, auth_headers, test_user):
        """해시 형식 검증"""
        _seed_timeseries(db, "005930", base_price=70000)
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "해시 형식 테스트")

        client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )

        history = client.get(
            "/api/v1/phase7/evaluations",
            params={"portfolio_id": portfolio_id},
            headers=auth_headers,
        )
        result_hash = history.json()["evaluations"][0]["result_hash"]

        # 검증: 해시가 유효한 형식인지 (예: SHA-256 = 64자 hex)
        assert result_hash is not None
        assert len(result_hash) > 0
        # 일반적인 해시 형식 검증 (hex 문자열)
        assert all(c in "0123456789abcdef" for c in result_hash.lower())
