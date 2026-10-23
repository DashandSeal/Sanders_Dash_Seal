'use strict';
const http = require('node:http');
const { WebSocketServer, WebSocket } = require('ws');

const HOST = 'sandersdashandseal.com';
const ORIGIN = `https://${HOST}`;
const ID = /^[A-Za-z0-9_.-]{1,128}$/;

// Only administrator configuration selects a backend. No client-supplied URL,
// identity header, shared master key, filesystem transaction or release bypass.
function createWorker({ backendUrl = 'http://app:8000', maxConnections = 64,
    maxBackendRequests = 16, maxPayload = 4096, backendTimeoutMs = 3000,
    heartbeatMs = 30000, shutdownMs = 5000, messagesPerMinute = 30 } = {}) {
    const backend = new URL(backendUrl);
    if (backend.protocol !== 'http:' || backend.username || backend.password ||
        backend.pathname !== '/' || backend.search || backend.hash ||
        !['app', '127.0.0.1', 'localhost'].includes(backend.hostname)) {
        throw new Error('Trusted internal Python backend required');
    }
    for (const value of [maxConnections, maxBackendRequests, maxPayload,
        backendTimeoutMs, heartbeatMs, shutdownMs, messagesPerMinute]) {
        if (!Number.isSafeInteger(value) || value < 1) throw new Error('Invalid limit');
    }
    let stopping = false, pendingUpgrades = 0, closePromise, checkStopped = () => {};
    const requests = new Set();
    const clients = new Set();
    const transports = new Set();

    function python(path, cookie = '', body) {
        if (stopping || requests.size >= maxBackendRequests) {
            return Promise.reject(new Error('Backend unavailable'));
        }
        return new Promise((resolve, reject) => {
            const data = body === undefined ? undefined : JSON.stringify(body);
            const headers = { Host: HOST, Origin: ORIGIN, Accept: 'application/json' };
            if (cookie) headers.Cookie = cookie;
            if (data !== undefined) {
                headers['Content-Type'] = 'application/json';
                headers['Content-Length'] = Buffer.byteLength(data);
            }
            const request = http.request(new URL(path, backend), {
                method: data === undefined ? 'GET' : 'POST', headers, agent: false,
                maxHeaderSize: 8192,
            });
            requests.add(request);
            const timer = setTimeout(() => request.destroy(new Error('Backend timeout')),
                backendTimeoutMs);
            request.on('close', () => { clearTimeout(timer); requests.delete(request); });
            request.on('error', reject);
            request.on('response', response => {
                let size = 0;
                const chunks = [];
                response.on('error', reject);
                response.on('data', chunk => {
                    size += chunk.length;
                    if (size > 16384) request.destroy(new Error('Backend response too large'));
                    else chunks.push(chunk);
                });
                response.on('end', () => {
                    try {
                        if (!response.complete || !/^application\/json(?:;|$)/i.test(
                            response.headers['content-type'] || '')) throw new Error('Invalid response');
                        resolve({ status: response.statusCode,
                            data: JSON.parse(Buffer.concat(chunks).toString('utf8')) });
                    } catch { reject(new Error('Invalid backend response')); }
                });
            });
            request.end(data);
        });
    }
    const server = http.createServer({ maxHeaderSize: 8192 }, async (req, res) => {
        let status = 404, data = { error: 'not_found' };
        if (req.headers.host !== HOST) { status = 421; data = { error: 'host_denied' }; }
        else if (req.method !== 'GET') { status = 405; data = { error: 'method_not_allowed' }; }
        else if (req.url === '/healthz') { status = 200; data = { process_alive: true }; }
        else if (req.url === '/readyz') {
            let ready = false;
            try {
                const result = await python('/readyz');
                ready = result.status === 200 && result.data.service_ready === true;
            } catch { /* Missing bindings, network errors and overload stay unavailable. */ }
            status = ready ? 200 : 503; data = { service_ready: ready };
        }
        res.writeHead(status, { 'Content-Type': 'application/json',
            'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' });
        res.end(JSON.stringify(data));
    });
    server.headersTimeout = 5000;
    server.requestTimeout = 10000;
    server.keepAliveTimeout = 2000;
    server.maxConnections = maxConnections * 2;
    server.on('connection', socket => {
        transports.add(socket);
        socket.on('close', () => transports.delete(socket));
    });
    const wss = new WebSocketServer({ noServer: true, maxPayload,
        perMessageDeflate: false, clientTracking: false });
    function rejectUpgrade(socket, status) {
        if (!socket.destroyed) socket.end(`HTTP/1.1 ${status}\r\nConnection: close\r\nContent-Length: 0\r\n\r\n`);
    }
    server.on('upgrade', async (req, socket, head) => {
        socket.on('error', () => {});
        if (req.url !== '/ingest' || req.method !== 'GET') return rejectUpgrade(socket, '404 Not Found');
        if (req.headers.host !== HOST || req.headers.origin !== ORIGIN) {
            return rejectUpgrade(socket, '403 Forbidden');
        }
        if (stopping || clients.size + pendingUpgrades >= maxConnections) {
            return rejectUpgrade(socket, '503 Service Unavailable');
        }
        const cookie = req.headers.cookie;
        if (!cookie || Buffer.byteLength(cookie) > 4096) return rejectUpgrade(socket, '401 Unauthorized');
        pendingUpgrades++;
        try {
            const session = await python('/api/session', cookie);
            if (session.status !== 200 || session.data.authenticated !== true) {
                return rejectUpgrade(socket, session.status === 401 ? '401 Unauthorized' : '503 Service Unavailable');
            }
            if (stopping || socket.destroyed) return rejectUpgrade(socket, '503 Service Unavailable');
            wss.handleUpgrade(req, socket, head, ws => connect(ws, cookie));
        } catch { rejectUpgrade(socket, '503 Service Unavailable'); }
        finally { pendingUpgrades--; checkStopped(); }
    });
    function send(ws, data) {
        if (ws.readyState !== WebSocket.OPEN) return;
        if (ws.bufferedAmount > 16384) { ws.terminate(); return; }
        ws.send(JSON.stringify(data), error => { if (error) ws.terminate(); });
    }
    function connect(ws, cookie) {
        clients.add(ws);
        let busy = false, alive = true, windowStart = Date.now(), count = 0;
        ws.on('pong', () => { alive = true; });
        ws.heartbeat = () => {
            if (!alive) return ws.terminate();
            alive = false; ws.ping(undefined, undefined, error => { if (error) ws.terminate(); });
        };
        ws.on('error', () => {});
        ws.on('close', () => { clients.delete(ws); checkStopped(); });
        ws.on('message', async (message, binary) => {
            if (stopping) return ws.close(1001, 'Service stopping');
            if (Date.now() - windowStart >= 60000) { windowStart = Date.now(); count = 0; }
            if (++count > messagesPerMinute) return ws.close(1008, 'Rate limit');
            if (busy) return ws.close(1008, 'One pending request permitted');
            let frame;
            try {
                if (binary) throw new Error('Text required');
                frame = JSON.parse(message.toString('utf8'));
                if (!frame || Array.isArray(frame) ||
                    Object.keys(frame).sort().join(',') !== 'action,payload' ||
                    frame.action !== 'request_appointment' || !frame.payload ||
                    typeof frame.payload !== 'object' || Array.isArray(frame.payload) ||
                    !ID.test(frame.payload.request_id || '') ||
                    typeof frame.payload.request_id !== 'string') throw new Error('Invalid frame');
            } catch { send(ws, { error: 'invalid_request' }); return; }
            busy = true;
            const requestId = frame.payload.request_id;
            try {
                // Python validates all fields, rechecks session/release/ownership,
                // commits its audited transaction and handles idempotent retries.
                const result = await python('/api/appointments', cookie, frame.payload);
                if (result.status === 201 && typeof result.data.appointment?.case_id === 'string' &&
                    ID.test(result.data.appointment.case_id)) {
                    send(ws, { ack: true, request_id: requestId,
                        case_id: result.data.appointment.case_id, status: 'request_recorded' });
                } else if (result.status === 401 || result.status === 403) {
                    ws.close(1008, 'Session unavailable');
                } else {
                    send(ws, { error: [400, 409, 415].includes(result.status) ?
                        'request_rejected' : 'outcome_unconfirmed', request_id: requestId });
                }
            } catch { send(ws, { error: 'outcome_unconfirmed', request_id: requestId }); }
            finally { busy = false; }
        });
    }
    const heartbeat = setInterval(() => {
        for (const ws of clients) if (ws.readyState === WebSocket.OPEN) ws.heartbeat();
    }, heartbeatMs);
    heartbeat.unref();

    function shutdown() {
        if (closePromise) return closePromise;
        stopping = true;
        clearInterval(heartbeat);
        closePromise = new Promise(resolve => {
            // Closing an in-flight request can leave an uncertain committed
            // outcome. The client must retry the SAME idempotency request ID.
            for (const request of requests) request.destroy(new Error('Service stopping'));
            for (const ws of clients) ws.close(1001, 'Service stopping');
            const timer = setTimeout(() => {
                for (const ws of clients) ws.terminate();
                for (const socket of transports) socket.destroy();
                server.closeAllConnections();
            }, shutdownMs);
            let httpDone = false;
            checkStopped = () => {
                if (httpDone && clients.size === 0 && pendingUpgrades === 0) {
                    clearTimeout(timer); resolve();
                }
            };
            server.close(() => { httpDone = true; checkStopped(); });
            wss.close();
        });
        return closePromise;
    }
    return { server, shutdown };
}
module.exports = { createWorker, HOST, ORIGIN };
