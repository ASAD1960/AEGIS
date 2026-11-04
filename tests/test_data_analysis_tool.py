
import csv

import pytest

from app.tools.data_analysis_tool import DataAnalysisTool


@pytest.fixture
def csv_file(tmp_path):
    file_path = tmp_path / "employees.csv"

    with file_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["name", "age", "salary", "department"])
        writer.writerow(["Ali", "25", "50000", "IT"])
        writer.writerow(["Sara", "30", "65000", "HR"])
        writer.writerow(["Ahmed", "28", "55000", "IT"])

    return file_path


@pytest.fixture
def tool():
    return DataAnalysisTool()


def test_analyze_csv_without_filter(tool, csv_file):
    result = tool.execute(file_path=str(csv_file))

    assert result["row_count"] == 3
    assert result["source_row_count"] == 3
    assert result["column_count"] == 4
    assert result["filtered"] is False


def test_numeric_filter(tool, csv_file):
    result = tool.execute(
        file_path=str(csv_file),
        filter_column="salary",
        filter_operator=">",
        filter_value=55000,
    )

    assert result["row_count"] == 1
    assert result["filter"]["matched_rows"] == 1


def test_equal_filter(tool, csv_file):
    result = tool.execute(
        file_path=str(csv_file),
        filter_column="department",
        filter_operator="==",
        filter_value="IT",
    )

    assert result["row_count"] == 2


def test_not_equal_filter(tool, csv_file):
    result = tool.execute(
        file_path=str(csv_file),
        filter_column="department",
        filter_operator="!=",
        filter_value="IT",
    )

    assert result["row_count"] == 1


def test_greater_than_or_equal_filter(tool, csv_file):
    result = tool.execute(
        file_path=str(csv_file),
        filter_column="age",
        filter_operator=">=",
        filter_value=28,
    )

    assert result["row_count"] == 2


def test_less_than_filter(tool, csv_file):
    result = tool.execute(
        file_path=str(csv_file),
        filter_column="age",
        filter_operator="<",
        filter_value=28,
    )

    assert result["row_count"] == 1


def test_less_than_or_equal_filter(tool, csv_file):
    result = tool.execute(
        file_path=str(csv_file),
        filter_column="age",
        filter_operator="<=",
        filter_value=28,
    )

    assert result["row_count"] == 2


def test_contains_filter(tool, csv_file):
    result = tool.execute(
        file_path=str(csv_file),
        filter_column="name",
        filter_operator="contains",
        filter_value="sa",
    )

    assert result["row_count"] == 1


def test_filter_is_case_insensitive(tool, csv_file):
    result = tool.execute(
        file_path=str(csv_file),
        filter_column="name",
        filter_operator="contains",
        filter_value="ALI",
    )

    assert result["row_count"] == 1


def test_unknown_filter_column(tool, csv_file):
    with pytest.raises(ValueError):
        tool.execute(
            file_path=str(csv_file),
            filter_column="unknown",
            filter_operator="==",
            filter_value="test",
        )


def test_unsupported_filter_operator(tool, csv_file):
    with pytest.raises(ValueError):
        tool.execute(
            file_path=str(csv_file),
            filter_column="age",
            filter_operator="approximately",
            filter_value=25,
        )


def test_partial_filter_arguments_rejected(tool, csv_file):
    with pytest.raises(TypeError):
        tool.execute(
            file_path=str(csv_file),
            filter_column="age",
        )


def test_non_numeric_comparison_value_rejected(tool, csv_file):
    with pytest.raises(ValueError):
        tool.execute(
            file_path=str(csv_file),
            filter_column="age",
            filter_operator=">",
            filter_value="abc",
        )


def test_non_finite_comparison_value_rejected(tool, csv_file):
    with pytest.raises(ValueError):
        tool.execute(
            file_path=str(csv_file),
            filter_column="age",
            filter_operator=">",
            filter_value=float("inf"),
        )


def test_boolean_filter_value_rejected(tool, csv_file):
    with pytest.raises(TypeError):
        tool.execute(
            file_path=str(csv_file),
            filter_column="age",
            filter_operator="==",
            filter_value=True,
        )


def test_missing_file_rejected(tool, tmp_path):
    with pytest.raises(FileNotFoundError):
        tool.execute(
            file_path=str(tmp_path / "missing.csv")
        )


def test_missing_required_argument_rejected(tool):
    with pytest.raises(TypeError):
        tool.execute()


def test_unexpected_argument_rejected(tool, csv_file):
    with pytest.raises(TypeError):
        tool.execute(
            file_path=str(csv_file),
            unknown_argument=True,
        )


def test_filtered_results_keep_source_row_count(tool, csv_file):
    result = tool.execute(
        file_path=str(csv_file),
        filter_column="salary",
        filter_operator=">",
        filter_value=55000,
    )

    assert result["source_row_count"] == 3
    assert result["row_count"] == 1


def test_numeric_statistics_after_filtering(tool, csv_file):
    result = tool.execute(
        file_path=str(csv_file),
        filter_column="department",
        filter_operator="==",
        filter_value="IT",
    )

    age_stats = result["column_summaries"]["age"]["statistics"]

    assert age_stats["mean"] == 26.5
    assert age_stats["minimum"] == 25.0
    assert age_stats["maximum"] == 28.0
