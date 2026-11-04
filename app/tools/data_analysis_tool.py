
"""
AEGIS Data Analysis Tool

Loads, inspects, filters, and analyzes CSV datasets
using Python's built-in CSV functionality.
"""

import csv
import math
import os
import statistics

from app.tools.base import BaseTool


class DataAnalysisTool(BaseTool):
    """Load, filter, and analyze structured CSV data."""

    name = "data_analysis"
    description = (
        "Loads CSV files, provides dataset summaries and "
        "numerical statistics, and filters records using conditions."
    )

    def execute(self, **kwargs):
        """
        Execute CSV dataset inspection and optional filtering.

        Required:
            file_path: Path to the CSV file.

        Optional filtering arguments:
            filter_column: Column to filter.
            filter_operator: ==, !=, >, >=, <, <=, contains
            filter_value: Value to compare against.
        """

        required = {"file_path"}

        optional = {
            "filter_column",
            "filter_operator",
            "filter_value",
        }

        missing = required - set(kwargs)

        if missing:
            raise TypeError(
                f"Missing required arguments: {sorted(missing)}"
            )

        unexpected = set(kwargs) - required - optional

        if unexpected:
            raise TypeError(
                f"Unexpected arguments: {sorted(unexpected)}"
            )

        file_path = kwargs["file_path"]

        if not isinstance(file_path, (str, os.PathLike)):
            raise TypeError("File path must be a string or path.")

        if not os.path.isfile(file_path):
            raise FileNotFoundError(
                f"CSV file not found: {file_path}"
            )

        filter_arguments = {
            "filter_column",
            "filter_operator",
            "filter_value",
        }

        supplied_filters = filter_arguments.intersection(kwargs)

        if supplied_filters and supplied_filters != filter_arguments:
            raise TypeError(
                "Provide filter_column, filter_operator, "
                "and filter_value together."
            )

        rows = []
        columns = []

        try:
            with open(
                file_path,
                mode="r",
                encoding="utf-8-sig",
                newline="",
            ) as csv_file:

                reader = csv.DictReader(csv_file)

                if not reader.fieldnames:
                    raise ValueError(
                        "CSV file must contain a header row."
                    )

                columns = reader.fieldnames

                if any(
                    not isinstance(column, str) or not column.strip()
                    for column in columns
                ):
                    raise ValueError(
                        "CSV column names must be non-empty."
                    )

                if len(set(columns)) != len(columns):
                    raise ValueError(
                        "CSV column names must be unique."
                    )

                for row_number, row in enumerate(reader, start=2):

                    if None in row:
                        raise ValueError(
                            f"Row {row_number} contains more values "
                            "than the header."
                        )

                    if any(value is None for value in row.values()):
                        raise ValueError(
                            f"Row {row_number} contains fewer values "
                            "than the header."
                        )

                    rows.append(row)

        except UnicodeDecodeError as error:
            raise ValueError(
                "CSV file must use UTF-8 encoding."
            ) from error

        source_row_count = len(rows)
        filter_details = None

        # Apply optional filtering.
        if supplied_filters:

            filter_column = kwargs["filter_column"]
            filter_operator = kwargs["filter_operator"]
            filter_value = kwargs["filter_value"]

            if not isinstance(filter_column, str):
                raise TypeError(
                    "Filter column must be a string."
                )

            if filter_column not in columns:
                raise ValueError(
                    f"Unknown filter column: {filter_column}"
                )

            allowed_operators = {
                "==", "!=", ">", ">=", "<", "<=", "contains"
            }

            if filter_operator not in allowed_operators:
                raise ValueError(
                    f"Unsupported filter operator: {filter_operator}"
                )

            if isinstance(filter_value, bool) or not isinstance(
                filter_value, (str, int, float)
            ):
                raise TypeError(
                    "Filter value must be a string or number."
                )

            if filter_operator in {">", ">=", "<", "<="}:

                try:
                    comparison_value = float(filter_value)
                except (ValueError, TypeError):
                    raise ValueError(
                        "Numeric comparison requires a numeric filter value."
                    )

                if not math.isfinite(comparison_value):
                    raise ValueError(
                        "Filter value must be a finite number."
                    )

            else:
                comparison_value = str(filter_value)

            filtered_rows = []

            for row in rows:

                cell_value = row[filter_column]

                if filter_operator == "==":
                    matches = cell_value == comparison_value

                elif filter_operator == "!=":
                    matches = cell_value != comparison_value

                elif filter_operator == "contains":
                    matches = (
                        comparison_value.casefold()
                        in cell_value.casefold()
                    )

                else:
                    try:
                        numeric_cell = float(cell_value)

                        if not math.isfinite(numeric_cell):
                            matches = False
                        elif filter_operator == ">":
                            matches = numeric_cell > comparison_value
                        elif filter_operator == ">=":
                            matches = numeric_cell >= comparison_value
                        elif filter_operator == "<":
                            matches = numeric_cell < comparison_value
                        else:
                            matches = numeric_cell <= comparison_value

                    except ValueError:
                        matches = False

                if matches:
                    filtered_rows.append(row)

            rows = filtered_rows

            filter_details = {
                "column": filter_column,
                "operator": filter_operator,
                "value": filter_value,
                "matched_rows": len(rows),
            }

        # Analyze the resulting dataset.
        column_summaries = {}

        for column in columns:

            values = [
                row[column]
                for row in rows
            ]

            non_missing = [
                value
                for value in values
                if value.strip() != ""
            ]

            numeric_values = []
            is_numeric = True

            for value in non_missing:

                try:
                    number = float(value)

                    if not math.isfinite(number):
                        is_numeric = False
                        break

                    numeric_values.append(number)

                except ValueError:
                    is_numeric = False
                    break

            if not non_missing:
                inferred_type = "empty"

            elif is_numeric:
                inferred_type = "numeric"

            else:
                inferred_type = "text"

            column_summary = {
                "inferred_type": inferred_type,
                "missing_values": len(values) - len(non_missing),
                "non_missing_values": len(non_missing),
            }

            if inferred_type == "numeric":

                column_summary["statistics"] = {
                    "mean": statistics.mean(numeric_values),
                    "median": statistics.median(numeric_values),
                    "minimum": min(numeric_values),
                    "maximum": max(numeric_values),
                }

            column_summaries[column] = column_summary

        result = {
            "file_name": os.path.basename(file_path),
            "source_row_count": source_row_count,
            "row_count": len(rows),
            "column_count": len(columns),
            "columns": columns,
            "column_summaries": column_summaries,
            "filtered": filter_details is not None,
            "filter": filter_details,
        }

        return result
