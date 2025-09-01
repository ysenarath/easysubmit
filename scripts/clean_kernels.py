import json
import os
import subprocess
from jupyter_client.kernelspec import KernelSpecManager

ksm = KernelSpecManager()
kernels = ksm.find_kernel_specs()

for name, path in kernels.items():
    kernel_json = os.path.join(path, "kernel.json")
    try:
        with open(kernel_json, "r") as f:
            data = json.load(f)
        python_exec = data["argv"][0]

        # Check if the python path exists and works
        result = subprocess.run(
            [python_exec, "--version"], capture_output=True, text=True
        )
        if result.returncode != 0:
            raise Exception("Invalid python")
    except Exception as e:
        print(f"Removing invalid kernel: {name}")
        os.system(f"jupyter kernelspec remove -f {name}")
