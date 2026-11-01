
"""
AEGIS Execution Engine

Executes tasks according to the selected strategy.

All text-analysis metrics are obtained from TextAnalysisTool
to maintain consistent counting rules across strategies.
"""

from app.learning.strategy import StrategySystem
from app.tools.text_tool import TextAnalysisTool


class TaskExecutor:

    def __init__(self):

        self.strategy_system = StrategySystem()
        self.text_tool = TextAnalysisTool()

    def execute(self, text, strategy_id):

        strategy = self.strategy_system.get_strategy(strategy_id)

        if strategy is None:
            raise ValueError(
                f"Unknown strategy: {strategy_id}"
            )

        steps = self.strategy_system.get_execution_steps(
            strategy_id
        )

        results = {}
        execution_history = []

        # Cache the analysis so it is calculated only once.
        analysis = None

        def get_analysis():

            nonlocal analysis

            if analysis is None:
                analysis = self.text_tool.analyze(text)

            return analysis

        # Map execution steps to authoritative analysis metrics.
        metric_steps = {
            "count_words": "word_count",
            "count_characters": "character_count",
            "count_sentences": "sentence_count",
            "count_letters": "letter_count",
            "count_digits": "digit_count",
            "count_whitespace": "whitespace_count",
            "count_punctuation": "punctuation_count",
            "count_symbols": "symbol_count",
        }

        for step in steps:

            if step == "validate_input":

                if not isinstance(text, str) or not text.strip():
                    raise ValueError("Text cannot be empty.")

                result = "Input validated successfully."

            elif step == "inspect_input":

                result = {
                    "input_length": len(text),
                    "input_type": type(text).__name__,
                }

            elif step in metric_steps:

                metric_name = metric_steps[step]
                result = get_analysis()[metric_name]

            elif step == "analyze_text":

                result = get_analysis()

            elif step == "verify_result":

                result = (
                    "Analysis completed successfully."
                    if results.get("analyze_text")
                    else "Analysis result not found."
                )

            else:

                raise ValueError(
                    f"Unknown execution step: {step}"
                )

            results[step] = result
            execution_history.append(step)

        return {
            "strategy": strategy["name"],
            "results": results,
            "execution_history": execution_history,
        }
