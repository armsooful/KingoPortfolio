"""
인증 관련 단위 테스트
"""
import pytest
from app.auth import (
    hash_password, verify_password, create_access_token,
    create_reset_token, verify_reset_token
)
from jose import jwt
from app.config import settings
from app.exceptions import InvalidTokenError, TokenExpiredError
from datetime import datetime, timedelta


@pytest.mark.unit
class TestPasswordHashing:
    """비밀번호 해싱 테스트"""

    def test_hash_password(self):
        """비밀번호 해싱이 정상 작동하는지 테스트"""
        password = "testpassword123"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt 해시 형식

    def test_verify_password_correct(self):
        """올바른 비밀번호 검증 테스트"""
        password = "testpassword123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """잘못된 비밀번호 검증 테스트"""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_hash_password_too_long(self):
        """72바이트 초과 비밀번호 테스트"""
        from app.exceptions import ValidationError as KingoValidationError

        long_password = "a" * 100  # 100글자

        with pytest.raises(KingoValidationError) as exc_info:
            hash_password(long_password)

        assert "72바이트" in str(exc_info.value.detail)


@pytest.mark.unit
class TestJWTToken:
    """JWT 토큰 생성/검증 테스트"""

    def test_create_access_token(self):
        """JWT 토큰 생성 테스트"""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_access_token(self):
        """JWT 토큰 디코딩 테스트"""
        email = "test@example.com"
        data = {"sub": email}
        token = create_access_token(data)

        decoded = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

        assert decoded["sub"] == email
        assert "exp" in decoded  # 만료 시간 포함 확인

    def test_token_expiration(self):
        """토큰 만료 시간 확인"""
        from datetime import timedelta

        data = {"sub": "test@example.com"}
        token = create_access_token(data, expires_delta=timedelta(minutes=30))
        decoded = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

        assert "exp" in decoded
        # 만료 시간이 현재 시간보다 미래인지 확인
        from datetime import datetime
        exp_timestamp = decoded["exp"]
        assert exp_timestamp > datetime.utcnow().timestamp()


@pytest.mark.unit
@pytest.mark.auth
class TestAuthentication:
    """인증 엔드포인트 테스트"""

    def test_signup_success(self, client):
        """회원가입 성공 테스트"""
        response = client.post(
            "/auth/signup",
            json={
                "email": "newuser@example.com",
                "password": "newpassword123"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "newuser@example.com"

    def test_signup_duplicate_email(self, client, test_user):
        """중복 이메일 회원가입 테스트"""
        response = client.post(
            "/auth/signup",
            json={
                "email": "test@example.com",  # 이미 존재하는 이메일
                "password": "password123"
            }
        )

        assert response.status_code == 409  # Conflict
        data = response.json()
        assert "error" in data
        assert "already" in data["error"]["message"].lower()

    def test_signup_short_password(self, client):
        """짧은 비밀번호 회원가입 테스트"""
        response = client.post(
            "/auth/signup",
            json={
                "email": "short@example.com",
                "password": "1234567"  # 8자 미만
            }
        )

        # Pydantic validation error returns 422 (Unprocessable Entity)
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        # Error code should be VALIDATION_ERROR
        assert data["error"]["code"] == "VALIDATION_ERROR"
        # Extra field should contain validation details
        assert "extra" in data["error"]
        assert "errors" in data["error"]["extra"]

    def test_login_success(self, client, test_user):
        """로그인 성공 테스트"""
        response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "test@example.com"

    def test_login_wrong_password(self, client, test_user):
        """잘못된 비밀번호 로그인 테스트"""
        response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword"
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert "올바르지 않습니다" in data["error"]["message"]

    def test_login_nonexistent_user(self, client):
        """존재하지 않는 사용자 로그인 테스트"""
        response = client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "password123"
            }
        )

        assert response.status_code == 401

    def test_get_current_user(self, client, auth_headers):
        """현재 사용자 정보 조회 테스트"""
        response = client.get("/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "id" in data
        assert "created_at" in data

    def test_get_current_user_without_token(self, client):
        """토큰 없이 사용자 정보 조회 시도"""
        response = client.get("/auth/me")

        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client):
        """유효하지 않은 토큰으로 사용자 정보 조회"""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token_xyz"}
        )

        assert response.status_code == 401


@pytest.mark.unit
class TestPasswordResetTokens:
    """비밀번호 재설정 토큰 테스트"""

    def test_create_reset_token(self):
        """재설정 토큰 생성 테스트"""
        user_id = "test-user-123"
        token = create_reset_token(user_id)

        # 토큰이 생성되었는지 확인
        assert token is not None
        assert len(token) > 0

        # 토큰 디코딩
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

        # 토큰 내용 확인
        assert payload["sub"] == user_id
        assert payload["type"] == "reset"
        assert "exp" in payload

    def test_verify_reset_token_valid(self):
        """유효한 재설정 토큰 검증 테스트"""
        user_id = "test-user-456"
        token = create_reset_token(user_id)

        # 토큰 검증
        verified_user_id = verify_reset_token(token)

        assert verified_user_id == user_id

    def test_verify_reset_token_expired(self):
        """만료된 재설정 토큰 검증 테스트"""
        user_id = "test-user-789"

        # 이미 만료된 토큰 생성 (과거 시간)
        expire = datetime.utcnow() - timedelta(minutes=1)  # 1분 전 만료
        to_encode = {
            "sub": user_id,
            "type": "reset",
            "exp": expire
        }
        expired_token = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

        # 만료된 토큰 검증 시 TokenExpiredError 발생
        with pytest.raises(TokenExpiredError) as exc_info:
            verify_reset_token(expired_token)

        assert "만료" in str(exc_info.value.detail)

    def test_verify_reset_token_invalid_type(self):
        """잘못된 타입의 토큰 검증 테스트"""
        user_id = "test-user-999"

        # access 타입 토큰 생성 (reset이 아님)
        expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode = {
            "sub": user_id,
            "type": "access",  # 잘못된 타입
            "exp": expire
        }
        wrong_type_token = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

        # 잘못된 타입의 토큰 검증 시 InvalidTokenError 발생
        with pytest.raises(InvalidTokenError) as exc_info:
            verify_reset_token(wrong_type_token)

        assert "타입" in str(exc_info.value.detail)

    def test_verify_reset_token_no_user_id(self):
        """사용자 ID가 없는 토큰 검증 테스트"""
        expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode = {
            "type": "reset",
            "exp": expire
            # "sub"가 없음
        }
        no_sub_token = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

        # 사용자 ID가 없는 토큰 검증 시 InvalidTokenError 발생
        with pytest.raises(InvalidTokenError) as exc_info:
            verify_reset_token(no_sub_token)

        assert "사용자 정보" in str(exc_info.value.detail)

    def test_verify_reset_token_invalid_signature(self):
        """잘못된 서명의 토큰 검증 테스트"""
        # 다른 secret key로 생성된 토큰
        wrong_secret = "wrong_secret_key_12345"
        user_id = "test-user-111"
        expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode = {
            "sub": user_id,
            "type": "reset",
            "exp": expire
        }
        wrong_token = jwt.encode(to_encode, wrong_secret, algorithm=settings.algorithm)

        # 잘못된 서명의 토큰 검증 시 InvalidTokenError 발생
        with pytest.raises(InvalidTokenError):
            verify_reset_token(wrong_token)


@pytest.mark.integration
class TestPasswordResetEndpoints:
    """비밀번호 재설정 엔드포인트 통합 테스트"""

    def test_forgot_password_success(self, client, db):
        """비밀번호 재설정 요청 성공 테스트"""
        # 먼저 사용자 회원가입
        signup_response = client.post(
            "/auth/signup",
            json={"email": "reset@example.com", "password": "oldPassword123"}
        )
        assert signup_response.status_code == 201

        # 비밀번호 재설정 요청
        response = client.post(
            "/auth/forgot-password",
            json={"email": "reset@example.com"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "이메일로 전송" in data["message"]

    def test_forgot_password_nonexistent_email(self, client):
        """존재하지 않는 이메일로 재설정 요청 (보안상 성공 응답)"""
        response = client.post(
            "/auth/forgot-password",
            json={"email": "nonexistent@example.com"}
        )

        # 보안상 존재하지 않는 이메일도 성공 응답
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_forgot_password_invalid_email(self, client):
        """유효하지 않은 이메일 형식으로 재설정 요청"""
        response = client.post(
            "/auth/forgot-password",
            json={"email": "not-an-email"}
        )

        # Pydantic validation error
        assert response.status_code == 422

    def test_reset_password_success(self, client, db):
        """비밀번호 재설정 성공 테스트"""
        # 1. 사용자 회원가입
        signup_response = client.post(
            "/auth/signup",
            json={"email": "resettest@example.com", "password": "oldPassword123"}
        )
        assert signup_response.status_code == 201
        user_data = signup_response.json()
        user_id = user_data["user"]["id"]

        # 2. 재설정 토큰 생성
        reset_token = create_reset_token(user_id)

        # 3. 비밀번호 재설정
        response = client.post(
            "/auth/reset-password",
            json={
                "token": reset_token,
                "new_password": "newPassword456!"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "성공적으로 변경" in data["message"]

        # 4. 새 비밀번호로 로그인 확인
        login_response = client.post(
            "/auth/login",
            json={"email": "resettest@example.com", "password": "newPassword456!"}
        )
        assert login_response.status_code == 200

        # 5. 이전 비밀번호로 로그인 실패 확인
        old_login_response = client.post(
            "/auth/login",
            json={"email": "resettest@example.com", "password": "oldPassword123"}
        )
        assert old_login_response.status_code == 401

    def test_reset_password_expired_token(self, client, db):
        """만료된 토큰으로 비밀번호 재설정 시도"""
        # 사용자 회원가입
        signup_response = client.post(
            "/auth/signup",
            json={"email": "expiredtest@example.com", "password": "oldPassword123"}
        )
        user_id = signup_response.json()["user"]["id"]

        # 만료된 토큰 생성
        expire = datetime.utcnow() - timedelta(minutes=1)
        to_encode = {
            "sub": user_id,
            "type": "reset",
            "exp": expire
        }
        expired_token = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

        # 비밀번호 재설정 시도
        response = client.post(
            "/auth/reset-password",
            json={
                "token": expired_token,
                "new_password": "newPassword456!"
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "TOKEN_EXPIRED"

    def test_reset_password_invalid_token(self, client):
        """유효하지 않은 토큰으로 비밀번호 재설정 시도"""
        response = client.post(
            "/auth/reset-password",
            json={
                "token": "invalid_token_xyz",
                "new_password": "newPassword456!"
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "INVALID_TOKEN"

    def test_reset_password_wrong_token_type(self, client, db):
        """잘못된 타입의 토큰으로 비밀번호 재설정 시도"""
        # 사용자 회원가입
        signup_response = client.post(
            "/auth/signup",
            json={"email": "wrongtype@example.com", "password": "oldPassword123"}
        )
        user_id = signup_response.json()["user"]["id"]

        # access 타입 토큰 생성
        expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode = {
            "sub": user_id,
            "type": "access",
            "exp": expire
        }
        wrong_type_token = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

        # 비밀번호 재설정 시도
        response = client.post(
            "/auth/reset-password",
            json={
                "token": wrong_type_token,
                "new_password": "newPassword456!"
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "INVALID_TOKEN"

    def test_reset_password_short_password(self, client, db):
        """짧은 비밀번호로 재설정 시도"""
        # 사용자 회원가입
        signup_response = client.post(
            "/auth/signup",
            json={"email": "shortpw@example.com", "password": "oldPassword123"}
        )
        user_id = signup_response.json()["user"]["id"]

        # 재설정 토큰 생성
        reset_token = create_reset_token(user_id)

        # 짧은 비밀번호로 재설정 시도
        response = client.post(
            "/auth/reset-password",
            json={
                "token": reset_token,
                "new_password": "short"  # 8자 미만
            }
        )

        # Pydantic validation error
        assert response.status_code == 422

    def test_reset_password_nonexistent_user(self, client):
        """존재하지 않는 사용자 ID로 비밀번호 재설정 시도"""
        # 존재하지 않는 사용자 ID로 토큰 생성
        nonexistent_user_id = "nonexistent-user-999"
        reset_token = create_reset_token(nonexistent_user_id)

        # 비밀번호 재설정 시도
        response = client.post(
            "/auth/reset-password",
            json={
                "token": reset_token,
                "new_password": "newPassword456!"
            }
        )

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "USER_NOT_FOUND"


@pytest.mark.integration
class TestProfileEndpoints:
    """프로필 관리 엔드포인트 통합 테스트"""

    def test_get_profile(self, client, db):
        """프로필 조회 테스트"""
        # 사용자 회원가입 및 로그인
        signup_response = client.post(
            "/auth/signup",
            json={"email": "profile@example.com", "password": "password123", "name": "홍길동"}
        )
        token = signup_response.json()["access_token"]

        # 프로필 조회
        response = client.get(
            "/auth/profile",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "profile@example.com"
        assert data["name"] == "홍길동"
        assert data["role"] == "user"
        assert "id" in data
        assert "created_at" in data

    def test_get_profile_without_token(self, client):
        """토큰 없이 프로필 조회 시도"""
        response = client.get("/auth/profile")
        assert response.status_code == 401

    def test_update_profile_name(self, client, db):
        """프로필 이름 수정 테스트"""
        # 사용자 회원가입
        signup_response = client.post(
            "/auth/signup",
            json={"email": "updatename@example.com", "password": "password123", "name": "홍길동"}
        )
        token = signup_response.json()["access_token"]

        # 이름 수정
        response = client.put(
            "/auth/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "김철수"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "김철수"
        assert data["email"] == "updatename@example.com"

    def test_update_profile_email(self, client, db):
        """프로필 이메일 수정 테스트"""
        # 사용자 회원가입
        signup_response = client.post(
            "/auth/signup",
            json={"email": "oldemail@example.com", "password": "password123"}
        )
        token = signup_response.json()["access_token"]

        # 이메일 수정
        response = client.put(
            "/auth/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={"email": "newemail@example.com"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newemail@example.com"

        # 새 이메일로 로그인 확인
        login_response = client.post(
            "/auth/login",
            json={"email": "newemail@example.com", "password": "password123"}
        )
        assert login_response.status_code == 200

    def test_update_profile_duplicate_email(self, client, db):
        """중복 이메일로 프로필 수정 시도"""
        # 첫 번째 사용자
        client.post(
            "/auth/signup",
            json={"email": "user1@example.com", "password": "password123"}
        )

        # 두 번째 사용자
        signup_response = client.post(
            "/auth/signup",
            json={"email": "user2@example.com", "password": "password123"}
        )
        token = signup_response.json()["access_token"]

        # 첫 번째 사용자 이메일로 변경 시도
        response = client.put(
            "/auth/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={"email": "user1@example.com"}
        )

        assert response.status_code == 409
        data = response.json()
        assert data["error"]["code"] == "DUPLICATE_EMAIL"

    def test_update_profile_no_fields(self, client, db):
        """필드 없이 프로필 수정 시도"""
        # 사용자 회원가입
        signup_response = client.post(
            "/auth/signup",
            json={"email": "nofields@example.com", "password": "password123"}
        )
        token = signup_response.json()["access_token"]

        # 필드 없이 수정 시도
        response = client.put(
            "/auth/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={}
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_change_password_success(self, client, db):
        """비밀번호 변경 성공 테스트"""
        # 사용자 회원가입
        signup_response = client.post(
            "/auth/signup",
            json={"email": "changepw@example.com", "password": "oldPassword123"}
        )
        token = signup_response.json()["access_token"]

        # 비밀번호 변경
        response = client.put(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "oldPassword123",
                "new_password": "newPassword456"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "성공적으로 변경" in data["message"]

        # 새 비밀번호로 로그인 확인
        login_response = client.post(
            "/auth/login",
            json={"email": "changepw@example.com", "password": "newPassword456"}
        )
        assert login_response.status_code == 200

        # 이전 비밀번호로 로그인 실패 확인
        old_login_response = client.post(
            "/auth/login",
            json={"email": "changepw@example.com", "password": "oldPassword123"}
        )
        assert old_login_response.status_code == 401

    def test_change_password_wrong_current(self, client, db):
        """잘못된 현재 비밀번호로 변경 시도"""
        # 사용자 회원가입
        signup_response = client.post(
            "/auth/signup",
            json={"email": "wrongpw@example.com", "password": "correctPassword123"}
        )
        token = signup_response.json()["access_token"]

        # 잘못된 현재 비밀번호로 변경 시도
        response = client.put(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "wrongPassword",
                "new_password": "newPassword456"
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "INVALID_CREDENTIALS"

    def test_change_password_same_as_current(self, client, db):
        """현재 비밀번호와 동일한 새 비밀번호로 변경 시도"""
        # 사용자 회원가입
        signup_response = client.post(
            "/auth/signup",
            json={"email": "samepw@example.com", "password": "samePassword123"}
        )
        token = signup_response.json()["access_token"]

        # 동일한 비밀번호로 변경 시도
        response = client.put(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "samePassword123",
                "new_password": "samePassword123"
            }
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "달라야" in data["error"]["message"]

    def test_delete_account(self, client, db):
        """계정 삭제 테스트"""
        # 사용자 회원가입
        signup_response = client.post(
            "/auth/signup",
            json={"email": "deleteuser@example.com", "password": "password123"}
        )
        token = signup_response.json()["access_token"]

        # 계정 삭제
        response = client.delete(
            "/auth/account",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "성공적으로 삭제" in data["message"]

        # 삭제된 계정으로 로그인 시도
        login_response = client.post(
            "/auth/login",
            json={"email": "deleteuser@example.com", "password": "password123"}
        )
        assert login_response.status_code == 401

        # 삭제된 토큰으로 프로필 조회 시도
        profile_response = client.get(
            "/auth/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert profile_response.status_code == 401
