
import pytest

from app.agent.agent import Agent


@pytest.fixture
def sample_csv(tmp_path):
    csv_file = tmp_path / "sales.csv"

    csv_file.write_text(
        "product,price,quantity\n"
        "Laptop,1000,2\n"
        "Mouse,25,5\n"
        "Keyboard,75,3\n",
        encoding="utf-8",
    )

    return csv_file


def test_routes_calculation_request():
    agent = Agent()

    response = agent.process_request("Add 25 and 10")

    assert response["tool_name"] == "calculator"
    assert response["result"]["result"] == 35


def test_routes_text_analysis_request():
    agent = Agent()

    response = agent.process_request(
        "Count the words and characters in this text: AEGIS is growing."
    )

    assert response["tool_name"] == "text_analysis"
    assert response["result"]["word_count"] == 3


def test_routes_csv_analysis_request(sample_csv):
    agent = Agent()

    response = agent.process_request(
        "Analyze this CSV file",
        file_path=str(sample_csv),
    )

    assert response["tool_name"] == "data_analysis"
    assert response["result"]["row_count"] == 3


def test_csv_request_requires_file_path():
    agent = Agent()

    with pytest.raises(ValueError):
        agent.process_request("Analyze this CSV file")


def test_request_restores_agent_status(sample_csv):
    agent = Agent()

    agent.process_request(
        "Analyze this CSV file",
        file_path=str(sample_csv),
    )

    assert agent.get_status() == "Initialized"
