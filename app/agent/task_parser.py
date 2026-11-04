
"""
AEGIS Task Parser

Converts supported natural-language arithmetic requests
into structured arguments for registered tools.

This is a deterministic parser, not an AI language model.
"""

import re


class TaskParser:
    """Parse simple arithmetic requests."""

    NUMBER = r"-?\d+(?:\.\d+)?"

    PATTERNS = [
        (
            "add",
            re.compile(
                rf"^(?:add|calculate the sum of)\s+"
                rf"({NUMBER})\s+(?:and|to)\s+({NUMBER})$",
                re.IGNORECASE,
            ),
        ),
        (
            "subtract",
            re.compile(
                rf"^subtract\s+({NUMBER})\s+from\s+({NUMBER})$",
                re.IGNORECASE,
            ),
        ),
        (
            "multiply",
            re.compile(
                rf"^(?:multiply|calculate)\s+({NUMBER})\s+"
                rf"(?:by|times)\s+({NUMBER})$",
                re.IGNORECASE,
            ),
        ),
        (
            "divide",
            re.compile(
                rf"^divide\s+({NUMBER})\s+by\s+({NUMBER})$",
                re.IGNORECASE,
            ),
        ),
        (
            "modulus",
            re.compile(
                rf"^find the remainder when\s+({NUMBER})\s+"
                rf"is divided by\s+({NUMBER})$",
                re.IGNORECASE,
            ),
        ),
        (
            "power",
            re.compile(
                rf"^(?:raise|calculate)\s+({NUMBER})\s+"
                rf"to the power of\s+({NUMBER})$",
                re.IGNORECASE,
            ),
        ),
    ]

    def parse(self, task):
        """
        Parse an arithmetic task.

        Returns:
            dict: Tool name and calculator arguments.

        Raises:
            TypeError: If task is not a string.
            ValueError: If the task is empty or unsupported.
        """

        if not isinstance(task, str):
            raise TypeError("Task must be a string.")

        normalized_task = " ".join(task.strip().split())

        if not normalized_task:
            raise ValueError("Task cannot be empty.")

        for operation, pattern in self.PATTERNS:

            match = pattern.fullmatch(normalized_task)

            if match:

                first = self._convert_number(match.group(1))
                second = self._convert_number(match.group(2))

                # Natural-language subtraction is reversed:
                # "subtract 10 from 25" means 25 - 10.
                if operation == "subtract":
                    first, second = second, first

                return {
                    "tool_name": "calculator",
                    "arguments": {
                        "operation": operation,
                        "a": first,
                        "b": second,
                    },
                }

        raise ValueError(
            "Unable to understand this arithmetic request."
        )

    @staticmethod
    def _convert_number(value):
        """Convert a numeric string into an int or float."""

        number = float(value)

        if number.is_integer():
            return int(number)

        return number
