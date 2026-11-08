
import pytest

from app.memory import database


USER_ID = "test-user-1"
OTHER_USER_ID = "test-user-2"


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
    conversation_id = conversation_db.create_conversation(USER_ID)

    assert isinstance(conversation_id, str)
    assert len(conversation_id) == 36

    conversations = conversation_db.get_all_conversations(USER_ID)

    assert len(conversations) == 1
    assert conversations[0]["id"] == conversation_id
    assert conversations[0]["title"] == "New conversation"


def test_user_message_is_persisted(conversation_db):
    conversation_id = conversation_db.create_conversation(USER_ID)

    message_id = conversation_db.save_conversation_message(
        conversation_id=conversation_id,
        user_id=USER_ID,
        role="user",
        content="Hello AEGIS",
    )

    messages = conversation_db.get_conversation_messages(
        conversation_id,
        USER_ID,
    )

    assert message_id > 0
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello AEGIS"


def test_assistant_message_is_persisted(conversation_db):
    conversation_id = conversation_db.create_conversation(USER_ID)

    conversation_db.save_conversation_message(
        conversation_id=conversation_id,
        user_id=USER_ID,
        role="user",
        content="Hello",
    )

    conversation_db.save_conversation_message(
        conversation_id=conversation_id,
        user_id=USER_ID,
        role="assistant",
        content="Hello! How can I help?",
        tool_name="cloudflare",
    )

    messages = conversation_db.get_conversation_messages(
        conversation_id,
        USER_ID,
    )

    assert len(messages) == 2
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Hello! How can I help?"
    assert messages[1]["tool_name"] == "cloudflare"


def test_conversation_title_uses_first_user_message(conversation_db):
    conversation_id = conversation_db.create_conversation(USER_ID)

    conversation_db.save_conversation_message(
        conversation_id=conversation_id,
        user_id=USER_ID,
        role="user",
        content="Explain artificial intelligence",
    )

    conversations = conversation_db.get_all_conversations(USER_ID)

    assert conversations[0]["title"] == (
        "Explain artificial intelligence"
    )


def test_messages_are_returned_in_chronological_order(conversation_db):
    conversation_id = conversation_db.create_conversation(USER_ID)

    conversation_db.save_conversation_message(
        conversation_id, USER_ID, "user", "First message"
    )

    conversation_db.save_conversation_message(
        conversation_id, USER_ID, "assistant", "First response"
    )

    conversation_db.save_conversation_message(
        conversation_id, USER_ID, "user", "Second message"
    )

    messages = conversation_db.get_conversation_messages(
        conversation_id,
        USER_ID,
    )

    assert [message["content"] for message in messages] == [
        "First message",
        "First response",
        "Second message",
    ]


def test_message_history_limit_returns_latest_messages(conversation_db):
    conversation_id = conversation_db.create_conversation(USER_ID)

    for number in range(5):
        conversation_db.save_conversation_message(
            conversation_id,
            USER_ID,
            "user",
            f"Message {number}",
        )

    messages = conversation_db.get_conversation_messages(
        conversation_id,
        USER_ID,
        limit=2,
    )

    assert len(messages) == 2
    assert messages[0]["content"] == "Message 3"
    assert messages[1]["content"] == "Message 4"


def test_conversation_list_includes_message_count(conversation_db):
    conversation_id = conversation_db.create_conversation(USER_ID)

    conversation_db.save_conversation_message(
        conversation_id, USER_ID, "user", "Hello"
    )

    conversation_db.save_conversation_message(
        conversation_id, USER_ID, "assistant", "Hello there"
    )

    conversations = conversation_db.get_all_conversations(USER_ID)

    assert len(conversations) == 1
    assert conversations[0]["message_count"] == 2


def test_conversation_can_be_deleted(conversation_db):
    conversation_id = conversation_db.create_conversation(USER_ID)

    conversation_db.save_conversation_message(
        conversation_id, USER_ID, "user", "Delete this conversation"
    )

    result = conversation_db.delete_conversation(
        conversation_id,
        USER_ID,
    )

    assert result is True
    assert conversation_db.get_all_conversations(USER_ID) == []


def test_deleting_conversation_also_deletes_messages(conversation_db):
    conversation_id = conversation_db.create_conversation(USER_ID)

    conversation_db.save_conversation_message(
        conversation_id,
        USER_ID,
        "user",
        "This message should also disappear",
    )

    conversation_db.delete_conversation(
        conversation_id,
        USER_ID,
    )

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
    conversation_id = conversation_db.create_conversation(USER_ID)

    with pytest.raises(ValueError):
        conversation_db.save_conversation_message(
            conversation_id,
            USER_ID,
            "system",
            "Invalid role",
        )


def test_empty_message_is_rejected(conversation_db):
    conversation_id = conversation_db.create_conversation(USER_ID)

    with pytest.raises(ValueError):
        conversation_db.save_conversation_message(
            conversation_id,
            USER_ID,
            "user",
            "   ",
        )


def test_missing_conversation_is_rejected(conversation_db):
    with pytest.raises(ValueError):
        conversation_db.get_conversation_messages(
            "non-existent-conversation",
            USER_ID,
        )


def test_invalid_history_limit_is_rejected(conversation_db):
    conversation_id = conversation_db.create_conversation(USER_ID)

    with pytest.raises(ValueError):
        conversation_db.get_conversation_messages(
            conversation_id,
            USER_ID,
            limit=0,
        )


# --------------------------------------------------
# User ownership and isolation tests
# --------------------------------------------------

def test_users_only_see_their_own_conversations(conversation_db):
    first_conversation = conversation_db.create_conversation(USER_ID)
    second_conversation = conversation_db.create_conversation(OTHER_USER_ID)

    first_user_conversations = conversation_db.get_all_conversations(
        USER_ID
    )

    second_user_conversations = conversation_db.get_all_conversations(
        OTHER_USER_ID
    )

    assert len(first_user_conversations) == 1
    assert first_user_conversations[0]["id"] == first_conversation

    assert len(second_user_conversations) == 1
    assert second_user_conversations[0]["id"] == second_conversation


def test_user_cannot_read_another_users_conversation(conversation_db):
    conversation_id = conversation_db.create_conversation(USER_ID)

    conversation_db.save_conversation_message(
        conversation_id,
        USER_ID,
        "user",
        "Private message",
    )

    with pytest.raises(ValueError):
        conversation_db.get_conversation_messages(
            conversation_id,
            OTHER_USER_ID,
        )


def test_user_cannot_add_messages_to_another_users_conversation(
    conversation_db,
):
    conversation_id = conversation_db.create_conversation(USER_ID)

    with pytest.raises(ValueError):
        conversation_db.save_conversation_message(
            conversation_id,
            OTHER_USER_ID,
            "user",
            "Unauthorized message",
        )


def test_user_cannot_delete_another_users_conversation(conversation_db):
    conversation_id = conversation_db.create_conversation(USER_ID)

    with pytest.raises(ValueError):
        conversation_db.delete_conversation(
            conversation_id,
            OTHER_USER_ID,
        )

    # The original owner must still have access.
    conversations = conversation_db.get_all_conversations(USER_ID)

    assert len(conversations) == 1
    assert conversations[0]["id"] == conversation_id


def test_users_cannot_access_conversations_with_empty_user_id(
    conversation_db,
):
    with pytest.raises(ValueError):
        conversation_db.create_conversation("")


def test_conversation_messages_are_isolated_between_users(conversation_db):
    first_conversation = conversation_db.create_conversation(USER_ID)
    second_conversation = conversation_db.create_conversation(OTHER_USER_ID)

    conversation_db.save_conversation_message(
        first_conversation,
        USER_ID,
        "user",
        "First user's private message",
    )

    conversation_db.save_conversation_message(
        second_conversation,
        OTHER_USER_ID,
        "user",
        "Second user's private message",
    )

    first_messages = conversation_db.get_conversation_messages(
        first_conversation,
        USER_ID,
    )

    second_messages = conversation_db.get_conversation_messages(
        second_conversation,
        OTHER_USER_ID,
    )

    assert first_messages[0]["content"] == "First user's private message"
    assert second_messages[0]["content"] == "Second user's private message"
