from __future__ import annotations

import argparse
import functools
import json
import uuid
from collections.abc import Sequence
from pathlib import Path

import __main__
from easysubmit.entities import AutoTask, Cluster, TaskConfig
from easysubmit.helpers import get_fingerprint

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
)

args = parser.parse_args()


def _format_hook(s: str, base_dir: str | Path) -> str:
    return s.format(BASE_DIR=str(base_dir))


def schedule(
    cluster: Cluster,
    configs: Sequence[TaskConfig | dict],
    base_dir: Path | str | None = None,
    max_task_count: int = 20,
) -> None:
    base_dir = Path(base_dir) if base_dir else Path.cwd() / "easysubmit"

    base_dir.mkdir(parents=True, exist_ok=True)

    if args.worker:
        run_worker(cluster, base_dir)
        return

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

    job = cluster.schedule(
        # run this script as a worker
        ["python", __main__.__file__, "--worker", "--run-id", run_id],
        functools.partial(_format_hook, base_dir=base_dir),
        array=list(range(task_count)),
    )


def run_worker(cluster: Cluster, base_dir: Path) -> None:
    run_id = args.run_id

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
    task.run()
