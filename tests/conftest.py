"""Integration tests use a dedicated PostgreSQL database, never the app's .env DB."""
import os

import pytest
from sqlalchemy.engine import make_url

test_url = os.environ.get("TEST_DATABASE_URL", "")
if not test_url:
    raise pytest.UsageError("Set TEST_DATABASE_URL to a dedicated PostgreSQL database ending in _test.")
url = make_url(test_url)
if url.get_backend_name() != "postgresql" or not (url.database or "").endswith("_test"):
    raise pytest.UsageError("TEST_DATABASE_URL must be PostgreSQL and its database name must end in _test.")

os.environ["DATABASE_URL"] = test_url
os.environ["SECRET_KEY"] = "test-only-secret-key-not-for-production-0123456789"
os.environ["APP_TIMEZONE"] = "Europe/Berlin"

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.auth import get_password_hash
from app.core.config import ROOT_DIR
from app.core.database import engine, get_session
from app.core.models import User
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    command.upgrade(Config(str(ROOT_DIR / "alembic.ini")), "head")
    yield
    engine.dispose()


@pytest.fixture
def session():
    # API commits release savepoints; the outer rollback removes all test data.
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()


@pytest.fixture
def client(session):
    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def password_hash():
    return get_password_hash("test-password-123")


@pytest.fixture
def user(session, password_hash):
    user = User(username="alice", hashed_password=password_hash)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def auth(client, user):
    response = client.post("/api/token", data={"username": user.username, "password": "test-password-123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
