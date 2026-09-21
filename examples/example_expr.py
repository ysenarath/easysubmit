from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from easysubmit.functions import BoundFunction, FunctionExecutor, Future
from easysubmit.slurm import (
    Cluster,
    SLURMCluster,
    SLURMConfig,
    get_slurm_array_job_id,
    get_slurm_array_task_id,
    get_slurm_job_id,
)

__all__ = [
    "Environment",
    "envs",
]

gpu_specs = {
    "10gb": {
        "slurm_template": "gpu:1g.10gb:{}",
        "gpus_per_node": 4,
        "cpus": 64,
        "ram": "500GB",
    },
    "20gb": {
        "slurm_template": "gpu:2g.20gb:{}",
        "gpus_per_node": 4,
        "cpus": 64,
        "ram": "500GB",
    },
    "40gb": {
        "slurm_template": "gpu:3g.40gb:{}",
        "gpus_per_node": 4,
        "cpus": 64,
        "ram": "500GB",
    },
    "80gb": {
        "slurm_template": "gpu:A100.80gb:{}",
        "gpus_per_node": 4,
        "cpus": 64,
        "ram": "500GB",
    },
    "A100.40gb": {
        "slurm_template": "gpu:A100.40gb:{}",
        "gpus_per_node": 8,
        "cpus": 128,
        "ram": "1TB",
    },
    "H100.80gb": {
        "slurm_template": "gpu:H100.80gb:{}",
        "gpus_per_node": 4,
        "cpus": 112,
        "ram": "2TB",
    },
}

partitions = ["gpuq", "contrib-gpuq"]
partition = 1


def create_slurm_gpu_cluster(
    vram: int = 10, num_gpus: int = 1, mem: int = 32, time: str = "2-6:00:00"
) -> SLURMCluster | None:
    cluster = None
    gpu_type = f"{vram}gb"
    spec = gpu_specs[gpu_type]
    assert num_gpus <= spec["gpus_per_node"], (
        f"Requested GPUs ({num_gpus}) exceed available GPUs per node "
        f"for {gpu_type} ({spec['gpus_per_node']})"
    )
    gres = str(spec["slurm_template"]).format(num_gpus)
    if SLURMCluster.is_available():
        config = SLURMConfig(
            partition=partitions[partition],  # contrib-gpuq
            qos="gpu",
            nodes=1,
            ntasks_per_node=1,
            gres=gres,
            mem=f"{mem}G",
            time=time,
            output="{BASE_DIR}/job-%j-slurm-%x-%A_%a-%N.out",
            error="{BASE_DIR}/job-%j-slurm-%x-%A_%a-%N.err",
        )
        cluster = SLURMCluster(config)
    return cluster


class Environment:
    def __init__(self, cluster: Cluster | None = None):
        self._func_exec = FunctionExecutor(cluster=cluster)

    def _mock_submit(self, __func, /, *args, **kwargs) -> Future:
        temp_dir = Path(tempfile.mkdtemp(dir=self._func_exec.dir))
        path = temp_dir / "input.pkl"
        BoundFunction(__func, *args, **kwargs).dump(path)
        task_id = temp_dir.name
        future = Future(self._func_exec.dir, task_id, job=None)
        fe = FunctionExecutor(dir=self._func_exec.dir)
        fe.execute(task_id, remove=False)
        return future

    def schedule(self, __func, *args, **kwargs) -> Future:
        if self._func_exec.cluster is None:
            future = self._mock_submit(__func, *args, **kwargs)
        else:
            future = self._func_exec.submit(__func, *args, **kwargs)
        return future

    def run(self, __func, *args, **kwargs):
        future = self.schedule(__func, *args, **kwargs)
        future.wait()
        result = future.result()
        return result


envs: dict[str, Environment] = {
    "train": Environment(cluster=None),
    "experiment": Environment(
        cluster=create_slurm_gpu_cluster(vram=20, mem=64, time="2-6:00:00")
    ),
    "experiment_40gb": Environment(
        cluster=create_slurm_gpu_cluster(vram=40, mem=64, time="2-6:00:00")
    ),
}


def get_current_env_info() -> list[str]:
    env_info = []
    # SLURM Information
    env_info.append("SLURM Information:")
    try:
        env_info.extend(
            (
                f"-> SLURM Job ID: {get_slurm_job_id()}",
                f"-> SLURM Array Job ID: {get_slurm_array_job_id()}",
                f"-> SLURM Array Task ID: {get_slurm_array_task_id()}",
            )
        )
    except Exception:  # ruff: ignore[blind-except]
        env_info.append("-> Unable to retrieve SLURM job information.")
    # Python Environment
    env_info.append("Python Environment:")
    python_executable = Path(sys.executable)
    venv_path = python_executable.parent.parent
    env_info.extend(
        (
            f"-> Process ID: {os.getpid()}",
            f"-> Parent Process ID: {os.getppid()}",
            f"-> Python Executable: {python_executable}",
            f"-> Virtual Environment Path: {venv_path}",
        )
    )
    return env_info
