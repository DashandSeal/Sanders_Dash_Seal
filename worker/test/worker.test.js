'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const { once } = require('node:events');
const { WebSocket } = require('ws');
const { createWorker, HOST, ORIGIN } = require('../src/worker');

const payload = { request_id: 'retry-1', jurisdiction: 'CO', service: 'MOBILE_NOTARY',
    requested_start: '2027-01-01T10:00:00Z', meeting_area: 'Denver', consent: true };
const frame = () => JSON.stringify({ action: 'request_appointment', payload });
async function fixture(t, options = {}) {
    const state = { ready: true, authenticated: true, writes: [], mode: 'ok' };
    const backend = http.createServer((req, res) => {
        const reply = (status, data) => {
            res.writeHead(status, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(data));
        };
        assert.equal(req.headers.host, HOST);
        assert.equal(req.headers.origin, ORIGIN);
        if (req.url === '/readyz') return reply(state.ready ? 200 : 503, { service_ready: state.ready });
        if (!state.ready) return reply(503, {});
        if (!state.authenticated || req.headers.cookie !== 'session=test') return reply(401, {});
        if (req.url === '/api/session') return reply(200, { authenticated: true });
        assert.equal(req.url, '/api/appointments');
        assert.equal(req.method, 'POST');
        const chunks = [];
        req.on('data', chunk => chunks.push(chunk));
        req.on('end', () => {
            state.writes.push(JSON.parse(Buffer.concat(chunks)));
            if (state.mode === 'timeout') return;
            if (state.mode === 'rejected') return reply(400, { error: 'private details never forwarded' });
            if (state.mode === 'malformed') return reply(201, { appointment: {} });
            if (state.mode === 'large') return reply(201, { data: 'x'.repeat(20000) });
            reply(201, { appointment: { case_id: 'appointment-fixture', status: 'PENDING_REVIEW',
                meeting_area: 'Private field must not appear in ack' } });
        });
    });
    backend.listen(0, '127.0.0.1'); await once(backend, 'listening');
    const worker = createWorker({ backendUrl: `http://127.0.0.1:${backend.address().port}`,
        shutdownMs: 50, backendTimeoutMs: 100, ...options });
    worker.server.listen(0, '127.0.0.1'); await once(worker.server, 'listening');
    const port = worker.server.address().port;
    const clients = [];
    t.after(async () => {
        for (const ws of clients) ws.terminate();
        await worker.shutdown();
        backend.closeAllConnections();
        await new Promise(resolve => backend.close(resolve));
    });
    function client({ path = '/ingest', headers = {}, ...rest } = {}) {
        const ws = new WebSocket(`ws://127.0.0.1:${port}${path}`, { headers: {
            Host: HOST, Origin: ORIGIN, Cookie: 'session=test', ...headers }, ...rest });
        ws.on('error', () => {}); clients.push(ws); return ws;
    }
    async function open(options) { const ws = client(options); await once(ws, 'open'); return ws; }
    async function denied(options) {
        const ws = client(options);
        return new Promise((resolve, reject) => {
            ws.on('unexpected-response', (req, res) => {
                res.resume(); ws.terminate(); resolve(res.statusCode);
            });
            ws.on('open', () => reject(new Error('Unexpected admission')));
        });
    }
    async function status(path, host = HOST) {
        return new Promise((resolve, reject) => http.get({ host: '127.0.0.1', port,
            path, headers: { Host: host } }, res => {
            res.resume(); res.on('end', () => resolve(res.statusCode));
        }).on('error', reject));
    }
    return { state, worker, open, denied, status };
}
async function send(ws, data = frame()) {
    const received = once(ws, 'message'); ws.send(data);
    return JSON.parse((await received)[0].toString());
}

test('liveness differs from backend-authorized readiness', async t => {
    const f = await fixture(t);
    assert.equal(await f.status('/healthz'), 200);
    assert.equal(await f.status('/readyz'), 200);
    f.state.ready = false;
    assert.equal(await f.status('/readyz'), 503);
    assert.equal(await f.denied(), 503);
    assert.equal(await f.status('/healthz', 'attacker.example'), 421);
});
test('upgrade requires exact host, origin, path, cookie and verified Python session', async t => {
    const f = await fixture(t);
    assert.equal(await f.denied({ path: '/ingest?token=secret' }), 404);
    assert.equal(await f.denied({ headers: { Host: 'sanderslegalhelpersllc.com' } }), 403);
    assert.equal(await f.denied({ headers: { Origin: 'https://attacker.example' } }), 403);
    assert.equal(await f.denied({ headers: { Cookie: '' } }), 401);
    assert.equal(await f.denied({ headers: { Cookie: 'forged=true' } }), 401);
    f.state.authenticated = false;
    assert.equal(await f.denied(), 401);
    assert.equal(f.state.writes.length, 0);
});
test('only successful Python request receipt returns a minimal acknowledgment', async t => {
    const f = await fixture(t), ws = await f.open();
    const ack = await send(ws);
    assert.deepEqual(ack, { ack: true, request_id: payload.request_id,
        case_id: 'appointment-fixture', status: 'request_recorded' });
    assert.deepEqual(f.state.writes, [payload]);
    assert.deepEqual(await send(ws), ack);
    assert.equal(f.state.writes[1].request_id, payload.request_id);
});
test('unsupported transactions, binary and malformed messages never reach Python', async t => {
    const f = await fixture(t), ws = await f.open();
    for (const invalid of ['not json', 'null', '[]',
        JSON.stringify({ action: 'dispatch_transaction', payload }), Buffer.from(frame())]) {
        assert.deepEqual(await send(ws, invalid), { error: 'invalid_request' });
    }
    assert.equal(f.state.writes.length, 0);
});
test('Python session revocation closes an existing connection', async t => {
    const f = await fixture(t), ws = await f.open();
    f.state.authenticated = false;
    const closed = once(ws, 'close'); ws.send(frame());
    assert.equal((await closed)[0], 1008);
    assert.equal(f.state.writes.length, 0);
});
test('release revocation and failed receipts never produce an ack', async t => {
    const f = await fixture(t), ws = await f.open();
    for (const mode of ['rejected', 'malformed', 'large', 'timeout']) {
        f.state.mode = mode;
        const result = await send(ws);
        assert.equal(result.ack, undefined);
        assert.equal(result.request_id, payload.request_id);
        assert.equal(result.error, mode === 'rejected' ? 'request_rejected' : 'outcome_unconfirmed');
    }
    f.state.ready = false;
    assert.equal((await send(ws)).error, 'outcome_unconfirmed');
});
test('oversized WebSocket frame is closed before backend submission', async t => {
    const f = await fixture(t), ws = await f.open();
    const closed = once(ws, 'close'); ws.send('x'.repeat(4097));
    assert.equal((await closed)[0], 1009);
    assert.equal(f.state.writes.length, 0);
});
test('connection and per-session rates are bounded', async t => {
    const f = await fixture(t, { maxConnections: 1, messagesPerMinute: 1 });
    const ws = await f.open();
    assert.equal(await f.denied(), 503);
    await send(ws);
    const closed = once(ws, 'close'); ws.send(frame());
    assert.equal((await closed)[0], 1008);
    assert.equal(f.state.writes.length, 1);
});
test('concurrent messages cannot grow an unbounded queue', async t => {
    const f = await fixture(t), ws = await f.open(); f.state.mode = 'timeout';
    const closed = once(ws, 'close'); ws.send(frame()); ws.send(frame());
    assert.equal((await closed)[0], 1008);
    assert.ok(f.state.writes.length <= 1);
});
test('heartbeat removes nonresponsive clients', async t => {
    const f = await fixture(t, { heartbeatMs: 20 });
    const ws = await f.open({ autoPong: false });
    assert.equal((await once(ws, 'close'))[0], 1006);
});
test('backend concurrency is bounded across connections', async t => {
    const f = await fixture(t, { maxBackendRequests: 1, backendTimeoutMs: 300 });
    const first = await f.open(), second = await f.open();
    f.state.mode = 'timeout';
    first.send(frame());
    // Receipt of the request at Python establishes that the slot is occupied.
    const deadline = Date.now() + 1000;
    while (f.state.writes.length === 0) {
        assert.ok(Date.now() < deadline);
        await new Promise(resolve => setTimeout(resolve, 2));
    }
    assert.equal((await send(second)).error, 'outcome_unconfirmed');
    assert.equal(f.state.writes.length, 1);
});
test('shutdown forcibly closes a peer that will not complete its close handshake', async t => {
    const f = await fixture(t, { shutdownMs: 30 }), ws = await f.open();
    ws._socket.pause(); // Deliberately simulate an unresponsive transport peer.
    const start = Date.now();
    await f.worker.shutdown();
    assert.ok(Date.now() - start < 1000);
    ws._socket.resume();
});
test('shutdown drains upgraded sockets and is idempotent', async t => {
    const f = await fixture(t), ws = await f.open();
    const closed = once(ws, 'close');
    const shutdown = f.worker.shutdown();
    assert.equal(shutdown, f.worker.shutdown());
    assert.equal((await closed)[0], 1001);
    await shutdown;
    assert.equal(f.worker.server.listening, false);
});
test('backend destination and limits cannot silently broaden', () => {
    for (const backendUrl of ['http://attacker.example', 'https://app:8000',
        'http://user:pass@app:8000', 'http://app:8000/private', 'http://app:8000/?x=1']) {
        assert.throws(() => createWorker({ backendUrl }));
    }
    assert.throws(() => createWorker({ maxConnections: -1 }));
});
