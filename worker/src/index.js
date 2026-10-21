'use strict';
const { createWorker } = require('./worker');
const port = Number(process.env.PORT || 3000);
if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('Invalid port');
const worker = createWorker({ backendUrl: process.env.PYTHON_BACKEND_URL || 'http://app:8000' });
let exiting = false;
async function stop() {
    if (exiting) return;
    exiting = true;
    await worker.shutdown();
    process.exitCode = 0;
}
process.on('SIGTERM', stop);
process.on('SIGINT', stop);
worker.server.on('error', () => { process.exitCode = 1; void worker.shutdown(); });
worker.server.listen(port, '0.0.0.0', () => {
    console.log('Sanders Dash & Seal ingestion transport started; readiness depends on Python authority.');
});
