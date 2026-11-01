
"""
AEGIS Benchmark Evaluator

Compares individual execution results against
independently specified benchmark expectations.
"""


class BenchmarkEvaluator:

    REQUIRED_METRICS = (
        "word_count",
        "character_count",
        "sentence_count",
    )

    def evaluate_case(self, case, execution_result):

        if not isinstance(case, dict):
            raise ValueError("Benchmark case must be a dictionary.")

        if "case_id" not in case or "expected" not in case:
            raise ValueError(
                "Benchmark case must contain case_id and expected."
            )

        expected = case["expected"]

        if not isinstance(expected, dict):
            raise ValueError("Expected results must be a dictionary.")

        if not all(
            metric in expected
            for metric in self.REQUIRED_METRICS
        ):
            raise ValueError(
                "Expected results are missing required metrics."
            )

        case_id = case["case_id"]

        if not isinstance(execution_result, dict):
            return {
                "case_id": case_id,
                "correct": False,
                "expected": expected,
                "actual": None,
                "reason": "Invalid execution result.",
            }

        if execution_result.get("error"):
            return {
                "case_id": case_id,
                "correct": False,
                "expected": expected,
                "actual": None,
                "reason": (
                    f"Execution failed: "
                    f"{execution_result['error']}"
                ),
            }

        results = execution_result.get("results")

        if not isinstance(results, dict):
            return {
                "case_id": case_id,
                "correct": False,
                "expected": expected,
                "actual": None,
                "reason": "Execution output is missing or invalid.",
            }

        # Direct and Careful strategies.
        if isinstance(results.get("analyze_text"), dict):

            actual = results["analyze_text"]

        # Step-by-Step strategy.
        else:

            actual = {
                "word_count": results.get("count_words"),
                "character_count": results.get(
                    "count_characters"
                ),
                "sentence_count": results.get(
                    "count_sentences"
                ),
            }

        # Compare only the required metrics.
        actual = {
            metric: actual.get(metric)
            for metric in self.REQUIRED_METRICS
        }

        correct = actual == {
            metric: expected[metric]
            for metric in self.REQUIRED_METRICS
        }

        return {
            "case_id": case_id,
            "correct": correct,
            "expected": expected,
            "actual": actual,
            "reason": (
                "All expected metrics matched."
                if correct
                else "One or more metrics did not match."
            ),
        }
