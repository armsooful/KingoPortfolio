"""
U-3 사용자 설정/이력 API 단위 테스트
"""

from datetime import datetime, timedelta

from app.models.user_preferences import UserActivityEvent


def test_presets_crud_and_default_switch(client, auth_headers, db, test_user):
    payload = {
        "preset_type": "FILTER",
        "preset_name": "low_risk",
        "preset_payload": {"risk_level": "low"},
        "is_default": True,
    }
    response = client.post("/api/v1/users/me/presets", headers=auth_headers, json=payload)
    assert response.status_code == 200
    first_id = response.json()["data"]["preset_id"]

    payload_two = {
        "preset_type": "FILTER",
        "preset_name": "balanced",
        "preset_payload": {"risk_level": "medium"},
        "is_default": True,
    }
    response = client.post("/api/v1/users/me/presets", headers=auth_headers, json=payload_two)
    assert response.status_code == 200
    second_id = response.json()["data"]["preset_id"]

    response = client.get("/api/v1/users/me/presets", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-store"
    data = response.json()["data"]
    assert len(data) == 2
    defaults = [item for item in data if item["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["preset_id"] == second_id

    response = client.patch(
        f"/api/v1/users/me/presets/{first_id}",
        headers=auth_headers,
        json={"preset_name": "low_risk_v2", "is_default": True},
    )
    assert response.status_code == 200

    response = client.get("/api/v1/users/me/presets", headers=auth_headers)
    data = response.json()["data"]
    defaults = [item for item in data if item["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["preset_id"] == first_id

    response = client.delete(
        f"/api/v1/users/me/presets/{second_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200


def test_presets_validation_and_conflict(client, auth_headers, db, test_user):
    response = client.post("/api/v1/users/me/presets", headers=auth_headers, json={})
    assert response.status_code == 400

    response = client.post(
        "/api/v1/users/me/presets",
        headers=auth_headers,
        json={"preset_type": "unknown", "preset_name": "x", "preset_payload": {}},
    )
    assert response.status_code == 400

    response = client.post(
        "/api/v1/users/me/presets",
        headers=auth_headers,
        json={"preset_type": "FILTER", "preset_name": "x", "preset_payload": "bad"},
    )
    assert response.status_code == 400

    response = client.post(
        "/api/v1/users/me/presets",
        headers=auth_headers,
        json={"preset_type": "FILTER", "preset_name": "dup", "preset_payload": {}},
    )
    assert response.status_code == 200

    response = client.post(
        "/api/v1/users/me/presets",
        headers=auth_headers,
        json={"preset_type": "FILTER", "preset_name": "dup", "preset_payload": {}},
    )
    assert response.status_code == 409


def test_notification_settings_default_and_update(client, auth_headers):
    response = client.get("/api/v1/users/me/notification-settings", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"]["enable_alerts"] is False
    assert response.json()["data"]["exposure_frequency"] == "STANDARD"

    response = client.put(
        "/api/v1/users/me/notification-settings",
        headers=auth_headers,
        json={"enable_alerts": True, "exposure_frequency": "low"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["enable_alerts"] is True
    assert response.json()["data"]["exposure_frequency"] == "LOW"

    response = client.put(
        "/api/v1/users/me/notification-settings",
        headers=auth_headers,
        json={"enable_alerts": True, "exposure_frequency": "invalid"},
    )
    assert response.status_code == 400


def test_activity_events_list(client, auth_headers, db, test_user):
    event_one = UserActivityEvent(
        user_id=test_user.id,
        event_type="VIEW_SUMMARY",
        status="COMPLETED",
        reason_code=None,
        metadata_json={"portfolio_id": "p1"},
        occurred_at=datetime.utcnow() - timedelta(minutes=10),
    )
    event_two = UserActivityEvent(
        user_id=test_user.id,
        event_type="VIEW_DETAIL",
        status="BLOCKED",
        reason_code="GUARD_BLOCK",
        metadata_json={"portfolio_id": "p2"},
        occurred_at=datetime.utcnow(),
    )
    db.add_all([event_one, event_two])
    db.commit()

    response = client.get("/api/v1/users/me/activity-events", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-store"
    data = response.json()["data"]
    assert len(data) == 2
    assert data[0]["event_type"] == "VIEW_DETAIL"
    assert data[1]["event_type"] == "VIEW_SUMMARY"


def test_activity_events_create_validation(client, auth_headers):
    response = client.post(
        "/api/v1/users/me/activity-events",
        headers=auth_headers,
        json={},
    )
    assert response.status_code == 400

    response = client.post(
        "/api/v1/users/me/activity-events",
        headers=auth_headers,
        json={"event_type": "VIEW", "status": "invalid"},
    )
    assert response.status_code == 400

    response = client.post(
        "/api/v1/users/me/activity-events",
        headers=auth_headers,
        json={"event_type": "VIEW", "status": "COMPLETED", "metadata": "bad"},
    )
    assert response.status_code == 400

    response = client.post(
        "/api/v1/users/me/activity-events",
        headers=auth_headers,
        json={"event_type": "VIEW", "status": "completed", "metadata": {"source": "test"}},
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "COMPLETED"
