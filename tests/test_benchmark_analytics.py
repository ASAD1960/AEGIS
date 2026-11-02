
import json

import pytest

import app.benchmark.analytics as analytics_module
from app.benchmark.analytics import BenchmarkAnalytics


@pytest.fixture
def analytics():
    return BenchmarkAnalytics()


@pytest.fixture
def sample_experiment():
    return {
        "experiment_id": "aegis-exp-test-001",
        "experiment_name": "Analytics Test Experiment",
        "dataset_id": "aegis-test-dataset",
        "dataset_version": "1.0.0",
        "random_seed": 42,
        "status": "completed",
    }


@pytest.fixture
def sample_cases():
    return [
        {
            "case_id": "case-001",
            "category": "basic_execution",
            "difficulty": "basic",
        },
        {
            "case_id": "case-002",
            "category": "memory_retrieval",
            "difficulty": "intermediate",
        },
    ]


def make_trial(
    case_id,
    strategy_id,
    execution_success=True,
    is_correct=True,
    execution_time=0.1,
    is_warmup=False,
    execution_details=None,
    trial_number=1,
):
    return {
        "case_id": case_id,
        "strategy_id": strategy_id,
        "execution_success": int(execution_success),
        "is_correct": int(is_correct),
        "execution_time_seconds": execution_time,
        "is_warmup": int(is_warmup),
        "trial_number": trial_number,
        "execution_details_json": (
            json.dumps(execution_details)
            if execution_details is not None
            else None
        ),
    }


def install_sample_data(
    monkeypatch,
    experiment,
    cases,
    trials,
):
    monkeypatch.setattr(
        analytics_module,
        "get_research_experiment",
        lambda experiment_id: experiment,
    )

    monkeypatch.setattr(
        analytics_module,
        "get_research_case_results",
        lambda experiment_id: cases,
    )

    monkeypatch.setattr(
        analytics_module,
        "get_research_trial_results",
        lambda experiment_id: trials,
    )


def test_rejects_empty_experiment_id(analytics):

    with pytest.raises(ValueError, match="non-empty string"):
        analytics.generate_research_report("")


def test_rejects_unknown_experiment(
    analytics,
    monkeypatch,
):

    monkeypatch.setattr(
        analytics_module,
        "get_research_experiment",
        lambda experiment_id: None,
    )

    with pytest.raises(ValueError, match="not found"):
        analytics.generate_research_report(
            "unknown-experiment"
        )


def test_generates_empty_research_report(
    analytics,
    monkeypatch,
    sample_experiment,
):

    install_sample_data(
        monkeypatch,
        sample_experiment,
        [],
        [],
    )

    report = analytics.generate_research_report(
        sample_experiment["experiment_id"]
    )

    assert report["summary"] == {
        "total_cases": 0,
        "measured_trials": 0,
        "warmup_trials": 0,
        "strategy_count": 0,
    }

    assert report["strategy_performance"] == {}
    assert report["category_performance"] == {}
    assert report["difficulty_performance"] == {}


def test_excludes_warmup_trials_from_performance(
    analytics,
    monkeypatch,
    sample_experiment,
    sample_cases,
):

    trials = [
        make_trial(
            "case-001",
            "direct",
            execution_time=0.05,
            is_warmup=True,
        ),
        make_trial(
            "case-001",
            "direct",
            execution_time=0.10,
            trial_number=1,
        ),
        make_trial(
            "case-001",
            "direct",
            execution_time=0.20,
            trial_number=2,
        ),
    ]

    install_sample_data(
        monkeypatch,
        sample_experiment,
        sample_cases,
        trials,
    )

    report = analytics.generate_research_report(
        sample_experiment["experiment_id"]
    )

    assert report["summary"]["warmup_trials"] == 1
    assert report["summary"]["measured_trials"] == 2

    performance = report["strategy_performance"]["direct"]

    assert performance["total_trials"] == 2
    assert performance["successful_trials"] == 2
    assert performance["correct_trials"] == 2
    assert performance["average_execution_time_seconds"] == 0.15
    assert performance["median_execution_time_seconds"] == 0.15
    assert performance["p95_execution_time_seconds"] == 0.20


def test_calculates_strategy_success_and_correctness(
    analytics,
    monkeypatch,
    sample_experiment,
    sample_cases,
):

    trials = [
        make_trial(
            "case-001",
            "direct",
            execution_success=True,
            is_correct=True,
            execution_time=0.10,
        ),
        make_trial(
            "case-002",
            "direct",
            execution_success=False,
            is_correct=False,
            execution_time=0.20,
        ),
        make_trial(
            "case-001",
            "step_by_step",
            execution_success=True,
            is_correct=False,
            execution_time=0.30,
        ),
        make_trial(
            "case-002",
            "step_by_step",
            execution_success=True,
            is_correct=True,
            execution_time=0.40,
        ),
    ]

    install_sample_data(
        monkeypatch,
        sample_experiment,
        sample_cases,
        trials,
    )

    report = analytics.generate_research_report(
        sample_experiment["experiment_id"]
    )

    direct = report["strategy_performance"]["direct"]
    step_by_step = report["strategy_performance"]["step_by_step"]

    assert direct["success_rate"] == 50.0
    assert direct["correctness_rate"] == 50.0

    assert step_by_step["success_rate"] == 100.0
    assert step_by_step["correctness_rate"] == 50.0


def test_summarizes_instrumentation(
    analytics,
    monkeypatch,
    sample_experiment,
    sample_cases,
):

    direct_details = {
        "one_pass_analysis_calls": 1,
        "individual_metric_calls": 0,
        "analysis_and_metric_method_calls": 1,
        "verification_operations": 0,
        "input_validation_calls": 1,
        "execution_step_count": 1,
        "verification_passed": None,
    }

    careful_details = {
        "one_pass_analysis_calls": 1,
        "individual_metric_calls": 8,
        "analysis_and_metric_method_calls": 9,
        "verification_operations": 8,
        "input_validation_calls": 10,
        "execution_step_count": 4,
        "verification_passed": True,
    }

    trials = [
        make_trial(
            "case-001",
            "direct",
            execution_details=direct_details,
        ),
        make_trial(
            "case-002",
            "careful",
            execution_details=careful_details,
        ),
    ]

    install_sample_data(
        monkeypatch,
        sample_experiment,
        sample_cases,
        trials,
    )

    report = analytics.generate_research_report(
        sample_experiment["experiment_id"]
    )

    direct = report["strategy_performance"]["direct"]["instrumentation"]
    careful = report["strategy_performance"]["careful"]["instrumentation"]

    assert direct["trials_with_instrumentation"] == 1
    assert direct["total_operations"]["one_pass_analysis_calls"] == 1
    assert direct["verification_not_applicable"] == 1
    assert direct["verification_pass_rate"] is None

    assert careful["trials_with_instrumentation"] == 1
    assert careful["total_operations"]["individual_metric_calls"] == 8
    assert careful["total_operations"]["verification_operations"] == 8
    assert careful["verification_passed"] == 1
    assert careful["verification_failed"] == 0
    assert careful["verification_pass_rate"] == 100.0


def test_handles_missing_and_invalid_instrumentation(
    analytics,
    monkeypatch,
    sample_experiment,
    sample_cases,
):

    trials = [
        make_trial(
            "case-001",
            "direct",
            execution_details={
                "one_pass_analysis_calls": 1,
                "verification_passed": None,
            },
        ),
        make_trial(
            "case-002",
            "direct",
            execution_details=None,
        ),
    ]

    trials[1]["execution_details_json"] = "{invalid-json"

    install_sample_data(
        monkeypatch,
        sample_experiment,
        sample_cases,
        trials,
    )

    report = analytics.generate_research_report(
        sample_experiment["experiment_id"]
    )

    instrumentation = (
        report["strategy_performance"]["direct"]["instrumentation"]
    )

    assert instrumentation["trials_with_instrumentation"] == 1
    assert instrumentation["trials_missing_instrumentation"] == 1
    assert instrumentation["total_operations"]["one_pass_analysis_calls"] == 1


def test_builds_category_and_difficulty_breakdowns(
    analytics,
    monkeypatch,
    sample_experiment,
    sample_cases,
):

    trials = [
        make_trial("case-001", "direct"),
        make_trial("case-001", "step_by_step"),
        make_trial("case-002", "direct"),
    ]

    install_sample_data(
        monkeypatch,
        sample_experiment,
        sample_cases,
        trials,
    )

    report = analytics.generate_research_report(
        sample_experiment["experiment_id"]
    )

    assert "basic_execution" in report["category_performance"]
    assert "memory_retrieval" in report["category_performance"]

    assert "basic" in report["difficulty_performance"]
    assert "intermediate" in report["difficulty_performance"]

    assert (
        report["category_performance"]["basic_execution"]["direct"]["total_trials"]
        == 1
    )

    assert (
        report["difficulty_performance"]["intermediate"]["direct"]["total_trials"]
        == 1
    )

def test_calculates_instrumentation_averages_using_available_values(
    analytics,
):

    trials = [
        {
            "execution_details_json": json.dumps({
                "one_pass_analysis_calls": 2,
                "individual_metric_calls": 4,
            })
        },
        {
            "execution_details_json": json.dumps({
                "one_pass_analysis_calls": 4,
            })
        },
    ]

    result = analytics._summarize_instrumentation(trials)

    averages = result[
        "average_operations_per_instrumented_trial"
    ]

    assert averages["one_pass_analysis_calls"] == 3.0
    assert averages["individual_metric_calls"] == 4.0
    assert averages["verification_operations"] is None

    assert result["total_operations"]["one_pass_analysis_calls"] == 6
    assert result["total_operations"]["individual_metric_calls"] == 4
