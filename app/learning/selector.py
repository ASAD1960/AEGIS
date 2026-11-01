"""
AEGIS Adaptive Strategy Selector

Selects strategies using historical feedback
and epsilon-greedy exploration.
"""

import random

from app.learning.strategy import StrategySystem
from app.learning.analyzer import LearningAnalyzer


class StrategySelector:

    def __init__(
        self,
        epsilon=0.2,
        min_samples=3
    ):

        if not 0 <= epsilon <= 1:
            raise ValueError("Epsilon must be between 0 and 1.")

        if min_samples < 1:
            raise ValueError("Minimum samples must be at least 1.")

        self.strategy_system = StrategySystem()
        self.analyzer = LearningAnalyzer()

        self.epsilon = epsilon
        self.min_samples = min_samples

    def select_strategy(self, strategy_id=None):

        strategies = self.strategy_system.get_all_strategies()

        # Manual selection remains available.
        if strategy_id is not None:

            strategy = self.strategy_system.get_strategy(strategy_id)

            if strategy is None:
                raise ValueError(
                    f"Unknown strategy: {strategy_id}"
                )

            return strategy

        strategy_ids = list(strategies.keys())

        # Analyze historical performance.
        performance = self.analyzer.compare_strategies()

        # Only trust strategies with enough feedback.
        experienced = {
            sid: data
            for sid, data in performance.items()
            if data["total_feedback"] >= self.min_samples
        }

        # Explore if there is insufficient experience.
        if not experienced:
            selected_id = random.choice(strategy_ids)

        # Epsilon-greedy exploration.
        elif random.random() < self.epsilon:
            selected_id = random.choice(strategy_ids)

        # Exploitation: choose the best-performing strategy.
        else:
            selected_id = max(
                experienced,
                key=lambda sid: experienced[sid]["average_rating"]
            )

        return strategies[selected_id]