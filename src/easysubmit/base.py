from __future__ import annotations

import argparse
import functools
import json
import uuid
from collections.abc import Sequence
from pathlib import Path

import __main__
from easysubmit.entities import AutoTask, Cluster, Job, TaskConfig
from easysubmit.helpers import format_hook, get_fingerprint
from easysubmit.profiler import (
    SCALENE_DEPENDENCY_MISSING_ERROR,
    enable_profiling,
    is_profiler_avilable,
)


class AppArgs:
    worker: bool
    run_id: str | None
    profile: bool


def _parse_args() -> AppArgs:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--worker",
        action="store_true",
        help="run the worker script",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        help="run id",
        default=None,
    )
    # add profilers
    parser.add_argument(
        "--profile",
        action="store_true",
        help="enable profiling with scalene",
    )
    return parser.parse_args()


def _validate_profilers(profilers: bool | str | Sequence[str]) -> Sequence[str] | None:
    if profilers is True or profilers == "all":
        profilers = ["cpu", "memory", "gpu"]
    elif isinstance(profilers, str):
        profilers = profilers.split(",")
        profilers = list(map(str.strip, profilers))
    elif profilers is None or not all(isinstance(p, str) for p in profilers):
        profilers = None
    else:
        profilers = list(map(str.strip, profilers))
    return profilers


def schedule(
    cluster: Cluster,
    configs: Sequence[TaskConfig | dict] | TaskConfig | dict,
    base_dir: Path | str | None = None,
    max_task_count: int = 20,
    profilers: bool | Sequence[str] | None = None,
) -> Job:
    profilers = _validate_profilers(profilers)

    base_dir = Path(base_dir) if base_dir else Path.cwd() / "easysubmit"

    base_dir.mkdir(parents=True, exist_ok=True)

    cli_args = _parse_args()

    if cli_args.worker:
        run_worker(cluster, base_dir, cli_args.run_id, cli_args.profile)
        return

    if isinstance(configs, (TaskConfig, dict)):
        configs = [configs]

    tasks = [AutoTask(config) for config in configs]

    # write the configs to a json files
    task_fingerprints = []

    for task in tasks:
        if len(task_fingerprints) >= max_task_count:
            break
        task_config_path = base_dir / f"{task.config.fingerprint}-task.json"
        try:
            with open(task_config_path, "x", encoding="utf-8") as f:
                json.dump(task.config.to_dict(), f, indent=4)
        except FileExistsError:
            continue
        job_path = base_dir / f"{task.config.fingerprint}-worker.txt"
        if job_path.exists():
            continue  # job already exists
        task_fingerprints.append(task.config.fingerprint)

    task_count = min(len(task_fingerprints), max_task_count)

    if task_count == 0:
        msg = "no tasks to run"
        raise RuntimeError(msg)

    run_id: str = get_fingerprint(uuid.uuid4().hex)

    manifest = {"run_id": run_id, "tasks": task_fingerprints}

    with open(base_dir / f"manifest-{run_id}.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f)

    if profilers:
        profile_file_name = "job-${{SLURM_JOB_ID}}-scalene.html"
        # --profile-interval
        cmd_args = [
            "python",
            "-m",
            "scalene",
            "--profile-interval",
            "5.0",
            "--html",
            *[f"--{p}" for p in profilers],
            "--outfile",
            str(base_dir / profile_file_name),
            "---",
            __main__.__file__,
            "--worker",
            "--run-id",
            run_id,
            "--profile",
        ]
        if not is_profiler_avilable():
            raise ImportError(SCALENE_DEPENDENCY_MISSING_ERROR)
    else:
        cmd_args = ["python", __main__.__file__, "--worker", "--run-id", run_id]

    return cluster.schedule(
        # run this script as a worker
        cmd_args,
        functools.partial(format_hook, base_dir=base_dir),
        array=list(range(task_count)),
    )


def run_worker(
    cluster: Cluster,
    base_dir: Path,
    run_id: str,
    profile: bool = False,
) -> None:
    with open(base_dir / f"manifest-{run_id}.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)

    fingerprints = manifest["tasks"]

    job_id = cluster.current_job.id

    config = None

    for task_path in base_dir.glob("*-task.json"):
        config = TaskConfig.from_json(task_path)

        if config.fingerprint not in fingerprints:
            config = None
            continue

        job_path = base_dir / f"{config.fingerprint}-worker.txt"
        try:
            with open(job_path, "x", encoding="utf-8") as f:
                f.write(str(job_id))
        except FileExistsError:
            config = None
            continue

        break

    if config is None:
        return

    task = AutoTask(config)

    if profile:
        with enable_profiling():
            task.run()
    else:
        task.run()
