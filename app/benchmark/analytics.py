
"""
AEGIS Benchmark Analytics

Analyzes historical benchmark experiments and
persisted research experiment results.
"""

import json
import math
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
