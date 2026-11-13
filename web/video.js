'use strict';
/* Sanders Dash & Seal — video / realtime page logic.
 *
 * Dependency-free vanilla JS. Two modes, both honest about what works:
 *
 * 1. Signalling-only (works today, no provider): camera/mic preview via
 *    getUserMedia, screen share via getDisplayMedia, and offer/answer/ICE
 *    relay through the in-repo signalling contract in
 *    worker/src/webrtc.js (messages: initialize_session, offer, answer,
 *    ice_candidate, targetSessionId). No peer connection is opened until
 *    the page has a session id + token AND a peer; without a signalling
 *    server / SFU there is no live call -- the status line says so.
 * 2. LiveKit (only when /api/realtime/status reports livekit_configured):
 *    the page fetches a session-scoped token from /api/realtime/token and
 *    dynamically loads the LiveKit client SDK. The SDK version must match
 *    the deployed LiveKit server; the load is attempted only in this mode
 *    and any failure degrades to mode 1 with a visible message. No SDK
 *    is bundled and no CDN call happens in mode 1.
 *
 * Nothing is captured, uploaded, or stored until you press a button.
 * Requires HTTPS or localhost + camera/mic/screen permission.
 */
const statusEl = document.getElementById('status');
const previewEl = document.getElementById('preview');
const screenEl = document.getElementById('screen');
const logEl = document.getElementById('log');
const sessionInput = document.getElementById('sessionId');
const startBtn = document.getElementById('startBtn');
const shareBtn = document.getElementById('shareBtn');
const stopShareBtn = document.getElementById('stopShareBtn');
const joinBtn = document.getElementById('joinBtn');
const leaveBtn = document.getElementById('leaveBtn');

let mediaStream = null;
let screenStream = null;
let peerConnection = null;
let signallingSocket = null;
let realtimeStatus = null;

function setStatus(text) { statusEl.textContent = text; }
function log(text) { logEl.textContent += text + '\n'; }

async function fetchRealtimeStatus() {
  try {
    const res = await fetch('/api/realtime/status');
    if (!res.ok) throw new Error('HTTP ' + res.status);
    realtimeStatus = await res.json();
    return realtimeStatus;
  } catch (err) {
    realtimeStatus = { provider: 'none', livekit_configured: false };
    log('Realtime status unavailable (' + err.message + '); signalling-only mode.');
    return realtimeStatus;
  }
}

/* --- Camera / mic preview (no upload) --- */
async function startPreview() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setStatus('getUserMedia is not available in this browser.');
    return;
  }
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
    previewEl.srcObject = mediaStream;
    setStatus('Preview running. No live call: no signalling server / SFU is configured yet.');
    log('Camera/mic preview started (local only, nothing uploaded).');
  } catch (err) {
    setStatus('Camera/mic permission denied or unavailable: ' + err.message);
  }
}

/* --- Screen share via getDisplayMedia (video track only; system audio is browser-dependent) --- */
async function startScreenShare() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
    setStatus('getDisplayMedia (screen share) is not available in this browser.');
    return;
  }
  try {
    screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
    screenEl.srcObject = screenStream;
    const track = screenStream.getVideoTracks()[0];
    track.addEventListener('ended', () => { stopScreenShare(); });
    shareBtn.disabled = true;
    stopShareBtn.disabled = false;
    setStatus('Sharing screen (local preview). The track is published over the call session once joined.');
    log('Screen share started: ' + (track.label || '(unnamed display)'));
  } catch (err) {
    setStatus('Screen share cancelled or unavailable: ' + err.message);
  }
}

function stopScreenShare() {
  if (screenStream) screenStream.getTracks().forEach((t) => t.stop());
  screenStream = null;
  screenEl.srcObject = null;
  shareBtn.disabled = false;
  stopShareBtn.disabled = true;
  setStatus('Screen share stopped.');
}

/* --- Signalling (mirrors worker/src/webrtc.js exactly) --- */
function signallingMessage(action, extra) {
  const sessionId = sessionInput.value.trim();
  if (!sessionId) throw new Error('Enter a session id first.');
  return Object.assign({ action, targetSessionId: sessionId }, extra || {});
}

function openSignallingSocket() {
  if (signallingSocket && signallingSocket.readyState === WebSocket.OPEN) return signallingSocket;
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(proto + '//' + location.host + '/ws/webrtc');
  ws.addEventListener('open', () => {
    try {
      ws.send(JSON.stringify(signallingMessage('initialize_session')));
      log('Signalling: session initialised.');
    } catch (err) { setStatus(err.message); }
  });
  ws.addEventListener('message', (event) => {
    let msg;
    try { msg = JSON.parse(event.data); } catch (err) { log('Signalling: unparseable message ignored.'); return; }
    if (msg.type === 'webrtc_error') { setStatus('Signalling error: ' + msg.error); return; }
    if (msg.type === 'webrtc_signal') handleRemoteSignal(msg);
  });
  ws.addEventListener('error', () => setStatus('Signalling socket error. No signalling server is running for this page yet.'));
  signallingSocket = ws;
  return ws;
}

async function handleRemoteSignal(msg) {
  if (!peerConnection) { log('Signalling: no peer connection; remote ' + msg.action + ' ignored.'); return; }
  try {
    if (msg.action === 'offer' || msg.action === 'answer') {
      await peerConnection.setRemoteDescription(new RTCSessionDescription(msg.sdp));
      log('Signalling: remote ' + msg.action + ' applied.');
      if (msg.action === 'offer') {
        const answer = await peerConnection.createAnswer();
        await peerConnection.setLocalDescription(answer);
        signallingSocket.send(JSON.stringify(signallingMessage('answer', { sdp: peerConnection.localDescription })));
      }
    } else if (msg.action === 'ice_candidate' && msg.candidate) {
      await peerConnection.addIceCandidate(new RTCIceCandidate(msg.candidate));
      log('Signalling: remote ICE candidate applied.');
    }
  } catch (err) { setStatus('Signalling handling failed: ' + err.message); }
}

/* --- Join: peer-to-peer via the in-repo relay (needs a signalling server + peer) --- */
async function joinCall() {
  const sessionId = sessionInput.value.trim();
  if (!sessionId) { setStatus('Enter a session id first.'); return; }
  if (!mediaStream) await startPreview();
  if (!mediaStream) return;
  try {
    peerConnection = new RTCPeerConnection();
    mediaStream.getTracks().forEach((t) => peerConnection.addTrack(t, mediaStream));
    if (screenStream) screenStream.getTracks().forEach((t) => peerConnection.addTrack(t, screenStream));
    peerConnection.addEventListener('icecandidate', (event) => {
      if (event.candidate && signallingSocket) {
        signallingSocket.send(JSON.stringify(signallingMessage('ice_candidate', { candidate: event.candidate })));
      }
    });
    peerConnection.addEventListener('track', (event) => {
      previewEl.srcObject = event.streams[0];
      log('Remote track received.');
    });
    const ws = openSignallingSocket();
    ws.addEventListener('open', async () => {
      const offer = await peerConnection.createOffer();
      await peerConnection.setLocalDescription(offer);
      ws.send(JSON.stringify(signallingMessage('offer', { sdp: peerConnection.localDescription })));
      log('Signalling: offer sent for session ' + sessionId + '. Waiting for a peer.');
    }, { once: true });
    joinBtn.disabled = true;
    leaveBtn.disabled = false;
    setStatus('Joining session ' + sessionId + ' (signalling-only; a live call needs a signalling server and a peer).');
  } catch (err) { setStatus('Join failed: ' + err.message); }
}

function leaveCall() {
  if (peerConnection) { peerConnection.close(); peerConnection = null; }
  if (signallingSocket) { signallingSocket.close(); signallingSocket = null; }
  joinBtn.disabled = false;
  leaveBtn.disabled = true;
  setStatus('Left the call.');
}

/* --- LiveKit (only when the server reports it configured) --- */
async function joinViaLiveKit() {
  const status = realtimeStatus || (await fetchRealtimeStatus());
  if (!status.livekit_configured) {
    setStatus('LiveKit is not configured (LIVEKIT_URL / LIVEKIT_API_KEY / LIVEKIT_API_SECRET). Use signalling-only join, or configure LiveKit first.');
    return;
  }
  const sessionId = sessionInput.value.trim();
  if (!sessionId) { setStatus('Enter a session id (used as the LiveKit room) first.'); return; }
  try {
    const res = await fetch('/api/realtime/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ room: sessionId, identity: 'user-' + sessionId }),
    });
    if (!res.ok) throw new Error('token endpoint HTTP ' + res.status);
    const data = await res.json();
    /* The LiveKit client SDK is loaded on demand only in this branch.
     * Pin the SDK major version to the deployed LiveKit server before
     * relying on it; a failed load degrades to signalling-only mode. */
    const livekit = await import('https://cdn.jsdelivr.net/npm/livekit-client@2/+esm');
    const room = new livekit.Room();
    await room.connect(data.url, data.token);
    log('LiveKit: connected to room ' + data.room + ' as ' + data.identity + '.');
    setStatus('LiveKit call live in room ' + data.room + '.');
  } catch (err) {
    setStatus('LiveKit join failed (' + err.message + '). Signalling-only mode is still available.');
    log('LiveKit join failed: ' + err.message);
  }
}

startBtn.addEventListener('click', startPreview);
shareBtn.addEventListener('click', startScreenShare);
stopShareBtn.addEventListener('click', stopScreenShare);
joinBtn.addEventListener('click', joinCall);
leaveBtn.addEventListener('click', leaveCall);
document.getElementById('livekitBtn').addEventListener('click', joinViaLiveKit);
fetchRealtimeStatus().then((status) => {
  setStatus(status.livekit_configured
    ? 'LiveKit is configured. You can join via LiveKit or signalling-only.'
    : 'Signalling-only mode: no LiveKit/SFU configured yet. Camera preview and screen share work locally; a live call needs a signalling server or LiveKit.');
});
