"""
U-3 사용자 설정/이력 통합 테스트
"""


def test_u3_user_settings_flow(client, auth_headers):
    preset_payload = {
        "preset_type": "VIEW",
        "preset_name": "default_view",
        "preset_payload": {"view": "summary"},
        "is_default": True,
    }
    response = client.post("/api/v1/users/me/presets", headers=auth_headers, json=preset_payload)
    assert response.status_code == 200
    preset_id = response.json()["data"]["preset_id"]

    response = client.get("/api/v1/users/me/presets", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-store"
    assert len(response.json()["data"]) == 1

    response = client.patch(
        f"/api/v1/users/me/presets/{preset_id}",
        headers=auth_headers,
        json={"preset_name": "default_view_v2"},
    )
    assert response.status_code == 200

    response = client.get("/api/v1/users/me/notification-settings", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"]["enable_alerts"] is False

    response = client.put(
        "/api/v1/users/me/notification-settings",
        headers=auth_headers,
        json={"enable_alerts": True, "exposure_frequency": "HIGH"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["enable_alerts"] is True

    response = client.post(
        "/api/v1/users/me/activity-events",
        headers=auth_headers,
        json={
            "event_type": "VIEW_SUMMARY",
            "status": "COMPLETED",
            "metadata": {"source": "integration"},
        },
    )
    assert response.status_code == 200

    response = client.get("/api/v1/users/me/activity-events", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-store"
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["event_type"] == "VIEW_SUMMARY"

    response = client.delete(
        f"/api/v1/users/me/presets/{preset_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
