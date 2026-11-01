
import pytest

from app.benchmark.runner import BenchmarkRunner


def test_runner_executes_all_strategies():

    runner = BenchmarkRunner()

    result = runner.run_benchmark(
        "AEGIS evaluates strategy performance.",
        trials=2,
    )

    assert result["total_strategies"] == 3
    assert result["trials_per_strategy"] == 2

    for strategy_id, data in result["results"].items():

        assert data["successful_runs"] == 2
        assert data["failed_runs"] == 0
        assert data["correct_runs"] == 2
        assert data["incorrect_runs"] == 0
        assert data["execution_accuracy"] == 100.0
        assert len(data["trial_results"]) == 2


def test_runner_records_individual_trial_results():

    runner = BenchmarkRunner()

    result = runner.run_benchmark(
        "Testing individual benchmark trials.",
        trials=3,
    )

    for data in result["results"].values():

        assert len(data["trial_results"]) == 3

        for trial in data["trial_results"]:

            assert trial["execution_success"] is True
            assert trial["correct"] is True
            assert trial["execution_time"] >= 0


def test_runner_rejects_empty_text():

    runner = BenchmarkRunner()

    with pytest.raises(ValueError):
        runner.run_benchmark("", trials=2)


@pytest.mark.parametrize(
    "invalid_trials",
    [0, -1, 1.5, True, "3", None],
)
def test_runner_rejects_invalid_trial_counts(invalid_trials):

    runner = BenchmarkRunner()

    with pytest.raises(ValueError):
        runner.run_benchmark(
            "Benchmark validation test.",
            trials=invalid_trials,
        )


def test_runner_records_execution_failures(monkeypatch):

    runner = BenchmarkRunner()

    def simulate_failure(text, strategy_id):
        raise RuntimeError("Simulated execution failure.")

    monkeypatch.setattr(
        runner.executor,
        "execute",
        simulate_failure,
    )

    result = runner.run_benchmark(
        "Failure handling test.",
        trials=2,
    )

    for data in result["results"].values():

        assert data["successful_runs"] == 0
        assert data["failed_runs"] == 2
        assert data["correct_runs"] == 0
        assert data["incorrect_runs"] == 0
        assert data["execution_accuracy"] == 0.0
        assert data["success"] is False
        assert len(data["trial_results"]) == 2

        for trial in data["trial_results"]:

            assert trial["execution_success"] is False
            assert trial["correct"] is False
            assert "Simulated execution failure" in trial["error"]

def test_runner_excludes_warmup_trials_from_measurements():

    runner = BenchmarkRunner()

    result = runner.run_benchmark(
        "Testing warm-up behaviour.",
        trials=2,
        warmup_trials=3,
        seed=42,
    )

    for data in result["results"].values():

        assert data["warmup_successful_runs"] == 3
        assert data["warmup_failed_runs"] == 0

        assert data["successful_runs"] == 2
        assert data["total_trials"] == 2
        assert len(data["trial_results"]) == 2


def test_runner_reproduces_execution_order_with_same_seed():

    first_runner = BenchmarkRunner()
    second_runner = BenchmarkRunner()

    first_result = first_runner.run_benchmark(
        "Testing reproducible ordering.",
        trials=10,
        warmup_trials=1,
        seed=12345,
    )

    second_result = second_runner.run_benchmark(
        "Testing reproducible ordering.",
        trials=10,
        warmup_trials=1,
        seed=12345,
    )

    assert (
        first_result["execution_order"]
        == second_result["execution_order"]
    )


def test_runner_excludes_evaluation_time_from_execution_time(
    monkeypatch,
):

    import app.benchmark.runner as runner_module

    runner = BenchmarkRunner()

    clock = {"value": 0}

    def fake_clock():

        clock["value"] += 100

        return clock["value"]

    monkeypatch.setattr(
        runner_module.time,
        "perf_counter_ns",
        fake_clock,
    )

    def slow_evaluation(case, execution_result):

        # Simulate substantial evaluation overhead.
        for _ in range(50):
            fake_clock()

        return {
            "correct": True,
        }

    monkeypatch.setattr(
        runner.evaluator,
        "evaluate_case",
        slow_evaluation,
    )

    result = runner.run_benchmark(
        "Testing timing isolation.",
        trials=2,
        warmup_trials=0,
        seed=42,
    )

    for data in result["results"].values():

        for trial in data["trial_results"]:

            # Execution itself advances the fake clock
            # by exactly 100 nanoseconds.
            assert trial["execution_time_ns"] == 100

def test_runner_separates_evaluation_failures_from_execution_failures(
    monkeypatch,
):

    runner = BenchmarkRunner()

    def failing_evaluation(case, execution_result):

        raise RuntimeError("Simulated evaluation failure.")

    monkeypatch.setattr(
        runner.evaluator,
        "evaluate_case",
        failing_evaluation,
    )

    result = runner.run_benchmark(
        "Testing evaluation failure handling.",
        trials=1,
        warmup_trials=0,
        seed=42,
    )

    for data in result["results"].values():

        assert data["successful_runs"] == 1
        assert data["failed_runs"] == 0

        assert data["evaluation_failed_runs"] == 1

        assert data["correct_runs"] == 0
        assert data["incorrect_runs"] == 1

        assert data["success"] is True

        trial = data["trial_results"][0]

        assert trial["execution_success"] is True
        assert trial["correct"] is False

        assert trial["evaluation"] is None

        assert (
            trial["evaluation_error"]
            == "Simulated evaluation failure."
        )

        assert trial["error"] is None

def test_runner_executes_versioned_dataset_against_all_strategies():

    from app.benchmark.dataset import (
        BENCHMARK_CASES,
        BENCHMARK_DATASET_VERSION,
    )

    runner = BenchmarkRunner()

    result = runner.run_dataset_benchmark(
        trials=2,
        warmup_trials=1,
        seed=42,
    )

    assert result["dataset_version"] == BENCHMARK_DATASET_VERSION

    assert result["total_cases"] == len(BENCHMARK_CASES)
    assert result["total_strategies"] == 3

    assert result["trials_per_strategy"] == 2
    assert result["warmup_trials_per_strategy"] == 1

    assert len(result["cases"]) == len(BENCHMARK_CASES)

    total_evaluations = 0

    for case_result, original_case in zip(
        result["cases"],
        BENCHMARK_CASES,
    ):

        assert case_result["case_id"] == original_case["case_id"]
        assert case_result["category"] == original_case["category"]

        strategy_results = case_result["benchmark"]["results"]

        assert set(strategy_results) == {
            "direct",
            "step_by_step",
            "careful",
        }

        for strategy_data in strategy_results.values():

            assert strategy_data["successful_runs"] == 2
            assert strategy_data["failed_runs"] == 0

            assert strategy_data["correct_runs"] == 2
            assert strategy_data["incorrect_runs"] == 0

            assert strategy_data["evaluation_failed_runs"] == 0

            assert strategy_data["warmup_successful_runs"] == 1

            assert len(strategy_data["trial_results"]) == 2

            total_evaluations += len(
                strategy_data["trial_results"]
            )

    assert total_evaluations == 30
