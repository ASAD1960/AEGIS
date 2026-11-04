
import pytest

from app.agent.agent import Agent


@pytest.fixture
def agent():
    return Agent()


@pytest.mark.parametrize(
    ("task", "expected_operation", "expected_result"),
    [
        ("Add 25 and 10", "add", 35),
        ("Subtract 10 from 25", "subtract", 15),
        ("Multiply 12 by 5", "multiply", 60),
        ("Divide 100 by 4", "divide", 25),
        (
            "Find the remainder when 17 is divided by 5",
            "modulus",
            2,
        ),
        ("Raise 2 to the power of 3", "power", 8),
    ],
)
def test_agent_processes_calculations(
    agent, task, expected_operation, expected_result
):
    response = agent.process_calculation(task)

    assert response["tool_name"] == "calculator"
    assert response["arguments"]["operation"] == expected_operation
    assert response["result"]["result"] == expected_result


def test_agent_returns_calculator_arguments(agent):
    response = agent.process_calculation("Multiply 12 by 5")

    assert response["arguments"] == {
        "operation": "multiply",
        "a": 12,
        "b": 5,
    }


def test_agent_restores_status_after_calculation(agent):
    agent.process_calculation("Add 25 and 10")

    assert agent.get_status() == "Initialized"


def test_agent_rejects_unsupported_calculation(agent):
    with pytest.raises(ValueError):
        agent.process_calculation("Calculate something")


def test_agent_restores_status_after_failed_calculation(agent):
    with pytest.raises(ValueError):
        agent.process_calculation("Calculate something")

    assert agent.get_status() == "Initialized"


def test_agent_does_not_change_research_execution(agent):
    result = agent.perform_task(
        "AEGIS research platform",
        strategy_id="direct",
    )

    assert result["strategy_id"] == "direct"
    assert result["results"]["analyze_text"]["word_count"] == 3
