from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Callable

from typing_extensions import Literal

__all__ = [
    "Cluster",
    "Job",
]


class Cluster:
    def schedule(
        self,
        __args: Sequence[str],
        __format_hook: Callable | None = None,
        /,
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
