
import pytest

from app.agent.agent import Agent


def test_agent_processes_natural_language_text_analysis():
    agent = Agent()

    task = "Count the words and characters in this text: AEGIS is growing."

    response = agent.process_text_analysis(task)

    assert response["tool_name"] == "text_analysis"
    assert response["arguments"]["text"] == "AEGIS is growing."

    result = response["result"]

    assert result["word_count"] == 3
    assert result["character_count"] == 17
    assert result["sentence_count"] == 1
    assert result["letter_count"] == 14
    assert result["whitespace_count"] == 2
    assert result["punctuation_count"] == 1
    assert result["digit_count"] == 0
    assert result["symbol_count"] == 0


def test_agent_processes_text_analysis_with_different_wording():
    agent = Agent()

    task = "Analyze this text: Python makes development easier."

    response = agent.process_text_analysis(task)

    assert response["tool_name"] == "text_analysis"
    assert response["arguments"]["text"] == (
        "Python makes development easier."
    )
    assert response["result"]["word_count"] == 4


def test_agent_rejects_empty_text_content():
    agent = Agent()

    with pytest.raises(ValueError):
        agent.process_text_analysis(
            "Analyze this text:"
        )


def test_agent_rejects_unsupported_text_analysis_request():
    agent = Agent()

    with pytest.raises(ValueError):
        agent.process_text_analysis(
            "Analyze this text without providing any content"
        )


def test_agent_restores_status_after_text_analysis():
    agent = Agent()

    agent.process_text_analysis(
        "Analyze this text: AEGIS is growing."
    )

    assert agent.get_status() == "Initialized"


def test_agent_restores_status_after_text_analysis_failure():
    agent = Agent()

    with pytest.raises(ValueError):
        agent.process_text_analysis("Analyze this text:")

    assert agent.get_status() == "Initialized"
