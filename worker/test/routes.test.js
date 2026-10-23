'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { once } = require('node:events');

test('Dashboard asset includes WebRTC telemetry binding', async () => {
 const fs = require('node:fs/promises');
 const html = await fs.readFile(path.join(__dirname,'../src/dashboard.html'),'utf8');
 assert.match(html,/window\.SDS_BindTelemetry/);
 assert.match(html,/getStats\(\)/);
});

test('Actual worker serves the native telemetry dashboard', async () => {
 const workerPath = path.join(__dirname,'../src/index.js');
 const backend = http.createServer((req,res) => {res.writeHead(503);res.end();});
 backend.listen(0,'127.0.0.1');
 await once(backend,'listening');
 const backendPort=backend.address().port;
 const port = await reservePort();
 const running=spawn(process.execPath,[workerPath],{
   cwd:path.join(__dirname,'..'),
   env:{...process.env,PORT:String(port),PYTHON_BACKEND_URL:'http://127.0.0.1:'+backendPort},
   stdio:['ignore','pipe','pipe']
  });
 try {
   const response=await waitForDashboard(port,running);
   assert.equal(response.status,200);
   assert.match(response.type,/^text\/html/);
   assert.match(response.body,/window\.SDS_BindTelemetry/);
   assert.equal(response.cache,'no-store');
   assert.equal(response.nosniff,'nosniff');
 } finally {
   running.kill('SIGTERM');
   await Promise.race([once(running,'exit'),new Promise(resolve=>setTimeout(resolve,6500))]);
   if(running.exitCode===null)running.kill('SIGKILL');
  }
 backend.close();
});

async function reservePort(){
 const server=http.createServer();
 server.listen(0,'127.0.0.1');await once(server,'listening');
 const port=server.address().port;
 await new Promise(resolve=>server.close(resolve));
 return port;
}
async function waitForDashboard(port,child){
 let lastError;
 for(let attempt=0;attempt<40;attempt++){
  if(child.exitCode!==null)throw new Error('Worker exited unexpectedly: '+child.exitCode);
  try {
   return await new Promise((resolve,reject)=>{
    const req=http.get('http://127.0.0.1:'+port+'/v1/telemetry/dashboard',res=>{
     let body='';res.setEncoding('utf8');res.on('data',chunk=>body+=chunk);
     res.on('end',()=>resolve({status:res.statusCode,type:res.headers['content-type'],
      cache:res.headers['cache-control'],nosniff:res.headers['x-content-type-options'],body}));
    });
    req.setTimeout(1000,()=>req.destroy(new Error('timeout')));
    req.on('error',reject);
   });
  }catch(err){lastError=err;await new Promise(resolve=>setTimeout(resolve,100));}
 }
 throw lastError||new Error('Worker did not start');
}
