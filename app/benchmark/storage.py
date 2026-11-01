
"""
AEGIS Benchmark Storage

Stores benchmark experiments permanently
in the SQLite database.
"""

from app.memory.database import save_benchmark_result


class BenchmarkStorage:

    def save_results(self, benchmark_result, evaluations):

        saved_records = []

        task = benchmark_result["task"]

        for strategy_id, data in (
            benchmark_result["results"].items()
        ):

            evaluation = evaluations.get(strategy_id, {})

            correct = (
                evaluation.get("correct", False)
                and data["success"]
            )

            record_id = save_benchmark_result(
                task=task,
                strategy_id=strategy_id,
                total_trials=data["total_trials"],
                successful_runs=data["successful_runs"],
                failed_runs=data["failed_runs"],
                average_execution_time=data[
                    "average_execution_time"
                ],
                correct=correct,
            )

            saved_records.append({
                "id": record_id,
                "strategy_id": strategy_id,
                "correct": correct,
            })

        return saved_records
