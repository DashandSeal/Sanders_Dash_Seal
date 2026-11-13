"""Disposable loopback test authority; never packaged or a production factory."""
from pathlib import Path
import signal
import sys
import tempfile
from types import SimpleNamespace
from wsgiref.simple_server import make_server, WSGIRequestHandler

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core_platform.appointments import AppointmentStore
from core_platform.cases import CaseRegistry
from core_platform.deployment import create_application, RuntimeBindings, ORIGIN
from core_platform.glass_box_audit import GlassBoxAudit
from core_platform.upgrade_sidecar import CORE_LAWS


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass


def stop(*args):
    raise SystemExit(0)


signal.signal(signal.SIGTERM, stop)
with tempfile.TemporaryDirectory(prefix='sds-worker-test-') as directory:
    root = Path(directory)
    cases = CaseRegistry(root / 'cases.db', CORE_LAWS)
    audit = GlassBoxAudit(root / 'audit.db')
    appointments = AppointmentStore(cases, audit)
    def unavailable(env, start):
        start('503 Service Unavailable', [('Content-Length', '0')])
        return [b'']
    bindings = RuntimeBindings(appointments,
        SimpleNamespace(appointments=appointments, origin=ORIGIN),
        lambda env: 'test-customer' if env.get('HTTP_COOKIE') == 'session=test' else None,
        unavailable, lambda: True)
    app = create_application(bindings if sys.argv[1] == 'enabled' else None)
    with make_server('127.0.0.1', 0, app, handler_class=QuietHandler) as server:
        print(server.server_port, flush=True)
        server.serve_forever()
