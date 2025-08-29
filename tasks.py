from invoke import task, Context
from pathlib import Path


@task
def build(c: Context) -> None:
    c.run("uv build")


@task
def clean(c: Context) -> None:
    # remove the dist directory if it exists
    c.run("rm -rf build dist *.egg-info")


@task
def test(c: Context) -> None:
    c.run('uv run python -m unittest discover -s tests -p "test_*.py" -v')


@task
def rsync(c: Context, config: str) -> None:
    # find the name of the file that matches the config exactly or that starts with the config
    # if there is multiple files that starts with config it should raise an error to the user
    files = list(Path("scripts/bin").glob(f"rsync-{config}*.sh"))
    if not files:
        raise ValueError(f"No rsync script found for config '{config}'")
    if len(files) > 1:
        raise ValueError(f"Multiple rsync scripts found for config '{config}': {files}")
    c.run(f"bash {files[0]}")
