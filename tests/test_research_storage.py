
import sqlite3

import pytest

from app.memory.database import (
    create_research_experiment,
    save_research_case_result,
    save_research_trial_result,
    update_research_experiment_status,
    get_research_experiment,
    get_research_case_results,
    get_research_trial_results,
)


EXPERIMENT_ID = "test-experiment-001"
CASE_ID = "test-case-001"

SHA256_A = "a" * 64
SHA256_B = "b" * 64


def create_test_experiment():

    return create_research_experiment(
        experiment_id=EXPERIMENT_ID,
        experiment_name="AEGIS Storage Test",
        dataset_id="aegis-research-v1",
        dataset_version="0.1.0",
        schema_version="1.0.0",
        dataset_sha256=SHA256_A,
        manifest_sha256=SHA256_B,
        dataset_path="datasets/test.jsonl",
        manifest_path="datasets/manifest.json",
        run_type="development_pilot",
        manifest_status="development",
        random_seed=42,
        trials=10,
        warmup_trials=1,
        configuration={
            "seed": 42,
            "trials": 10,
            "warmup_trials": 1,
        },
    )


def create_test_case():

    return save_research_case_result(
        experiment_id=EXPERIMENT_ID,
        case_id=CASE_ID,
        category="basic_execution",
        difficulty="intermediate",
        group_id="test-group-001",
        validation_status="draft",
        expected_outcome={
            "sentence_count": 7,
        },
    )


def test_research_experiment_is_persisted():

    record_id = create_test_experiment()

    experiment = get_research_experiment(EXPERIMENT_ID)

    assert record_id > 0
    assert experiment is not None
    assert experiment["experiment_id"] == EXPERIMENT_ID
    assert experiment["dataset_id"] == "aegis-research-v1"
    assert experiment["random_seed"] == 42
    assert experiment["trials"] == 10
    assert experiment["status"] == "running"


def test_research_experiment_configuration_is_preserved():

    create_test_experiment()

    import json

    experiment = get_research_experiment(EXPERIMENT_ID)

    configuration = json.loads(
        experiment["configuration_json"]
    )

    assert configuration == {
        "seed": 42,
        "trials": 10,
        "warmup_trials": 1,
    }


def test_duplicate_experiment_id_is_rejected():

    create_test_experiment()

    with pytest.raises(sqlite3.IntegrityError):
        create_test_experiment()


def test_invalid_dataset_hash_is_rejected():

    with pytest.raises(ValueError):
        create_research_experiment(
            experiment_id="invalid-hash-test",
            experiment_name="Invalid Hash",
            dataset_id="test",
            dataset_version="0.1.0",
            schema_version="1.0.0",
            dataset_sha256="invalid",
            manifest_sha256=SHA256_B,
            dataset_path="test.jsonl",
            manifest_path="manifest.json",
            run_type="development_pilot",
            manifest_status="development",
            random_seed=42,
            trials=10,
            warmup_trials=1,
            configuration={},
        )


def test_research_case_result_is_persisted():

    create_test_experiment()

    record_id = create_test_case()

    cases = get_research_case_results(EXPERIMENT_ID)

    assert record_id > 0
    assert len(cases) == 1
    assert cases[0]["case_id"] == CASE_ID
    assert cases[0]["category"] == "basic_execution"
    assert cases[0]["difficulty"] == "intermediate"
    assert cases[0]["validation_status"] == "draft"


def test_expected_outcome_is_preserved():

    import json

    create_test_experiment()
    create_test_case()

    cases = get_research_case_results(EXPERIMENT_ID)

    expected = json.loads(
        cases[0]["expected_outcome_json"]
    )

    assert expected == {"sentence_count": 7}


def test_duplicate_case_id_within_experiment_is_rejected():

    create_test_experiment()
    create_test_case()

    with pytest.raises(sqlite3.IntegrityError):
        create_test_case()


def test_case_cannot_reference_missing_experiment():

    with pytest.raises(sqlite3.IntegrityError):
        save_research_case_result(
            experiment_id="missing-experiment",
            case_id=CASE_ID,
            category="basic_execution",
            difficulty="basic",
            group_id="test-group",
            validation_status="draft",
            expected_outcome={"sentence_count": 1},
        )


def test_research_trial_result_is_persisted():

    create_test_experiment()
    create_test_case()

    record_id = save_research_trial_result(
        experiment_id=EXPERIMENT_ID,
        case_id=CASE_ID,
        strategy_id="direct",
        trial_number=1,
        is_warmup=False,
        execution_success=True,
        is_correct=True,
        execution_time_seconds=0.000125,
    )

    trials = get_research_trial_results(EXPERIMENT_ID)

    assert record_id > 0
    assert len(trials) == 1
    assert trials[0]["strategy_id"] == "direct"
    assert trials[0]["trial_number"] == 1
    assert trials[0]["execution_success"] == 1
    assert trials[0]["is_correct"] == 1
    assert trials[0]["execution_time_seconds"] == 0.000125


def test_trials_can_be_filtered_by_case():

    create_test_experiment()
    create_test_case()

    save_research_trial_result(
        experiment_id=EXPERIMENT_ID,
        case_id=CASE_ID,
        strategy_id="direct",
        trial_number=1,
        is_warmup=False,
        execution_success=True,
        is_correct=True,
        execution_time_seconds=0.001,
    )

    assert len(
        get_research_trial_results(
            EXPERIMENT_ID,
            case_id=CASE_ID,
        )
    ) == 1

    assert get_research_trial_results(
        EXPERIMENT_ID,
        case_id="unknown-case",
    ) == []


def test_trial_cannot_reference_missing_case():

    create_test_experiment()

    with pytest.raises(sqlite3.IntegrityError):
        save_research_trial_result(
            experiment_id=EXPERIMENT_ID,
            case_id="missing-case",
            strategy_id="direct",
            trial_number=1,
            is_warmup=False,
            execution_success=True,
            is_correct=True,
            execution_time_seconds=0.001,
        )


@pytest.mark.parametrize(
    "invalid_trial_number",
    [0, -1, 1.5, True, "1"],
)
def test_invalid_trial_numbers_are_rejected(invalid_trial_number):

    create_test_experiment()
    create_test_case()

    with pytest.raises(ValueError):
        save_research_trial_result(
            experiment_id=EXPERIMENT_ID,
            case_id=CASE_ID,
            strategy_id="direct",
            trial_number=invalid_trial_number,
            is_warmup=False,
            execution_success=True,
            is_correct=True,
            execution_time_seconds=0.001,
        )


def test_boolean_execution_time_is_rejected():

    create_test_experiment()
    create_test_case()

    with pytest.raises(ValueError):
        save_research_trial_result(
            experiment_id=EXPERIMENT_ID,
            case_id=CASE_ID,
            strategy_id="direct",
            trial_number=1,
            is_warmup=False,
            execution_success=True,
            is_correct=True,
            execution_time_seconds=True,
        )


def test_experiment_status_can_be_updated():

    create_test_experiment()

    result = update_research_experiment_status(
        experiment_id=EXPERIMENT_ID,
        status="completed",
        total_cases=10,
    )

    experiment = get_research_experiment(EXPERIMENT_ID)

    assert result is True
    assert experiment["status"] == "completed"
    assert experiment["total_cases"] == 10
    assert experiment["completed_at"] is not None


def test_failed_experiment_records_error():

    create_test_experiment()

    update_research_experiment_status(
        experiment_id=EXPERIMENT_ID,
        status="failed",
        error_message="Test execution failed.",
    )

    experiment = get_research_experiment(EXPERIMENT_ID)

    assert experiment["status"] == "failed"
    assert experiment["error_message"] == "Test execution failed."


def test_missing_experiment_status_update_is_rejected():

    with pytest.raises(ValueError):
        update_research_experiment_status(
            experiment_id="missing-experiment",
            status="completed",
        )


def test_invalid_experiment_status_is_rejected():

    create_test_experiment()

    with pytest.raises(ValueError):
        update_research_experiment_status(
            experiment_id=EXPERIMENT_ID,
            status="unknown",
        )


def test_nonexistent_experiment_returns_none():

    assert get_research_experiment("unknown") is None
    assert get_research_case_results("unknown") == []
    assert get_research_trial_results("unknown") == []
def test_research_experiment_configuration_can_be_updated():

    create_test_experiment()

    updated_configuration = {
        "seed": 42,
        "trials": 10,
        "warmup_trials": 2,
        "warmup_summary": {
            "direct": {
                "successful": 2,
                "failed": 0,
            }
        },
    }

    from app.memory.database import (
        update_research_experiment_configuration,
    )

    result = update_research_experiment_configuration(
        EXPERIMENT_ID,
        updated_configuration,
    )

    import json

    experiment = get_research_experiment(EXPERIMENT_ID)

    assert result is True

    assert json.loads(
        experiment["configuration_json"]
    ) == updated_configuration


def test_configuration_update_rejects_missing_experiment():

    from app.memory.database import (
        update_research_experiment_configuration,
    )

    with pytest.raises(ValueError):
        update_research_experiment_configuration(
            "missing-experiment",
            {"seed": 42},
        )


def test_configuration_update_rejects_non_dictionary():

    create_test_experiment()

    from app.memory.database import (
        update_research_experiment_configuration,
    )

    with pytest.raises(ValueError):
        update_research_experiment_configuration(
            EXPERIMENT_ID,
            ["invalid"],
        )