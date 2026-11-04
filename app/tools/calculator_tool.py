
"""
AEGIS Calculator Tool

Provides deterministic arithmetic operations through
the common AEGIS tool interface.
"""

import math

from app.tools.base import BaseTool


class CalculatorTool(BaseTool):
    """Perform basic arithmetic operations."""

    name = "calculator"
    description = (
        "Performs addition, subtraction, multiplication, "
        "division, modulus, and power operations."
    )

    def execute(self, **kwargs):
        """
        Execute an arithmetic operation.

        Required arguments:
            operation: Name of the arithmetic operation.
            a: First numeric operand.
            b: Second numeric operand.
        """

        required = {"operation", "a", "b"}
        missing = required - set(kwargs)

        if missing:
            raise TypeError(
                f"Missing required arguments: {sorted(missing)}"
            )

        unexpected = set(kwargs) - required

        if unexpected:
            raise TypeError(
                f"Unexpected arguments: {sorted(unexpected)}"
            )

        operation = kwargs["operation"]
        a = kwargs["a"]
        b = kwargs["b"]

        if not isinstance(operation, str):
            raise TypeError("Operation must be a string.")

        if isinstance(a, bool) or not isinstance(a, (int, float)):
            raise TypeError("First operand must be a number.")

        if isinstance(b, bool) or not isinstance(b, (int, float)):
            raise TypeError("Second operand must be a number.")

        if not math.isfinite(a) or not math.isfinite(b):
            raise ValueError("Operands must be finite numbers.")

        operations = {
            "add": lambda: a + b,
            "subtract": lambda: a - b,
            "multiply": lambda: a * b,
            "divide": lambda: a / b,
            "modulus": lambda: a % b,
            "power": lambda: a ** b,
        }

        if operation not in operations:
            raise ValueError(
                f"Unsupported operation: {operation}"
            )

        if operation in {"divide", "modulus"} and b == 0:
            raise ZeroDivisionError(
                "Cannot divide or calculate modulus by zero."
            )

        try:
            result = operations[operation]()
        except OverflowError as error:
            raise OverflowError(
                "The operation produced a non-finite result."
            ) from error

        if isinstance(result, complex):
            raise ValueError(
                "Complex-number results are not supported."
            )

        if isinstance(result, float) and not math.isfinite(result):
            raise OverflowError(
                "The operation produced a non-finite result."
            )

        return {
            "operation": operation,
            "a": a,
            "b": b,
            "result": result,
        }
