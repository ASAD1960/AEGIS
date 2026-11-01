
from app.learning.selector import StrategySelector


def test_selector_returns_a_valid_strategy():

    selector = StrategySelector()

    strategy = selector.select_strategy()

    assert isinstance(strategy, dict)
    assert strategy["name"]
    assert strategy["description"]


def test_selector_supports_manual_strategy_selection():

    selector = StrategySelector()

    strategy = selector.select_strategy("careful")

    assert strategy["name"] == "Careful Approach"


def test_selector_rejects_unknown_strategy():

    selector = StrategySelector()

    try:
        selector.select_strategy("unknown_strategy")
    except (ValueError, KeyError):
        pass
    else:
        raise AssertionError(
            "Selector should reject an unknown strategy."
        )


def main():

    selector = StrategySelector()

    print("=" * 45)
    print("       AEGIS STRATEGY SELECTOR")
    print("=" * 45)

    strategy = selector.select_strategy()

    print("Default Strategy:")
    print(f"Name: {strategy['name']}")
    print(f"Description: {strategy['description']}")

    print("\nTesting Custom Selection:")

    strategy = selector.select_strategy("careful")

    print(f"Selected: {strategy['name']}")

    print("=" * 45)


if __name__ == "__main__":
    main()
