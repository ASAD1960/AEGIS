import pytest

from app.memory import database


@pytest.fixture(autouse=True)
def isolate_database(tmp_path, monkeypatch):
    """
    Give every test its own temporary SQLite database.

    This prevents automated tests from changing the real
    AEGIS database or depending on records from other tests.
    """

    test_database_path = tmp_path / "aegis_test.db"

    monkeypatch.setattr(
        database,
        "DATABASE_PATH",
        test_database_path,
    )

    database.initialize_database()