from __future__ import annotations

import json
import sys
from pathlib import Path

import __main__
from easysubmit.entities import Cluster, Job, Task


class Scheduler:
    def __init__(
        self,
        cluster: Cluster,
        tasks: list[Task] | None = None,
        base_dir: Path | str | None = None,
    ):
        if base_dir is None:
            base_dir = Path.cwd() / "slurm"
        self.base_dir: Path = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True, parents=True)
        self.cluster = cluster
        self.tasks = tasks or []

    def is_scheduler_running(self) -> bool:
        for job_path in self.base_dir.glob("manifest-*.json"):
            with open(job_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            if "job_id" not in manifest:
                continue
            job_id = manifest["job_id"]
            job = self.cluster.get_job(job_id)
            status = job.get_status()
            if status in ("PENDING", "RUNNING"):
                return True
        return False  # UNKOWN, COMPLETED, FAILED, CANCELLED

    def _format_hook(self, s: str) -> str:
        return s.format(BASE_DIR=self.base_dir)

    def run(self, max_task_count: int = 20) -> Job:
        if "--worker" in sys.argv:
            self.run_worker()
            return
        if self.is_scheduler_running():
            msg = "scheduler is running"
            raise RuntimeError(msg)
        task_count = 0
        for task in self.tasks:
            if task_count >= max_task_count:
                break
            try:
                # write task to file
                task_path = self.base_dir / f"{task.fingerprint}-task.json"
                task.write_json(task_path, mode="x")
            except FileExistsError:
                continue  # task already exists
            job_path = self.base_dir / f"{task.fingerprint}-worker.txt"
            if job_path.exists():
                continue  # job already exists
            task_count += 1
        task_count = min(task_count, max_task_count)
        if task_count == 0:
            msg = "no tasks to run"
            raise RuntimeError(msg)
        job = self.cluster.schedule(
            # run this script as a worker
            ["python", __main__.__file__, "--worker"],
            self._format_hook,
            array=list(range(task_count)),
        )
        # write main job id to file
        manifest = {"job_id": job.id}
        main_job_path = self.base_dir / f"manifest-{job.id}.json"
        with open(main_job_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f)

    def run_worker(self):
        job_id = self.cluster.current_job.id
        task_id = None
        for task_path in self.base_dir.glob("*-task.json"):
            # note that output not be of real task type
            t = Task.read_json(task_path)
            job_path = self.base_dir / f"{t.fingerprint}-worker.txt"
            try:
                with open(job_path, "x", encoding="utf-8") as f:
                    f.write(str(job_id))
            except FileExistsError:
                continue
            task_id = t.id
            break
        if task_id is None:
            return
        task = None
        for t in self.tasks:
            if t.id == task_id:
                task = t
                break
        if task is None:
            msg = f"task {task_id} not found"
            raise RuntimeError(msg)
        try:
            task.run()
        except Exception as e:
            self._job_failed(task.id, job_id, e)
            raise e

    def _job_failed(self, task_id: str, job_id: str, error: Exception):
        pass  # job failed
