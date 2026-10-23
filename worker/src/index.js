// Assembly prefix: imports and upgrade/message setup connect the owner's earlier
// complete worker to the later helper, receipt, heartbeat and shutdown revision.
const http = require('http');
const fs = require('fs');
const path = require('path');
const { WebSocketServer } = require('ws');
const { handleWebRTCSignaling } = require('./webrtc');

const PORT = process.env.PORT || 3000;
const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://wsgi-backend:8000';
const CLIENT_HEARTBEAT_INTERVAL_MS = 30000;
const activeSockets = new Set();
const server = http.createServer((req, res) => {
    if (req.method === 'GET' && req.url === '/v1/telemetry/dashboard') {
        fs.readFile(path.join(__dirname, 'dashboard.html'), (err, content) => {
            if (err) {
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Dashboard unavailable' }));
                return;
            }
            res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' });
            res.end(content);
        });
        return;
    }
    if (req.url === '/health' || req.url === '/') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'HEALTHY', timestamp: new Date().toISOString(), uptime: process.uptime() }));
        return;
    }
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Endpoint Not Found' }));
});
const wss = new WebSocketServer({ noServer: true });
server.on('upgrade', async (request, socket, head) => {
    socket.on('error', () => {});
    if (isShuttingDown) { socket.destroy(); return; }
    // Browsers cannot set Authorization on WebSocket upgrades. A scoped
    // short-lived token is supplied as a WebSocket subprotocol instead.
    const protocols = (request.headers['sec-websocket-protocol'] || '').split(',').map(v => v.trim());
    const browserProtocol = protocols.find(v => /^sds-auth\\.[a-f0-9]{64}$/.test(v));
    const token = request.headers.authorization || (browserProtocol ? 'Bearer ' + browserProtocol.slice(9) : null);
    if (!token) {
        socket.end('HTTP/1.1 401 Unauthorized\r\nConnection: close\r\nContent-Length: 0\r\n\r\n');
        return;
    }
    const verification = await verifySessionWithPythonBackend(token);
    if (!verification.isValid || isShuttingDown || socket.destroyed) {
        socket.destroy(); return;
    }
    if (browserProtocol) delete request.headers['sec-websocket-protocol'];
    wss.handleUpgrade(request, socket, head, (ws) => {
        ws.sessionData = verification.session;
        wss.emit('connection', ws, request);
    });
});
wss.on('connection', (ws) => {
    activeSockets.add(ws);
    ws.isAlive = true;
    ws.on('pong', () => { ws.isAlive = true; });
    ws.on('message', async (message) => {
        try {
            const payload = JSON.parse(message.toString());
            if (payload && payload.type === 'webrtc_signal') {
                handleWebRTCSignaling(ws, payload, activeSockets);
                return;
            }
            // Proxy transaction payload directly to Python for strict validation and recording
            const backendReceipt = await dispatchToPythonBackend(payload, ws.sessionData);

            if (backendReceipt.success) {
                // Return formal receipt to client ONLY after Python successfully validates and commits
                ws.send(JSON.stringify({ 
                    success: true, 
                    receipt: backendReceipt.data,
                    timestamp: new Date().toISOString()
                }));
            } else {
                ws.send(JSON.stringify({ success: false, error: backendReceipt.error || 'Transaction rejected by transactional engine' }));
            }
        } catch (error) {
            ws.send(JSON.stringify({ success: false, error: 'Malformed framework frame payload dropped' }));
        }
    });

    ws.on('close', () => activeSockets.delete(ws));
    ws.on('error', () => activeSockets.delete(ws));
});

// Heartbeat verification loop to prune dead client channels
const heartbeatMonitor = setInterval(() => {
    wss.clients.forEach((ws) => {
        if (!ws.isAlive) {
            console.log('Terminating dead websocket client channel via heartbeat cleanup.');
            return ws.terminate();
        }
        ws.isAlive = false;
        ws.ping();
    });
}, CLIENT_HEARTBEAT_INTERVAL_MS);

// Helper Network Communication Routines with Backend Authority
function verifySessionWithPythonBackend(token) {
    return new Promise((resolve) => {
        const req = http.request(`${PYTHON_BACKEND_URL}/api/auth/verify`, {
            method: 'POST',
            headers: { 'Authorization': token, 'Content-Type': 'application/json', 'Content-Length': '0' },
            timeout: 3000
        }, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                if (res.statusCode === 200) {
                    try {
                        const session = JSON.parse(data);
                        const id = /^[A-Za-z0-9_.-]{1,128}$/;
                        if (session && id.test(session.user_id || '') &&
                            id.test(session.assigned_session_id || '') &&
                            Array.isArray(session.notary_session_ids) &&
                            session.notary_session_ids.includes(session.assigned_session_id)) {
                            resolve({ isValid: true, session });
                        } else resolve({ isValid: false });
                    } catch (_) { resolve({ isValid: false }); }
                } else {
                    resolve({ isValid: false });
                }
            });
        });
        req.on('error', () => resolve({ isValid: false }));
        req.on('timeout', () => req.destroy());
        req.end();
    });
}

function dispatchToPythonBackend(payload, session) {
    return new Promise((resolve) => {
        const body = JSON.stringify({ transaction: payload, session: session });
        const req = http.request(`${PYTHON_BACKEND_URL}/api/transactions/process`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) }
        }, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                resolve({ success: res.statusCode === 200, data: data ? JSON.parse(data) : null });
            });
        });
        req.on('error', (err) => resolve({ success: false, error: err.message }));
        req.write(body);
        req.end();
    });
}

// Bounded Shutdown State Engine
let isShuttingDown = false;
function initiateGracefulShutdown(signal) {
    if (isShuttingDown) return;
    isShuttingDown = true;

    console.log(`[${signal}] Executing clean pipeline draining sequence.`);
    clearInterval(heartbeatMonitor);

    // Stop accepting new network endpoints
    server.close(() => {
        console.log('Operational HTTP abstraction network server successfully closed.');
        process.exit(0);
    });

    // Notify active connections of maintenance exit status
    for (const ws of activeSockets) {
        if (ws.readyState === ws.OPEN) {
            ws.close(1001, 'Worker entering maintenance mode');
        }
    }

    // Strict 5-second deadline safety rail to prevent lingering processes
    setTimeout(() => {
        console.warn('Forced shutdown timeout deadline elapsed. Halting residual bindings.');
        process.exit(1);
    }, 5000);
}

process.on('SIGTERM', () => initiateGracefulShutdown('SIGTERM'));
process.on('SIGINT', () => initiateGracefulShutdown('SIGINT'));

server.listen(PORT);
