from easysubmit.entities import Cluster, Job, Task, TaskConfig, AutoTask
from easysubmit.slurm import SLURMCluster, SLURMConfig

__version__ = "0.2.2"

__all__ = [
    "Task",
    "TaskConfig",
    "AutoTask",
    "Job",
    "Cluster",
    "SLURMCluster",
    "SLURMConfig",
]
