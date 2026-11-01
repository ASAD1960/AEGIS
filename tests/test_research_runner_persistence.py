import json

from app.benchmark.runner import BenchmarkRunner
from app.memory.database import (
    get_research_experiment,
    get_research_case_results,
    get_research_trial_results,
)


def make_record():
    return {
        "case_id": "persistence_test_case_0001",
        "category": "basic_execution",
        "difficulty": "basic",
        "task": "Count sentences.",
        "context": {
            "text": "First sentence. Second sentence? Third sentence!"
        },
        "expected_outcome": {
            "sentence_count": 3
        },
        "success_criteria": [
            "The sentence count is correct."
        ],
        "allowed_tools": ["text_tool"],
        "source": "Original synthetic test record.",
        "license": "Original synthetic; no third-party source material.",
        "group_id": "persistence_test_group_0001",
        "validation_status": "approved",
    }


def write_dataset(directory):
    dataset_path = directory / "research_dataset.jsonl"
    manifest_path = directory / "manifest.json"

    dataset_path.write_text(
        json.dumps(make_record()) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "dataset_name": "AEGIS Persistence Test Dataset",
        "dataset_id": "aegis-persistence-test",
        "dataset_version": "0.1.0",
        "schema_version": "0.1.0",
        "status": "development",
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


def run_test_benchmark(directory, trials=2, warmup_trials=1):
    dataset_path, manifest_path = write_dataset(directory)

    runner = BenchmarkRunner()

    return runner.run_research_dataset_benchmark(
        dataset_path=dataset_path,
        manifest_path=manifest_path,
        trials=trials,
        warmup_trials=warmup_trials,
        seed=42,
    )


def test_research_runner_persists_completed_experiment(tmp_path):

    result = run_test_benchmark(tmp_path)

    experiment_id = result["experiment_id"]

    experiment = get_research_experiment(experiment_id)

    assert experiment is not None
    assert experiment["experiment_id"] == experiment_id
    assert experiment["dataset_id"] == "aegis-persistence-test"
    assert experiment["status"] == "completed"
    assert experiment["total_cases"] == 1

    assert len(experiment["dataset_sha256"]) == 64
    assert len(experiment["manifest_sha256"]) == 64

    assert experiment["completed_at"] is not None


def test_research_runner_persists_cases_and_measured_trials(tmp_path):

    result = run_test_benchmark(
        tmp_path,
        trials=2,
        warmup_trials=1,
    )

    experiment_id = result["experiment_id"]

    cases = get_research_case_results(experiment_id)
    trials = get_research_trial_results(experiment_id)

    assert len(cases) == 1

    assert cases[0]["case_id"] == (
        "persistence_test_case_0001"
    )

    assert cases[0]["case_status"] == "completed"

    # Three strategies, two measured trials each.
    assert len(trials) == 6

    assert all(
        trial["is_warmup"] == 0
        for trial in trials
    )

    assert all(
        trial["execution_success"] == 1
        for trial in trials
    )

    assert all(
        trial["is_correct"] == 1
        for trial in trials
    )


def test_research_runner_preserves_warmup_summary(tmp_path):

    result = run_test_benchmark(
        tmp_path,
        trials=1,
        warmup_trials=2,
    )

    experiment = get_research_experiment(
        result["experiment_id"]
    )

    configuration = json.loads(
        experiment["configuration_json"]
    )

    assert configuration["warmup_trials_per_strategy"] == 2

    assert configuration["random_seed"] == 42