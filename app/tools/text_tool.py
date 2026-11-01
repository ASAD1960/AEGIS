
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

Note:
    Unicode code points are not necessarily the same as
    user-perceived characters. Some emoji and accented
    characters consist of multiple code points.
"""

import unicodedata


class TextAnalysisTool:
    """Perform deterministic text analysis."""

    def analyze(self, text: str) -> dict:
        """
        Analyze text and return its original and extended metrics.

        Existing metric definitions are preserved for compatibility.
        """

        if not isinstance(text, str):
            raise TypeError("Input must be a string.")

        if not text.strip():
            raise ValueError("Text cannot be empty.")

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
            # Existing metrics: preserve their behavior.
            "word_count": len(words),
            "character_count": len(text),
            "sentence_count": len(sentences),

            # BE-02: Unicode-aware character analysis.
            "letter_count": letter_count,
            "digit_count": digit_count,
            "whitespace_count": whitespace_count,
            "punctuation_count": punctuation_count,
            "symbol_count": symbol_count,
        }
