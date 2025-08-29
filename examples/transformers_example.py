from __future__ import annotations

import functools
from pathlib import Path

import evaluate
import numpy as np
from datasets import Dataset, load_dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

from easysubmit import SLURMCluster, SLURMConfig, Function


def tokenize(examples, tokenizer):
    return tokenizer(examples["text"], padding="max_length", truncation=True)


def compute_metrics(eval_pred, metric: evaluate.Metric):
    logits, labels = eval_pred
    # convert the logits to their predicted class
    predictions = np.argmax(logits, axis=-1)
    return metric.compute(predictions=predictions, references=labels)


def train(
    model: AutoModelForSequenceClassification,
    datasets: dict[str, Dataset],
    output_dir: str,
):
    small_train = datasets["train"].shuffle(seed=42).select(range(1000))
    small_eval = datasets["test"].shuffle(seed=42).select(range(1000))
    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir=str(output_dir) if output_dir else None,
            eval_strategy="epoch",
            push_to_hub=False,
        ),
        train_dataset=small_train,
        eval_dataset=small_eval,
        compute_metrics=functools.partial(
            compute_metrics, metric=evaluate.load("accuracy")
        ),
    )
    trainer.train()


def submit_train(
    model: AutoModelForSequenceClassification,
    datasets: dict[str, Dataset],
    base_dir: Path,
):
    if SLURMCluster.is_available() is False:
        raise RuntimeError("SLURM is not available.")
    config = SLURMConfig(
        partition="contrib-gpuq",  # contrib-gpuq
        qos="gpu",
        nodes=1,
        ntasks_per_node=1,
        gres="gpu:3g.40gb:1",
        mem="32G",
        output="{BASE_DIR}/job-%j-slurm-%x-%A_%a-%N.out",
        error="{BASE_DIR}/job-%j-slurm-%x-%A_%a-%N.err",
    )
    cluster = SLURMCluster(config)
    submit = Function(train, cluster=cluster, dir=base_dir / "slurm")
    output_dir = base_dir / "checkpoints"
    output_dir.mkdir(parents=True, exist_ok=True)
    return submit(model=model, datasets=datasets, output_dir=output_dir)


def main():
    here = Path(__file__)
    base_dir = here.parent / here.stem
    # create the base directory if it doesn't exist
    base_dir.mkdir(parents=True, exist_ok=True)
    # START
    dataset_name = "yelp_review_full"
    model_name = "google-bert/bert-base-cased"
    datasets = load_dataset(dataset_name)
    num_labels = datasets["train"].features["label"].num_classes
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    datasets = datasets.map(tokenize, batched=True, fn_kwargs={"tokenizer": tokenizer})
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name, num_labels=num_labels
    )
    try:
        future = submit_train(model, datasets, base_dir=base_dir)
        future.wait()
        result = future.result()
    except RuntimeError:
        # run locally if SLURM is not available
        print("SLURM is not available, running locally...")
        output_dir = base_dir / "checkpoints"
        output_dir.mkdir(parents=True, exist_ok=True)
        result = train(model, datasets, output_dir=output_dir)
    print(result)


if __name__ == "__main__":
    main()
