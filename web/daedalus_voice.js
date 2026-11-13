/* =========================================================================
 * Module: web/daedalus_voice.js
 * Daedalus voice capture for Sanders Dash & Seal (added 2026-11-13).
 *
 * Browser-side capture only, dependency-free, no keys and no hardcoded
 * server endpoint. The supported path is the current standard one:
 *
 *   navigator.mediaDevices.getUserMedia({ audio: true })
 *     -> MediaRecorder (Opus in WebM where supported)
 *     -> Blob -> fetch() POST to a caller-supplied endpoint
 *     -> play the returned audio with an <audio> element
 *
 * What this module deliberately does NOT do:
 * - Live WebRTC peer streaming (RTCPeerConnection) is not wired up:
 *   there is no signalling server or peer endpoint in this repository,
 *   and a peer connection without one would be a fabrication. When a
 *   real peer/signalling endpoint exists, add it here behind an
 *   explicit endpoint argument; do not invent one.
 * - No transcription or speech happens in the browser: audio is sent
 *   to the endpoint the caller configures, which is expected to run
 *   the server-side Daedalus voice pipeline (core_platform/daedalus_voice.py).
 * - No audio is stored by this module. Object URLs are revoked after
 *   playback ends.
 * ========================================================================= */

"use strict";

(function (global) {
    var MIME_CANDIDATES = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/mp4",
        "audio/ogg;codecs=opus",
        ""
    ];

    function supported() {
        var nav = global.navigator || {};
        return {
            getUserMedia: Boolean(
                nav.mediaDevices && typeof nav.mediaDevices.getUserMedia === "function"
            ),
            mediaRecorder: typeof global.MediaRecorder === "function",
            audioPlayback: typeof global.Audio === "function"
        };
    }

    function pickMimeType() {
        if (typeof global.MediaRecorder !== "function") return "";
        if (typeof global.MediaRecorder.isTypeSupported !== "function") return "";
        for (var i = 0; i < MIME_CANDIDATES.length; i++) {
            var candidate = MIME_CANDIDATES[i];
            if (candidate === "" || global.MediaRecorder.isTypeSupported(candidate)) {
                return candidate;
            }
        }
        return "";
    }

    function startCapture(options) {
        var opts = options || {};
        var caps = supported();
        if (!caps.getUserMedia) {
            return Promise.reject(new Error("getUserMedia is not available in this browser"));
        }
        if (!caps.mediaRecorder) {
            return Promise.reject(new Error("MediaRecorder is not available in this browser"));
        }
        var constraints = {
            audio: {
                echoCancellation: true,
                noiseSuppression: true
            }
        };
        if (opts.deviceId) constraints.audio.deviceId = { exact: opts.deviceId };
        return global.navigator.mediaDevices.getUserMedia(constraints).then(function (stream) {
            var mimeType = pickMimeType();
            var recorder = mimeType
                ? new global.MediaRecorder(stream, { mimeType: mimeType })
                : new global.MediaRecorder(stream);
            var chunks = [];
            recorder.addEventListener("dataavailable", function (event) {
                if (event.data && event.data.size > 0) chunks.push(event.data);
            });
            recorder.start(opts.timesliceMs || 250);
            var stopped = false;
            return {
                recorder: recorder,
                stream: stream,
                mimeType: recorder.mimeType || mimeType,
                stop: function () {
                    if (stopped) return Promise.resolve(null);
                    stopped = true;
                    return new Promise(function (resolve) {
                        recorder.addEventListener("stop", function onStop() {
                            recorder.removeEventListener("stop", onStop);
                            stream.getTracks().forEach(function (track) { track.stop(); });
                            resolve(new Blob(chunks, { type: recorder.mimeType || mimeType }));
                        });
                        if (recorder.state !== "inactive") recorder.stop();
                    });
                }
            };
        });
    }

    function record(options) {
        var opts = options || {};
        var maxMs = typeof opts.maxMs === "number" && opts.maxMs > 0 ? opts.maxMs : 30000;
        return startCapture(opts).then(function (capture) {
            return new Promise(function (resolve, reject) {
                var timer = setTimeout(function () {
                    capture.stop().then(resolve, reject);
                }, maxMs);
                capture.stop = (function (originalStop) {
                    return function () {
                        clearTimeout(timer);
                        return originalStop();
                    };
                })(capture.stop);
                if (typeof opts.onStarted === "function") opts.onStarted(capture);
            });
        });
    }

    function sendAudio(blob, endpoint, options) {
        if (!blob || blob.size === 0) {
            return Promise.reject(new Error("Audio blob is required"));
        }
        if (!endpoint) {
            return Promise.reject(new Error("A voice endpoint URL is required"));
        }
        var opts = options || {};
        return fetch(endpoint, {
            method: "POST",
            body: blob,
            headers: { "Content-Type": blob.type || "application/octet-stream" },
            signal: opts.signal || undefined
        });
    }

    function playAudio(blob) {
        if (!blob || blob.size === 0) {
            return Promise.reject(new Error("Audio blob is required"));
        }
        if (typeof global.Audio !== "function") {
            return Promise.reject(new Error("Audio playback is not available in this browser"));
        }
        var url = URL.createObjectURL(blob);
        var audio = new global.Audio(url);
        audio.addEventListener("ended", function () { URL.revokeObjectURL(url); });
        return audio.play().then(function () { return audio; });
    }

    function playResponseAudio(response) {
        var contentType = response.headers.get("Content-Type") || "";
        if (contentType.indexOf("audio/") !== 0) {
            return Promise.reject(
                new Error("Voice endpoint did not return audio (Content-Type: " + contentType + ")")
            );
        }
        return response.blob().then(playAudio);
    }

    global.DaedalusVoice = {
        supported: supported,
        pickMimeType: pickMimeType,
        startCapture: startCapture,
        record: record,
        sendAudio: sendAudio,
        playAudio: playAudio,
        playResponseAudio: playResponseAudio
    };
})(typeof window !== "undefined" ? window : globalThis);
