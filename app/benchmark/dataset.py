
"""
AEGIS Benchmark Dataset

Versioned benchmark cases with predefined expected outputs.

Expected values are specified explicitly rather than
calculated using the production text-analysis tool.
"""

BENCHMARK_DATASET_VERSION = "1.0.0"


BENCHMARK_CASES = (
    {
        "case_id": "basic_001",
        "category": "basic_text",
        "text": "AEGIS learns from experience.",
        "expected": {
            "word_count": 4,
            "character_count": 29,
            "sentence_count": 1,
        },
    },
    {
        "case_id": "punctuation_001",
        "category": "punctuation",
        "text": "Hello! How are you? I am fine.",
        "expected": {
            "word_count": 7,
            "character_count": 30,
            "sentence_count": 3,
        },
    },
    {
        "case_id": "whitespace_001",
        "category": "whitespace",
        "text": "  alpha   beta\n gamma  ",
        "expected": {
            "word_count": 3,
            "character_count": 23,
            "sentence_count": 1,
        },
    },
    {
        "case_id": "multiple_sentences_001",
        "category": "multiple_sentences",
        "text": "First line. Second line follows.",
        "expected": {
            "word_count": 5,
            "character_count": 32,
            "sentence_count": 2,
        },
    },
    {
        "case_id": "repeated_punctuation_001",
        "category": "repeated_punctuation",
        "text": "Wait... Really?! Yes.",
        "expected": {
            "word_count": 3,
            "character_count": 21,
            "sentence_count": 3,
        },
    },
)
