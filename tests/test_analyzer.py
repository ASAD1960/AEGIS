
from app.learning.analyzer import LearningAnalyzer


def test_analyzer_returns_performance_metrics():

    analyzer = LearningAnalyzer()

    results = analyzer.analyze_performance()

    assert isinstance(results, dict)

    expected_fields = [
        "total_records",
        "average_rating",
        "positive_feedback",
        "negative_feedback",
        "performance_level",
    ]

    for field in expected_fields:
        assert field in results


def test_analyzer_returns_valid_feedback_counts():

    analyzer = LearningAnalyzer()

    results = analyzer.analyze_performance()

    assert results["total_records"] >= 0
    assert results["positive_feedback"] >= 0
    assert results["negative_feedback"] >= 0

    assert (
        results["positive_feedback"]
        + results["negative_feedback"]
        <= results["total_records"]
    )


def test_analyzer_returns_valid_average_rating():

    analyzer = LearningAnalyzer()

    results = analyzer.analyze_performance()

    if results["total_records"] > 0:
        assert 1 <= results["average_rating"] <= 5


def main():

    analyzer = LearningAnalyzer()

    results = analyzer.analyze_performance()

    print("=" * 45)
    print("       AEGIS LEARNING ANALYSIS")
    print("=" * 45)

    print(f"Total Feedback: {results['total_records']}")
    print(f"Average Rating: {results['average_rating']}/5")
    print(f"Positive Feedback: {results['positive_feedback']}")
    print(f"Negative Feedback: {results['negative_feedback']}")
    print(f"Performance Level: {results['performance_level']}")

    print("=" * 45)


if __name__ == "__main__":
    main()
