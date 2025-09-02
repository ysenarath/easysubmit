from __future__ import annotations

import functools
import importlib
import importlib.util
import inspect
import os
import sys
import tempfile
import time
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

import click
import dill
from typing_extensions import Self

from easysubmit.entities import Cluster, Job, Task, TaskConfig
from easysubmit.helpers import format_hook, gettempdir

FSW_TASK_NAME = "FileSystemWorker"


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


class BoundFunction:
    __slots__ = ("module", "name", "args", "kwargs")

    def __init__(self, __func: Callable, /, *args, **kwargs):
        m = inspect.getmodule(__func)
        if m.__name__ == "__main__":
            module, name = m.__file__, __func.__name__
        else:
            module, name = m.__name__, __func.__name__
        self.module = module
        self.name = name
        self.args = args
        self.kwargs = kwargs

    def dump(self, path: str | Path):
        path = Path(path)
        dir_ = path.parent
        attrs = {}
        for k in self.__slots__:
            attrs[k] = getattr(self, k)
        fd, tmp_path = tempfile.mkstemp(dir=dir_)
        try:
            with os.fdopen(fd, "wb") as f:
                dill.dump(attrs, f)
                # sync to disk
                f.flush()
                os.fsync(f.fileno())  # ensure data is flushed to disk
                os.replace(tmp_path, path)  # atomic rename
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    @classmethod
    def load(cls, path: str | Path) -> Self:
        wait_for_file(path)
        attrs = {}
        with open(path, "rb") as f:
            attrs.update(dill.load(f))
        self = cls.__new__(cls)
        for k, v in attrs.items():
            setattr(self, k, v)
        return self

    def __call__(self):
        func = import_function(self.module, self.name)
        return func(*self.args, **self.kwargs)


class Future:
    def __init__(self, dir: str | Path, task_id: str, job: Job | None = None):
        self.dir = Path(dir).resolve()
        self.task_id = task_id
        self.job = job

    def get_output_path(self) -> Path:
        return self.dir / self.task_id / "output.pkl"

    def done(self) -> bool:
        return self.get_output_path().exists()

    def wait(self, timeout: int | float | None = None):
        # busy wait for the output file to be created
        output_path = self.get_output_path()
        start = time.time()
        while True:
            if timeout is None or timeout <= 0:
                remaining = None
            else:
                remaining = timeout - (time.time() - start)
            if remaining is not None and remaining <= 0:
                raise TimeoutError("waiting for result timed out")
            if output_path.exists() and wait_for_file(output_path):
                break
            time.sleep(0.1)

    def cancel(self) -> bool:
        if self.job:
            try:
                self.job.cancel()
                return True
            except Exception:
                pass
        return False

    def result(self) -> any:
        self.wait()
        output_path = self.get_output_path()
        with open(output_path, "rb") as f:
            payload: dict = dill.load(f)
        if not payload["ok"]:
            exc: Exception | None = payload["exception"]
            tb = payload.get("traceback")
            if tb:
                tb = RuntimeError(tb)
            if exc:
                raise exc from tb
            err = "error occurred in function execution"
            raise RuntimeError(err) from tb
        return payload["result"]


class FunctionExecutor:
    def __init__(self, cluster: Cluster | None = None, dir: str | Path | None = None):
        if dir is None:
            dir = gettempdir()
        dir = Path(dir)
        dir.mkdir(parents=True, exist_ok=True)
        self.dir = dir
        self.cluster = cluster

    def submit(self, __func, /, *args, **kwargs) -> Future:
        temp_dir = Path(tempfile.mkdtemp(dir=self.dir))
        path = temp_dir / "input.pkl"
        BoundFunction(__func, *args, **kwargs).dump(path)
        task_id = temp_dir.name
        job = None
        if self.cluster:
            job = basic_schedule(
                self.cluster,
                {
                    "name": FSW_TASK_NAME,
                    "dir": str(self.dir),
                    "task_id": task_id,
                },
            )
        return Future(self.dir, task_id, job=job)

    def execute(self, task_id: str, remove: bool = False):
        input_path = self.dir / task_id / "input.pkl"
        output_path = self.dir / task_id / "output.pkl"
        bound_func = BoundFunction.load(input_path)
        try:
            result = bound_func()
            payload = {"ok": True, "result": result}
        except Exception as e:
            tb = traceback.format_exc()
            payload = {"ok": False, "exception": e, "traceback": tb}
        with open(output_path, "wb") as f:
            dill.dump(payload, f)
        if remove:
            os.remove(input_path)


class FileSystemWorkerConfig(TaskConfig):
    name: ClassVar[str] = FSW_TASK_NAME
    dir: str
    task_id: str
    remove: bool = False


class FileSystemWorker(Task):
    config: FileSystemWorkerConfig

    def run(self):
        fx = FunctionExecutor(dir=self.config.dir)
        fx.execute(task_id=self.config.task_id, remove=self.config.remove)


def basic_schedule(
    cluster: Cluster,
    config: dict | FileSystemWorkerConfig,
) -> Job:
    if not isinstance(config, FileSystemWorkerConfig):
        config = FileSystemWorkerConfig.from_dict(config)
    path = Path(config.dir).resolve()
    base_dir = path / config.task_id / "logs"
    cmd_args = [
        "python",
        inspect.getfile(basic_schedule),
        "--dir",
        str(path),
        "--task-id",
        config.task_id,
    ]
    if config.remove:
        cmd_args.append("--remove")
    return cluster.schedule(
        cmd_args,
        functools.partial(format_hook, base_dir=base_dir),
    )


@click.command()
@click.option("--dir", required=True, type=click.Path(exists=True, file_okay=False))
@click.option("--task-id", required=True, type=str)
@click.option("--remove", is_flag=True, default=False)
def main(dir, task_id, remove):
    """Run the function worker."""
    fe = FunctionExecutor(dir=dir)
    fe.execute(task_id, remove=remove)


if __name__ == "__main__":
    main()
