
import pytest

from app.benchmark.dataset import BENCHMARK_CASES
from app.benchmark.evaluator import BenchmarkEvaluator
from app.agent.executor import TaskExecutor


@pytest.fixture
def evaluator():
    return BenchmarkEvaluator()


@pytest.fixture
def benchmark_case():
    return BENCHMARK_CASES[0]


@pytest.fixture
def unicode_case():
    return {
        "case_id": "be02_unicode_001",
        "text": "Aé 12! $ 🚀",
        "expected": {
            "word_count": 4,
            "character_count": 10,
            "sentence_count": 2,
            "letter_count": 2,
            "digit_count": 2,
            "whitespace_count": 3,
            "punctuation_count": 1,
            "symbol_count": 2,
        },
    }


@pytest.mark.parametrize(
    "strategy_id",
    ["direct", "step_by_step", "careful"],
)
def test_original_benchmark_works_with_all_strategies(
    evaluator,
    benchmark_case,
    strategy_id,
):

    result = TaskExecutor().execute(
        benchmark_case["text"],
        strategy_id,
    )

    evaluation = evaluator.evaluate_case(
        benchmark_case,
        result,
    )

    assert evaluation["correct"] is True


@pytest.mark.parametrize(
    "strategy_id",
    ["direct", "step_by_step", "careful"],
)
def test_all_unicode_metrics_are_evaluated(
    evaluator,
    unicode_case,
    strategy_id,
):

    result = TaskExecutor().execute(
        unicode_case["text"],
        strategy_id,
    )

    evaluation = evaluator.evaluate_case(
        unicode_case,
        result,
    )

    assert evaluation["correct"] is True
    assert evaluation["expected"] == evaluation["actual"]
    assert len(evaluation["actual"]) == 8


def test_evaluator_detects_incorrect_original_metric(
    evaluator,
    benchmark_case,
):

    result = {
        "results": {
            "analyze_text": {
                "word_count": 100,
                "character_count": 200,
                "sentence_count": 10,
            }
        }
    }

    evaluation = evaluator.evaluate_case(
        benchmark_case,
        result,
    )

    assert evaluation["correct"] is False
    assert evaluation["reason"] == (
        "One or more metrics did not match."
    )


def test_evaluator_detects_incorrect_unicode_metric(
    evaluator,
    unicode_case,
):

    result = TaskExecutor().execute(
        unicode_case["text"],
        "direct",
    )

    result["results"]["analyze_text"]["symbol_count"] = 99

    evaluation = evaluator.evaluate_case(
        unicode_case,
        result,
    )

    assert evaluation["correct"] is False
    assert evaluation["actual"]["symbol_count"] == 99


def test_evaluator_detects_missing_unicode_metric(
    evaluator,
    unicode_case,
):

    result = TaskExecutor().execute(
        unicode_case["text"],
        "direct",
    )

    del result["results"]["analyze_text"]["symbol_count"]

    evaluation = evaluator.evaluate_case(
        unicode_case,
        result,
    )

    assert evaluation["correct"] is False
    assert evaluation["actual"]["symbol_count"] is None


def test_evaluator_handles_execution_failure(
    evaluator,
    benchmark_case,
):

    result = {
        "error": "Simulated execution failure."
    }

    evaluation = evaluator.evaluate_case(
        benchmark_case,
        result,
    )

    assert evaluation["correct"] is False
    assert "Execution failed" in evaluation["reason"]


def test_evaluator_handles_missing_results(
    evaluator,
    benchmark_case,
):

    evaluation = evaluator.evaluate_case(
        benchmark_case,
        {},
    )

    assert evaluation["correct"] is False
    assert evaluation["actual"] is None


def test_evaluator_rejects_invalid_benchmark_case(
    evaluator,
):

    with pytest.raises(ValueError):
        evaluator.evaluate_case(
            {"text": "Invalid case"},
            {"results": {}},
        )


def test_evaluator_rejects_missing_expected_metrics(
    evaluator,
):

    invalid_case = {
        "case_id": "invalid_001",
        "expected": {
            "word_count": 4,
        },
    }

    with pytest.raises(ValueError):
        evaluator.evaluate_case(
            invalid_case,
            {"results": {}},
        )


def test_evaluator_rejects_unsupported_metric(
    evaluator,
):

    invalid_case = {
        "case_id": "invalid_002",
        "expected": {
            "word_count": 4,
            "character_count": 10,
            "sentence_count": 2,
            "unknown_metric": 5,
        },
    }

    with pytest.raises(
        ValueError,
        match="Unsupported benchmark metrics",
    ):
        evaluator.evaluate_case(
            invalid_case,
            {"results": {}},
        )
