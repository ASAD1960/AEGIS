
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


def test_aggregates_repeated_trials_by_case_and_strategy(analytics):

    trials = [
        make_trial(
            "case-001", "direct",
            execution_success=True,
            is_correct=True,
            execution_time=0.1,
        ),
        make_trial(
            "case-001", "direct",
            execution_success=False,
            is_correct=False,
            execution_time=0.9,
            trial_number=2,
        ),
        make_trial(
            "case-001", "direct",
            execution_success=True,
            is_correct=False,
            execution_time=0.3,
            trial_number=3,
        ),
        make_trial(
            "case-001", "direct",
            execution_success=True,
            is_correct=True,
            execution_time=0.01,
            is_warmup=True,
            trial_number=4,
        ),
        make_trial(
            "case-001", "careful",
            execution_success=True,
            is_correct=True,
            execution_time=0.2,
        ),
    ]

    result = analytics._aggregate_case_strategy_results(trials)

    direct = result["direct"]["case-001"]
    careful = result["careful"]["case-001"]

    assert direct["trial_count"] == 3
    assert direct["success_rate"] == pytest.approx(2 / 3)
    assert direct["correctness_rate"] == pytest.approx(1 / 3)
    assert direct["median_execution_time"] == pytest.approx(0.2)
    assert direct["timed_successful_trials"] == 2

    assert careful["trial_count"] == 1
    assert careful["success_rate"] == 1.0
    assert careful["correctness_rate"] == 1.0
    assert careful["median_execution_time"] == pytest.approx(0.2)


def test_builds_paired_differences_for_matching_cases(analytics):

    aggregated = {
        "direct": {
            "case-001": {
                "success_rate": 1.0,
                "correctness_rate": 0.8,
                "median_execution_time": 0.2,
            },
            "case-002": {
                "success_rate": 0.5,
                "correctness_rate": 0.6,
                "median_execution_time": None,
            },
            "case-003": {
                "success_rate": 1.0,
                "correctness_rate": 1.0,
                "median_execution_time": 0.3,
            },
        },
        "careful": {
            "case-001": {
                "success_rate": 0.8,
                "correctness_rate": 0.9,
                "median_execution_time": 0.4,
            },
            "case-002": {
                "success_rate": 1.0,
                "correctness_rate": 0.7,
                "median_execution_time": 0.5,
            },
            "case-004": {
                "success_rate": 1.0,
                "correctness_rate": 1.0,
                "median_execution_time": 0.1,
            },
        },
    }

    success_result = analytics._build_paired_differences(
        aggregated,
        "direct",
        "careful",
        "success_rate",
    )

    assert success_result["matched_case_count"] == 2
    assert success_result["excluded_case_count"] == 2

    assert success_result["matched_case_ids"] == [
        "case-001",
        "case-002",
    ]

    assert success_result["excluded_case_ids"] == [
        "case-003",
        "case-004",
    ]

    assert success_result["differences"] == pytest.approx([
        0.2,
        -0.5,
    ])

    time_result = analytics._build_paired_differences(
        aggregated,
        "direct",
        "careful",
        "median_execution_time",
    )

    assert time_result["matched_case_count"] == 1
    assert time_result["excluded_case_count"] == 3

    assert time_result["differences"] == pytest.approx([
        -0.2,
    ])


def test_bootstrap_confidence_interval_is_reproducible(analytics):

    differences = [-0.2, 0.1, 0.3, 0.4]

    first = analytics._bootstrap_confidence_interval(
        differences,
        resamples=10000,
        seed=42,
    )

    second = analytics._bootstrap_confidence_interval(
        differences,
        resamples=10000,
        seed=42,
    )

    assert first == second
    assert first["sample_size"] == 4
    assert first["mean_difference"] == pytest.approx(0.15)
    assert first["confidence_level"] == 0.95
    assert first["resamples"] == 10000
    assert first["seed"] == 42
    assert first["method"] == "paired_percentile_bootstrap"
    assert first["lower_bound"] <= first["upper_bound"]


def test_bootstrap_confidence_interval_rejects_insufficient_data(
    analytics,
):

    with pytest.raises(ValueError):
        analytics._bootstrap_confidence_interval([0.2])


def test_bootstrap_confidence_interval_rejects_invalid_values(
    analytics,
):

    with pytest.raises(ValueError):
        analytics._bootstrap_confidence_interval(
            [0.2, float("nan")]
        )

    with pytest.raises(ValueError):
        analytics._bootstrap_confidence_interval(
            [0.2, True]
        )


def test_bootstrap_confidence_interval_rejects_invalid_parameters(
    analytics,
):

    with pytest.raises(ValueError):
        analytics._bootstrap_confidence_interval(
            [0.2, 0.3],
            confidence_level=1.0,
        )

    with pytest.raises(ValueError):
        analytics._bootstrap_confidence_interval(
            [0.2, 0.3],
            resamples=100,
        )


def test_paired_permutation_test_is_reproducible(analytics):

    differences = [-0.2, 0.1, 0.3, 0.4]

    first = analytics._paired_permutation_test(
        differences,
        resamples=10000,
        seed=42,
    )

    second = analytics._paired_permutation_test(
        differences,
        resamples=10000,
        seed=42,
    )

    assert first == second
    assert first["sample_size"] == 4
    assert first["observed_mean_difference"] == pytest.approx(0.15)
    assert first["resamples"] == 10000
    assert first["seed"] == 42
    assert first["method"] == "paired_sign_flip_permutation"
    assert first["alternative"] == "two-sided"
    assert 0 < first["p_value"] <= 1


def test_paired_permutation_test_detects_strong_paired_difference(
    analytics,
):

    differences = [1.0] * 20

    result = analytics._paired_permutation_test(
        differences,
        resamples=10000,
        seed=42,
    )

    assert result["observed_mean_difference"] == pytest.approx(1.0)
    assert result["p_value"] < 0.05
    assert result["statistically_significant"] is True


def test_paired_permutation_test_returns_one_for_zero_differences(
    analytics,
):

    result = analytics._paired_permutation_test(
        [0.0, 0.0, 0.0, 0.0],
        resamples=1000,
        seed=42,
    )

    assert result["observed_mean_difference"] == 0
    assert result["extreme_permutations"] == 1000
    assert result["p_value"] == 1.0
    assert result["statistically_significant"] is False


def test_paired_permutation_test_rejects_invalid_inputs(analytics):

    with pytest.raises(ValueError):
        analytics._paired_permutation_test([0.2])

    with pytest.raises(ValueError):
        analytics._paired_permutation_test(
            [0.2, float("nan")]
        )

    with pytest.raises(ValueError):
        analytics._paired_permutation_test(
            [0.2, True]
        )

    with pytest.raises(ValueError):
        analytics._paired_permutation_test(
            [0.2, 0.3],
            resamples=100,
        )

def test_cohens_dz_calculates_positive_effect_size():
    analytics = BenchmarkAnalytics()

    result = analytics._cohens_dz([1, 2, 3])

    assert result["sample_size"] == 3
    assert result["mean_difference"] == 2
    assert result["standard_deviation"] == 1
    assert result["cohens_dz"] == 2
    assert result["effect_size_status"] == "calculated"


def test_cohens_dz_calculates_negative_effect_size():
    analytics = BenchmarkAnalytics()

    result = analytics._cohens_dz([-1, -2, -3])

    assert result["mean_difference"] == -2
    assert result["cohens_dz"] == -2
    assert result["effect_size_status"] == "calculated"


def test_cohens_dz_handles_zero_variance():
    analytics = BenchmarkAnalytics()

    result = analytics._cohens_dz([2, 2, 2])

    assert result["mean_difference"] == 2
    assert result["standard_deviation"] == 0
    assert result["cohens_dz"] is None
    assert (
        result["effect_size_status"]
        == "undefined_zero_variance"
    )


def test_cohens_dz_rejects_insufficient_data():
    analytics = BenchmarkAnalytics()

    with pytest.raises(ValueError):
        analytics._cohens_dz([1])


def test_cohens_dz_rejects_invalid_values():
    analytics = BenchmarkAnalytics()

    with pytest.raises(ValueError):
        analytics._cohens_dz([1, float("nan")])

    with pytest.raises(ValueError):
        analytics._cohens_dz([1, float("inf")])

    with pytest.raises(ValueError):
        analytics._cohens_dz([1, True])


def test_cohens_dz_rejects_non_list_input():
    analytics = BenchmarkAnalytics()

    with pytest.raises(TypeError):
        analytics._cohens_dz(5)
# ------------------------------------------------------
# Holm-Bonferroni correction tests.
# ------------------------------------------------------


def test_holm_adjusts_p_values_correctly():
    analytics = BenchmarkAnalytics()

    result = analytics._holm_adjust_p_values(
        [0.01, 0.04, 0.03, 0.002]
    )

    assert result == pytest.approx(
        [0.03, 0.06, 0.06, 0.008]
    )


def test_holm_preserves_original_input_order():
    analytics = BenchmarkAnalytics()

    p_values = [0.04, 0.002, 0.01]

    result = analytics._holm_adjust_p_values(p_values)

    assert result == pytest.approx(
    [0.04, 0.006, 0.02]
)

def test_holm_handles_equal_p_values():
    analytics = BenchmarkAnalytics()

    result = analytics._holm_adjust_p_values(
        [0.01, 0.01, 0.5]
    )

    assert result == pytest.approx(
        [0.03, 0.03, 0.5]
    )


def test_holm_handles_zero_and_one_p_values():
    analytics = BenchmarkAnalytics()

    result = analytics._holm_adjust_p_values(
        [0, 0.5, 1]
    )

    assert result == pytest.approx([0, 1, 1])


def test_holm_handles_empty_input():
    analytics = BenchmarkAnalytics()

    result = analytics._holm_adjust_p_values([])

    assert result == []


def test_holm_rejects_invalid_input():
    analytics = BenchmarkAnalytics()

    with pytest.raises(TypeError):
        analytics._holm_adjust_p_values(0.05)

    with pytest.raises(ValueError):
        analytics._holm_adjust_p_values([-0.1, 0.05])

    with pytest.raises(ValueError):
        analytics._holm_adjust_p_values([0.05, 1.1])

    with pytest.raises(ValueError):
        analytics._holm_adjust_p_values([0.05, float("nan")])

    with pytest.raises(ValueError):
        analytics._holm_adjust_p_values([0.05, float("inf")])

    with pytest.raises(ValueError):
        analytics._holm_adjust_p_values([0.05, True])
# ------------------------------------------------------
# Strategy comparison engine tests.
# ------------------------------------------------------


def make_comparison_trials():
    """Create repeatable trials for three strategies."""

    success_counts = {
        "direct": [2, 1, 1],
        "step_by_step": [1, 2, 1],
        "careful": [1, 1, 2],
    }

    correct_counts = {
        "direct": [2, 1, 0],
        "step_by_step": [1, 1, 1],
        "careful": [1, 1, 2],
    }

    trials = []

    for case_index in range(3):
        case_id = f"case-{case_index + 1:03d}"

        for strategy_index, strategy_id in enumerate(
            ["direct", "step_by_step", "careful"]
        ):
            for trial_number in range(1, 3):

                execution_success = (
                    trial_number
                    <= success_counts[strategy_id][case_index]
                )

                is_correct = (
                    trial_number
                    <= correct_counts[strategy_id][case_index]
                )

                execution_time = (
                    0.1
                    + strategy_index * 0.03
                    + case_index * 0.01
                    + trial_number * 0.001
                )

                trials.append(
                    make_trial(
                        case_id=case_id,
                        strategy_id=strategy_id,
                        execution_success=execution_success,
                        is_correct=is_correct,
                        execution_time=execution_time,
                        trial_number=trial_number,
                    )
                )

    # This trial must never enter the analysis.
    trials.append(
        make_trial(
            case_id="case-001",
            strategy_id="direct",
            is_warmup=True,
            trial_number=99,
        )
    )

    return trials


def test_strategy_comparison_generates_pairwise_results(
    analytics,
    monkeypatch,
    sample_experiment,
):
    trials = make_comparison_trials()

    install_sample_data(
        monkeypatch,
        sample_experiment,
        [],
        trials,
    )

    p_values = iter([
        0.01, 0.04, 0.03,
        0.20, 0.30, 0.40,
        0.001, 0.02, 0.03,
    ])

    def fake_bootstrap(
        differences,
        confidence_level=0.95,
        resamples=10000,
        seed=42,
    ):
        return {
            "sample_size": len(differences),
            "mean_difference": sum(differences) / len(differences),
            "confidence_level": confidence_level,
            "lower_bound": -0.1,
            "upper_bound": 0.1,
            "resamples": resamples,
            "seed": seed,
            "method": "test_bootstrap",
        }

    def fake_permutation(
        differences,
        resamples=10000,
        seed=42,
    ):
        return {
            "sample_size": len(differences),
            "p_value": next(p_values),
            "resamples": resamples,
            "method": "test_permutation",
        }

    monkeypatch.setattr(
        analytics,
        "_bootstrap_confidence_interval",
        fake_bootstrap,
    )

    monkeypatch.setattr(
        analytics,
        "_paired_permutation_test",
        fake_permutation,
    )

    report = analytics.generate_strategy_comparison(
        experiment_id="aegis-exp-test-001",
        strategies=[
            "direct",
            "step_by_step",
            "careful",
        ],
        resamples=1000,
        seed=42,
    )

    assert report["summary"]["measured_trials"] == 18
    assert report["summary"]["selected_strategy_count"] == 3

    assert set(report["outcome_families"]) == {
        "success_rate",
        "correctness_rate",
        "median_execution_time",
    }

    for family in report["outcome_families"].values():
        assert family["comparison_count"] == 3
        assert family["analyzed_comparison_count"] == 3

        for comparison in family["comparisons"]:
            assert comparison["status"] == "analyzed"
            assert comparison["matched_case_count"] == 3
            assert comparison["excluded_case_count"] == 0
            assert comparison["confidence_interval"] is not None
            assert comparison["permutation_test"] is not None
            assert comparison["effect_size"] is not None

    assert report["outcome_families"]["success_rate"][
        "comparisons"
    ][0]["adjusted_p_value"] == pytest.approx(0.03)

    assert report["outcome_families"]["success_rate"][
        "comparisons"
    ][1]["adjusted_p_value"] == pytest.approx(0.06)

    assert report["outcome_families"]["success_rate"][
        "comparisons"
    ][2]["adjusted_p_value"] == pytest.approx(0.06)

    assert report["outcome_families"]["correctness_rate"][
        "comparisons"
    ][0]["adjusted_p_value"] == pytest.approx(0.60)

    assert report["outcome_families"]["median_execution_time"][
        "comparisons"
    ][0]["adjusted_p_value"] == pytest.approx(0.003)

    assert (
        report["methodology"]["correction_scope"]
        == "within_each_outcome_family"
    )


def test_strategy_comparison_excludes_warmup_trials(
    analytics,
    monkeypatch,
    sample_experiment,
):
    trials = make_comparison_trials()

    install_sample_data(
        monkeypatch,
        sample_experiment,
        [],
        trials,
    )

    monkeypatch.setattr(
        analytics,
        "_bootstrap_confidence_interval",
        lambda differences, **kwargs: {
            "sample_size": len(differences),
            "lower_bound": 0,
            "upper_bound": 1,
        },
    )

    monkeypatch.setattr(
        analytics,
        "_paired_permutation_test",
        lambda differences, **kwargs: {
            "p_value": 0.5,
        },
    )

    report = analytics.generate_strategy_comparison(
        "aegis-exp-test-001",
        outcomes=["success_rate"],
        resamples=1000,
    )

    assert report["summary"]["measured_trials"] == 18

    for comparison in report["outcome_families"][
        "success_rate"
    ]["comparisons"]:
        assert comparison["matched_case_count"] == 3
        assert "case-001" not in comparison["excluded_case_ids"]


def test_strategy_comparison_handles_insufficient_paired_cases(
    analytics,
    monkeypatch,
    sample_experiment,
):
    trials = [
        make_trial(
            "case-001",
            "direct",
        ),
        make_trial(
            "case-001",
            "step_by_step",
        ),
        make_trial(
            "case-002",
            "direct",
        ),
    ]

    install_sample_data(
        monkeypatch,
        sample_experiment,
        [],
        trials,
    )

    report = analytics.generate_strategy_comparison(
        "aegis-exp-test-001",
        outcomes=["success_rate"],
        resamples=1000,
    )

    family = report["outcome_families"]["success_rate"]

    assert family["comparison_count"] == 1
    assert family["analyzed_comparison_count"] == 0
    assert family["insufficient_comparison_count"] == 1

    comparison = family["comparisons"][0]

    assert comparison["status"] == "insufficient_paired_cases"
    assert comparison["matched_case_count"] == 1
    assert comparison["raw_p_value"] is None
    assert comparison["adjusted_p_value"] is None


def test_strategy_comparison_rejects_invalid_strategy(
    analytics,
    monkeypatch,
    sample_experiment,
):
    install_sample_data(
        monkeypatch,
        sample_experiment,
        [],
        make_comparison_trials(),
    )

    with pytest.raises(ValueError, match="Unknown strategy"):
        analytics.generate_strategy_comparison(
            "aegis-exp-test-001",
            strategies=["direct", "unknown"],
        )


def test_strategy_comparison_rejects_invalid_outcome(
    analytics,
    monkeypatch,
    sample_experiment,
):
    install_sample_data(
        monkeypatch,
        sample_experiment,
        [],
        make_comparison_trials(),
    )

    with pytest.raises(ValueError, match="Unsupported outcome"):
        analytics.generate_strategy_comparison(
            "aegis-exp-test-001",
            outcomes=["accuracy"],
        )
