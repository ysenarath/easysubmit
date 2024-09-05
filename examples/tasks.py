from __future__ import annotations

from easysubmit.base import Scheduler, Task
from easysubmit.slurm import SLURMCluster, SLURMConfig


class ExampleTask(Task):
    def run(self):
        print(f"Running task {self.id} with config {self.config}")


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
    scheduler = Scheduler(cluster)
    scheduler.tasks.append(ExampleTask("task_a", {"name": "Alice"}))
    scheduler.tasks.append(ExampleTask("task_b", {"name": "Bob"}))
    scheduler.run()


if __name__ == "__main__":
    main()
