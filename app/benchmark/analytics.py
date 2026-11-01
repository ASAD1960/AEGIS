
"""
AEGIS Benchmark Analytics

Analyzes historical benchmark experiments
stored in the database.
"""

from app.memory.database import get_all_benchmark_results


class BenchmarkAnalytics:

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

        total_trials = sum(
            record[3] for record in records
        )

        successful_runs = sum(
            record[4] for record in records
        )

        correct_experiments = sum(
            record[7] for record in records
        )

        success_rate = (
            successful_runs / total_trials
        ) * 100

        correctness_rate = (
            correct_experiments / total_experiments
        ) * 100

        average_execution_time = sum(
            record[6] for record in records
        ) / total_experiments

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
                ),
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
