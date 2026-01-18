from datetime import date
import uuid

from app.models.performance import PerformanceResult, PerformanceBasis, PerformancePublicView


def _create_performance_result(db, performance_type: str) -> PerformanceResult:
    performance_id = str(uuid.uuid4())
    result = PerformanceResult(
        performance_id=performance_id,
        performance_type=performance_type,
        entity_type="PORTFOLIO",
        entity_id="portfolio_001",
        period_type="MONTHLY",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 31),
        period_return=0.05,
        cumulative_return=0.05,
        annualized_return=0.6,
        volatility=0.2,
        mdd=-0.1,
        sharpe_ratio=1.1,
        sortino_ratio=1.4,
        snapshot_ids=[],
        calc_params={},
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def test_public_performance_live_only(client, db, auth_headers):
    live_result = _create_performance_result(db, "LIVE")
    _create_performance_result(db, "SIM")

    db.add(
        PerformanceBasis(
            performance_id=live_result.performance_id,
            price_basis="CLOSE",
            include_fee=True,
            include_tax=False,
            include_dividend=False,
            notes="테스트 기준",
        )
    )
    db.add(
        PerformancePublicView(
            performance_id=live_result.performance_id,
            headline_json={"summary": "LIVE 성과 요약"},
            disclaimer_text="테스트 면책 문구",
        )
    )
    db.commit()

    response = client.get("/api/performance/public", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert len(payload["data"]) == 1
    item = payload["data"][0]
    assert item["performance_type"] == "LIVE"
    assert item["headline"]["summary"] == "LIVE 성과 요약"
    assert item["disclaimer"] == "테스트 면책 문구"


def test_internal_performance_admin_only(client, db, admin_headers, auth_headers):
    _create_performance_result(db, "LIVE")
    _create_performance_result(db, "SIM")

    response = client.get("/internal/performance/results", headers=auth_headers)
    assert response.status_code == 403

    response = client.get("/internal/performance/results", headers=admin_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert len(payload["data"]) == 2
