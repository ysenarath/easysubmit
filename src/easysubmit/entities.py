from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Sequence
from typing import Any, Callable

from typing_extensions import Literal, Self

__all__ = [
    "Job",
    "Cluster",
    "Task",
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
        return self.get_job()

    def get_job(self, job_id: str | None = None) -> Job:
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


class Task:
    def __init__(self, config: dict, id: int | str | None = None):
        self.config = config
        self.id = id

    @property
    def config(self) -> dict:
        return self.__dict__.get("config", {})

    @config.setter
    def config(self, value: Any):
        if value is None:
            raise ValueError("Task config cannot be None")
        if not isinstance(value, dict):
            raise TypeError("Task config must be a dictionary")
        self.__dict__["config"] = value

    @property
    def id(self) -> str:
        id_ = self.__dict__.get("id", None)
        if id_ is None:
            # if id is None, we use the fingerprint
            return self.fingerprint
        return id_

    @id.setter
    def id(self, value: Any):
        if value is None:
            return
        if not isinstance(value, str):
            raise TypeError("Task id must be a string")
        if not value:
            raise ValueError("Task id cannot be empty")
        self.__dict__["id"] = value

    def to_dict(self) -> dict:
        """
        Convert the Task object to a dictionary representation.
        """
        return {
            "id": self.__dict__.get("id", None),
            "config": self.config,
        }

    @classmethod
    def read_json(cls, path: Any) -> Self:
        """
        Read a JSON file and return a Task object.
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(config=data.get("config"), id=data.get("id"))

    def write_json(self, path: Any, mode: str = "x") -> None:
        with open(path, mode=mode, encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=4, sort_keys=True)

    @property
    def fingerprint(self) -> str:
        # 1. Serialize to canonical JSON string
        raw = json.dumps(
            self.to_dict(),
            sort_keys=True,  # Ensures key order consistency
            separators=(",", ":"),  # Ensures compact, consistent spacing
            ensure_ascii=False,  # Allows unicode characters
        )

        # 2. Encode the string to bytes (required by hash functions)
        raw_bytes = raw.encode("utf-8")

        # 3. Hash using BLAKE2b with a 16-byte (128-bit) digest size
        #    Use .digest() to get the raw bytes of the hash
        #    Using 16 bytes provides good collision resistance and a shorter hash.
        #    For 256-bit (like SHA-256), use digest_size=32.
        hasher = hashlib.blake2b(digest_size=16)
        hasher.update(raw_bytes)
        encoded_hash_bytes = hasher.digest()

        # 4. Encode the raw hash bytes using URL-safe Base64
        base64_encoded = base64.urlsafe_b64encode(encoded_hash_bytes)

        # 5. Decode the Base64 bytes into a string
        return base64_encoded.decode("utf-8").rstrip("=")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Task):
            raise NotImplementedError
        # both id and fingerprint must be equal
        return self.id == other.id and self.fingerprint == other.fingerprint

    def run(self):
        raise NotImplementedError
