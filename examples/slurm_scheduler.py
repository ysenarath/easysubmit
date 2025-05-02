from __future__ import annotations

import time

from easysubmit import Scheduler, SLURMCluster, SLURMConfig, Task


class ExampleTask(Task):
    def run(self):
        time.sleep(20)
        print(f"Running task {self.id} with config {self.config}")


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
    scheduler = Scheduler(cluster)
    scheduler.tasks.append(ExampleTask({"name": "Alice"}))
    scheduler.tasks.append(ExampleTask({"name": "Bob"}))
    scheduler.tasks.append(ExampleTask({"name": "Charlie"}))
    scheduler.run()


if __name__ == "__main__":
    main()
