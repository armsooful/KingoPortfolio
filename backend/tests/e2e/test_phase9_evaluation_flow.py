"""
Phase 9 E2E 테스트: 평가 플로우 (TC-1.x)

신규 사용자 포트폴리오 평가 전체 플로우를 검증한다.
"""

from datetime import date

import pytest

from app.models.phase7_portfolio import Phase7Portfolio, Phase7PortfolioItem
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


def _seed_extended_timeseries(db, ticker: str, start_date: date, days: int = 30) -> None:
    """확장 테스트용 시계열 데이터 생성 (리밸런싱 테스트용)"""
    import random
    from datetime import timedelta
    random.seed(42)

    rows = []
    price = 100.0
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        if current_date.weekday() >= 5:  # 주말 제외
            continue
        price = price * (1 + random.uniform(-0.03, 0.03))
        rows.append(
            KrxTimeSeries(
                ticker=ticker,
                date=current_date,
                open=price,
                high=price * 1.01,
                low=price * 0.99,
                close=price,
                volume=1000,
            )
        )
    db.add_all(rows)
    db.commit()


@pytest.mark.e2e
@pytest.mark.p0
class TestTC1_1_NewUserEvaluationFlow:
    """TC-1.1: 신규 사용자 회원가입 → 포트폴리오 생성 → 평가 → 결과 확인"""

    def test_full_evaluation_flow(self, client, db):
        """전체 평가 플로우 E2E 테스트"""
        # Step 1: 신규 사용자 회원가입
        signup_response = client.post(
            "/auth/signup",
            json={
                "email": "e2e_newuser@test.com",
                "password": "SecurePass123!",
                "name": "E2E 테스트 사용자",
            },
        )
        assert signup_response.status_code == 201
        token = signup_response.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        # 시계열 데이터 준비
        _seed_timeseries(db, "005930", base_price=70000)

        # Step 2: 포트폴리오 생성
        portfolio_response = client.post(
            "/api/v1/phase7/portfolios",
            json={
                "portfolio_type": "SECURITY",
                "portfolio_name": "E2E 테스트 포트폴리오",
                "items": [
                    {"id": "005930", "name": "삼성전자", "weight": 1.0}
                ],
            },
            headers=auth_headers,
        )
        assert portfolio_response.status_code == 201
        portfolio_id = portfolio_response.json()["portfolio_id"]
        assert portfolio_id is not None

        # Step 3: 평가 실행
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
        eval_body = evaluation_response.json()

        # 검증: disclaimer_version
        assert eval_body.get("disclaimer_version") == "v2"

        # 검증: metrics 포함
        assert "metrics" in eval_body
        metrics = eval_body["metrics"]
        assert "cumulative_return" in metrics
        assert "cagr" in metrics
        assert "volatility" in metrics
        assert "max_drawdown" in metrics

        # 검증: extensions 포함 (Phase 8-A)
        assert "extensions" in eval_body

        # Step 4: 평가 이력 조회
        history_response = client.get(
            "/api/v1/phase7/evaluations",
            headers=auth_headers,
        )
        assert history_response.status_code == 200
        history_body = history_response.json()
        assert history_body["count"] >= 1
        assert history_body["evaluations"][0]["result_hash"] is not None

        # Step 5: 평가 상세 조회
        evaluation_id = history_body["evaluations"][0]["evaluation_id"]
        detail_response = client.get(
            f"/api/v1/phase7/evaluations/{evaluation_id}",
            headers=auth_headers,
        )
        assert detail_response.status_code == 200
        detail_body = detail_response.json()
        assert detail_body["result"]["disclaimer_version"] == "v2"
        assert detail_body["result_hash"] is not None
        assert "extensions" in detail_body["result"]


@pytest.mark.e2e
@pytest.mark.p0
class TestTC1_2_SingleSecurityPortfolio:
    """TC-1.2: 포트폴리오 종목 구성 (단일 종목)"""

    def test_single_security_portfolio(self, client, db, auth_headers, test_user):
        """단일 종목 포트폴리오 평가"""
        _seed_timeseries(db, "005930", base_price=70000)

        # 포트폴리오 생성
        portfolio_response = client.post(
            "/api/v1/phase7/portfolios",
            json={
                "portfolio_type": "SECURITY",
                "portfolio_name": "단일 종목 테스트",
                "items": [
                    {"id": "005930", "name": "삼성전자", "weight": 1.0}
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

        # 검증: 비중 합계 = 1.0
        portfolio = db.query(Phase7Portfolio).filter_by(portfolio_id=portfolio_id).first()
        total_weight = sum(float(item.weight) for item in portfolio.items)
        assert abs(total_weight - 1.0) < 0.0001


@pytest.mark.e2e
@pytest.mark.p0
class TestTC1_3_MultipleSecuritiesPortfolio:
    """TC-1.3: 포트폴리오 종목 구성 (복수 종목)"""

    def test_multiple_securities_portfolio(self, client, db, auth_headers, test_user):
        """복수 종목 포트폴리오 평가"""
        # 복수 종목 시계열 데이터 준비
        _seed_timeseries(db, "005930", base_price=70000)
        _seed_timeseries(db, "000660", base_price=120000)
        _seed_timeseries(db, "035420", base_price=200000)

        # 포트폴리오 생성
        portfolio_response = client.post(
            "/api/v1/phase7/portfolios",
            json={
                "portfolio_type": "SECURITY",
                "portfolio_name": "복수 종목 테스트",
                "items": [
                    {"id": "005930", "name": "삼성전자", "weight": 0.4},
                    {"id": "000660", "name": "SK하이닉스", "weight": 0.3},
                    {"id": "035420", "name": "NAVER", "weight": 0.3},
                ],
            },
            headers=auth_headers,
        )
        assert portfolio_response.status_code == 201
        portfolio_id = portfolio_response.json()["portfolio_id"]

        # 검증: 비중 합계 = 1.0
        portfolio = db.query(Phase7Portfolio).filter_by(portfolio_id=portfolio_id).first()
        total_weight = sum(float(item.weight) for item in portfolio.items)
        assert abs(total_weight - 1.0) < 0.0001

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
        eval_body = evaluation_response.json()

        # 검증: 지표 계산 정상
        assert "metrics" in eval_body
        assert eval_body["metrics"]["cumulative_return"] is not None


@pytest.mark.e2e
@pytest.mark.p1
class TestTC1_4_RebalancingOptions:
    """TC-1.4: 리밸런싱 옵션별 평가"""

    def test_rebalancing_options(self, client, db, auth_headers, test_user):
        """리밸런싱 옵션별 평가 테스트"""
        # 충분한 기간의 시계열 데이터 준비
        _seed_extended_timeseries(db, "005930", date(2024, 1, 1), days=90)
        _seed_extended_timeseries(db, "000660", date(2024, 1, 1), days=90)

        # 포트폴리오 생성
        portfolio_response = client.post(
            "/api/v1/phase7/portfolios",
            json={
                "portfolio_type": "SECURITY",
                "portfolio_name": "리밸런싱 테스트",
                "items": [
                    {"id": "005930", "name": "삼성전자", "weight": 0.5},
                    {"id": "000660", "name": "SK하이닉스", "weight": 0.5},
                ],
            },
            headers=auth_headers,
        )
        assert portfolio_response.status_code == 201
        portfolio_id = portfolio_response.json()["portfolio_id"]

        results = {}
        rebalance_options = ["NONE", "MONTHLY", "QUARTERLY"]

        for rebalance in rebalance_options:
            evaluation_response = client.post(
                "/api/v1/phase7/evaluations",
                json={
                    "portfolio_id": portfolio_id,
                    "period": {"start": "2024-01-02", "end": "2024-03-15"},
                    "rebalance": rebalance,
                },
                headers=auth_headers,
            )
            assert evaluation_response.status_code == 201, f"Rebalance {rebalance} failed"
            results[rebalance] = evaluation_response.json()

        # 검증: 각 옵션별 평가 성공
        for rebalance in rebalance_options:
            assert "metrics" in results[rebalance]
            assert results[rebalance]["disclaimer_version"] == "v2"


@pytest.mark.e2e
@pytest.mark.p0
class TestTC1_MetricsValidation:
    """평가 결과 지표 검증"""

    def test_metrics_structure(self, client, db, auth_headers, test_user):
        """평가 결과 지표 구조 검증"""
        _seed_timeseries(db, "005930", base_price=70000)

        # 포트폴리오 생성
        portfolio_response = client.post(
            "/api/v1/phase7/portfolios",
            json={
                "portfolio_type": "SECURITY",
                "portfolio_name": "지표 검증 테스트",
                "items": [
                    {"id": "005930", "name": "삼성전자", "weight": 1.0}
                ],
            },
            headers=auth_headers,
        )
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
        eval_body = evaluation_response.json()

        # 필수 지표 존재 확인
        metrics = eval_body["metrics"]
        required_metrics = ["cumulative_return", "cagr", "volatility", "max_drawdown"]
        for metric in required_metrics:
            assert metric in metrics, f"Missing metric: {metric}"
            assert metrics[metric] is not None, f"Metric {metric} is None"

        # 지표 값 타입 검증
        assert isinstance(metrics["cumulative_return"], (int, float))
        assert isinstance(metrics["cagr"], (int, float))
        assert isinstance(metrics["volatility"], (int, float))
        assert isinstance(metrics["max_drawdown"], (int, float))
