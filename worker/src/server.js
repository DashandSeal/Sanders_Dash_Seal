/*
 * Bozly-owned authenticated WebSocket event relay.
 * Node built-ins only; no socket SaaS, telemetry fabrication or public publisher.
 * Token and entity scope are required. Backend publishers must supply real
 * event provenance. Actual telemetry starts only when a real publisher posts.
 */
"use strict";
const http=require("node:http");
const crypto=require("node:crypto");
const {URL}=require("node:url");
const PORT=Number(process.env.BOZLY_TELEMETRY_PORT||8080);
const HOST=process.env.BOZLY_TELEMETRY_BIND||"0.0.0.0";
const ORIGIN=process.env.BOZLY_PUBLIC_ORIGIN||"";
const PUBLISH_TOKEN=process.env.BOZLY_TELEMETRY_PUBLISH_TOKEN||"";
const RAW_READ=process.env.BOZLY_TELEMETRY_READ_TOKENS_JSON||"{}";
let READ={};
try { READ=JSON.parse(RAW_READ); }catch(_) {throw new Error("Invalid telemetry reader directory");}
if(!READ||typeof READ!=="object"||Array.isArray(READ)) throw new Error("Invalid reader directory");
if(!ORIGIN.startsWith("https://")||!PUBLISH_TOKEN||Object.keys(READ).length===0)
  throw new Error("Configure genuine HTTPS public origin, publisher token and scoped readers");
const peers=new Map();
function equal(a,b){
  if(typeof a!=="string"||typeof b!=="string")return false;
  const x=Buffer.from(a),y=Buffer.from(b);
  return x.length===y.length&&crypto.timingSafeEqual(x,y);
}
function send(socket,object){
  const raw=Buffer.from(JSON.stringify(object));
  if(raw.length>65535) return;
  const header=raw.length<126?Buffer.from([0x81,raw.length]):
    Buffer.from([0x81,126,(raw.length>>8)&255,raw.length&255]);
  if(!socket.destroyed&&socket.writableLength<512000)socket.write(Buffer.concat([header,raw]));
}
function fail(response,code){
 response.writeHead(code,{"Content-Type":"application/json","Cache-Control":"no-store"});
 response.end(JSON.stringify({error:code===401?"UNAUTHORIZED":"REQUEST_REJECTED"}));
}
const server=http.createServer((req,res)=>{
  let path;
  try{path=new URL(req.url,"http://localhost").pathname;}catch(_){return fail(res,400);}
  if(req.method!=="POST"||path!=="/internal/bozly-telemetry")return fail(res,404);
  if(!equal((req.headers.authorization||"").replace(/^Bearer /,""),PUBLISH_TOKEN))
    return fail(res,401);
  let chunks=[],size=0,failed=false;
  req.on("data",part=>{
    size+=part.length;
    if(size>65536){failed=true;req.destroy();return;}
    chunks.push(part);
  });
  req.on("end",()=>{
    if(failed)return;
    let v;
    try{v=JSON.parse(Buffer.concat(chunks).toString("utf8"));}catch(_){return fail(res,400);}
    if(!v||typeof v!=="object"||typeof v.entity_id!=="string"||
       !Object.hasOwn(READ,v.entity_id)||typeof v.kind!=="string"||
       typeof v.reference!=="string"||!Number.isSafeInteger(v.timestamp)||
       typeof v.source_sha256!=="string"||
       !/^[a-f0-9]{64}$/.test(v.source_sha256))
       return fail(res,400);
    const event={entity_id:v.entity_id,kind:v.kind.slice(0,90),
      reference:v.reference.slice(0,240),timestamp:v.timestamp,
      source_sha256:v.source_sha256};
    for(const [socket,entity] of peers){
      if(entity===v.entity_id)send(socket,event);
    }
    res.writeHead(202,{"Content-Type":"application/json","Cache-Control":"no-store"});
    res.end(JSON.stringify({accepted:true,
      active_recipients:[...peers.values()].filter(x=>x===v.entity_id).length}));
  });
});
server.on("upgrade",(req,socket)=>{
  try{
    const path=new URL(req.url,"http://localhost").pathname;
    if(path!=="/v1/telemetry/stream"||req.headers.origin!==ORIGIN||
       req.headers.upgrade?.toLowerCase()!=="websocket"||
       req.headers["sec-websocket-version"]!=="13"){
      socket.destroy();return;
    }
    const protocols=(req.headers["sec-websocket-protocol"]||"").split(",").map(s=>s.trim());
    if(protocols[0]!=="bozly-reader"||protocols.length!==3||!protocols[1]||!protocols[2]){
      socket.destroy();return;
    }
    const entity=protocols[1],token=protocols[2];
    if(!Object.hasOwn(READ,entity)||!equal(token,READ[entity])){
      socket.destroy();return;
    }
    const key=req.headers["sec-websocket-key"];
    if(typeof key!=="string"||!(/^[A-Za-z0-9+/]{22}==$/.test(key))) {
      socket.destroy();return;
    }
    const accept=crypto.createHash("sha1").update(key+
      "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").digest("base64");
    socket.write("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n"+
       "Connection: Upgrade\r\nSec-WebSocket-Accept: "+accept+
       "\r\nSec-WebSocket-Protocol: bozly-reader\r\n\r\n");
    peers.set(socket,entity);
    send(socket,{entity_id:entity,kind:"CONNECTION_READY",
      reference:"Awaiting genuine published telemetry",timestamp:Date.now()/1000|0,
      source_sha256:"0".repeat(64)});
    socket.on("data",raw=>{
      // All client frames must be masked per RFC 6455. No client commands.
      if(raw.length>65536||raw.length<2||!(raw[1]&128)){socket.destroy();return;}
      if((raw[0]&15)===8)socket.end();
    });
    socket.on("close",()=>peers.delete(socket));
    socket.on("error",()=>peers.delete(socket));
  }catch(_){socket.destroy();}
});
server.listen(PORT,HOST);
