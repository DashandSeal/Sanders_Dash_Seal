"""Sanders Signal — SignalHub: queue, routing, approval gate, fan-out.

Composer (write once) -> guardrails -> queue (now or scheduled) ->
routing (company-only, or HQ broadcast) -> approval gate (HQ
broadcast: explicit owner approval, default deny) -> adapters ->
publish log -> notifications.

The hub never publishes a headquarters broadcast without an approval
record, never routes a company post to another company, never adds an
address or contact info, and never blocks import or startup when an
adapter is unconfigured: unconfigured adapters report
``not_configured`` diagnostically. One network's failure never blocks
the others.
"""
from __future__ import annotations

import os

from . import analytics, notifications
from .adapters import adapter_for
from .config import ALL_COMPANIES, HEADQUARTERS_COMPANY
from .guardrails import check_post
from .media import route_media
from .models import (
    ApprovalRecord,
    MediaAsset,
    Notification,
    Post,
    PublishResult,
    utcnow,
)
from .roles import can_approve, can_publish, can_write
from .scheduling import is_due, is_overdue, sort_for_publish

_BOZLY_HOOK_NOTE = "bozly_receipt: not configured — no signature invented"


class SignalHub:
    """The Sanders Signal distribution hub (local only, no live post
    without configured tokens)."""

    def __init__(self, transport=None) -> None:
        # transport(method, url, payload) -> dict; injected by the
        # dry-run recording stub so no request ever leaves the machine.
        self.transport = transport
        self._queue: list[Post] = []
        self._posts: dict[str, Post] = {}
        self._log: list[dict] = []
        self._results: list[PublishResult] = []
        self.media_assets: dict[str, MediaAsset] = {}

    # -- media library -------------------------------------------------

    def register_asset(self, asset: MediaAsset) -> None:
        """Add one approved media asset (reference, not a file copy)."""
        self.media_assets[asset.asset_id] = asset

    # -- compose / queue ----------------------------------------------

    def compose(self, post: Post, officer: str) -> Post:
        """Role check + guardrails + accessibility metadata, then queue.

        Returns the post with its status set: ``awaiting_approval`` for
        an unapproved headquarters broadcast, otherwise ``queued``.
        A blocked post gets status ``blocked`` and is not queued.
        """
        allowed, reason = can_write(officer, post.author_company)
        if not allowed:
            post.status = "blocked"
            self._log_event("compose_denied", post, {"reason": reason})
            raise PermissionError(reason)
        problems = check_post(post, known_asset_ids=set(self.media_assets))
        if problems:
            post.status = "blocked"
            self._log_event("compose_blocked", post, {"reasons": problems})
            raise ValueError("; ".join(problems))
        if post.reach == "headquarters" and post.approval is None:
            post.status = "awaiting_approval"
        else:
            post.status = "queued"
        self._posts[post.post_id] = post
        self._log_event("composed", post, {})
        return post

    def enqueue(self, post: Post) -> Post:
        """Put a composed post on the queue (no duplicate entries)."""
        if post not in self._queue:
            self._queue.append(post)
        return post

    # -- approval -------------------------------------------------------

    def approve(
        self,
        post_id: str,
        officer: str,
        client_signatures: dict | None = None,
        public_keys: dict | None = None,
    ) -> ApprovalRecord:
        """Approve a headquarters broadcast. Default is deny.

        Only the headquarters company can broadcast, and only an
        officer holding the approver role for it. The approval is
        recorded through the Bozly action-integrity hook when Bozly
        keys are configured; otherwise the record carries the hook
        note and no signature is ever invented.
        """
        post = self._posts.get(post_id)
        if post is None:
            raise ValueError("unknown post: %r" % (post_id,))
        if post.reach != "headquarters":
            raise ValueError("only a headquarters broadcast needs approval")
        allowed, reason = can_approve(officer, HEADQUARTERS_COMPANY)
        if not allowed:
            self._log_event("approve_denied", post, {"reason": reason})
            raise PermissionError(reason)
        destinations = list(ALL_COMPANIES)
        payload = {
            "post_id": post.post_id,
            "reach": post.reach,
            "destinations": destinations,
            "officer": officer,
        }
        receipt, note = self._bozly_receipt(payload, client_signatures, public_keys)
        record = ApprovalRecord(
            post_id=post.post_id,
            officer=officer,
            approved_at=utcnow(),
            destinations=destinations,
            receipt=receipt,
            note=note,
        )
        post.approval = record
        post.status = "approved"
        self._log_event("approved", post, {"officer": officer, "receipt": receipt})
        return record

    def _bozly_receipt(
        self,
        payload: dict,
        client_signatures: dict | None,
        public_keys: dict | None,
    ) -> tuple[str | None, str]:
        """Bozly action-integrity hook. Returns (receipt, note).

        The receipt is the Bozly payload hash (and, when the owner
        supplies signatures and provisioned public keys, the verified
        signatories). When Bozly is not configured, the receipt is None
        and the note says so — no signature is ever invented.
        """
        configured = any(key.startswith("BOZLY_") for key in os.environ)
        if not configured:
            return None, _BOZLY_HOOK_NOTE
        try:
            from core_platform.bozly.bozly_auth_gate import BozlyAuthGate
        except ImportError:
            return None, _BOZLY_HOOK_NOTE
        try:
            gate = BozlyAuthGate()
            digest = gate.generate_action_payload_hash("sanders_signal.publish", payload)
            if client_signatures and public_keys:
                outcome = gate.evaluate_executive_approvals(
                    "sanders_signal.publish", payload, client_signatures, public_keys
                )
                verified = outcome.get("verified_signatories", [])
                return digest, "bozly verified signatories: %s" % (verified,)
            return digest, "bozly payload hash recorded (no signatures supplied)"
        except Exception as error:
            return None, "bozly hook failed (no signature invented): %s" % (error,)

    # -- publish ---------------------------------------------------------

    def publish_now(self, post_id: str, officer: str) -> list[PublishResult]:
        """Publish one post now: publisher role, guardrails, approval,
        then fan-out. Returns the per-network, per-company results."""
        post = self._posts.get(post_id)
        if post is None:
            raise ValueError("unknown post: %r" % (post_id,))
        allowed, reason = can_publish(officer, post.author_company)
        if not allowed:
            post.status = "blocked"
            self._log_event("publish_denied", post, {"reason": reason})
            raise PermissionError(reason)
        if post.reach == "headquarters" and post.approval is None:
            post.status = "awaiting_approval"
            self._log_event("approval_waiting", post, {})
            notifications.on_approval_waiting(
                post.post_id,
                "Headquarters broadcast %s is waiting for owner approval"
                % post.post_id,
            )
            return []
        problems = check_post(
            post,
            known_asset_ids=set(self.media_assets),
            require_approval=(post.reach == "headquarters"),
        )
        if problems:
            post.status = "blocked"
            self._log_event("publish_blocked", post, {"reasons": problems})
            raise ValueError("; ".join(problems))
        results = self._fan_out(post)
        self._finish_publish(post, results)
        return results

    def publish_due(self, now=None) -> list[PublishResult]:
        """Publish every due post, in scheduled order. Overdue posts
        publish at the next run and are logged as overdue."""
        moment = now or utcnow()
        due = [post for post in sort_for_publish(list(self._queue)) if is_due(post, moment)]
        all_results: list[PublishResult] = []
        for post in due:
            if is_overdue(post, moment):
                self._log_event("publish_overdue", post, {})
            try:
                all_results.extend(self.publish_now(post.post_id, post.author_officer))
            except (PermissionError, ValueError) as error:
                post.status = "failed"
                self._log_event("publish_failed", post, {"reason": str(error)})
                notifications.on_failed(
                    post.post_id, "Publish failed: %s" % (error,)
                )
        return all_results

    def _fan_out(self, post: Post) -> list[PublishResult]:
        """One post to every destination company and network."""
        if post.reach == "headquarters":
            destinations = list(ALL_COMPANIES)
        else:
            destinations = [post.author_company]
        media_plan = dict(
            (network, (accepted, reason))
            for network, accepted, reason in route_media(post)
        )
        results: list[PublishResult] = []
        for company in destinations:
            for network, (accepted, reason) in media_plan.items():
                if not accepted:
                    results.append(
                        PublishResult(
                            post_id=post.post_id,
                            network=network,
                            company=company,
                            status="declined",
                            reason=reason,
                        )
                    )
                    continue
                adapter = adapter_for(network, transport=self.transport)
                results.append(adapter.publish(post, company))
        return results

    def _finish_publish(self, post: Post, results: list[PublishResult]) -> None:
        """Record results, aggregate metrics, fire notifications."""
        self._results.extend(results)
        if post in self._queue:
            self._queue.remove(post)
        published = [r for r in results if r.status == "published"]
        failed = [r for r in results if r.status == "failed"]
        post.status = "published" if published else "failed"
        summary = analytics.collect_metrics(results)
        self._log_event(
            "published" if published else "publish_failed",
            post,
            {
                "published": len(published),
                "failed": len(failed),
                "metrics": summary,
            },
        )
        if published:
            notifications.on_published(
                post.post_id,
                "Post %s published to %d destination(s)"
                % (post.post_id, len(published)),
            )
        if failed:
            notifications.on_failed(
                post.post_id,
                "Post %s failed on %s"
                % (post.post_id, "; ".join(
                    "%s/%s: %s" % (r.network, r.company, r.reason) for r in failed
                )),
            )

    # -- log -------------------------------------------------------------

    def publish_log(self) -> list[dict]:
        """Full history: every event with its post's accessibility
        metadata attached, so a post never loses its language,
        sign-language or Braille information in the record."""
        return list(self._log)

    def results(self) -> list[PublishResult]:
        """All publish results so far."""
        return list(self._results)

    def _log_event(self, event: str, post: Post, details: dict) -> None:
        """One log entry, carrying the post's accessibility metadata."""
        entry = {
            "event": event,
            "post_id": post.post_id,
            "company": post.author_company,
            "reach": post.reach,
            "language": post.language,
            "sign_languages": sorted(
                {a.sign_language for a in post.attachments if a.sign_language}
            ),
            "braille_ready": bool(post.braille_ready_text),
            "status": post.status,
            "at": utcnow().isoformat(),
        }
        entry.update(details)
        self._log.append(entry)


__all__ = ["SignalHub"]
