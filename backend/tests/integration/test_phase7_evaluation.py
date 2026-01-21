from datetime import date

from app.models.phase7_portfolio import Phase7Portfolio, Phase7PortfolioItem
from app.models.securities import KrxTimeSeries


def _seed_timeseries(db, ticker: str) -> None:
    rows = [
        KrxTimeSeries(
            ticker=ticker,
            date=date(2024, 1, 2),
            open=100.0,
            high=105.0,
            low=99.0,
            close=101.0,
            volume=1000,
        ),
        KrxTimeSeries(
            ticker=ticker,
            date=date(2024, 1, 3),
            open=101.0,
            high=103.0,
            low=100.0,
            close=102.0,
            volume=1100,
        ),
        KrxTimeSeries(
            ticker=ticker,
            date=date(2024, 1, 4),
            open=102.0,
            high=104.0,
            low=101.0,
            close=103.0,
            volume=1200,
        ),
    ]
    db.add_all(rows)
    db.commit()


def _seed_portfolio(db, user_id: str, ticker: str) -> Phase7Portfolio:
    portfolio = Phase7Portfolio(
        owner_user_id=user_id,
        portfolio_type="SECURITY",
        portfolio_name="테스트 포트폴리오",
    )
    db.add(portfolio)
    db.flush()

    item = Phase7PortfolioItem(
        portfolio_id=portfolio.portfolio_id,
        item_key=ticker,
        item_name="테스트 종목",
        weight=1.0,
    )
    db.add(item)
    db.commit()
    db.refresh(portfolio)
    return portfolio


def test_phase7_evaluation_flow(client, db, auth_headers, test_user):
    ticker = "000001"
    _seed_timeseries(db, ticker)
    portfolio = _seed_portfolio(db, test_user.id, ticker)

    response = client.post(
        "/api/v1/phase7/evaluations",
        json={
            "portfolio_id": portfolio.portfolio_id,
            "period": {"start": "2024-01-02", "end": "2024-01-04"},
            "rebalance": "NONE",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["disclaimer_version"] == "v2"
    assert "metrics" in body

    list_response = client.get(
        "/api/v1/phase7/evaluations",
        headers=auth_headers,
    )
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["count"] >= 1
    assert list_body["evaluations"][0]["result_hash"]

    evaluation_id = list_body["evaluations"][0]["evaluation_id"]
    detail_response = client.get(
        f"/api/v1/phase7/evaluations/{evaluation_id}",
        headers=auth_headers,
    )
    assert detail_response.status_code == 200
    detail_body = detail_response.json()
    assert detail_body["result"]["disclaimer_version"] == "v2"
    assert detail_body["result_hash"]


def test_phase7_evaluation_invalid_period(client, db, auth_headers, test_user):
    ticker = "000003"
    _seed_timeseries(db, ticker)
    portfolio = _seed_portfolio(db, test_user.id, ticker)

    response = client.post(
        "/api/v1/phase7/evaluations",
        json={
            "portfolio_id": portfolio.portfolio_id,
            "period": {"start": "2024-01-04", "end": "2024-01-02"},
            "rebalance": "NONE",
        },
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_phase7_evaluation_missing_portfolio(client, auth_headers):
    response = client.post(
        "/api/v1/phase7/evaluations",
        json={
            "portfolio_id": 99999,
            "period": {"start": "2024-01-02", "end": "2024-01-04"},
            "rebalance": "NONE",
        },
        headers=auth_headers,
    )
    assert response.status_code == 404
