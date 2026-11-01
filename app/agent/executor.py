
"""
AEGIS Execution Engine

Executes tasks according to the selected strategy.
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

            elif step == "count_words":

                result = len(text.split())

            elif step == "count_characters":

                result = len(text)

            elif step == "count_sentences":

                result = len([
                    sentence
                    for sentence in (
                        text.replace("!", ".")
                        .replace("?", ".")
                        .split(".")
                    )
                    if sentence.strip()
                ])

            elif step == "analyze_text":

                result = self.text_tool.analyze(text)

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
