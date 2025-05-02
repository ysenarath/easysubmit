from __future__ import annotations

import time

from easysubmit import Task


class ExampleTask(Task):
    def run(self):
        time.sleep(2)
        print(f"Running task {self.id} with config {self.config}")


def main():
    task = ExampleTask({"param1": "value1", "param2": "value2"})
    print(f"Task ID: {task.id}")
    task.run()
    print("Task completed.")
    task = ExampleTask({"param2": "value2", "param1": "value1"})
    print(f"Task ID: {task.id}")
    task.run()
    print("Task completed.")


if __name__ == "__main__":
    main()
