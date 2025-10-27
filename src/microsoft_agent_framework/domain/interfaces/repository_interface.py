"""Repository interface definitions."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class IRepository(ABC, Generic[T]):
    """Generic repository interface."""

    @abstractmethod
    async def get_by_id(self, id: str) -> T | None:
        """Get entity by ID."""
        pass

    @abstractmethod
    async def get_all(self) -> list[T]:
        """Get all entities."""
        pass

    @abstractmethod
    async def save(self, entity: T) -> T:
        """Save entity."""
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete entity by ID."""
        pass

    @abstractmethod
    async def exists(self, id: str) -> bool:
        """Check if entity exists."""
        pass
