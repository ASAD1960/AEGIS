
import json

import pytest

from app.benchmark.dataset_validator import (
    DatasetValidator,
    DatasetValidationError,
    REQUIRED_FIELDS,
)


@pytest.fixture
def validator():
    return DatasetValidator()


@pytest.fixture
def valid_record():
    return {
        "case_id": "planning_001",
        "category": "multi_step_planning",
        "difficulty": "intermediate",
        "task": "Plan a sequence of three independent operations.",
        "context": {
            "available_resources": ["tool_a", "tool_b"]
        },
        "expected_outcome": {
            "plan": ["operation_a", "operation_b", "operation_c"]
        },
        "success_criteria": [
            "All operations are included.",
            "Dependencies are respected."
        ],
        "allowed_tools": ["tool_a", "tool_b"],
        "source": "human_authored",
        "license": "CC0-1.0",
        "group_id": "planning_group_001",
        "validation_status": "reviewed",
    }


def write_jsonl(path, records):
    path.write_text(
        "\n".join(
            json.dumps(record)
            for record in records
        ),
        encoding="utf-8",
    )


def test_valid_record_passes(validator, valid_record):
    issues, warnings = validator.validate_record(valid_record)

    assert issues == []
    assert warnings == []


def test_all_required_fields_are_defined():
    assert "case_id" in REQUIRED_FIELDS
    assert "expected_outcome" in REQUIRED_FIELDS
    assert "license" in REQUIRED_FIELDS


def test_non_dictionary_record_fails(validator):
    issues, _ = validator.validate_record("invalid")

    assert issues[0].code == "INVALID_RECORD_TYPE"


def test_missing_required_field_fails(validator, valid_record):
    del valid_record["case_id"]

    issues, _ = validator.validate_record(valid_record)

    assert any(
        issue.code == "MISSING_REQUIRED_FIELD"
        for issue in issues
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("category", "unknown_category"),
        ("difficulty", "expert"),
        ("validation_status", "unverified"),
    ],
)
def test_invalid_controlled_values_fail(
    validator,
    valid_record,
    field,
    value,
):
    valid_record[field] = value

    issues, _ = validator.validate_record(valid_record)

    assert issues


def test_empty_task_fails(validator, valid_record):
    valid_record["task"] = "   "

    issues, _ = validator.validate_record(valid_record)

    assert any(issue.code == "INVALID_TASK" for issue in issues)


def test_invalid_context_fails(validator, valid_record):
    valid_record["context"] = []

    issues, _ = validator.validate_record(valid_record)

    assert any(issue.code == "INVALID_CONTEXT" for issue in issues)


def test_empty_expected_outcome_fails(validator, valid_record):
    valid_record["expected_outcome"] = {}

    issues, _ = validator.validate_record(valid_record)

    assert any(
        issue.code == "INVALID_EXPECTED_OUTCOME"
        for issue in issues
    )


def test_empty_success_criteria_fails(validator, valid_record):
    valid_record["success_criteria"] = []

    issues, _ = validator.validate_record(valid_record)

    assert any(
        issue.code == "INVALID_SUCCESS_CRITERIA"
        for issue in issues
    )


def test_duplicate_success_criteria_fails(validator, valid_record):
    valid_record["success_criteria"] = ["same", "same"]

    issues, _ = validator.validate_record(valid_record)

    assert any(
        issue.code == "DUPLICATE_SUCCESS_CRITERIA"
        for issue in issues
    )


def test_duplicate_allowed_tools_fail(validator, valid_record):
    valid_record["allowed_tools"] = ["tool_a", "tool_a"]

    issues, _ = validator.validate_record(valid_record)

    assert any(
        issue.code == "DUPLICATE_ALLOWED_TOOLS"
        for issue in issues
    )


def test_unknown_field_generates_warning(validator, valid_record):
    valid_record["future_field"] = "future value"

    issues, warnings = validator.validate_record(valid_record)

    assert issues == []
    assert warnings[0].code == "UNKNOWN_FIELD"


def test_valid_jsonl_loads_records(
    validator,
    valid_record,
    tmp_path,
):
    path = tmp_path / "dataset.jsonl"

    write_jsonl(path, [valid_record])

    records = validator.load_jsonl(path)

    assert len(records) == 1
    assert records[0]["case_id"] == "planning_001"


def test_duplicate_case_ids_fail(
    validator,
    valid_record,
    tmp_path,
):
    second_record = valid_record.copy()
    second_record["task"] = "A different task."

    path = tmp_path / "duplicates.jsonl"

    write_jsonl(path, [valid_record, second_record])

    with pytest.raises(DatasetValidationError) as error:
        validator.load_jsonl(path)

    assert "DUPLICATE_CASE_ID" in str(error.value)


def test_duplicate_json_keys_fail(
    validator,
    valid_record,
    tmp_path,
):
    path = tmp_path / "duplicate_keys.jsonl"

    path.write_text(
        '{"case_id":"first","case_id":"second"}',
        encoding="utf-8",
    )

    report, records = validator.validate_file(path)

    assert not report.is_valid
    assert records == []
    assert report.issues[0].code == "INVALID_JSON"


def test_malformed_json_fails(
    validator,
    tmp_path,
):
    path = tmp_path / "malformed.jsonl"

    path.write_text(
        '{"case_id": "broken"',
        encoding="utf-8",
    )

    report, records = validator.validate_file(path)

    assert not report.is_valid
    assert records == []


def test_nonstandard_nan_fails(
    validator,
    tmp_path,
):
    path = tmp_path / "nan.jsonl"

    path.write_text(
        '{"value": NaN}',
        encoding="utf-8",
    )

    report, _ = validator.validate_file(path)

    assert any(
        issue.code == "INVALID_JSON"
        for issue in report.issues
    )


def test_utf8_bom_is_supported(
    validator,
    valid_record,
    tmp_path,
):
    path = tmp_path / "utf8_bom.jsonl"

    path.write_text(
        json.dumps(valid_record),
        encoding="utf-8-sig",
    )

    records = validator.load_jsonl(path)

    assert records[0]["case_id"] == "planning_001"


def test_empty_lines_generate_warnings(
    validator,
    valid_record,
    tmp_path,
):
    path = tmp_path / "empty_lines.jsonl"

    path.write_text(
        json.dumps(valid_record) + "\n\n",
        encoding="utf-8",
    )

    report, records = validator.validate_file(path)

    assert report.is_valid
    assert len(records) == 1
    assert report.warning_count == 1


def test_missing_file_returns_validation_report(
    validator,
    tmp_path,
):
    path = tmp_path / "missing.jsonl"

    report, records = validator.validate_file(path)

    assert not report.is_valid
    assert records == []
    assert report.issues[0].code == "FILE_NOT_FOUND"


def test_report_serializes_to_dictionary(
    validator,
    valid_record,
    tmp_path,
):
    path = tmp_path / "report.jsonl"

    write_jsonl(path, [valid_record])

    report, _ = validator.validate_file(path)

    result = report.to_dict()

    assert result["is_valid"] is True
    assert result["total_records"] == 1
    assert result["valid_records"] == 1
    assert result["error_count"] == 0


def test_line_number_is_preserved(
    validator,
    tmp_path,
):
    path = tmp_path / "line_numbers.jsonl"

    path.write_text(
        '{"broken": true}\n',
        encoding="utf-8",
    )

    report, _ = validator.validate_file(path)

    assert report.issues[0].line_number == 1
