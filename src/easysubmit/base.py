from __future__ import annotations

import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Callable, List, TypeVar

from typing_extensions import Literal, ParamSpec

import __main__

from easysubmit.utils import ValidatedProperty

P = ParamSpec("P")
T = TypeVar("T")
R = TypeVar("R")


class Job:
    id: str = ValidatedProperty(validator=str)

    def __init__(self, id: int | str):
        self.id = id

    def get_status(
        self,
    ) -> Literal["PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", "UNKNOWN"]:
        raise NotImplementedError

    def cancel(self):
        raise NotImplementedError


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
            _task_id = file.read_text(encoding="utf-8").strip()
            job_path = jobs_path / f"task-{_task_id}.job"
            try:
                with open(job_path, "x", encoding="utf-8") as f:
                    f.write(str(job_id))
            except FileExistsError:
                continue
            task_id = _task_id
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
        if self.is_scheduler_running():
            msg = "scheduler is already running"
            raise RuntimeError(msg)
        tasks_path = self.base_dir / "tasks"
        tasks_path.mkdir(exist_ok=True, parents=True)
        max_task_count = 20
        task_count = 0
        for task in self.tasks:
            if task_count >= max_task_count:
                break
            try:
                with open(
                    tasks_path / f"task-{task.id}.task", "x", encoding="utf-8"
                ) as f:
                    f.write(str(task.id))
            except FileExistsError:
                continue
            # skip since somehow there is already a job file
            job_path = self.base_dir / "jobs" / f"task-{task.id}.job"
            if job_path.exists():
                continue
            task_count += 1
        task_count = min(task_count, max_task_count)
        if task_count == 0:
            msg = "no more tasks to run"
            raise RuntimeError(msg)
        job = self.cluster.schedule(
            ["python", __main__.__file__, "--worker"],
            self._format_hook,
            array=list(range(task_count)),
        )
        # write job id to file
        (self.base_dir / "jobs").mkdir(exist_ok=True, parents=True)
        job_path = self.base_dir / "jobs" / f"job-{job.id}.job"
        with open(job_path, "w", encoding="utf-8") as f:
            f.write(str(job.id))

    def _format_hook(self, s: str) -> str:
        return s.format(
            BASE_DIR=self.base_dir,
            LOGS_DIR=self.base_dir / "logs",
        )

    def is_scheduler_running(self) -> bool:
        for job_path in (self.base_dir / "jobs").glob("job-*.job"):
            job_id = job_path.read_text(encoding="utf-8").strip()
            job = self.cluster.get_job(job_id)
            status = job.get_status()
            if status in ("PENDING", "RUNNING"):
                return True
        # UNKOWN, COMPLETED, FAILED, CANCELLED
        return False
