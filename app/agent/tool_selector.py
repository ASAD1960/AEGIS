
"""
AEGIS Tool Selector

Selects the appropriate registered tool based on
the user's task description.

This is a deterministic rule-based selector.
It does not use an external AI API.
"""

import re


class ToolSelector:
    """Select tools based on task keywords and intent."""

    TOOL_KEYWORDS = {
        "data_analysis": {
            "csv",
            "spreadsheet",
            "dataset",
            "data analysis",
            "data analytics",
            "column",
            "columns",
            "row",
            "rows",
        },

        "text_analysis": {
            "text analysis",
            "analyze text",
            "analyse text",
            "analyze this text",
            "analyse this text",
            "count words",
            "count the words",
            "count words and characters",
            "count the words and characters",
            "word count",
            "number of words",
            "how many words",
            "character count",
            "count characters",
            "count the characters",
            "number of characters",
            "how many characters",
            "sentence count",
            "count sentences",
            "count the sentences",
            "number of sentences",
            "how many sentences",
            "count letters",
            "count digits",
            "count symbols",
            "count punctuation",
            "count whitespace",
            "analyze paragraph",
            "analyse paragraph",
        },

        "calculator": {
            "calculate",
            "calculation",
            "compute",
            "addition",
            "add",
            "plus",
            "subtraction",
            "subtract",
            "minus",
            "multiplication",
            "multiply",
            "multiplied",
            "times",
            "division",
            "divide",
            "divided",
            "modulus",
            "remainder",
            "power",
            "square",
        },
    }

    @staticmethod
    def _matches_keyword(task, keyword):
        """
        Match a keyword as a complete word or phrase.

        Prevents accidental matches such as:
        'row' inside 'growing'.
        """

        pattern = (
            r"(?<!\w)"
            + re.escape(keyword)
            + r"(?!\w)"
        )

        return re.search(pattern, task) is not None

    def select(self, task):
        """
        Select a tool for the supplied task.

        Returns:
            str: Registered tool name.

        Raises:
            TypeError: If task is not a string.
            ValueError: If task is empty or no tool can be selected.
        """

        if not isinstance(task, str):
            raise TypeError("Task must be a string.")

        normalized_task = " ".join(task.casefold().split())

        if not normalized_task:
            raise ValueError("Task cannot be empty.")

        # Structured dataset requests take priority.
        if any(
            self._matches_keyword(normalized_task, keyword)
            for keyword in self.TOOL_KEYWORDS["data_analysis"]
        ):
            return "data_analysis"

        # Text-analysis requests.
        if any(
            self._matches_keyword(normalized_task, keyword)
            for keyword in self.TOOL_KEYWORDS["text_analysis"]
        ):
            return "text_analysis"

        # Arithmetic requests.
        if any(
            self._matches_keyword(normalized_task, keyword)
            for keyword in self.TOOL_KEYWORDS["calculator"]
        ):
            return "calculator"

        raise ValueError(
            "Unable to determine the appropriate tool for this task."
        )
