'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const { spawn } = require('node:child_process');
const { once } = require('node:events');
const path = require('node:path');
const { WebSocket } = require('ws');

test('selected worker relays generic transactions to real Python and durable receipts', async t => {
    const processes = [];
    const clients = [];
    t.after(async () => {
        for (const ws of clients) ws.terminate();
        for (const child of processes.reverse()) {
            if (child.exitCode !== null) continue;
            const done = once(child, 'exit'); child.kill('SIGTERM');
            const timer = setTimeout(() => child.kill('SIGKILL'), 6000);
            await done; clearTimeout(timer);
        }
    });
    const python = spawn('python3', [path.join(__dirname, 'selected_fixture.py')],
        { stdio: ['ignore', 'pipe', 'pipe'] });
    processes.push(python);
    const backendPort = await new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error('Python startup timeout')), 5000);
        python.once('error', reject);
        python.once('exit', () => { clearTimeout(timer); reject(new Error('Python exited')); });
        python.stdout.once('data', data => { clearTimeout(timer); resolve(Number(data.toString().trim())); });
    });
    const probe = http.createServer(); probe.listen(0, '127.0.0.1');
    await once(probe, 'listening'); const port = probe.address().port;
    await new Promise(resolve => probe.close(resolve));
    const worker = spawn(process.execPath, [path.join(__dirname, '../src/index.js')], {
        env: { ...process.env, PORT: String(port), PYTHON_BACKEND_URL: `http://127.0.0.1:${backendPort}` },
        stdio: ['ignore', 'ignore', 'pipe'] });
    processes.push(worker);
    async function health() {
        return new Promise((resolve, reject) => {
            http.get(`http://127.0.0.1:${port}/health`, res => {
                res.resume(); res.on('end', () => resolve(res.statusCode));
            }).on('error', reject);
        });
    }
    const deadline = Date.now() + 5000;
    while (true) {
        try { assert.equal(await health(), 200); break; }
        catch (error) { if (Date.now() > deadline) throw error; await new Promise(r => setTimeout(r, 20)); }
    }
    const denied = new WebSocket(`ws://127.0.0.1:${port}/ws`);
    clients.push(denied); denied.on('error', () => {});
    assert.equal(await new Promise(resolve => denied.on('unexpected-response', (req, res) => {
        res.resume(); denied.terminate(); resolve(res.statusCode);
    })), 401);
    const ws = new WebSocket(`ws://127.0.0.1:${port}/ws`, { headers: { Authorization: 'Bearer test-only' } });
    clients.push(ws); await once(ws, 'open');
    async function submit(payload) {
        const message = once(ws, 'message'); ws.send(JSON.stringify(payload));
        return JSON.parse((await message)[0].toString());
    }
    const transaction = { request_id: 'generic-test-1', action: 'test_record', value: 'generic payload' };
    const first = await submit(transaction);
    assert.equal(first.success, true);
    assert.equal(first.receipt.request_id, transaction.request_id);
    assert.equal(first.receipt.result.recorded, true);
    assert.deepEqual((await submit(transaction)).receipt, first.receipt);
    assert.equal((await submit({ ...transaction, value: 'conflicting reuse' })).success, false);
    assert.equal((await submit({ ...transaction, request_id: 'r2', action: 'invalid_operation' })).success, false);
    const badFrame = once(ws, 'message'); ws.send('not json');
    assert.equal(JSON.parse((await badFrame)[0].toString()).success, false);
});
