
"""
AEGIS Text Analysis Tool

Provides deterministic text analysis using Python's
Unicode character classification.

Counting conventions
--------------------
word_count:
    Number of whitespace-separated tokens.

character_count:
    Number of Unicode code points, including whitespace.

sentence_count:
    Existing punctuation-based sentence estimate.

letter_count:
    Number of Unicode characters whose category begins with L.

digit_count:
    Number of Unicode decimal digits (category Nd).

whitespace_count:
    Number of characters for which str.isspace() is True.

punctuation_count:
    Number of Unicode characters whose category begins with P.

symbol_count:
    Number of Unicode characters whose category begins with S.
"""

import unicodedata

from app.tools.base import BaseTool


class TextAnalysisTool(BaseTool):
    """Perform deterministic text analysis."""

    name = "text_analysis"
    description = (
        "Analyzes text and calculates eight text metrics."
    )

    def __init__(self):
        self.input_validation_calls = 0

    def execute(self, **kwargs):
        """
        Execute text analysis through the common tool interface.
        """

        if "text" not in kwargs:
            raise TypeError(
                "TextAnalysisTool.execute() requires a 'text' argument."
            )

        unexpected = set(kwargs) - {"text"}

        if unexpected:
            raise TypeError(
                f"Unexpected arguments: {sorted(unexpected)}"
            )

        return self.analyze(kwargs["text"])

    def reset_validation_count(self) -> None:
        """Reset the validation-call counter."""
        self.input_validation_calls = 0

    def _validate_text(self, text: str) -> None:
        """Validate input and record the validation call."""

        self.input_validation_calls += 1

        if not isinstance(text, str):
            raise TypeError("Input must be a string.")

        if not text.strip():
            raise ValueError("Text cannot be empty.")

    def count_words(self, text: str) -> int:
        self._validate_text(text)
        return len(text.split())

    def count_characters(self, text: str) -> int:
        self._validate_text(text)
        return len(text)

    def count_sentences(self, text: str) -> int:
        self._validate_text(text)

        sentences = [
            sentence
            for sentence in (
                text.replace("!", ".")
                .replace("?", ".")
                .split(".")
            )
            if sentence.strip()
        ]

        return len(sentences)

    def count_letters(self, text: str) -> int:
        self._validate_text(text)

        return sum(
            1
            for character in text
            if unicodedata.category(character).startswith("L")
        )

    def count_digits(self, text: str) -> int:
        self._validate_text(text)

        return sum(
            1
            for character in text
            if unicodedata.category(character) == "Nd"
        )

    def count_whitespace(self, text: str) -> int:
        self._validate_text(text)

        return sum(
            1
            for character in text
            if character.isspace()
        )

    def count_punctuation(self, text: str) -> int:
        self._validate_text(text)

        return sum(
            1
            for character in text
            if unicodedata.category(character).startswith("P")
        )

    def count_symbols(self, text: str) -> int:
        self._validate_text(text)

        return sum(
            1
            for character in text
            if unicodedata.category(character).startswith("S")
        )

    def analyze(self, text: str) -> dict:
        """
        Perform all eight metrics in one pass.

        This preserves the original direct-analysis implementation
        and its counting conventions.
        """

        self._validate_text(text)

        words = text.split()

        sentences = [
            sentence
            for sentence in (
                text.replace("!", ".")
                .replace("?", ".")
                .split(".")
            )
            if sentence.strip()
        ]

        letter_count = 0
        digit_count = 0
        whitespace_count = 0
        punctuation_count = 0
        symbol_count = 0

        for character in text:
            category = unicodedata.category(character)

            if category.startswith("L"):
                letter_count += 1

            if category == "Nd":
                digit_count += 1

            if character.isspace():
                whitespace_count += 1

            if category.startswith("P"):
                punctuation_count += 1

            if category.startswith("S"):
                symbol_count += 1

        return {
            "word_count": len(words),
            "character_count": len(text),
            "sentence_count": len(sentences),
            "letter_count": letter_count,
            "digit_count": digit_count,
            "whitespace_count": whitespace_count,
            "punctuation_count": punctuation_count,
            "symbol_count": symbol_count,
        }
