
"""Reproducible, group-aware splitting for the AEGIS research dataset."""

from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


SPLIT_NAMES = ("train", "validation", "test")


class DatasetSplitError(ValueError):
    """Raised when dataset splitting or leakage validation fails."""


@dataclass(frozen=True)
class SplitSummary:
    """Metadata describing the generated dataset splits."""

    seed: int
    record_counts: dict[str, int]
    group_counts: dict[str, int]
    category_counts: dict[str, dict[str, int]]
    group_assignments: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable summary."""
        return {
            "seed": self.seed,
            "record_counts": self.record_counts,
            "group_counts": self.group_counts,
            "category_counts": self.category_counts,
            "group_assignments": self.group_assignments,
        }


@dataclass(frozen=True)
class DatasetSplits:
    """The three dataset partitions and their summary."""

    train: list[dict[str, Any]]
    validation: list[dict[str, Any]]
    test: list[dict[str, Any]]
    summary: SplitSummary

    def as_dict(self) -> dict[str, list[dict[str, Any]]]:
        """Return the partitions as a dictionary."""
        return {
            "train": self.train,
            "validation": self.validation,
            "test": self.test,
        }


def _validate_ratios(
    train_ratio: float,
    validation_ratio: float,
    test_ratio: float,
) -> None:
    """Validate that split ratios are finite, positive, and sum to one."""

    ratios = (train_ratio, validation_ratio, test_ratio)

    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
        for value in ratios
    ):
        raise DatasetSplitError(
            "All split ratios must be finite positive numbers."
        )

    if not math.isclose(sum(ratios), 1.0, abs_tol=1e-9):
        raise DatasetSplitError(
            "Train, validation, and test ratios must sum to 1.0."
        )


def _prepare_groups(
    records: Sequence[dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], Counter]:
    """Validate essential record fields and group records by group_id."""

    if not records:
        raise DatasetSplitError("Cannot split an empty dataset.")

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_case_ids: set[str] = set()
    category_totals: Counter = Counter()

    for position, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise DatasetSplitError(
                f"Record {position} must be a dictionary."
            )

        for field in ("case_id", "group_id", "category"):
            value = record.get(field)

            if not isinstance(value, str) or not value.strip():
                raise DatasetSplitError(
                    f"Record {position} has an invalid or missing "
                    f"'{field}' field."
                )

        case_id = record["case_id"]
        group_id = record["group_id"]
        category = record["category"]

        if case_id in seen_case_ids:
            raise DatasetSplitError(
                f"Duplicate case_id detected: '{case_id}'."
            )

        seen_case_ids.add(case_id)
        groups[group_id].append(record)
        category_totals[category] += 1

    return dict(groups), category_totals


def _assignment_score(
    candidate: str,
    group_size: int,
    group_categories: Counter,
    current_records: Mapping[str, int],
    current_categories: Mapping[str, Counter],
    total_records: int,
    category_totals: Counter,
    ratios: Mapping[str, float],
) -> float:
    """Measure how well a possible assignment balances the splits."""

    score = 0.0

    for split_name in SPLIT_NAMES:
        added_records = (
            group_size if split_name == candidate else 0
        )
        actual_records = current_records[split_name] + added_records
        target_records = total_records * ratios[split_name]

        record_error = (
            (actual_records - target_records)
            / max(target_records, 1.0)
        ) ** 2

        score += record_error

        for category, total in category_totals.items():
            added_category = (
                group_categories[category]
                if split_name == candidate
                else 0
            )

            actual_category = (
                current_categories[split_name][category]
                + added_category
            )
            target_category = total * ratios[split_name]

            category_error = (
                (actual_category - target_category)
                / max(target_category, 1.0)
            ) ** 2

            score += category_error

    return score


def assert_no_group_leakage(
    splits: Mapping[str, Sequence[dict[str, Any]]],
) -> None:
    """Raise an error if a group appears in multiple partitions."""

    group_locations: dict[str, str] = {}

    for split_name, records in splits.items():
        for record in records:
            group_id = record.get("group_id")

            if not isinstance(group_id, str) or not group_id.strip():
                raise DatasetSplitError(
                    f"Invalid group_id found in '{split_name}'."
                )

            previous_split = group_locations.get(group_id)

            if previous_split is not None and previous_split != split_name:
                raise DatasetSplitError(
                    f"Group leakage detected: '{group_id}' appears in "
                    f"'{previous_split}' and '{split_name}'."
                )

            group_locations[group_id] = split_name


def split_records(
    records: Sequence[dict[str, Any]],
    train_ratio: float = 0.70,
    validation_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> DatasetSplits:
    """
    Split records by group while balancing record counts and categories.

    Related records sharing a group_id are always assigned to the same
    partition. A fixed seed makes the assignment reproducible for the
    same input dataset and configuration.
    """

    _validate_ratios(
        train_ratio,
        validation_ratio,
        test_ratio,
    )

    if isinstance(seed, bool) or not isinstance(seed, int):
        raise DatasetSplitError("Seed must be an integer.")

    groups, category_totals = _prepare_groups(records)

    if len(groups) < len(SPLIT_NAMES):
        raise DatasetSplitError(
            "At least three distinct groups are required "
            "to populate all three splits."
        )

    ratios = {
        "train": train_ratio,
        "validation": validation_ratio,
        "test": test_ratio,
    }

    total_records = len(records)

    current_records = {name: 0 for name in SPLIT_NAMES}
    current_categories = {
        name: Counter() for name in SPLIT_NAMES
    }
    assigned_groups = {
        name: [] for name in SPLIT_NAMES
    }
    group_assignments: dict[str, str] = {}

    rng = random.Random(seed)

    # Sort first so the same dataset produces the same result
    # even if its input records arrive in a different order.
    group_items = sorted(groups.items(), key=lambda item: item[0])

    # Randomize ties reproducibly, then process larger groups first.
    rng.shuffle(group_items)
    group_items.sort(
        key=lambda item: len(item[1]),
        reverse=True,
    )

    for index, (group_id, group_records) in enumerate(group_items):
        group_size = len(group_records)
        group_categories = Counter(
            record["category"] for record in group_records
        )

        empty_splits = [
            name
            for name in SPLIT_NAMES
            if current_records[name] == 0
        ]

        remaining_groups = len(group_items) - index

        # Reserve enough remaining groups to populate empty splits.
        candidates = (
            empty_splits
            if remaining_groups == len(empty_splits)
            else list(SPLIT_NAMES)
        )

        selected_split = min(
            candidates,
            key=lambda name: _assignment_score(
                candidate=name,
                group_size=group_size,
                group_categories=group_categories,
                current_records=current_records,
                current_categories=current_categories,
                total_records=total_records,
                category_totals=category_totals,
                ratios=ratios,
            ),
        )

        assigned_groups[selected_split].extend(group_records)
        current_records[selected_split] += group_size
        current_categories[selected_split].update(group_categories)
        group_assignments[group_id] = selected_split

    # Sort records for stable output files and comparisons.
    for split_name in SPLIT_NAMES:
        assigned_groups[split_name].sort(
            key=lambda record: record["case_id"]
        )

    result_mapping = assigned_groups

    assert_no_group_leakage(result_mapping)

    summary = SplitSummary(
        seed=seed,
        record_counts={
            name: len(result_mapping[name])
            for name in SPLIT_NAMES
        },
        group_counts={
            name: sum(
                1
                for assigned_split in group_assignments.values()
                if assigned_split == name
            )
            for name in SPLIT_NAMES
        },
        category_counts={
            name: dict(current_categories[name])
            for name in SPLIT_NAMES
        },
        group_assignments=dict(sorted(group_assignments.items())),
    )

    return DatasetSplits(
        train=result_mapping["train"],
        validation=result_mapping["validation"],
        test=result_mapping["test"],
        summary=summary,
    )
