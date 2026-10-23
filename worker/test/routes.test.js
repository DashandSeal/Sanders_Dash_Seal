'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');

// Exercise the dashboard asset and the same response semantics as the worker route.
// A separate end-to-end test is required to exercise the actual worker process.
test('Dashboard asset is present with WebRTC binding', async () => {
 const file=path.join(__dirname,'../src/dashboard.html');
 const html=await fs.promises.readFile(file,'utf8');
 assert.match(html,/window\.SDS_BindTelemetry/);
 assert.match(html,/getStats\(\)/);
});
test('Dashboard HTTP response serves HTML and binding hook', async () => {
 const dashboardPath=path.join(__dirname,'../src/dashboard.html');
 const server=http.createServer((req,res)=>{
  if(req.method==='GET' && req.url==='/v1/telemetry/dashboard'){
   fs.readFile(dashboardPath,(err,content)=>{
    if(err){res.writeHead(500,{'Content-Type':'application/json'});res.end(JSON.stringify({error:'Dashboard unavailable'}));return;}
    res.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});
    res.end(content);
   });return;
  }
  res.writeHead(404);res.end();
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 try{
  const port=server.address().port;
  const result=await new Promise((resolve,reject)=>{
   http.get('http://127.0.0.1:'+port+'/v1/telemetry/dashboard',res=>{
    let body='';res.setEncoding('utf8');res.on('data',chunk=>body+=chunk);
    res.on('end',()=>resolve({status:res.statusCode,type:res.headers['content-type'],body}));
   }).on('error',reject);
  });
  assert.equal(result.status,200);
  assert.match(result.type,/^text\/html/);
  assert.ok(result.body.includes('window.SDS_BindTelemetry'));
 }finally{await new Promise(resolve=>server.close(resolve));}
});
