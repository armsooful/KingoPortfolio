"""
전역 에러 핸들러 테스트
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.exceptions import (
    BaseKingoException,
    InvalidTokenError,
    AdminOnlyError,
    StockNotFoundError,
    DuplicateEmailError,
    ValidationError as KingoValidationError,
    InternalServerError
)
from app.error_handlers import setup_exception_handlers


@pytest.fixture
def error_test_app():
    """에러 테스트용 FastAPI 앱"""
    app = FastAPI()
    setup_exception_handlers(app)

    # 테스트용 엔드포인트 정의
    @app.get("/test/base-kingo-exception")
    async def test_base_kingo_exception():
        raise BaseKingoException(
            status_code=400,
            detail="테스트 Kingo 예외",
            error_code="TEST_ERROR",
            extra={"field": "test"}
        )

    @app.get("/test/invalid-token")
    async def test_invalid_token():
        raise InvalidTokenError()

    @app.get("/test/admin-only")
    async def test_admin_only():
        raise AdminOnlyError()

    @app.get("/test/stock-not-found")
    async def test_stock_not_found():
        raise StockNotFoundError(symbol="AAPL")

    @app.get("/test/duplicate-email")
    async def test_duplicate_email():
        raise DuplicateEmailError(email="test@example.com")

    @app.get("/test/validation-error")
    async def test_validation_error():
        raise KingoValidationError(
            detail="검증 실패",
            extra={"errors": [{"field": "email", "message": "invalid"}]}
        )

    @app.get("/test/internal-server-error")
    async def test_internal_server_error():
        raise InternalServerError()

    @app.get("/test/general-exception")
    async def test_general_exception():
        raise Exception("예상하지 못한 일반 에러")

    @app.get("/test/zero-division")
    async def test_zero_division():
        return 1 / 0

    return app


@pytest.fixture
def error_client(error_test_app):
    """에러 테스트용 클라이언트"""
    return TestClient(error_test_app)


@pytest.mark.unit
@pytest.mark.error_handlers
class TestKingoExceptionHandlers:
    """Kingo 커스텀 예외 핸들러 테스트"""

    def test_base_kingo_exception_handler(self, error_client):
        """기본 Kingo 예외 핸들러"""
        response = error_client.get("/test/base-kingo-exception")

        assert response.status_code == 400
        data = response.json()

        assert "error" in data
        assert data["error"]["code"] == "TEST_ERROR"
        assert data["error"]["message"] == "테스트 Kingo 예외"
        assert data["error"]["status"] == 400
        assert data["error"]["extra"]["field"] == "test"

    def test_invalid_token_error(self, error_client):
        """InvalidTokenError 핸들러"""
        response = error_client.get("/test/invalid-token")

        assert response.status_code == 401
        data = response.json()

        assert data["error"]["code"] == "INVALID_TOKEN"
        assert "토큰" in data["error"]["message"]

    def test_admin_only_error(self, error_client):
        """AdminOnlyError 핸들러"""
        response = error_client.get("/test/admin-only")

        assert response.status_code == 403
        data = response.json()

        assert data["error"]["code"] == "ADMIN_ONLY"
        assert "관리자" in data["error"]["message"]

    def test_stock_not_found_error(self, error_client):
        """StockNotFoundError 핸들러"""
        response = error_client.get("/test/stock-not-found")

        assert response.status_code == 404
        data = response.json()

        assert data["error"]["code"] == "STOCK_NOT_FOUND"
        assert "AAPL" in data["error"]["message"]
        assert data["error"]["extra"]["symbol"] == "AAPL"

    def test_duplicate_email_error(self, error_client):
        """DuplicateEmailError 핸들러"""
        response = error_client.get("/test/duplicate-email")

        assert response.status_code == 409
        data = response.json()

        assert data["error"]["code"] == "DUPLICATE_EMAIL"
        assert "test@example.com" in data["error"]["message"]
        assert data["error"]["extra"]["email"] == "test@example.com"

    def test_validation_error_handler(self, error_client):
        """ValidationError 핸들러"""
        response = error_client.get("/test/validation-error")

        assert response.status_code == 422
        data = response.json()

        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "검증" in data["error"]["message"]

    def test_internal_server_error_handler(self, error_client):
        """InternalServerError 핸들러"""
        response = error_client.get("/test/internal-server-error")

        assert response.status_code == 500
        data = response.json()

        assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert "서버" in data["error"]["message"]


@pytest.mark.unit
@pytest.mark.error_handlers
class TestGeneralExceptionHandlers:
    """일반 예외 핸들러 테스트"""

    def test_general_exception_handler(self, error_client):
        """예상하지 못한 일반 예외 핸들러"""
        # TestClient에서는 500 에러가 raise되므로 pytest.raises 사용
        with pytest.raises(Exception, match="예상하지 못한 일반 에러"):
            response = error_client.get("/test/general-exception")

    def test_zero_division_error_handler(self, error_client):
        """ZeroDivisionError 처리"""
        # TestClient에서는 500 에러가 raise되므로 pytest.raises 사용
        with pytest.raises(ZeroDivisionError):
            response = error_client.get("/test/zero-division")


@pytest.mark.unit
@pytest.mark.error_handlers
class TestErrorResponseStructure:
    """에러 응답 구조 테스트"""

    def test_error_response_has_required_fields(self, error_client):
        """에러 응답이 필수 필드를 포함하는지 확인"""
        response = error_client.get("/test/invalid-token")

        data = response.json()

        # 필수 필드 확인
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "status" in data["error"]

        # 타입 확인
        assert isinstance(data["error"]["code"], str)
        assert isinstance(data["error"]["message"], str)
        assert isinstance(data["error"]["status"], int)

    def test_error_response_with_extra_data(self, error_client):
        """에러 응답에 추가 데이터 포함 확인"""
        response = error_client.get("/test/stock-not-found")

        data = response.json()

        # extra 필드 확인
        assert "extra" in data["error"]
        assert isinstance(data["error"]["extra"], dict)
        assert "symbol" in data["error"]["extra"]


@pytest.mark.integration
@pytest.mark.error_handlers
class TestErrorHandlerIntegration:
    """에러 핸들러 통합 테스트"""

    def test_auth_error_handling(self, client):
        """인증 에러 핸들링"""
        # 잘못된 토큰으로 인증 필요한 엔드포인트 접근
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == 401
        data = response.json()

        assert "error" in data
        assert data["error"]["code"] in ["INVALID_TOKEN", "TOKEN_EXPIRED"]

    def test_admin_permission_error_handling(self, client, auth_headers):
        """관리자 권한 에러 핸들링"""
        # 일반 사용자로 admin 엔드포인트 접근
        response = client.get("/admin/data-status", headers=auth_headers)

        assert response.status_code == 403
        data = response.json()

        assert "error" in data
        assert data["error"]["code"] == "ADMIN_ONLY"
        assert "관리자" in data["error"]["message"]

    def test_validation_error_handling(self, client):
        """Pydantic 검증 에러 핸들링"""
        # 잘못된 데이터로 회원가입 시도
        response = client.post(
            "/auth/signup",
            json={"email": "invalid-email", "password": ""}  # 잘못된 이메일, 빈 비밀번호
        )

        assert response.status_code == 422
        data = response.json()

        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.unit
@pytest.mark.error_handlers
class TestCustomExceptionProperties:
    """커스텀 예외 속성 테스트"""

    def test_exception_has_error_code(self):
        """예외가 error_code를 가지는지 확인"""
        exc = InvalidTokenError()

        assert hasattr(exc, 'error_code')
        assert exc.error_code == "INVALID_TOKEN"

    def test_exception_has_extra_data(self):
        """예외가 extra 데이터를 가지는지 확인"""
        exc = StockNotFoundError(symbol="TSLA")

        assert hasattr(exc, 'extra')
        assert isinstance(exc.extra, dict)
        assert exc.extra["symbol"] == "TSLA"

    def test_exception_inherits_from_http_exception(self):
        """커스텀 예외가 HTTPException을 상속하는지 확인"""
        from fastapi import HTTPException

        exc = BaseKingoException(
            status_code=400,
            detail="Test"
        )

        assert isinstance(exc, HTTPException)
