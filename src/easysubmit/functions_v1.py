from __future__ import annotations

from dataclasses import dataclass
import functools
import tempfile
from pathlib import Path
import time

import cloudpickle

from easysubmit.entities import Cluster

__all__ = [
    "Function",
]


def _format_hook(s: str, base_dir: str | Path) -> str:
    return s.format(BASE_DIR=str(base_dir))


@dataclass
class Future:
    path: Path

    @property
    def path(self) -> Path:
        return self._path

    @path.setter
    def path(self, value: str | Path):
        self._path = Path(value)

    def add_done_callback(self, callback):
        raise NotImplementedError

    def done(self) -> bool:
        output_path = Path(self.path) / "output.pkl"
        return output_path.exists()

    def result(self):
        output_path = Path(self.path) / "output.pkl"
        with output_path.open("rb") as f:
            res = cloudpickle.load(f)
        if isinstance(res, Exception):
            raise res
        return res

    def wait(self, timeout: int | float | None = None, sleep: int | float = 1):
        # get the current time in seconds since the epoch
        start = time.time()
        if timeout is None:
            timeout = -1
        while not self.done():
            diff = time.time() - start
            if timeout >= 0 and diff > timeout:
                raise TimeoutError("Timeout waiting for result.")
            time.sleep(sleep)


class Function:
    def __init__(self, __func, /, cluster: Cluster, dir: Path | str):
        self.func = __func
        self.dir = Path(dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        # make sure the base_dir exists
        if not self.dir.exists():
            err = f"'{self.dir}' does not exist"
            raise FileNotFoundError(err)
        self.cluster = cluster

    def __call__(self, *args, **kwargs) -> Future:
        pfunc = functools.partial(self.func, *args, **kwargs)
        p = Path(tempfile.mkdtemp(dir=self.dir))
        f = p / "input.pkl"
        with f.open("wb") as f:
            cloudpickle.dump(pfunc, f)
        f = p / "run.py"
        f.write_text(pyfile(), encoding="utf-8")
        args = ["python", str(f)]
        job = self.cluster.schedule(
            args,
            functools.partial(_format_hook, base_dir=p),
        )
        # write the job id to a file so we can track it later
        job_id_file = p / "job_id.txt"
        job_id_file.write_text(str(job.id), encoding="utf-8")
        return Future(p)


def pyfile():
    return """\
from pathlib import Path
import cloudpickle

def run():
    path = Path(__file__).parent
    input_path = path / "input.pkl"
    with input_path.open("rb") as input_file:
        func = cloudpickle.load(input_file)
    try:
        output = func()
    except Exception as e:
        output = e
    # save output to a file in the base directory
    output_path = path / "output.pkl"
    with output_path.open("wb") as output_file:
        cloudpickle.dump(output, output_file)

if __name__ == "__main__":
    run()
"""
