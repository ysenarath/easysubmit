from __future__ import annotations

import base64
import hashlib
import importlib
import importlib.util
import json
import os
import sys
import time
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar

from easysubmit.config import EASYSUBMIT_PATH

__all__ = [
    "gettempdir",
]


T = TypeVar("T")
R = TypeVar("R")
Type = type


def import_function(file_or_module: str, func_name: str) -> callable:
    if os.path.isfile(file_or_module):
        # If path exists and is a file, load as module from path
        module_name = (
            f"_temp_module_{os.path.basename(file_or_module).replace('.', '_')}"
        )
        spec = importlib.util.spec_from_file_location(module_name, file_or_module)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from path: {file_or_module}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    else:
        # Treat as regular module name
        module = importlib.import_module(file_or_module)
    if not hasattr(module, func_name):
        raise AttributeError(f"Function '{func_name}' not found in {file_or_module}")
    func = getattr(module, func_name)
    if not callable(func):
        raise TypeError(f"'{func_name}' exists in {file_or_module} but is not callable")
    return func


def wait_for_file(path, retries=10, delay=0.1):
    last_size = -1
    for _ in range(retries):
        try:
            size = os.path.getsize(path)
            if size > 0 and size == last_size:
                return True
            last_size = size
        except FileNotFoundError:
            pass
        time.sleep(delay)
    return False


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
    """Context manager to capture stdout and stderr to specified files."""
    with (
        open(outfile, "w", encoding="utf-8") as outfile,
        open(errfile, "w", encoding="utf-8") as errfile,
        redirect_stdout(outfile),
        redirect_stderr(errfile),
    ):
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
