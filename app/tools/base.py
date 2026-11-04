"""
AEGIS Base Tool Interface

Defines the common contract that all AEGIS tools
must implement.
"""

from abc import ABC, abstractmethod


class BaseTool(ABC):
    """
    Abstract base class for all AEGIS tools.

    Every concrete tool must provide:
        - A unique name.
        - A description.
        - An execute() method.
    """

    name = "base_tool"
    description = "Base interface for AEGIS tools."

    @abstractmethod
    def execute(self, **kwargs):
        """
        Execute the tool's operation.

        Individual tools define their own accepted
        keyword arguments and return values.
        """
        raise NotImplementedError

    def get_metadata(self):
        """Return basic information about the tool."""

        return {
            "name": self.name,
            "description": self.description,
        }