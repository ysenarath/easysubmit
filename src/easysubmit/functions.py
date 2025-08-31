from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
import os
import sys
import threading
import time
import traceback
from collections.abc import Callable
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import ClassVar

import dill
from typing_extensions import Self
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from easysubmit.base import schedule
from easysubmit.entities import Cluster, Job, Task, TaskConfig

FSW_TASK_NAME = "easysubmit.functions.FileSystemWorker"

logger = logging.getLogger(__name__)


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
        attrs = {}
        for k in self.__slots__:
            attrs[k] = getattr(self, k)
        with open(path, "wb") as f:
            dill.dump(attrs, f)

    @classmethod
    def load(cls, path: str | Path) -> Self:
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


class FileHandler(FileSystemEventHandler):
    def __init__(self, filename: str):
        self.filename = filename
        self.ready = False

    def on_created(self, event) -> None:
        if event.src_path.endswith(self.filename):
            self.ready = True


class Future:
    def __init__(self, dir: str | Path, submit_id: str, job: Job | None = None):
        self.dir = Path(dir).resolve()
        self.submit_id = submit_id
        self.job = job
        self.condition = threading.Condition()
        self.ready = False

    def _file_ready(self):
        with self.condition:
            self.ready = True
            self.condition.notify_all()

    def _status_ready(self):
        with self.condition:
            self.ready = True
            self.condition.notify_all()

    def _monitor_status(self):
        if not self.job:
            return
        status = self.job.get_status()
        while True:
            time.sleep(0.1)
            if status in ("COMPLETED", "FAILED", "CANCELLED", "UNKNOWN"):
                self._status_ready()
                break

    def wait(self, timeout: int | float | None = None):
        start = time.time()
        handler = FileHandler(f"{self.submit_id}.output")
        # Set up watchdog observer to monitor the directory for output file creation
        observer = Observer()
        observer.schedule(handler, str(self.dir), recursive=False)
        observer.start()
        # Start a thread to monitor job status if job is provided
        if self.job:
            status_thread = threading.Thread(target=self._monitor_status)
            status_thread.start()
        try:
            with self.condition:
                while not handler.ready:
                    if timeout is None:
                        remaining = None
                    else:
                        remaining = timeout - (time.time() - start)
                    if remaining is not None and remaining <= 0:
                        raise TimeoutError("waiting for result timed out")
                    self.condition.wait(timeout=remaining)
        finally:
            observer.stop()
            observer.join()
            if status_thread:
                status_thread.join()

    def result(self) -> any:
        self.wait()
        path = self.dir / f"{self.submit_id}.output"
        with open(path, "rb") as f:
            payload = dill.load(f)
        if not payload["ok"]:
            exc = payload["exception"]
            if exc:
                raise exc
            err = "error occurred in function execution"
            raise RuntimeError(err)
        return payload["result"]


class FunctionExecutor:
    def __init__(self, dir: str | Path, cluster: Cluster | None = None):
        dir = Path(dir)
        dir.mkdir(parents=True, exist_ok=True)
        self.dir = dir
        self.cluster = cluster

    def submit(self, __func, /, *args, **kwargs) -> Future:
        submit_id = None
        with NamedTemporaryFile(dir=self.dir, suffix=".input", delete=False) as f:
            path = Path(f.name)
            BoundFunction(__func, *args, **kwargs).dump(path)
            submit_id = path.stem
        job = None
        if self.cluster:
            job = schedule(
                self.cluster,
                {
                    "name": FSW_TASK_NAME,
                    "dir": str(self.dir),
                    "submit_id": submit_id,
                },
            )
        return Future(self.dir, submit_id, job=job)

    def execute(self, submit_id: str, remove: bool = False):
        input_path = self.dir / f"{submit_id}.input"
        output_path = self.dir / f"{submit_id}.output"
        logger.info(f"Starting execution for submit_id: {submit_id}")
        bound_func = BoundFunction.load(input_path)
        logger.debug(f"Loaded BoundFunction from {input_path}")
        try:
            result = bound_func()
            payload = {"ok": True, "result": result}
            logger.info(f"Execution successful for submit_id: {submit_id}")
        except Exception as e:
            tb = traceback.format_exc()
            payload = {"ok": False, "exception": e, "traceback": tb}
            logger.error(f"Execution failed for submit_id: {submit_id}")
            logger.debug(f"Exception traceback: {tb}")
        with open(output_path, "wb") as f:
            dill.dump(payload, f)
        logger.debug(f"Output written to {output_path}")
        if remove:
            os.remove(input_path)
            logger.debug(f"Input file {input_path} removed")


class FileSystemDynamicWorker(FileSystemEventHandler):
    def __init__(self, dir: str | Path):
        self.dir = Path(dir).resolve()

    def on_created(self, event):
        if event.src_path.endswith(".input"):
            submit_id = Path(event.src_path).stem
            FunctionExecutor(self.dir).execute(submit_id)

    def run(self):
        observer = Observer()
        observer.schedule(self, str(self.dir), recursive=False)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()


class FileSystemWorkerConfig(TaskConfig):
    name: ClassVar[str] = FSW_TASK_NAME
    dir: str
    submit_id: str


class FileSystemWorker(Task):
    config: FileSystemWorkerConfig

    def run(self):
        fex = FunctionExecutor(self.config.dir)
        fex.execute(self.config.submit_id, remove=True)
