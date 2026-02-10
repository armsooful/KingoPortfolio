"""
Pytest 설정 및 공통 Fixtures

테스트 환경: PostgreSQL (로컬 환경과 동일 DBMS)
- TEST_DATABASE_URL 환경변수로 테스트 DB 지정 가능
- 기본값: postgresql://changrim@localhost:5432/kingo_test
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.auth import hash_password
from app.rate_limiter import limiter


# ============================================================================
# PostgreSQL 테스트 데이터베이스 설정
# ============================================================================

TEST_DATABASE_URL = os.getenv(
    'TEST_DATABASE_URL',
    'postgresql://changrim@localhost:5432/kingo_test'
)

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# data_source 시딩 데이터 (테스트 간 TRUNCATE 후 재삽입)
_REFERENCE_SOURCES = [
    ('PYKRX', 'pykrx 한국주식 시세 API', 'API'),
    ('KRX_TS', 'KRX TimeSeries 마이그레이션', 'MIGRATION'),
    ('YAHOO', 'Yahoo Finance', 'API'),
    ('FSC', '금융위원회 API', 'API'),
    ('DART', 'DART 전자공시', 'API'),
    ('ALPHA_VANTAGE', 'Alpha Vantage', 'API'),
]


@pytest.fixture(scope="session", autouse=True)
def ensure_test_database():
    """테스트 데이터베이스 자동 생성 (존재하지 않는 경우)"""
    base_url = TEST_DATABASE_URL.rsplit('/', 1)[0]
    db_name = TEST_DATABASE_URL.rsplit('/', 1)[1].split('?')[0]

    admin_engine = create_engine(f"{base_url}/postgres", isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": db_name}
            )
            if not result.fetchone():
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    finally:
        admin_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def setup_tables(ensure_test_database):
    """세션 단위 테이블 생성 및 참조 데이터 시딩"""
    # 스키마 변경 대응: 기존 테이블 삭제 후 재생성
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # FK 참조에 필요한 data_source 레코드 시딩
    _seed_reference_data()

    yield
    Base.metadata.drop_all(bind=engine)


def _seed_reference_data():
    """data_source 참조 데이터 삽입"""
    session = TestingSessionLocal()
    try:
        from app.models.real_data import DataSource
        for sid, name, stype in _REFERENCE_SOURCES:
            session.add(DataSource(
                source_id=sid,
                source_name=name,
                source_type=stype,
                is_active=True,
            ))
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


@pytest.fixture(scope="session", autouse=True)
def patch_session_local(setup_tables):
    """SessionLocal을 테스트 DB로 패치 (병렬 워커 등 직접 SessionLocal 사용하는 코드 대응)"""
    import app.services.pykrx_loader as pykrx_module
    import app.database as db_module

    original_pykrx = pykrx_module.SessionLocal
    original_db = db_module.SessionLocal

    pykrx_module.SessionLocal = TestingSessionLocal
    db_module.SessionLocal = TestingSessionLocal

    yield

    pykrx_module.SessionLocal = original_pykrx
    db_module.SessionLocal = original_db


@pytest.fixture(scope="function")
def db(setup_tables):
    """테스트용 데이터베이스 세션 (함수별 데이터 격리)"""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

        # 모든 테이블 데이터 정리 후 참조 데이터 재삽입
        with engine.connect() as conn:
            tables = [t.name for t in Base.metadata.sorted_tables]
            if tables:
                tables_str = ', '.join(f'"{t}"' for t in tables)
                conn.execute(text(
                    f"TRUNCATE {tables_str} RESTART IDENTITY CASCADE"
                ))
                conn.commit()
        _seed_reference_data()


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
