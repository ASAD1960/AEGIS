
from app.learning.feedback import FeedbackSystem
from app.learning.analyzer import LearningAnalyzer


def test_feedback_is_available_to_learning_analyzer():

    feedback_system = FeedbackSystem()

    feedback_system.record_feedback(
        task="Integration verification task",
        rating=5,
        comment="Integration test feedback."
    )

    analyzer = LearningAnalyzer()

    results = analyzer.analyze_performance()

    assert results["total_records"] >= 1
    assert results["positive_feedback"] >= 1


def test_feedback_and_analyzer_share_persistent_storage():

    feedback_system = FeedbackSystem()

    saved = feedback_system.record_feedback(
        task="Persistent integration task",
        rating=4,
        comment="Checking shared storage."
    )

    history = feedback_system.get_feedback_history()

    matching_records = [
        record
        for record in history
        if record["id"] == saved["id"]
    ]

    assert len(matching_records) == 1
    assert matching_records[0]["task"] == (
        "Persistent integration task"
    )


def main():

    feedback_system = FeedbackSystem()

    saved_feedback = feedback_system.record_feedback(
        task="Explain Python classes",
        rating=4,
        comment="Good explanation, but could include more examples."
    )

    print("AEGIS Feedback Integration Test")
    print("=" * 45)

    print("New feedback saved:")
    print(saved_feedback)

    print("\nComplete feedback history:")

    history = feedback_system.get_feedback_history()

    for feedback in history:
        print("-" * 45)
        print(f"ID: {feedback['id']}")
        print(f"Task: {feedback['task']}")
        print(f"Rating: {feedback['rating']}/5")
        print(f"Comment: {feedback['comment']}")
        print(f"Created: {feedback['created_at']}")

    print("=" * 45)
    print(f"Total feedback records: {len(history)}")


if __name__ == "__main__":
    main()
