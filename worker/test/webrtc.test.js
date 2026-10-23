'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {handleWebRTCSignaling}=require('../src/webrtc');
function peer(user,allowed) {
  return {OPEN:1,readyState:1,sessionData:{user_id:user,notary_session_ids:allowed},
    sent:[],send(data){this.sent.push(JSON.parse(data));}};
}
test('authorized SDP and ICE routing stays inside the session',()=>{
  const a=peer('notary',['s1']),b=peer('signer',['s1']),c=peer('other',['s2']);
  const sockets=new Set([a,b,c]);
  for (const ws of [a,b]) handleWebRTCSignaling(ws,{action:'initialize_session',targetSessionId:'s1'},sockets);
  handleWebRTCSignaling(a,{action:'offer',targetSessionId:'s1',sdp:{type:'offer',sdp:'v=0'}},sockets);
  assert.equal(b.sent.at(-1).action,'offer');
  assert.equal(c.sent.length,0);
  handleWebRTCSignaling(b,{action:'ice_candidate',targetSessionId:'s1',candidate:{candidate:'candidate:1'}},sockets);
  assert.equal(a.sent.at(-1).action,'ice_candidate');
});
test('unauthorized session and uninitialized routing are rejected',()=>{
  const a=peer('notary',['s1']),b=peer('attacker',['s2']);
  const sockets=new Set([a,b]);
  handleWebRTCSignaling(b,{action:'initialize_session',targetSessionId:'s1'},sockets);
  assert.equal(b.sent.at(-1).type,'webrtc_error');
  handleWebRTCSignaling(a,{action:'offer',targetSessionId:'s1',sdp:{type:'offer',sdp:'v=0'}},sockets);
  assert.equal(a.sent.at(-1).type,'webrtc_error');
});
test('invalid SDP and unauthenticated peers are rejected',()=>{
  const a=peer('notary',['s1']),b=peer('signer',['s1']);
  handleWebRTCSignaling(a,{action:'initialize_session',targetSessionId:'s1'},new Set([a,b]));
  handleWebRTCSignaling(a,{action:'offer',targetSessionId:'s1',sdp:{type:'answer',sdp:'v=0'}},new Set([a,b]));
  assert.equal(a.sent.at(-1).type,'webrtc_error');
  assert.equal(b.sent.length,0);
  delete b.sessionData;
  handleWebRTCSignaling(b,{action:'initialize_session',targetSessionId:'s1'},new Set([a,b]));
  assert.equal(b.sent.at(-1).type,'webrtc_error');
});
