
"""
AEGIS Research Dataset Validation Engine
=========================================

Production-oriented validation infrastructure for the
AEGIS Agent Task Benchmark.

Features:
- Strict JSONL parsing
- Duplicate JSON key detection
- Schema and type validation
- Controlled vocabulary validation
- Duplicate case ID detection
- Research provenance checks
- Structured validation issues
- Validation summaries
- UTF-8 and UTF-8 BOM support

This module uses only the Python standard library.
"""

from __future__ import annotations

import json
import re

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ============================================================
# DATASET SCHEMA
# ============================================================

DATASET_SCHEMA_VERSION = "0.1.0"

REQUIRED_FIELDS = frozenset({
    "case_id",
    "category",
    "difficulty",
    "task",
    "context",
    "expected_outcome",
    "success_criteria",
    "allowed_tools",
    "source",
    "license",
    "group_id",
    "validation_status",
})

ALLOWED_CATEGORIES = frozenset({
    "basic_execution",
    "multi_step_planning",
    "memory_retrieval",
    "tool_selection",
    "failure_recovery",
    "feedback_adaptation",
})

ALLOWED_DIFFICULTIES = frozenset({
    "basic",
    "intermediate",
    "advanced",
})

ALLOWED_VALIDATION_STATUSES = frozenset({
    "draft",
    "reviewed",
    "approved",
})

CASE_ID_PATTERN = re.compile(
    r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$"
)


# ============================================================
# VALIDATION MODELS
# ============================================================

@dataclass(frozen=True)
class ValidationIssue:
    """Represents one dataset validation issue."""

    code: str
    message: str
    severity: str
    line_number: int | None = None
    field_name: str | None = None

    def to_dict(self) -> dict[str, Any]:

        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "line_number": self.line_number,
            "field_name": self.field_name,
        }


@dataclass
class DatasetValidationReport:
    """Structured summary of a dataset validation operation."""

    dataset_path: str
    schema_version: str = DATASET_SCHEMA_VERSION

    total_records: int = 0
    valid_records: int = 0

    issues: list[ValidationIssue] = field(
        default_factory=list
    )

    warnings: list[ValidationIssue] = field(
        default_factory=list
    )

    @property
    def is_valid(self) -> bool:

        return len(self.issues) == 0

    @property
    def error_count(self) -> int:

        return len(self.issues)

    @property
    def warning_count(self) -> int:

        return len(self.warnings)

    def to_dict(self) -> dict[str, Any]:

        return {
            "dataset_path": self.dataset_path,
            "schema_version": self.schema_version,
            "is_valid": self.is_valid,
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [
                issue.to_dict()
                for issue in self.issues
            ],
            "warnings": [
                warning.to_dict()
                for warning in self.warnings
            ],
        }


class DatasetValidationError(Exception):
    """Raised when a dataset fails validation."""

    def __init__(self, report: DatasetValidationReport):

        self.report = report

        super().__init__(
            self._format_report(report)
        )

    @staticmethod
    def _format_report(report):

        lines = [
            "AEGIS dataset validation failed.",
            f"Dataset: {report.dataset_path}",
            f"Records: {report.total_records}",
            f"Errors: {report.error_count}",
            f"Warnings: {report.warning_count}",
            "",
        ]

        for issue in report.issues:

            location = (
                f"Line {issue.line_number}"
                if issue.line_number is not None
                else "Dataset"
            )

            if issue.field_name:
                location += f" | {issue.field_name}"

            lines.append(
                f"[{issue.code}] {location}: "
                f"{issue.message}"
            )

        return "\n".join(lines)


# ============================================================
# JSON PARSING SECURITY
# ============================================================

def _reject_duplicate_json_keys(pairs):

    result = {}

    for key, value in pairs:

        if key in result:
            raise ValueError(
                f"Duplicate JSON object key: '{key}'."
            )

        result[key] = value

    return result


def _reject_nonstandard_json_constant(value):

    raise ValueError(
        f"Non-standard JSON constant is not allowed: {value}."
    )


# ============================================================
# DATASET VALIDATOR
# ============================================================

class DatasetValidator:
    """
    Validates AEGIS research dataset records and JSONL files.

    Strict errors prevent invalid records from entering
    the approved dataset.
    """

    def __init__(self):

        self.schema_version = DATASET_SCHEMA_VERSION

    # --------------------------------------------------------
    # ISSUE CREATION
    # --------------------------------------------------------

    @staticmethod
    def _issue(
        code,
        message,
        severity="error",
        line_number=None,
        field_name=None,
    ):

        return ValidationIssue(
            code=code,
            message=message,
            severity=severity,
            line_number=line_number,
            field_name=field_name,
        )

    # --------------------------------------------------------
    # INDIVIDUAL RECORD VALIDATION
    # --------------------------------------------------------

    def validate_record(self, record, record_number=1):

        issues = []
        warnings = []

        if not isinstance(record, dict):

            issues.append(
                self._issue(
                    "INVALID_RECORD_TYPE",
                    "Each dataset record must be a JSON object.",
                    line_number=record_number,
                )
            )

            return issues, warnings

        # Required fields

        missing_fields = (
            REQUIRED_FIELDS - set(record.keys())
        )

        for name in sorted(missing_fields):

            issues.append(
                self._issue(
                    "MISSING_REQUIRED_FIELD",
                    f"Required field '{name}' is missing.",
                    line_number=record_number,
                    field_name=name,
                )
            )

        # Unknown fields are warnings to allow controlled
        # future schema extensions.

        unknown_fields = (
            set(record.keys()) - REQUIRED_FIELDS
        )

        for name in sorted(unknown_fields):

            warnings.append(
                self._issue(
                    "UNKNOWN_FIELD",
                    f"Field '{name}' is not defined in schema "
                    f"{self.schema_version}.",
                    severity="warning",
                    line_number=record_number,
                    field_name=name,
                )
            )

        if missing_fields:
            return issues, warnings

        # Case identifier

        case_id = record["case_id"]

        if (
            not isinstance(case_id, str)
            or not CASE_ID_PATTERN.fullmatch(case_id)
        ):

            issues.append(
                self._issue(
                    "INVALID_CASE_ID",
                    "case_id must use lowercase letters, "
                    "numbers, and underscores, and start "
                    "with a letter.",
                    line_number=record_number,
                    field_name="case_id",
                )
            )

        # Category

        if (
            not isinstance(record["category"], str)
            or record["category"] not in ALLOWED_CATEGORIES
        ):

            issues.append(
                self._issue(
                    "INVALID_CATEGORY",
                    "Category is not in the approved category list.",
                    line_number=record_number,
                    field_name="category",
                )
            )

        # Difficulty

        if (
            not isinstance(record["difficulty"], str)
            or record["difficulty"] not in ALLOWED_DIFFICULTIES
        ):

            issues.append(
                self._issue(
                    "INVALID_DIFFICULTY",
                    "Difficulty must be basic, intermediate, "
                    "or advanced.",
                    line_number=record_number,
                    field_name="difficulty",
                )
            )

        # Task

        if (
            not isinstance(record["task"], str)
            or not record["task"].strip()
        ):

            issues.append(
                self._issue(
                    "INVALID_TASK",
                    "Task must be a non-empty string.",
                    line_number=record_number,
                    field_name="task",
                )
            )

        # Context

        if not isinstance(record["context"], dict):

            issues.append(
                self._issue(
                    "INVALID_CONTEXT",
                    "Context must be a JSON object.",
                    line_number=record_number,
                    field_name="context",
                )
            )

        # Expected outcome

        if (
            not isinstance(record["expected_outcome"], dict)
            or not record["expected_outcome"]
        ):

            issues.append(
                self._issue(
                    "INVALID_EXPECTED_OUTCOME",
                    "Expected outcome must be a non-empty JSON object.",
                    line_number=record_number,
                    field_name="expected_outcome",
                )
            )

        # Success criteria

        criteria = record["success_criteria"]

        if (
            not isinstance(criteria, list)
            or not criteria
            or not all(
                isinstance(item, str) and item.strip()
                for item in criteria
            )
        ):

            issues.append(
                self._issue(
                    "INVALID_SUCCESS_CRITERIA",
                    "Success criteria must be a non-empty list "
                    "of non-empty strings.",
                    line_number=record_number,
                    field_name="success_criteria",
                )
            )

        elif len(criteria) != len(set(criteria)):

            issues.append(
                self._issue(
                    "DUPLICATE_SUCCESS_CRITERIA",
                    "Success criteria must not contain duplicates.",
                    line_number=record_number,
                    field_name="success_criteria",
                )
            )

        # Allowed tools

        tools = record["allowed_tools"]

        if (
            not isinstance(tools, list)
            or not all(
                isinstance(item, str) and item.strip()
                for item in tools
            )
        ):

            issues.append(
                self._issue(
                    "INVALID_ALLOWED_TOOLS",
                    "Allowed tools must be a list of "
                    "non-empty strings.",
                    line_number=record_number,
                    field_name="allowed_tools",
                )
            )

        elif len(tools) != len(set(tools)):

            issues.append(
                self._issue(
                    "DUPLICATE_ALLOWED_TOOLS",
                    "Allowed tools must not contain duplicates.",
                    line_number=record_number,
                    field_name="allowed_tools",
                )
            )

        # Provenance fields

        provenance_fields = (
            "source",
            "license",
            "group_id",
        )

        for name in provenance_fields:

            value = record[name]

            if (
                not isinstance(value, str)
                or not value.strip()
            ):

                issues.append(
                    self._issue(
                        "INVALID_PROVENANCE",
                        f"{name} must be a non-empty string.",
                        line_number=record_number,
                        field_name=name,
                    )
                )

        # Validation status

        status = record["validation_status"]

        if (
            not isinstance(status, str)
            or status not in ALLOWED_VALIDATION_STATUSES
        ):

            issues.append(
                self._issue(
                    "INVALID_VALIDATION_STATUS",
                    "Status must be draft, reviewed, or approved.",
                    line_number=record_number,
                    field_name="validation_status",
                )
            )

        return issues, warnings

    # --------------------------------------------------------
    # COMPLETE JSONL VALIDATION
    # --------------------------------------------------------

    def validate_file(self, file_path):

        path = Path(file_path)

        report = DatasetValidationReport(
            dataset_path=str(path),
            schema_version=self.schema_version,
        )

        if not path.exists():

            report.issues.append(
                self._issue(
                    "FILE_NOT_FOUND",
                    "Dataset file does not exist.",
                )
            )

            return report, []

        if not path.is_file():

            report.issues.append(
                self._issue(
                    "INVALID_DATASET_PATH",
                    "Dataset path must reference a file.",
                )
            )

            return report, []

        records = []
        seen_ids = set()

        try:

            with path.open(
                "r",
                encoding="utf-8-sig",
            ) as file:

                for line_number, line in enumerate(
                    file,
                    start=1,
                ):

                    if not line.strip():

                        report.warnings.append(
                            self._issue(
                                "EMPTY_LINE",
                                "Empty JSONL line was skipped.",
                                severity="warning",
                                line_number=line_number,
                            )
                        )

                        continue

                    report.total_records += 1

                    try:

                        record = json.loads(
                            line,
                            object_pairs_hook=(
                                _reject_duplicate_json_keys
                            ),
                            parse_constant=(
                                _reject_nonstandard_json_constant
                            ),
                        )

                    except (json.JSONDecodeError, ValueError) as error:

                        report.issues.append(
                            self._issue(
                                "INVALID_JSON",
                                str(error),
                                line_number=line_number,
                            )
                        )

                        continue

                    issues, warnings = self.validate_record(
                        record,
                        record_number=line_number,
                    )

                    report.issues.extend(issues)
                    report.warnings.extend(warnings)

                    if issues:
                        continue

                    case_id = record["case_id"]

                    if case_id in seen_ids:

                        report.issues.append(
                            self._issue(
                                "DUPLICATE_CASE_ID",
                                f"case_id '{case_id}' "
                                "already exists in this dataset.",
                                line_number=line_number,
                                field_name="case_id",
                            )
                        )

                        continue

                    seen_ids.add(case_id)
                    records.append(record)
                    report.valid_records += 1

        except UnicodeDecodeError as error:

            report.issues.append(
                self._issue(
                    "ENCODING_ERROR",
                    f"Dataset must be UTF-8 encoded: {error}.",
                )
            )

            records = []

        except OSError as error:

            report.issues.append(
                self._issue(
                    "FILE_READ_ERROR",
                    str(error),
                )
            )

            records = []

        return report, records

    # --------------------------------------------------------
    # STRICT DATASET LOADING
    # --------------------------------------------------------

    def load_jsonl(self, file_path):

        report, records = self.validate_file(file_path)

        if not report.is_valid:

            raise DatasetValidationError(report)

        return records
