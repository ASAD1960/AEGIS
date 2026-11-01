
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
# ============================================================
# RESEARCH DATASET INTEGRATION TESTS
# ============================================================

def _make_research_record(
    case_id="basic_execution_test_case_0001",
    validation_status="approved",
):
    return {
        "case_id": case_id,
        "category": "basic_execution",
        "difficulty": "basic",
        "task": "Count the sentences in the supplied text.",
        "context": {
            "text": "First sentence. Second sentence? Third sentence!"
        },
        "expected_outcome": {
            "sentence_count": 3
        },
        "success_criteria": [
            "The sentence_count value is correct."
        ],
        "allowed_tools": ["text_tool"],
        "source": "Original synthetic test record.",
        "license": "Original synthetic; no third-party source material.",
        "group_id": "basic_execution_test_group_0001",
        "validation_status": validation_status,
    }


def _write_research_dataset(
    directory,
    records,
    manifest_status="development",
):
    import json

    dataset_path = directory / "research_dataset.jsonl"
    manifest_path = directory / "manifest.json"

    with dataset_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record) + "\n")

    manifest = {
        "dataset_name": "AEGIS Research Test Dataset",
        "dataset_id": "aegis-test-dataset",
        "dataset_version": "0.1.0",
        "schema_version": "0.1.0",
        "status": manifest_status,
        "categories": [
            "basic_execution",
            "multi_step_planning",
            "memory_retrieval",
            "tool_selection",
            "failure_recovery",
            "feedback_adaptation",
        ],
    }

    manifest_path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    return dataset_path, manifest_path


def test_research_runner_rejects_draft_records_by_default(tmp_path):

    from app.benchmark.runner import (
        BenchmarkRunner,
        ResearchBenchmarkError,
    )

    dataset_path, manifest_path = _write_research_dataset(
        tmp_path,
        [_make_research_record(validation_status="draft")],
    )

    runner = BenchmarkRunner()

    with pytest.raises(ResearchBenchmarkError):
        runner.run_research_dataset_benchmark(
            dataset_path=dataset_path,
            manifest_path=manifest_path,
            trials=1,
            warmup_trials=0,
        )


def test_research_runner_can_execute_draft_pilot_explicitly(tmp_path):

    from app.benchmark.runner import BenchmarkRunner

    dataset_path, manifest_path = _write_research_dataset(
        tmp_path,
        [_make_research_record(validation_status="draft")],
    )

    runner = BenchmarkRunner()

    result = runner.run_research_dataset_benchmark(
        dataset_path=dataset_path,
        manifest_path=manifest_path,
        trials=1,
        warmup_trials=0,
        seed=42,
        allow_non_approved=True,
    )

    assert result["dataset_id"] == "aegis-test-dataset"
    assert result["dataset_version"] == "0.1.0"
    assert result["manifest_status"] == "development"
    assert result["total_cases"] == 1
    assert result["validation_status_counts"] == {"draft": 1}

    case_result = result["cases"][0]

    assert case_result["case_id"] == (
        "basic_execution_test_case_0001"
    )
    assert case_result["validation_status"] == "draft"

    for strategy_data in case_result["benchmark"]["results"].values():
        assert strategy_data["correct_runs"] == 1
        assert strategy_data["incorrect_runs"] == 0


def test_research_runner_evaluates_partial_sentence_metrics(tmp_path):

    from app.benchmark.runner import BenchmarkRunner

    dataset_path, manifest_path = _write_research_dataset(
        tmp_path,
        [_make_research_record()],
    )

    runner = BenchmarkRunner()

    result = runner.run_research_dataset_benchmark(
        dataset_path=dataset_path,
        manifest_path=manifest_path,
        trials=2,
        warmup_trials=0,
        seed=42,
    )

    case_result = result["cases"][0]

    assert case_result["expected"] == {"sentence_count": 3}

    for strategy_data in case_result["benchmark"]["results"].values():
        assert strategy_data["successful_runs"] == 2
        assert strategy_data["correct_runs"] == 2
        assert strategy_data["incorrect_runs"] == 0
        assert strategy_data["evaluation_failed_runs"] == 0


def test_research_runner_rejects_invalid_dataset(tmp_path):

    from app.benchmark.runner import (
        BenchmarkRunner,
        ResearchBenchmarkError,
    )

    dataset_path, manifest_path = _write_research_dataset(
        tmp_path,
        [_make_research_record()],
    )

    # Introduce malformed JSON into the dataset.
    dataset_path.write_text(
        '{"case_id": "broken", invalid json}\n',
        encoding="utf-8",
    )

    runner = BenchmarkRunner()

    with pytest.raises(ResearchBenchmarkError):
        runner.run_research_dataset_benchmark(
            dataset_path=dataset_path,
            manifest_path=manifest_path,
            trials=1,
            warmup_trials=0,
        )


def test_research_runner_preserves_dataset_records_and_manifest(
    tmp_path,
):

    dataset_path, manifest_path = _write_research_dataset(
        tmp_path,
        [_make_research_record()],
    )

    original_dataset = dataset_path.read_bytes()
    original_manifest = manifest_path.read_bytes()

    from app.benchmark.runner import BenchmarkRunner

    runner = BenchmarkRunner()

    runner.run_research_dataset_benchmark(
        dataset_path=dataset_path,
        manifest_path=manifest_path,
        trials=1,
        warmup_trials=0,
    )

    assert dataset_path.read_bytes() == original_dataset
    assert manifest_path.read_bytes() == original_manifest
