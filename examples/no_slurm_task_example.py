from __future__ import annotations

import time
from dataclasses import dataclass

from nightjar import register

from easysubmit import AutoTask, Task, TaskConfig


@dataclass(eq=False)
class ExampleTaskConfig1(TaskConfig):
    name: str = "ExampleTaskConfig1"
    param1: str = "default_value"


@register(name="ExampleTaskConfig1")
class ExampleTask(Task):
    config: ExampleTaskConfig1

    def run(self):
        time.sleep(2)
        print(f"ExampleTask({self.config})")


@dataclass(eq=False)
class ExampleTaskConfig2(TaskConfig):
    name: str = "ExampleTaskConfig2"
    param1: str = "default_value"


@register(name="ExampleTaskConfig2")
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
