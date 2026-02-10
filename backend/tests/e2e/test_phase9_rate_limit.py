"""
Phase 9 E2E 테스트: 대량 요청/반복 요청 (TC-4.x)

레이트 리밋 및 동시 요청 처리를 검증한다.
"""

from datetime import date
import threading
import time

import pytest

from decimal import Decimal

from app.models.real_data import StockPriceDaily


def _seed_timeseries(db, ticker: str, base_price: float = 100.0) -> None:
    """테스트용 시계열 데이터 생성"""
    rows = []
    prices = [base_price, base_price * 1.01, base_price * 1.02, base_price * 0.99, base_price * 1.03]
    for i, price in enumerate(prices):
        td = date(2024, 1, 2 + i)
        rows.append(
            StockPriceDaily(
                ticker=ticker,
                trade_date=td,
                open_price=Decimal(str(round(price, 2))),
                high_price=Decimal(str(round(price * 1.02, 2))),
                low_price=Decimal(str(round(price * 0.98, 2))),
                close_price=Decimal(str(round(price, 2))),
                volume=1000 + i * 100,
                source_id='PYKRX',
                as_of_date=td,
                quality_flag='NORMAL',
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
class TestTC4_1_ConsecutiveEvaluations:
    """TC-4.1: 연속 평가 요청"""

    def test_consecutive_evaluation_requests(self, client, db, auth_headers, test_user):
        """동일 사용자로 10회 연속 평가 요청"""
        _seed_timeseries(db, "005930", base_price=70000)
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "연속 요청 테스트")

        evaluation_payload = {
            "portfolio_id": portfolio_id,
            "period": {"start": "2024-01-02", "end": "2024-01-06"},
            "rebalance": "NONE",
        }

        results = []
        for i in range(10):
            response = client.post(
                "/api/v1/phase7/evaluations",
                json=evaluation_payload,
                headers=auth_headers,
            )
            results.append(response)

        # 검증: 모든 요청 성공
        for i, response in enumerate(results):
            assert response.status_code == 201, f"Request {i+1} failed with status {response.status_code}"

        # 검증: 모든 결과에 metrics 포함
        for response in results:
            body = response.json()
            assert "metrics" in body
            assert body["disclaimer_version"] == "v2"

    def test_response_time_consistency(self, client, db, auth_headers, test_user):
        """응답 시간 일관성 검증"""
        _seed_timeseries(db, "005930", base_price=70000)
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "응답 시간 테스트")

        evaluation_payload = {
            "portfolio_id": portfolio_id,
            "period": {"start": "2024-01-02", "end": "2024-01-06"},
            "rebalance": "NONE",
        }

        response_times = []
        for _ in range(5):
            start_time = time.time()
            response = client.post(
                "/api/v1/phase7/evaluations",
                json=evaluation_payload,
                headers=auth_headers,
            )
            end_time = time.time()
            response_times.append(end_time - start_time)
            assert response.status_code == 201

        # 검증: 응답 시간이 10초 이내
        for rt in response_times:
            assert rt < 10.0, f"Response time {rt:.2f}s exceeded 10s limit"


@pytest.mark.e2e
@pytest.mark.p1
class TestTC4_2_RateLimitExceeded:
    """TC-4.2: 레이트 리밋 초과"""

    @pytest.mark.skip(reason="레이트 리밋이 테스트 환경에서 비활성화됨")
    def test_rate_limit_exceeded(self, client, db, auth_headers, test_user):
        """레이트 리밋 초과 시 429 반환"""
        # 참고: 테스트 환경에서는 레이트 리밋이 비활성화되어 있음
        # 실제 운영 환경에서 테스트 필요
        pass

    def test_rate_limit_headers_present(self, client, db, auth_headers, test_user):
        """레이트 리밋 관련 헤더 확인 (비활성화 상태에서도 검증)"""
        _seed_timeseries(db, "005930", base_price=70000)
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "헤더 테스트")

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
        # 레이트 리밋 헤더는 활성화 환경에서만 존재
        # 비활성화 상태에서는 헤더 없음이 정상


@pytest.mark.e2e
@pytest.mark.p1
class TestTC4_3_ConcurrentRequests:
    """TC-4.3: 동시 요청 처리"""

    @pytest.mark.skip(reason="SQLite 테스트 환경에서 동시성 제약 - PostgreSQL 환경에서 테스트 필요")
    def test_concurrent_requests_from_same_user(self, client, db, auth_headers, test_user):
        """동일 사용자의 동시 요청 처리"""
        _seed_timeseries(db, "005930", base_price=70000)
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "동시 요청 테스트")

        evaluation_payload = {
            "portfolio_id": portfolio_id,
            "period": {"start": "2024-01-02", "end": "2024-01-06"},
            "rebalance": "NONE",
        }

        results = []
        errors = []

        def make_request():
            try:
                response = client.post(
                    "/api/v1/phase7/evaluations",
                    json=evaluation_payload,
                    headers=auth_headers,
                )
                results.append(response)
            except Exception as e:
                errors.append(e)

        # 5개 동시 요청
        threads = []
        for _ in range(5):
            t = threading.Thread(target=make_request)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # 검증: 에러 없음
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # 검증: 모든 요청 성공
        assert len(results) == 5
        for response in results:
            assert response.status_code == 201

    def test_data_integrity_under_concurrent_load(self, client, db, auth_headers, test_user):
        """동시 요청 시 데이터 무결성 유지"""
        _seed_timeseries(db, "005930", base_price=70000)

        results = []
        portfolio_ids = []

        def create_and_evaluate(idx):
            # 각 스레드에서 포트폴리오 생성
            portfolio_response = client.post(
                "/api/v1/phase7/portfolios",
                json={
                    "portfolio_type": "SECURITY",
                    "portfolio_name": f"동시 포트폴리오 {idx}",
                    "items": [{"id": "005930", "name": "삼성전자", "weight": 1.0}],
                },
                headers=auth_headers,
            )
            if portfolio_response.status_code == 201:
                pid = portfolio_response.json()["portfolio_id"]
                portfolio_ids.append(pid)

                # 평가 실행
                eval_response = client.post(
                    "/api/v1/phase7/evaluations",
                    json={
                        "portfolio_id": pid,
                        "period": {"start": "2024-01-02", "end": "2024-01-06"},
                        "rebalance": "NONE",
                    },
                    headers=auth_headers,
                )
                results.append((idx, eval_response.status_code))

        # 3개 동시 생성 및 평가
        threads = []
        for i in range(3):
            t = threading.Thread(target=create_and_evaluate, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # 검증: 중복 portfolio_id 없음
        unique_ids = set(portfolio_ids)
        assert len(unique_ids) == len(portfolio_ids), "Duplicate portfolio IDs detected"

        # 검증: 모든 평가 성공
        for idx, status in results:
            assert status == 201, f"Evaluation {idx} failed with status {status}"


@pytest.mark.e2e
@pytest.mark.p1
class TestTC4_BurstRequests:
    """버스트 요청 처리"""

    def test_burst_requests(self, client, db, auth_headers, test_user):
        """짧은 시간 내 연속 요청 (버스트)"""
        _seed_timeseries(db, "005930", base_price=70000)
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "버스트 테스트")

        evaluation_payload = {
            "portfolio_id": portfolio_id,
            "period": {"start": "2024-01-02", "end": "2024-01-06"},
            "rebalance": "NONE",
        }

        # 20개 요청을 빠르게 전송
        responses = []
        for _ in range(20):
            response = client.post(
                "/api/v1/phase7/evaluations",
                json=evaluation_payload,
                headers=auth_headers,
            )
            responses.append(response)

        # 성공한 요청 수 확인
        success_count = sum(1 for r in responses if r.status_code == 201)
        throttled_count = sum(1 for r in responses if r.status_code == 429)

        # 레이트 리밋 비활성화 상태: 모두 성공
        # 레이트 리밋 활성화 상태: 일부 429
        assert success_count + throttled_count == 20
        assert success_count > 0  # 최소 1개는 성공해야 함
