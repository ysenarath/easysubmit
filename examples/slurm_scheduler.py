from __future__ import annotations

import time
from typing import ClassVar

from easysubmit import Task, TaskConfig, SLURMCluster, SLURMConfig

from easysubmit.base import schedule


class ExperimentConfig(TaskConfig):
    name: ClassVar[str] = "Experiment"
    param1: str = "default_value"
    param2: int = 0


class Experiment(Task):
    config: ExperimentConfig

    def run(self):
        # Simulate a long-running task
        print(
            f"Running experiment with param1={self.config.param1} and param2={self.config.param2}"
        )
        time.sleep(5)


def main():
    config = SLURMConfig(
        partition="contrib-gpuq",  # contrib-gpuq
        qos="gpu",
        nodes=1,
        ntasks_per_node=1,
        gres="gpu:3g.40gb:1",
        mem="32G",
        output="{BASE_DIR}/job-%j-slurm-%x-%A_%a-%N.out",
        error="{BASE_DIR}/job-%j-slurm-%x-%A_%a-%N.err",
    )
    cluster = SLURMCluster(config)
    experiments = [
        {"name": "Experiment", "param1": "value1", "param2": 1},
        {"name": "Experiment", "param1": "value2", "param2": 2},
        {"name": "Experiment", "param1": "value3", "param2": 3},
        {"name": "Experiment", "param1": "value4", "param2": 4},
        {"name": "Experiment", "param1": "value5", "param2": 5},
    ]
    schedule(cluster, experiments)


if __name__ == "__main__":
    main()
