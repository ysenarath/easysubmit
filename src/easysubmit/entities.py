from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from nightjar import dispatch, from_dict, to_dict
from typing_extensions import Literal

from easysubmit.helpers import get_fingerprint

__all__ = [
    "Job",
    "Cluster",
    "Task",
    "TaskConfig",
]


class Cluster:
    def schedule(
        self,
        __args: Sequence[str],
        __format_hook: Callable | None = None,
        **kwargs,
    ) -> Job:
        raise NotImplementedError

    @property
    def current_job(self) -> Job:
        # Job of the current job
        return self.get_job()

    @property
    def current_array_job(self) -> Job:
        # Job of the current job array (i.e., the first job in the array)
        return self.get_array_job()

    def get_job(self, job_id: str | None = None) -> Job:
        raise NotImplementedError

    def get_array_job(self, job_id: str | None = None) -> Job:
        raise NotImplementedError


class Job:
    def __init__(self, id: int | str):
        self.id = id

    @property
    def id(self) -> str:
        try:
            return self.__dict__["id"]
        except KeyError:
            msg = f"'{self.__class__.__name__}' object has no attribute 'id'"
            raise AttributeError(msg) from None

    @id.setter
    def id(self, value: Any):
        if not value or not isinstance(value, str):
            msg = f"'{self.__class__.__name__}' id must be a non-empty string"
            raise TypeError(msg)
        self.__dict__["id"] = value

    def get_status(
        self,
    ) -> Literal["PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", "UNKNOWN"]:
        raise NotImplementedError

    def cancel(self):
        raise NotImplementedError

    @classmethod
    def is_available(cls) -> bool:
        return False


@dataclass(eq=False)
class TaskConfig:
    """Base for dataclass task configurations with declared dispatch fields."""

    def to_dict(self) -> dict:
        return to_dict(self)

    @classmethod
    def from_dict(cls, data: dict) -> TaskConfig:
        """Convert a concrete config, or dispatch the base family to a task config.

        Loading through TaskConfig constructs the registered task. Constructors
        should only store configuration; perform work in run().
        """
        if cls is TaskConfig:
            return dispatch(cls, data).config
        return from_dict(cls, data)

    @property
    def fingerprint(self) -> str:
        return get_fingerprint(self.to_dict())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TaskConfig):
            raise NotImplementedError
        # both id and fingerprint must be equal
        return self.fingerprint == other.fingerprint

    @classmethod
    def from_json(cls, path: str | Path) -> TaskConfig:
        with open(path, "r", encoding="utf-8") as f:
            config = cls.from_dict(json.load(f))
        return config


class Task:
    config: TaskConfig

    def __init__(self, config: TaskConfig):
        self.config = config

    def run(self):
        raise NotImplementedError
