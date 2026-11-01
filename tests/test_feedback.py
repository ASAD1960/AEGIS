
from app.learning.feedback import FeedbackSystem


def test_feedback_can_be_saved_and_retrieved():

    feedback_system = FeedbackSystem()

    saved = feedback_system.record_feedback(
        task="Automated test task",
        rating=5,
        comment="Test feedback record."
    )

    assert saved["id"] is not None
    assert saved["task"] == "Automated test task"
    assert saved["rating"] == 5
    assert saved["comment"] == "Test feedback record."


def test_feedback_contains_strategy_information():

    feedback_system = FeedbackSystem()

    saved = feedback_system.record_feedback(
        task="Strategy test task",
        rating=4,
        comment="Testing strategy association.",
        strategy_id="careful"
    )

    assert saved["strategy_id"] == "careful"


def test_feedback_history_returns_records():

    feedback_system = FeedbackSystem()

    history = feedback_system.get_feedback_history()

    assert isinstance(history, list)

    if history:
        record = history[-1]

        assert "id" in record
        assert "task" in record
        assert "rating" in record
        assert "comment" in record
        assert "created_at" in record
        assert "strategy_id" in record


def main():

    feedback_system = FeedbackSystem()

    feedback_system.record_feedback(
        task="Generate a Python function",
        rating=5,
        comment="The result was correct."
    )

    feedback_system.record_feedback(
        task="Explain a programming concept",
        rating=3,
        comment="The explanation needs improvement."
    )

    print("AEGIS Feedback Test")
    print("=" * 40)

    for feedback in feedback_system.get_feedback_history():
        print(f"Task: {feedback['task']}")
        print(f"Rating: {feedback['rating']}/5")
        print(f"Comment: {feedback['comment']}")
        print("-" * 40)


if __name__ == "__main__":
    main()
