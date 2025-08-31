import time
from pathlib import Path

import click
import evaluate
import numpy as np
from datasets import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

from easysubmit.functions import FileSystemDynamicWorker, FunctionExecutor

metric = evaluate.load("accuracy")


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return metric.compute(references=labels, predictions=preds)


def train_transformer(texts, labels):
    """Train a transformer on provided text data."""
    # Build dataset
    dataset = Dataset.from_dict({"text": texts, "label": labels}).train_test_split(
        test_size=0.2
    )

    model_name = "distilbert-base-uncased"
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    def tokenize_fn(batch):
        return tokenizer(
            batch["text"], padding="max_length", truncation=True, max_length=64
        )

    dataset = dataset.map(tokenize_fn, batched=True)

    model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=2)

    training_args = TrainingArguments(
        output_dir="./results",
        eval_strategy="epoch",
        logging_strategy="epoch",
        save_strategy="no",  # don’t save checkpoints for this toy job
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        num_train_epochs=1,  # keep it short for demo
        seed=42,
        disable_tqdm=True,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["test"],
        compute_metrics=compute_metrics,
    )

    trainer.train()
    eval_result = trainer.evaluate()
    return eval_result


@click.group()
def cli():
    pass


@cli.command()
def main():
    """Submit a transformer training job to the worker."""
    dir = Path(__file__).parent / "tmp"
    fexec = FunctionExecutor(dir)

    # Dummy data
    texts = [f"This is example {i}" for i in range(200)]
    labels = np.random.randint(0, 2, size=200).tolist()

    print("Submitting transformer training job...")
    future = fexec.submit(train_transformer, texts, labels)
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
