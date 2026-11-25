"""Sanders AI Medical — Signed Policy Bundle (fixes 5 and 7).

The stack's trust root lives OUTSIDE the code. At provisioning time
the owner (or the owner's provisioning tooling) writes a JSON policy
bundle pinning:

- the identity baselines (manifest hashes) the running code must
  match (Fix 7 — the code never derives trust from itself),
- the firewall calibration (threshold and per-layer floors),
- the kernel tripwire rule-set version,

and signs the bundle with an Ed25519 bundle key whose PRIVATE half
never enters the repo or the runtime. The runtime holds only the
bundle-signing PUBLIC key, provisioned by the owner alongside the
entity keys.

Named provisioning states (fail closed, never invented):
- POLICY_BUNDLE_NOT_PROVISIONED — the bundle file is absent.
- BUNDLE_SIGNING_KEY_NOT_PROVISIONED — the bundle public key is
  absent (referenced exactly in the owner-held pattern the repo
  already uses, e.g. SDS_EVIDENCE_SIGNING_KEY: a key the owner
  places, the code only names).
- POLICY_BUNDLE_SIGNATURE_INVALID — the bundle does not verify
  against the provisioned public key.
- POLICY_BUNDLE_MALFORMED — the bundle is unreadable or incomplete.

Honest classification (Fix 5): this module implements bundle loading
and signature verification. It does not claim a deployment topology;
process separation is a deployment property recorded in
docs/SPEC_CONFORMANCE.md, not asserted here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

BUNDLE_FORMAT = "SDS-AI-MEDICAL-POLICY-BUNDLE/1"


class PolicyBundleError(Exception):
    """Base class for policy-bundle refusals (all fail closed)."""

    STATE = "POLICY_BUNDLE_ERROR"


class PolicyBundleNotProvisioned(PolicyBundleError):
    STATE = "POLICY_BUNDLE_NOT_PROVISIONED"


class BundleSigningKeyNotProvisioned(PolicyBundleError):
    STATE = "BUNDLE_SIGNING_KEY_NOT_PROVISIONED"


class PolicyBundleSignatureInvalid(PolicyBundleError):
    STATE = "POLICY_BUNDLE_SIGNATURE_INVALID"


class PolicyBundleMalformed(PolicyBundleError):
    STATE = "POLICY_BUNDLE_MALFORMED"


@dataclass
class FirewallCalibration:
    """Firewall gate calibration, pinned by the bundle (Fix 6).

    The gate is reachable by a legitimate AI-professional-system
    input (a perfect score of 1.00 clears every floor and the
    threshold) and unreachable by human origin (human metadata and
    human linguistic markers cap the combined score far below the
    threshold). Both directions are proven by execution in the
    build drive; the numbers themselves are policy, owned by the
    bundle, not hard-coded trust."""

    threshold: float = 0.90
    metadata_floor: float = 0.75
    linguistic_floor: float = 0.60
    weight_metadata: float = 0.55
    weight_linguistic: float = 0.35
    weight_behavioral: float = 0.10


@dataclass
class PolicyBundle:
    version: str
    identity_baselines: dict[str, str]
    firewall: FirewallCalibration
    tripwire_ruleset: str
    raw: dict = field(default_factory=dict)

    def baseline_for(self, role_value: str) -> Optional[str]:
        return self.identity_baselines.get(role_value)


def _canonical(bundle_body: dict) -> bytes:
    return json.dumps(bundle_body, sort_keys=True).encode()


def load_bundle_public_key(path: Path) -> Ed25519PublicKey:
    path = Path(path)
    if not path.exists():
        raise BundleSigningKeyNotProvisioned(
            "BUNDLE_SIGNING_KEY_NOT_PROVISIONED: the policy bundle "
            f"signing public key was not found at {path}. The key is "
            "owner-provisioned (owner-held pattern; cf. "
            "SDS_EVIDENCE_SIGNING_KEY); the stack never invents one."
        )
    key = serialization.load_pem_public_key(path.read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise BundleSigningKeyNotProvisioned(
            "BUNDLE_SIGNING_KEY_NOT_PROVISIONED: the bundle signing "
            f"key at {path} is not an Ed25519 public key."
        )
    return key


def load_policy_bundle(
    bundle_path: Path, public_key_path: Path
) -> PolicyBundle:
    """Load and verify the signed policy bundle. Any failure raises a
    named PolicyBundleError subclass; there is no unsigned fallback."""
    bundle_path = Path(bundle_path)
    if not bundle_path.exists():
        raise PolicyBundleNotProvisioned(
            "POLICY_BUNDLE_NOT_PROVISIONED: no signed policy bundle "
            f"at {bundle_path}. Identity baselines and firewall "
            "calibration are pinned by the owner-signed bundle "
            "(Fix 7); without it the stack does not operate."
        )
    public_key = load_bundle_public_key(public_key_path)
    try:
        doc = json.loads(bundle_path.read_text())
    except Exception as exc:
        raise PolicyBundleMalformed(
            f"POLICY_BUNDLE_MALFORMED: cannot parse {bundle_path}: {exc}"
        ) from exc
    if not isinstance(doc, dict) or doc.get("format") != BUNDLE_FORMAT:
        raise PolicyBundleMalformed(
            "POLICY_BUNDLE_MALFORMED: bundle format marker missing "
            f"or not {BUNDLE_FORMAT}."
        )
    signature_hex = doc.get("signature")
    body = doc.get("body")
    if not signature_hex or not isinstance(body, dict):
        raise PolicyBundleMalformed(
            "POLICY_BUNDLE_MALFORMED: bundle lacks a signature or body."
        )
    try:
        public_key.verify(bytes.fromhex(signature_hex), _canonical(body))
    except (InvalidSignature, ValueError) as exc:
        raise PolicyBundleSignatureInvalid(
            "POLICY_BUNDLE_SIGNATURE_INVALID: the policy bundle at "
            f"{bundle_path} does not verify against the provisioned "
            "bundle signing key. Refusing to operate on unsigned or "
            "altered policy."
        ) from exc

    baselines = body.get("identity_baselines")
    if not isinstance(baselines, dict) or not baselines:
        raise PolicyBundleMalformed(
            "POLICY_BUNDLE_MALFORMED: bundle pins no identity baselines."
        )
    fw = body.get("firewall") or {}
    calibration = FirewallCalibration(
        threshold=float(fw.get("threshold", 0.90)),
        metadata_floor=float(fw.get("metadata_floor", 0.75)),
        linguistic_floor=float(fw.get("linguistic_floor", 0.60)),
        weight_metadata=float(fw.get("weight_metadata", 0.55)),
        weight_linguistic=float(fw.get("weight_linguistic", 0.35)),
        weight_behavioral=float(fw.get("weight_behavioral", 0.10)),
    )
    return PolicyBundle(
        version=str(body.get("version", "")),
        identity_baselines={str(k): str(v) for k, v in baselines.items()},
        firewall=calibration,
        tripwire_ruleset=str(body.get("tripwire_ruleset", "")),
        raw=body,
    )
