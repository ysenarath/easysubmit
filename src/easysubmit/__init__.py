from easysubmit.entities import Cluster, Job
from easysubmit.functions import FunctionExecutor
from easysubmit.slurm import SLURMCluster, SLURMConfig

__version__ = "0.4.0"

__all__ = [
    "Cluster",
    "FunctionExecutor",
    "Job",
    "SLURMCluster",
    "SLURMConfig",
]
