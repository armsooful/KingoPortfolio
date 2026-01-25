"""
Phase 9 E2E 테스트: 타임아웃/재시도 정책 (TC-7.x)

타임아웃 및 재시도 정책의 정상 동작을 검증한다.
"""

from datetime import date
import time

import pytest

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
    response = client.post(
        "/api/v1/phase7/portfolios",
        json={
            "portfolio_type": "SECURITY",
            "portfolio_name": name,
            "items": [{"id": ticker, "name": name, "weight": 1.0}],
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["portfolio_id"]


@pytest.mark.e2e
@pytest.mark.p1
class TestTC7_1_TimeoutHandling:
    """TC-7.1: 타임아웃 처리"""

    def test_normal_request_within_timeout(self, client, db, auth_headers, test_user):
        """정상 요청은 타임아웃 내에 완료"""
        _seed_timeseries(db, "005930", base_price=70000)
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "타임아웃 테스트")

        start_time = time.time()
        response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )
        elapsed = time.time() - start_time

        # 검증: 성공
        assert response.status_code == 201

        # 검증: 합리적인 시간 내 완료 (5초 이내)
        assert elapsed < 5.0, f"Request took {elapsed:.2f}s, expected < 5s"

    def test_api_response_time_acceptable(self, client, db, auth_headers, test_user):
        """API 응답 시간이 허용 범위 내"""
        _seed_timeseries(db, "005930", base_price=70000)
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "응답 시간 검증")

        # 여러 번 측정하여 평균 확인
        times = []
        for _ in range(3):
            start = time.time()
            response = client.post(
                "/api/v1/phase7/evaluations",
                json={
                    "portfolio_id": portfolio_id,
                    "period": {"start": "2024-01-02", "end": "2024-01-06"},
                    "rebalance": "NONE",
                },
                headers=auth_headers,
            )
            times.append(time.time() - start)
            assert response.status_code == 201

        avg_time = sum(times) / len(times)
        # 검증: 평균 응답 시간 3초 이내
        assert avg_time < 3.0, f"Average response time {avg_time:.2f}s exceeded 3s"


@pytest.mark.e2e
@pytest.mark.p1
class TestTC7_2_RetryAfterError:
    """TC-7.2: 오류 후 재시도"""

    def test_retry_after_client_error_works(self, client, db, auth_headers, test_user):
        """클라이언트 오류 후 올바른 요청은 성공"""
        _seed_timeseries(db, "005930", base_price=70000)
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "재시도 테스트")

        # 첫 번째 요청: 잘못된 기간 (실패)
        error_response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": "2024-01-10", "end": "2024-01-05"},  # 잘못된 기간
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )
        assert error_response.status_code == 400

        # 두 번째 요청: 올바른 기간 (성공)
        success_response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )
        assert success_response.status_code == 201

    def test_retry_after_not_found_works(self, client, db, auth_headers, test_user):
        """404 오류 후 올바른 요청은 성공"""
        _seed_timeseries(db, "005930", base_price=70000)

        # 첫 번째 요청: 존재하지 않는 포트폴리오 (실패)
        error_response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": 99999,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )
        assert error_response.status_code == 404

        # 포트폴리오 생성
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "재시도 테스트 2")

        # 두 번째 요청: 올바른 포트폴리오 (성공)
        success_response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )
        assert success_response.status_code == 201

    def test_multiple_retries_do_not_corrupt_state(self, client, db, auth_headers, test_user):
        """여러 번 재시도해도 상태가 손상되지 않음"""
        _seed_timeseries(db, "005930", base_price=70000)
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "상태 검증 테스트")

        # 여러 번 실패 시도
        for _ in range(3):
            client.post(
                "/api/v1/phase7/evaluations",
                json={
                    "portfolio_id": portfolio_id,
                    "period": {"start": "2024-01-10", "end": "2024-01-05"},
                    "rebalance": "NONE",
                },
                headers=auth_headers,
            )

        # 성공 요청
        response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201

        # 포트폴리오 상태 확인
        portfolio_response = client.get(
            f"/api/v1/phase7/portfolios/{portfolio_id}",
            headers=auth_headers,
        )
        assert portfolio_response.status_code == 200


@pytest.mark.e2e
@pytest.mark.p1
class TestTC7_ServiceRecovery:
    """서비스 복구 검증"""

    def test_service_continues_after_errors(self, client, db, auth_headers, test_user):
        """오류 발생 후에도 서비스가 정상 동작"""
        _seed_timeseries(db, "005930", base_price=70000)
        _seed_timeseries(db, "000660", base_price=120000)

        # 여러 오류 유형 발생
        # 1. 잘못된 기간
        client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": 1,
                "period": {"start": "2024-01-10", "end": "2024-01-05"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )

        # 2. 존재하지 않는 포트폴리오
        client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": 99999,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )

        # 3. 잘못된 리밸런싱 옵션
        client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": 1,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "INVALID",
            },
            headers=auth_headers,
        )

        # 정상 요청은 성공해야 함
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "복구 테스트")
        response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201

        # 다른 포트폴리오도 정상 동작
        portfolio_id_2 = _create_portfolio(client, auth_headers, "000660", "복구 테스트 2")
        response_2 = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id_2,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )
        assert response_2.status_code == 201
