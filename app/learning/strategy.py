
"""
AEGIS Strategy System

Defines available strategies and their execution plans.
"""


class StrategySystem:

    def __init__(self):

        self.strategies = {
            "direct": {
                "name": "Direct Approach",
                "description": (
                    "Complete a task directly without "
                    "breaking it into smaller steps."
                ),
                "steps": [
                    "analyze_text"
                ]
            },

            "step_by_step": {
                "name": "Step-by-Step Approach",
                "description": (
                    "Break a task into smaller, manageable steps."
                ),
                "steps": [
                    "validate_input",
                    "count_words",
                    "count_characters",
                    "count_sentences"
                ]
            },

            "careful": {
                "name": "Careful Approach",
                "description": (
                    "Analyze the task before selecting an action."
                ),
                "steps": [
                    "validate_input",
                    "inspect_input",
                    "analyze_text",
                    "verify_result"
                ]
            }
        }

    def get_all_strategies(self):
        return self.strategies

    def get_strategy(self, strategy_id):
        return self.strategies.get(strategy_id)

    def get_execution_steps(self, strategy_id):

        strategy = self.get_strategy(strategy_id)

        if strategy is None:
            raise ValueError(
                f"Unknown strategy: {strategy_id}"
            )

        return strategy["steps"]
