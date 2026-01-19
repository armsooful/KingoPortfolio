"""
Phase 3-D 이벤트 수집 API 단위 테스트
"""


def test_event_log_create_success(client, auth_headers):
    response = client.post(
        "/api/v1/events",
        headers=auth_headers,
        json={
            "event_type": "VIEW",
            "path": "/u3/settings",
            "status": "COMPLETED",
            "metadata": {"source": "unit"},
        },
    )
    assert response.status_code == 201
    body = response.json()["data"]
    assert body["event_type"] == "VIEW"
    assert body["status"] == "COMPLETED"


def test_event_log_create_validation(client, auth_headers):
    response = client.post("/api/v1/events", headers=auth_headers, json={})
    assert response.status_code == 400

    response = client.post(
        "/api/v1/events",
        headers=auth_headers,
        json={"event_type": "VIEW", "path": "/u3", "status": "invalid"},
    )
    assert response.status_code == 400

    response = client.post(
        "/api/v1/events",
        headers=auth_headers,
        json={"event_type": "VIEW", "path": "/u3", "status": "COMPLETED", "metadata": "bad"},
    )
    assert response.status_code == 400

    response = client.post(
        "/api/v1/events",
        headers=auth_headers,
        json={
            "event_type": "VIEW",
            "path": "/u3",
            "status": "COMPLETED",
            "metadata": {"score": 1},
        },
    )
    assert response.status_code == 400
