
from app.learning.strategy import StrategySystem


def test_all_expected_strategies_are_available():

    strategy_system = StrategySystem()

    strategies = strategy_system.get_all_strategies()

    expected_strategies = {
        "direct",
        "step_by_step",
        "careful",
    }

    assert set(strategies.keys()) == expected_strategies


def test_step_by_step_strategy_can_be_retrieved():

    strategy_system = StrategySystem()

    strategy = strategy_system.get_strategy("step_by_step")

    assert strategy is not None
    assert strategy["name"]
    assert strategy["description"]
    assert strategy["steps"]


def main():

    strategy_system = StrategySystem()

    strategies = strategy_system.get_all_strategies()

    print("=" * 45)
    print("       AEGIS AVAILABLE STRATEGIES")
    print("=" * 45)

    for strategy_id, strategy in strategies.items():

        print(f"\nID: {strategy_id}")
        print(f"Name: {strategy['name']}")
        print(f"Description: {strategy['description']}")

    print("\n" + "=" * 45)

    selected = strategy_system.get_strategy("step_by_step")

    print("TEST: Retrieve Individual Strategy")
    print(f"Selected: {selected['name']}")

    print("=" * 45)


if __name__ == "__main__":
    main()
