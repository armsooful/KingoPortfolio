"""
Smoke 테스트: 기본 헬스 체크
"""


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
