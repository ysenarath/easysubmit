from __future__ import annotations

from typing import Any, Callable, Generic, Type, TypeVar

T = TypeVar("T")
R = TypeVar("R")


class ValidationError(ValueError): ...


class ValidatedProperty(Generic[T, R]):
    def __init__(self, validator: Callable[[Any], R]):
        self.validator = validator

    def __set_name__(self, owner: Type[T], name: str):
        self.name = name
        self.private_name = f"_{name}"

    def __get__(self, instance: T | None, owner: Type[T]) -> R:
        if instance is None:
            return self
        return getattr(instance, self.private_name)

    def __set__(self, instance: T | None, value: R):
        if instance is None:
            msg = "can only be accessed via instance"
            raise AttributeError(msg)
        try:
            value = self.validator(value)
        except Exception as e:
            msg = f"validation failed for {self.name} with value {value}"
            raise ValueError(msg) from e
        setattr(instance, self.private_name, value)
