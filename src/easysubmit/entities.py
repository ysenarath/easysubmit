from __future__ import annotations

from collections.abc import Sequence
import json
from pathlib import Path
from typing import Any, Callable, ClassVar

from typing_extensions import Literal
from nightjar import AutoModule, BaseModule, BaseConfig
from easysubmit.helpers import get_fingerprint

__all__ = [
    "Job",
    "Cluster",
    "Task",
    "TaskConfig",
    "AutoTask",
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


class TaskConfig(BaseConfig, dispatch="name"):
    name: ClassVar[str]

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


class Task(BaseModule):
    config: TaskConfig

    def run(self):
        raise NotImplementedError


class AutoTask(AutoModule):
    def __new__(cls, config: Any) -> Task:
        if not isinstance(config, TaskConfig):
            config = TaskConfig.from_dict(config)
        return super().__new__(cls, config)
