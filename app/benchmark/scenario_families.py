"""
AEGIS synthetic research scenario families.

Scenario builders create task-specific records for the dataset generator.
All generated scenarios are synthetic and remain unapproved drafts.

Expected outcomes are calculated independently from the AEGIS tools
to reduce the risk of circular benchmark evaluation.
"""

from __future__ import annotations

import random
import unicodedata

from app.benchmark.dataset_generator import ScenarioFamily


# ===========================================================================
# BE-01: Basic execution — word counting
# ===========================================================================

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


# ===========================================================================
# BE-02: Basic execution — character and symbol analysis
# ===========================================================================

CHARACTER_ANALYSIS_LENGTHS = {
    "basic": (9, 15),
    "intermediate": (20, 35),
    "advanced": (40, 70),
}


# Every generated case includes examples of the main Unicode categories.
# Additional tokens introduce variation across generated cases.
UNICODE_REQUIRED_TOKENS = (
    "AEGIS",       # Latin letters
    "café",        # Accented Latin letters
    "١٢٣",         # Arabic-Indic decimal digits
    "!",           # Punctuation
    ".",           # Sentence-ending punctuation
    "$",           # Currency symbol
    "€",           # Currency symbol
    "🚀",          # Emoji symbol
    "e\u0301",     # Letter plus combining acute accent
)


UNICODE_ADDITIONAL_TOKENS = (
    "Ωmega",
    "مرحبا",
    "नमस्ते",
    "１２３",       # Full-width decimal digits
    "٣٤٥",
    "؟",
    "¿",
    "©",
    "→",
    "👩‍💻",        # Emoji sequence containing a joiner
    "👍🏽",         # Emoji with skin-tone modifier
    "漢字",
    "добро",
    "ø",
    "ñ",
)


UNICODE_WHITESPACE = (
    " ",
    "\t",
    "\n",
    "\u00a0",      # Non-breaking space
    "\u2003",      # Em space
)


def calculate_reference_text_metrics(text: str) -> dict:
    """
    Calculate benchmark expectations independently.

    This function deliberately does not call TextAnalysisTool.
    It uses Python's standard Unicode database and explicit
    benchmark counting conventions.
    """

    sentences = [
        sentence
        for sentence in (
            text.replace("!", ".")
            .replace("?", ".")
            .split(".")
        )
        if sentence.strip()
    ]

    metrics = {
        "word_count": len(text.split()),
        "character_count": len(text),
        "sentence_count": len(sentences),
        "letter_count": 0,
        "digit_count": 0,
        "whitespace_count": 0,
        "punctuation_count": 0,
        "symbol_count": 0,
    }

    for character in text:

        category = unicodedata.category(character)

        if category.startswith("L"):
            metrics["letter_count"] += 1

        if category == "Nd":
            metrics["digit_count"] += 1

        if character.isspace():
            metrics["whitespace_count"] += 1

        if category.startswith("P"):
            metrics["punctuation_count"] += 1

        if category.startswith("S"):
            metrics["symbol_count"] += 1

    return metrics


def build_character_symbol_case(
    variant_index: int,
    difficulty: str,
    rng: random.Random,
) -> dict:
    """
    Generate a Unicode character and symbol analysis task.

    Difficulty is controlled by the number of whitespace-separated
    tokens. Each case includes representative Unicode categories.
    """

    if difficulty not in CHARACTER_ANALYSIS_LENGTHS:
        raise ValueError(f"Unsupported difficulty: {difficulty}")

    minimum, maximum = CHARACTER_ANALYSIS_LENGTHS[difficulty]

    token_count = rng.randint(minimum, maximum)

    tokens = list(UNICODE_REQUIRED_TOKENS)

    additional_count = token_count - len(tokens)

    additional_tokens = [
        rng.choice(UNICODE_ADDITIONAL_TOKENS)
        for _ in range(additional_count)
    ]

    tokens.extend(additional_tokens)

    rng.shuffle(tokens)

    separators = [
        rng.choice(UNICODE_WHITESPACE)
        for _ in range(len(tokens) - 1)
    ]

    text_parts = []

    for index, token in enumerate(tokens):

        text_parts.append(token)

        if index < len(separators):
            text_parts.append(separators[index])

    text = "".join(text_parts)

    expected_metrics = calculate_reference_text_metrics(text)

    return {
        "task": (
            "Analyze the supplied text and calculate all eight metrics: "
            "word_count, character_count, sentence_count, letter_count, "
            "digit_count, whitespace_count, punctuation_count, and "
            "symbol_count. Follow the counting conventions supplied "
            "in the context. Return each metric as an integer."
        ),
        "context": {
            "text": text,
            "counting_conventions": {
                "word_count": (
                    "Count non-empty tokens separated by whitespace."
                ),
                "character_count": (
                    "Count Unicode code points, including whitespace."
                ),
                "sentence_count": (
                    "Replace exclamation and question marks with periods, "
                    "split on periods, and count non-empty segments."
                ),
                "letter_count": (
                    "Count Unicode characters whose category begins with L."
                ),
                "digit_count": (
                    "Count Unicode decimal digits in category Nd."
                ),
                "whitespace_count": (
                    "Count characters for which isspace() is true."
                ),
                "punctuation_count": (
                    "Count Unicode characters whose category begins with P."
                ),
                "symbol_count": (
                    "Count Unicode characters whose category begins with S."
                ),
            },
        },
        "expected_outcome": expected_metrics,
        "success_criteria": [
            "The output contains all eight required metric fields.",
            "Every metric value is an integer.",
            "All eight values match the independently calculated reference.",
            "Unicode letters are classified correctly.",
            "Unicode decimal digits are classified correctly.",
            "Whitespace characters are counted correctly.",
            "Punctuation and symbols are distinguished correctly.",
            "Unicode code points are counted using the specified convention.",
        ],
        "allowed_tools": [
            "text_tool",
        ],
    }


# ===========================================================================
# BE-03: Basic execution — sentence boundary analysis
# ===========================================================================

SENTENCE_ANALYSIS_LENGTHS = {
    "basic": (2, 4),
    "intermediate": (5, 8),
    "advanced": (9, 14),
}


def calculate_reference_sentence_count(text: str) -> int:
    """
    Calculate sentence count using the documented AEGIS convention.

    Rules:
    1. Replace exclamation marks with periods.
    2. Replace question marks with periods.
    3. Split the text on periods.
    4. Count non-empty segments after stripping whitespace.

    This function is independent of TextAnalysisTool.
    """

    if not isinstance(text, str):
        raise TypeError("Input must be a string.")

    sentences = [
        segment
        for segment in (
            text.replace("!", ".")
            .replace("?", ".")
            .split(".")
        )
        if segment.strip()
    ]

    return len(sentences)


def build_sentence_boundary_case(
    variant_index: int,
    difficulty: str,
    rng: random.Random,
) -> dict:
    """
    Generate a sentence-boundary analysis task.

    Difficulty is controlled by the number of sentence segments.
    Different punctuation patterns introduce variation.
    """

    if difficulty not in SENTENCE_ANALYSIS_LENGTHS:
        raise ValueError(f"Unsupported difficulty: {difficulty}")

    minimum, maximum = SENTENCE_ANALYSIS_LENGTHS[difficulty]

    sentence_count = rng.randint(minimum, maximum)

    sentence_templates = (
        "The agent completed task {number}.",
        "The system retrieved memory {number}!",
        "Can the agent verify result {number}?",
        "The strategy selected operation {number}.",
        "The workflow recorded outcome {number}...",
        "The executor checked state {number}!!",
        "Did recovery succeed for task {number}?!",
        "The benchmark measured performance {number}.",
    )

    segments = []

    for index in range(sentence_count):
        template = rng.choice(sentence_templates)
        segments.append(template.format(number=index + 1))

    text = " ".join(segments)

    expected_count = calculate_reference_sentence_count(text)

    return {
        "task": (
            "Count the sentences in the supplied text. "
            "Follow the sentence-counting convention in the context. "
            "Return the result as an integer in the sentence_count field."
        ),
        "context": {
            "text": text,
            "counting_rule": (
                "Replace exclamation marks and question marks with periods, "
                "split the text on periods, and count non-empty segments "
                "after stripping whitespace."
            ),
        },
        "expected_outcome": {
            "sentence_count": expected_count,
        },
        "success_criteria": [
            "The output contains a sentence_count field.",
            "The sentence_count value is an integer.",
            "The sentence_count matches the independent reference.",
            "Exclamation marks are treated as sentence separators.",
            "Question marks are treated as sentence separators.",
            "Repeated punctuation follows the documented splitting rule.",
            "Empty segments are not counted.",
        ],
        "allowed_tools": [
            "text_tool",
        ],
    }


# ===========================================================================
# Initial scenario-family registry
# ===========================================================================

INITIAL_SCENARIO_FAMILIES = (
    ScenarioFamily(
        category="basic_execution",
        family_id="word_count",
        description=(
            "Evaluate accurate word counting across different input lengths."
        ),
        builder=build_word_count_case,
    ),

    ScenarioFamily(
        category="basic_execution",
        family_id="character_symbol_analysis",
        description=(
            "Evaluate Unicode-aware character, digit, whitespace, "
            "punctuation, and symbol analysis."
        ),
        builder=build_character_symbol_case,
    ),

    ScenarioFamily(
        category="basic_execution",
        family_id="sentence_boundary_analysis",
        description=(
            "Evaluate sentence counting using explicit punctuation-based "
            "boundary rules, including repeated punctuation."
        ),
        builder=build_sentence_boundary_case,
    ),
)