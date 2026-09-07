from dataclasses import dataclass
import json
from pathlib import Path
import tempfile
import unittest

from nightjar import register

from easysubmit import AutoTask, Task, TaskConfig
from easysubmit.functions import FileSystemWorker, FileSystemWorkerConfig


@dataclass(eq=False)
class FirstConfig(TaskConfig):
    name: str = 'test-first'
    count: int = 1


@register(name='test-first')
class FirstTask(Task):
    config: FirstConfig


@dataclass(eq=False)
class SecondConfig(TaskConfig):
    name: str = 'test-second'
    value: str = 'default'


@register(name='test-second')
class SecondTask(Task):
    config: SecondConfig


class TaskTests(unittest.TestCase):
    def test_mapping_dispatch_and_conversion(self):
        task = AutoTask({'name': 'test-first', 'count': '7'})
        self.assertIsInstance(task, FirstTask)
        self.assertEqual(task.config.count, 7)
        self.assertIsInstance(AutoTask({'name': 'test-second'}), SecondTask)

    def test_instance_dispatch_preserves_identity(self):
        config = FirstConfig(count=3)
        self.assertIs(AutoTask(config).config, config)

    def test_round_trip(self):
        config = FirstConfig(count=3)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'task.json'
            path.write_text(json.dumps(config.to_dict()))
            restored = TaskConfig.from_json(path)
        self.assertEqual(restored, config)
        self.assertEqual(restored.fingerprint, config.fingerprint)
        self.assertIsInstance(AutoTask(restored), FirstTask)
        self.assertEqual(restored.to_dict()['name'], 'test-first')

    def test_concrete_conversion(self):
        self.assertEqual(FirstConfig.from_dict({'count': '4'}).count, 4)

    def test_invalid_mapping(self):
        for data in ({}, {'name': 'unknown'}):
            with self.assertRaises(ValueError):
                AutoTask(data)
        with self.assertRaises(TypeError):
            AutoTask({'name': 'test-first', 'extra': True})

    def test_ambiguous_dispatch(self):
        @dataclass
        class AmbiguousConfig:
            name: str = 'ambiguous'

        @register(AmbiguousConfig, name='ambiguous')
        class One(Task):
            pass

        @register(AmbiguousConfig, name='ambiguous')
        class Two(Task):
            pass

        from nightjar import dispatch
        with self.assertRaises(ValueError):
            dispatch(AmbiguousConfig, {'name': 'ambiguous'})
        with self.assertRaises(ValueError):
            dispatch(AmbiguousConfig())

    def test_builtin_worker(self):
        config = FileSystemWorkerConfig(dir='/tmp/jobs', task_id='test')
        task = AutoTask(config.to_dict())
        self.assertIsInstance(task, FileSystemWorker)
        self.assertEqual(task.config, config)
        with self.assertRaises(TypeError):
            AutoTask({'name': 'FileSystemWorker'})
