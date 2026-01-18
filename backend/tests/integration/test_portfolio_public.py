from datetime import date, datetime, timedelta

from app.models.custom_portfolio import CustomPortfolio, CustomPortfolioWeight
from app.models.performance import PerformanceResult, BenchmarkResult
from app.models.ops import ResultVersion


def _seed_portfolio(db, user_id: str) -> int:
    last_id = db.query(CustomPortfolio.portfolio_id).order_by(CustomPortfolio.portfolio_id.desc()).first()
    next_id = (last_id[0] + 1) if last_id and last_id[0] else 1
    portfolio = CustomPortfolio(
        portfolio_id=next_id,
        owner_user_id=None,
        owner_key=user_id,
        portfolio_name="Test Portfolio",
        description=None,
        is_active=True,
    )
    db.add(portfolio)

    weights = [
        CustomPortfolioWeight(
            portfolio_id=portfolio.portfolio_id,
            asset_class_code="EQUITY",
            target_weight=0.6,
        ),
        CustomPortfolioWeight(
            portfolio_id=portfolio.portfolio_id,
            asset_class_code="BOND",
            target_weight=0.4,
        ),
    ]
    db.add_all(weights)
    db.commit()
    return portfolio.portfolio_id


def _seed_live_performance(db, portfolio_id: int, created_at: datetime) -> PerformanceResult:
    entity_id = f"custom_{portfolio_id}"
    result = PerformanceResult(
        performance_type="LIVE",
        entity_type="PORTFOLIO",
        entity_id=entity_id,
        period_type="1M",
        period_start=date.today() - timedelta(days=30),
        period_end=date.today(),
        period_return=0.012,
        cumulative_return=0.089,
        result_version_id="rv-1",
        created_at=created_at,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def _seed_result_version(db, portfolio_id: int, is_active: bool) -> ResultVersion:
    entity_id = f"custom_{portfolio_id}"
    version = ResultVersion(
        result_type="PERFORMANCE",
        result_id=entity_id,
        version_no=1,
        is_active=is_active,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def test_portfolio_summary_reference_when_no_performance(client, db, test_user, auth_headers):
    portfolio_id = _seed_portfolio(db, test_user.id)

    response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/summary",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "public, max-age=300"
    payload = response.json()["data"]
    assert payload["portfolio_id"] == portfolio_id
    assert payload["is_reference"] is True
    assert payload["status_message"] is not None
    assert len(payload["assets"]) == 2


def test_portfolio_summary_and_performance_live(client, db, test_user, auth_headers):
    portfolio_id = _seed_portfolio(db, test_user.id)
    version = _seed_result_version(db, portfolio_id, is_active=True)
    performance = _seed_live_performance(db, portfolio_id, datetime.utcnow())
    performance.result_version_id = str(version.version_id)
    db.commit()

    benchmark = BenchmarkResult(
        performance_id=performance.performance_id,
        benchmark_type="INDEX",
        benchmark_code="KOSPI",
        benchmark_return=0.01,
        excess_return=0.002,
    )
    db.add(benchmark)
    db.commit()

    summary = client.get(
        f"/api/v1/portfolios/{portfolio_id}/summary",
        headers=auth_headers,
    )
    assert summary.status_code == 200
    summary_payload = summary.json()["data"]
    assert summary_payload["is_reference"] is False
    assert summary_payload["is_version_active"] is True

    performance_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/performance",
        headers=auth_headers,
    )
    assert performance_response.status_code == 200
    perf_payload = performance_response.json()["data"]
    assert perf_payload["performance_type"] == "LIVE"
    assert perf_payload["returns"]["1M"] == 0.012
    assert perf_payload["benchmark_return"] == 0.01
    assert perf_payload["selected_period"] is None

    selected_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/performance",
        headers=auth_headers,
        params={"period": "1M"},
    )
    assert selected_response.status_code == 200
    selected_payload = selected_response.json()["data"]
    assert selected_payload["selected_period"] == "1M"
    assert selected_payload["selected_return"] == 0.012

    explanation_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/performance/explanation",
        headers=auth_headers,
    )
    assert explanation_response.status_code == 200
    explanation_payload = explanation_response.json()["data"]
    assert explanation_payload["price_basis"] == "close"
    assert len(explanation_payload["disclaimer"]) == 3

    why_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/explain/why",
        headers=auth_headers,
    )
    assert why_response.status_code == 200
    why_payload = why_response.json()["data"]
    assert why_payload["title"]
    assert len(why_payload["disclaimer"]) == 3


def test_portfolio_summary_reflects_active_version_switch(client, db, test_user, auth_headers):
    portfolio_id = _seed_portfolio(db, test_user.id)
    version_old = _seed_result_version(db, portfolio_id, is_active=True)
    perf_old = _seed_live_performance(db, portfolio_id, datetime.utcnow() - timedelta(days=2))
    perf_old.result_version_id = str(version_old.version_id)

    version_old.is_active = False
    version_new = _seed_result_version(db, portfolio_id, is_active=True)
    version_new.version_no = 2
    perf_new = _seed_live_performance(db, portfolio_id, datetime.utcnow())
    perf_new.result_version_id = str(version_new.version_id)
    db.commit()

    summary = client.get(
        f"/api/v1/portfolios/{portfolio_id}/summary",
        headers=auth_headers,
    )
    assert summary.status_code == 200
    payload = summary.json()["data"]
    assert payload["is_reference"] is False
    assert payload["is_version_active"] is True
