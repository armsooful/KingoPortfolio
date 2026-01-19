"""
U-1 ~ U-3 사용자 플로우 E2E
"""

from datetime import date, timedelta

from sqlalchemy import func

from app.models.custom_portfolio import CustomPortfolio


def _create_portfolio(db, owner_user_id: str) -> CustomPortfolio:
    next_id = db.query(func.max(CustomPortfolio.portfolio_id)).scalar() or 0
    portfolio = CustomPortfolio(
        portfolio_id=next_id + 1,
        owner_user_id=None,
        owner_key=str(owner_user_id),
        portfolio_name="E2E Portfolio",
        description="e2e",
    )
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio


def test_u1_u3_end_to_end_flow(client, auth_headers, db, test_user):
    portfolio = _create_portfolio(db, test_user.id)

    response = client.get(
        f"/api/v1/portfolios/{portfolio.portfolio_id}/summary",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

    response = client.get(
        f"/api/v1/portfolios/{portfolio.portfolio_id}/performance/history",
        headers=auth_headers,
        params={"interval": "MONTHLY"},
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

    today = date.today()
    response = client.get(
        f"/api/v1/portfolios/{portfolio.portfolio_id}/performance/compare",
        headers=auth_headers,
        params={
            "left_from": today - timedelta(days=30),
            "left_to": today - timedelta(days=15),
            "right_from": today - timedelta(days=60),
            "right_to": today - timedelta(days=45),
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

    response = client.get(
        f"/api/v1/portfolios/{portfolio.portfolio_id}/metrics/cagr",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

    response = client.post(
        "/api/v1/users/me/presets",
        headers=auth_headers,
        json={
            "preset_type": "VIEW",
            "preset_name": "e2e_view",
            "preset_payload": {"view": "summary"},
            "is_default": True,
        },
    )
    assert response.status_code == 200

    response = client.post(
        "/api/v1/users/me/activity-events",
        headers=auth_headers,
        json={
            "event_type": "VIEW_SUMMARY",
            "status": "COMPLETED",
            "metadata": {"portfolio_id": str(portfolio.portfolio_id)},
        },
    )
    assert response.status_code == 200
