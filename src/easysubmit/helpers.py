from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Callable, Generic, Type, TypeVar

from easysubmit.config import EASYSUBMIT_PATH

__all__ = [
    "gettempdir",
]


T = TypeVar("T")
R = TypeVar("R")


def gettempdir() -> str:
    """Get the temporary directory from environment or default."""
    temp_dir = Path(EASYSUBMIT_PATH) / "temp"
    # make sure the directory exists
    os.makedirs(temp_dir, exist_ok=True)
    return str(temp_dir)


def format_hook(s: str, base_dir: str | Path) -> str:
    return s.format(BASE_DIR=str(base_dir))


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


def get_fingerprint(obj: Any) -> str:
    # 1. Serialize to canonical JSON string
    raw = json.dumps(
        obj,
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
