# LiveKit canonical choice — Sanders Dash & Seal (P3, 2026-11-13)

## Decision

**`core_platform/livekit_realtime.py` is the canonical LiveKit module.**
It owns `LiveKitClient` / `DailyClient` / `RealtimeConfig`, is used by the
live routes (`core_platform/realtime_api.py`, `deploy/deployment.py`
`/api/realtime/*`), and holds the single shared JWT implementation
(`_b64url` / `_b64url_decode` / `_hs256_jwt`).

**`core_platform/livekit_video.py` is RETAINED, not merged away.** It is
the token issue/validate + status helper (`issue_room_token`,
`validate_room_token`, `video_status`, `sdk_available`,
`livekit_config_from_env`) referenced by the service-linking table
(`core_platform/service_linking.py`), and it is imported by
`tests/test_ai_platform_services.py`. Since P3 it imports its JWT
helpers from `livekit_realtime`, so the crypto is implemented once.

## Why a full merge is unsafe (verified 2026-11-13)

The two modules are parallel implementations with different, test-pinned
contracts. Merging them into one API would silently change one caller's
behaviour whichever way the conflict is resolved:

| Difference | `livekit_realtime.py` | `livekit_video.py` | Consequence of forcing one |
|---|---|---|---|
| Identity charset | `[A-Za-z0-9_.-]` (no `@`) — matches the signalling contract in `worker/src/webrtc.js` and `daedalus_voice.validate_video_session` | `[A-Za-z0-9_@.-]` (allows `@`, for email-style identities) | One regex either newly accepts `@` on the realtime route (diverging from the signalling contract) or breaks video tokens for `@` identities |
| Token TTL bounds | 1–86400 s (`DEFAULT_TOKEN_TTL_SECONDS`) | 60–86400 s (`MAX_TTL_SECONDS`, min 60) | One bound either accepts sub-60 s video tokens or rejects short realtime tokens |
| Token issue return | `issue_access_token` / `LiveKitClient.issue_token` return a bare JWT `str` | `issue_room_token` returns a `dict` (`url`, `room`, `identity`, `token`, `expires_at`, `status`, `note`) | Callers (`realtime_api.py` vs service tests) depend on each shape |
| Missing-config error | `RealtimeNotConfigured` | `ValueError` | Callers catching one type would miss the other |
| Unique scope | `DailyClient`, `RealtimeConfig`, `FakeRoomService`, `screen_share_requirements`, `is_valid_webrtc_token` | `sdk_available`, `video_status`, `livekit_config_from_env`, `validate_room_token` (local JWT validation) | A merged module would still carry both token paths — ~700 lines with two overlapping APIs, not one |

## What WAS unified (P3)

- The duplicated JWT helpers: `livekit_video._b64url` /
  `_b64url_decode` were deleted; `livekit_video` imports both from
  `livekit_realtime`. The crypto is now implemented once.
- Interoperability is pinned by test: `tests/test_p3_livekit.py`
  proves a token issued by `livekit_realtime.issue_access_token`
  validates under `livekit_video.validate_room_token` (same secret),
  and a token issued by `livekit_video.issue_room_token` decodes under
  `livekit_realtime._decode_jwt_payload` with identical claims. Both
  payloads use the same LiveKit wire format (`iss` = API key, `sub` =
  identity, `video.room` / `video.roomJoin` / `canPublish` /
  `canSubscribe`). The identity-`@` difference is also pinned:
  `livekit_video` accepts it, `livekit_realtime` rejects it.

## What unblocking a full merge would need (owner decision, not P3)

An owner decision on the single identity charset (drop `@` support in
video tokens, or widen the realtime signalling contract), a single TTL
floor, and a single token-issue return shape — then the two public
APIs could be merged behind one name with the other kept as a
compatibility shim. Until then, both modules stay, with this file as
the record of which is canonical for what.
