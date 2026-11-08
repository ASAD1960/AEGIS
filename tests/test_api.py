
from fastapi.testclient import TestClient

from app.api.main import app, get_current_user_id


client = TestClient(app)

TEST_USER_ID = "aegis-test-user-1"
OTHER_USER_ID = "aegis-test-user-2"


def test_health_check():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "application": "AEGIS",
        "version": "0.1.0",
    }


def test_agent_status():
    response = client.get("/api/status")

    assert response.status_code == 200

    data = response.json()

    assert data["agent"] == "AEGIS"
    assert data["status"] == "Initialized"
    assert data["version"] == "0.1.0"


def test_registered_tools():
    response = client.get("/api/tools")

    assert response.status_code == 200

    data = response.json()

    tool_names = {
        tool["name"]
        for tool in data["tools"]
    }

    assert tool_names == {
        "text_analysis",
        "calculator",
        "data_analysis",
    }


# ==========================================================
# Authentication tests.
# ==========================================================

def test_protected_endpoint_rejects_missing_authentication():
    original_override = app.dependency_overrides.pop(
        get_current_user_id,
        None,
    )

    try:
        response = client.get("/api/conversations")
    finally:
        if original_override is not None:
            app.dependency_overrides[get_current_user_id] = (
                original_override
            )

    assert response.status_code == 401


# ==========================================================
# Agent task API tests.
# ==========================================================

def test_calculator_task():
    response = client.post(
        "/api/tasks",
        json={"task": "Add 25 and 15"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["execution"]["tool_name"] == "calculator"
    assert data["execution"]["result"]["result"] == 40


def test_text_analysis_task():
    response = client.post(
        "/api/tasks",
        json={
            "task": "Analyze text: AEGIS is an intelligent agent."
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["execution"]["tool_name"] == "text_analysis"

    result = data["execution"]["result"]

    assert result["word_count"] == 5
    assert result["sentence_count"] == 1


def test_csv_analysis_task():
    response = client.post(
        "/api/tasks",
        json={"task": "Analyze CSV data"},
    )

    assert response.status_code == 400


# ==========================================================
# CSV upload API tests.
# ==========================================================

def test_csv_upload_success(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.api.main.UPLOAD_DIRECTORY",
        tmp_path,
    )

    csv_content = (
        b"Name,Age,Salary\n"
        b"Ali,24,50000\n"
        b"Sara,27,65000\n"
    )

    response = client.post(
        "/api/data/upload",
        files={
            "file": (
                "employees.csv",
                csv_content,
                "text/csv",
            )
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["original_filename"] == "employees.csv"
    assert data["execution"]["tool_name"] == "data_analysis"

    result = data["execution"]["result"]

    assert result["row_count"] == 2
    assert result["column_count"] == 3
    assert (
        result["column_summaries"]["Salary"]["statistics"]["mean"]
        == 57500
    )

    stored_file = tmp_path / data["stored_filename"]

    assert stored_file.exists()


def test_csv_upload_rejects_non_csv_file():
    response = client.post(
        "/api/data/upload",
        files={
            "file": (
                "employees.txt",
                b"This is not a CSV file.",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only CSV files are accepted."


def test_csv_upload_rejects_oversized_file():
    oversized_content = b"A" * (5 * 1024 * 1024 + 1)

    response = client.post(
        "/api/data/upload",
        files={
            "file": (
                "large.csv",
                oversized_content,
                "text/csv",
            )
        },
    )

    assert response.status_code == 413
    assert response.json()["detail"] == (
        "File exceeds the 5 MB upload limit."
    )


def test_csv_upload_rejects_invalid_encoding():
    invalid_content = bytes([255, 254, 250, 251])

    response = client.post(
        "/api/data/upload",
        files={
            "file": (
                "invalid.csv",
                invalid_content,
                "text/csv",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "CSV file must use UTF-8 encoding."
    )


# ==========================================================
# Persistent conversation API tests.
# ==========================================================

def test_task_creates_persistent_conversation():
    response = client.post(
        "/api/tasks",
        json={"task": "Add 25 and 15"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert isinstance(data["conversation_id"], str)
    assert len(data["conversation_id"]) == 36

    conversation_id = data["conversation_id"]

    history_response = client.get(
        f"/api/conversations/{conversation_id}/messages"
    )

    assert history_response.status_code == 200

    messages = history_response.json()["messages"]

    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Add 25 and 15"
    assert messages[1]["role"] == "assistant"


def test_task_continues_existing_conversation():
    first_response = client.post(
        "/api/tasks",
        json={"task": "Add 10 and 20"},
    )

    assert first_response.status_code == 200

    conversation_id = first_response.json()["conversation_id"]

    second_response = client.post(
        "/api/tasks",
        json={
            "task": "Add 30 and 40",
            "conversation_id": conversation_id,
        },
    )

    assert second_response.status_code == 200

    assert (
        second_response.json()["conversation_id"]
        == conversation_id
    )

    history_response = client.get(
        f"/api/conversations/{conversation_id}/messages"
    )

    messages = history_response.json()["messages"]

    assert len(messages) == 4
    assert messages[0]["content"] == "Add 10 and 20"
    assert messages[2]["content"] == "Add 30 and 40"


def test_conversation_list_endpoint():
    task_response = client.post(
        "/api/tasks",
        json={"task": "Add 5 and 5"},
    )

    assert task_response.status_code == 200

    conversation_id = task_response.json()["conversation_id"]

    response = client.get("/api/conversations")

    assert response.status_code == 200

    conversations = response.json()["conversations"]

    matching_conversations = [
        conversation
        for conversation in conversations
        if conversation["id"] == conversation_id
    ]

    assert len(matching_conversations) == 1

    conversation = matching_conversations[0]

    assert conversation["message_count"] == 2
    assert conversation["title"] == "Add 5 and 5"


def test_conversation_delete_endpoint():
    task_response = client.post(
        "/api/tasks",
        json={"task": "Add 8 and 12"},
    )

    assert task_response.status_code == 200

    conversation_id = task_response.json()["conversation_id"]

    response = client.delete(
        f"/api/conversations/{conversation_id}"
    )

    assert response.status_code == 200
    assert response.json()["success"] is True

    history_response = client.get(
        f"/api/conversations/{conversation_id}/messages"
    )

    assert history_response.status_code == 404


def test_missing_conversation_returns_404():
    response = client.get(
        "/api/conversations/non-existent-conversation/messages"
    )

    assert response.status_code == 404


# ==========================================================
# Conversation ownership tests.
# ==========================================================

def test_user_cannot_read_another_users_conversation():
    task_response = client.post(
        "/api/tasks",
        json={"task": "Add 10 and 15"},
    )

    assert task_response.status_code == 200

    conversation_id = task_response.json()["conversation_id"]

    original_override = app.dependency_overrides[
        get_current_user_id
    ]

    app.dependency_overrides[get_current_user_id] = (
        lambda: OTHER_USER_ID
    )

    try:
        response = client.get(
            f"/api/conversations/{conversation_id}/messages"
        )
    finally:
        app.dependency_overrides[get_current_user_id] = (
            original_override
        )

    assert response.status_code == 404


def test_user_cannot_delete_another_users_conversation():
    task_response = client.post(
        "/api/tasks",
        json={"task": "Add 10 and 15"},
    )

    assert task_response.status_code == 200

    conversation_id = task_response.json()["conversation_id"]

    original_override = app.dependency_overrides[
        get_current_user_id
    ]

    app.dependency_overrides[get_current_user_id] = (
        lambda: OTHER_USER_ID
    )

    try:
        response = client.delete(
            f"/api/conversations/{conversation_id}"
        )
    finally:
        app.dependency_overrides[get_current_user_id] = (
            original_override
        )

    assert response.status_code == 404

    # The original owner must still be able to read the conversation.
    history_response = client.get(
        f"/api/conversations/{conversation_id}/messages"
    )

    assert history_response.status_code == 200
# ==========================================================
# Persistent personal memory API tests.
# ==========================================================

def test_task_retrieves_and_passes_personal_memories(monkeypatch):
    expected_memories = [
        {
            "memory_key": "programming.java",
            "content": "The user enjoys Java.",
            "category": "interests",
            "source_type": "explicit_statement",
        },
        {
            "memory_key": "education.java",
            "content": "The user studied Java in Object-Oriented Programming.",
            "category": "education",
            "source_type": "explicit_statement",
        },
    ]

    retrieved_users = []
    agent_calls = []

    def fake_get_user_memories(user_id, limit=None):
        retrieved_users.append((user_id, limit))
        return expected_memories

    def fake_process_request(
        *,
        task,
        conversation_history=None,
        personal_memories=None,
    ):
        agent_calls.append({
            "task": task,
            "conversation_history": conversation_history,
            "personal_memories": personal_memories,
        })

        return {
            "result": "Personal memory integration test.",
            "tool_name": None,
        }

    monkeypatch.setattr(
        "app.api.main.get_user_memories",
        fake_get_user_memories,
    )

    monkeypatch.setattr(
        "app.api.main.agent.process_request",
        fake_process_request,
    )

    response = client.post(
        "/api/tasks",
        json={"task": "What do you remember about Java?"},
    )

    assert response.status_code == 200

    assert retrieved_users == [
        (TEST_USER_ID, 30)
    ]

    assert len(agent_calls) == 1

    assert agent_calls[0]["personal_memories"] == expected_memories

# ==========================================================
# Automatic personal memory persistence API tests.
# ==========================================================

def test_explicit_personal_statement_is_saved(monkeypatch):

    from app.memory import database

    monkeypatch.setattr(
        "app.api.main.agent.process_request",
        lambda **kwargs: {
            "result": "Memory test completed.",
            "tool_name": None,
        },
    )

    response = client.post(
        "/api/tasks",
        json={"task": "I enjoy Java."},
    )

    assert response.status_code == 200

    memories = database.get_user_memories(TEST_USER_ID)

    assert len(memories) == 1
    assert memories[0]["memory_key"] == (
        "programming.java.preference"
    )
    assert memories[0]["content"] == "The user enjoys Java."
    assert memories[0]["source_type"] == "explicit_statement"


def test_correction_supersedes_previous_memory(monkeypatch):

    from app.memory import database

    monkeypatch.setattr(
        "app.api.main.agent.process_request",
        lambda **kwargs: {
            "result": "Memory test completed.",
            "tool_name": None,
        },
    )

    first = client.post(
        "/api/tasks",
        json={"task": "I enjoy Java."},
    )

    second = client.post(
        "/api/tasks",
        json={"task": "Correction: I do not enjoy Java."},
    )

    assert first.status_code == 200
    assert second.status_code == 200

    active = database.get_user_memories(TEST_USER_ID)

    assert len(active) == 1
    assert active[0]["content"] == "The user does not enjoy Java."
    assert active[0]["source_type"] == "correction"

    history = database.get_user_memory_history(
        TEST_USER_ID,
        memory_key="programming.java.preference",
    )

    assert len(history) == 2
    assert sum(m["status"] == "active" for m in history) == 1
    assert sum(m["status"] == "superseded" for m in history) == 1


def test_ambiguous_statement_is_not_saved(monkeypatch):

    from app.memory import database

    monkeypatch.setattr(
        "app.api.main.agent.process_request",
        lambda **kwargs: {
            "result": "Memory test completed.",
            "tool_name": None,
        },
    )

    response = client.post(
        "/api/tasks",
        json={"task": "I might learn Python."},
    )

    assert response.status_code == 200
    assert database.get_user_memories(TEST_USER_ID) == []


def test_repeated_statement_does_not_create_duplicate_history(
    monkeypatch,
):

    from app.memory import database

    monkeypatch.setattr(
        "app.api.main.agent.process_request",
        lambda **kwargs: {
            "result": "Memory test completed.",
            "tool_name": None,
        },
    )

    for _ in range(2):
        response = client.post(
            "/api/tasks",
            json={"task": "I enjoy Java."},
        )

        assert response.status_code == 200

    history = database.get_user_memory_history(
        TEST_USER_ID,
        memory_key="programming.java.preference",
    )

    assert len(history) == 1
