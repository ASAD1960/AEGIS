"""
AEGIS Feedback System

Collects and permanently stores agent feedback.
"""

from app.memory.database import (
    initialize_database,
    save_feedback,
    get_all_feedback,
)


class FeedbackSystem:

    def __init__(self):
        initialize_database()

    def record_feedback(
        self,
        task,
        rating,
        comment="",
        strategy_id=None
    ):

        record_id = save_feedback(
            task,
            rating,
            comment,
            strategy_id
        )

        return {
            "id": record_id,
            "task": task,
            "rating": rating,
            "comment": comment,
            "strategy_id": strategy_id,
        }

    def get_feedback_history(self):

        records = get_all_feedback()

        feedback_history = []

        for record in records:

            feedback_history.append({
                "id": record[0],
                "task": record[1],
                "rating": record[2],
                "comment": record[3],
                "created_at": record[4],
                "strategy_id": record[5],
            })

        return feedback_history