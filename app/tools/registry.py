
"""
AEGIS Tool Registry

Maintains the collection of tools available to AEGIS
and provides methods to register, discover, and retrieve them.
"""

from app.tools.base import BaseTool


class ToolRegistry:
    """Register and manage AEGIS tools."""

    def __init__(self):
        self._tools = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool using its unique name."""

        if not isinstance(tool, BaseTool):
            raise TypeError("Registered tools must inherit from BaseTool.")

        name = tool.name

        if not isinstance(name, str) or not name.strip():
            raise ValueError("Tool name must be a non-empty string.")

        if name in self._tools:
            raise ValueError(f"Tool '{name}' is already registered.")

        self._tools[name] = tool

    def get(self, name: str) -> BaseTool:
        """Retrieve a registered tool by name."""

        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered.")

        return self._tools[name]

    def list_tools(self) -> list:
        """Return metadata for all registered tools."""

        return [
            tool.get_metadata()
            for tool in self._tools.values()
        ]

    def has_tool(self, name: str) -> bool:
        """Check whether a tool is registered."""

        return name in self._tools

    def unregister(self, name: str) -> None:
        """Remove a registered tool."""

        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered.")

        del self._tools[name]
