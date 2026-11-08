
import pytest

from app.memory import database


USER_A = "test-user-a"
USER_B = "test-user-b"


def save_java_memory(
    user_id=USER_A,
    content="I enjoy Java.",
    source_type="explicit_statement",
    source_text="I enjoy Java.",
):
    return database.save_user_memory(
        user_id=user_id,
        memory_key="programming.java.preference",
        content=content,
        category="programming",
        source_type=source_type,
        source_text=source_text,
    )


# ==========================================================
# Saving memories
# ==========================================================

def test_save_explicit_personal_memory():

    memory_id = save_java_memory()

    memories = database.get_user_memories(USER_A)

    assert memory_id
    assert len(memories) == 1

    memory = memories[0]

    assert memory["id"] == memory_id
    assert memory["user_id"] == USER_A
    assert memory["memory_key"] == "programming.java.preference"
    assert memory["content"] == "I enjoy Java."
    assert memory["category"] == "programming"
    assert memory["source_type"] == "explicit_statement"
    assert memory["source_text"] == "I enjoy Java."
    assert memory["status"] == "active"


def test_save_correction_memory():

    memory_id = save_java_memory(
        content="I studied Java in Object-Oriented Programming.",
        source_type="correction",
        source_text=(
            "Correction: I studied Java in Object-Oriented Programming."
        ),
    )

    memories = database.get_user_memories(USER_A)

    assert len(memories) == 1
    assert memories[0]["id"] == memory_id
    assert memories[0]["source_type"] == "correction"


# ==========================================================
# Updating and preserving memory history
# ==========================================================

def test_correction_supersedes_previous_memory():

    original_id = save_java_memory()

    corrected_id = save_java_memory(
        content="I enjoy Java and studied it in OOP.",
        source_type="correction",
        source_text="Correction: I enjoy Java and studied it in OOP.",
    )

    assert original_id != corrected_id

    active_memories = database.get_user_memories(USER_A)

    assert len(active_memories) == 1
    assert active_memories[0]["id"] == corrected_id
    assert active_memories[0]["content"] == (
        "I enjoy Java and studied it in OOP."
    )
    assert active_memories[0]["status"] == "active"

    history = database.get_user_memory_history(
        USER_A,
        memory_key="programming.java.preference",
    )

    assert len(history) == 2

    versions = {memory["id"]: memory for memory in history}

    assert versions[original_id]["status"] == "superseded"
    assert versions[corrected_id]["status"] == "active"


def test_different_memory_keys_remain_independent():

    java_id = save_java_memory()

    python_id = database.save_user_memory(
        user_id=USER_A,
        memory_key="programming.python.experience",
        content="I have used Python.",
        category="programming",
        source_type="explicit_statement",
        source_text="I have used Python.",
    )

    memories = database.get_user_memories(USER_A)

    assert len(memories) == 2
    assert {memory["id"] for memory in memories} == {
        java_id,
        python_id,
    }


# ==========================================================
# Retrieving memories
# ==========================================================

def test_retrieve_memories_by_user():

    save_java_memory(user_id=USER_A)

    database.save_user_memory(
        user_id=USER_B,
        memory_key="programming.java.preference",
        content="Another user's Java preference.",
        category="programming",
        source_type="explicit_statement",
        source_text="Another user's Java preference.",
    )

    memories_a = database.get_user_memories(USER_A)
    memories_b = database.get_user_memories(USER_B)

    assert len(memories_a) == 1
    assert len(memories_b) == 1

    assert memories_a[0]["content"] == "I enjoy Java."
    assert memories_b[0]["content"] == "Another user's Java preference."


def test_retrieve_memories_by_category():

    save_java_memory()

    database.save_user_memory(
        user_id=USER_A,
        memory_key="education.degree",
        content="I completed a bachelor's degree.",
        category="education",
        source_type="explicit_statement",
        source_text="I completed a bachelor's degree.",
    )

    programming = database.get_user_memories(
        USER_A,
        category="programming",
    )

    education = database.get_user_memories(
        USER_A,
        category="education",
    )

    assert len(programming) == 1
    assert programming[0]["category"] == "programming"

    assert len(education) == 1
    assert education[0]["category"] == "education"


def test_retrieve_memories_with_limit():

    for number in range(3):
        database.save_user_memory(
            user_id=USER_A,
            memory_key=f"test.memory.{number}",
            content=f"Test memory {number}.",
            category="test",
            source_type="explicit_statement",
            source_text=f"Test memory {number}.",
        )

    memories = database.get_user_memories(
        USER_A,
        limit=2,
    )

    assert len(memories) == 2


def test_retrieve_memory_history():

    original_id = save_java_memory()

    corrected_id = save_java_memory(
        content="I enjoy Java and studied it in OOP.",
        source_type="correction",
        source_text="Correction: I studied Java in OOP.",
    )

    history = database.get_user_memory_history(USER_A)

    assert len(history) == 2
    assert {memory["id"] for memory in history} == {
        original_id,
        corrected_id,
    }


def test_memory_history_isolated_between_users():

    save_java_memory(user_id=USER_A)

    save_java_memory(
        user_id=USER_B,
        content="Different user's memory.",
        source_text="Different user's memory.",
    )

    history_a = database.get_user_memory_history(USER_A)
    history_b = database.get_user_memory_history(USER_B)

    assert len(history_a) == 1
    assert len(history_b) == 1

    assert history_a[0]["user_id"] == USER_A
    assert history_b[0]["user_id"] == USER_B


# ==========================================================
# User ownership and security
# ==========================================================

def test_user_cannot_delete_another_users_memory():

    memory_id = save_java_memory(user_id=USER_A)

    with pytest.raises(ValueError, match="Memory was not found"):
        database.delete_user_memory(USER_B, memory_id)

    memories = database.get_user_memories(USER_A)

    assert len(memories) == 1
    assert memories[0]["id"] == memory_id


def test_user_cannot_retrieve_another_users_memory_history():

    save_java_memory(user_id=USER_A)

    history = database.get_user_memory_history(USER_B)

    assert history == []


def test_delete_user_memory():

    memory_id = save_java_memory()

    result = database.delete_user_memory(USER_A, memory_id)

    assert result is True
    assert database.get_user_memories(USER_A) == []
    assert database.get_user_memory_history(USER_A) == []


def test_delete_memory_does_not_affect_other_users():

    memory_a = save_java_memory(user_id=USER_A)

    memory_b = save_java_memory(
        user_id=USER_B,
        content="Another user's memory.",
        source_text="Another user's memory.",
    )

    database.delete_user_memory(USER_A, memory_a)

    memories_b = database.get_user_memories(USER_B)

    assert len(memories_b) == 1
    assert memories_b[0]["id"] == memory_b


# ==========================================================
# Input validation
# ==========================================================

@pytest.mark.parametrize(
    "user_id",
    ["", "   ", None, 123],
)
def test_save_memory_rejects_invalid_user_id(user_id):

    with pytest.raises(ValueError):
        database.save_user_memory(
            user_id=user_id,
            memory_key="test.key",
            content="Test content.",
            category="test",
            source_type="explicit_statement",
            source_text="Test source.",
        )


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
def test_save_memory_rejects_empty_required_fields(field, value):

    arguments = {
        "user_id": USER_A,
        "memory_key": "test.key",
        "content": "Test content.",
        "category": "test",
        "source_type": "explicit_statement",
        "source_text": "Test source.",
    }

    arguments[field] = value

    with pytest.raises(ValueError):
        database.save_user_memory(**arguments)


@pytest.mark.parametrize(
    "source_type",
    [
        "inference",
        "conversation_summary",
        "",
        None,
    ],
)
def test_save_memory_rejects_unsupported_source_type(source_type):

    with pytest.raises(ValueError):
        save_java_memory(source_type=source_type)


@pytest.mark.parametrize(
    "limit",
    [0, -1, 1.5, True, "2"],
)
def test_get_user_memories_rejects_invalid_limit(limit):

    with pytest.raises(ValueError):
        database.get_user_memories(USER_A, limit=limit)


def test_get_memory_history_rejects_invalid_limit():

    with pytest.raises(ValueError):
        database.get_user_memory_history(USER_A, limit=0)


def test_delete_memory_rejects_empty_memory_id():

    with pytest.raises(ValueError):
        database.delete_user_memory(USER_A, "")


def test_memory_history_can_be_filtered_by_key():

    java_id = save_java_memory()

    database.save_user_memory(
        user_id=USER_A,
        memory_key="education.degree",
        content="I completed a bachelor's degree.",
        category="education",
        source_type="explicit_statement",
        source_text="I completed a bachelor's degree.",
    )

    history = database.get_user_memory_history(
        USER_A,
        memory_key="programming.java.preference",
    )

    assert len(history) == 1
    assert history[0]["id"] == java_id
