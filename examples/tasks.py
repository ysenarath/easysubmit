from __future__ import annotations

import time
from typing import ClassVar

from easysubmit import AutoTask, Task, TaskConfig


class ExampleTaskConfig1(TaskConfig):
    name: ClassVar[str] = "ExampleTaskConfig1"
    param1: str = "default_value"


class ExampleTask(Task):
    config: ExampleTaskConfig1

    def run(self):
        time.sleep(2)
        print(f"ExampleTask({self.config})")


class ExampleTaskConfig2(TaskConfig):
    name: ClassVar[str] = "ExampleTaskConfig2"
    param1: str = "default_value"


class ExampleTask2(Task):
    config: ExampleTaskConfig2

    def run(self):
        time.sleep(2)
        print(f"ExampleTask2({self.config})")


def main():
    config1 = {"name": "ExampleTaskConfig1", "param1": "value1"}
    task1 = AutoTask(config1)
    task1.run()
    config2 = {"name": "ExampleTaskConfig2", "param1": "value2"}
    task2 = AutoTask(config2)
    task2.run()


if __name__ == "__main__":
    main()
