import os

if os.getenv("AEGIS_DATABASE_URL", "").strip():
    from . import postgres_backend as _backend
    BACKEND_NAME = "postgresql"
else:
    from . import database as _backend
    BACKEND_NAME = "sqlite"


_FUNCTIONS = (
    "get_connection",
    "initialize_database",
    "save_feedback",
    "get_all_feedback",
    "save_benchmark_result",
    "get_all_benchmark_results",
    "create_research_experiment",
    "save_research_case_result",
    "save_research_trial_result",
    "update_research_experiment_status",
    "get_research_experiment",
    "get_research_case_results",
    "get_research_trial_results",
    "update_research_experiment_configuration",
    "create_conversation",
    "save_conversation_message",
    "get_conversation_messages",
    "get_all_conversations",
    "delete_conversation",
)

for _name in _FUNCTIONS:
    globals()[_name] = getattr(_backend, _name)

__all__ = ["BACKEND_NAME", *_FUNCTIONS]
