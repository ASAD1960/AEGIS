
import pytest

from app.agent.task_parser import TaskParser


@pytest.fixture
def parser():
    return TaskParser()


@pytest.mark.parametrize(
    ("task", "expected_operation", "expected_a", "expected_b"),
    [
        ("Add 25 and 10", "add", 25, 10),
        ("Subtract 10 from 25", "subtract", 25, 10),
        ("Multiply 12 by 5", "multiply", 12, 5),
        ("Divide 100 by 4", "divide", 100, 4),
        (
            "Find the remainder when 17 is divided by 5",
            "modulus",
            17,
            5,
        ),
        ("Raise 2 to the power of 3", "power", 2, 3),
    ],
)
def test_parses_arithmetic_operations(
    parser, task, expected_operation, expected_a, expected_b
):
    result = parser.parse(task)

    assert result["tool_name"] == "calculator"
    assert result["arguments"] == {
        "operation": expected_operation,
        "a": expected_a,
        "b": expected_b,
    }


@pytest.mark.parametrize(
    ("task", "expected_a", "expected_b"),
    [
        ("Add 2.5 and 1.5", 2.5, 1.5),
        ("Multiply -3 by 2", -3, 2),
        ("Subtract -5 from 10", 10, -5),
        ("Divide 7 by 2", 7, 2),
    ],
)
def test_parses_decimal_and_negative_numbers(
    parser, task, expected_a, expected_b
):
    result = parser.parse(task)

    assert result["arguments"]["a"] == expected_a
    assert result["arguments"]["b"] == expected_b


def test_normalizes_extra_whitespace(parser):
    result = parser.parse("  Add   25   and   10  ")

    assert result["arguments"] == {
        "operation": "add",
        "a": 25,
        "b": 10,
    }


def test_parsing_is_case_insensitive(parser):
    result = parser.parse("MULTIPLY 12 BY 5")

    assert result["arguments"]["operation"] == "multiply"


@pytest.mark.parametrize(
    "task",
    [
        "",
        "   ",
        "Calculate something",
        "Add 10",
        "Multiply ten by five",
        "Divide 100 by",
        "What is the weather today?",
    ],
)
def test_rejects_empty_or_unsupported_requests(parser, task):
    with pytest.raises(ValueError):
        parser.parse(task)


@pytest.mark.parametrize(
    "task",
    [
        None,
        123,
        ["Add", 25, 10],
    ],
)
def test_rejects_non_string_input(parser, task):
    with pytest.raises(TypeError):
        parser.parse(task)
