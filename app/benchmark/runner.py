
"""
AEGIS Benchmark Runner

Runs reproducible, interleaved strategy experiments,
measures execution performance, and independently
evaluates output correctness against benchmark cases.
"""

import random
import statistics
import time

from app.agent.executor import TaskExecutor
from app.learning.strategy import StrategySystem
from app.benchmark.evaluator import BenchmarkEvaluator
from app.benchmark.dataset import (
    BENCHMARK_CASES,
    BENCHMARK_DATASET_VERSION,
)


class BenchmarkRunner:

    def __init__(self):

        self.executor = TaskExecutor()
        self.strategy_system = StrategySystem()
        self.evaluator = BenchmarkEvaluator()

    def run_dataset_benchmark(
        self,
        trials=10,
        warmup_trials=1,
        seed=42,
    ):

        case_results = []

        for index, case in enumerate(BENCHMARK_CASES):

            case_seed = seed + index

            benchmark_result = self.run_benchmark(
                case["text"],
                trials=trials,
                warmup_trials=warmup_trials,
                seed=case_seed,
                benchmark_case=case,
            )

            case_results.append({
                "case_id": case["case_id"],
                "category": case["category"],
                "expected": case["expected"],
                "benchmark": benchmark_result,
            })

        return {
            "dataset_version": BENCHMARK_DATASET_VERSION,
            "total_cases": len(case_results),
            "total_strategies": len(
                self.strategy_system.get_all_strategies()
            ),
            "trials_per_strategy": trials,
            "warmup_trials_per_strategy": warmup_trials,
            "random_seed": seed,
            "cases": case_results,
        }

    def run_benchmark(
        self,
        text,
        trials=10,
        warmup_trials=1,
        seed=42,
        benchmark_case=None,
    ):

        if not isinstance(text, str) or not text.strip():
            raise ValueError("Text must be a non-empty string.")

        if type(trials) is not int or trials < 1:
            raise ValueError("Trials must be a positive integer.")

        if type(warmup_trials) is not int or warmup_trials < 0:
            raise ValueError(
                "Warm-up trials must be a non-negative integer."
            )

        if type(seed) is not int:
            raise ValueError("Seed must be an integer.")

        # Use independent predefined expectations when supplied.
        if benchmark_case is None:

            benchmark_case = {
                "case_id": "custom_benchmark",
                "text": text,
                "expected": {
                    "word_count": len(text.split()),
                    "character_count": len(text),
                    "sentence_count": len([
                        sentence
                        for sentence in (
                            text.replace("!", ".")
                            .replace("?", ".")
                            .split(".")
                        )
                        if sentence.strip()
                    ]),
                },
            }

        else:

            if not isinstance(benchmark_case, dict):
                raise ValueError(
                    "Benchmark case must be a dictionary."
                )

            if benchmark_case.get("text") != text:
                raise ValueError(
                    "Benchmark case text does not match input text."
                )

            if (
                "case_id" not in benchmark_case
                or "expected" not in benchmark_case
            ):
                raise ValueError(
                    "Benchmark case must contain case_id and expected."
                )

        strategy_ids = list(
            self.strategy_system.get_all_strategies()
        )

        if not strategy_ids:
            raise ValueError("No strategies are available.")

        rng = random.Random(seed)

        # Initialize result containers.
        results = {}

        for strategy_id in strategy_ids:

            results[strategy_id] = {
                "success": True,
                "total_trials": trials,
                "successful_runs": 0,
                "failed_runs": 0,
                "correct_runs": 0,
                "incorrect_runs": 0,
                "evaluation_failed_runs": 0,
                "execution_accuracy": 0.0,
                "average_execution_time": 0.0,
                "median_execution_time": 0.0,
                "standard_deviation_execution_time": 0.0,
                "minimum_execution_time": 0.0,
                "maximum_execution_time": 0.0,
                "strategy": strategy_id,
                "results": None,
                "execution_history": [],
                "trial_results": [],
                "error": None,
                "warmup_successful_runs": 0,
                "warmup_failed_runs": 0,
            }

        # Warm-up phase: these executions are not measured.
        for _ in range(warmup_trials):

            warmup_order = strategy_ids.copy()
            rng.shuffle(warmup_order)

            for strategy_id in warmup_order:

                try:

                    self.executor.execute(
                        text,
                        strategy_id
                    )

                    results[strategy_id][
                        "warmup_successful_runs"
                    ] += 1

                except Exception:

                    results[strategy_id][
                        "warmup_failed_runs"
                    ] += 1

        # Measurement phase: interleave strategies.
        execution_order = []

        for trial_number in range(1, trials + 1):

            round_order = strategy_ids.copy()
            rng.shuffle(round_order)

            execution_order.append(round_order.copy())

            for strategy_id in round_order:

                data = results[strategy_id]

                start_time = time.perf_counter_ns()

                # Execute and measure only the execution phase.
                try:

                    execution_result = self.executor.execute(
                        text,
                        strategy_id
                    )

                except Exception as error:

                    execution_time_ns = (
                        time.perf_counter_ns() - start_time
                    )

                    data["failed_runs"] += 1
                    data["error"] = str(error)

                    evaluation = None
                    evaluation_error = None
                    trial_error = str(error)

                else:

                    # Stop timing immediately after execution.
                    execution_time_ns = (
                        time.perf_counter_ns() - start_time
                    )

                    data["successful_runs"] += 1

                    data["strategy"] = execution_result["strategy"]
                    data["results"] = execution_result["results"]
                    data["execution_history"] = (
                        execution_result["execution_history"]
                    )

                    trial_error = None

                    # Evaluate independently of execution.
                    try:

                        evaluation = self.evaluator.evaluate_case(
                            benchmark_case,
                            execution_result
                        )

                        if evaluation["correct"]:
                            data["correct_runs"] += 1
                        else:
                            data["incorrect_runs"] += 1

                        evaluation_error = None

                    except Exception as error:

                        data["incorrect_runs"] += 1
                        data["evaluation_failed_runs"] += 1

                        evaluation = None
                        evaluation_error = str(error)

                execution_time_seconds = (
                    execution_time_ns / 1_000_000_000
                )

                data["trial_results"].append({
                    "trial": trial_number,
                    "execution_time": round(
                        execution_time_seconds, 9
                    ),
                    "execution_time_ns": execution_time_ns,
                    "execution_success": (
                        trial_error is None
                    ),
                    "correct": (
                        evaluation["correct"]
                        if evaluation is not None
                        else False
                    ),
                    "evaluation": evaluation,
                    "evaluation_error": evaluation_error,
                    "error": trial_error,
                })

        # Calculate statistics using measured trials only.
        for strategy_id, data in results.items():

            trial_times = [
                trial["execution_time"]
                for trial in data["trial_results"]
            ]

            data["success"] = data["failed_runs"] == 0

            data["execution_accuracy"] = round(
                (data["correct_runs"] / trials) * 100,
                2
            )

            data["average_execution_time"] = round(
                statistics.mean(trial_times), 9
            )

            data["median_execution_time"] = round(
                statistics.median(trial_times), 9
            )

            data["standard_deviation_execution_time"] = round(
                statistics.pstdev(trial_times), 9
            )

            data["minimum_execution_time"] = round(
                min(trial_times), 9
            )

            data["maximum_execution_time"] = round(
                max(trial_times), 9
            )

        return {
            "task": text,
            "total_strategies": len(strategy_ids),
            "trials_per_strategy": trials,
            "warmup_trials_per_strategy": warmup_trials,
            "random_seed": seed,
            "execution_order": execution_order,
            "results": results,
        }
