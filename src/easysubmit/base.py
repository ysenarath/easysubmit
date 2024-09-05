from __future__ import annotations

import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Callable, Dict, List, Mapping, TypeVar

from typing_extensions import ParamSpec

import __main__

P = ParamSpec("P")
T = TypeVar("T")
R = TypeVar("R")


class Job:
    def __init__(self, id: int | str):
        self.id = str(id)

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
    def schedule(self, args: List[str], **kwargs) -> Job:
        raise NotImplementedError

    @property
    def current_job(self) -> Job:
        return self.get_job()

    def get_job(self, job_id: str | None = None) -> Job:
        raise NotImplementedError


class Scheduler:
    def __init__(
        self,
        cluster: Cluster,
        func: Callable[[dict], None],
        configs: Dict[str, dict] | List[dict] | None = None,
        base_dir: Path | str | None = None,
    ):
        if base_dir is None:
            base_dir = Path.cwd()
        self.base_dir: Path = Path(base_dir)
        self.func = func
        if configs is None:
            configs = {}
        if not isinstance(configs, Mapping):
            configs = {
                f"config_{i}": config for i, config in enumerate(configs)
            }
        self.configs = configs
        self.cluster = cluster

    def run_worker(self):
        job_id = self.cluster.current_job.id
        config_path = self.base_dir / "config"
        jobs_path = self.base_dir / "jobs"
        jobs_path.mkdir(exist_ok=True, parents=True)
        config_id, config = None, None
        for file in config_path.glob("*.json"):
            job_path = jobs_path / f"{file.stem}.job"
            try:
                with open(job_path, "x", encoding="utf-8") as f:
                    f.write(str(job_id))
            except FileExistsError:
                continue
            config_id = file.stem
            with open(file, encoding="utf-8") as f:
                config = json.load(f)
            break
        if config is None:
            # job successfully completed
            # no more tasks to run
            return
        errfile = self.base_dir / "logs" / f"{config_id}.err"
        outfile = self.base_dir / "logs" / f"{config_id}.out"
        with open(errfile, "w", encoding="utf-8") as errfile:  # noqa: SIM117
            with open(outfile, "w", encoding="utf-8") as outfile:
                with redirect_stdout(outfile), redirect_stderr(errfile):
                    try:
                        self.func(config)
                    except Exception as e:
                        # job failed
                        self._job_failed(config_id, job_id, e)
                        raise e

    def _job_failed(self, config_id: str, job_id: str, error: Exception):
        # job failed so we need to reschedule it therefor
        # we need to remove the job file and the config file
        (self.base_dir / "jobs" / f"{config_id}.job").unlink()
        (self.base_dir / "config" / f"{config_id}.json").unlink()

    def run(self) -> Job:
        if "--worker" in sys.argv:
            self.run_worker()
            return
        config_path = self.base_dir / "config"
        config_path.mkdir(exist_ok=True, parents=True)
        max_task_count = 40
        task_count = 0
        for config_id, config in self.configs.items():
            if task_count >= max_task_count:
                break
            try:
                with open(config_path / f"{config_id}.json", "xb") as f:
                    json.dump(config, f)
                task_count += 1
            except FileExistsError:
                continue
        task_count = min(task_count, max_task_count)
        if task_count == 0:
            msg = "no more tasks to run"
            raise RuntimeError(msg)
        return self.cluster.schedule(
            ["python", __main__.__file__, "--worker"],
            array=list(range(task_count)),
        )
