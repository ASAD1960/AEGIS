
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


def test_direct_strategy_produces_correct_result(
    evaluator,
    benchmark_case,
):

    result = TaskExecutor().execute(
        benchmark_case["text"],
        "direct",
    )

    evaluation = evaluator.evaluate_case(
        benchmark_case,
        result,
    )

    assert evaluation["correct"] is True
    assert evaluation["case_id"] == "basic_001"


def test_step_by_step_strategy_produces_correct_result(
    evaluator,
    benchmark_case,
):

    result = TaskExecutor().execute(
        benchmark_case["text"],
        "step_by_step",
    )

    evaluation = evaluator.evaluate_case(
        benchmark_case,
        result,
    )

    assert evaluation["correct"] is True


def test_careful_strategy_produces_correct_result(
    evaluator,
    benchmark_case,
):

    result = TaskExecutor().execute(
        benchmark_case["text"],
        "careful",
    )

    evaluation = evaluator.evaluate_case(
        benchmark_case,
        result,
    )

    assert evaluation["correct"] is True


def test_evaluator_detects_incorrect_result(
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
