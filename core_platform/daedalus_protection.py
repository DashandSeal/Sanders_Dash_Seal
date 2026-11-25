"""Daedalus protection layer (founder-directed build, 2026-11-25).

Founder direction (2026-11-25, verbatim): "He's got to be tamper
proof quantum encryption protection protocols with the full Sanders
labyrinth shield 🛡️ and the RTSA minotaur patoling the labyrinth
shield itself." Founder affirmation the same day: "The Sanders
labyrinth shield 🛡️ itself is a RTSA too."

Identity discipline (platform-to-platform, never absorption): the
Sanders Labyrinth Shield is a full RTSA platform in its own right
(registry id ``sanders_labyrinth_shield``; its own modules are the
repository-root ``labyrinth_shield.py`` and
``core_platform/labyrinth_shield_service.py``), and the RTSA
Minotaur is one platform (registry id ``minotaur_sentinel``, founder
ruling D-N8; its Sentinel core is the repository-root
``minotaur_sentinel.py`` and its service is
``core_platform/minotaur_service.py``). This module wires Daedalus
*inside* the Shield's protection and *under* the Minotaur's patrol
by calling those platforms' own modules through their own APIs. It
does not modify, copy, rename, or absorb either platform: the
Shield's module, the Minotaur's module, and both registry entries
remain intact and separately accounted. What lives here is only the
binding, the patrol state Daedalus's protection keeps, and the
quantum protection protocol layer Daedalus's artifacts use.

What the binding does:

1. **Shield evaluation gate.** Every operation the native core
   performs through its transport face, and every teaching or
   outcome write, is first evaluated by the Shield platform's own
   ``LabyrinthShield.evaluate_packet(source, payload)``. A payload
   the Shield rejects is refused before any reasoning or learning
   happens (fail closed): :class:`ShieldBlockedError` is raised and
   nothing is computed or stored.

2. **Minotaur patrol.** The Minotaur Sentinel core's own SHA-256
   hashing (``MinotaurSentinel.compute_target_hash``) and its own
   patrol cycle run over Daedalus: baselines are pinned over the
   native core module, this protection module, the L15 capability
   registry, the learned-knowledge store module, the engine, the
   platform registry, and the Shield's and Minotaur's own modules —
   the Minotaur patrolling the Labyrinth Shield itself is part of
   the cycle, through the Sentinel's own ``PROTECTED_TARGETS`` and
   through the Shield module's presence in Daedalus's patrol set,
   cross-checked against the Shield's own ``compute_shield_hash()``
   self-audit. The learned-knowledge store's database is patrolled
   by content: every stored record's evidence hash is recomputed
   with the store's own ``evidence_hash`` and its record id
   re-derived, so a tampered learned record is detected even though
   legitimate learning changes the file. A patrol runs on a defined
   cycle (:data:`PATROL_INTERVAL_SECONDS`) and on demand; every
   patrol writes a signed, hash-chained Glass-Box record to the
   patrol ledger. Any baseline mismatch or invalid learned record
   is a tamper event: it is named in the patrol record, and the
   operation gate (:meth:`DaedalusProtection.require_intact`)
   refuses — Daedalus does not reason over a compromised perimeter.

3. **Tamper-evident artifacts.** Daedalus's artifacts — generated
   responses, learned records, signed evidence digests, patrol
   reports — are entered into one append-only hash-chained ledger
   (each entry's hash is SHA3-256 over the previous entry's hash
   and the entry's canonical content). Altering any entered byte
   breaks the chain at that entry and verification names it. The
   chain head is anchored by hash-based signatures (below), so the
   ledger's state is itself signed, not merely hashed.

4. **Quantum protection protocols — implemented scope.** The
   signature layer is a hash-based scheme in the post-quantum
   family: WOTS+ one-time signatures (Winternitz chains over
   SHA-256 with per-step masks, the construction standardized in
   RFC 8391 and used by XMSS / SLH-DSA) under a SHA-256 Merkle
   tree, with key material derived from one seed by SHAKE-256 and
   digests by SHA-3 — pure Python standard library, no external
   package, no network. Hash-based signatures rest only on hash
   function security and are the quantum-resistant signature family
   behind SLH-DSA (FIPS 205). One-time discipline is enforced: a
   leaf index that has signed once never signs again (reuse would
   weaken WOTS+), and exhaustion fails closed.

   **Declared, not implemented, in this layer:** ML-KEM key
   exchange. ML-KEM is not in the Python standard library, and this
   layer imports nothing outside it. Examination record: the repo
   carries ``core_platform/pqc.py``, a genuine ML-KEM-768
   (FIPS 203) + ML-DSA-65 (FIPS 204) implementation backed by the
   third-party ``cryptography`` library (minimum verified version
   50.0.2, OpenSSL >= 3.5); it is fail-closed and honestly reported,
   but it is not usable from this layer — the native core's
   standard-library-only law excludes a third-party dependency
   from Daedalus's protection path, and in the verification
   environment for this build the ``cryptography`` library was not
   installed at all (its own ``status()`` reported
   ``available: False``). That module is unattributed (it is not
   HYDRA-Q's; HYDRA-Q remains the post-quantum readiness register
   and performs no cryptography), and attribution is an owner
   decision this build does not make. Key exchange therefore stays
   a declared target here, and nothing in this module claims it.

State: protection state lives under ``data/`` at the repository
root (the codebase's runtime-state convention; created on first
use, never committed): a state file (baselines, signing identity,
used one-time indices, chain head) and the hash-chained ledger.
The signing seed comes from the ``DAEDALUS_PROTECTION_SEED_HEX``
environment variable when the owner supplies it through the secure
carrier path; otherwise a seed is generated once and kept in the
state directory (file mode 0600 attempted) — the seed source is
reported in :meth:`DaedalusProtection.status`, never hidden.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Mapping

__all__ = [
    "PATROL_INTERVAL_SECONDS",
    "PATROL_TARGETS",
    "DaedalusProtection",
    "DaedalusTamperError",
    "HashSignatureScheme",
    "ProtectionError",
    "ShieldBlockedError",
    "canonical_bytes",
]

# The defined patrol cycle: a full patrol (with its signed ledger
# record) runs at most this often from the operation path, and any
# caller may run one on demand at any time.
PATROL_INTERVAL_SECONDS = 300

# Daedalus's patrol set, as repository-relative paths: his own core
# files, the registry he reasons over, and the two protecting
# platforms' own modules — the Shield he operates inside and the
# Minotaur that patrols, each present under its own identity.
PATROL_TARGETS = (
    "core_platform/daedalus_native_core.py",
    "core_platform/daedalus_protection.py",
    "core_platform/daedalus_l15_capabilities.py",
    "core_platform/daedalus_knowledge_store.py",
    "core_platform/daedalus_engine.py",
    "core_platform/ai_platform_links.json",
    "labyrinth_shield.py",
    "minotaur_sentinel.py",
)

SHIELD_PLATFORM_ID = "sanders_labyrinth_shield"
SHIELD_MODULE = "labyrinth_shield.py"
MINOTAUR_PLATFORM_ID = "minotaur_sentinel"
MINOTAUR_MODULE = "minotaur_sentinel.py"

_SEED_ENV = "DAEDALUS_PROTECTION_SEED_HEX"
_STATE_FILE = "daedalus_protection_state.json"
_LEDGER_FILE = "daedalus_protection_ledger.jsonl"
_SEED_FILE = "daedalus_protection_seed.hex"
_GENESIS = "0" * 64


class ProtectionError(RuntimeError):
    """Base for protection-layer refusals (all fail closed)."""


class ShieldBlockedError(ProtectionError):
    """The Labyrinth Shield evaluated the payload and rejected it."""


class DaedalusTamperError(ProtectionError):
    """A patrol or integrity check found a protected artifact altered."""


def canonical_bytes(record: Mapping) -> bytes:
    """Deterministic JSON bytes for a record (sorted keys, tight
    separators) — the same canonical form the codebase's evidence
    hashes use, so a digest here means the same thing everywhere."""
    return json.dumps(
        dict(record), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _iso(epoch: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def _load_module(name: str, path: Path):
    """Load one of the protecting platforms' own modules by path.

    The Shield and the Minotaur live at the repository root, outside
    the ``core_platform`` package; loading by path calls their real
    code without moving or copying it.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ProtectionError("Cannot load platform module at " + str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ----------------------------------------------------------------------
# Hash-based signatures: WOTS+ under a Merkle tree (pure stdlib)
# ----------------------------------------------------------------------

_WOTS_W = 16            # Winternitz parameter: digits are base-16.
_WOTS_LEN1 = 64         # digits in a 32-byte digest at w=16.
_WOTS_LEN2 = 3          # checksum digits (64*15 = 960 < 16**3).
_WOTS_LEN = _WOTS_LEN1 + _WOTS_LEN2
_TREE_HEIGHT = 5        # 32 one-time keypairs per seed epoch.
_LEAVES = 1 << _TREE_HEIGHT


def _wots_digits(digest: bytes) -> list[int]:
    digits: list[int] = []
    for byte in digest:
        digits.append(byte >> 4)
        digits.append(byte & 0x0F)
    checksum = sum((_WOTS_W - 1) - d for d in digits)
    for shift in (8, 4, 0):
        digits.append((checksum >> shift) & 0x0F)
    return digits


class HashSignatureScheme:
    """WOTS+ one-time signatures under a SHA-256 Merkle tree.

    Keys are derived deterministically from one 32-byte seed:
    per-leaf secret elements and the public seed come from
    SHAKE-256 domain-separated derivation, each public element is
    its secret element pushed through a masked Winternitz chain
    (RFC 8391 construction), each leaf of the Merkle tree is the
    SHA-256 of one leaf's public elements, and the tree root is
    the public identity signatures are verified against.
    """

    def __init__(self, seed: bytes) -> None:
        if not isinstance(seed, (bytes, bytearray)) or len(seed) != 32:
            raise ValueError("Hash signature seed must be 32 bytes")
        self._seed = bytes(seed)
        self._pub_seed = hashlib.shake_256(
            self._seed + b"|daedalus-wots-pubseed|"
        ).digest(32)
        self._leaf_hashes: list[bytes] = []
        self._leaf_pubkeys: list[list[bytes]] = []
        for leaf in range(_LEAVES):
            pubkey = [self._chain(self._secret(leaf, i), leaf, i, 0, _WOTS_W - 1)
                      for i in range(_WOTS_LEN)]
            self._leaf_pubkeys.append(pubkey)
            self._leaf_hashes.append(
                hashlib.sha256(b"".join(pubkey)).digest()
            )
        self._tree: list[list[bytes]] = [self._leaf_hashes]
        while len(self._tree[-1]) > 1:
            level = self._tree[-1]
            self._tree.append([
                hashlib.sha256(level[i] + level[i + 1]).digest()
                for i in range(0, len(level), 2)
            ])
        self.root = self._tree[-1][0]

    # -- primitives -------------------------------------------------

    def _secret(self, leaf: int, chain_index: int) -> bytes:
        return hashlib.shake_256(
            self._seed + b"|daedalus-wots-sk|"
            + leaf.to_bytes(4, "big") + chain_index.to_bytes(2, "big")
        ).digest(32)

    def _chain(self, x: bytes, leaf: int, chain_index: int,
               start: int, steps: int) -> bytes:
        adrs = (
            leaf.to_bytes(4, "big") + chain_index.to_bytes(4, "big")
            + (0).to_bytes(4, "big")
        )
        for step in range(start, start + steps):
            mask = hashlib.sha256(
                self._pub_seed + adrs + step.to_bytes(4, "big")
            ).digest()
            x = hashlib.sha256(
                bytes(a ^ b for a, b in zip(x, mask))
            ).digest()
        return x

    def _auth_path(self, leaf: int) -> list[bytes]:
        path = []
        index = leaf
        for level in self._tree[:-1]:
            sibling = index ^ 1
            path.append(level[sibling])
            index //= 2
        return path

    # -- signing / verification --------------------------------------

    def sign(self, message: bytes, leaf_index: int) -> dict:
        """Sign ``message`` with one-time leaf ``leaf_index``.

        One-time discipline is the caller's state to keep (see
        :class:`DaedalusProtection`, which never reuses a leaf);
        this scheme signs with the leaf it is given.
        """
        if not 0 <= leaf_index < _LEAVES:
            raise ValueError("Leaf index out of range")
        digest = hashlib.sha256(message).digest()
        digits = _wots_digits(digest)
        elements = [
            self._chain(self._secret(leaf_index, i), leaf_index, i, 0, digits[i])
            for i in range(_WOTS_LEN)
        ]
        return {
            "scheme": "WOTS+ (SHA-256, w=16) under SHA-256 Merkle tree",
            "leaf_index": leaf_index,
            "pub_seed": self._pub_seed.hex(),
            "root": self.root.hex(),
            "elements": [e.hex() for e in elements],
            "auth_path": [p.hex() for p in self._auth_path(leaf_index)],
        }

    @staticmethod
    def verify(message: bytes, signature: Mapping,
               trusted_root: str | None = None) -> bool:
        """Verify a WOTS+ signature. ``False`` for any forgery.

        The public key is recovered from the signature by completing
        each Winternitz chain, hashed to the leaf, and walked up the
        authentication path to the Merkle root, which must equal the
        signature's root and, when supplied, ``trusted_root``.
        """
        try:
            leaf_index = int(signature["leaf_index"])
            pub_seed = bytes.fromhex(signature["pub_seed"])
            elements = [bytes.fromhex(e) for e in signature["elements"]]
            auth_path = [bytes.fromhex(p) for p in signature["auth_path"]]
            root_hex = str(signature["root"])
        except (KeyError, TypeError, ValueError):
            return False
        if len(elements) != _WOTS_LEN or len(auth_path) != _TREE_HEIGHT:
            return False
        if trusted_root is not None and root_hex != trusted_root:
            return False
        scheme_pub_seed = pub_seed

        def chain(x: bytes, chain_index: int, start: int, steps: int) -> bytes:
            adrs = (
                leaf_index.to_bytes(4, "big")
                + chain_index.to_bytes(4, "big") + (0).to_bytes(4, "big")
            )
            for step in range(start, start + steps):
                mask = hashlib.sha256(
                    scheme_pub_seed + adrs + step.to_bytes(4, "big")
                ).digest()
                x = hashlib.sha256(bytes(a ^ b for a, b in zip(x, mask))).digest()
            return x

        digest = hashlib.sha256(message).digest()
        digits = _wots_digits(digest)
        pubkey = [
            chain(elements[i], i, digits[i], (_WOTS_W - 1) - digits[i])
            for i in range(_WOTS_LEN)
        ]
        node = hashlib.sha256(b"".join(pubkey)).digest()
        index = leaf_index
        for sibling in auth_path:
            if index % 2 == 0:
                node = hashlib.sha256(node + sibling).digest()
            else:
                node = hashlib.sha256(sibling + node).digest()
            index //= 2
        return node.hex() == root_hex


# ----------------------------------------------------------------------
# The binding: Shield gate + Minotaur patrol + artifact chain
# ----------------------------------------------------------------------


class DaedalusProtection:
    """Daedalus's protection, wired platform-to-platform.

    Constructed over a repository root (where the Shield's and
    Minotaur's own modules and Daedalus's own files live) and a
    state directory for patrol baselines and the chained ledger.
    Both default from this module's own location: the repository
    root is the parent of ``core_platform`` and the state directory
    is ``data/`` beneath it.
    """

    def __init__(
        self,
        repo_root: str | Path | None = None,
        state_dir: str | Path | None = None,
        *,
        seed: bytes | None = None,
    ) -> None:
        self.repo_root = (
            Path(repo_root) if repo_root is not None
            else Path(__file__).resolve().parent.parent
        )
        self.state_dir = (
            Path(state_dir) if state_dir is not None
            else self.repo_root / "data"
        )
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._state_path = self.state_dir / _STATE_FILE
        self._ledger_path = self.state_dir / _LEDGER_FILE

        # The protecting platforms, loaded from their own modules.
        shield_module = _load_module(
            "labyrinth_shield_platform", self.repo_root / SHIELD_MODULE
        )
        self._shield = shield_module.LabyrinthShield()
        self.shield_id = self._shield.shield_id
        minotaur_module = _load_module(
            "minotaur_sentinel_platform", self.repo_root / MINOTAUR_MODULE
        )
        self._minotaur_class = minotaur_module.MinotaurSentinel
        # The Minotaur pins its own baselines at construction,
        # resolved against the repository root (its targets are
        # repository-relative), and its patrol cycle then detects
        # drift from those baselines for the rest of this process.
        self._minotaur = self._construct_minotaur()
        self.sentinel_id = self._minotaur.sentinel_id

        self._seed, self._seed_source = self._resolve_seed(seed)
        self._scheme = HashSignatureScheme(self._seed)
        self._state = self._load_state()

    # -- construction helpers ----------------------------------------

    def _construct_minotaur(self):
        cwd = os.getcwd()
        os.chdir(self.repo_root)
        try:
            return self._minotaur_class()
        finally:
            os.chdir(cwd)

    def _resolve_seed(self, seed: bytes | None) -> tuple[bytes, str]:
        if seed is not None:
            return bytes(seed), "supplied_to_constructor"
        env_hex = os.environ.get(_SEED_ENV)
        if env_hex:
            try:
                raw = bytes.fromhex(env_hex.strip())
            except ValueError:
                raw = b""
            if len(raw) == 32:
                return raw, "environment:" + _SEED_ENV
        seed_path = self.state_dir / _SEED_FILE
        if seed_path.exists():
            try:
                raw = bytes.fromhex(seed_path.read_text(encoding="utf-8").strip())
                if len(raw) == 32:
                    return raw, "state_directory_seed_file"
            except (OSError, ValueError):
                pass
        raw = os.urandom(32)
        try:
            seed_path.write_text(raw.hex(), encoding="utf-8")
            os.chmod(seed_path, 0o600)
        except OSError:
            return raw, "ephemeral_state_directory_unwritable"
        return raw, "generated_into_state_directory"

    def _load_state(self) -> dict:
        if self._state_path.exists():
            try:
                state = json.loads(self._state_path.read_text(encoding="utf-8"))
                if state.get("merkle_root") != self._scheme.root.hex():
                    # A different signing seed opens a new one-time
                    # epoch: baselines and the ledger chain carry
                    # over (they are content, not keys); only the
                    # used-leaf set resets, under the new root.
                    state["merkle_root"] = self._scheme.root.hex()
                    state["seed_source"] = self._seed_source
                    state["used_leaf_indices"] = []
                return state
            except (OSError, ValueError):
                pass
        return {
            "version": 1,
            "merkle_root": self._scheme.root.hex(),
            "seed_source": self._seed_source,
            "used_leaf_indices": [],
            "baselines": {},
            "baseline_pinned_at": None,
            "chain_head": _GENESIS,
            "chain_length": 0,
            "last_patrol": None,
            "last_patrol_epoch": 0.0,
        }

    def _save_state(self) -> None:
        tmp = self._state_path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(self._state, indent=1, sort_keys=True), encoding="utf-8"
        )
        os.replace(tmp, self._state_path)

    # -- Shield gate ---------------------------------------------------

    def shield_hash(self) -> str:
        """The Shield platform's own self-audit hash of its module."""
        return self._shield.compute_shield_hash()

    def shield_evaluate(self, source: str, payload: str) -> bool:
        """Evaluate one payload through the Shield platform itself."""
        return bool(self._shield.evaluate_packet(source, payload))

    def require_shield_admission(self, source: str, payload: str) -> dict:
        """Gate one operation through the Labyrinth Shield.

        Returns the admission record on success; raises
        :class:`ShieldBlockedError` when the Shield rejects the
        payload — the operation does not proceed (fail closed).
        """
        admitted = self.shield_evaluate(source, payload)
        record = {
            "shield_platform": SHIELD_PLATFORM_ID,
            "shield_id": self.shield_id,
            "source": source,
            "payload_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
            "admitted": admitted,
        }
        if not admitted:
            raise ShieldBlockedError(
                "The Sanders Labyrinth Shield (" + self.shield_id
                + ") rejected the payload from source " + repr(source)
                + "; the operation is refused."
            )
        return record

    # -- Hash-chained ledger -------------------------------------------

    def _append_ledger(self, kind: str, payload: Mapping, *,
                       sign: bool = False) -> dict:
        index = int(self._state["chain_length"])
        prev = str(self._state["chain_head"])
        body = {
            "index": index,
            "kind": kind,
            "at": _iso(time.time()),
            "payload": dict(payload),
        }
        digest = hashlib.sha3_256(
            bytes.fromhex(prev) + canonical_bytes(body)
        ).hexdigest()
        record = {**body, "prev": prev, "hash": digest}
        if sign:
            record["signature"] = self._sign(bytes.fromhex(digest))
        with open(self._ledger_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
        self._state["chain_head"] = digest
        self._state["chain_length"] = index + 1
        self._save_state()
        return record

    def _sign(self, message: bytes) -> dict:
        used = set(self._state["used_leaf_indices"])
        for leaf in range(_LEAVES):
            if leaf not in used:
                break
        else:
            raise ProtectionError(
                "Hash-signature one-time key pool exhausted for this "
                "seed epoch; refusing to reuse a one-time key. The "
                "owner rotates the seed to open a new epoch."
            )
        signature = self._scheme.sign(message, leaf)
        self._state["used_leaf_indices"] = sorted(used | {leaf})
        self._save_state()
        return signature

    def sign_message(self, message: bytes) -> dict:
        """Sign bytes with the next unused one-time key."""
        return self._sign(message)

    def verify_message(self, message: bytes, signature: Mapping) -> bool:
        """Verify a signature against this protection's Merkle root."""
        return HashSignatureScheme.verify(
            message, signature, trusted_root=self._scheme.root.hex()
        )

    def verify_chain(self) -> dict:
        """Walk the protection ledger and verify every link.

        Each record's hash is recomputed from the previous record's
        hash and the record's canonical content; signed records also
        have their signatures verified. Returns the first break, by
        index, when the chain does not verify.
        """
        records = []
        if self._ledger_path.exists():
            for line in self._ledger_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    records.append(json.loads(line))
        prev = _GENESIS
        for expected_index, record in enumerate(records):
            body = {
                "index": record.get("index"),
                "kind": record.get("kind"),
                "at": record.get("at"),
                "payload": record.get("payload"),
            }
            digest = hashlib.sha3_256(
                bytes.fromhex(prev) + canonical_bytes(body)
            ).hexdigest()
            if record.get("index") != expected_index or record.get("prev") != prev:
                return {
                    "valid": False, "records": len(records),
                    "broken_at": expected_index,
                    "reason": "chain linkage broken (index/prev mismatch)",
                }
            if digest != record.get("hash"):
                return {
                    "valid": False, "records": len(records),
                    "broken_at": expected_index,
                    "reason": "record content altered (hash mismatch)",
                }
            signature = record.get("signature")
            if signature is not None and not HashSignatureScheme.verify(
                bytes.fromhex(digest), signature,
            ):
                return {
                    "valid": False, "records": len(records),
                    "broken_at": expected_index,
                    "reason": "record signature does not verify",
                }
            prev = digest
        return {
            "valid": True, "records": len(records), "chain_head": prev,
            "reason": None,
        }

    # -- Artifact sealing ------------------------------------------------

    def seal_artifact(self, kind: str, content: bytes, *,
                      meta: Mapping | None = None) -> dict:
        """Enter one artifact into the hash-chained ledger.

        The entry binds the artifact's SHA3-256 digest to the chain;
        any later alteration of the artifact or of the entry is
        detectable by :meth:`verify_artifact` / :meth:`verify_chain`.
        """
        entry = self._append_ledger("artifact", {
            "artifact_kind": kind,
            "digest_sha3_256": hashlib.sha3_256(content).hexdigest(),
            "meta": dict(meta or {}),
        })
        return entry

    def verify_artifact(self, entry: Mapping, content: bytes) -> bool:
        """True only if ``content`` is exactly what ``entry`` sealed."""
        payload = entry.get("payload") or {}
        return (
            payload.get("digest_sha3_256")
            == hashlib.sha3_256(content).hexdigest()
        )

    def anchor_chain(self) -> dict:
        """Sign the current chain head, anchoring the ledger state."""
        head = str(self._state["chain_head"])
        return self._append_ledger("chain_anchor", {
            "anchored_head": head,
            "anchored_length": int(self._state["chain_length"]),
        }, sign=True)

    # -- Signed executable measurement ------------------------------------

    def measure_executable(self, relpath: str) -> dict:
        """A signed measurement of one executable module's bytes.

        The measurement is the Minotaur's own SHA-256 of the file,
        signed with a hash-based one-time signature: a signed
        statement of exactly which bytes the module held.
        """
        target = self.repo_root / relpath
        digest = self._minotaur.compute_target_hash(str(target))
        if digest == "FILE_MISSING":
            raise ProtectionError("Cannot measure missing file: " + relpath)
        body = {"path": relpath, "sha256": digest}
        signature = self._sign(canonical_bytes(body))
        return {**body, "signature": signature}

    def verify_measurement(self, measurement: Mapping) -> bool:
        """Verify a signed measurement and the file's current bytes."""
        body = {
            "path": measurement.get("path"),
            "sha256": measurement.get("sha256"),
        }
        signature = measurement.get("signature")
        if signature is None or not self.verify_message(
            canonical_bytes(body), signature
        ):
            return False
        target = self.repo_root / str(measurement.get("path"))
        return self._minotaur.compute_target_hash(str(target)) == body["sha256"]

    # -- Minotaur patrol ---------------------------------------------------

    def _hash_target(self, relpath: str) -> str:
        return self._minotaur.compute_target_hash(str(self.repo_root / relpath))

    def pin_baselines(self) -> dict:
        """Pin SHA-256 baselines over Daedalus's patrol set.

        Recorded as a signed ledger entry: the baseline set itself
        is a protected artifact.
        """
        baselines = {rel: self._hash_target(rel) for rel in PATROL_TARGETS}
        self._state["baselines"] = baselines
        self._state["baseline_pinned_at"] = _iso(time.time())
        self._save_state()
        return self._append_ledger("baselines_pinned", {
            "targets": baselines,
            "pinned_by": self.sentinel_id,
        }, sign=True)

    def verify_knowledge_store(self, db_path: str | Path | None = None) -> dict:
        """Content patrol of the learned-knowledge store.

        Legitimate learning changes the store file, so the patrol
        verifies content instead of bytes: every record's evidence
        hash is recomputed with the store's own ``evidence_hash``
        and its record id re-derived. A record whose content was
        altered after the fact fails its own evidence hash and is
        named here.
        """
        store_module = _load_module(
            "daedalus_knowledge_store_patrol",
            self.repo_root / "core_platform" / "daedalus_knowledge_store.py",
        )
        path = Path(db_path) if db_path is not None else store_module.default_store_path()
        if not path.exists():
            return {"present": False, "path": str(path), "valid": True,
                    "learned_records": 0, "outcome_records": 0, "invalid": []}
        if path.stat().st_size == 0:
            return {"present": True, "path": str(path), "valid": True,
                    "learned_records": 0, "outcome_records": 0, "invalid": []}
        invalid: list[str] = []
        counts = {"learned_records": 0, "outcome_records": 0}
        try:
            conn = sqlite3.connect("file:" + str(path) + "?mode=ro", uri=True)
            try:
                learned = conn.execute(
                    "SELECT record_id, kind, subject, predicate, object,"
                    " source, note, learned_at, learned_at_iso,"
                    " evidence_hash FROM learned_records ORDER BY rowid"
                ).fetchall()
                outcomes = conn.execute(
                    "SELECT record_id, component, outcome, reason, source,"
                    " recorded_at, recorded_at_iso, evidence_hash"
                    " FROM outcome_records ORDER BY rowid"
                ).fetchall()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            return {"present": True, "path": str(path), "valid": False,
                    "learned_records": 0, "outcome_records": 0,
                    "invalid": ["store unreadable: " + type(exc).__name__]}
        for row in learned:
            counts["learned_records"] += 1
            content = {
                "kind": row[1], "subject": row[2], "predicate": row[3],
                "object": row[4], "source": row[5], "note": row[6],
                "learned_at_epoch": row[7], "learned_at_iso": row[8],
            }
            digest = store_module.evidence_hash(content)
            if digest != row[9] or row[0] != "learned-" + digest[:24]:
                invalid.append(row[0])
        for row in outcomes:
            counts["outcome_records"] += 1
            content = {
                "component": row[1], "outcome": row[2], "reason": row[3],
                "source": row[4], "recorded_at_epoch": row[5],
                "recorded_at_iso": row[6],
            }
            digest = store_module.evidence_hash(content)
            if digest != row[7] or row[0] != "outcome-" + digest[:24]:
                invalid.append(row[0])
        return {"present": True, "path": str(path), "valid": not invalid,
                **counts, "invalid": invalid}

    def _minotaur_cycle(self) -> list[str]:
        """The Minotaur's own patrol cycle, run from the repo root.

        Its targets resolve relative to the working directory; run
        it from the repository root so it patrols the real files it
        pinned at construction.
        """
        cwd = os.getcwd()
        os.chdir(self.repo_root)
        try:
            return list(self._minotaur.execute_patrol_cycle())
        finally:
            os.chdir(cwd)

    def patrol(self) -> dict:
        """Run one full Minotaur patrol cycle over Daedalus.

        Compares every patrolled file against its pinned baseline
        (pinning first when no baseline exists — the Minotaur's own
        initialize-on-start pattern), runs the Minotaur's own patrol
        cycle over its own targets (which include the Shield), and
        verifies the learned-knowledge store's content. The result
        is written to the ledger as a signed Glass-Box record.
        """
        if not self._state["baselines"]:
            self.pin_baselines()
        baselines = self._state["baselines"]
        altered: list[str] = []
        missing: list[str] = []
        for rel in PATROL_TARGETS:
            current = self._hash_target(rel)
            if current == "FILE_MISSING":
                missing.append(rel)
            elif current != baselines.get(rel):
                altered.append(rel)
        minotaur_anomalies = self._minotaur_cycle()
        # The Shield is inside Daedalus's perimeter: an anomaly the
        # Minotaur's own cycle reports against the Shield's module
        # is a tamper event for Daedalus too. (The Minotaur's other
        # targets are its own platform's wider patrol, reported in
        # the record but not Daedalus's gate.)
        shield_anomalies = [
            a for a in minotaur_anomalies
            if a.startswith(SHIELD_MODULE + ":")
        ]
        store = self.verify_knowledge_store()
        shield_self_hash = self.shield_hash()
        shield_file_hash = self._hash_target(SHIELD_MODULE)
        tamper = bool(
            altered or missing or shield_anomalies or not store["valid"]
        )
        report = {
            "patrol_by": self.sentinel_id,
            "patrol_platform": MINOTAUR_PLATFORM_ID,
            "status": "tamper_detected" if tamper else "clean",
            "altered": altered,
            "missing": missing,
            "minotaur_own_cycle_anomalies": minotaur_anomalies,
            "knowledge_store": store,
            "shield_self_hash": shield_self_hash,
            "shield_file_hash_matches_self_audit": (
                shield_self_hash == shield_file_hash
            ),
            "targets_checked": len(PATROL_TARGETS),
        }
        self._state["last_patrol"] = report
        self._state["last_patrol_epoch"] = time.time()
        self._save_state()
        self._append_ledger("patrol", report, sign=True)
        return report

    def patrol_if_due(self) -> dict | None:
        """Run the defined-cycle patrol when its interval has elapsed."""
        if time.time() - float(self._state["last_patrol_epoch"]) >= PATROL_INTERVAL_SECONDS:
            return self.patrol()
        return None

    def require_intact(self) -> dict:
        """The operation gate: refuse when the perimeter is altered.

        Verifies Daedalus's patrolled files against their baselines
        and the learned store's content integrity. Raises
        :class:`DaedalusTamperError` naming every altered target —
        the operation does not proceed (fail closed).
        """
        if not self._state["baselines"]:
            self.pin_baselines()
        baselines = self._state["baselines"]
        altered = [
            rel for rel in PATROL_TARGETS
            if self._hash_target(rel) != baselines.get(rel)
        ]
        shield_anomalies = [
            a for a in self._minotaur_cycle()
            if a.startswith(SHIELD_MODULE + ":")
        ]
        store = self.verify_knowledge_store()
        if altered or shield_anomalies or not store["valid"]:
            names = list(altered) + shield_anomalies
            if not store["valid"]:
                names.append(
                    "learned-knowledge store (invalid records: "
                    + ", ".join(store["invalid"]) + ")"
                )
            raise DaedalusTamperError(
                "Minotaur patrol integrity failure; altered: "
                + "; ".join(names)
                + ". The operation is refused (fail closed)."
            )
        return {"status": "intact", "targets_checked": len(PATROL_TARGETS),
                "knowledge_store": store}

    # -- Status -------------------------------------------------------------

    def status(self) -> dict:
        """This protection layer's own status, stated factually."""
        return {
            "binding": "platform_to_platform",
            "shield": {
                "platform_id": SHIELD_PLATFORM_ID,
                "module": SHIELD_MODULE,
                "shield_id": self.shield_id,
                "self_hash": self.shield_hash(),
                "role": "perimeter_evaluation_of_every_operation",
            },
            "patrol": {
                "platform_id": MINOTAUR_PLATFORM_ID,
                "module": MINOTAUR_MODULE,
                "sentinel_id": self.sentinel_id,
                "targets": list(PATROL_TARGETS),
                "interval_seconds": PATROL_INTERVAL_SECONDS,
                "baselines_pinned": bool(self._state["baselines"]),
                "last_patrol_status": (
                    (self._state["last_patrol"] or {}).get("status")
                ),
            },
            "quantum_protocols": {
                "signatures": (
                    "WOTS+ one-time signatures (SHA-256, w=16) under a "
                    "SHA-256 Merkle tree — hash-based post-quantum "
                    "family (RFC 8391 construction, as in XMSS / "
                    "SLH-DSA); implemented and proven in this layer"
                ),
                "digests": "SHA-3-256 (ledger chain), SHAKE-256 (key derivation)",
                "merkle_root": self._scheme.root.hex(),
                "one_time_leaves_total": _LEAVES,
                "one_time_leaves_used": len(self._state["used_leaf_indices"]),
                "seed_source": self._seed_source,
                "key_exchange": (
                    "ML-KEM: declared, not implemented in this layer "
                    "(not in the Python standard library; see module "
                    "docstring examination of core_platform/pqc.py)"
                ),
            },
            "ledger": {
                "records": int(self._state["chain_length"]),
                "chain_head": self._state["chain_head"],
            },
        }
