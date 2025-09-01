import getpass
import os
from pathlib import Path

__all__ = [
    "EASYSUBMIT_PATH",
]

username = getpass.getuser()

scratch = Path(f"/scratch/{username}")

if scratch.exists() and os.access(scratch, os.W_OK):
    cache_dir = scratch / ".cache" / "easysubmit"
else:
    cache_dir = Path.home() / ".cache" / "easysubmit"

EASYSUBMIT_PATH = os.getenv("EASYSUBMIT_PATH", str(cache_dir))
