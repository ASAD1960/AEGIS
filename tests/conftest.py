
import pytest

from app.api.main import app, get_current_user_id
from app.memory import database


TEST_USER_ID = "aegis-test-user-1"


@pytest.fixture(autouse=True)
def isolate_database(tmp_path, monkeypatch):
    """
    Give every test its own temporary SQLite database.
    """
    test_database_path = tmp_path / "aegis_test.db"

    monkeypatch.setattr(
        database,
        "DATABASE_PATH",
        test_database_path,
    )

    database.initialize_database()


@pytest.fixture(autouse=True)
def authenticate_api_requests(monkeypatch):
    """
    Simulate a verified user for automated API tests only.
    """
    monkeypatch.setitem(
        app.dependency_overrides,
        get_current_user_id,
        lambda: TEST_USER_ID,
    )
