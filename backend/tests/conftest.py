"""
Pytest 설정 및 공통 Fixtures
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB

from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.auth import hash_password
from app.rate_limiter import limiter


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kwargs):
    """SQLite에서 JSONB를 JSON으로 처리"""
    return "JSON"


# 테스트용 인메모리 데이터베이스
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """테스트용 데이터베이스 세션"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """테스트용 FastAPI 클라이언트"""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # 테스트 환경에서 rate limiter 비활성화
    limiter.enabled = False

    with TestClient(app) as test_client:
        yield test_client

    # 정리
    limiter.enabled = True
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    """테스트용 일반 사용자"""
    user = User(
        email="test@example.com",
        hashed_password=hash_password("testpassword123"),
        is_admin=False,
        role='user'
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_admin(db):
    """테스트용 관리자 사용자"""
    admin = User(
        email="admin@example.com",
        hashed_password=hash_password("adminpassword123"),
        is_admin=True,
        role='admin'
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture
def test_premium_user(db):
    """테스트용 프리미엄 사용자"""
    premium = User(
        email="premium@example.com",
        hashed_password=hash_password("premiumpassword123"),
        is_admin=False,
        role='premium'
    )
    db.add(premium)
    db.commit()
    db.refresh(premium)
    return premium


@pytest.fixture
def user_token(client, test_user):
    """일반 사용자 인증 토큰"""
    response = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def admin_token(client, test_admin):
    """관리자 인증 토큰"""
    response = client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "adminpassword123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def premium_token(client, test_premium_user):
    """프리미엄 사용자 인증 토큰"""
    response = client.post(
        "/auth/login",
        json={"email": "premium@example.com", "password": "premiumpassword123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(user_token):
    """일반 사용자 인증 헤더"""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def admin_headers(admin_token):
    """관리자 인증 헤더"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def premium_headers(premium_token):
    """프리미엄 사용자 인증 헤더"""
    return {"Authorization": f"Bearer {premium_token}"}
