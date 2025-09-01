from __future__ import annotations

import copy
import os
import subprocess
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from subprocess import CompletedProcess
from tempfile import NamedTemporaryFile
from typing import Callable

from easysubmit.entities import Cluster, Job
from easysubmit.helpers import get_current_venv

__all__ = [
    "SLURMConfig",
    "build_sbatch_script",
    "sbatch",
    "SLURMJob",
    "get_slurm_job_array",
    "parse_slurm_array_arg",
    "format_slurm_array_arg",
    "get_slurm_job_id",
    "get_slurm_array_job_id",
    "get_slurm_array_task_id",
    "SLURMCluster",
]


class Lmod:
    @staticmethod
    def list():
        command = "list"
        lsmod = os.path.join(os.environ["LMOD_PKG"], "libexec", "lmod")
        args = [lsmod, "python", command]
        proc = subprocess.Popen(
            args,  # noqa: S603
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _, stderr = proc.communicate()
        modules = []
        add_next = False
        for item in stderr.decode().split():
            item = item.strip()
            if len(item) == 0:
                continue
            if item.endswith(")"):
                add_next = True
            elif add_next:
                modules.append(item)
                add_next = False
        return modules


@dataclass
class SLURMConfig:
    partition: str | None = None
    qos: str | None = None
    nodes: int | None = None
    ntasks_per_node: int | None = None
    gres: str | None = None
    mem_per_cpu: str | None = None
    mem: str | None = "16GB"
    time: str = "1:00:00"
    output: str | None = None
    error: str | None = None
    job_name: str = "default"
    array: None | list[int] | str = None
    modules: list[str] | None = field(default_factory=Lmod.list)
    cwd: str | None = field(default_factory=Path.cwd)
    venv: str | None = field(default_factory=get_current_venv)


def build_sbatch_script(args: Sequence[str], config: SLURMConfig) -> str:
    slurm = ["#!/bin/sh"]
    for key, value in asdict(config).items():
        if key in {"modules", "cwd", "venv"}:
            continue
        if value is None:
            continue
        if key == "array" and not isinstance(value, str):
            value = ",".join(map(str, value))
        key = key.replace("_", "-")
        slurm.append(f"#SBATCH --{key}={value}")
    if config.modules:
        slurm.append("")
        if not isinstance(config.modules, str):
            modules = " ".join(config.modules)
        slurm.append(f"module load {modules}")
    if config.cwd:
        slurm.append("")
        slurm.append(f"cd {config.cwd}")
    slurm.append("")
    slurm.extend(
        [
            'echo "+---------------------------------------+"',
            'echo "|           SLURM_JOB_INFO              |"',
            'echo "+---------------------------------------+"',
            'echo "\tSLURM_JOB_NAME     \t: ${{SLURM_JOB_NAME}}"',
            'echo "\tSLURM_JOB_ID       \t: ${{SLURM_JOB_ID}}"',
            'echo "\tSLURM_ARRAY_TASK_ID\t: ${{SLURM_ARRAY_TASK_ID}}"',
            'echo "\tSLURM_ARRAY_JOB_ID \t: ${{SLURM_ARRAY_JOB_ID}}"',
            'echo "+---------------------------------------+"',
        ]
    )
    activate_path = Path(config.venv) / "bin" / "activate"
    if config.venv and activate_path.exists():
        # only required if venv is not activated
        slurm.append("")
        slurm.append(f"source {activate_path}")
    elif config.venv:
        slurm.append("")
        slurm.append(f"export PATH={config.venv}/bin:$PATH")
        # slurm.append(f"alias python='{config.venv}/bin/python")
        # slurm.append(f"alias pip='{config.venv}/bin/pip")
        # echo "Python: `which python`"
        slurm.append('echo "Path to Python: `which python`"')
    else:
        raise ValueError("no python environment found")

    slurm.append("")
    slurm.append(" ".join(args))
    return "\n".join(slurm)


def sbatch(path: str | Path) -> SLURMJob:
    if isinstance(path, Path):
        path = str(path)
    command = ["sbatch", path]
    proc = subprocess.Popen(
        command,  # noqa: S603
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = proc.communicate()
    stderr = stderr.decode().strip()
    if stderr:
        raise RuntimeError(stderr)
    job_id = stdout.decode().strip().split()[-1]
    return SLURMJob(job_id)


class SLURMJob(Job):
    def get_status(self) -> str:
        status = subprocess.run(
            [  # noqa: S603, S607
                "sacct",
                "-j",
                self.id,
                "-X",
                "--noheader",
                "--format=state",
            ],
            capture_output=True,
            check=False,
        )
        status = status.stdout.decode("utf-8").strip().upper()
        # in case of array job
        status = set(status.split())
        if "PENDING" in status:
            return "PENDING"
        if "RUNNING" in status:
            return "RUNNING"
        if "CANCELLED" in status:
            return "CANCELLED"
        if "FAILED" in status:
            return "FAILED"
        if "COMPLETED" in status:
            return "COMPLETED"
        return "UNKNOWN"

    def cancel(self):
        subprocess.run(
            ["scancel", self.id],  # noqa: S603, S607
            check=False,
        )

    def __repr__(self):
        return f"SLURMJob(job_id={self.id})"


def get_slurm_job_array(id: int | str) -> list[Job]:
    result: CompletedProcess[bytes] = subprocess.run(
        [  # noqa: S603, S607
            "sacct",
            "-j",
            str(id),
            "-X",
            "--noheader",
            "--format=jobid",
        ],
        capture_output=True,
        check=False,
    )
    job_ids = result.stdout.decode("utf-8").strip().split()
    return [SLURMJob(job_id) for job_id in job_ids]


def parse_slurm_array_arg(array: str) -> list[int]:
    if array is None:
        return []
    if isinstance(array, list):
        return array
    array = array.split(",")
    array_ids = []
    for job in array:
        if "-" in job:
            start, end = job.split("-")
            if ":" in end:
                start = int(start)
                end, step = end.split(":")
                end, step = int(end), int(step)
            else:
                start, end = int(start), int(end)
                step = 1
            array_ids.extend(range(start, end + 1, step))
        else:
            array_ids.append(int(job))
    return array_ids


def format_slurm_array_arg(array: list[int]) -> str:
    array = sorted(array)
    # concatenate consecutive numbers
    # 1,2,3,4,5,6,7,8,9,10 = 1-10
    # 1,2,3,5,7 = 1,2,3,5,7
    array = sorted(set(array))
    start = array[0]
    end = array[0]
    array_str = []
    for i in range(1, len(array) + 1):
        if i < len(array) and array[i] - end == 1:
            end = array[i]
        else:
            if end - start == 0:
                array_str.append(str(start))
            elif end - start == 1:
                array_str.extend([str(start), str(end)])
            else:
                array_str.append(f"{start}-{end}")
            if i < len(array):
                start = array[i]
                end = array[i]
    return ",".join(array_str)


def get_slurm_job_id() -> str | None:
    # SLURM_JOB_ID will be set to the unique job ID of the current job.
    if "SLURM_JOB_ID" not in os.environ:
        return None
    return os.environ["SLURM_JOB_ID"].strip()


def get_slurm_array_job_id() -> str | None:
    # SLURM_ARRAY_JOB_ID will be set to the first job ID of the array.
    if "SLURM_ARRAY_JOB_ID" not in os.environ:
        return None
    return os.environ["SLURM_ARRAY_JOB_ID"].strip()


def get_slurm_array_task_id() -> int | None:
    # SLURM_ARRAY_TASK_ID will be set to the job array index value.
    if "SLURM_ARRAY_TASK_ID" not in os.environ:
        return None
    return int(os.environ["SLURM_ARRAY_TASK_ID"])


class SLURMCluster(Cluster):
    def __init__(self, config: SLURMConfig):
        self.config = config

    def get_job(self, id: str | None = None) -> Job:  # noqa: PLR6301
        if id is None:
            id = get_slurm_job_id()
        return SLURMJob(id)

    def get_array_job(self, id: str | None = None) -> Job:
        if id is None:
            id = get_slurm_array_job_id()
        return SLURMJob(id)

    def schedule(
        self, __args: Sequence[str], __format_hook: Callable | None = None, **kwargs
    ) -> SLURMJob:
        config = copy.deepcopy(self.config)
        for key, value in kwargs.items():
            if not hasattr(config, key):
                continue
            setattr(config, key, value)
        script = build_sbatch_script(__args, config)
        if __format_hook is not None:
            script = __format_hook(script)
        with NamedTemporaryFile(
            "w",
            dir=Path.cwd(),
            encoding="utf-8",
            prefix=".slurm.",
            suffix=".sh",
        ) as file:
            file.write(script)
            file.flush()
            job = sbatch(file.name)
        return job

    @classmethod
    def is_available(cls) -> bool:
        try:
            subprocess.run(  # noqa: S603, S607
                ["sinfo"],
                capture_output=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
