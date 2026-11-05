
import pytest

from app.memory import database


@pytest.fixture
def conversation_db(tmp_path, monkeypatch):
    """Use a separate temporary database for every test."""

    test_database = tmp_path / "test_aegis.db"

    monkeypatch.setattr(
        database,
        "DATABASE_PATH",
        test_database,
    )

    database.initialize_database()

    return database


def test_conversation_is_created(conversation_db):
    conversation_id = conversation_db.create_conversation()

    assert isinstance(conversation_id, str)
    assert len(conversation_id) == 36

    conversations = conversation_db.get_all_conversations()

    assert len(conversations) == 1
    assert conversations[0]["id"] == conversation_id
    assert conversations[0]["title"] == "New conversation"


def test_user_message_is_persisted(conversation_db):
    conversation_id = conversation_db.create_conversation()

    message_id = conversation_db.save_conversation_message(
        conversation_id=conversation_id,
        role="user",
        content="Hello AEGIS",
    )

    messages = conversation_db.get_conversation_messages(
        conversation_id
    )

    assert message_id > 0
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello AEGIS"


def test_assistant_message_is_persisted(conversation_db):
    conversation_id = conversation_db.create_conversation()

    conversation_db.save_conversation_message(
        conversation_id,
        "user",
        "Hello",
    )

    conversation_db.save_conversation_message(
        conversation_id,
        "assistant",
        "Hello! How can I help?",
        tool_name="cloudflare",
    )

    messages = conversation_db.get_conversation_messages(
        conversation_id
    )

    assert len(messages) == 2
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Hello! How can I help?"
    assert messages[1]["tool_name"] == "cloudflare"


def test_conversation_title_uses_first_user_message(conversation_db):
    conversation_id = conversation_db.create_conversation()

    conversation_db.save_conversation_message(
        conversation_id,
        "user",
        "Explain artificial intelligence",
    )

    conversations = conversation_db.get_all_conversations()

    assert conversations[0]["title"] == (
        "Explain artificial intelligence"
    )


def test_messages_are_returned_in_chronological_order(conversation_db):
    conversation_id = conversation_db.create_conversation()

    conversation_db.save_conversation_message(
        conversation_id,
        "user",
        "First message",
    )

    conversation_db.save_conversation_message(
        conversation_id,
        "assistant",
        "First response",
    )

    conversation_db.save_conversation_message(
        conversation_id,
        "user",
        "Second message",
    )

    messages = conversation_db.get_conversation_messages(
        conversation_id
    )

    assert [message["content"] for message in messages] == [
        "First message",
        "First response",
        "Second message",
    ]


def test_message_history_limit_returns_latest_messages(conversation_db):
    conversation_id = conversation_db.create_conversation()

    for number in range(5):
        conversation_db.save_conversation_message(
            conversation_id,
            "user",
            f"Message {number}",
        )

    messages = conversation_db.get_conversation_messages(
        conversation_id,
        limit=2,
    )

    assert len(messages) == 2
    assert messages[0]["content"] == "Message 3"
    assert messages[1]["content"] == "Message 4"


def test_conversation_list_includes_message_count(conversation_db):
    conversation_id = conversation_db.create_conversation()

    conversation_db.save_conversation_message(
        conversation_id,
        "user",
        "Hello",
    )

    conversation_db.save_conversation_message(
        conversation_id,
        "assistant",
        "Hello there",
    )

    conversations = conversation_db.get_all_conversations()

    assert len(conversations) == 1
    assert conversations[0]["message_count"] == 2


def test_conversation_can_be_deleted(conversation_db):
    conversation_id = conversation_db.create_conversation()

    conversation_db.save_conversation_message(
        conversation_id,
        "user",
        "Delete this conversation",
    )

    result = conversation_db.delete_conversation(conversation_id)

    assert result is True
    assert conversation_db.get_all_conversations() == []


def test_deleting_conversation_also_deletes_messages(conversation_db):
    conversation_id = conversation_db.create_conversation()

    conversation_db.save_conversation_message(
        conversation_id,
        "user",
        "This message should also disappear",
    )

    conversation_db.delete_conversation(conversation_id)

    with conversation_db.get_connection() as connection:
        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM conversation_messages
            WHERE conversation_id = ?
            """,
            (conversation_id,),
        ).fetchone()[0]

    assert count == 0


def test_invalid_message_role_is_rejected(conversation_db):
    conversation_id = conversation_db.create_conversation()

    with pytest.raises(ValueError):
        conversation_db.save_conversation_message(
            conversation_id,
            "system",
            "Invalid role",
        )


def test_empty_message_is_rejected(conversation_db):
    conversation_id = conversation_db.create_conversation()

    with pytest.raises(ValueError):
        conversation_db.save_conversation_message(
            conversation_id,
            "user",
            "   ",
        )


def test_missing_conversation_is_rejected(conversation_db):
    with pytest.raises(ValueError):
        conversation_db.get_conversation_messages(
            "non-existent-conversation"
        )


def test_invalid_history_limit_is_rejected(conversation_db):
    conversation_id = conversation_db.create_conversation()

    with pytest.raises(ValueError):
        conversation_db.get_conversation_messages(
            conversation_id,
            limit=0,
        )
