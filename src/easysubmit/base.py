from __future__ import annotations

import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Callable, List, TypeVar

from typing_extensions import ParamSpec

import __main__

from easysubmit.utils import ValidatedProperty

P = ParamSpec("P")
T = TypeVar("T")
R = TypeVar("R")


class Job:
    id: str = ValidatedProperty(validator=str)

    def __init__(self, id: int | str):
        self.id = id

    def get_status(self) -> str:
        raise NotImplementedError

    def cancel(self):
        raise NotImplementedError

    def is_running(self) -> bool:
        return self.get_status() == "RUNNING"

    def is_pending(self) -> bool:
        return self.get_status() == "PENDING"

    def is_completed(self) -> bool:
        return self.get_status() == "COMPLETED"

    def is_failed(self) -> bool:
        return self.get_status() == "FAILED"

    def is_cancelled(self) -> bool:
        return self.get_status() == "CANCELLED"


class Cluster:
    def schedule(
        self, __args: List[str], __format_hook: Callable | None = None, **kwargs
    ) -> Job:
        raise NotImplementedError

    @property
    def current_job(self) -> Job:
        return self.get_job()

    def get_job(self, job_id: str | None = None) -> Job:
        raise NotImplementedError


class Task:
    id: str = ValidatedProperty["Task", str](validator=str)
    config: dict = ValidatedProperty["Task", str](validator=dict)

    def __init__(self, id: int | str, config: dict):
        self.id = id
        self.config = config

    def run(self):
        raise NotImplementedError


class Scheduler:
    def __init__(
        self,
        cluster: Cluster,
        tasks: List[Task] | None = None,
        base_dir: Path | str | None = None,
    ):
        if base_dir is None:
            base_dir = Path.cwd() / "slurm"
        self.base_dir: Path = Path(base_dir)
        self.cluster = cluster
        if tasks is None:
            tasks = []
        self.tasks = tasks

    def run_worker(self):
        job_id = self.cluster.current_job.id
        jobs_path = self.base_dir / "jobs"
        jobs_path.mkdir(exist_ok=True, parents=True)
        tasks_path = self.base_dir / "tasks"
        task_id = None
        for file in tasks_path.glob("*.task"):
            job_path = jobs_path / f"{file.stem}.job"
            try:
                with open(job_path, "x", encoding="utf-8") as f:
                    f.write(str(job_id))
            except FileExistsError:
                continue
            task_id = file.stem
            break
        if task_id is None:
            # job successfully completed
            # no more tasks to run
            return
        task = None
        for t in self.tasks:
            if t.id == task_id:
                task = t
                break
        if task is None:
            # unable to find task
            # do not unlink the job file so that we can
            #   debug and see what went wrong
            # Path(jobs_path / f"{task_id}.job").unlink()
            raise RuntimeError(f"unable to find task with id {task_id}")
        # (self.base_dir / "logs" / f"job-{job_id}").mkdir(exist_ok=True, parents=True)
        errfile = self.base_dir / "logs" / f"job-{job_id}-task-{task_id}.err"
        outfile = self.base_dir / "logs" / f"job-{job_id}-task-{task_id}.out"
        with open(errfile, "w", encoding="utf-8") as errfile:  # noqa: SIM117
            with open(outfile, "w", encoding="utf-8") as outfile:
                with redirect_stdout(outfile), redirect_stderr(errfile):
                    try:
                        task.run()
                    except Exception as e:
                        # job failed
                        self._job_failed(task_id, job_id, e)
                        raise e

    def _job_failed(self, task_id: str, job_id: str, error: Exception):
        pass  # job failed

    def run(self) -> Job:
        if "--worker" in sys.argv:
            self.run_worker()
            return
        tasks_path = self.base_dir / "tasks"
        tasks_path.mkdir(exist_ok=True, parents=True)
        max_task_count = 40
        task_count = 0
        for task in self.tasks:
            if task_count >= max_task_count:
                break
            try:
                Path(tasks_path / f"{task.id}.task").touch(exist_ok=False)
            except FileExistsError:
                continue
            task_count += 1
        task_count = min(task_count, max_task_count)
        if task_count == 0:
            msg = "no more tasks to run"
            raise RuntimeError(msg)
        return self.cluster.schedule(
            ["python", __main__.__file__, "--worker"],
            self._format_hook,
            array=list(range(task_count)),
        )

    def _format_hook(self, s: str) -> str:
        return s.format(
            BASE_DIR=self.base_dir,
            LOGS_DIR=self.base_dir / "logs",
        )
