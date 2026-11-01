import json

import pytest

from app.benchmark.dataset_generator import (
    DatasetGenerationError,
    DatasetGenerator,
    ScenarioFamily,
)


def valid_builder(index, difficulty, rng):
    return {
        "task": f"Calculate the result for test case {index}.",
        "context": {"input": index},
        "expected_outcome": {"value": index},
        "success_criteria": [
            "The output contains the correct value."
        ],
        "allowed_tools": [],
    }


def make_family(
    category="basic_execution",
    family_id="test_family",
    builder=valid_builder,
):
    return ScenarioFamily(
        category=category,
        family_id=family_id,
        description="Test scenario family.",
        builder=builder,
    )


def test_generates_requested_number_of_records():
    generator = DatasetGenerator([make_family()])

    records, summary = generator.generate_records(10)

    assert len(records) == 10
    assert summary.total_records == 10


def test_generation_is_reproducible():
    generator = DatasetGenerator(
        [make_family()],
        random_seed=42,
    )

    first, _ = generator.generate_records(20)
    second, _ = generator.generate_records(20)

    assert first == second


def test_different_seeds_produce_different_schedules():
    family = make_family()

    first, _ = DatasetGenerator(
        [family],
        random_seed=42,
    ).generate_records(30)

    second, _ = DatasetGenerator(
        [family],
        random_seed=99,
    ).generate_records(30)

    assert first != second


def test_difficulty_distribution():
    generator = DatasetGenerator([make_family()])

    records, summary = generator.generate_records(15)

    assert summary.difficulty_counts == {
        "advanced": 3,
        "basic": 6,
        "intermediate": 6,
    }

    assert len(records) == 15


def test_all_records_remain_drafts():
    generator = DatasetGenerator([make_family()])

    records, _ = generator.generate_records(10)

    assert all(
        record["validation_status"] == "draft"
        for record in records
    )


def test_case_ids_are_unique():
    generator = DatasetGenerator([make_family()])

    records, _ = generator.generate_records(25)

    case_ids = [record["case_id"] for record in records]

    assert len(case_ids) == len(set(case_ids))


def test_records_are_assigned_to_groups():
    generator = DatasetGenerator(
        [make_family()],
        group_size=5,
    )

    records, _ = generator.generate_records(15)

    groups = {
        record["group_id"]
        for record in records
    }

    assert len(groups) == 3


def test_each_group_has_expected_size():
    generator = DatasetGenerator(
        [make_family()],
        group_size=5,
    )

    records, _ = generator.generate_records(15)

    group_sizes = {}

    for record in records:
        group = record["group_id"]
        group_sizes[group] = group_sizes.get(group, 0) + 1

    assert sorted(group_sizes.values()) == [5, 5, 5]


def test_reserved_case_id_is_rejected():
    generator = DatasetGenerator([make_family()])

    with pytest.raises(
        DatasetGenerationError,
        match="Duplicate case_id",
    ):
        generator.generate_records(
            5,
            reserved_case_ids={
                "basic_execution_test_family_0001"
            },
        )


def test_empty_family_registry_is_rejected():
    generator = DatasetGenerator()

    with pytest.raises(
        DatasetGenerationError,
        match="No scenario families",
    ):
        generator.generate_records(5)


@pytest.mark.parametrize("count", [0, -1, True, 1.5])
def test_invalid_variant_count_is_rejected(count):
    generator = DatasetGenerator([make_family()])

    with pytest.raises(ValueError):
        generator.generate_records(count)


@pytest.mark.parametrize("seed", [True, "42", 3.5])
def test_invalid_random_seed_is_rejected(seed):
    with pytest.raises(ValueError):
        DatasetGenerator(random_seed=seed)


@pytest.mark.parametrize("size", [0, -1, True, 2.5])
def test_invalid_group_size_is_rejected(size):
    with pytest.raises(ValueError):
        DatasetGenerator(group_size=size)


def test_invalid_category_is_rejected():
    with pytest.raises(
        DatasetGenerationError,
        match="Unsupported category",
    ):
        DatasetGenerator([
            make_family(category="unknown_category")
        ])


def test_duplicate_family_registration_is_rejected():
    generator = DatasetGenerator([make_family()])

    with pytest.raises(
        DatasetGenerationError,
        match="already registered",
    ):
        generator.register_family(make_family())


def test_invalid_family_id_is_rejected():
    with pytest.raises(
        DatasetGenerationError,
        match="Invalid family_id",
    ):
        DatasetGenerator([
            make_family(family_id="Invalid Family")
        ])


def test_builder_returning_non_dictionary_is_rejected():
    def invalid_builder(index, difficulty, rng):
        return "not a dictionary"

    generator = DatasetGenerator([
        make_family(builder=invalid_builder)
    ])

    with pytest.raises(
        DatasetGenerationError,
        match="must return a dictionary",
    ):
        generator.generate_records(1)


def test_builder_exception_is_wrapped():
    def failing_builder(index, difficulty, rng):
        raise RuntimeError("Intentional test failure")

    generator = DatasetGenerator([
        make_family(builder=failing_builder)
    ])

    with pytest.raises(
        DatasetGenerationError,
        match="Scenario builder failed",
    ):
        generator.generate_records(1)


def test_invalid_generated_record_is_rejected():
    def invalid_builder(index, difficulty, rng):
        return {
            "task": "",
            "context": {},
            "expected_outcome": {},
            "success_criteria": [],
            "allowed_tools": [],
        }

    generator = DatasetGenerator([
        make_family(builder=invalid_builder)
    ])

    with pytest.raises(
        DatasetGenerationError,
        match="failed validation",
    ):
        generator.generate_records(1)


def test_jsonl_writer_creates_valid_file(tmp_path):
    generator = DatasetGenerator([make_family()])

    records, _ = generator.generate_records(3)

    output = tmp_path / "generated.jsonl"

    result = generator.write_jsonl(records, output)

    assert result == output
    assert output.exists()

    loaded = [
        json.loads(line)
        for line in output.read_text(encoding="utf-8").splitlines()
    ]

    assert len(loaded) == 3
    assert loaded == records


def test_jsonl_writer_protects_existing_file(tmp_path):
    output = tmp_path / "generated.jsonl"
    output.write_text("original content", encoding="utf-8")

    with pytest.raises(
        DatasetGenerationError,
        match="refusing to overwrite",
    ):
        DatasetGenerator.write_jsonl([], output)

    assert output.read_text(encoding="utf-8") == "original content"


def test_jsonl_writer_supports_explicit_overwrite(tmp_path):
    output = tmp_path / "generated.jsonl"
    output.write_text("old content", encoding="utf-8")

    records = [{
        "case_id": "test_001",
        "value": 42,
    }]

    DatasetGenerator.write_jsonl(
        records,
        output,
        overwrite=True,
    )

    loaded = json.loads(
        output.read_text(encoding="utf-8").strip()
    )

    assert loaded == records[0]


def test_jsonl_writer_rejects_non_finite_numbers(tmp_path):
    output = tmp_path / "invalid.jsonl"

    with pytest.raises(
        DatasetGenerationError,
        match="Could not write dataset",
    ):
        DatasetGenerator.write_jsonl(
            [{"value": float("nan")}],
            output,
        )

    assert not output.exists()