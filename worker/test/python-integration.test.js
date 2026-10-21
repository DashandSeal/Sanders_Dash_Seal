'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const { once } = require('node:events');
const path = require('node:path');
const { WebSocket } = require('ws');
const { createWorker, HOST, ORIGIN } = require('../src/worker');

async function runtime(t, mode) {
    const python = spawn('python3', [path.join(__dirname, 'python_fixture.py'), mode],
        { stdio: ['ignore', 'pipe', 'pipe'] });
    let error = '';
    python.stderr.on('data', data => { error += data; });
    t.after(async () => {
        if (python.exitCode === null) {
            const exited = once(python, 'exit'); python.kill('SIGTERM'); await exited;
        }
    });
    const port = await new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error('Python fixture startup timeout')), 5000);
        python.once('error', e => { clearTimeout(timer); reject(e); });
        python.once('exit', () => { clearTimeout(timer); reject(new Error(error || 'Python exited')); });
        python.stdout.once('data', data => {
            clearTimeout(timer); const port = Number(data.toString().trim());
            if (!Number.isInteger(port) || port < 1) reject(new Error('Invalid fixture port'));
            else resolve(port);
        });
    });
    const worker = createWorker({ backendUrl: `http://127.0.0.1:${port}` });
    worker.server.listen(0, '127.0.0.1'); await once(worker.server, 'listening');
    t.after(() => worker.shutdown());
    const client = () => {
        const ws = new WebSocket(`ws://127.0.0.1:${worker.server.address().port}/ingest`, {
            headers: { Host: HOST, Origin: ORIGIN, Cookie: 'session=test' } });
        ws.on('error', () => {}); t.after(() => ws.terminate()); return ws;
    };
    return { client };
}
test('real Python default runtime refuses WebSocket admission', async t => {
    const r = await runtime(t, 'disabled'), ws = r.client();
    const status = await new Promise(resolve => ws.on('unexpected-response', (req, res) => {
        res.resume(); ws.terminate(); resolve(res.statusCode);
    }));
    assert.equal(status, 503);
});
test('Node to real Python SQLite request preserves idempotency and authority rejection', async t => {
    const r = await runtime(t, 'enabled'), ws = r.client(); await once(ws, 'open');
    const payload = { request_id: 'integration-1', jurisdiction: 'CO', service: 'MOBILE_NOTARY',
        requested_start: new Date(Date.now() + 86400000).toISOString(),
        meeting_area: 'Test Denver area', consent: true };
    async function submit(data) {
        const message = once(ws, 'message');
        ws.send(JSON.stringify({ action: 'request_appointment', payload: data }));
        return JSON.parse((await message)[0].toString());
    }
    const first = await submit(payload);
    assert.equal(first.ack, true);
    assert.match(first.case_id, /^appointment-/);
    assert.equal(first.status, 'request_recorded');
    assert.deepEqual(await submit(payload), first);
    assert.equal((await submit({ ...payload, meeting_area: 'Conflicting reuse' })).error, 'request_rejected');
    assert.equal((await submit({ ...payload, request_id: 'integration-2', paid: true })).error, 'request_rejected');
    assert.equal((await submit({ ...payload, request_id: 'integration-3', consent: false })).error, 'request_rejected');
});
