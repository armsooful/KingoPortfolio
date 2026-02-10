"""
Phase 9 E2E 테스트: 입력 오류/누락/극단값 처리 (TC-3.x)

입력 검증 및 오류 처리를 검증한다.
"""

from datetime import date, timedelta

import pytest

from app.models.phase7_portfolio import Phase7Portfolio, Phase7PortfolioItem
from decimal import Decimal

from app.models.real_data import StockPriceDaily


def _get_error_message(response) -> str:
    """에러 응답에서 메시지 추출 (다양한 형식 지원)"""
    body = response.json()
    # 형식 1: {"detail": "..."}
    if "detail" in body:
        return body["detail"]
    # 형식 2: {"error": {"message": "..."}}
    if "error" in body and isinstance(body["error"], dict):
        return body["error"].get("message", "")
    return str(body)


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
class TestTC3_1_InvalidPeriodStartAfterEnd:
    """TC-3.1: 잘못된 평가 기간 (start >= end)"""

    def test_invalid_period_start_after_end(self, client, db, auth_headers, test_user):
        """시작일이 종료일보다 늦은 경우"""
        _seed_timeseries(db, "005930")
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "기간 오류 테스트")

        response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": "2024-01-10", "end": "2024-01-05"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )

        # 검증: 400 Bad Request
        assert response.status_code == 400
        assert "기간" in _get_error_message(response)

    def test_invalid_period_same_date(self, client, db, auth_headers, test_user):
        """시작일과 종료일이 동일한 경우"""
        _seed_timeseries(db, "005930")
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "동일 날짜 테스트")

        response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": "2024-01-05", "end": "2024-01-05"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )

        # 검증: 400 Bad Request
        assert response.status_code == 400


@pytest.mark.e2e
@pytest.mark.p0
class TestTC3_2_FutureDatePeriod:
    """TC-3.2: 미래 날짜 지정"""

    def test_future_end_date(self, client, db, auth_headers, test_user):
        """종료일이 미래인 경우"""
        _seed_timeseries(db, "005930")
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "미래 날짜 테스트")

        future_date = (date.today() + timedelta(days=365)).isoformat()

        response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": "2024-01-01", "end": future_date},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )

        # 검증: 400 Bad Request
        assert response.status_code == 400
        assert "기간" in _get_error_message(response)

    def test_both_dates_in_future(self, client, db, auth_headers, test_user):
        """시작일과 종료일 모두 미래인 경우"""
        _seed_timeseries(db, "005930")
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "미래 기간 테스트")

        future_start = (date.today() + timedelta(days=30)).isoformat()
        future_end = (date.today() + timedelta(days=60)).isoformat()

        response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": future_start, "end": future_end},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )

        # 검증: 400 Bad Request
        assert response.status_code == 400


@pytest.mark.e2e
@pytest.mark.p0
class TestTC3_3_NonexistentPortfolio:
    """TC-3.3: 존재하지 않는 포트폴리오 ID"""

    def test_nonexistent_portfolio_id(self, client, db, auth_headers, test_user):
        """존재하지 않는 포트폴리오 ID로 평가 시도"""
        response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": 99999,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )

        # 검증: 404 Not Found
        assert response.status_code == 404
        assert "포트폴리오" in _get_error_message(response)

    def test_negative_portfolio_id(self, client, db, auth_headers, test_user):
        """음수 포트폴리오 ID"""
        response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": -1,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )

        # 검증: 404 Not Found 또는 422 Validation Error
        assert response.status_code in [404, 422]


@pytest.mark.e2e
@pytest.mark.p1
class TestTC3_4_InvalidWeightSum:
    """TC-3.4: 비중 합계 != 100%"""

    def test_weight_sum_less_than_100(self, client, db, auth_headers, test_user):
        """비중 합계가 100% 미만"""
        _seed_timeseries(db, "005930")
        _seed_timeseries(db, "000660")

        response = client.post(
            "/api/v1/phase7/portfolios",
            json={
                "portfolio_type": "SECURITY",
                "portfolio_name": "비중 부족 테스트",
                "items": [
                    {"id": "005930", "name": "삼성전자", "weight": 0.3},
                    {"id": "000660", "name": "SK하이닉스", "weight": 0.3},
                ],
            },
            headers=auth_headers,
        )

        # 검증: 400 Bad Request
        assert response.status_code == 400
        assert "비중" in _get_error_message(response)

    def test_weight_sum_greater_than_100(self, client, db, auth_headers, test_user):
        """비중 합계가 100% 초과"""
        _seed_timeseries(db, "005930")
        _seed_timeseries(db, "000660")

        response = client.post(
            "/api/v1/phase7/portfolios",
            json={
                "portfolio_type": "SECURITY",
                "portfolio_name": "비중 초과 테스트",
                "items": [
                    {"id": "005930", "name": "삼성전자", "weight": 0.6},
                    {"id": "000660", "name": "SK하이닉스", "weight": 0.6},
                ],
            },
            headers=auth_headers,
        )

        # 검증: 400 Bad Request
        assert response.status_code == 400
        assert "비중" in _get_error_message(response)

    def test_weight_exactly_100_with_rounding(self, client, db, auth_headers, test_user):
        """비중 합계가 정확히 100% (소수점 반올림)"""
        _seed_timeseries(db, "005930")
        _seed_timeseries(db, "000660")
        _seed_timeseries(db, "035420")

        response = client.post(
            "/api/v1/phase7/portfolios",
            json={
                "portfolio_type": "SECURITY",
                "portfolio_name": "정확한 비중 테스트",
                "items": [
                    {"id": "005930", "name": "삼성전자", "weight": 0.3333},
                    {"id": "000660", "name": "SK하이닉스", "weight": 0.3333},
                    {"id": "035420", "name": "NAVER", "weight": 0.3334},
                ],
            },
            headers=auth_headers,
        )

        # 검증: 201 Created (허용 오차 내)
        assert response.status_code == 201


@pytest.mark.e2e
@pytest.mark.p1
class TestTC3_5_NoDataForSecurity:
    """TC-3.5: 데이터 없는 종목"""

    def test_no_timeseries_data(self, client, db, auth_headers, test_user):
        """시계열 데이터가 없는 종목으로 평가"""
        # 시계열 데이터 없이 포트폴리오 생성
        portfolio_response = client.post(
            "/api/v1/phase7/portfolios",
            json={
                "portfolio_type": "SECURITY",
                "portfolio_name": "데이터 없음 테스트",
                "items": [{"id": "NODATA", "name": "데이터 없는 종목", "weight": 1.0}],
            },
            headers=auth_headers,
        )
        assert portfolio_response.status_code == 201
        portfolio_id = portfolio_response.json()["portfolio_id"]

        # 평가 시도
        response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )

        # 검증: 400 Bad Request (데이터 부족)
        assert response.status_code == 400

    def test_partial_data_for_period(self, client, db, auth_headers, test_user):
        """요청 기간에 부분적인 데이터만 존재"""
        # 짧은 기간의 데이터만 생성
        _seed_timeseries(db, "PARTIAL", base_price=100.0)

        portfolio_response = client.post(
            "/api/v1/phase7/portfolios",
            json={
                "portfolio_type": "SECURITY",
                "portfolio_name": "부분 데이터 테스트",
                "items": [{"id": "PARTIAL", "name": "부분 데이터 종목", "weight": 1.0}],
            },
            headers=auth_headers,
        )
        portfolio_id = portfolio_response.json()["portfolio_id"]

        # 데이터 범위를 벗어난 기간으로 평가 시도
        response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": "2023-01-01", "end": "2023-12-31"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )

        # 검증: 400 Bad Request (데이터 부족) 또는 일부 성공
        assert response.status_code in [200, 201, 400]


@pytest.mark.e2e
@pytest.mark.p1
class TestTC3_6_ExtremePeriod:
    """TC-3.6: 극단값 입력 (매우 긴 기간)"""

    def test_very_long_period(self, client, db, auth_headers, test_user):
        """매우 긴 기간 요청"""
        _seed_timeseries(db, "005930")
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "긴 기간 테스트")

        response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": "2000-01-01", "end": "2024-12-31"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )

        # 데이터 존재 시 성공, 없으면 400
        assert response.status_code in [200, 201, 400]

    def test_single_day_period(self, client, db, auth_headers, test_user):
        """하루짜리 기간 (최소 기간)"""
        _seed_timeseries(db, "005930")
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "하루 기간 테스트")

        response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": "2024-01-02", "end": "2024-01-03"},
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )

        # 최소 기간 허용 여부에 따라 결과 달라짐
        assert response.status_code in [200, 201, 400]


@pytest.mark.e2e
@pytest.mark.p1
class TestTC3_MalformedInput:
    """잘못된 형식의 입력"""

    def test_invalid_date_format(self, client, db, auth_headers, test_user):
        """잘못된 날짜 형식"""
        _seed_timeseries(db, "005930")
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "날짜 형식 테스트")

        response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": "01-02-2024", "end": "01-06-2024"},  # 잘못된 형식
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )

        # 검증: 422 Validation Error
        assert response.status_code == 422

    def test_invalid_rebalance_option(self, client, db, auth_headers, test_user):
        """잘못된 리밸런싱 옵션"""
        _seed_timeseries(db, "005930")
        portfolio_id = _create_portfolio(client, auth_headers, "005930", "리밸런싱 옵션 테스트")

        response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": portfolio_id,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "INVALID_OPTION",
            },
            headers=auth_headers,
        )

        # 검증: 422 Validation Error
        assert response.status_code == 422

    def test_missing_required_field(self, client, db, auth_headers, test_user):
        """필수 필드 누락"""
        response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": 1,
                # period 누락
                "rebalance": "NONE",
            },
            headers=auth_headers,
        )

        # 검증: 422 Validation Error
        assert response.status_code == 422

    def test_empty_items_list(self, client, db, auth_headers, test_user):
        """빈 종목 목록"""
        response = client.post(
            "/api/v1/phase7/portfolios",
            json={
                "portfolio_type": "SECURITY",
                "portfolio_name": "빈 종목 테스트",
                "items": [],
            },
            headers=auth_headers,
        )

        # 검증: 400 또는 422
        assert response.status_code in [400, 422]


@pytest.mark.e2e
@pytest.mark.p1
class TestTC3_AuthenticationErrors:
    """인증 관련 오류"""

    def test_no_auth_header(self, client, db):
        """인증 헤더 없음"""
        response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": 1,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "NONE",
            },
        )

        # 검증: 401 Unauthorized
        assert response.status_code == 401

    def test_invalid_token(self, client, db):
        """잘못된 토큰"""
        response = client.post(
            "/api/v1/phase7/evaluations",
            json={
                "portfolio_id": 1,
                "period": {"start": "2024-01-02", "end": "2024-01-06"},
                "rebalance": "NONE",
            },
            headers={"Authorization": "Bearer invalid_token_here"},
        )

        # 검증: 401 Unauthorized
        assert response.status_code == 401
