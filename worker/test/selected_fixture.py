"""Loopback-only integration fixture for the owner's selected generic transport."""
import signal
import sys
import tempfile
from pathlib import Path
from wsgiref.simple_server import make_server, WSGIRequestHandler

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core_platform.pipeline_api import create_pipeline_app, TransactionStore, TransactionRejected


class Quiet(WSGIRequestHandler):
    def log_message(self, *args):
        pass


def stop(*args):
    raise SystemExit(0)


def processor(transaction, actor, db):
    if transaction.get('action') != 'test_record':
        raise TransactionRejected('Test operation only')
    db.execute('CREATE TABLE IF NOT EXISTS fixture_records(value TEXT)')
    db.execute('INSERT INTO fixture_records VALUES (?)', (transaction['value'],))
    return {'recorded': True}


signal.signal(signal.SIGTERM, stop)
with tempfile.TemporaryDirectory(prefix='sds-selected-test-') as directory:
    app = create_pipeline_app(
        lambda env: 'test-actor' if env.get('HTTP_AUTHORIZATION') == 'Bearer test-only' else None,
        processor, lambda: True, TransactionStore(Path(directory) / 'pipeline.db'))
    with make_server('127.0.0.1', 0, app, handler_class=Quiet) as server:
        print(server.server_port, flush=True)
        server.serve_forever()
