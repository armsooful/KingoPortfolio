"""
U-2 공개 API 단위 테스트 (성과 히스토리/기간 비교/지표 상세)
"""

from datetime import date

from sqlalchemy import func

from app.models.custom_portfolio import CustomPortfolio
from app.models.performance import PerformanceResult, PerformanceBasis


def _create_portfolio(db, owner_user_id: str, name: str = "Test Portfolio") -> CustomPortfolio:
    next_id = db.query(func.max(CustomPortfolio.portfolio_id)).scalar() or 0
    portfolio = CustomPortfolio(
        portfolio_id=next_id + 1,
        owner_user_id=None,
        owner_key=str(owner_user_id),
        portfolio_name=name,
        description="test",
    )
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio


def _create_user(db, email: str):
    from app.models.user import User
    user = User(
        email=email,
        hashed_password="hashed",
        is_admin=False,
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_performance_result(
    db,
    portfolio_id: int,
    period_type: str,
    period_start: date,
    period_end: date,
    period_return: float,
    cumulative_return: float,
    annualized_return: float | None = None,
):
    result = PerformanceResult(
        performance_type="LIVE",
        entity_type="PORTFOLIO",
        entity_id=f"custom_{portfolio_id}",
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        period_return=period_return,
        cumulative_return=cumulative_return,
        annualized_return=annualized_return,
        snapshot_ids=[],
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def test_performance_history_returns_items(client, auth_headers, db, test_user):
    portfolio = _create_portfolio(db, owner_user_id=test_user.id)
    _create_performance_result(
        db,
        portfolio_id=portfolio.portfolio_id,
        period_type="MONTHLY",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 31),
        period_return=0.01,
        cumulative_return=0.01,
    )

    response = client.get(
        f"/api/v1/portfolios/{portfolio.portfolio_id}/performance/history?interval=MONTHLY",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["interval"] == "MONTHLY"
    assert len(data["items"]) == 1


def test_performance_history_invalid_interval(client, auth_headers, db, test_user):
    portfolio = _create_portfolio(db, owner_user_id=test_user.id)
    response = client.get(
        f"/api/v1/portfolios/{portfolio.portfolio_id}/performance/history?interval=YEARLY",
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_performance_compare_summary(client, auth_headers, db, test_user):
    portfolio = _create_portfolio(db, owner_user_id=test_user.id)
    _create_performance_result(
        db,
        portfolio_id=portfolio.portfolio_id,
        period_type="MONTHLY",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 6, 30),
        period_return=0.05,
        cumulative_return=0.12,
    )
    _create_performance_result(
        db,
        portfolio_id=portfolio.portfolio_id,
        period_type="MONTHLY",
        period_start=date(2023, 1, 1),
        period_end=date(2023, 6, 30),
        period_return=0.01,
        cumulative_return=0.04,
    )

    response = client.get(
        f"/api/v1/portfolios/{portfolio.portfolio_id}/performance/compare"
        "?left_from=2024-01-01&left_to=2024-06-30"
        "&right_from=2023-01-01&right_to=2023-06-30",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["summary"] == "좌측 기간의 수익률이 우측 기간보다 높습니다."


def test_metric_detail_returns_value(client, auth_headers, db, test_user):
    portfolio = _create_portfolio(db, owner_user_id=test_user.id)
    result = _create_performance_result(
        db,
        portfolio_id=portfolio.portfolio_id,
        period_type="MONTHLY",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 31),
        period_return=0.01,
        cumulative_return=0.02,
        annualized_return=0.08,
    )
    basis = PerformanceBasis(
        performance_id=result.performance_id,
        price_basis="CLOSE",
        include_fee=True,
        include_tax=False,
        include_dividend=True,
        fx_snapshot_id=None,
    )
    db.add(basis)
    db.commit()

    response = client.get(
        f"/api/v1/portfolios/{portfolio.portfolio_id}/metrics/cagr",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["metric_key"] == "cagr"
    assert data["value"] == 0.08


def test_metric_detail_invalid_key(client, auth_headers, db, test_user):
    portfolio = _create_portfolio(db, owner_user_id=test_user.id)
    response = client.get(
        f"/api/v1/portfolios/{portfolio.portfolio_id}/metrics/invalid",
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_metric_detail_null_value_sets_status_message(client, auth_headers, db, test_user):
    portfolio = _create_portfolio(db, owner_user_id=test_user.id)
    _create_performance_result(
        db,
        portfolio_id=portfolio.portfolio_id,
        period_type="MONTHLY",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 31),
        period_return=0.01,
        cumulative_return=0.02,
        annualized_return=None,
    )

    response = client.get(
        f"/api/v1/portfolios/{portfolio.portfolio_id}/metrics/cagr",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["value"] is None
    assert data["status_message"] == "해당 지표 데이터가 아직 준비되지 않았습니다."


def test_u2_endpoints_forbidden_for_other_user(client, auth_headers, db, test_user):
    other_user = _create_user(db, "other_user@example.com")
    portfolio = _create_portfolio(db, owner_user_id=other_user.id)

    endpoints = [
        f"/api/v1/portfolios/{portfolio.portfolio_id}/performance/history",
        f"/api/v1/portfolios/{portfolio.portfolio_id}/performance/compare"
        "?left_from=2024-01-01&left_to=2024-06-30"
        "&right_from=2023-01-01&right_to=2023-06-30",
        f"/api/v1/portfolios/{portfolio.portfolio_id}/metrics/cagr",
    ]

    for endpoint in endpoints:
        response = client.get(endpoint, headers=auth_headers)
        assert response.status_code == 404


def test_performance_history_empty_returns_reference(client, auth_headers, db, test_user):
    portfolio = _create_portfolio(db, owner_user_id=test_user.id)
    response = client.get(
        f"/api/v1/portfolios/{portfolio.portfolio_id}/performance/history",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["items"] == []
    assert data["is_reference"] is True


def test_performance_compare_missing_side_returns_reference(client, auth_headers, db, test_user):
    portfolio = _create_portfolio(db, owner_user_id=test_user.id)
    _create_performance_result(
        db,
        portfolio_id=portfolio.portfolio_id,
        period_type="MONTHLY",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 6, 30),
        period_return=0.05,
        cumulative_return=0.12,
    )

    response = client.get(
        f"/api/v1/portfolios/{portfolio.portfolio_id}/performance/compare"
        "?left_from=2024-01-01&left_to=2024-06-30"
        "&right_from=2023-01-01&right_to=2023-06-30",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["is_reference"] is True
    assert data["summary"] == "비교할 데이터가 충분하지 않습니다."


def test_performance_history_invalid_date_range(client, auth_headers, db, test_user):
    portfolio = _create_portfolio(db, owner_user_id=test_user.id)
    response = client.get(
        f"/api/v1/portfolios/{portfolio.portfolio_id}/performance/history"
        "?from=2024-02-01&to=2024-01-01",
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_performance_history_invalid_limit(client, auth_headers, db, test_user):
    portfolio = _create_portfolio(db, owner_user_id=test_user.id)
    response = client.get(
        f"/api/v1/portfolios/{portfolio.portfolio_id}/performance/history?limit=0",
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_performance_compare_invalid_date_range(client, auth_headers, db, test_user):
    portfolio = _create_portfolio(db, owner_user_id=test_user.id)
    response = client.get(
        f"/api/v1/portfolios/{portfolio.portfolio_id}/performance/compare"
        "?left_from=2024-02-01&left_to=2024-01-01"
        "&right_from=2023-01-01&right_to=2023-06-30",
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_performance_history_interval_case_insensitive(client, auth_headers, db, test_user):
    portfolio = _create_portfolio(db, owner_user_id=test_user.id)
    response = client.get(
        f"/api/v1/portfolios/{portfolio.portfolio_id}/performance/history?interval=monthly",
        headers=auth_headers,
    )
    assert response.status_code == 200


def test_performance_compare_no_data_returns_reference(client, auth_headers, db, test_user):
    portfolio = _create_portfolio(db, owner_user_id=test_user.id)
    response = client.get(
        f"/api/v1/portfolios/{portfolio.portfolio_id}/performance/compare"
        "?left_from=2024-01-01&left_to=2024-06-30"
        "&right_from=2023-01-01&right_to=2023-06-30",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["is_reference"] is True
    assert data["summary"] == "비교할 데이터가 충분하지 않습니다."
