'use strict';
/* Signaling only. Media capture, archival and participant authorization are separate. */
const ID = /^[A-Za-z0-9_.-]{1,128}$/;
const MAX_SDP = 65536;
const MAX_CANDIDATE = 4096;
function reject(ws, reason) {
  if (ws.readyState === ws.OPEN) ws.send(JSON.stringify({type:'webrtc_error',error:reason}));
}
function handleWebRTCSignaling(ws, payload, activeSockets) {
  if (!ws.sessionData || typeof ws.sessionData.user_id !== 'string' ||
      !ID.test(ws.sessionData.user_id)) return reject(ws,'Authentication required');
  if (!payload || typeof payload !== 'object' || Array.isArray(payload) ||
      !ID.test(payload.targetSessionId || '')) return reject(ws,'Invalid session');
  const sessionId=payload.targetSessionId;
  // The authentication response must explicitly authorize the session.
  if (ws.sessionData.assigned_session_id !== sessionId)
    return reject(ws,'Room assignment mismatch');
  const allowed=ws.sessionData.notary_session_ids;
  if (!Array.isArray(allowed) || !allowed.includes(sessionId))
    return reject(ws,'Session membership not authorized');
  if (payload.action === 'initialize_session') {
    ws.notarySessionId=sessionId;
    return ws.send(JSON.stringify({type:'webrtc_signal',action:'initialized',targetSessionId:sessionId}));
  }
  if (ws.notarySessionId !== sessionId) return reject(ws,'Session not initialized');
  let frame;
  if (payload.action==='offer' || payload.action==='answer') {
    if (!payload.sdp || typeof payload.sdp !== 'object' ||
        payload.sdp.type !== payload.action || typeof payload.sdp.sdp !== 'string' ||
        payload.sdp.sdp.length<1 || payload.sdp.sdp.length>MAX_SDP)
      return reject(ws,'Invalid SDP');
    frame={type:'webrtc_signal',action:payload.action,targetSessionId:sessionId,sdp:payload.sdp,
      sender:ws.sessionData.user_id};
  } else if (payload.action==='ice_candidate') {
    if (!payload.candidate || typeof payload.candidate !== 'object' ||
        typeof payload.candidate.candidate !== 'string' ||
        payload.candidate.candidate.length>MAX_CANDIDATE)
      return reject(ws,'Invalid ICE candidate');
    frame={type:'webrtc_signal',action:'ice_candidate',targetSessionId:sessionId,
      candidate:payload.candidate,sender:ws.sessionData.user_id};
  } else return reject(ws,'Unknown signaling action');
  for (const peer of activeSockets) {
    if (peer===ws || peer.readyState!==peer.OPEN || peer.notarySessionId!==sessionId ||
        !peer.sessionData || !Array.isArray(peer.sessionData.notary_session_ids) ||
        !peer.sessionData.notary_session_ids.includes(sessionId)) continue;
    peer.send(JSON.stringify(frame));
  }
}
module.exports={handleWebRTCSignaling};
