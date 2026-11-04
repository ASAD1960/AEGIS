
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


def test_agent_processes_csv_analysis(sample_csv):
    agent = Agent()

    response = agent.process_data_analysis(
        "Analyze this CSV file",
        str(sample_csv),
    )

    assert response["tool_name"] == "data_analysis"
    assert response["arguments"]["file_path"] == str(sample_csv)

    result = response["result"]

    assert result["file_name"] == "sales.csv"
    assert result["source_row_count"] == 3
    assert result["row_count"] == 3
    assert result["column_count"] == 3
    assert result["columns"] == ["product", "price", "quantity"]


def test_agent_processes_filtered_csv_analysis(sample_csv):
    agent = Agent()

    response = agent.process_data_analysis(
        "Analyze this CSV dataset",
        str(sample_csv),
        filter_column="price",
        filter_operator=">",
        filter_value=50,
    )

    result = response["result"]

    assert result["filtered"] is True
    assert result["source_row_count"] == 3
    assert result["row_count"] == 2


def test_agent_rejects_non_data_analysis_request(sample_csv):
    agent = Agent()

    with pytest.raises(ValueError):
        agent.process_data_analysis(
            "Calculate 25 multiplied by 4",
            str(sample_csv),
        )


def test_agent_rejects_missing_csv_file():
    agent = Agent()

    with pytest.raises((ValueError, FileNotFoundError)):
        agent.process_data_analysis(
            "Analyze this CSV file",
            "missing_file.csv",
        )


def test_agent_restores_status_after_csv_analysis(sample_csv):
    agent = Agent()

    agent.process_data_analysis(
        "Analyze this CSV file",
        str(sample_csv),
    )

    assert agent.get_status() == "Initialized"


def test_agent_restores_status_after_csv_analysis_failure():
    agent = Agent()

    with pytest.raises((ValueError, FileNotFoundError)):
        agent.process_data_analysis(
            "Analyze this CSV file",
            "missing_file.csv",
        )

    assert agent.get_status() == "Initialized"
