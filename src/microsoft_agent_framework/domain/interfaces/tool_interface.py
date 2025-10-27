"""Tool interface definitions."""

from abc import ABC, abstractmethod
from typing import Any


class ITool(ABC):
    """Interface for all tool implementations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the tool's name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Get the tool's description."""
        pass

    @abstractmethod
    async def execute(self, parameters: dict[str, Any]) -> Any:
        """
        Execute the tool with the given parameters.

        Args:
            parameters: Tool parameters

        Returns:
            Tool execution result
        """
        pass

    @abstractmethod
    def get_schema(self) -> dict[str, Any]:
        """Get the tool's parameter schema."""
        pass


class IToolProvider(ABC):
    """Interface for tool providers."""

    @abstractmethod
    def get_tool(self, name: str) -> ITool | None:
        """
        Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool instance or None if not found
        """
        pass

    @abstractmethod
    def get_available_tools(self) -> list[str]:
        """Get list of available tool names."""
        pass

    @abstractmethod
    async def register_tool(self, tool: ITool) -> None:
        """
        Register a new tool.

        Args:
            tool: Tool to register
        """
        pass
