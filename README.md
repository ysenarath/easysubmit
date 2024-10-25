# EasySubmit

## Introduction
easysubmit is a Python-based job scheduling and management system designed to seamlessly integrate with Slurm, a popular cluster management and job scheduling platform. This project aims to simplify the process of submitting, monitoring, and managing jobs on cluster environments.

## Getting Started
### Prerequisites
- Python 3.8+
- Slurm cluster environment

### Installation
#### Method 1: Clone Repository and Install Dependencies
```bash
# Clone the repository
git clone https://github.com/ysenarath/easysubmit.git

# Navigate into the project directory
cd easysubmit

# Install dependencies
pip install -r requirements.txt
```

#### Method 2: Install using pip
```bash
pip install easysubmit
```

### Basic Setup
1. Configure your Slurm cluster settings.
2. Create tasks by instantiating the `Task` class.
3. Initialize the `Scheduler` with your tasks and cluster settings.

## Usage
### Creating Tasks
```python
from easysubmit.base import Task

# Example task creation
task = Task("task_id", {"config_key": "config_value"})
```

### Scheduling Jobs
```python
from easysubmit.base import Scheduler, Cluster

# Initialize the cluster and scheduler
cluster = Cluster()
scheduler = Scheduler(cluster, [task])

# Schedule the job
job = scheduler.run()
```

### Monitoring Job Status
```python
# Get the job status
status = job.get_status()
print(status)
```

### SLURM Configuration Example
For Slurm, configure jobs using `SLURMConfig` as shown in our [example](examples/slurm.py):
```python
from easysubmit.slurm import SLURMConfig

config = SLURMConfig(
    partition="gpuq",  
    qos="gpu",
    nodes=1,
    ntasks_per_node=1,
    gres="gpu:3g.40gb:1",
    mem="32G",
    output="logs/slurm/job-%x-%A/task-%a-%N.out",
    error="logs/slurm/job-%x-%A/task-%a-%N.err",
    array=[1, 2, 3, 4, 5],
)
```

### Array Job Scheduling
easysubmit supports scheduling array jobs with Slurm. Use `get_slurm_array_task_id()` to handle array task execution, as demonstrated in [examples/slurm.py](examples/slurm.py).

## API Documentation
### Main Classes
- `Job`: Represents a job with an ID.
  - `get_status()`: Retrieves the job's status.
  - `cancel()`: Cancels the job.
- `Cluster`: Abstracts the cluster environment.
  - `schedule(...)`: Schedules a job.
  - `get_job(job_id)`: Retrieves a job by its ID.
- `Task`: Embodies a task with an ID and configuration.
  - `run()`: Executes the task.
- `Scheduler`: Coordinates the scheduling process.
  - `run()`: Schedules jobs and manages tasks.

## Troubleshooting
- **Job Submission Errors**: Check Slurm cluster settings and job configuration.
- **Scheduler Issues**: Verify the scheduler's running status and task queue.

## Contributing
Contributions are welcome! Please submit a pull request with a clear description of changes.

## License
easysubmit is licensed under the MIT License.
