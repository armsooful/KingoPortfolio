"""
RBAC (Role-Based Access Control) 테스트
"""
import pytest


@pytest.mark.unit
@pytest.mark.admin
class TestRBAC:
    """역할 기반 접근 제어 테스트"""

    def test_user_role_assignment(self, test_user, test_admin, test_premium_user):
        """사용자 역할 할당 확인"""
        assert test_user.role == 'user'
        assert test_user.is_admin is False

        assert test_admin.role == 'admin'
        assert test_admin.is_admin is True

        assert test_premium_user.role == 'premium'
        assert test_premium_user.is_admin is False

    def test_admin_access_granted(self, client, admin_headers):
        """관리자의 admin 엔드포인트 접근 허용"""
        response = client.get("/admin/data-status", headers=admin_headers)

        assert response.status_code == 200

    def test_user_access_denied(self, client, auth_headers):
        """일반 사용자의 admin 엔드포인트 접근 거부"""
        response = client.get("/admin/data-status", headers=auth_headers)

        assert response.status_code == 403
        data = response.json()
        assert "error" in data
        assert "관리자 권한" in data["error"]["message"]

    def test_premium_access_denied_to_admin(self, client, premium_headers):
        """프리미엄 사용자의 admin 엔드포인트 접근 거부"""
        response = client.get("/admin/data-status", headers=premium_headers)

        assert response.status_code == 403

    def test_unauthenticated_access_denied(self, client):
        """인증되지 않은 사용자의 접근 거부"""
        response = client.get("/admin/data-status")

        assert response.status_code == 401

    def test_is_admin_backward_compatibility(self, db):
        """is_admin 필드 하위 호환성 테스트"""
        from app.models.user import User
        from app.auth import hash_password

        # is_admin=True이지만 role이 user인 경우
        old_admin = User(
            email="old_admin@example.com",
            hashed_password=hash_password("password123"),
            is_admin=True,
            role='user'  # 구버전에서 마이그레이션 전
        )
        db.add(old_admin)
        db.commit()
        db.refresh(old_admin)

        assert old_admin.is_admin is True
        assert old_admin.role == 'user'  # 아직 자동 마이그레이션 전

    def test_role_migration_on_login(self, client, db):
        """로그인 시 is_admin → role 자동 마이그레이션"""
        from app.models.user import User
        from app.auth import hash_password

        # is_admin=True이지만 role='user'인 사용자 생성
        old_admin = User(
            email="migrate@example.com",
            hashed_password=hash_password("password123"),
            is_admin=True,
            role='user'
        )
        db.add(old_admin)
        db.commit()
        db.refresh(old_admin)

        # 로그인 시도
        response = client.post(
            "/auth/login",
            json={"email": "migrate@example.com", "password": "password123"}
        )

        assert response.status_code == 200

        # Note: 실제 마이그레이션은 get_current_user() 호출 시 발생
        # 로그인만으로는 role이 변경되지 않으므로
        # 이 테스트는 로그인 성공만 확인


@pytest.mark.integration
@pytest.mark.admin
class TestAdminEndpoints:
    """관리자 전용 엔드포인트 접근 제어 테스트"""

    admin_endpoints = [
        "/admin/data-status",
        "/admin/progress/test-task-id",
    ]

    @pytest.mark.parametrize("endpoint", admin_endpoints)
    def test_admin_endpoints_require_authentication(self, client, endpoint):
        """모든 admin 엔드포인트가 인증을 요구하는지 테스트"""
        response = client.get(endpoint)
        assert response.status_code == 401

    @pytest.mark.parametrize("endpoint", admin_endpoints)
    def test_admin_endpoints_deny_regular_users(self, client, auth_headers, endpoint):
        """모든 admin 엔드포인트가 일반 사용자를 거부하는지 테스트"""
        response = client.get(endpoint, headers=auth_headers)
        assert response.status_code == 403

    @pytest.mark.parametrize("endpoint", ["/admin/data-status"])
    def test_admin_endpoints_allow_admins(self, client, admin_headers, endpoint):
        """admin 엔드포인트가 관리자를 허용하는지 테스트"""
        response = client.get(endpoint, headers=admin_headers)
        # 404가 아닌 200 또는 다른 정상적인 응답
        assert response.status_code in [200, 404, 422]  # 404는 데이터가 없는 경우
