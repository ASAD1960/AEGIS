"""
AEGIS synthetic research scenario families.

Scenario builders create task-specific records for the dataset generator.
All generated scenarios are synthetic and remain unapproved drafts.
"""

from __future__ import annotations

import random

from app.benchmark.dataset_generator import ScenarioFamily


# ---------------------------------------------------------------------------
# Basic execution: word counting
# ---------------------------------------------------------------------------

WORD_BANK = (
    "agent", "system", "memory", "planning", "execution",
    "feedback", "strategy", "recovery", "research", "dataset",
    "benchmark", "reliability", "decision", "verification",
    "operation", "context", "retrieval", "analysis", "process",
    "performance", "evaluation", "intelligence", "information",
    "accuracy", "quality", "result", "evidence", "learning",
    "workflow", "reasoning", "task", "tool", "response",
    "experiment", "observation", "outcome", "method", "record",
    "validation", "measurement", "adaptation", "structure",
    "capability", "consistency", "efficiency", "computation",
    "automation", "knowledge", "assessment", "improvement",
)


WORD_COUNT_LENGTHS = {
    "basic": (8, 15),
    "intermediate": (20, 35),
    "advanced": (40, 70),
}


def build_word_count_case(
    variant_index: int,
    difficulty: str,
    rng: random.Random,
) -> dict:
    """
    Generate a word-counting task with an exact expected answer.

    Difficulty is controlled by the length of the supplied text.
    """

    if difficulty not in WORD_COUNT_LENGTHS:
        raise ValueError(f"Unsupported difficulty: {difficulty}")

    minimum, maximum = WORD_COUNT_LENGTHS[difficulty]

    word_count = rng.randint(minimum, maximum)

    words = [
        rng.choice(WORD_BANK)
        for _ in range(word_count)
    ]

    text = " ".join(words)

    return {
        "task": (
            "Count the words in the supplied text. "
            "Treat each whitespace-separated token as one word. "
            "Return the result as an integer in the word_count field."
        ),
        "context": {
            "text": text,
            "counting_rule": (
                "A word is one non-empty token separated by whitespace."
            ),
        },
        "expected_outcome": {
            "word_count": len(text.split()),
        },
        "success_criteria": [
            "The output contains a word_count field.",
            "The word_count value is an integer.",
            f"The word_count value equals {word_count}.",
            "The supplied text is counted using whitespace-separated tokens.",
        ],
        "allowed_tools": [
            "text_tool",
        ],
    }


# ---------------------------------------------------------------------------
# Initial scenario-family registry
# ---------------------------------------------------------------------------

INITIAL_SCENARIO_FAMILIES = (
    ScenarioFamily(
        category="basic_execution",
        family_id="word_count",
        description=(
            "Evaluate accurate word counting across different input lengths."
        ),
        builder=build_word_count_case,
    ),
)