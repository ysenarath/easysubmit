from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

try:
    from scalene import scalene_profiler
except ImportError:
    scalene_profiler = None

SCALENE_MISSING_ERROR = "scalene profiler is not installed"


def is_profiler_avilable() -> bool:
    """Check if the Scalene profiler is available."""
    return scalene_profiler is not None


@contextmanager
def enable_profiling() -> Generator[None, None, None]:
    if scalene_profiler is None:
        raise ImportError(SCALENE_MISSING_ERROR)
    scalene_profiler.start()
    try:
        yield
    finally:
        scalene_profiler.stop()


def start_profiling() -> None:
    if scalene_profiler is None:
        raise ImportError(SCALENE_MISSING_ERROR)
    scalene_profiler.start()


def stop_profiling() -> None:
    if scalene_profiler is None:
        raise ImportError(SCALENE_MISSING_ERROR)
    scalene_profiler.stop()
