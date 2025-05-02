import subprocess
import sys
from pathlib import Path

this = Path(__file__).parent.resolve()
current_venv = Path(sys.prefix)


def main(filename: str = "train.py"):
    job_name = f"{this.stem}-{filename}"
    print(job_name)
    command = f"""sbatch <<EOF
#!/bin/bash
#SBATCH --job-name=python
#SBATCH --qos=gpu
#SBATCH --partition=gpuq
#SBATCH --gres=gpu:A100.40gb:1

#SBATCH --output=slurm/gpu_job-%j.out
#SBATCH --error=slurm/gpu_job-%j.err

#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1

#SBATCH --mem=32G
#SBATCH --time=2-23:59:00

#Load needed modules
module load gnu10/10.3.0-ya zlib/1.2.11-2y sqlite/3.37.1-6s python/3.9.9-jh openmpi4/4.1.2-4a

#Execute
source {current_venv / "bin" / "activate"}
python {this / filename}
EOF
"""
    print(command)
    subprocess.run(command, shell=True)


if __name__ == "__main__":
    main(sys.argv[1])
