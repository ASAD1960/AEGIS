
import pytest

from app.tools.base import BaseTool
from app.tools.registry import ToolRegistry
from app.tools.text_tool import TextAnalysisTool
from app.tools.calculator_tool import CalculatorTool


@pytest.fixture
def registry():
    return ToolRegistry()


def test_register_text_tool(registry):
    tool = TextAnalysisTool()

    registry.register(tool)

    assert registry.has_tool("text_analysis")
    assert registry.get("text_analysis") is tool


def test_register_calculator_tool(registry):
    tool = CalculatorTool()

    registry.register(tool)

    assert registry.has_tool("calculator")
    assert registry.get("calculator") is tool


def test_register_multiple_tools(registry):
    registry.register(TextAnalysisTool())
    registry.register(CalculatorTool())

    assert registry.has_tool("text_analysis")
    assert registry.has_tool("calculator")
    assert len(registry.list_tools()) == 2


def test_reject_non_base_tool(registry):
    with pytest.raises(TypeError, match="inherit from BaseTool"):
        registry.register(object())


def test_reject_duplicate_tool_name(registry):
    registry.register(TextAnalysisTool())

    with pytest.raises(ValueError, match="already registered"):
        registry.register(TextAnalysisTool())


def test_retrieve_unknown_tool(registry):
    with pytest.raises(KeyError, match="not registered"):
        registry.get("unknown_tool")


def test_has_tool_returns_false_for_unknown_tool(registry):
    assert registry.has_tool("unknown_tool") is False


def test_list_tools_returns_metadata(registry):
    registry.register(TextAnalysisTool())
    registry.register(CalculatorTool())

    tools = registry.list_tools()

    assert tools == [
        {
            "name": "text_analysis",
            "description": (
                "Analyzes text and calculates eight text metrics."
            ),
        },
        {
            "name": "calculator",
            "description": (
                "Performs addition, subtraction, multiplication, "
                "division, modulus, and power operations."
            ),
        },
    ]


def test_unregister_tool(registry):
    registry.register(TextAnalysisTool())

    registry.unregister("text_analysis")

    assert registry.has_tool("text_analysis") is False


def test_unregister_unknown_tool(registry):
    with pytest.raises(KeyError, match="not registered"):
        registry.unregister("unknown_tool")


def test_registered_tool_can_execute(registry):
    registry.register(CalculatorTool())

    result = registry.get("calculator").execute(
        operation="multiply",
        a=12,
        b=8,
    )

    assert result["result"] == 96


def test_base_tool_is_abstract():
    from inspect import isabstract

    assert isabstract(BaseTool)
