
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

from app.memory import postgres_backend as database


USER_A = "test-user-a"
USER_B = "test-user-b"
MEMORY_KEY = "programming.java.preference"


@pytest.fixture
def mock_database(monkeypatch):
    connection = MagicMock()
    cursor = MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor

    @contextmanager
    def fake_connection():
        yield connection

    monkeypatch.setattr(database, "get_connection", fake_connection)

    return connection, cursor


def save_java_memory(**overrides):
    arguments = {
        "user_id": USER_A,
        "memory_key": MEMORY_KEY,
        "content": "I enjoy Java.",
        "category": "programming",
        "source_type": "explicit_statement",
        "source_text": "I enjoy Java.",
    }
    arguments.update(overrides)
    return database.save_user_memory(**arguments)


# ==========================================================
# Saving memories
# ==========================================================

def test_save_explicit_memory(mock_database):
    _, cursor = mock_database

    memory_id = save_java_memory()

    assert isinstance(memory_id, str)
    assert len(memory_id) == 36

    assert cursor.execute.call_count == 3

    calls = cursor.execute.call_args_list

    assert "pg_advisory_xact_lock" in calls[0].args[0]
    assert calls[0].args[1] == (USER_A, MEMORY_KEY)

    assert "UPDATE user_memories" in calls[1].args[0]
    assert calls[1].args[1] == (USER_A, MEMORY_KEY)

    assert "INSERT INTO user_memories" in calls[2].args[0]

    insert_parameters = calls[2].args[1]

    assert insert_parameters == (
        memory_id,
        USER_A,
        MEMORY_KEY,
        "I enjoy Java.",
        "programming",
        "explicit_statement",
        "I enjoy Java.",
    )


def test_save_correction_supersedes_previous_version(mock_database):
    _, cursor = mock_database

    save_java_memory(
        content="I enjoy Java and studied it in OOP.",
        source_type="correction",
        source_text="Correction: I enjoy Java and studied it in OOP.",
    )

    update_sql = cursor.execute.call_args_list[1].args[0]
    insert_sql = cursor.execute.call_args_list[2].args[0]
    insert_parameters = cursor.execute.call_args_list[2].args[1]

    assert "status = 'superseded'" in update_sql
    assert "status = 'active'" in update_sql

    assert "INSERT INTO user_memories" in insert_sql
    assert insert_parameters[4] == "programming"
    assert insert_parameters[5] == "correction"
    assert insert_parameters[6] == (
        "Correction: I enjoy Java and studied it in OOP."
    )


def test_memory_values_are_trimmed_before_saving(mock_database):
    _, cursor = mock_database

    save_java_memory(
        user_id=" test-user-a ",
        memory_key=" programming.java.preference ",
        content=" I enjoy Java. ",
        category=" programming ",
        source_text=" I enjoy Java. ",
    )

    insert_parameters = cursor.execute.call_args_list[2].args[1]

    assert insert_parameters[1] == USER_A
    assert insert_parameters[2] == MEMORY_KEY
    assert insert_parameters[3] == "I enjoy Java."
    assert insert_parameters[4] == "programming"
    assert insert_parameters[6] == "I enjoy Java."


# ==========================================================
# Retrieving active memories
# ==========================================================

def test_get_active_memories(mock_database):
    _, cursor = mock_database

    expected = [
        {
            "id": "memory-1",
            "user_id": USER_A,
            "content": "I enjoy Java.",
            "status": "active",
        }
    ]

    cursor.fetchall.return_value = expected

    result = database.get_user_memories(USER_A)

    assert result == expected

    query, parameters = cursor.execute.call_args.args

    assert "FROM user_memories" in query
    assert "WHERE user_id = %s" in query
    assert "status = 'active'" in query
    assert parameters == [USER_A]


def test_get_memories_by_category_and_limit(mock_database):
    _, cursor = mock_database
    cursor.fetchall.return_value = []

    database.get_user_memories(
        USER_A,
        category=" programming ",
        limit=2,
    )

    query, parameters = cursor.execute.call_args.args

    assert "AND category = %s" in query
    assert "LIMIT %s" in query
    assert parameters == [USER_A, "programming", 2]


def test_get_memories_uses_dict_row(mock_database):
    connection, cursor = mock_database

    database.get_user_memories(USER_A)

    connection.cursor.assert_called_once_with(
        row_factory=database.dict_row
    )
    assert cursor.execute.called
    assert cursor.fetchall.called


# ==========================================================
# Retrieving memory history
# ==========================================================

def test_get_memory_history_includes_superseded_records(mock_database):
    _, cursor = mock_database
    cursor.fetchall.return_value = [
        {"id": "new", "status": "active"},
        {"id": "old", "status": "superseded"},
    ]

    result = database.get_user_memory_history(USER_A)

    assert len(result) == 2
    assert result[0]["status"] == "active"
    assert result[1]["status"] == "superseded"

    query, parameters = cursor.execute.call_args.args

    assert "FROM user_memories" in query
    assert "WHERE user_id = %s" in query
    assert parameters == [USER_A]


def test_get_memory_history_by_key_and_limit(mock_database):
    _, cursor = mock_database
    cursor.fetchall.return_value = []

    database.get_user_memory_history(
        USER_A,
        memory_key=MEMORY_KEY,
        limit=5,
    )

    query, parameters = cursor.execute.call_args.args

    assert "AND memory_key = %s" in query
    assert "LIMIT %s" in query
    assert parameters == [USER_A, MEMORY_KEY, 5]


# ==========================================================
# User ownership and deletion
# ==========================================================

def test_delete_memory_uses_user_ownership_filter(mock_database):
    _, cursor = mock_database
    cursor.rowcount = 1

    result = database.delete_user_memory(USER_A, "memory-1")

    assert result is True

    query, parameters = cursor.execute.call_args.args

    assert "DELETE FROM user_memories" in query
    assert "WHERE id = %s" in query
    assert "AND user_id = %s" in query
    assert parameters == ("memory-1", USER_A)


def test_user_cannot_delete_another_users_memory(mock_database):
    _, cursor = mock_database
    cursor.rowcount = 0

    with pytest.raises(ValueError, match="Memory was not found"):
        database.delete_user_memory(USER_B, "memory-1")

    _, parameters = cursor.execute.call_args.args

    assert parameters == ("memory-1", USER_B)


# ==========================================================
# Input validation
# ==========================================================

@pytest.mark.parametrize(
    "user_id",
    ["", "   ", None, 123],
)
def test_save_rejects_invalid_user_id(user_id):
    with pytest.raises(ValueError):
        save_java_memory(user_id=user_id)


@pytest.mark.parametrize(
    "field,value",
    [
        ("memory_key", ""),
        ("memory_key", "   "),
        ("content", ""),
        ("content", "   "),
        ("category", ""),
        ("category", "   "),
        ("source_text", ""),
        ("source_text", "   "),
    ],
)
def test_save_rejects_empty_fields(field, value):
    with pytest.raises(ValueError):
        save_java_memory(**{field: value})


@pytest.mark.parametrize(
    "source_type",
    ["inference", "conversation_summary", "", None],
)
def test_save_rejects_unsupported_source_type(source_type):
    with pytest.raises(ValueError):
        save_java_memory(source_type=source_type)


@pytest.mark.parametrize(
    "limit",
    [0, -1, 1.5, True, "2"],
)
def test_get_memories_rejects_invalid_limit(limit):
    with pytest.raises(ValueError):
        database.get_user_memories(USER_A, limit=limit)


@pytest.mark.parametrize(
    "limit",
    [0, -1, 1.5, True, "2"],
)
def test_get_history_rejects_invalid_limit(limit):
    with pytest.raises(ValueError):
        database.get_user_memory_history(USER_A, limit=limit)


@pytest.mark.parametrize(
    "category",
    ["", "   ", 123],
)
def test_get_memories_rejects_invalid_category(category):
    with pytest.raises(ValueError):
        database.get_user_memories(USER_A, category=category)


@pytest.mark.parametrize(
    "memory_key",
    ["", "   ", 123],
)
def test_get_history_rejects_invalid_memory_key(memory_key):
    with pytest.raises(ValueError):
        database.get_user_memory_history(
            USER_A,
            memory_key=memory_key,
        )


def test_delete_rejects_empty_memory_id():
    with pytest.raises(ValueError):
        database.delete_user_memory(USER_A, "")


def test_delete_rejects_invalid_user_id():
    with pytest.raises(ValueError):
        database.delete_user_memory("", "memory-1")
