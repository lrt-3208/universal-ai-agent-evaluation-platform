"""SPI Registry base class and common interfaces

Reference: ../docs/phases/phase-1-foundation.md §8
"""

from abc import ABC, abstractmethod
from typing import Generic, Type, TypeVar

T = TypeVar("T")


class Registry(ABC, Generic[T]):
    """SPI unified registry base class

    All plugin registries (AdapterRegistry, JudgeRegistry, etc.) inherit from this.
    Built-in implementations are registered via register() at import time.
    """

    _registry: dict[str, Type] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Each subclass gets its own registry dict
        cls._registry = {}

    @classmethod
    def register(cls, name: str, impl: Type[T]) -> None:
        """Register an implementation by name"""
        cls._registry[name] = impl

    @classmethod
    def create(cls, name: str, **kwargs) -> T:
        """Create an instance by name"""
        if name not in cls._registry:
            available = list(cls._registry.keys())
            raise KeyError(f"Unknown implementation: '{name}'. Available: {available}")
        return cls._registry[name](**kwargs)

    @classmethod
    def list_registered(cls) -> list[str]:
        """List all registered implementation names"""
        return list(cls._registry.keys())

    @classmethod
    def get_class(cls, name: str) -> Type[T]:
        """Get the class (not instance) by name"""
        if name not in cls._registry:
            available = list(cls._registry.keys())
            raise KeyError(f"Unknown implementation: '{name}'. Available: {available}")
        return cls._registry[name]
