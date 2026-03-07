"""Base tool interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    """Result from a tool execution."""

    success: bool
    data: Any = None
    error: str | None = None


class BaseTool(ABC):
    """Abstract base class for agent tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the tool name."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Return a description of what the tool does."""
        ...

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters.

        Returns:
            ToolResult with success status and data/error.
        """
        ...

    def is_available(self) -> bool:
        """Check if the tool is available (credentials configured, etc.)."""
        return True
