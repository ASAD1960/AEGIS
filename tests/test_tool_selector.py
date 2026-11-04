
import pytest

from app.agent.tool_selector import ToolSelector


@pytest.fixture
def selector():
    return ToolSelector()


@pytest.mark.parametrize(
    ("task", "expected"),
    [
        ("Calculate 250 multiplied by 8", "calculator"),
        ("Perform addition", "calculator"),
        ("Find the remainder", "calculator"),
        ("Analyze this CSV dataset", "data_analysis"),
        ("Show me the columns in this spreadsheet", "data_analysis"),
        ("Count words in this paragraph", "text_analysis"),
        ("Calculate the number of characters in this text", "text_analysis"),
        ("Calculate the number of words in this paragraph", "text_analysis"),
    ],
)
def test_selects_correct_tool(selector, task, expected):
    assert selector.select(task) == expected


def test_selection_is_case_insensitive(selector):
    assert selector.select("COUNT WORDS IN THIS TEXT") == "text_analysis"


def test_selection_handles_extra_whitespace(selector):
    assert selector.select("  Calculate   25   multiplied by 4  ") == "calculator"


def test_data_analysis_has_priority(selector):
    assert selector.select("Analyze this CSV dataset") == "data_analysis"


def test_text_analysis_has_priority_over_calculation_keyword(selector):
    task = "Calculate the number of characters in this text"
    assert selector.select(task) == "text_analysis"


@pytest.mark.parametrize(
    "task",
    [
        "",
        "   ",
        "Analyze this",
        "Do something useful",
    ],
)
def test_rejects_empty_or_ambiguous_tasks(selector, task):
    with pytest.raises(ValueError):
        selector.select(task)


@pytest.mark.parametrize(
    "task",
    [
        None,
        123,
        ["calculate", "10"],
    ],
)
def test_rejects_non_string_tasks(selector, task):
    with pytest.raises(TypeError):
        selector.select(task)
