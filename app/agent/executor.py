
"""
AEGIS Execution Engine

Executes tasks using distinct deterministic execution strategies:

1. Direct:
   Uses one-pass text analysis.

2. Step-by-step:
   Calculates each metric independently.

3. Careful:
   Performs one-pass analysis and recalculates every metric
   using individual methods to verify the result.

Note:
   Verification uses separate methods within TextAnalysisTool.
   It is not an independent implementation of the algorithms.
"""

from app.learning.strategy import StrategySystem
from app.tools.text_tool import TextAnalysisTool


class TaskExecutor:

    METRIC_METHODS = {
        "word_count": "count_words",
        "character_count": "count_characters",
        "sentence_count": "count_sentences",
        "letter_count": "count_letters",
        "digit_count": "count_digits",
        "whitespace_count": "count_whitespace",
        "punctuation_count": "count_punctuation",
        "symbol_count": "count_symbols",
    }

    STEP_TO_METRIC = {
        "count_words": "word_count",
        "count_characters": "character_count",
        "count_sentences": "sentence_count",
        "count_letters": "letter_count",
        "count_digits": "digit_count",
        "count_whitespace": "whitespace_count",
        "count_punctuation": "punctuation_count",
        "count_symbols": "symbol_count",
    }

    def __init__(self):
        self.strategy_system = StrategySystem()
        self.text_tool = TextAnalysisTool()

    def _execute_direct(
        self,
        text,
        results,
        history,
        counters,
    ):
        """Execute one-pass analysis."""

        counters["one_pass_analysis_calls"] += 1

        analysis = self.text_tool.analyze(text)

        results["analyze_text"] = analysis
        history.append("analyze_text")

        return analysis

    def _execute_step_by_step(
        self,
        text,
        results,
        history,
        counters,
    ):
        """Calculate every metric through its individual method."""

        analysis = {}

        for step, metric in self.STEP_TO_METRIC.items():

            method_name = self.METRIC_METHODS[metric]
            method = getattr(self.text_tool, method_name)

            counters["individual_metric_calls"] += 1

            value = method(text)

            results[step] = value
            analysis[metric] = value
            history.append(step)

        results["analysis_summary"] = analysis

        return analysis

    def _execute_careful(
        self,
        text,
        results,
        history,
        counters,
    ):
        """Analyze and verify every metric using individual methods."""

        self.text_tool._validate_text(text)

        results["validate_input"] = (
            "Input validated successfully."
        )
        history.append("validate_input")

        inspection = {
            "input_length": len(text),
            "input_type": type(text).__name__,
        }

        results["inspect_input"] = inspection
        history.append("inspect_input")

        counters["one_pass_analysis_calls"] += 1

        analysis = self.text_tool.analyze(text)

        results["analyze_text"] = analysis
        history.append("analyze_text")

        verification = {}

        for metric, method_name in self.METRIC_METHODS.items():

            method = getattr(self.text_tool, method_name)

            counters["individual_metric_calls"] += 1
            counters["verification_operations"] += 1

            independently_calculated = method(text)

            verification[metric] = {
                "reported": analysis[metric],
                "independently_calculated": independently_calculated,
                "matches": (
                    analysis[metric] == independently_calculated
                ),
            }

        all_verified = all(
            item["matches"]
            for item in verification.values()
        )

        results["verification"] = verification
        results["verify_result"] = all_verified
        history.append("verify_result")

        if not all_verified:
            raise RuntimeError(
               "Result verification failed."
            )

        return analysis

    def execute(self, text, strategy_id):

        strategy = self.strategy_system.get_strategy(strategy_id)

        if strategy is None:
            raise ValueError(
                f"Unknown strategy: {strategy_id}"
            )

        # Reset instrumentation for this execution.
        self.text_tool.reset_validation_count()

        results = {}
        execution_history = []

        counters = {
            "one_pass_analysis_calls": 0,
            "individual_metric_calls": 0,
            "verification_operations": 0,
        }

        if strategy_id == "direct":

            self._execute_direct(
                text,
                results,
                execution_history,
                counters,
            )

        elif strategy_id == "step_by_step":

            self._execute_step_by_step(
                text,
                results,
                execution_history,
                counters,
            )

        elif strategy_id == "careful":

            self._execute_careful(
                text,
                results,
                execution_history,
                counters,
            )

        else:
            raise ValueError(
                f"Unsupported strategy: {strategy_id}"
            )

        execution_details = {
            "strategy_id": strategy_id,
            "one_pass_analysis_calls": (
                counters["one_pass_analysis_calls"]
            ),
            "individual_metric_calls": (
                counters["individual_metric_calls"]
            ),
            "analysis_and_metric_method_calls": (
                counters["one_pass_analysis_calls"]
                + counters["individual_metric_calls"]
            ),
            "verification_operations": (
                counters["verification_operations"]
            ),
            "input_validation_calls": (
                self.text_tool.input_validation_calls
            ),
            "execution_step_count": len(execution_history),
            "verification_passed": results.get(
                "verify_result"
            ),
            "execution_history": execution_history.copy(),
        }

        return {
            "strategy": strategy["name"],
            "results": results,
            "execution_history": execution_history,
            "execution_details": execution_details,
        }
