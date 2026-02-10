"""
Phase 9 E2E 테스트: 로그·감사 이벤트 검증 (TC-6.x)

로그 및 감사 이벤트의 정상 기록을 검증한다.
"""

from datetime import date
import json

import pytest

from app.models.phase7_evaluation import Phase7EvaluationRun
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
class TestTC6_1_EvaluationAuditLog:
    """TC-6.1: 평가 실행 시 감사 로그 생성"""

    def test_evaluation_creates_db_record(self, client, db, auth_headers, test_user):
        """평가 실행 시 DB에 레코드 생성"""
        _seed_timeseries(db, "005930", base_price=70000)
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "감사 로그 테스트")

        # 평가 실행
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

        # DB에서 직접 확인
        evaluation = (
            db.query(Phase7EvaluationRun)
            .filter(Phase7EvaluationRun.portfolio_id == portfolio_id)
            .first()
        )

        # 검증: 레코드 존재
        assert evaluation is not None

        # 검증: owner_user_id 기록
        assert evaluation.owner_user_id == test_user.id

        # 검증: 기간 기록
        assert evaluation.period_start == date(2024, 1, 2)
        assert evaluation.period_end == date(2024, 1, 6)

        # 검증: 리밸런싱 옵션 기록
        assert evaluation.rebalance == "NONE"

    def test_evaluation_records_result_hash(self, client, db, auth_headers, test_user):
        """평가 결과 해시가 기록됨"""
        _seed_timeseries(db, "005930", base_price=70000)
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "해시 기록 테스트")

        # 평가 실행
        client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )

        # DB에서 확인
        evaluation = (
            db.query(Phase7EvaluationRun)
            .filter(Phase7EvaluationRun.portfolio_id == portfolio_id)
            .first()
        )

        # 검증: result_hash 존재
        assert evaluation.result_hash is not None
        assert len(evaluation.result_hash) > 0

    def test_evaluation_stores_complete_result(self, client, db, auth_headers, test_user):
        """평가 결과가 완전하게 저장됨"""
        _seed_timeseries(db, "005930", base_price=70000)
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "완전 저장 테스트")

        # 평가 실행
        api_response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )
        api_result = api_response.json()

        # DB에서 확인
        evaluation = (
            db.query(Phase7EvaluationRun)
            .filter(Phase7EvaluationRun.portfolio_id == portfolio_id)
            .first()
        )

        # 검증: result_json 존재
        assert evaluation.result_json is not None

        # 검증: JSON 파싱 가능
        db_result = json.loads(evaluation.result_json)

        # 검증: 주요 필드 일치
        assert db_result["metrics"]["cumulative_return"] == api_result["metrics"]["cumulative_return"]
        assert db_result["disclaimer_version"] == api_result["disclaimer_version"]


@pytest.mark.e2e
@pytest.mark.p1
class TestTC6_2_UserActionEvents:
    """TC-6.2: 사용자 액션 이벤트 기록"""

    def test_portfolio_creation_tracked(self, client, db, auth_headers, test_user):
        """포트폴리오 생성 이벤트 추적"""
        _seed_timeseries(db, "005930", base_price=70000)

        # 포트폴리오 생성 전 개수
        from app.models.phase7_portfolio import Phase7Portfolio
        before_count = db.query(Phase7Portfolio).filter(
            Phase7Portfolio.owner_user_id == test_user.id
        ).count()

        # 포트폴리오 생성
        _create_portfolio(client, auth_headers, "005930", "이벤트 추적 테스트")

        # 포트폴리오 생성 후 개수
        after_count = db.query(Phase7Portfolio).filter(
            Phase7Portfolio.owner_user_id == test_user.id
        ).count()

        # 검증: 포트폴리오 1개 증가
        assert after_count == before_count + 1

    def test_evaluation_history_tracked(self, client, db, auth_headers, test_user):
        """평가 이력 추적"""
        _seed_timeseries(db, "005930", base_price=70000)
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "이력 추적 테스트")

        # 평가 3회 실행
        for i in range(3):
            client.post(
                "/api/v1/phase7/evaluations",
                json={
                    "portfolio_id": portfolio_id,
                    "period": {"start": "2024-01-02", "end": "2024-01-06"},
                    "rebalance": "NONE",
                },
                headers=auth_headers,
            )

        # 이력 확인
        history_response = client.get(
            "/api/v1/phase7/evaluations",
            params={"portfolio_id": portfolio_id},
            headers=auth_headers,
        )

        # 검증: 3개 이력 존재
        assert history_response.json()["count"] == 3

    def test_evaluation_timestamp_recorded(self, client, db, auth_headers, test_user):
        """평가 타임스탬프 기록"""
        _seed_timeseries(db, "005930", base_price=70000)
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "타임스탬프 테스트")

        # 평가 실행
        client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )

        # DB에서 확인
        evaluation = (
            db.query(Phase7EvaluationRun)
            .filter(Phase7EvaluationRun.portfolio_id == portfolio_id)
            .first()
        )

        # 검증: created_at 존재
        assert evaluation.created_at is not None


@pytest.mark.e2e
@pytest.mark.p1
class TestTC6_QueryAuditTrail:
    """조회 감사 추적"""

    def test_evaluation_detail_accessible(self, client, db, auth_headers, test_user):
        """평가 상세 조회 가능"""
        _seed_timeseries(db, "005930", base_price=70000)
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "상세 조회 테스트")

        # 평가 실행
        client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )

        # 이력에서 evaluation_id 조회
        history = client.get(
            "/api/v1/phase7/evaluations",
            params={"portfolio_id": portfolio_id},
            headers=auth_headers,
        )
        evaluation_id = history.json()["evaluations"][0]["evaluation_id"]

        # 상세 조회
        detail = client.get(
            f"/api/v1/phase7/evaluations/{evaluation_id}",
            headers=auth_headers,
        )

        # 검증: 조회 성공
        assert detail.status_code == 200
        assert detail.json()["evaluation_id"] == evaluation_id

    def test_history_returns_all_evaluations(self, client, db, auth_headers, test_user):
        """이력 조회 시 모든 평가 반환"""
        _seed_timeseries(db, "005930", base_price=70000)
        _seed_timeseries(db, "000660", base_price=120000)

        portfolio_1 = _create_portfolio(client, auth_headers, "005930", "이력 테스트 1")
        portfolio_2 = _create_portfolio(client, auth_headers, "000660", "이력 테스트 2")

        # 각 포트폴리오에 평가 실행
        for pid in [portfolio_1, portfolio_2]:
            client.post(
                "/api/v1/phase7/evaluations",
                json={
                    "portfolio_id": pid,
                    "period": {"start": "2024-01-02", "end": "2024-01-06"},
                    "rebalance": "NONE",
                },
                headers=auth_headers,
            )

        # 전체 이력 조회
        history = client.get(
            "/api/v1/phase7/evaluations",
            headers=auth_headers,
        )

        # 검증: 2개 이상 반환
        assert history.json()["count"] >= 2


@pytest.mark.e2e
@pytest.mark.p1
class TestTC6_DataIntegrity:
    """데이터 무결성 검증"""

    def test_stored_result_matches_api_response(self, client, db, auth_headers, test_user):
        """저장된 결과와 API 응답 일치"""
        _seed_timeseries(db, "005930", base_price=70000)
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "무결성 테스트")

        # 평가 실행
        api_response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )
        api_result = api_response.json()

        # 이력에서 조회
        history = client.get(
            "/api/v1/phase7/evaluations",
            params={"portfolio_id": portfolio_id},
            headers=auth_headers,
        )
        evaluation_id = history.json()["evaluations"][0]["evaluation_id"]

        # 상세 조회
        detail = client.get(
            f"/api/v1/phase7/evaluations/{evaluation_id}",
            headers=auth_headers,
        )
        stored_result = detail.json()["result"]

        # 검증: 주요 필드 일치
        assert stored_result["metrics"]["cumulative_return"] == api_result["metrics"]["cumulative_return"]
        assert stored_result["metrics"]["cagr"] == api_result["metrics"]["cagr"]
        assert stored_result["metrics"]["volatility"] == api_result["metrics"]["volatility"]
        assert stored_result["metrics"]["max_drawdown"] == api_result["metrics"]["max_drawdown"]
        assert stored_result["disclaimer_version"] == api_result["disclaimer_version"]
