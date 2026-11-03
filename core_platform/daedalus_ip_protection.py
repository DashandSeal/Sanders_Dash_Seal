"""Daedalus intellectual-property preservation controls.

Technical controls protect evidence and confidentiality. They do not grant
patent rights, substitute for a patent filing, or establish inventorship.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping


@dataclass(frozen=True)
class InventionRecord:
    invention_id: str
    title: str
    inventor_assertions: tuple[str, ...]
    source_sha256: str
    created_utc: str
    confidentiality: str = "restricted"

    @classmethod
    def from_source(
        cls, *, invention_id: str, title: str,
        inventor_assertions: tuple[str, ...], source: bytes,
    ) -> "InventionRecord":
        if not invention_id or not title or not source:
            raise ValueError("Invention ID, title and source are required")
        return cls(
            invention_id=invention_id,
            title=title,
            inventor_assertions=inventor_assertions,
            source_sha256=hashlib.sha256(source).hexdigest(),
            created_utc=datetime.now(timezone.utc).isoformat(),
        )

    def canonical_bytes(self) -> bytes:
        return json.dumps(
            self.__dict__, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")


def sign_evidence(record: InventionRecord, signing_key: bytes) -> str:
    """HMAC authenticity for private records; key must remain outside Git."""
    if len(signing_key) < 32:
        raise ValueError("Signing key must have at least 32 bytes")
    return hmac.new(signing_key, record.canonical_bytes(), hashlib.sha256).hexdigest()


def verify_evidence(record: InventionRecord, signing_key: bytes, signature: str) -> bool:
    return hmac.compare_digest(sign_evidence(record, signing_key), signature)


def publication_guard(
    *,
    classification: str,
    explicit_publication_authorization: bool,
    patent_counsel_clearance: bool,
) -> None:
    """Prevent accidental disclosure of restricted invention materials."""
    if classification != "public" and not (
        explicit_publication_authorization and patent_counsel_clearance
    ):
        raise PermissionError("Restricted invention content must not be published")


def sanitize_provenance(metadata: Mapping[str, str]) -> dict[str, str]:
    """Keep only nonsecret provenance fields in repository metadata."""
    permitted = {"invention_id", "source_sha256", "created_utc", "classification"}
    return {key: value for key, value in metadata.items() if key in permitted}
