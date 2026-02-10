from datetime import date

from app.models.phase7_portfolio import Phase7Portfolio, Phase7PortfolioItem
from decimal import Decimal

from app.models.real_data import StockPriceDaily


def _seed_timeseries(db, ticker: str) -> None:
    rows = [
        StockPriceDaily(
            ticker=ticker,
            trade_date=date(2024, 1, 2),
            open_price=Decimal('100.00'),
            high_price=Decimal('105.00'),
            low_price=Decimal('99.00'),
            close_price=Decimal('101.00'),
            volume=1000,
            source_id='PYKRX',
            as_of_date=date(2024, 1, 2),
            quality_flag='NORMAL',
        ),
        StockPriceDaily(
            ticker=ticker,
            trade_date=date(2024, 1, 3),
            open_price=Decimal('101.00'),
            high_price=Decimal('103.00'),
            low_price=Decimal('100.00'),
            close_price=Decimal('102.00'),
            volume=1100,
            source_id='PYKRX',
            as_of_date=date(2024, 1, 3),
            quality_flag='NORMAL',
        ),
        StockPriceDaily(
            ticker=ticker,
            trade_date=date(2024, 1, 4),
            open_price=Decimal('102.00'),
            high_price=Decimal('104.00'),
            low_price=Decimal('101.00'),
            close_price=Decimal('103.00'),
            volume=1200,
            source_id='PYKRX',
            as_of_date=date(2024, 1, 4),
            quality_flag='NORMAL',
        ),
    ]
    db.add_all(rows)
    db.commit()


def _seed_portfolio(db, user_id: str, ticker: str, name: str) -> Phase7Portfolio:
    portfolio = Phase7Portfolio(
        owner_user_id=user_id,
        portfolio_type="SECURITY",
        portfolio_name=name,
    )
    db.add(portfolio)
    db.flush()

    item = Phase7PortfolioItem(
        portfolio_id=portfolio.portfolio_id,
        item_key=ticker,
        item_name=name,
        weight=1.0,
    )
    db.add(item)
    db.commit()
    db.refresh(portfolio)
    return portfolio


def _run_evaluation(client, portfolio_id: int, auth_headers) -> None:
    response = client.post(
        "/api/v1/phase7/evaluations",
        json={
            "portfolio_id": portfolio_id,
            "period": {"start": "2024-01-02", "end": "2024-01-04"},
            "rebalance": "NONE",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201


def test_phase7_comparison_latest_results(client, db, auth_headers, test_user):
    _seed_timeseries(db, "000001")
    _seed_timeseries(db, "000002")

    portfolio_a = _seed_portfolio(db, test_user.id, "000001", "포트폴리오 A")
    portfolio_b = _seed_portfolio(db, test_user.id, "000002", "포트폴리오 B")

    _run_evaluation(client, portfolio_a.portfolio_id, auth_headers)
    _run_evaluation(client, portfolio_b.portfolio_id, auth_headers)

    response = client.post(
        "/api/v1/phase7/comparisons",
        json={"portfolio_ids": [portfolio_a.portfolio_id, portfolio_b.portfolio_id]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert body["portfolios"][0]["disclaimer_version"] == "v2"


def test_phase7_comparison_requires_evaluations(client, db, auth_headers, test_user):
    _seed_timeseries(db, "000010")
    _seed_timeseries(db, "000011")

    portfolio_a = _seed_portfolio(db, test_user.id, "000010", "포트폴리오 C")
    portfolio_b = _seed_portfolio(db, test_user.id, "000011", "포트폴리오 D")

    response = client.post(
        "/api/v1/phase7/comparisons",
        json={"portfolio_ids": [portfolio_a.portfolio_id, portfolio_b.portfolio_id]},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_phase7_comparison_missing_portfolio(client, auth_headers):
    response = client.post(
        "/api/v1/phase7/comparisons",
        json={"portfolio_ids": [99991, 99992]},
        headers=auth_headers,
    )
    assert response.status_code == 404
