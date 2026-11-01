"""
AEGIS Research Dataset Generator.

Provides a reproducible generation engine for category-specific synthetic
research scenarios. Scenario families are registered separately from the
generation engine so that the dataset can grow without duplicating logic.

Generated records are always marked as drafts. Generation and schema
validation do not constitute human review or research approval.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import tempfile

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.benchmark.dataset_validator import (
    ALLOWED_CATEGORIES,
    ALLOWED_DIFFICULTIES,
    DatasetValidator,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_RANDOM_SEED = 42
DEFAULT_GROUP_SIZE = 5

DIFFICULTY_DISTRIBUTION = {
    "basic": 0.40,
    "intermediate": 0.40,
    "advanced": 0.20,
}

SYNTHETIC_SOURCE = (
    "Original synthetic scenario authored for the AEGIS research dataset."
)

SYNTHETIC_LICENSE = (
    "Original synthetic; no third-party source material."
)


# A scenario builder receives:
#   variant_index: the position of the case within its family
#   difficulty: basic, intermediate, or advanced
#   rng: a deterministic random number generator
#
# It must return a dictionary containing the scenario's task-specific fields.
ScenarioBuilder = Callable[[int, str, random.Random], dict[str, Any]]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class DatasetGenerationError(Exception):
    """Raised when dataset generation or validation fails."""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScenarioFamily:
    """A reusable family of related research scenarios."""

    category: str
    family_id: str
    description: str
    builder: ScenarioBuilder


@dataclass(frozen=True)
class GenerationSummary:
    """Summary of one dataset generation operation."""

    total_records: int
    category_counts: dict[str, int]
    difficulty_counts: dict[str, int]
    family_counts: dict[str, int]
    random_seed: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_records": self.total_records,
            "category_counts": dict(self.category_counts),
            "difficulty_counts": dict(self.difficulty_counts),
            "family_counts": dict(self.family_counts),
            "random_seed": self.random_seed,
        }


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class DatasetGenerator:
    """
    Generates reproducible synthetic research dataset records.

    This class deliberately separates:
      1. Generation mechanics.
      2. Scenario-family definitions.
      3. Dataset validation.
      4. Dataset file writing.

    It does not automatically approve generated records.
    """

    def __init__(
        self,
        families: Iterable[ScenarioFamily] = (),
        random_seed: int = DEFAULT_RANDOM_SEED,
        group_size: int = DEFAULT_GROUP_SIZE,
    ) -> None:
        if isinstance(random_seed, bool) or not isinstance(random_seed, int):
            raise ValueError("random_seed must be an integer.")

        if isinstance(group_size, bool) or not isinstance(group_size, int):
            raise ValueError("group_size must be an integer.")

        if group_size < 1:
            raise ValueError("group_size must be at least 1.")

        self.random_seed = random_seed
        self.group_size = group_size
        self.validator = DatasetValidator()

        self._families: dict[tuple[str, str], ScenarioFamily] = {}

        for family in families:
            self.register_family(family)

    # -----------------------------------------------------------------------
    # Scenario registration
    # -----------------------------------------------------------------------

    def register_family(self, family: ScenarioFamily) -> None:
        """Register one scenario family."""

        if not isinstance(family, ScenarioFamily):
            raise TypeError("family must be a ScenarioFamily instance.")

        if family.category not in ALLOWED_CATEGORIES:
            raise DatasetGenerationError(
                f"Unsupported category: {family.category}"
            )

        if not re.fullmatch(r"[a-z][a-z0-9_]*", family.family_id):
            raise DatasetGenerationError(
                f"Invalid family_id: {family.family_id}"
            )

        if not family.description.strip():
            raise DatasetGenerationError(
                "Scenario family description cannot be empty."
            )

        if not callable(family.builder):
            raise DatasetGenerationError(
                "Scenario family builder must be callable."
            )

        key = (family.category, family.family_id)

        if key in self._families:
            raise DatasetGenerationError(
                f"Scenario family already registered: {key}"
            )

        self._families[key] = family

    @property
    def families(self) -> tuple[ScenarioFamily, ...]:
        """Return registered families in deterministic order."""

        return tuple(
            self._families[key]
            for key in sorted(self._families)
        )

    # -----------------------------------------------------------------------
    # Reproducibility
    # -----------------------------------------------------------------------

    def _family_random(self, family: ScenarioFamily) -> random.Random:
        """
        Create a stable random generator for one family.

        SHA-256 is used instead of Python's built-in hash(), whose values
        may differ between interpreter processes.
        """

        seed_material = (
            f"{self.random_seed}:"
            f"{family.category}:"
            f"{family.family_id}"
        )

        digest = hashlib.sha256(
            seed_material.encode("utf-8")
        ).digest()

        family_seed = int.from_bytes(digest[:8], byteorder="big")

        return random.Random(family_seed)

    # -----------------------------------------------------------------------
    # Difficulty assignment
    # -----------------------------------------------------------------------

    @staticmethod
    def _difficulty_schedule(
        count: int,
        rng: random.Random,
    ) -> list[str]:
        """Create a reproducible 40/40/20 difficulty distribution."""

        if isinstance(count, bool) or not isinstance(count, int):
            raise ValueError("count must be an integer.")

        if count < 1:
            raise ValueError("count must be at least 1.")

        exact_counts = {
            level: count * proportion
            for level, proportion in DIFFICULTY_DISTRIBUTION.items()
        }

        counts = {
            level: int(value)
            for level, value in exact_counts.items()
        }

        remaining = count - sum(counts.values())

        remainder_order = sorted(
            exact_counts,
            key=lambda level: (
                exact_counts[level] - counts[level],
                -list(DIFFICULTY_DISTRIBUTION).index(level),
            ),
            reverse=True,
        )

        for level in remainder_order[:remaining]:
            counts[level] += 1

        schedule = [
            level
            for level, amount in counts.items()
            for _ in range(amount)
        ]

        rng.shuffle(schedule)

        return schedule

    # -----------------------------------------------------------------------
    # Record generation
    # -----------------------------------------------------------------------

    def _build_record(
        self,
        family: ScenarioFamily,
        variant_index: int,
        difficulty: str,
        rng: random.Random,
    ) -> dict[str, Any]:
        """Build and validate one record."""

        try:
            scenario = family.builder(
                variant_index,
                difficulty,
                rng,
            )
        except Exception as exc:
            raise DatasetGenerationError(
                "Scenario builder failed for "
                f"{family.category}/{family.family_id}, "
                f"variant {variant_index}: {exc}"
            ) from exc

        if not isinstance(scenario, dict):
            raise DatasetGenerationError(
                f"Builder for {family.family_id} must return a dictionary."
            )

        record = dict(scenario)

        # The engine controls these fields to ensure consistent metadata.
        record.update({
            "case_id": (
                f"{family.category}_{family.family_id}_"
                f"{variant_index:04d}"
            ),
            "category": family.category,
            "difficulty": difficulty,
            "group_id": (
                f"{family.category}_{family.family_id}_"
                f"group_{((variant_index - 1) // self.group_size) + 1:04d}"
            ),
            "source": SYNTHETIC_SOURCE,
            "license": SYNTHETIC_LICENSE,
            "validation_status": "draft",
        })

        issues, warnings = self.validator.validate_record(
            record,
            record_number=variant_index,
        )

        if issues:
            details = "; ".join(str(issue) for issue in issues)

            raise DatasetGenerationError(
                f"Generated record {record['case_id']} failed validation: "
                f"{details}"
            )

        if warnings:
            details = "; ".join(str(warning) for warning in warnings)

            raise DatasetGenerationError(
                f"Generated record {record['case_id']} has warnings: "
                f"{details}"
            )

        return record

    def generate_records(
        self,
        variants_per_family: int,
        reserved_case_ids: Iterable[str] = (),
    ) -> tuple[list[dict[str, Any]], GenerationSummary]:
        """
        Generate records from every registered family.

        Related variants are assigned the same group_id in batches of
        group_size. This supports group-aware train/validation/test splits.

        Builders are responsible for producing genuinely distinct scenarios.
        """

        if (
            isinstance(variants_per_family, bool)
            or not isinstance(variants_per_family, int)
        ):
            raise ValueError(
                "variants_per_family must be an integer."
            )

        if variants_per_family < 1:
            raise ValueError(
                "variants_per_family must be at least 1."
            )

        if not self._families:
            raise DatasetGenerationError(
                "No scenario families are registered."
            )

        used_ids = set(reserved_case_ids)

        if any(
            not isinstance(case_id, str) or not case_id.strip()
            for case_id in used_ids
        ):
            raise ValueError(
                "reserved_case_ids must contain non-empty strings."
            )

        records: list[dict[str, Any]] = []

        category_counts = {
            category: 0
            for category in sorted(ALLOWED_CATEGORIES)
        }

        difficulty_counts = {
            difficulty: 0
            for difficulty in sorted(ALLOWED_DIFFICULTIES)
        }

        family_counts: dict[str, int] = {}

        for family in self.families:
            rng = self._family_random(family)

            difficulties = self._difficulty_schedule(
                variants_per_family,
                rng,
            )

            family_key = f"{family.category}/{family.family_id}"

            for index, difficulty in enumerate(difficulties, start=1):
                record = self._build_record(
                    family,
                    index,
                    difficulty,
                    rng,
                )

                case_id = record["case_id"]

                if case_id in used_ids:
                    raise DatasetGenerationError(
                        f"Duplicate case_id detected: {case_id}"
                    )

                used_ids.add(case_id)
                records.append(record)

                category_counts[family.category] += 1
                difficulty_counts[difficulty] += 1
                family_counts[family_key] = (
                    family_counts.get(family_key, 0) + 1
                )

        summary = GenerationSummary(
            total_records=len(records),
            category_counts=category_counts,
            difficulty_counts=difficulty_counts,
            family_counts=family_counts,
            random_seed=self.random_seed,
        )

        return records, summary

    # -----------------------------------------------------------------------
    # JSONL output
    # -----------------------------------------------------------------------

    @staticmethod
    def write_jsonl(
        records: Iterable[dict[str, Any]],
        output_path: str | Path,
        overwrite: bool = False,
    ) -> Path:
        """
        Write records to JSONL using a temporary file.

        Existing files are protected unless overwrite=True.
        """

        destination = Path(output_path)

        if destination.exists() and not overwrite:
            raise DatasetGenerationError(
                f"Output already exists; refusing to overwrite: "
                f"{destination}"
            )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                suffix=".tmp",
                prefix=".aegis_dataset_",
                dir=destination.parent,
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)

                for record in records:
                    temporary_file.write(
                        json.dumps(
                            record,
                            ensure_ascii=False,
                            sort_keys=True,
                            allow_nan=False,
                        )
                    )
                    temporary_file.write("\n")

                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            if destination.exists() and not overwrite:
                raise DatasetGenerationError(
                    f"Output appeared during generation: {destination}"
                )

            os.replace(temporary_path, destination)
            temporary_path = None

            return destination

        except DatasetGenerationError:
            raise

        except (OSError, TypeError, ValueError) as exc:
            raise DatasetGenerationError(
                f"Could not write dataset to {destination}: {exc}"
            ) from exc

        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass