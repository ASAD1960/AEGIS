
from app.memory.database import (
    initialize_database,
    get_connection,
)

initialize_database()

with get_connection() as connection:

    feedback_count = connection.execute(
        "SELECT COUNT(*) FROM feedback"
    ).fetchone()[0]

    benchmark_records = connection.execute(
        """
        SELECT
            id,
            strategy_id,
            total_trials,
            successful_runs,
            failed_runs,
            correct
        FROM benchmark_results
        ORDER BY id
        """
    ).fetchall()

    print("Feedback records:", feedback_count)
    print("\nSaved benchmark experiments:")

    for record in benchmark_records:
        print(record)

    print("\nTotal benchmark records:", len(benchmark_records))
