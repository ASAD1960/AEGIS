
import pytest

from app.benchmark.dataset_splitter import (
    DatasetSplitError,
    assert_no_group_leakage,
    split_records,
)


@pytest.fixture
def sample_records():
    records = []

    categories = [
        "basic_execution",
        "multi_step_planning",
        "memory_retrieval",
        "tool_selection",
        "failure_recovery",
        "feedback_adaptation",
    ]

    for index in range(30):
        records.append({
            "case_id": f"case_{index:03d}",
            "category": categories[index % len(categories)],
            "group_id": f"group_{index // 2:03d}",
            "task": f"Example research task {index}",
        })

    return records


def test_split_produces_three_nonempty_partitions(sample_records):
    result = split_records(sample_records)

    assert result.train
    assert result.validation
    assert result.test


def test_all_records_are_preserved(sample_records):
    result = split_records(sample_records)

    total = (
        result.train
        + result.validation
        + result.test
    )

    assert len(total) == len(sample_records)

    original_ids = {record["case_id"] for record in sample_records}
    split_ids = {record["case_id"] for record in total}

    assert original_ids == split_ids


def test_no_group_leakage(sample_records):
    result = split_records(sample_records)

    assert_no_group_leakage(result.as_dict())

    assignments = {}

    for split_name, records in result.as_dict().items():
        for record in records:
            group_id = record["group_id"]

            if group_id in assignments:
                assert assignments[group_id] == split_name
            else:
                assignments[group_id] = split_name


def test_same_seed_produces_same_assignments(sample_records):
    first = split_records(sample_records, seed=42)
    second = split_records(sample_records, seed=42)

    assert (
        first.summary.group_assignments
        == second.summary.group_assignments
    )


def test_different_input_order_preserves_assignments(sample_records):
    first = split_records(sample_records, seed=42)
    reversed_records = list(reversed(sample_records))
    second = split_records(reversed_records, seed=42)

    assert (
        first.summary.group_assignments
        == second.summary.group_assignments
    )


def test_different_seed_can_change_assignments(sample_records):
    first = split_records(sample_records, seed=42)
    second = split_records(sample_records, seed=99)

    assert (
        first.summary.group_assignments
        != second.summary.group_assignments
    )


def test_summary_counts_match_actual_splits(sample_records):
    result = split_records(sample_records)

    for name, records in result.as_dict().items():
        assert result.summary.record_counts[name] == len(records)
        assert result.summary.group_counts[name] > 0


def test_category_counts_match_actual_splits(sample_records):
    result = split_records(sample_records)

    for split_name, records in result.as_dict().items():
        actual_categories = {}

        for record in records:
            category = record["category"]
            actual_categories[category] = (
                actual_categories.get(category, 0) + 1
            )

        assert (
            result.summary.category_counts[split_name]
            == actual_categories
        )


@pytest.mark.parametrize(
    "ratios",
    [
        (0.70, 0.15, 0.10),
        (0.70, 0.20, 0.20),
        (0, 0.50, 0.50),
        (-0.10, 0.55, 0.55),
        (float("nan"), 0.50, 0.50),
        (float("inf"), 0.0, 0.0),
    ],
)
def test_invalid_ratios_are_rejected(sample_records, ratios):
    with pytest.raises(DatasetSplitError):
        split_records(
            sample_records,
            train_ratio=ratios[0],
            validation_ratio=ratios[1],
            test_ratio=ratios[2],
        )


def test_boolean_ratio_is_rejected(sample_records):
    with pytest.raises(DatasetSplitError):
        split_records(
            sample_records,
            train_ratio=True,
            validation_ratio=0.15,
            test_ratio=0.15,
        )


def test_invalid_seed_is_rejected(sample_records):
    with pytest.raises(DatasetSplitError):
        split_records(sample_records, seed="42")


def test_empty_dataset_is_rejected():
    with pytest.raises(DatasetSplitError):
        split_records([])


def test_duplicate_case_ids_are_rejected(sample_records):
    records = list(sample_records)
    records.append(dict(records[0]))

    with pytest.raises(DatasetSplitError, match="Duplicate case_id"):
        split_records(records)


@pytest.mark.parametrize(
    "field",
    ["case_id", "group_id", "category"],
)
def test_missing_required_split_field_is_rejected(sample_records, field):
    records = [dict(record) for record in sample_records]
    del records[0][field]

    with pytest.raises(DatasetSplitError):
        split_records(records)


def test_invalid_record_type_is_rejected(sample_records):
    records = list(sample_records)
    records[0] = "not a record"

    with pytest.raises(DatasetSplitError):
        split_records(records)


def test_too_few_groups_are_rejected():
    records = [
        {
            "case_id": "case_001",
            "group_id": "group_001",
            "category": "basic_execution",
        },
        {
            "case_id": "case_002",
            "group_id": "group_001",
            "category": "basic_execution",
        },
    ]

    with pytest.raises(DatasetSplitError, match="At least three"):
        split_records(records)


def test_group_leakage_detection_rejects_cross_split_group():
    splits = {
        "train": [
            {"case_id": "case_001", "group_id": "shared_group"}
        ],
        "validation": [
            {"case_id": "case_002", "group_id": "shared_group"}
        ],
        "test": [
            {"case_id": "case_003", "group_id": "test_group"}
        ],
    }

    with pytest.raises(DatasetSplitError, match="Group leakage"):
        assert_no_group_leakage(splits)


def test_split_summary_is_json_serializable(sample_records):
    import json

    result = split_records(sample_records)

    serialized = json.dumps(result.summary.to_dict())

    assert isinstance(serialized, str)
    assert '"seed": 42' in serialized
