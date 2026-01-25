"""
Phase 9 E2E 테스트: 포트폴리오 비교 (TC-2.x)

본인 포트폴리오 간 비교 기능을 검증한다.
"""

from datetime import date

import pytest

from app.models.phase7_portfolio import Phase7Portfolio, Phase7PortfolioItem
from app.models.securities import KrxTimeSeries
from app.models.user import User
from app.auth import hash_password


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


def _create_portfolio_and_evaluate(client, db, auth_headers, ticker: str, name: str, user_id: str) -> int:
    """포트폴리오 생성 및 평가 실행, portfolio_id 반환"""
    _seed_timeseries(db, ticker)

    # 포트폴리오 생성
    portfolio_response = client.post(
        "/api/v1/phase7/portfolios",
        json={
            "portfolio_type": "SECURITY",
            "portfolio_name": name,
            "items": [
                {"id": ticker, "name": name, "weight": 1.0}
            ],
        },
        headers=auth_headers,
    )
    assert portfolio_response.status_code == 201
    portfolio_id = portfolio_response.json()["portfolio_id"]

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

    return portfolio_id


@pytest.mark.e2e
@pytest.mark.p0
class TestTC2_1_TwoPortfolioComparison:
    """TC-2.1: 두 포트폴리오 비교"""

    def test_compare_two_portfolios(self, client, db, auth_headers, test_user):
        """동일 사용자의 두 포트폴리오 비교"""
        # 포트폴리오 A 생성 및 평가
        portfolio_a_id = _create_portfolio_and_evaluate(
            client, db, auth_headers, "005930", "포트폴리오 A", test_user.id
        )

        # 포트폴리오 B 생성 및 평가
        portfolio_b_id = _create_portfolio_and_evaluate(
            client, db, auth_headers, "000660", "포트폴리오 B", test_user.id
        )

        # 비교 요청
        comparison_response = client.post(
            "/api/v1/phase7/comparisons",
            json={"portfolio_ids": [portfolio_a_id, portfolio_b_id]},
            headers=auth_headers,
        )
        assert comparison_response.status_code == 200

        body = comparison_response.json()

        # 검증: count == 2
        assert body["count"] == 2

        # 검증: 각 포트폴리오별 metrics 포함
        for portfolio in body["portfolios"]:
            assert "metrics" in portfolio
            assert portfolio["metrics"] is not None

        # 검증: disclaimer_version 포함
        assert body["portfolios"][0]["disclaimer_version"] == "v2"

        # 검증: 우열 판단 표현 없음 (규제 준수)
        # 응답에 "best", "worst", "winner", "loser", "rank" 등의 키가 없어야 함
        response_str = str(body).lower()
        forbidden_terms = ["best", "worst", "winner", "loser", "rank", "추천", "우수", "열등"]
        for term in forbidden_terms:
            assert term not in response_str, f"Forbidden term found: {term}"


@pytest.mark.e2e
@pytest.mark.p0
class TestTC2_2_ComparisonWithoutEvaluation:
    """TC-2.2: 평가 미실행 포트폴리오 비교 시도"""

    def test_compare_without_evaluation(self, client, db, auth_headers, test_user):
        """평가 없이 비교 시도 시 에러"""
        # 시계열 데이터 준비
        _seed_timeseries(db, "005930")
        _seed_timeseries(db, "000660")

        # 포트폴리오 A 생성 (평가 없음)
        portfolio_a_response = client.post(
            "/api/v1/phase7/portfolios",
            json={
                "portfolio_type": "SECURITY",
                "portfolio_name": "평가 없음 A",
                "items": [{"id": "005930", "name": "삼성전자", "weight": 1.0}],
            },
            headers=auth_headers,
        )
        portfolio_a_id = portfolio_a_response.json()["portfolio_id"]

        # 포트폴리오 B 생성 (평가 없음)
        portfolio_b_response = client.post(
            "/api/v1/phase7/portfolios",
            json={
                "portfolio_type": "SECURITY",
                "portfolio_name": "평가 없음 B",
                "items": [{"id": "000660", "name": "SK하이닉스", "weight": 1.0}],
            },
            headers=auth_headers,
        )
        portfolio_b_id = portfolio_b_response.json()["portfolio_id"]

        # 비교 시도 (평가 미실행 상태)
        comparison_response = client.post(
            "/api/v1/phase7/comparisons",
            json={"portfolio_ids": [portfolio_a_id, portfolio_b_id]},
            headers=auth_headers,
        )

        # 검증: 400 Bad Request
        assert comparison_response.status_code == 400


@pytest.mark.e2e
@pytest.mark.p0
class TestTC2_3_CrossUserComparisonBlocked:
    """TC-2.3: 타 사용자 포트폴리오 비교 차단"""

    def test_cross_user_comparison_blocked(self, client, db, auth_headers, test_user):
        """타 사용자 포트폴리오 접근 차단 확인"""
        # User A의 포트폴리오 생성 및 평가
        portfolio_a_id = _create_portfolio_and_evaluate(
            client, db, auth_headers, "005930", "User A 포트폴리오", test_user.id
        )

        # User B 생성 및 로그인
        user_b = User(
            email="userb@test.com",
            hashed_password=hash_password("testpassword123"),
            is_admin=False,
            role="user",
        )
        db.add(user_b)
        db.commit()

        login_response = client.post(
            "/auth/login",
            json={"email": "userb@test.com", "password": "testpassword123"},
        )
        user_b_token = login_response.json()["access_token"]
        user_b_headers = {"Authorization": f"Bearer {user_b_token}"}

        # User B의 포트폴리오 생성 및 평가
        _seed_timeseries(db, "000660")
        portfolio_b_response = client.post(
            "/api/v1/phase7/portfolios",
            json={
                "portfolio_type": "SECURITY",
                "portfolio_name": "User B 포트폴리오",
                "items": [{"id": "000660", "name": "SK하이닉스", "weight": 1.0}],
            },
            headers=user_b_headers,
        )
        portfolio_b_id = portfolio_b_response.json()["portfolio_id"]

        client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_b_id,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "NONE",
            },
            headers=user_b_headers,
        )

        # User B가 User A의 포트폴리오와 비교 시도
        comparison_response = client.post(
            "/api/v1/phase7/comparisons",
            json={"portfolio_ids": [portfolio_a_id, portfolio_b_id]},
            headers=user_b_headers,
        )

        # 검증: 404 Not Found (User A의 포트폴리오에 접근 불가)
        assert comparison_response.status_code == 404

    def test_access_other_user_portfolio_directly(self, client, db, auth_headers, test_user):
        """타 사용자 포트폴리오 직접 접근 차단"""
        # User A의 포트폴리오 생성
        _seed_timeseries(db, "005930")
        portfolio_response = client.post(
            "/api/v1/phase7/portfolios",
            json={
                "portfolio_type": "SECURITY",
                "portfolio_name": "User A 포트폴리오",
                "items": [{"id": "005930", "name": "삼성전자", "weight": 1.0}],
            },
            headers=auth_headers,
        )
        portfolio_id = portfolio_response.json()["portfolio_id"]

        # User B 생성 및 로그인
        user_b = User(
            email="userb2@test.com",
            hashed_password=hash_password("testpassword123"),
            is_admin=False,
            role="user",
        )
        db.add(user_b)
        db.commit()

        login_response = client.post(
            "/auth/login",
            json={"email": "userb2@test.com", "password": "testpassword123"},
        )
        user_b_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        # User B가 User A의 포트폴리오 직접 조회 시도
        get_response = client.get(
            f"/api/v1/phase7/portfolios/{portfolio_id}",
            headers=user_b_headers,
        )

        # 검증: 404 Not Found
        assert get_response.status_code == 404


@pytest.mark.e2e
@pytest.mark.p1
class TestTC2_ComparisonEdgeCases:
    """비교 기능 엣지 케이스"""

    def test_compare_same_portfolio_twice(self, client, db, auth_headers, test_user):
        """동일 포트폴리오를 두 번 비교 (엣지 케이스)"""
        portfolio_id = _create_portfolio_and_evaluate(
            client, db, auth_headers, "005930", "동일 포트폴리오", test_user.id
        )

        comparison_response = client.post(
            "/api/v1/phase7/comparisons",
            json={"portfolio_ids": [portfolio_id, portfolio_id]},
            headers=auth_headers,
        )

        # 동일 포트폴리오 비교 시 적절한 처리 (200 또는 400)
        assert comparison_response.status_code in [200, 400]

    def test_compare_nonexistent_portfolio(self, client, db, auth_headers, test_user):
        """존재하지 않는 포트폴리오 비교 시도"""
        comparison_response = client.post(
            "/api/v1/phase7/comparisons",
            json={"portfolio_ids": [99999, 99998]},
            headers=auth_headers,
        )

        # 검증: 404 Not Found
        assert comparison_response.status_code == 404

    def test_compare_three_portfolios(self, client, db, auth_headers, test_user):
        """세 개 포트폴리오 비교"""
        portfolio_a_id = _create_portfolio_and_evaluate(
            client, db, auth_headers, "005930", "포트폴리오 A", test_user.id
        )
        portfolio_b_id = _create_portfolio_and_evaluate(
            client, db, auth_headers, "000660", "포트폴리오 B", test_user.id
        )
        portfolio_c_id = _create_portfolio_and_evaluate(
            client, db, auth_headers, "035420", "포트폴리오 C", test_user.id
        )

        comparison_response = client.post(
            "/api/v1/phase7/comparisons",
            json={"portfolio_ids": [portfolio_a_id, portfolio_b_id, portfolio_c_id]},
            headers=auth_headers,
        )

        # 세 개 비교 지원 여부에 따라 200 또는 400
        if comparison_response.status_code == 200:
            body = comparison_response.json()
            assert body["count"] == 3
