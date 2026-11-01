
"""
AEGIS Agent Core

Main agent connecting tools, strategies,
execution and feedback.
"""

from app.agent.identity import (
    AGENT_NAME,
    AGENT_ROLE,
    AGENT_CAPABILITIES,
)

from app.tools.text_tool import TextAnalysisTool
from app.learning.selector import StrategySelector
from app.learning.feedback import FeedbackSystem
from app.agent.executor import TaskExecutor


class Agent:

    def __init__(self):

        self.name = AGENT_NAME
        self.role = AGENT_ROLE
        self.capabilities = AGENT_CAPABILITIES
        self.status = "Initialized"

        self.text_tool = TextAnalysisTool()
        self.strategy_selector = StrategySelector()
        self.feedback_system = FeedbackSystem()
        self.executor = TaskExecutor()

        self.last_execution = None

    def get_status(self):
        return self.status

    def introduce(self):

        print(f"My name is {self.name}.")
        print(self.role)
        print(f"My current status is: {self.status}")

    def analyze_text(self, text):

        self.status = "Working"

        try:
            return self.text_tool.analyze(text)

        finally:
            self.status = "Initialized"

    def choose_strategy(self):
        return self.strategy_selector.select_strategy()

    def perform_task(self, text, strategy_id=None):

        self.status = "Working"
        self.last_execution = None

        try:

            if strategy_id is None:

                strategy = self.choose_strategy()

                strategy_id = next(
                    key
                    for key, value in
                    self.strategy_selector.strategy_system
                    .get_all_strategies().items()
                    if value == strategy
                )

            result = self.executor.execute(
                text,
                strategy_id
            )

            result["strategy_id"] = strategy_id

            self.last_execution = {
                "task": text,
                "strategy_id": strategy_id,
            }

            return result

        finally:
            self.status = "Initialized"

    def record_feedback(self, rating, comment=""):

        if self.last_execution is None:
            raise RuntimeError(
                "Execute a task before recording feedback."
            )

        return self.feedback_system.record_feedback(
            task=self.last_execution["task"],
            rating=rating,
            comment=comment,
            strategy_id=self.last_execution["strategy_id"],
        )
