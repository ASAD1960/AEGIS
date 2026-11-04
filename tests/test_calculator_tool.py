
import pytest

from app.tools.calculator_tool import CalculatorTool


@pytest.fixture
def calculator():
    return CalculatorTool()


@pytest.mark.parametrize(
    ("operation", "a", "b", "expected"),
    [
        ("add", 10, 5, 15),
        ("subtract", 10, 5, 5),
        ("multiply", 10, 5, 50),
        ("divide", 10, 5, 2),
        ("modulus", 10, 3, 1),
        ("power", 2, 3, 8),
    ],
)
def test_calculator_operations(
    calculator, operation, a, b, expected
):
    result = calculator.execute(
        operation=operation,
        a=a,
        b=b,
    )

    assert result["operation"] == operation
    assert result["a"] == a
    assert result["b"] == b
    assert result["result"] == expected


@pytest.mark.parametrize("operation", ["divide", "modulus"])
def test_zero_division_protection(calculator, operation):
    with pytest.raises(ZeroDivisionError):
        calculator.execute(
            operation=operation,
            a=10,
            b=0,
        )


def test_unsupported_operation(calculator):
    with pytest.raises(ValueError, match="Unsupported operation"):
        calculator.execute(
            operation="square_root",
            a=16,
            b=2,
        )


def test_missing_arguments(calculator):
    with pytest.raises(TypeError, match="Missing required arguments"):
        calculator.execute(
            operation="add",
            a=10,
        )


def test_unexpected_arguments(calculator):
    with pytest.raises(TypeError, match="Unexpected arguments"):
        calculator.execute(
            operation="add",
            a=10,
            b=5,
            extra=1,
        )


@pytest.mark.parametrize(
    ("a", "b"),
    [
        (True, 5),
        (10, False),
        ("10", 5),
        (10, "5"),
    ],
)
def test_rejects_invalid_operands(calculator, a, b):
    with pytest.raises(TypeError):
        calculator.execute(
            operation="add",
            a=a,
            b=b,
        )


@pytest.mark.parametrize(
    ("a", "b"),
    [
        (float("nan"), 5),
        (10, float("inf")),
        (float("-inf"), 5),
    ],
)
def test_rejects_non_finite_operands(calculator, a, b):
    with pytest.raises(ValueError, match="finite numbers"):
        calculator.execute(
            operation="add",
            a=a,
            b=b,
        )


def test_rejects_complex_results(calculator):
    with pytest.raises(ValueError, match="Complex-number results"):
        calculator.execute(
            operation="power",
            a=-1,
            b=0.5,
        )


def test_rejects_non_finite_results(calculator):
    with pytest.raises(OverflowError, match="non-finite result"):
        calculator.execute(
            operation="power",
            a=1e308,
            b=2,
        )
