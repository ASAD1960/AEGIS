
"""End-to-end, reproducible AEGIS research dataset pipeline."""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.benchmark.dataset_splitter import (
    DatasetSplitError,
    assert_no_group_leakage,
    split_records,
)
from app.benchmark.dataset_validator import (
    DatasetValidationError,
    DatasetValidator,
)


class DatasetPipelineError(RuntimeError):
    """Raised when the research dataset pipeline cannot complete."""


def _sha256_file(file_path: Path) -> str:
    """Calculate a file's SHA-256 checksum."""

    digest = hashlib.sha256()

    with file_path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _read_manifest(manifest_path: Path) -> dict[str, Any]:
    """Read a manifest and validate its required configuration."""

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DatasetPipelineError(
            f"Manifest not found: {manifest_path}"
        ) from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise DatasetPipelineError(
            f"Manifest is not valid UTF-8 JSON: {exc}"
        ) from exc
    except OSError as exc:
        raise DatasetPipelineError(
            f"Could not read manifest: {exc}"
        ) from exc

    if not isinstance(manifest, dict):
        raise DatasetPipelineError(
            "Manifest root must be a JSON object."
        )

    required_string_fields = (
        "dataset_id",
        "dataset_version",
        "schema_version",
    )

    for field in required_string_fields:
        value = manifest.get(field)

        if not isinstance(value, str) or not value.strip():
            raise DatasetPipelineError(
                f"Manifest field '{field}' must be a non-empty string."
            )

    categories = manifest.get("categories")

    if (
        not isinstance(categories, list)
        or not categories
        or any(
            not isinstance(item, str) or not item.strip()
            for item in categories
        )
        or len(categories) != len(set(categories))
    ):
        raise DatasetPipelineError(
            "Manifest categories must be unique, non-empty strings."
        )

    split_config = manifest.get("data_splits")

    if not isinstance(split_config, dict):
        raise DatasetPipelineError(
            "Manifest data_splits must be an object."
        )

    if split_config.get("strategy") != "group_aware":
        raise DatasetPipelineError(
            "Only the group_aware split strategy is supported."
        )

    ratio_fields = ("train", "validation", "test")
    ratios: list[float] = []

    for field in ratio_fields:
        value = split_config.get(field)

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            raise DatasetPipelineError(
                f"Split ratio '{field}' must be a finite positive number."
            )

        ratios.append(float(value))

    if not math.isclose(sum(ratios), 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise DatasetPipelineError(
            "Train, validation, and test ratios must sum to 1.0."
        )

    seed = split_config.get("random_seed")

    if isinstance(seed, bool) or not isinstance(seed, int):
        raise DatasetPipelineError(
            "Split random_seed must be an integer."
        )

    return manifest


def _write_jsonl(
    file_path: Path,
    records: list[dict[str, Any]],
) -> None:
    """Write records as UTF-8 JSON Lines."""

    with file_path.open("w", encoding="utf-8", newline="\n") as output:
        for record in records:
            output.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    sort_keys=True,
                    allow_nan=False,
                )
            )
            output.write("\n")


def _create_staged_file(
    destination: Path,
    prefix: str,
) -> Path:
    """Create a temporary file in the destination's directory."""

    destination.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        dir=destination.parent,
        prefix=prefix,
        suffix=".tmp",
        delete=False,
    ) as temporary:
        return Path(temporary.name)


def _install_staged_files(
    staged_files: list[tuple[Path, Path]],
    overwrite: bool,
) -> None:
    """
    Install staged files and roll back if installation fails.

    Existing destinations are backed up before replacement. If a later
    replacement fails, installed files are removed and backups restored.
    """

    backups: dict[Path, Path] = {}
    installed: list[Path] = []
    preserve_backups = False

    try:
        if not overwrite:
            existing = [
                destination
                for _, destination in staged_files
                if destination.exists()
            ]

            if existing:
                raise DatasetPipelineError(
                    "Output files already exist. Set overwrite=True "
                    "only after verifying that replacing them is intended: "
                    + ", ".join(str(path) for path in existing)
                )

        # Back up existing destinations before installing new files.
        for _, destination in staged_files:
            if destination.exists():
                if not overwrite:
                    raise DatasetPipelineError(
                        f"Output file appeared during processing: {destination}"
                    )

                backup = _create_staged_file(
                    destination,
                    prefix=f".{destination.name}_backup_",
                )

                try:
                    os.replace(destination, backup)
                except Exception:
                    backup.unlink(missing_ok=True)
                    raise

                backups[destination] = backup

        # Install the staged files.
        for temporary_path, destination in staged_files:
            if not overwrite and destination.exists():
                raise DatasetPipelineError(
                    f"Output file appeared during installation: {destination}"
                )

            os.replace(temporary_path, destination)
            installed.append(destination)

    except Exception as original_error:
        rollback_errors: list[str] = []

        # Remove files installed by this operation.
        for destination in reversed(installed):
            try:
                destination.unlink(missing_ok=True)
            except OSError as exc:
                rollback_errors.append(
                    f"Could not remove {destination}: {exc}"
                )

        # Restore original files.
        for destination, backup in backups.items():
            try:
                if backup.exists():
                    os.replace(backup, destination)
            except OSError as exc:
                rollback_errors.append(
                    f"Could not restore {destination} from {backup}: {exc}"
                )

        if rollback_errors:
            preserve_backups = True
            details = "; ".join(rollback_errors)

            raise DatasetPipelineError(
                "Output installation failed and rollback was incomplete. "
                f"Original error: {original_error}. "
                "Recovery files have been preserved. "
                f"Rollback errors: {details}"
            ) from original_error

        raise

    finally:
        # Always clean up staged output files.
        for temporary_path, _ in staged_files:
            temporary_path.unlink(missing_ok=True)

        # Never delete backups if restoration failed.
        if not preserve_backups:
            for backup in backups.values():
                backup.unlink(missing_ok=True)


def build_dataset_splits(
    input_path: str | Path,
    manifest_path: str | Path,
    output_root: str | Path,
    overwrite: bool = False,
) -> dict[str, Any]:
    """
    Validate, split, and export an approved research dataset.

    Existing output files are protected unless overwrite=True.
    Input data and the manifest are never modified.
    """

    source = Path(input_path)
    manifest_file = Path(manifest_path)
    output_directory = Path(output_root)

    if not source.is_file():
        raise DatasetPipelineError(
            f"Input dataset file not found: {source}"
        )

    manifest = _read_manifest(manifest_file)
    split_config = manifest["data_splits"]

    validator = DatasetValidator()

    try:
        records = validator.load_jsonl(source)
    except DatasetValidationError as exc:
        raise DatasetPipelineError(
            f"Dataset validation failed: {exc}"
        ) from exc
    except OSError as exc:
        raise DatasetPipelineError(
            f"Could not read input dataset: {exc}"
        ) from exc

    if not records:
        raise DatasetPipelineError(
            "The validated dataset contains no records."
        )

    allowed_categories = set(manifest["categories"])
    actual_categories = {
        record["category"] for record in records
    }

    unknown_categories = actual_categories - allowed_categories

    if unknown_categories:
        raise DatasetPipelineError(
            "Dataset contains categories not declared in the manifest: "
            + ", ".join(sorted(unknown_categories))
        )

    # Only human-approved cases are eligible for research splits.
    unapproved = [
        record["case_id"]
        for record in records
        if record.get("validation_status") != "approved"
    ]

    if unapproved:
        preview = ", ".join(unapproved[:10])
        raise DatasetPipelineError(
            f"{len(unapproved)} records are not approved. "
            f"Examples: {preview}"
        )

    try:
        result = split_records(
            records=records,
            train_ratio=split_config["train"],
            validation_ratio=split_config["validation"],
            test_ratio=split_config["test"],
            seed=split_config["random_seed"],
        )

        partitions = result.as_dict()
        assert_no_group_leakage(partitions)

    except (DatasetSplitError, TypeError, ValueError) as exc:
        raise DatasetPipelineError(
            f"Dataset splitting failed: {exc}"
        ) from exc

    destinations = {
        "train": output_directory / "training" / "train.jsonl",
        "validation": (
            output_directory / "validation" / "validation.jsonl"
        ),
        "test": output_directory / "testing" / "test.jsonl",
    }

    metadata_path = output_directory / "split_metadata.json"

    all_destinations = list(destinations.values()) + [metadata_path]

    protected_paths = {
        source.resolve(),
        manifest_file.resolve(),
    }

    for destination in all_destinations:
        if destination.resolve() in protected_paths:
            raise DatasetPipelineError(
                "An output destination would overwrite the input dataset "
                f"or manifest: {destination}"
            )

    if not overwrite:
        existing = [
            path for path in all_destinations
            if path.exists()
        ]

        if existing:
            raise DatasetPipelineError(
                "Output files already exist. Set overwrite=True "
                "only after verifying that replacing them is intended: "
                + ", ".join(str(path) for path in existing)
            )

    try:
        source_checksum = _sha256_file(source)
        manifest_checksum = _sha256_file(manifest_file)
    except OSError as exc:
        raise DatasetPipelineError(
            f"Could not calculate input checksums: {exc}"
        ) from exc

    metadata: dict[str, Any] = {
        "dataset_id": manifest["dataset_id"],
        "dataset_version": manifest["dataset_version"],
        "schema_version": manifest["schema_version"],
        "source_file": source.name,
        "source_sha256": source_checksum,
        "manifest_sha256": manifest_checksum,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "split_strategy": "group_aware",
        "seed": split_config["random_seed"],
        "ratios": {
            "train": split_config["train"],
            "validation": split_config["validation"],
            "test": split_config["test"],
        },
        "record_counts": result.summary.record_counts,
        "group_counts": result.summary.group_counts,
        "category_counts": result.summary.category_counts,
        "group_assignments": result.summary.group_assignments,
        "leakage_check": "passed",
    }

    staged_files: list[tuple[Path, Path]] = []

    try:
        for split_name, destination in destinations.items():
            temporary_path = _create_staged_file(
                destination,
                prefix=f".{destination.stem}_",
            )

            # Register the file before writing so failures cannot leave
            # an untracked temporary file behind.
            staged_files.append((temporary_path, destination))

            _write_jsonl(
                temporary_path,
                partitions[split_name],
            )

        # Record hashes of the exact staged split files.
        metadata["output_sha256"] = {
            split_name: _sha256_file(
                next(
                    temporary
                    for temporary, destination in staged_files
                    if destination == destinations[split_name]
                )
            )
            for split_name in destinations
        }

        metadata_temp = _create_staged_file(
            metadata_path,
            prefix=".split_metadata_",
        )

        # Register the metadata file before writing it.
        staged_files.append((metadata_temp, metadata_path))

        with metadata_temp.open(
            "w",
            encoding="utf-8",
            newline="\n",
        ) as output:
            json.dump(
                metadata,
                output,
                indent=2,
                ensure_ascii=False,
                allow_nan=False,
            )
            output.write("\n")

        _install_staged_files(
            staged_files=staged_files,
            overwrite=overwrite,
        )

    except DatasetPipelineError:
        for temporary_path, _ in staged_files:
            temporary_path.unlink(missing_ok=True)
        raise
    except (OSError, TypeError, ValueError) as exc:
        for temporary_path, _ in staged_files:
            temporary_path.unlink(missing_ok=True)

        raise DatasetPipelineError(
            f"Could not prepare dataset outputs: {exc}"
        ) from exc

    return metadata
