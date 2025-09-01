import time

import evaluate
import numpy as np
from datasets import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

from easysubmit.functions import FunctionExecutor
from easysubmit.slurm import SLURMCluster, SLURMConfig

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


def main():
    """Submit a transformer training job to the worker."""
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

    fe = FunctionExecutor(cluster=cluster)

    # Dummy data
    texts = [f"This is example {i}" for i in range(200)]
    labels = np.random.randint(0, 2, size=200).tolist()

    print("Submitting transformer training job...")
    future = fe.submit(train_transformer, texts, labels)
    result = future.result()

    print(f"Training finished. Result: {result}")
    time.sleep(1)


if __name__ == "__main__":
    main()
