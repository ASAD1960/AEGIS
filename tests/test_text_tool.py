import pytest

from app.tools.text_tool import TextAnalysisTool


@pytest.fixture
def tool():
    return TextAnalysisTool()


def test_preserves_original_metrics(tool):
    result = tool.analyze("AEGIS learns from experience.")

    assert result["word_count"] == 4
    assert result["character_count"] == 29
    assert result["sentence_count"] == 1


def test_counts_unicode_letters(tool):
    result = tool.analyze("café naïve Ελληνικά")

    assert result["letter_count"] == 17


def test_counts_unicode_decimal_digits(tool):
    result = tool.analyze("Year 2026: ٢٠٢٦")

    assert result["digit_count"] == 8


def test_counts_whitespace_characters(tool):
    result = tool.analyze("alpha beta\tgamma\ndelta")

    assert result["whitespace_count"] == 3


def test_separates_punctuation_and_symbols(tool):
    result = tool.analyze("Price: $100!")

    assert result["punctuation_count"] == 2
    assert result["symbol_count"] == 1
    assert result["digit_count"] == 3


def test_counts_emoji_as_unicode_symbols(tool):
    result = tool.analyze("AEGIS 🚀")

    assert result["symbol_count"] == 1


def test_counts_combining_marks_as_codepoints(tool):
    text = "cafe\u0301"

    result = tool.analyze(text)

    assert result["character_count"] == 5
    assert result["letter_count"] == 4


def test_returns_all_expected_metrics(tool):
    result = tool.analyze("AEGIS 2026! $100 € café 🚀")

    expected_fields = {
        "word_count",
        "character_count",
        "sentence_count",
        "letter_count",
        "digit_count",
        "whitespace_count",
        "punctuation_count",
        "symbol_count",
    }

    assert set(result.keys()) == expected_fields


def test_rejects_non_string_input(tool):
    with pytest.raises(TypeError):
        tool.analyze(123)


def test_rejects_empty_input(tool):
    with pytest.raises(ValueError):
        tool.analyze("")


def test_rejects_whitespace_only_input(tool):
    with pytest.raises(ValueError):
        tool.analyze("   \t\n")
