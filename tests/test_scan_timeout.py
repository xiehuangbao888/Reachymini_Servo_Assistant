import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import web_tool as web


class ScanTests(unittest.TestCase):
    def test_hung_child_terminated_and_next_probe_works(self):
        real_popen = subprocess.Popen
        children = []
        def record(*args, **kwargs):
            child = real_popen(*args, **kwargs)
            children.append(child)
            return child
        start = time.monotonic()
        with patch.object(web.subprocess, 'Popen', side_effect=record):
            with self.assertRaisesRegex(RuntimeError, '扫描超时'):
                web.isolated_scan('wrong-port', 1000000, threading.Event(), timeout=0.4,
                                  command=[sys.executable, '-c', 'import time; time.sleep(60)'])
        self.assertLess(time.monotonic() - start, 4)
        self.assertIsNotNone(children[0].poll())
        result = web.isolated_scan('test', 1000000, threading.Event(),
            command=[sys.executable, '-c', 'print(\'{"devices":{"15":[1200,53]}}\')'])
        self.assertEqual(result, {'15': [1200, 53]})

    def test_cancel_child(self):
        cancel = threading.Event()
        timer = threading.Timer(0.2, cancel.set)
        timer.start()
        try:
            with self.assertRaisesRegex(RuntimeError, '扫描已取消'):
                web.isolated_scan('test', 1000000, cancel,
                                  command=[sys.executable, '-c', 'import time; time.sleep(60)'])
        finally:
            timer.join()

    def test_probe_error_is_reported(self):
        with self.assertRaisesRegex(RuntimeError, 'port unavailable'):
            web.isolated_scan('test', 1000000, threading.Event(),
                command=[sys.executable, '-c', 'print(\'{"error":"port unavailable"}\')'])

    def test_timeout_unlocks_job_and_leaves_disconnected(self):
        with tempfile.TemporaryDirectory() as output:
            tool = web.Tool(output_dir=output)
            with patch.object(web, 'isolated_scan', side_effect=RuntimeError('扫描超时')):
                tool.run('scan', dict(port='COM-test', baudrate=1000000))
            self.assertEqual(tool.job['status'], 'error')
            self.assertIsNone(tool.connection)
            self.assertEqual(tool.devices, {})
            with patch.object(web, 'isolated_scan', return_value={'15': [1200, 53]}):
                tool.run('scan', dict(port='COM-test', baudrate=1000000))
            self.assertEqual(tool.job['status'], 'success')

    def test_cancel_request_only_allowed_for_scan(self):
        with tempfile.TemporaryDirectory() as output:
            tool = web.Tool(demo=True, output_dir=output)
            tool.job = dict(kind='restore', status='running')
            with self.assertRaises(ValueError):
                tool.start('cancel-scan', {})
            self.assertFalse(tool.cancel_scan.is_set())
            tool.job = dict(kind='scan', status='running')
            tool.start('cancel-scan', {})
            self.assertTrue(tool.cancel_scan.is_set())
