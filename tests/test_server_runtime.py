"""Actual HTTP and SIGTERM checks against the pinned server, without live services."""
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class ServerRuntimeTests(unittest.TestCase):
    def test_http_gates_and_clean_sigterm(self):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        root = Path(__file__).resolve().parents[1]
        import os
        env = os.environ.copy()
        env.pop('SANDERS_RUNTIME_FACTORY', None)
        env.pop('GUNICORN_CMD_ARGS', None)
        database = tempfile.TemporaryDirectory(prefix='sds-server-test-')
        self.addCleanup(database.cleanup)
        env['SQLITE_DB_PATH'] = str(Path(database.name) / 'sds_production.db')
        stderr_log = tempfile.TemporaryFile(mode='w+t')
        self.addCleanup(stderr_log.close)
        server = subprocess.Popen([sys.executable, '-m', 'gunicorn', '--config',
            'deploy/gunicorn.conf.py', '--bind', f'127.0.0.1:{port}', 'wsgi:application'],
            cwd=root, env=env, stdout=subprocess.DEVNULL, stderr=stderr_log)
        def status(path, host):
            try:
                with urlopen(Request(f'http://127.0.0.1:{port}{path}',
                                     headers={'Host': host}), timeout=1) as response:
                    return response.status
            except HTTPError as error:
                return error.code
        try:
            deadline = time.monotonic() + 10
            while True:
                try:
                    code = status('/healthz', 'sandersdashandseal.com')
                    break
                except OSError:
                    if server.poll() is not None or time.monotonic() > deadline:
                        stderr_log.seek(0)
                        detail = stderr_log.read().strip()
                        self.fail(f'WSGI server failed to start: {detail or "no server stderr"}')
                    time.sleep(0.05)
            self.assertEqual(code, 200)
            self.assertEqual(status('/readyz', 'sandersdashandseal.com'), 200)
            with urlopen(Request(f'http://127.0.0.1:{port}/readyz',
                    headers={'Host': 'sandersdashandseal.com'}), timeout=1) as response:
                readiness = json.load(response)
            self.assertTrue(readiness['service_ready'])
            self.assertFalse(readiness['complete_build_ready'])
            self.assertEqual(status('/api/appointments', 'sandersdashandseal.com'), 401)
            self.assertEqual(status('/healthz', 'untrusted.invalid'), 421)
            server.terminate()
            self.assertEqual(server.wait(timeout=8), 0)
        finally:
            if server.poll() is None:
                server.kill()
                server.wait(timeout=5)
