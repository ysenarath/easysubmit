from __future__ import annotations

from base import Scheduler
from slurm import SLURMCluster, SLURMConfig


def worker_func(config: dict):
    print(config)


def main():
    config = SLURMConfig(
        partition="gpuq",  # contrib-gpuq
        qos="gpu",
        nodes=1,
        ntasks_per_node=1,
        gres="gpu:3g.40gb:1",
        mem="32G",
        output="logs/slurm/job-%x-%A/task-%a-%N.out",
        error="logs/slurm/job-%x-%A/task-%a-%N.err",
    )
    cluster = SLURMCluster(config)
    scheduler = Scheduler(cluster, worker_func)
    scheduler.run()


if __name__ == "__main__":
    main()
