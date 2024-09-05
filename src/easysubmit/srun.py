from __future__ import annotations

from easysubmit.base import Scheduler
from easysubmit.slurm import SLURMCluster, SLURMConfig


def worker_func(config: dict):
    if config["name"] == "A":
        raise NotImplementedError
    print(config)


def main():
    config = SLURMConfig(
        partition="contrib-gpuq",  # contrib-gpuq
        qos="gpu",
        nodes=1,
        ntasks_per_node=1,
        gres="gpu:3g.40gb:1",
        mem="32G",
        output="{LOGS_DIR}/job-%j-slurm-%x-%A_%a-%N.out",
        error="{LOGS_DIR}/job-%j-slurm-%x-%A_%a-%N.err",
    )
    cluster = SLURMCluster(config)
    scheduler = Scheduler(cluster, worker_func)
    scheduler.configs["A"] = {"name": "A"}
    scheduler.configs["B"] = {"name": "B"}
    scheduler.run()


if __name__ == "__main__":
    main()
