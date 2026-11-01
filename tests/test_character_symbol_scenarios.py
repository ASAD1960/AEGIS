import random
import unicodedata

import pytest

from app.benchmark.scenario_families import (
    INITIAL_SCENARIO_FAMILIES,
    build_character_symbol_case,
    calculate_reference_text_metrics,
)
from app.tools.text_tool import TextAnalysisTool


@pytest.fixture
def text_tool():
    return TextAnalysisTool()


@pytest.mark.parametrize(
    "difficulty",
    ["basic", "intermediate", "advanced"],
)
def test_builder_generates_valid_case(difficulty):

    case = build_character_symbol_case(
        variant_index=1,
        difficulty=difficulty,
        rng=random.Random(42),
    )

    assert case["task"]
    assert isinstance(case["context"]["text"], str)
    assert case["expected_outcome"]
    assert len(case["expected_outcome"]) == 8
    assert "text_tool" in case["allowed_tools"]


@pytest.mark.parametrize(
    "difficulty",
    ["basic", "intermediate", "advanced"],
)
def test_builder_expected_metrics_match_independent_reference(
    difficulty,
    text_tool,
):

    case = build_character_symbol_case(
        variant_index=1,
        difficulty=difficulty,
        rng=random.Random(42),
    )

    text = case["context"]["text"]

    reference = calculate_reference_text_metrics(text)
    actual = text_tool.analyze(text)

    assert case["expected_outcome"] == reference
    assert actual == reference


def test_builder_is_reproducible():

    first = build_character_symbol_case(
        variant_index=1,
        difficulty="intermediate",
        rng=random.Random(42),
    )

    second = build_character_symbol_case(
        variant_index=1,
        difficulty="intermediate",
        rng=random.Random(42),
    )

    assert first == second


def test_builder_rejects_unsupported_difficulty():

    with pytest.raises(
        ValueError,
        match="Unsupported difficulty",
    ):
        build_character_symbol_case(
            variant_index=1,
            difficulty="expert",
            rng=random.Random(42),
        )


def test_reference_calculator_distinguishes_unicode_categories():

    text = "Aé ١٢٣ ! $ 🚀"

    metrics = calculate_reference_text_metrics(text)

    assert metrics["letter_count"] == 2
    assert metrics["digit_count"] == 3
    assert metrics["punctuation_count"] == 1
    assert metrics["symbol_count"] == 2


def test_reference_calculator_counts_combining_marks_separately():

    text = "e\u0301"

    metrics = calculate_reference_text_metrics(text)

    assert metrics["character_count"] == 2
    assert metrics["letter_count"] == 1


def test_reference_calculator_counts_unicode_whitespace():

    text = "A B\tC\nD\u00a0E\u2003F"

    metrics = calculate_reference_text_metrics(text)

    assert metrics["whitespace_count"] == 5


def test_scenario_registry_contains_be02():

    family_ids = {
        family.family_id
        for family in INITIAL_SCENARIO_FAMILIES
    }

    assert "word_count" in family_ids
    assert "character_symbol_analysis" in family_ids


def test_reference_calculator_uses_unicode_database():

    text = "AéΩ١٢٣"

    metrics = calculate_reference_text_metrics(text)

    expected_letters = sum(
        unicodedata.category(character).startswith("L")
        for character in text
    )

    assert metrics["letter_count"] == expected_letters