from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

try:
    from scalene import scalene_profiler
except ImportError:
    scalene_profiler = None  # type: ignore[assignment]

SCALENE_DEPENDENCY_MISSING_ERROR = "Scalene profiler is not installed. Please install it with `pip install easysubmit[scalene]`."


def is_profiler_avilable() -> bool:
    """Check if the Scalene profiler is available."""
    return scalene_profiler is not None


@contextmanager
def enable_profiling() -> Generator[None, None, None]:
    if scalene_profiler is None:
        raise ImportError(SCALENE_DEPENDENCY_MISSING_ERROR)
    scalene_profiler.start()
    try:
        yield
    finally:
        scalene_profiler.stop()


def start_profiling() -> None:
    if scalene_profiler is None:
        raise ImportError(SCALENE_DEPENDENCY_MISSING_ERROR)
    scalene_profiler.start()


def stop_profiling() -> None:
    if scalene_profiler is None:
        raise ImportError(SCALENE_DEPENDENCY_MISSING_ERROR)
    scalene_profiler.stop()
