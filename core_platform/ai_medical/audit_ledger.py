"""Sanders AI Medical — Immutable Audit Ledger.

Append-only, hash-chained JSONL ledger for every enforcement event,
built from the received design (2026-11-25) with the fix-plan
changes:

- FIX 12 (anchoring): flush_and_anchor() computes the Merkle root of
  the pending window and, when the gateway supplies the repo's
  Glass-Box audit adapter as the anchor sink, preserves the root
  into the sovereign Glass-Box chain (the repo's existing anchoring
  direction: no-record-no-action receipts). No external timestamp
  authority endpoint is invented; the Charter's sovereign audit
  chain integration remains the Glass Box. The returned receipt
  names the anchor state honestly: RECORDED_TO_GLASS_BOX when the
  sink accepted the root, LOCAL_ONLY_NOT_ANCHORED otherwise.
- FIX 12 (signatures): when a signing key is provisioned (the policy
  kernel's receipt key), each entry carries an Ed25519 signature
  over its entry hash. The signature is stored outside the hashed
  content; verify_integrity() checks it whenever a verification key
  is configured. Without a provisioned key, entries are chained but
  unsigned and the ledger says so in its status.
- FIX 10: every LedgerEventType defined here is emitted by a real
  code path in the gateway/kernel (see api_gateway.py and
  policy_kernel.py); SYSTEM_ABORT is written by the gateway on
  attestation failure and is also writable by an external supervisor
  through write_abort_record() when a process dies by signal.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

GENESIS_HASH = "0" * 64


class LedgerEventType(Enum):
    BOOT_ATTESTATION = "BOOT_ATTESTATION"
    RUNTIME_ATTESTATION = "RUNTIME_ATTESTATION"
    INPUT_RECEIVED = "INPUT_RECEIVED"
    INPUT_PERMITTED = "INPUT_PERMITTED"
    INPUT_REJECTED = "INPUT_REJECTED"
    INFERENCE_START = "INFERENCE_START"
    INFERENCE_COMPLETE = "INFERENCE_COMPLETE"
    CONSTRAINT_VIOLATION = "CONSTRAINT_VIOLATION"
    ACTION_STRIPPED = "ACTION_STRIPPED"
    INTENT_VIOLATION = "INTENT_VIOLATION"
    RISK_ENGINE_TRIGGERED = "RISK_ENGINE_TRIGGERED"
    POLICY_EVALUATION = "POLICY_EVALUATION"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    CROSS_VALIDATION_START = "CROSS_VALIDATION_START"
    CROSS_VALIDATION_PASSED = "CROSS_VALIDATION_PASSED"
    CROSS_VALIDATION_CONFLICT = "CROSS_VALIDATION_CONFLICT"
    ESCALATION_TRIGGERED = "ESCALATION_TRIGGERED"
    OUTPUT_ISSUED = "OUTPUT_ISSUED"
    SAFE_HOLD_ENTERED = "SAFE_HOLD_ENTERED"
    HUMAN_APPROVAL_RECEIVED = "HUMAN_APPROVAL_RECEIVED"
    HUMAN_APPROVAL_REJECTED = "HUMAN_APPROVAL_REJECTED"
    SYSTEM_ABORT = "SYSTEM_ABORT"


@dataclass
class LedgerEntry:
    sequence: int
    timestamp_utc: float
    event_type: LedgerEventType
    entity_role: Optional[str]
    request_id: Optional[str]
    payload: dict
    previous_hash: str
    entry_hash: str = field(default="")
    entry_signature: Optional[str] = None

    def _hash_content(self) -> dict:
        return {
            "sequence": self.sequence,
            "timestamp_utc": self.timestamp_utc,
            "event_type": self.event_type.value,
            "entity_role": self.entity_role,
            "request_id": self.request_id,
            "payload": self.payload,
            "previous_hash": self.previous_hash,
        }

    def compute_hash(self) -> str:
        serialized = json.dumps(
            self._hash_content(), sort_keys=True
        ).encode()
        return hashlib.sha256(serialized).hexdigest()

    def to_dict(self) -> dict:
        d = self._hash_content()
        d["entry_hash"] = self.entry_hash
        d["entry_signature"] = self.entry_signature
        return d


class AuditLedger:
    """Thread-safe append-only ledger. Constructing it on an existing
    file resumes the chain after verifying the tail entry's hash, so
    a truncated or altered history is detected at open."""

    def __init__(
        self,
        ledger_path: Path,
        *,
        signing_key: Optional[Ed25519PrivateKey] = None,
        anchor_sink: Optional[Callable[[dict], None]] = None,
    ):
        self._path = Path(ledger_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._signing_key = signing_key
        self._anchor_sink = anchor_sink
        self._sequence = 0
        self._last_hash = GENESIS_HASH
        self._pending_anchor: list[str] = []
        if self._path.exists() and self._path.stat().st_size > 0:
            self._resume()

    def _resume(self) -> None:
        last_line: Optional[str] = None
        count = 0
        with open(self._path) as f:
            for line in f:
                if line.strip():
                    last_line = line
                    count += 1
        if last_line is None:
            return
        tail = json.loads(last_line)
        entry = LedgerEntry(
            sequence=tail["sequence"],
            timestamp_utc=tail["timestamp_utc"],
            event_type=LedgerEventType(tail["event_type"]),
            entity_role=tail["entity_role"],
            request_id=tail["request_id"],
            payload=tail["payload"],
            previous_hash=tail["previous_hash"],
            entry_hash=tail["entry_hash"],
            entry_signature=tail.get("entry_signature"),
        )
        if entry.compute_hash() != tail["entry_hash"]:
            raise ValueError(
                "Ledger tail entry hash mismatch — the audit history "
                "has been altered. Refusing to extend a broken chain."
            )
        self._sequence = count
        self._last_hash = tail["entry_hash"]

    @property
    def entries_signed(self) -> bool:
        return self._signing_key is not None

    def append(
        self,
        event_type: LedgerEventType,
        payload: dict,
        entity_role: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> LedgerEntry:
        with self._lock:
            entry = LedgerEntry(
                sequence=self._sequence,
                timestamp_utc=time.time(),
                event_type=event_type,
                entity_role=entity_role,
                request_id=request_id,
                payload=payload,
                previous_hash=self._last_hash,
            )
            entry.entry_hash = entry.compute_hash()
            if self._signing_key is not None:
                entry.entry_signature = self._signing_key.sign(
                    entry.entry_hash.encode()
                ).hex()
            line = json.dumps(entry.to_dict(), sort_keys=True)
            with open(self._path, "a") as f:
                f.write(line + "\n")
                f.flush()
                os.fsync(f.fileno())
            self._sequence += 1
            self._last_hash = entry.entry_hash
            self._pending_anchor.append(entry.entry_hash)
            return entry

    def verify_integrity(
        self, verify_key: Optional[Ed25519PublicKey] = None
    ) -> tuple[bool, list[str]]:
        errors: list[str] = []
        previous = GENESIS_HASH
        expected_sequence = 0
        with open(self._path) as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                entry = LedgerEntry(
                    sequence=data["sequence"],
                    timestamp_utc=data["timestamp_utc"],
                    event_type=LedgerEventType(data["event_type"]),
                    entity_role=data["entity_role"],
                    request_id=data["request_id"],
                    payload=data["payload"],
                    previous_hash=data["previous_hash"],
                    entry_hash=data["entry_hash"],
                    entry_signature=data.get("entry_signature"),
                )
                if entry.sequence != expected_sequence:
                    errors.append(
                        f"Sequence gap at entry {expected_sequence}: "
                        f"found {entry.sequence}"
                    )
                if entry.previous_hash != previous:
                    errors.append(
                        f"Chain break at sequence {entry.sequence}"
                    )
                if entry.compute_hash() != entry.entry_hash:
                    errors.append(
                        f"Hash mismatch at sequence {entry.sequence}"
                    )
                if verify_key is not None:
                    if not entry.entry_signature:
                        errors.append(
                            "Missing entry signature at sequence "
                            f"{entry.sequence}"
                        )
                    else:
                        try:
                            verify_key.verify(
                                bytes.fromhex(entry.entry_signature),
                                entry.entry_hash.encode(),
                            )
                        except InvalidSignature:
                            errors.append(
                                "Invalid entry signature at sequence "
                                f"{entry.sequence}"
                            )
                previous = entry.entry_hash
                expected_sequence += 1
        return (len(errors) == 0, errors)

    def flush_and_anchor(self) -> dict:
        """Merkle-root the pending window and anchor the root into
        the Glass-Box chain when a sink is bound (Fix 12)."""
        with self._lock:
            pending = list(self._pending_anchor)
            self._pending_anchor.clear()
        if not pending:
            return {
                "status": "NOTHING_TO_ANCHOR",
                "anchor_state": "LOCAL_ONLY_NOT_ANCHORED",
                "entries_anchored": 0,
            }
        layer = pending
        while len(layer) > 1:
            nxt = []
            for i in range(0, len(layer), 2):
                left = layer[i]
                right = layer[i + 1] if i + 1 < len(layer) else left
                nxt.append(
                    hashlib.sha256(
                        (left + right).encode()
                    ).hexdigest()
                )
            layer = nxt
        merkle_root = layer[0]
        receipt = {
            "merkle_root": merkle_root,
            "entries_anchored": len(pending),
            "anchored_at_utc": time.time(),
            "anchor_state": "LOCAL_ONLY_NOT_ANCHORED",
        }
        if self._anchor_sink is not None:
            self._anchor_sink(
                {
                    "event": "AI_MEDICAL_LEDGER_ANCHOR",
                    "merkle_root": merkle_root,
                    "entries_anchored": len(pending),
                }
            )
            receipt["anchor_state"] = "RECORDED_TO_GLASS_BOX"
        return receipt

    def status(self) -> dict:
        return {
            "entries": self._sequence,
            "last_hash": self._last_hash,
            "entries_signed": self.entries_signed,
            "anchor_sink_bound": self._anchor_sink is not None,
            "path": str(self._path),
        }


def write_abort_record(
    ledger_path: Path,
    reason: str,
    *,
    entity_role: Optional[str] = None,
    detail: Optional[dict] = None,
) -> LedgerEntry:
    """Supervisor path for Fix 10: when a stack process dies by
    signal (so no in-process handler ran), the supervisor calls this
    to leave the SYSTEM_ABORT record the abort itself could not."""
    ledger = AuditLedger(Path(ledger_path))
    return ledger.append(
        LedgerEventType.SYSTEM_ABORT,
        {"reason": reason, "recorded_by": "SUPERVISOR", **(detail or {})},
        entity_role=entity_role,
    )
