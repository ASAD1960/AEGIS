
import pytest

from app.memory.extraction import extract_personal_memory_candidates


def test_extract_explicit_java_preference():
    result = extract_personal_memory_candidates("I enjoy Java.")

    assert len(result) == 1
    assert result[0]["memory_key"] == "programming.java.preference"
    assert result[0]["content"] == "The user enjoys Java."
    assert result[0]["source_type"] == "explicit_statement"
    assert result[0]["source_text"] == "I enjoy Java."
    assert result[0]["action"] == "save"


def test_extract_java_oop_study():
    result = extract_personal_memory_candidates("I studied Java in OOP.")

    assert len(result) == 1
    assert result[0]["memory_key"] == "education.java.oop_study"
    assert result[0]["content"] == (
        "The user studied Java in Object-Oriented Programming."
    )


def test_extract_combined_java_preference_and_study():
    result = extract_personal_memory_candidates(
        "I enjoy Java and studied it in OOP."
    )

    assert len(result) == 2

    keys = {item["memory_key"] for item in result}

    assert keys == {
        "programming.java.preference",
        "education.java.oop_study",
    }


def test_extract_explicit_correction():
    result = extract_personal_memory_candidates(
        "Correction: I enjoy Java."
    )

    assert len(result) == 1
    assert result[0]["source_type"] == "correction"
    assert result[0]["source_text"] == "Correction: I enjoy Java."


def test_extract_negative_preference():
    result = extract_personal_memory_candidates("I don't enjoy Java.")

    assert len(result) == 1
    assert result[0]["content"] == "The user does not enjoy Java."


def test_ambiguous_learning_intention_requires_confirmation():
    result = extract_personal_memory_candidates("I might learn Python.")

    assert len(result) == 1
    assert result[0]["action"] == "confirm"
    assert result[0]["source_type"] is None


def test_questions_are_not_saved():
    result = extract_personal_memory_candidates(
        "Do you think Java is useful?"
    )

    assert result == []


@pytest.mark.parametrize(
    "message",
    [
        "Tell me about Java bytecode.",
        "Explain the JVM.",
        "Java is an interesting language.",
        "I understand JVM and bytecode in depth.",
        "I have mastered Java.",
        "What is object-oriented programming?",
    ],
)
def test_general_discussion_does_not_create_personal_memories(message):
    result = extract_personal_memory_candidates(message)

    assert result == []


def test_empty_message_returns_no_candidates():
    assert extract_personal_memory_candidates("") == []


def test_non_string_message_returns_no_candidates():
    assert extract_personal_memory_candidates(None) == []


def test_oversized_message_returns_no_candidates():
    message = "I enjoy Java. " * 500

    assert extract_personal_memory_candidates(message) == []


def test_unrecognized_language_is_not_extracted():
    result = extract_personal_memory_candidates("I enjoy Rust.")

    assert result == []


@pytest.mark.parametrize(
    "message",
    [
        '"I enjoy Java."',
        "My friend says I enjoy Java.",
        "I don't think I enjoy Java.",
        "I don't know if I enjoy Java.",
    ],
)
def test_unreliable_context_does_not_create_personal_memory(message):
    result = extract_personal_memory_candidates(message)

    assert result == []


def test_correction_extracts_multiple_supported_facts():
    result = extract_personal_memory_candidates(
        "Correction: I enjoy Java and studied it in OOP."
    )

    assert len(result) == 2
    assert all(item["source_type"] == "correction" for item in result)
    assert all(item["action"] == "save" for item in result)

    keys = {item["memory_key"] for item in result}

    assert keys == {
        "programming.java.preference",
        "education.java.oop_study",
    }


def test_to_clarify_prefix_is_recognized():
    result = extract_personal_memory_candidates(
        "To clarify: I enjoy Python."
    )

    assert len(result) == 1
    assert result[0]["source_type"] == "correction"


def test_multiple_sentences_are_extracted_independently():
    result = extract_personal_memory_candidates(
        "I enjoy Java. I studied Java in OOP."
    )

    assert len(result) == 2
    assert all(
        item["source_type"] == "explicit_statement"
        for item in result
    )


def test_ambiguous_intention_does_not_become_automatic_save():
    result = extract_personal_memory_candidates("I might learn Python.")

    assert len(result) == 1
    assert result[0]["action"] == "confirm"
    assert result[0]["source_type"] is None
