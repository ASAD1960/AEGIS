import random

import pytest

from app.benchmark.scenario_families import (
    INITIAL_SCENARIO_FAMILIES,
    SENTENCE_ANALYSIS_LENGTHS,
    build_sentence_boundary_case,
    calculate_reference_sentence_count,
)
from app.tools.text_tool import TextAnalysisTool


@pytest.fixture
def text_tool():
    return TextAnalysisTool()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("First. Second!", 2),
        ("Really? Yes.", 2),
        ("Wait... what?!", 2),
        ("First... Second!!", 2),
        ("...", 0),
        ("One sentence", 1),
        ("First.\nSecond?", 2),
    ],
)
def test_reference_sentence_count_edge_cases(text, expected):
    assert calculate_reference_sentence_count(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("First. Second!", 2),
        ("Really? Yes.", 2),
        ("Wait... what?!", 2),
        ("First... Second!!", 2),
        ("...", 0),
        ("One sentence", 1),
        ("First.\nSecond?", 2),
    ],
)
def test_text_tool_sentence_count_edge_cases(text_tool, text, expected):
    assert text_tool.analyze(text)["sentence_count"] == expected


@pytest.mark.parametrize("difficulty", list(SENTENCE_ANALYSIS_LENGTHS))
def test_generated_cases_match_reference_and_text_tool(text_tool, difficulty):
    for index in range(10):
        rng = random.Random(42 + index)

        case = build_sentence_boundary_case(
            variant_index=index + 1,
            difficulty=difficulty,
            rng=rng,
        )

        text = case["context"]["text"]
        expected = case["expected_outcome"]["sentence_count"]

        assert expected == calculate_reference_sentence_count(text)
        assert expected == text_tool.analyze(text)["sentence_count"]


def test_sentence_boundary_generator_is_reproducible():
    first = build_sentence_boundary_case(
        variant_index=1,
        difficulty="advanced",
        rng=random.Random(42),
    )

    second = build_sentence_boundary_case(
        variant_index=1,
        difficulty="advanced",
        rng=random.Random(42),
    )

    assert first == second


def test_sentence_boundary_family_is_registered():
    family_ids = {
        family.family_id
        for family in INITIAL_SCENARIO_FAMILIES
    }

    assert "sentence_boundary_analysis" in family_ids


def test_reference_rejects_non_string_input():
    with pytest.raises(TypeError):
        calculate_reference_sentence_count(123)