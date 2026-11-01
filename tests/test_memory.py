
import pytest

from app.memory.database import (
    initialize_database,
    save_feedback,
    get_all_feedback,
    save_benchmark_result,
    get_all_benchmark_results,
)


def test_database_initializes_successfully():

    initialize_database()

    assert isinstance(get_all_feedback(), list)
    assert isinstance(get_all_benchmark_results(), list)


def test_feedback_record_is_persisted():

    task = "Memory persistence verification"

    record_id = save_feedback(
        task=task,
        rating=5,
        comment="Testing persistent storage.",
        strategy_id="careful",
    )

    records = get_all_feedback()

    matching_records = [
        record for record in records
        if record[0] == record_id
    ]

    assert len(matching_records) == 1
    assert matching_records[0][1] == task
    assert matching_records[0][2] == 5
    assert matching_records[0][3] == "Testing persistent storage."
    assert matching_records[0][5] == "careful"


@pytest.mark.parametrize(
    "invalid_rating",
    [0, 6, -1, 1.5, True, "5", None],
)
def test_database_rejects_invalid_ratings(invalid_rating):

    with pytest.raises(ValueError):
        save_feedback(
            task="Invalid rating test",
            rating=invalid_rating,
            comment="This rating should be rejected.",
        )


@pytest.mark.parametrize(
    "invalid_task",
    ["", "   ", None, 123],
)
def test_database_rejects_invalid_tasks(invalid_task):

    with pytest.raises(ValueError):
        save_feedback(
            task=invalid_task,
            rating=5,
        )


def test_benchmark_result_is_persisted():

    record_id = save_benchmark_result(
        task="Memory benchmark verification",
        strategy_id="careful",
        total_trials=10,
        successful_runs=8,
        failed_runs=2,
        average_execution_time=0.025,
        correct=True,
    )

    records = get_all_benchmark_results()

    matching_records = [
        record for record in records
        if record[0] == record_id
    ]

    assert len(matching_records) == 1

    record = matching_records[0]

    assert record[1] == "Memory benchmark verification"
    assert record[2] == "careful"
    assert record[3] == 10
    assert record[4] == 8
    assert record[5] == 2
    assert record[6] == 0.025
    assert record[7] == 1


def test_benchmark_rejects_invalid_trial_counts():

    with pytest.raises(ValueError):
        save_benchmark_result(
            task="Invalid benchmark",
            strategy_id="careful",
            total_trials=10,
            successful_runs=8,
            failed_runs=1,
            average_execution_time=0.025,
            correct=True,
        )


def test_benchmark_rejects_invalid_correct_value():

    with pytest.raises(ValueError):
        save_benchmark_result(
            task="Invalid benchmark",
            strategy_id="careful",
            total_trials=10,
            successful_runs=8,
            failed_runs=2,
            average_execution_time=0.025,
            correct=1,
        )


def test_benchmark_rejects_boolean_execution_time():

    with pytest.raises(ValueError):
        save_benchmark_result(
            task="Invalid benchmark",
            strategy_id="careful",
            total_trials=10,
            successful_runs=8,
            failed_runs=2,
            average_execution_time=True,
            correct=True,
        )


def main():

    initialize_database()

    record_id = save_feedback(
        task="Build a Python function",
        rating=5,
        comment="The task was completed correctly.",
    )

    print("AEGIS Persistent Memory Test")
    print("=" * 40)

    print(f"Saved record ID: {record_id}")

    print("\nStored feedback:")

    for record in get_all_feedback():
        print(record)

    print("=" * 40)


if __name__ == "__main__":
    main()
