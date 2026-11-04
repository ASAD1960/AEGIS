
from fastapi.testclient import TestClient

from app.api.main import app


client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "application": "AEGIS",
        "version": "0.1.0",
    }


def test_agent_status():
    response = client.get("/api/status")

    assert response.status_code == 200

    data = response.json()

    assert data["agent"] == "AEGIS"
    assert data["status"] == "Initialized"
    assert data["version"] == "0.1.0"


def test_registered_tools():
    response = client.get("/api/tools")

    assert response.status_code == 200

    data = response.json()

    tool_names = {
        tool["name"]
        for tool in data["tools"]
    }

    assert tool_names == {
        "text_analysis",
        "calculator",
        "data_analysis",
    }


def test_calculator_task():
    response = client.post(
        "/api/tasks",
        json={"task": "Add 25 and 15"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["execution"]["tool_name"] == "calculator"
    assert data["execution"]["result"]["result"] == 40


def test_text_analysis_task():
    response = client.post(
        "/api/tasks",
        json={
            "task": "Analyze text: AEGIS is an intelligent agent."
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["execution"]["tool_name"] == "text_analysis"

    result = data["execution"]["result"]

    assert result["word_count"] == 5
    assert result["sentence_count"] == 1


def test_csv_analysis_task():
    response = client.post(
        "/api/tasks",
        json={"task": "Analyze CSV data"},
    )

    assert response.status_code == 400


def test_csv_upload_success(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.api.main.UPLOAD_DIRECTORY",
        tmp_path,
    )

    csv_content = (
        b"Name,Age,Salary\n"
        b"Ali,24,50000\n"
        b"Sara,27,65000\n"
    )

    response = client.post(
        "/api/data/upload",
        files={
            "file": (
                "employees.csv",
                csv_content,
                "text/csv",
            )
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["original_filename"] == "employees.csv"
    assert data["execution"]["tool_name"] == "data_analysis"

    result = data["execution"]["result"]

    assert result["row_count"] == 2
    assert result["column_count"] == 3
    assert (
        result["column_summaries"]["Salary"]["statistics"]["mean"]
        == 57500
    )

    stored_file = tmp_path / data["stored_filename"]

    assert stored_file.exists()


def test_csv_upload_rejects_non_csv_file():
    response = client.post(
        "/api/data/upload",
        files={
            "file": (
                "employees.txt",
                b"This is not a CSV file.",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only CSV files are accepted."


def test_csv_upload_rejects_oversized_file():
    oversized_content = b"A" * (5 * 1024 * 1024 + 1)

    response = client.post(
        "/api/data/upload",
        files={
            "file": (
                "large.csv",
                oversized_content,
                "text/csv",
            )
        },
    )

    assert response.status_code == 413
    assert response.json()["detail"] == (
        "File exceeds the 5 MB upload limit."
    )


def test_csv_upload_rejects_invalid_encoding():
    invalid_content = bytes([255, 254, 250, 251])

    response = client.post(
        "/api/data/upload",
        files={
            "file": (
                "invalid.csv",
                invalid_content,
                "text/csv",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "CSV file must use UTF-8 encoding."
    )
