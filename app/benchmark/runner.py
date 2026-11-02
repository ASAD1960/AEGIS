
"""
AEGIS Benchmark Runner

Runs reproducible, interleaved strategy experiments,
measures execution performance, and independently
evaluates output correctness against benchmark cases.

Supports:
- Original built-in benchmark datasets.
- Validated JSONL research datasets.
- Approved research records by default.
- Explicit execution of draft/reviewed pilot records.
- Partial-metric research cases.
- Dataset and manifest integrity hashes.
- Persistent experiment, case, and trial results.
- Per-trial execution instrumentation metadata.
"""

import hashlib
import json
import random
import statistics
import time
import uuid

from collections import Counter
from pathlib import Path

from app.memory.database import (
    create_research_experiment,
    save_research_case_result,
    save_research_trial_result,
    update_research_experiment_status,
    update_research_experiment_configuration,
)

from app.agent.executor import TaskExecutor
from app.learning.strategy import StrategySystem
from app.benchmark.evaluator import BenchmarkEvaluator
from app.benchmark.dataset import (
    BENCHMARK_CASES,
    BENCHMARK_DATASET_VERSION,
)
from app.benchmark.dataset_validator import (
    DatasetValidationError,
    DatasetValidator,
)


class ResearchBenchmarkError(RuntimeError):
    """Raised when a research benchmark cannot be executed."""


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

    def run_research_dataset_benchmark(
        self,
        dataset_path,
        manifest_path="datasets/manifest.json",
        trials=10,
        warmup_trials=1,
        seed=42,
        allow_non_approved=False,
    ):
        """
        Execute a validated AEGIS research dataset.

        Only approved records are accepted by default.
        Draft and reviewed records require explicit opt-in.

        This initial research runner supports text-based
        research cases through the existing TaskExecutor.

        The dataset and manifest are never modified.

        Completed experiment metadata, case results, and
        measured trial results are persisted in SQLite.
        """

        # ----------------------------------------------------
        # 1. Validate execution configuration
        # ----------------------------------------------------

        if type(trials) is not int or trials < 1:
            raise ResearchBenchmarkError(
                "Trials must be a positive integer."
            )

        if type(warmup_trials) is not int or warmup_trials < 0:
            raise ResearchBenchmarkError(
                "Warm-up trials must be a non-negative integer."
            )

        if type(seed) is not int:
            raise ResearchBenchmarkError(
                "Seed must be an integer."
            )

        if type(allow_non_approved) is not bool:
            raise ResearchBenchmarkError(
                "allow_non_approved must be a boolean."
            )

        dataset_file = Path(dataset_path)
        manifest_file = Path(manifest_path)

        # ----------------------------------------------------
        # 2. Read and validate the manifest
        # ----------------------------------------------------

        try:

            manifest = json.loads(
                manifest_file.read_text(encoding="utf-8")
            )

        except FileNotFoundError as error:

            raise ResearchBenchmarkError(
                f"Manifest not found: {manifest_file}"
            ) from error

        except (json.JSONDecodeError, UnicodeDecodeError) as error:

            raise ResearchBenchmarkError(
                f"Manifest is not valid UTF-8 JSON: {error}"
            ) from error

        except OSError as error:

            raise ResearchBenchmarkError(
                f"Could not read manifest: {error}"
            ) from error

        if not isinstance(manifest, dict):

            raise ResearchBenchmarkError(
                "Manifest root must be a JSON object."
            )

        required_manifest_fields = (
            "dataset_id",
            "dataset_version",
            "schema_version",
            "status",
            "categories",
        )

        for field in required_manifest_fields:

            value = manifest.get(field)

            if field == "categories":
                continue

            if not isinstance(value, str) or not value.strip():

                raise ResearchBenchmarkError(
                    f"Manifest field '{field}' must be "
                    "a non-empty string."
                )

        categories = manifest["categories"]

        if (
            not isinstance(categories, list)
            or not categories
            or any(
                not isinstance(category, str)
                or not category.strip()
                for category in categories
            )
            or len(categories) != len(set(categories))
        ):

            raise ResearchBenchmarkError(
                "Manifest categories must be unique, "
                "non-empty strings."
            )

        validator = DatasetValidator()

        if manifest["schema_version"] != validator.schema_version:

            raise ResearchBenchmarkError(
                "Manifest schema version does not match "
                "the installed dataset validator."
            )

        # ----------------------------------------------------
        # 3. Validate the complete research dataset
        # ----------------------------------------------------

        try:

            records = validator.load_jsonl(dataset_file)

        except DatasetValidationError as error:

            raise ResearchBenchmarkError(
                f"Research dataset validation failed: {error}"
            ) from error

        if not records:

            raise ResearchBenchmarkError(
                "Research dataset contains no valid records."
            )

        # ----------------------------------------------------
        # 4. Validate categories and approval status
        # ----------------------------------------------------

        validation_status_counts = Counter()

        for record in records:

            category = record["category"]

            if category not in categories:

                raise ResearchBenchmarkError(
                    f"Record '{record['case_id']}' uses category "
                    f"'{category}' which is not declared "
                    "in the manifest."
                )

            status = record["validation_status"]

            validation_status_counts[status] += 1

            if (
                status != "approved"
                and not allow_non_approved
            ):

                raise ResearchBenchmarkError(
                    f"Record '{record['case_id']}' has status "
                    f"'{status}'. Only approved records can "
                    "be executed by default. Set "
                    "allow_non_approved=True for an explicit "
                    "development or pilot run."
                )

        # ----------------------------------------------------
        # 5. Prepare all research cases before execution
        # ----------------------------------------------------

        prepared_cases = []

        for record in records:

            context = record["context"]
            text = context.get("text")

            if not isinstance(text, str) or not text.strip():

                raise ResearchBenchmarkError(
                    f"Record '{record['case_id']}' must contain "
                    "a non-empty string at context.text. "
                    "The current executor supports text-based "
                    "research cases only."
                )

            prepared_cases.append({
                "case_id": record["case_id"],
                "category": record["category"],
                "difficulty": record["difficulty"],
                "group_id": record["group_id"],
                "validation_status": record["validation_status"],
                "text": text,
                "expected": record["expected_outcome"],
                "allow_partial_metrics": True,
            })

        # ----------------------------------------------------
        # 6. Calculate input checksums
        # ----------------------------------------------------

        try:

            dataset_checksum = hashlib.sha256(
                dataset_file.read_bytes()
            ).hexdigest()

            manifest_checksum = hashlib.sha256(
                manifest_file.read_bytes()
            ).hexdigest()

        except OSError as error:

            raise ResearchBenchmarkError(
                f"Could not calculate input checksums: {error}"
            ) from error

        # ----------------------------------------------------
        # 7. Create persistent experiment record
        # ----------------------------------------------------

        experiment_id = (
            f"aegis-exp-{uuid.uuid4().hex}"
        )

        strategy_ids = list(
            self.strategy_system.get_all_strategies()
        )

        if not strategy_ids:
            raise ResearchBenchmarkError(
                "No strategies are available."
            )

        run_type = (
            "development_pilot"
            if allow_non_approved
            else "approved_research"
        )

        experiment_name = (
            f"AEGIS Research Benchmark - "
            f"{manifest['dataset_id']} "
            f"v{manifest['dataset_version']}"
        )

        experiment_configuration = {
            "trials_per_strategy": trials,
            "warmup_trials_per_strategy": warmup_trials,
            "random_seed": seed,
            "allow_non_approved": allow_non_approved,
            "strategy_ids": strategy_ids,
            "warmup_results": {},
            "case_seeds": {},
        }

        create_research_experiment(
            experiment_id=experiment_id,
            experiment_name=experiment_name,
            dataset_id=manifest["dataset_id"],
            dataset_version=manifest["dataset_version"],
            schema_version=manifest["schema_version"],
            dataset_sha256=dataset_checksum,
            manifest_sha256=manifest_checksum,
            dataset_path=str(dataset_file),
            manifest_path=str(manifest_file),
            run_type=run_type,
            manifest_status=manifest["status"],
            random_seed=seed,
            trials=trials,
            warmup_trials=warmup_trials,
            configuration=experiment_configuration,
        )

        # ----------------------------------------------------
        # 8. Execute cases and persist their results
        # ----------------------------------------------------

        case_results = []

        try:

            for index, case in enumerate(prepared_cases):

                case_seed = seed + index

                experiment_configuration[
                    "case_seeds"
                ][case["case_id"]] = case_seed

                benchmark_result = self.run_benchmark(
                    text=case["text"],
                    trials=trials,
                    warmup_trials=warmup_trials,
                    seed=case_seed,
                    benchmark_case=case,
                )

                # Save the completed case.
                save_research_case_result(
                    experiment_id=experiment_id,
                    case_id=case["case_id"],
                    category=case["category"],
                    difficulty=case["difficulty"],
                    group_id=case["group_id"],
                    validation_status=case["validation_status"],
                    expected_outcome=case["expected"],
                    case_status="completed",
                )

                # Persist measured trials for every strategy.
                for strategy_id, strategy_result in (
                    benchmark_result["results"].items()
                ):

                    # Individual warm-up measurements are not
                    # part of the measured trial dataset.
                    experiment_configuration[
                        "warmup_results"
                    ].setdefault(
                        case["case_id"], {}
                    )[strategy_id] = {
                        "successful_runs": strategy_result[
                            "warmup_successful_runs"
                        ],
                        "failed_runs": strategy_result[
                            "warmup_failed_runs"
                        ],
                    }

                    for trial_result in strategy_result[
                        "trial_results"
                    ]:

                        # Preserve execution errors separately
                        # from evaluation errors in the runner.
                        error_type = (
                            trial_result["error_type"]
                            or trial_result[
                                "evaluation_error_type"
                            ]
                        )

                        error_message = (
                            trial_result["error"]
                            or trial_result["evaluation_error"]
                        )

                        save_research_trial_result(
                            experiment_id=experiment_id,
                            case_id=case["case_id"],
                            strategy_id=strategy_id,
                            trial_number=trial_result["trial"],
                            is_warmup=False,
                            execution_success=trial_result[
                                "execution_success"
                            ],
                            is_correct=trial_result["correct"],
                            execution_time_seconds=trial_result[
                                "execution_time"
                            ],
                            error_type=error_type,
                            error_message=error_message,
                            execution_details=trial_result.get(
                                "execution_details"
                            ),
                        )

                case_results.append({
                    "case_id": case["case_id"],
                    "category": case["category"],
                    "difficulty": case["difficulty"],
                    "group_id": case["group_id"],
                    "validation_status": case["validation_status"],
                    "expected": case["expected"],
                    "benchmark": benchmark_result,
                })

            # Save the final configuration, including warm-up
            # summaries and the deterministic case seed mapping.
            update_research_experiment_configuration(
                experiment_id=experiment_id,
                configuration=experiment_configuration,
            )

            # Mark the experiment completed only after all
            # case and measured trial records have been saved.
            update_research_experiment_status(
                experiment_id=experiment_id,
                status="completed",
                total_cases=len(case_results),
            )

        except Exception as error:

            # Preserve the failed experiment in the database.
            try:

                update_research_experiment_configuration(
                    experiment_id=experiment_id,
                    configuration=experiment_configuration,
                )

                update_research_experiment_status(
                    experiment_id=experiment_id,
                    status="failed",
                    total_cases=len(case_results),
                    error_message=(
                        f"{type(error).__name__}: {error}"
                    ),
                )

            except Exception:
                # Do not replace the original benchmark error
                # with a secondary database update error.
                pass

            raise

        # ----------------------------------------------------
        # 9. Return reproducible research metadata
        # ----------------------------------------------------

        return {
            "experiment_id": experiment_id,
            "experiment_name": experiment_name,
            "experiment_status": "completed",
            "run_type": run_type,
            "dataset_id": manifest["dataset_id"],
            "dataset_version": manifest["dataset_version"],
            "schema_version": manifest["schema_version"],
            "manifest_status": manifest["status"],
            "dataset_path": str(dataset_file),
            "manifest_path": str(manifest_file),
            "dataset_sha256": dataset_checksum,
            "manifest_sha256": manifest_checksum,
            "total_cases": len(case_results),
            "total_strategies": len(strategy_ids),
            "trials_per_strategy": trials,
            "warmup_trials_per_strategy": warmup_trials,
            "random_seed": seed,
            "allow_non_approved": allow_non_approved,
            "validation_status_counts": dict(
                sorted(validation_status_counts.items())
            ),
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

                # Metadata is absent if execution fails.
                execution_details = None

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
                    evaluation_error_type = None

                    trial_error = str(error)
                    trial_error_type = type(error).__name__

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

                    # Capture the instrumentation metadata.
                    execution_details = execution_result.get(
                        "execution_details"
                    )

                    trial_error = None
                    trial_error_type = None
                    evaluation_error_type = None

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
                        evaluation_error_type = type(error).__name__

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
                    "evaluation_error_type": evaluation_error_type,
                    "error": trial_error,
                    "error_type": trial_error_type,
                    "execution_details": execution_details,
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
