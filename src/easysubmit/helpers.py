from __future__ import annotations

import sys
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Callable, Generic, Type, TypeVar

T = TypeVar("T")
R = TypeVar("R")


def get_current_venv() -> Path:
    return Path(sys.prefix).absolute()


@contextmanager
def capture(outfile: Path, errfile: Path):
    with (
        open(outfile, "w", encoding="utf-8") as outfile,
        open(errfile, "w", encoding="utf-8") as errfile,
    ):
        with redirect_stdout(outfile), redirect_stderr(errfile):
            yield


class ValidationError(ValueError):
    pass


class ValidatedProperty(Generic[T, R]):
    def __init__(self, validator: Callable[[Any], R]):
        self.validator = validator

    def __set_name__(self, owner: Type[T], name: str):
        self.name = name

    def __get__(self, instance: T | None, owner: Type[T]) -> R:
        if instance is None:
            return self
        try:
            return instance.__dict__[self.name]
        except KeyError:
            msg = f"{self.name} not set on {instance}"
            raise AttributeError(msg)

    def __set__(self, instance: T | None, value: R):
        if instance is None:
            msg = "can only be accessed via instance"
            raise AttributeError(msg)
        try:
            value = self.validator(value)
        except Exception as e:
            msg = f"validation failed for {self.name} with value {value}"
            raise ValidationError(msg) from e
        instance.__dict__[self.name] = value
