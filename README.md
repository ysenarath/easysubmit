# EasySubmit

A Python library for simplified job scheduling and management on SLURM clusters.

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

EasySubmit is a Python-based job scheduling and management system designed to seamlessly integrate with SLURM, a popular cluster management and job scheduling platform. This project aims to simplify the process of submitting, monitoring, and managing jobs on cluster environments through an intuitive Python API.

## Key Features

- **Simple API**: Easy-to-use Python interface for SLURM job submission
- **Task Management**: Define and configure tasks with type-safe configuration classes
- **Batch Scheduling**: Submit multiple experiments or jobs with different parameters
- **Profiling Support**: Optional integration with Scalene for performance profiling
- **Flexible Configuration**: Comprehensive SLURM configuration options
- **Type Safety**: Built with modern Python type hints for better development experience

## Installation

### From PyPI (Recommended)
```bash
pip install easysubmit
```

### From Source
```bash
# Clone the repository
git clone https://github.com/ysenarath/easysubmit.git
cd easysubmit

# Install in development mode
pip install -e .
```

### Optional Dependencies
For profiling support:
```bash
pip install easysubmit[scalene]
```

## Quick Start

Here's a simple example of how to use EasySubmit:

```python
from easysubmit import SLURMCluster, SLURMConfig, Task, TaskConfig
from easysubmit.base import schedule

# Define your task configuration
class ExperimentConfig(TaskConfig):
    name: str = "MyExperiment"
    learning_rate: float = 0.001
    batch_size: int = 32

# Define your task
class Experiment(Task):
    config: ExperimentConfig
    
    def run(self):
        print(f"Running experiment with lr={self.config.learning_rate}")
        # Your experiment code here

# Configure SLURM settings
config = SLURMConfig(
    partition="gpu",
    nodes=1,
    ntasks_per_node=1,
    gres="gpu:1",
    mem="16G"
)

# Create cluster and schedule jobs
cluster = SLURMCluster(config)
experiments = [
    {"name": "MyExperiment", "learning_rate": 0.001, "batch_size": 32},
    {"name": "MyExperiment", "learning_rate": 0.01, "batch_size": 64},
]

schedule(cluster, experiments)
```

## Core Components

### Task and TaskConfig
- `TaskConfig`: Define configuration parameters for your tasks with type safety
- `Task`: Base class for implementing your computational tasks

### SLURM Integration
- `SLURMCluster`: Interface to SLURM cluster management
- `SLURMConfig`: Comprehensive SLURM job configuration options

### Job Management
- `Job`: Represents individual jobs in the cluster
- `AutoTask`: Advanced task automation features

## Prerequisites

- Python 3.9 or higher
- Access to a SLURM cluster environment
- SLURM commands (`sbatch`, `squeue`, etc.) available in PATH

## Examples

Check out the `examples/` directory for more comprehensive usage examples:

- `examples/slurm_scheduler.py`: Basic SLURM job scheduling
- `examples/slurm_scheduler_with_profile.py`: Job scheduling with profiling
- `examples/tasks.py`: Task definition examples

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/ysenarath/easysubmit/issues)
- **Documentation**: [GitHub README](https://github.com/ysenarath/easysubmit#readme)
- **Source Code**: [GitHub Repository](https://github.com/ysenarath/easysubmit)
