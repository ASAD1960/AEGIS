
"""
AEGIS Persistent Memory

Manages user feedback, legacy benchmark results,
and reproducible research experiment storage.
"""
import json
import sqlite3
from pathlib import Path
import sqlite3
from pathlib import Path


DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "aegis.db"


def get_connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database():

    with get_connection() as connection:

        # --------------------------------------------------
        # Existing user feedback storage.
        # --------------------------------------------------

        connection.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                comment TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        columns = [
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(feedback)"
            ).fetchall()
        ]

        if "strategy_id" not in columns:
            connection.execute("""
                ALTER TABLE feedback
                ADD COLUMN strategy_id TEXT
            """)

        # --------------------------------------------------
        # Existing legacy benchmark storage.
        # --------------------------------------------------

        connection.execute("""
            CREATE TABLE IF NOT EXISTS benchmark_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                strategy_id TEXT NOT NULL,
                total_trials INTEGER NOT NULL,
                successful_runs INTEGER NOT NULL,
                failed_runs INTEGER NOT NULL,
                average_execution_time REAL NOT NULL,
                correct INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # --------------------------------------------------
        # New research experiment storage.
        # --------------------------------------------------

        connection.execute("""
            CREATE TABLE IF NOT EXISTS research_experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT NOT NULL UNIQUE,
                experiment_name TEXT NOT NULL,
                dataset_id TEXT NOT NULL,
                dataset_version TEXT NOT NULL,
                schema_version TEXT NOT NULL,
                dataset_sha256 TEXT NOT NULL,
                manifest_sha256 TEXT NOT NULL,
                dataset_path TEXT NOT NULL,
                manifest_path TEXT NOT NULL,
                run_type TEXT NOT NULL,
                manifest_status TEXT NOT NULL,
                random_seed INTEGER NOT NULL,
                trials INTEGER NOT NULL,
                warmup_trials INTEGER NOT NULL,
                configuration_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'running',
                total_cases INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                error_message TEXT
            )
        """)

        # --------------------------------------------------
        # Individual research case results.
        # --------------------------------------------------

        connection.execute("""
            CREATE TABLE IF NOT EXISTS research_case_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT NOT NULL,
                case_id TEXT NOT NULL,
                category TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                group_id TEXT NOT NULL,
                validation_status TEXT NOT NULL,
                expected_outcome_json TEXT NOT NULL,
                case_status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                UNIQUE (experiment_id, case_id),

                FOREIGN KEY (experiment_id)
                    REFERENCES research_experiments(experiment_id)
                    ON DELETE CASCADE
            )
        """)

        # --------------------------------------------------
        # Individual strategy trial results.
        # --------------------------------------------------

        connection.execute("""
            CREATE TABLE IF NOT EXISTS research_trial_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT NOT NULL,
                case_id TEXT NOT NULL,
                strategy_id TEXT NOT NULL,
                trial_number INTEGER NOT NULL,
                is_warmup INTEGER NOT NULL DEFAULT 0,
                execution_success INTEGER NOT NULL,
                is_correct INTEGER NOT NULL,
                execution_time_seconds REAL,
                error_type TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (experiment_id, case_id)
                    REFERENCES research_case_results(
                        experiment_id,
                        case_id
                    )
                    ON DELETE CASCADE
            )
        """)

        # --------------------------------------------------
        # Research query indexes.
        # --------------------------------------------------

        connection.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_research_cases_experiment
            ON research_case_results(experiment_id)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_research_cases_category
            ON research_case_results(category, difficulty)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_research_trials_experiment
            ON research_trial_results(experiment_id)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_research_trials_strategy
            ON research_trial_results(strategy_id)
        """)


# ==========================================================
# Existing feedback functions.
# ==========================================================

def save_feedback(task, rating, comment="", strategy_id=None):

    if not isinstance(task, str) or not task.strip():
        raise ValueError("Task must be a non-empty string.")

    if type(rating) is not int or not 1 <= rating <= 5:
        raise ValueError("Rating must be an integer between 1 and 5.")

    with get_connection() as connection:

        cursor = connection.execute(
            """
            INSERT INTO feedback
            (task, rating, comment, strategy_id)
            VALUES (?, ?, ?, ?)
            """,
            (task, rating, comment, strategy_id),
        )

        return cursor.lastrowid


def get_all_feedback():

    with get_connection() as connection:

        cursor = connection.execute("""
            SELECT id, task, rating, comment,
                   created_at, strategy_id
            FROM feedback
            ORDER BY id
        """)

        return cursor.fetchall()


# ==========================================================
# Existing legacy benchmark functions.
# ==========================================================

def save_benchmark_result(
    task,
    strategy_id,
    total_trials,
    successful_runs,
    failed_runs,
    average_execution_time,
    correct,
):

    if not isinstance(task, str) or not task.strip():
        raise ValueError("Task must be a non-empty string.")

    if not isinstance(strategy_id, str) or not strategy_id.strip():
        raise ValueError("Strategy ID must be a non-empty string.")

    if type(total_trials) is not int or total_trials < 1:
        raise ValueError("Total trials must be a positive integer.")

    if (
        type(successful_runs) is not int
        or type(failed_runs) is not int
        or successful_runs < 0
        or failed_runs < 0
        or successful_runs + failed_runs != total_trials
    ):
        raise ValueError("Run counts must be valid and match total trials.")

    if (
        not isinstance(average_execution_time, (int, float))
        or isinstance(average_execution_time, bool)
        or average_execution_time < 0
    ):
        raise ValueError("Execution time must be a non-negative number.")

    if type(correct) is not bool:
        raise ValueError("Correct must be True or False.")

    with get_connection() as connection:

        cursor = connection.execute(
            """
            INSERT INTO benchmark_results (
                task,
                strategy_id,
                total_trials,
                successful_runs,
                failed_runs,
                average_execution_time,
                correct
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task,
                strategy_id,
                total_trials,
                successful_runs,
                failed_runs,
                average_execution_time,
                int(correct),
            ),
        )

        return cursor.lastrowid


def get_all_benchmark_results():

    with get_connection() as connection:

        cursor = connection.execute("""
            SELECT id, task, strategy_id, total_trials,
                   successful_runs, failed_runs,
                   average_execution_time, correct, created_at
            FROM benchmark_results
            ORDER BY id
        """)

        return cursor.fetchall()

# ==========================================================
# Research experiment persistence.
# ==========================================================

def create_research_experiment(
    experiment_id,
    experiment_name,
    dataset_id,
    dataset_version,
    schema_version,
    dataset_sha256,
    manifest_sha256,
    dataset_path,
    manifest_path,
    run_type,
    manifest_status,
    random_seed,
    trials,
    warmup_trials,
    configuration,
):
    """Create a research experiment and return its database ID."""

    required_strings = {
        "experiment_id": experiment_id,
        "experiment_name": experiment_name,
        "dataset_id": dataset_id,
        "dataset_version": dataset_version,
        "schema_version": schema_version,
        "dataset_sha256": dataset_sha256,
        "manifest_sha256": manifest_sha256,
        "dataset_path": dataset_path,
        "manifest_path": manifest_path,
        "run_type": run_type,
        "manifest_status": manifest_status,
    }

    for field, value in required_strings.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string.")

    for field, value in (
        ("dataset_sha256", dataset_sha256),
        ("manifest_sha256", manifest_sha256),
    ):
        if (
            len(value) != 64
            or any(character not in "0123456789abcdefABCDEF"
                   for character in value)
        ):
            raise ValueError(f"{field} must be a valid SHA-256 hash.")

    if type(random_seed) is not int:
        raise ValueError("Random seed must be an integer.")

    if type(trials) is not int or trials < 1:
        raise ValueError("Trials must be a positive integer.")

    if type(warmup_trials) is not int or warmup_trials < 0:
        raise ValueError("Warm-up trials must be non-negative.")

    if not isinstance(configuration, dict):
        raise ValueError("Configuration must be a dictionary.")

    try:
        configuration_json = json.dumps(
            configuration,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise ValueError("Configuration must contain valid JSON data.") from error

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO research_experiments (
                experiment_id,
                experiment_name,
                dataset_id,
                dataset_version,
                schema_version,
                dataset_sha256,
                manifest_sha256,
                dataset_path,
                manifest_path,
                run_type,
                manifest_status,
                random_seed,
                trials,
                warmup_trials,
                configuration_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                experiment_id,
                experiment_name,
                dataset_id,
                dataset_version,
                schema_version,
                dataset_sha256,
                manifest_sha256,
                dataset_path,
                manifest_path,
                run_type,
                manifest_status,
                random_seed,
                trials,
                warmup_trials,
                configuration_json,
            ),
        )

        return cursor.lastrowid


def save_research_case_result(
    experiment_id,
    case_id,
    category,
    difficulty,
    group_id,
    validation_status,
    expected_outcome,
    case_status="completed",
):
    """Save one scenario's result."""

    fields = {
        "experiment_id": experiment_id,
        "case_id": case_id,
        "category": category,
        "difficulty": difficulty,
        "group_id": group_id,
        "validation_status": validation_status,
        "case_status": case_status,
    }

    for field, value in fields.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string.")

    if not isinstance(expected_outcome, dict) or not expected_outcome:
        raise ValueError("Expected outcome must be a non-empty dictionary.")

    try:
        expected_json = json.dumps(
            expected_outcome,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise ValueError("Expected outcome must contain valid JSON data.") from error

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO research_case_results (
                experiment_id,
                case_id,
                category,
                difficulty,
                group_id,
                validation_status,
                expected_outcome_json,
                case_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                experiment_id,
                case_id,
                category,
                difficulty,
                group_id,
                validation_status,
                expected_json,
                case_status,
            ),
        )

        return cursor.lastrowid


def save_research_trial_result(
    experiment_id,
    case_id,
    strategy_id,
    trial_number,
    is_warmup,
    execution_success,
    is_correct,
    execution_time_seconds=None,
    error_type=None,
    error_message=None,
):
    """Save one individual strategy execution."""

    for field, value in (
        ("experiment_id", experiment_id),
        ("case_id", case_id),
        ("strategy_id", strategy_id),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string.")

    if type(trial_number) is not int or trial_number < 1:
        raise ValueError("Trial number must be a positive integer.")

    for field, value in (
        ("is_warmup", is_warmup),
        ("execution_success", execution_success),
        ("is_correct", is_correct),
    ):
        if type(value) is not bool:
            raise ValueError(f"{field} must be a boolean.")

    if execution_time_seconds is not None:
        if (
            not isinstance(execution_time_seconds, (int, float))
            or isinstance(execution_time_seconds, bool)
            or execution_time_seconds < 0
        ):
            raise ValueError(
                "Execution time must be a non-negative number or None."
            )

    for field, value in (
        ("error_type", error_type),
        ("error_message", error_message),
    ):
        if value is not None and not isinstance(value, str):
            raise ValueError(f"{field} must be a string or None.")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO research_trial_results (
                experiment_id,
                case_id,
                strategy_id,
                trial_number,
                is_warmup,
                execution_success,
                is_correct,
                execution_time_seconds,
                error_type,
                error_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                experiment_id,
                case_id,
                strategy_id,
                trial_number,
                int(is_warmup),
                int(execution_success),
                int(is_correct),
                execution_time_seconds,
                error_type,
                error_message,
            ),
        )

        return cursor.lastrowid


def update_research_experiment_status(
    experiment_id,
    status,
    total_cases=None,
    error_message=None,
):
    """Update experiment status and completion information."""

    if not isinstance(experiment_id, str) or not experiment_id.strip():
        raise ValueError("Experiment ID must be a non-empty string.")

    if status not in ("running", "completed", "failed"):
        raise ValueError("Invalid research experiment status.")

    if total_cases is not None:
        if type(total_cases) is not int or total_cases < 0:
            raise ValueError("Total cases must be a non-negative integer.")

    if error_message is not None and not isinstance(error_message, str):
        raise ValueError("Error message must be a string or None.")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE research_experiments
            SET status = ?,
                total_cases = COALESCE(?, total_cases),
                error_message = ?,
                completed_at = CASE
                    WHEN ? IN ('completed', 'failed')
                    THEN CURRENT_TIMESTAMP
                    ELSE NULL
                END
            WHERE experiment_id = ?
            """,
            (
                status,
                total_cases,
                error_message,
                status,
                experiment_id,
            ),
        )

        if cursor.rowcount == 0:
            raise ValueError("Research experiment was not found.")

        return True


def get_research_experiment(experiment_id):
    """Retrieve one experiment as a dictionary."""

    with get_connection() as connection:
        connection.row_factory = sqlite3.Row

        row = connection.execute(
            """
            SELECT *
            FROM research_experiments
            WHERE experiment_id = ?
            """,
            (experiment_id,),
        ).fetchone()

        return dict(row) if row else None


def get_research_case_results(experiment_id):
    """Retrieve all scenario results for an experiment."""

    with get_connection() as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute(
            """
            SELECT *
            FROM research_case_results
            WHERE experiment_id = ?
            ORDER BY case_id
            """,
            (experiment_id,),
        ).fetchall()

        return [dict(row) for row in rows]


def get_research_trial_results(experiment_id, case_id=None):
    """Retrieve individual strategy trials for an experiment."""

    with get_connection() as connection:
        connection.row_factory = sqlite3.Row

        if case_id is None:
            rows = connection.execute(
                """
                SELECT *
                FROM research_trial_results
                WHERE experiment_id = ?
                ORDER BY case_id, strategy_id, is_warmup, trial_number
                """,
                (experiment_id,),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT *
                FROM research_trial_results
                WHERE experiment_id = ? AND case_id = ?
                ORDER BY strategy_id, is_warmup, trial_number
                """,
                (experiment_id, case_id),
            ).fetchall()

        return [dict(row) for row in rows]
def update_research_experiment_configuration(
    experiment_id,
    configuration,
):
    """Update the reproducibility configuration of an experiment."""

    if not isinstance(experiment_id, str) or not experiment_id.strip():
        raise ValueError("Experiment ID must be a non-empty string.")

    if not isinstance(configuration, dict):
        raise ValueError("Configuration must be a dictionary.")

    try:
        configuration_json = json.dumps(
            configuration,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"Configuration is not valid JSON data: {error}"
        ) from error

    with get_connection() as connection:

        cursor = connection.execute(
            """
            UPDATE research_experiments
            SET configuration_json = ?
            WHERE experiment_id = ?
            """,
            (configuration_json, experiment_id),
        )

        if cursor.rowcount == 0:
            raise ValueError(
                f"Research experiment '{experiment_id}' does not exist."
            )

    return True