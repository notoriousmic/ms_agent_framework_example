"""Service interface definitions."""

from abc import ABC, abstractmethod


class IService(ABC):
    """Base interface for all services."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the service."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup service resources."""
        pass

    @property
    @abstractmethod
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        pass
