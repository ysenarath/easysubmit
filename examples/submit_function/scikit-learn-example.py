import time
from pathlib import Path

import click
import evaluate
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

from easysubmit.functions import FileSystemDynamicWorker, FunctionExecutor

metric = evaluate.load("accuracy")


def train_and_evaluate(X, y):
    """Train a logistic regression model and return accuracy on test split."""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = LogisticRegression()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    return metric.compute(references=y_test, predictions=y_pred)


@click.group()
def cli():
    pass


@cli.command()
def main():
    """Submit a training job to the worker."""
    dir = Path(__file__).parent / "tmp"
    fexec = FunctionExecutor(dir)

    # Generate dummy dataset
    X = np.random.randn(200, 10).tolist()
    y = np.random.randint(0, 2, size=200).tolist()

    print("Submitting training job...")
    future = fexec.submit(train_and_evaluate, X, y)
    result = future.result()
    print(f"Training finished. Result: {result}")
    time.sleep(1)


@cli.command()
def worker():
    """Run the worker loop."""
    dir = Path(__file__).parent / "tmp"
    dir.mkdir(parents=True, exist_ok=True)
    worker = FileSystemDynamicWorker(dir)
    worker.run()


@cli.command()
def clean():
    """Clean up job directory."""
    dir = Path(__file__).parent / "tmp"
    for f in dir.glob("*"):
        if f.is_file():
            f.unlink()


if __name__ == "__main__":
    cli()
