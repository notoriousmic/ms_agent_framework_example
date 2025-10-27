"""Dependency injection container for managing service dependencies."""

from collections.abc import Callable
from typing import Any, TypeVar, get_type_hints

T = TypeVar("T")


class DIContainer:
    """Simple dependency injection container."""

    def __init__(self):
        self._services: dict[type, Any] = {}
        self._factories: dict[type, Callable[[], Any]] = {}
        self._singletons: dict[type, Any] = {}

    def register_singleton(self, service_type: type[T], instance: T) -> None:
        """Register a singleton instance."""
        self._singletons[service_type] = instance

    def register_transient(self, service_type: type[T], factory: Callable[[], T]) -> None:
        """Register a transient service factory."""
        self._factories[service_type] = factory

    def register_service(self, service_type: type[T], implementation: type[T]) -> None:
        """Register a service implementation."""
        self._services[service_type] = implementation

    def get(self, service_type: type[T]) -> T:
        """Get a service instance."""
        # Check singletons first
        if service_type in self._singletons:
            return self._singletons[service_type]

        # Check transient factories
        if service_type in self._factories:
            return self._factories[service_type]()

        # Check registered services
        if service_type in self._services:
            implementation = self._services[service_type]
            return self._create_instance(implementation)

        # Try to create instance if it's a concrete class
        if hasattr(service_type, "__init__"):
            return self._create_instance(service_type)

        raise ValueError(f"Service {service_type} is not registered")

    def _create_instance(self, service_class: type[T]) -> T:
        """Create an instance with dependency injection."""
        try:
            # Get constructor type hints
            hints = get_type_hints(service_class.__init__)
            kwargs = {}

            for param_name, param_type in hints.items():
                if param_name == "return":
                    continue
                try:
                    kwargs[param_name] = self.get(param_type)
                except ValueError:
                    # Skip parameters that can't be resolved
                    pass

            return service_class(**kwargs)
        except Exception:
            # Fallback to no-args constructor
            return service_class()


# Global DI container
container = DIContainer()
