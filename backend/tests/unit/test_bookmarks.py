"""
U-2 북마크 API 단위 테스트
"""

from sqlalchemy import func

from app.models.custom_portfolio import CustomPortfolio
from app.models.user import User


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


def _create_user(db, email: str) -> User:
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


def test_bookmark_add_list_delete(client, auth_headers, db, test_user):
    portfolio = _create_portfolio(db, owner_user_id=test_user.id)

    response = client.post(
        "/api/v1/bookmarks",
        headers=auth_headers,
        json={"portfolio_id": portfolio.portfolio_id},
    )
    assert response.status_code == 200
    assert response.json()["data"]["portfolio_id"] == portfolio.portfolio_id

    portfolio_two = _create_portfolio(db, owner_user_id=test_user.id, name="Second Portfolio")
    response = client.post(
        "/api/v1/bookmarks",
        headers=auth_headers,
        json={"portfolio_id": portfolio_two.portfolio_id},
    )
    assert response.status_code == 200

    response = client.get("/api/v1/bookmarks", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-store"
    data = response.json()["data"]
    assert len(data) == 2
    assert data[0]["portfolio_id"] == portfolio_two.portfolio_id

    response = client.delete(
        f"/api/v1/bookmarks/{portfolio.portfolio_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200

    response = client.get("/api/v1/bookmarks", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["portfolio_id"] == portfolio_two.portfolio_id


def test_bookmark_duplicate_returns_conflict(client, auth_headers, db, test_user):
    portfolio = _create_portfolio(db, owner_user_id=test_user.id)

    response = client.post(
        "/api/v1/bookmarks",
        headers=auth_headers,
        json={"portfolio_id": portfolio.portfolio_id},
    )
    assert response.status_code == 200

    response = client.post(
        "/api/v1/bookmarks",
        headers=auth_headers,
        json={"portfolio_id": portfolio.portfolio_id},
    )
    assert response.status_code == 409


def test_bookmark_other_user_forbidden(client, auth_headers, db):
    other_user = _create_user(db, "other@example.com")
    portfolio = _create_portfolio(db, owner_user_id=other_user.id)

    response = client.post(
        "/api/v1/bookmarks",
        headers=auth_headers,
        json={"portfolio_id": portfolio.portfolio_id},
    )
    assert response.status_code == 403


def test_bookmark_missing_portfolio_id(client, auth_headers):
    response = client.post(
        "/api/v1/bookmarks",
        headers=auth_headers,
        json={},
    )
    assert response.status_code == 400


def test_bookmark_not_found(client, auth_headers):
    response = client.post(
        "/api/v1/bookmarks",
        headers=auth_headers,
        json={"portfolio_id": 999999},
    )
    assert response.status_code == 404
