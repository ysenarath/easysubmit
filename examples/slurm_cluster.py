from easysubmit import SLURMCluster, SLURMConfig
from easysubmit.slurm import get_slurm_array_task_id


def main():
    task_id = get_slurm_array_task_id()
    if task_id is not None:
        print(f"Running task {task_id}")
        return
    config = SLURMConfig(
        partition="gpuq",  # contrib-gpuq
        qos="gpu",
        nodes=1,
        ntasks_per_node=1,
        gres="gpu:3g.40gb:1",
        mem="32G",
        output="logs/slurm/job-%x-%A/task-%a-%N.out",
        error="logs/slurm/job-%x-%A/task-%a-%N.err",
        array=[1, 2, 3, 4, 5],
    )
    args = ["python", __file__]
    cluster = SLURMCluster(config)
    job = cluster.schedule(args)
    print(job)


if __name__ == "__main__":
    main()
