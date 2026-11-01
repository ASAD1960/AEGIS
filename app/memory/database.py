
"""
AEGIS Persistent Memory

Manages feedback and benchmark experiment storage.
"""

import sqlite3
from pathlib import Path


DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "aegis.db"


def get_connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DATABASE_PATH)


def initialize_database():

    with get_connection() as connection:

        # User feedback storage.
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

        # Benchmark experiment storage.
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
