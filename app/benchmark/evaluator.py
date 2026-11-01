
"""
AEGIS Benchmark Evaluator

Compares execution results against independently
specified benchmark expectations.

Supports:
- Original text-analysis metrics.
- Extended Unicode character-analysis metrics.
- Single-metric and multi-metric research cases.
- Direct, step-by-step, and careful execution strategies.
"""


class BenchmarkEvaluator:
    """Evaluate benchmark execution results."""

    REQUIRED_METRICS = (
        "word_count",
        "character_count",
        "sentence_count",
    )

    SUPPORTED_METRICS = {
        "word_count": "count_words",
        "character_count": "count_characters",
        "sentence_count": "count_sentences",
        "letter_count": "count_letters",
        "digit_count": "count_digits",
        "whitespace_count": "count_whitespace",
        "punctuation_count": "count_punctuation",
        "symbol_count": "count_symbols",
    }

    def evaluate_case(self, case, execution_result):
        """Compare expected metrics with actual execution output."""

        self._validate_case(case)

        case_id = case["case_id"]
        expected = case["expected"]

        if not isinstance(execution_result, dict):
            return self._failure(
                case_id,
                expected,
                "Invalid execution result.",
            )

        if execution_result.get("error"):
            return self._failure(
                case_id,
                expected,
                f"Execution failed: {execution_result['error']}",
            )

        results = execution_result.get("results")

        if not isinstance(results, dict):
            return self._failure(
                case_id,
                expected,
                "Execution output is missing or invalid.",
            )

        actual = self._extract_metrics(results, expected)

        correct = actual == expected

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

    def _validate_case(self, case):
        """Validate benchmark case structure and expected metrics."""

        if not isinstance(case, dict):
            raise ValueError(
                "Benchmark case must be a dictionary."
            )

        if "case_id" not in case or "expected" not in case:
            raise ValueError(
                "Benchmark case must contain case_id and expected."
            )

        case_id = case["case_id"]

        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(
                "Benchmark case ID must be a non-empty string."
            )

        expected = case["expected"]

        if not isinstance(expected, dict):
            raise ValueError(
                "Expected results must be a dictionary."
            )

        if not expected:
            raise ValueError(
                "Expected results must contain at least one metric."
            )

        unsupported_metrics = (
            set(expected) - set(self.SUPPORTED_METRICS)
        )

        if unsupported_metrics:
            raise ValueError(
                "Unsupported benchmark metrics: "
                + ", ".join(sorted(unsupported_metrics))
            )

        # Preserve the original benchmark contract by default.
        # Research cases can explicitly enable partial metrics.
        allow_partial = case.get("allow_partial_metrics", False)

        if not isinstance(allow_partial, bool):
            raise ValueError(
                "allow_partial_metrics must be a boolean."
            )

        if not allow_partial:
            if not all(
                metric in expected
                for metric in self.REQUIRED_METRICS
            ):
                raise ValueError(
                    "Expected results are missing required metrics."
                )

        for metric, value in expected.items():
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(
                    f"Expected value for '{metric}' must be an integer."
                )

            if value < 0:
                raise ValueError(
                    f"Expected value for '{metric}' cannot be negative."
                )

    def _extract_metrics(self, results, expected):
        """Extract only the metrics requested by the benchmark case."""

        analysis = results.get("analyze_text")

        if isinstance(analysis, dict):
            # Direct and careful strategies.
            return {
                metric: analysis.get(metric)
                for metric in expected
            }

        # Step-by-step strategy.
        return {
            metric: results.get(self.SUPPORTED_METRICS[metric])
            for metric in expected
        }

    @staticmethod
    def _failure(case_id, expected, reason):
        """Return a consistent failed evaluation."""

        return {
            "case_id": case_id,
            "correct": False,
            "expected": expected,
            "actual": None,
            "reason": reason,
        }
