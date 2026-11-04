
"""
AEGIS Benchmark Analytics

Analyzes historical benchmark experiments and
persisted research experiment results.
"""

import json
import math
import random
from statistics import mean, median

from app.memory.database import (
    get_all_benchmark_results,
    get_research_experiment,
    get_research_case_results,
    get_research_trial_results,
)


class BenchmarkAnalytics:

    INSTRUMENTATION_FIELDS = (
        "one_pass_analysis_calls",
        "individual_metric_calls",
        "analysis_and_metric_method_calls",
        "verification_operations",
        "input_validation_calls",
        "execution_step_count",
    )

    # ------------------------------------------------------
    # Existing historical benchmark report.
    # ------------------------------------------------------

    def generate_report(self):

        records = get_all_benchmark_results()

        if not records:
            return {
                "total_experiments": 0,
                "total_trials": 0,
                "success_rate": 0,
                "correctness_rate": 0,
                "average_execution_time": 0,
                "strategy_performance": {},
                "best_strategy": None,
            }

        total_experiments = len(records)

        total_trials = sum(record[3] for record in records)
        successful_runs = sum(record[4] for record in records)
        correct_experiments = sum(record[7] for record in records)

        success_rate = (
            successful_runs / total_trials * 100
            if total_trials else 0
        )

        correctness_rate = (
            correct_experiments / total_experiments * 100
        )

        average_execution_time = (
            sum(record[6] for record in records)
            / total_experiments
        )

        strategy_data = {}

        for record in records:

            strategy_id = record[2]

            if strategy_id not in strategy_data:
                strategy_data[strategy_id] = {
                    "experiments": 0,
                    "successful_runs": 0,
                    "total_trials": 0,
                    "correct_experiments": 0,
                    "execution_times": [],
                }

            data = strategy_data[strategy_id]

            data["experiments"] += 1
            data["successful_runs"] += record[4]
            data["total_trials"] += record[3]
            data["correct_experiments"] += record[7]
            data["execution_times"].append(record[6])

        strategy_performance = {}

        for strategy_id, data in strategy_data.items():

            strategy_performance[strategy_id] = {
                "experiments": data["experiments"],
                "success_rate": round(
                    data["successful_runs"]
                    / data["total_trials"] * 100,
                    2,
                ) if data["total_trials"] else 0,
                "correctness_rate": round(
                    data["correct_experiments"]
                    / data["experiments"] * 100,
                    2,
                ),
                "average_execution_time": round(
                    sum(data["execution_times"])
                    / len(data["execution_times"]),
                    6,
                ),
            }

        best_strategy = max(
            strategy_performance,
            key=lambda strategy: (
                strategy_performance[strategy]["correctness_rate"],
                strategy_performance[strategy]["success_rate"],
                -strategy_performance[strategy][
                    "average_execution_time"
                ],
            ),
        )

        return {
            "total_experiments": total_experiments,
            "total_trials": total_trials,
            "success_rate": round(success_rate, 2),
            "correctness_rate": round(correctness_rate, 2),
            "average_execution_time": round(
                average_execution_time, 6
            ),
            "strategy_performance": strategy_performance,
            "best_strategy": best_strategy,
        }

    # ------------------------------------------------------
    # Research analytics helpers.
    # ------------------------------------------------------

    @staticmethod
    def _percentile(values, percentile):

        if not values:
            return None

        ordered = sorted(values)

        index = math.ceil(
            percentile * len(ordered)
        ) - 1

        return ordered[max(0, index)]

    @staticmethod
    def _round_time(value):

        if value is None:
            return None

        return round(value, 9)

    def _summarize_trials(self, trials):

        total_trials = len(trials)

        successful_trials = sum(
            bool(trial["execution_success"])
            for trial in trials
        )

        correct_trials = sum(
            bool(trial["is_correct"])
            for trial in trials
        )

        execution_times = [
            trial["execution_time_seconds"]
            for trial in trials
            if trial["execution_time_seconds"] is not None
        ]

        return {
            "total_trials": total_trials,
            "successful_trials": successful_trials,
            "failed_trials": total_trials - successful_trials,
            "correct_trials": correct_trials,
            "success_rate": round(
                successful_trials / total_trials * 100,
                2,
            ) if total_trials else 0,
            "correctness_rate": round(
                correct_trials / total_trials * 100,
                2,
            ) if total_trials else 0,
            "timed_trials": len(execution_times),
            "average_execution_time_seconds": self._round_time(
                mean(execution_times)
            ) if execution_times else None,
            "median_execution_time_seconds": self._round_time(
                median(execution_times)
            ) if execution_times else None,
            "p95_execution_time_seconds": self._round_time(
                self._percentile(execution_times, 0.95)
            ),
        }

    def _summarize_instrumentation(self, trials):

        totals = {
            field: 0
            for field in self.INSTRUMENTATION_FIELDS
        }

        # Count records containing a valid value for each field.
        field_record_counts = {
            field: 0
            for field in self.INSTRUMENTATION_FIELDS
        }

        valid_records = 0
        missing_records = 0

        verification_passed = 0
        verification_failed = 0
        verification_not_applicable = 0

        for trial in trials:

            raw_details = trial.get(
                "execution_details_json"
            )

            if not raw_details:
                missing_records += 1
                continue

            try:
                details = json.loads(raw_details)
            except (TypeError, ValueError):
                missing_records += 1
                continue

            if not isinstance(details, dict):
                missing_records += 1
                continue

            valid_records += 1

            for field in self.INSTRUMENTATION_FIELDS:

                value = details.get(field)

                if (
                    isinstance(value, int)
                    and not isinstance(value, bool)
                    and value >= 0
                ):
                    totals[field] += value
                    field_record_counts[field] += 1

            verification = details.get(
                "verification_passed"
            )

            if verification is True:
                verification_passed += 1

            elif verification is False:
                verification_failed += 1

            else:
                verification_not_applicable += 1

        averages = {
            field: round(
                totals[field] / field_record_counts[field],
                4,
            ) if field_record_counts[field] else None
            for field in self.INSTRUMENTATION_FIELDS
        }

        verification_count = (
            verification_passed + verification_failed
        )

        return {
            "trials_with_instrumentation": valid_records,
            "trials_missing_instrumentation": missing_records,
            "total_operations": totals,
            "average_operations_per_instrumented_trial": averages,
            "verification_passed": verification_passed,
            "verification_failed": verification_failed,
            "verification_not_applicable": (
                verification_not_applicable
            ),
            "verification_pass_rate": round(
                verification_passed / verification_count * 100,
                2,
            ) if verification_count else None,
        }

    # ------------------------------------------------------
    # Grouped scenario analysis.
    # ------------------------------------------------------

    def _build_group_breakdown(
        self,
        trials,
        case_lookup,
        group_field,
    ):

        groups = {}

        for trial in trials:

            case_id = trial["case_id"]
            case = case_lookup.get(case_id)

            if case is None:
                continue

            group_value = case[group_field]
            strategy_id = trial["strategy_id"]

            groups.setdefault(
                group_value,
                {},
            ).setdefault(
                strategy_id,
                [],
            ).append(trial)

        breakdown = {}

        for group_value, strategies in groups.items():

            breakdown[group_value] = {
                strategy_id: self._summarize_trials(
                    strategy_trials
                )
                for strategy_id, strategy_trials
                in strategies.items()
            }

        return breakdown

    # ------------------------------------------------------
    # Case-level strategy aggregation.
    # ------------------------------------------------------

    def _aggregate_case_strategy_results(self, trials):
        """
        Aggregate measured trials by benchmark case and strategy.

        Each case-strategy pair produces:

        - Trial count.
        - Execution success proportion.
        - Correctness proportion.
        - Median execution time among successful trials.
        - Number of successful trials with valid timing.

        Warm-up trials are excluded.

        The benchmark case is the unit of analysis for
        subsequent paired statistical comparisons.
        """

        grouped = {}

        for trial in trials:

            if bool(trial.get("is_warmup", False)):
                continue

            case_id = trial.get("case_id")
            strategy_id = trial.get("strategy_id")

            if not case_id or not strategy_id:
                continue

            key = (case_id, strategy_id)

            grouped.setdefault(
                key,
                [],
            ).append(trial)

        aggregated = {}

        for (case_id, strategy_id), case_trials in grouped.items():

            total_trials = len(case_trials)

            successful_trials = [
                trial
                for trial in case_trials
                if bool(trial["execution_success"])
            ]

            correct_trials = [
                trial
                for trial in case_trials
                if bool(trial["is_correct"])
            ]

            successful_times = [
                trial["execution_time_seconds"]
                for trial in successful_trials
                if (
                    isinstance(
                        trial["execution_time_seconds"],
                        (int, float),
                    )
                    and not isinstance(
                        trial["execution_time_seconds"],
                        bool,
                    )
                    and math.isfinite(
                        trial["execution_time_seconds"]
                    )
                    and trial["execution_time_seconds"] >= 0
                )
            ]

            aggregated.setdefault(
                strategy_id,
                {},
            )[case_id] = {
                "trial_count": total_trials,
                "success_rate": (
                    len(successful_trials) / total_trials
                ),
                "correctness_rate": (
                    len(correct_trials) / total_trials
                ),
                "median_execution_time": (
                    median(successful_times)
                    if successful_times
                    else None
                ),
                "timed_successful_trials": len(
                    successful_times
                ),
            }

        return aggregated

    # ------------------------------------------------------
    # Paired strategy comparison helper.
    # ------------------------------------------------------

    def _build_paired_differences(
        self,
        aggregated,
        strategy_a,
        strategy_b,
        metric,
    ):
        """
        Build matched case-level differences between two strategies.

        Only cases with valid measurements for both strategies
        are included.

        Difference convention:
            Strategy A value - Strategy B value

        Supported metrics:
            - success_rate
            - correctness_rate
            - median_execution_time
        """

        supported_metrics = {
            "success_rate",
            "correctness_rate",
            "median_execution_time",
        }

        if metric not in supported_metrics:
            raise ValueError(
                f"Unsupported comparison metric: {metric}"
            )

        if strategy_a == strategy_b:
            raise ValueError(
                "Strategies must be different."
            )

        strategy_a_cases = aggregated.get(
            strategy_a,
            {},
        )

        strategy_b_cases = aggregated.get(
            strategy_b,
            {},
        )

        all_case_ids = sorted(
            set(strategy_a_cases) | set(strategy_b_cases)
        )

        paired_results = []
        excluded_case_ids = []

        for case_id in all_case_ids:

            result_a = strategy_a_cases.get(case_id)
            result_b = strategy_b_cases.get(case_id)

            if not isinstance(result_a, dict):
                excluded_case_ids.append(case_id)
                continue

            if not isinstance(result_b, dict):
                excluded_case_ids.append(case_id)
                continue

            value_a = result_a.get(metric)
            value_b = result_b.get(metric)

            valid_a = (
                isinstance(value_a, (int, float))
                and not isinstance(value_a, bool)
                and math.isfinite(value_a)
            )

            valid_b = (
                isinstance(value_b, (int, float))
                and not isinstance(value_b, bool)
                and math.isfinite(value_b)
            )

            if not valid_a or not valid_b:
                excluded_case_ids.append(case_id)
                continue

            paired_results.append({
                "case_id": case_id,
                "strategy_a_value": value_a,
                "strategy_b_value": value_b,
                "difference": value_a - value_b,
            })

        return {
            "strategy_a": strategy_a,
            "strategy_b": strategy_b,
            "metric": metric,
            "matched_case_count": len(paired_results),
            "excluded_case_count": len(excluded_case_ids),
            "matched_case_ids": [
                item["case_id"]
                for item in paired_results
            ],
            "excluded_case_ids": excluded_case_ids,
            "paired_results": paired_results,
            "differences": [
                item["difference"]
                for item in paired_results
            ],
        }

    # ------------------------------------------------------
    # Paired bootstrap confidence interval.
    # ------------------------------------------------------

    def _bootstrap_confidence_interval(
        self,
        differences,
        confidence_level=0.95,
        resamples=10000,
        seed=42,
    ):
        """
        Calculate a paired bootstrap confidence interval
        for the mean of paired differences.

        Each resample draws cases with replacement.
        The same number of cases is retained in every resample.

        Uses a local random generator for reproducibility.
        """

        if not isinstance(differences, (list, tuple)):
            raise TypeError(
                "Differences must be a list or tuple."
            )

        values = list(differences)

        if len(values) < 2:
            raise ValueError(
                "At least two paired differences are required."
            )

        for value in values:
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError(
                    "All differences must be finite numbers."
                )

        if (
            isinstance(confidence_level, bool)
            or not isinstance(confidence_level, (int, float))
            or not math.isfinite(confidence_level)
            or not 0 < confidence_level < 1
        ):
            raise ValueError(
                "Confidence level must be between 0 and 1."
            )

        if (
            isinstance(resamples, bool)
            or not isinstance(resamples, int)
            or resamples < 1000
        ):
            raise ValueError(
                "At least 1000 bootstrap resamples are required."
            )

        generator = random.Random(seed)

        bootstrap_means = []

        for _ in range(resamples):
            sample = generator.choices(
                values,
                k=len(values),
            )

            bootstrap_means.append(mean(sample))

        tail_probability = (
            1 - confidence_level
        ) / 2

        return {
            "sample_size": len(values),
            "mean_difference": mean(values),
            "confidence_level": confidence_level,
            "lower_bound": self._percentile(
                bootstrap_means,
                tail_probability,
            ),
            "upper_bound": self._percentile(
                bootstrap_means,
                1 - tail_probability,
            ),
            "resamples": resamples,
            "seed": seed,
            "method": "paired_percentile_bootstrap",
        }

    # ------------------------------------------------------
    # Paired permutation significance test.
    # ------------------------------------------------------

    def _paired_permutation_test(
        self,
        differences,
        resamples=10000,
        seed=42,
    ):
        """
        Perform a two-sided paired sign-flip permutation test.

        Under the null hypothesis, the signs of paired
        differences are exchangeable.

        The test statistic is the absolute mean difference.

        Uses the plus-one correction for the Monte Carlo
        p-value to avoid reporting a zero p-value.
        """

        if not isinstance(differences, (list, tuple)):
            raise TypeError(
                "Differences must be a list or tuple."
            )

        values = list(differences)

        if len(values) < 2:
            raise ValueError(
                "At least two paired differences are required."
            )

        for value in values:
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError(
                    "All differences must be finite numbers."
                )

        if (
            isinstance(resamples, bool)
            or not isinstance(resamples, int)
            or resamples < 1000
        ):
            raise ValueError(
                "At least 1000 permutation resamples are required."
            )

        observed_mean = mean(values)
        observed_statistic = abs(observed_mean)

        generator = random.Random(seed)

        extreme_count = 0

        for _ in range(resamples):

            permuted_values = [
                value if generator.random() < 0.5 else -value
                for value in values
            ]

            permuted_statistic = abs(
                mean(permuted_values)
            )

            if (
                permuted_statistic
                >= observed_statistic - 1e-12
            ):
                extreme_count += 1

        p_value = (
            extreme_count + 1
        ) / (
            resamples + 1
        )

        return {
            "sample_size": len(values),
            "observed_mean_difference": observed_mean,
            "observed_statistic": observed_statistic,
            "extreme_permutations": extreme_count,
            "resamples": resamples,
            "p_value": p_value,
            "significance_level": 0.05,
            "statistically_significant": p_value < 0.05,
            "alternative": "two-sided",
            "method": "paired_sign_flip_permutation",
            "seed": seed,
            "null_hypothesis": (
                "The paired differences have no systematic effect."
            ),
            "assumption": (
                "Paired differences are exchangeable under sign changes."
            ),
        }

    # ------------------------------------------------------
    # Paired effect size: Cohen's dz.
    # ------------------------------------------------------

    # ------------------------------------------------------
    # Holm-Bonferroni multiple-comparison correction.
    # ------------------------------------------------------

    @staticmethod
    def _holm_adjust_p_values(p_values):
        """
        Apply Holm-Bonferroni correction to a family of p-values.

        The procedure:

        1. Sort p-values from smallest to largest.
        2. Multiply each p-value by the number of
           hypotheses remaining in the ordered family.
        3. Apply a cumulative maximum to preserve
           monotonicity.
        4. Cap adjusted values at 1.0.
        5. Restore the original input order.

        Returns:
            A list of adjusted p-values in the same order
            as the original input.

        An empty input returns an empty list.
        """

        if not isinstance(p_values, (list, tuple)):
            raise TypeError(
                "P-values must be provided as a list or tuple."
            )

        values = list(p_values)

        for value in values:
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or not 0 <= value <= 1
            ):
                raise ValueError(
                    "Every p-value must be a finite number between 0 and 1."
                )

        if not values:
            return []

        indexed_values = sorted(
            enumerate(values),
            key=lambda item: item[1],
        )

        total_tests = len(values)
        adjusted_values = [0.0] * total_tests

        previous_adjusted = 0.0

        for rank, (original_index, p_value) in enumerate(
            indexed_values
        ):

            multiplier = total_tests - rank

            adjusted_value = min(
                1.0,
                multiplier * p_value,
            )

            adjusted_value = max(
                previous_adjusted,
                adjusted_value,
            )

            adjusted_values[original_index] = adjusted_value
            previous_adjusted = adjusted_value

        return adjusted_values

    def _cohens_dz(self, differences):
        """
        Calculate Cohen's dz for paired observations.

        Cohen's dz is the mean paired difference divided
        by the sample standard deviation of differences.

        Difference direction:
            Strategy A value - Strategy B value

        Returns None for the effect size when the sample
        standard deviation is zero because the ratio is
        undefined.
        """

        if not isinstance(differences, (list, tuple)):
            raise TypeError(
                "Differences must be a list or tuple."
            )

        values = list(differences)

        if len(values) < 2:
            raise ValueError(
                "At least two paired differences are required."
            )

        for value in values:
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError(
                    "All differences must be finite numbers."
                )

        sample_size = len(values)
        mean_difference = mean(values)

        squared_deviations = sum(
            (value - mean_difference) ** 2
            for value in values
        )

        sample_variance = (
            squared_deviations / (sample_size - 1)
        )

        standard_deviation = math.sqrt(sample_variance)

        if standard_deviation == 0:
            return {
                "sample_size": sample_size,
                "mean_difference": mean_difference,
                "standard_deviation": 0.0,
                "cohens_dz": None,
                "effect_size_status": "undefined_zero_variance",
                "method": "cohens_dz_paired",
            }

        effect_size = (
            mean_difference / standard_deviation
        )

        return {
            "sample_size": sample_size,
            "mean_difference": mean_difference,
            "standard_deviation": standard_deviation,
            "cohens_dz": effect_size,
            "effect_size_status": "calculated",
            "method": "cohens_dz_paired",
        }

    # ------------------------------------------------------
    # Main research report.
    # ------------------------------------------------------

    def generate_research_report(self, experiment_id):

        if (
            not isinstance(experiment_id, str)
            or not experiment_id.strip()
        ):
            raise ValueError(
                "Experiment ID must be a non-empty string."
            )

        experiment = get_research_experiment(
            experiment_id
        )

        if experiment is None:
            raise ValueError(
                f"Research experiment not found: {experiment_id}"
            )

        case_results = get_research_case_results(
            experiment_id
        )

        all_trials = get_research_trial_results(
            experiment_id
        )

        warmup_trials = [
            trial
            for trial in all_trials
            if bool(trial["is_warmup"])
        ]

        measured_trials = [
            trial
            for trial in all_trials
            if not bool(trial["is_warmup"])
        ]

        case_lookup = {
            case["case_id"]: case
            for case in case_results
        }

        strategies = {}

        for trial in measured_trials:

            strategy_id = trial["strategy_id"]

            strategies.setdefault(
                strategy_id,
                [],
            ).append(trial)

        strategy_performance = {}

        for strategy_id, strategy_trials in strategies.items():

            strategy_performance[strategy_id] = {
                **self._summarize_trials(strategy_trials),
                "instrumentation": (
                    self._summarize_instrumentation(
                        strategy_trials
                    )
                ),
            }

        return {
            "experiment": {
                "experiment_id": experiment["experiment_id"],
                "experiment_name": experiment["experiment_name"],
                "dataset_id": experiment["dataset_id"],
                "dataset_version": experiment["dataset_version"],
                "random_seed": experiment["random_seed"],
                "status": experiment["status"],
            },
            "summary": {
                "total_cases": len(case_results),
                "measured_trials": len(measured_trials),
                "warmup_trials": len(warmup_trials),
                "strategy_count": len(strategies),
            },
            "strategy_performance": strategy_performance,
            "category_performance": self._build_group_breakdown(
                measured_trials,
                case_lookup,
                "category",
            ),
            "difficulty_performance": self._build_group_breakdown(
                measured_trials,
                case_lookup,
                "difficulty",
            ),
        }

    # ------------------------------------------------------
    # Pairwise research strategy comparison.
    # ------------------------------------------------------

    def generate_strategy_comparison(
        self,
        experiment_id,
        strategies=None,
        outcomes=None,
        resamples=10000,
        seed=42,
    ):
        """
        Compare research strategies using paired case-level
        statistical analysis.

        Each benchmark case is one observation.

        Repeated trials within a case are aggregated before
        statistical comparisons are performed.

        Supported outcomes:
            - success_rate
            - correctness_rate
            - median_execution_time

        Holm correction is applied separately within each
        outcome family.

        Difference convention:
            Strategy A - Strategy B
        """

        if (
            not isinstance(experiment_id, str)
            or not experiment_id.strip()
        ):
            raise ValueError(
                "Experiment ID must be a non-empty string."
            )

        if (
            isinstance(resamples, bool)
            or not isinstance(resamples, int)
            or resamples < 1000
        ):
            raise ValueError(
                "At least 1000 resamples are required."
            )

        if (
            isinstance(seed, bool)
            or not isinstance(seed, int)
        ):
            raise ValueError(
                "Seed must be an integer."
            )

        supported_outcomes = (
            "success_rate",
            "correctness_rate",
            "median_execution_time",
        )

        if outcomes is None:
            selected_outcomes = list(supported_outcomes)

        else:
            if not isinstance(outcomes, (list, tuple)):
                raise TypeError(
                    "Outcomes must be a list or tuple."
                )

            selected_outcomes = list(outcomes)

            if len(selected_outcomes) != len(set(selected_outcomes)):
                raise ValueError(
                    "Outcomes must not contain duplicates."
                )

            if not selected_outcomes:
                raise ValueError(
                    "At least one outcome must be selected."
                )

            for outcome in selected_outcomes:
                if outcome not in supported_outcomes:
                    raise ValueError(
                        f"Unsupported outcome: {outcome}"
                    )

        experiment = get_research_experiment(
            experiment_id
        )

        if experiment is None:
            raise ValueError(
                f"Research experiment not found: {experiment_id}"
            )

        all_trials = get_research_trial_results(
            experiment_id
        )

        measured_trials = [
            trial
            for trial in all_trials
            if not bool(trial.get("is_warmup", False))
        ]

        aggregated = self._aggregate_case_strategy_results(
            measured_trials
        )

        available_strategies = sorted(aggregated)

        if strategies is None:
            selected_strategies = available_strategies

        else:
            if not isinstance(strategies, (list, tuple)):
                raise TypeError(
                    "Strategies must be a list or tuple."
                )

            selected_strategies = list(strategies)

            if len(selected_strategies) < 2:
                raise ValueError(
                    "At least two strategies must be selected."
                )

            if len(selected_strategies) != len(set(selected_strategies)):
                raise ValueError(
                    "Strategies must not contain duplicates."
                )

            for strategy in selected_strategies:
                if (
                    not isinstance(strategy, str)
                    or not strategy.strip()
                ):
                    raise ValueError(
                        "Strategy IDs must be non-empty strings."
                    )

                if strategy not in available_strategies:
                    raise ValueError(
                        f"Unknown strategy: {strategy}"
                    )

        if len(selected_strategies) < 2:
            raise ValueError(
                "At least two available strategies are required."
            )

        outcome_families = {}

        for outcome_index, outcome in enumerate(
            selected_outcomes
        ):

            comparisons = []

            comparison_pairs = [
                (
                    selected_strategies[index_a],
                    selected_strategies[index_b],
                )
                for index_a in range(
                    len(selected_strategies)
                )
                for index_b in range(
                    index_a + 1,
                    len(selected_strategies),
                )
            ]

            for pair_index, (
                strategy_a,
                strategy_b,
            ) in enumerate(comparison_pairs):

                paired = self._build_paired_differences(
                    aggregated,
                    strategy_a,
                    strategy_b,
                    outcome,
                )

                differences = paired["differences"]

                comparison = {
                    **paired,
                    "status": "insufficient_paired_cases",
                    "mean_difference": None,
                    "confidence_interval": None,
                    "permutation_test": None,
                    "raw_p_value": None,
                    "adjusted_p_value": None,
                    "raw_statistically_significant": None,
                    "statistically_significant": None,
                    "effect_size": None,
                }

                if len(differences) < 2:
                    comparisons.append(comparison)
                    continue

                comparison_seed = (
                    seed
                    + outcome_index * 100000
                    + pair_index
                )

                confidence_interval = (
                    self._bootstrap_confidence_interval(
                        differences,
                        confidence_level=0.95,
                        resamples=resamples,
                        seed=comparison_seed,
                    )
                )

                permutation_test = (
                    self._paired_permutation_test(
                        differences,
                        resamples=resamples,
                        seed=comparison_seed,
                    )
                )

                effect_size = self._cohens_dz(
                    differences
                )

                raw_p_value = permutation_test["p_value"]

                comparison.update({
                    "status": "analyzed",
                    "mean_difference": mean(differences),
                    "confidence_interval": confidence_interval,
                    "permutation_test": permutation_test,
                    "raw_p_value": raw_p_value,
                    "raw_statistically_significant": (
                        raw_p_value < 0.05
                    ),
                    "effect_size": effect_size,
                })

                comparisons.append(comparison)

            # Apply Holm correction only to comparisons
            # with valid inferential p-values.
            valid_indices = [
                index
                for index, comparison in enumerate(comparisons)
                if comparison["raw_p_value"] is not None
            ]

            raw_p_values = [
                comparisons[index]["raw_p_value"]
                for index in valid_indices
            ]

            adjusted_p_values = (
                self._holm_adjust_p_values(raw_p_values)
            )

            for index, adjusted_p_value in zip(
                valid_indices,
                adjusted_p_values,
            ):

                comparisons[index]["adjusted_p_value"] = (
                    adjusted_p_value
                )

                comparisons[index]["statistically_significant"] = (
                    adjusted_p_value < 0.05
                )

            outcome_families[outcome] = {
                "comparison_count": len(comparisons),
                "analyzed_comparison_count": len(valid_indices),
                "insufficient_comparison_count": (
                    len(comparisons) - len(valid_indices)
                ),
                "multiple_comparison_correction": (
                    "holm_bonferroni"
                ),
                "significance_level": 0.05,
                "comparisons": comparisons,
            }

        return {
            "experiment": {
                "experiment_id": experiment["experiment_id"],
                "experiment_name": experiment["experiment_name"],
                "dataset_id": experiment["dataset_id"],
                "dataset_version": experiment["dataset_version"],
                "random_seed": experiment["random_seed"],
                "status": experiment["status"],
            },
            "methodology": {
                "unit_of_analysis": "benchmark_case",
                "difference_direction": (
                    "strategy_a_minus_strategy_b"
                ),
                "confidence_level": 0.95,
                "bootstrap_resamples": resamples,
                "permutation_resamples": resamples,
                "random_seed": seed,
                "permutation_test": (
                    "two_sided_paired_sign_flip"
                ),
                "effect_size": "cohens_dz_paired",
                "multiple_comparison_correction": (
                    "holm_bonferroni"
                ),
                "correction_scope": "within_each_outcome_family",
                "significance_level": 0.05,
            },
            "summary": {
                "measured_trials": len(measured_trials),
                "available_strategy_count": len(
                    available_strategies
                ),
                "selected_strategy_count": len(
                    selected_strategies
                ),
                "selected_strategies": selected_strategies,
                "selected_outcomes": selected_outcomes,
            },
            "outcome_families": outcome_families,
        }
