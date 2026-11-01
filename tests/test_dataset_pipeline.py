
import json

import pytest

import app.benchmark.dataset_pipeline as pipeline_module

from app.benchmark.dataset_pipeline import (
    DatasetPipelineError,
    build_dataset_splits,
)


@pytest.fixture
def research_records():
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
            "case_id": f"research_{index:03d}",
            "category": categories[index % len(categories)],
            "difficulty": "intermediate",
            "task": f"Complete research task number {index}.",
            "context": {
                "available_resources": ["tool_a", "tool_b"]
            },
            "expected_outcome": {
                "result": f"expected_result_{index}"
            },
            "success_criteria": [
                f"Criterion one for task {index}.",
                f"Criterion two for task {index}.",
            ],
            "allowed_tools": ["tool_a", "tool_b"],
            "source": "human_authored",
            "license": "CC0-1.0",
            "group_id": f"research_group_{index // 2:03d}",
            "validation_status": "approved",
        })

    return records


@pytest.fixture
def manifest_data():
    return {
        "dataset_name": "AEGIS Test Research Dataset",
        "dataset_id": "aegis-test-v1",
        "dataset_version": "0.1.0",
        "schema_version": "0.1.0",
        "categories": [
            "basic_execution",
            "multi_step_planning",
            "memory_retrieval",
            "tool_selection",
            "failure_recovery",
            "feedback_adaptation",
        ],
        "data_splits": {
            "strategy": "group_aware",
            "train": 0.70,
            "validation": 0.15,
            "test": 0.15,
            "random_seed": 42,
        },
    }


@pytest.fixture
def pipeline_files(tmp_path, research_records, manifest_data):
    source = tmp_path / "research.jsonl"
    manifest = tmp_path / "manifest.json"
    output = tmp_path / "output"

    source.write_text(
        "\n".join(
            json.dumps(record)
            for record in research_records
        ) + "\n",
        encoding="utf-8",
    )

    manifest.write_text(
        json.dumps(manifest_data, indent=2),
        encoding="utf-8",
    )

    return source, manifest, output


def _output_files(output):
    """Return all four generated pipeline output paths."""

    return [
        output / "training" / "train.jsonl",
        output / "validation" / "validation.jsonl",
        output / "testing" / "test.jsonl",
        output / "split_metadata.json",
    ]


def test_pipeline_creates_all_three_splits(pipeline_files):
    source, manifest, output = pipeline_files

    metadata = build_dataset_splits(
        source,
        manifest,
        output,
    )

    assert (output / "training" / "train.jsonl").is_file()
    assert (output / "validation" / "validation.jsonl").is_file()
    assert (output / "testing" / "test.jsonl").is_file()
    assert (output / "split_metadata.json").is_file()

    assert metadata["leakage_check"] == "passed"


def test_pipeline_preserves_every_input_record(pipeline_files):
    source, manifest, output = pipeline_files

    build_dataset_splits(source, manifest, output)

    split_files = [
        output / "training" / "train.jsonl",
        output / "validation" / "validation.jsonl",
        output / "testing" / "test.jsonl",
    ]

    split_ids = []

    for path in split_files:
        records = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
        ]
        split_ids.extend(record["case_id"] for record in records)

    original_records = [
        json.loads(line)
        for line in source.read_text(encoding="utf-8").splitlines()
    ]

    original_ids = {record["case_id"] for record in original_records}

    assert len(split_ids) == len(original_ids)
    assert set(split_ids) == original_ids


def test_pipeline_metadata_contains_reproducibility_information(
    pipeline_files,
):
    source, manifest, output = pipeline_files

    metadata = build_dataset_splits(
        source,
        manifest,
        output,
    )

    assert metadata["dataset_id"] == "aegis-test-v1"
    assert metadata["dataset_version"] == "0.1.0"
    assert metadata["seed"] == 42
    assert metadata["split_strategy"] == "group_aware"
    assert len(metadata["source_sha256"]) == 64
    assert sum(metadata["record_counts"].values()) == 30


def test_pipeline_prevents_group_leakage(pipeline_files):
    source, manifest, output = pipeline_files

    build_dataset_splits(source, manifest, output)

    metadata = json.loads(
        (output / "split_metadata.json").read_text(encoding="utf-8")
    )

    assignments = metadata["group_assignments"]

    assert len(assignments) == 15
    assert set(assignments.values()) == {
        "train",
        "validation",
        "test",
    }


def test_pipeline_rejects_unapproved_records(
    pipeline_files,
    research_records,
):
    source, manifest, output = pipeline_files

    research_records[0]["validation_status"] = "reviewed"

    source.write_text(
        "\n".join(
            json.dumps(record)
            for record in research_records
        ) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        DatasetPipelineError,
        match="not approved",
    ):
        build_dataset_splits(source, manifest, output)


def test_pipeline_rejects_unknown_categories(
    pipeline_files,
    manifest_data,
):
    source, manifest, output = pipeline_files

    manifest_data["categories"].remove("basic_execution")

    manifest.write_text(
        json.dumps(manifest_data),
        encoding="utf-8",
    )

    with pytest.raises(
        DatasetPipelineError,
        match="not declared",
    ):
        build_dataset_splits(source, manifest, output)


def test_pipeline_rejects_invalid_manifest(pipeline_files):
    source, manifest, output = pipeline_files

    manifest.write_text(
        "{invalid json",
        encoding="utf-8",
    )

    with pytest.raises(DatasetPipelineError, match="valid UTF-8 JSON"):
        build_dataset_splits(source, manifest, output)


def test_pipeline_rejects_missing_input_file(pipeline_files):
    source, manifest, output = pipeline_files

    with pytest.raises(DatasetPipelineError, match="not found"):
        build_dataset_splits(
            source.parent / "missing.jsonl",
            manifest,
            output,
        )


def test_pipeline_protects_existing_outputs(pipeline_files):
    source, manifest, output = pipeline_files

    build_dataset_splits(source, manifest, output)

    original_metadata = (
        output / "split_metadata.json"
    ).read_text(encoding="utf-8")

    with pytest.raises(
        DatasetPipelineError,
        match="already exist",
    ):
        build_dataset_splits(source, manifest, output)

    assert (
        output / "split_metadata.json"
    ).read_text(encoding="utf-8") == original_metadata


def test_pipeline_allows_explicit_overwrite(pipeline_files):
    source, manifest, output = pipeline_files

    build_dataset_splits(source, manifest, output)

    metadata = build_dataset_splits(
        source,
        manifest,
        output,
        overwrite=True,
    )

    assert metadata["leakage_check"] == "passed"


def test_pipeline_rejects_invalid_split_strategy(
    pipeline_files,
    manifest_data,
):
    source, manifest, output = pipeline_files

    manifest_data["data_splits"]["strategy"] = "random"

    manifest.write_text(
        json.dumps(manifest_data),
        encoding="utf-8",
    )

    with pytest.raises(
        DatasetPipelineError,
        match="group_aware",
    ):
        build_dataset_splits(source, manifest, output)


def test_pipeline_restores_all_original_outputs_after_install_failure(
    pipeline_files,
    monkeypatch,
):
    source, manifest, output = pipeline_files

    build_dataset_splits(source, manifest, output)

    destinations = _output_files(output)

    original_contents = {}

    for index, path in enumerate(destinations):
        content = f"original-output-{index}"
        path.write_text(content, encoding="utf-8")
        original_contents[path] = content

    real_replace = pipeline_module.os.replace
    replace_calls = 0

    def failing_replace(source_path, destination_path):
        nonlocal replace_calls
        replace_calls += 1

        # Four calls back up the original files.
        # Fail on the second new-file installation.
        if replace_calls == 6:
            raise OSError("Simulated installation failure")

        return real_replace(source_path, destination_path)

    monkeypatch.setattr(
        pipeline_module.os,
        "replace",
        failing_replace,
    )

    # The pipeline wraps installation OSErrors in DatasetPipelineError.
    with pytest.raises(
        DatasetPipelineError,
        match="Could not prepare dataset outputs",
    ):
        build_dataset_splits(
            source,
            manifest,
            output,
            overwrite=True,
        )

    for path, expected_content in original_contents.items():
        assert path.read_text(encoding="utf-8") == expected_content

    assert not list(output.rglob("*_backup_*.tmp"))
    assert not list(output.rglob("*.tmp"))


def test_pipeline_preserves_backups_when_rollback_fails(
    pipeline_files,
    monkeypatch,
):
    source, manifest, output = pipeline_files

    build_dataset_splits(source, manifest, output)

    destinations = _output_files(output)

    original_contents = {}

    for index, path in enumerate(destinations):
        content = f"recovery-original-{index}"
        path.write_text(content, encoding="utf-8")
        original_contents[path] = content

    real_replace = pipeline_module.os.replace
    replace_calls = 0

    def failing_replace(source_path, destination_path):
        nonlocal replace_calls
        replace_calls += 1

        # Calls 1-4 back up the existing files.
        # Call 5 fails during installation.
        # Call 6 fails during the first backup restoration.
        if replace_calls in (5, 6):
            raise OSError(
                f"Simulated replacement failure {replace_calls}"
            )

        return real_replace(source_path, destination_path)

    monkeypatch.setattr(
        pipeline_module.os,
        "replace",
        failing_replace,
    )

    with pytest.raises(
        DatasetPipelineError,
        match="rollback was incomplete",
    ):
        build_dataset_splits(
            source,
            manifest,
            output,
            overwrite=True,
        )

    backup_files = list(output.rglob("*_backup_*.tmp"))

    assert backup_files, "Recovery backup files were not preserved."

    preserved_content = [
        path.read_text(encoding="utf-8")
        for path in backup_files
    ]

    assert any(
        content in original_contents.values()
        for content in preserved_content
    )


def test_pipeline_cleans_temporary_files_after_write_failure(
    pipeline_files,
    monkeypatch,
):
    source, manifest, output = pipeline_files

    real_write_jsonl = pipeline_module._write_jsonl

    def failing_write(file_path, records):
        real_write_jsonl(file_path, records)
        raise OSError("Simulated dataset write failure")

    monkeypatch.setattr(
        pipeline_module,
        "_write_jsonl",
        failing_write,
    )

    with pytest.raises(
        DatasetPipelineError,
        match="Could not prepare dataset outputs",
    ):
        build_dataset_splits(source, manifest, output)

    assert not list(output.rglob("*.tmp"))

    assert not (output / "training" / "train.jsonl").exists()
    assert not (output / "validation" / "validation.jsonl").exists()
    assert not (output / "testing" / "test.jsonl").exists()
    assert not (output / "split_metadata.json").exists()
