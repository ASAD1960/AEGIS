"""
AEGIS Learning Analyzer

Analyzes historical feedback and compares strategy performance.
"""

from app.memory.database_backend import get_all_feedback


class LearningAnalyzer:

    def analyze_performance(self):

        records = get_all_feedback()

        if not records:
            return {
                "total_records": 0,
                "average_rating": 0,
                "positive_feedback": 0,
                "negative_feedback": 0,
                "performance_level": "No Data",
            }

        ratings = [record[2] for record in records]

        total_records = len(ratings)
        average_rating = sum(ratings) / total_records

        positive_feedback = sum(
            1 for rating in ratings if rating >= 4
        )

        negative_feedback = sum(
            1 for rating in ratings if rating <= 2
        )

        if average_rating >= 4:
            performance_level = "Excellent"
        elif average_rating >= 3:
            performance_level = "Good"
        else:
            performance_level = "Needs Improvement"

        return {
            "total_records": total_records,
            "average_rating": round(average_rating, 2),
            "positive_feedback": positive_feedback,
            "negative_feedback": negative_feedback,
            "performance_level": performance_level,
        }

    def compare_strategies(self):

        records = get_all_feedback()

        strategy_data = {}

        for record in records:

            strategy_id = record[5]
            rating = record[2]

            if strategy_id is None:
                continue

            if strategy_id not in strategy_data:
                strategy_data[strategy_id] = []

            strategy_data[strategy_id].append(rating)

        results = {}

        for strategy_id, ratings in strategy_data.items():

            results[strategy_id] = {
                "total_feedback": len(ratings),
                "average_rating": round(
                    sum(ratings) / len(ratings), 2
                ),
            }

        return results