"""Sanders Signal — network adapters.

``BaseAdapter`` is the interface every network adapter implements.
``MetaAdapter`` is real: Meta Graph API for Facebook Pages and
Instagram Business accounts, tokens from the environment only, with an
injectable HTTP transport so a dry run never touches the network.
LinkedIn, Threads, YouTube, TikTok and X are not-connected stubs: they
return ``not_configured`` with a reason and never touch the network or
raise at import. X's stub additionally records that a paid tier is
required (owner decision pending).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import timezone

from .config import AdapterStatus, env, meta_env_name, meta_status
from .models import Post, PublishResult, utcnow

GRAPH_API_BASE = "https://graph.facebook.com/v20.0"


class BaseAdapter:
    """Interface for one network adapter."""

    network = "base"

    def status(self, company: str) -> AdapterStatus:
        return AdapterStatus(AdapterStatus.NOT_CONNECTED, "no adapter")

    def publish(self, post: Post, company: str) -> PublishResult:
        raise NotImplementedError


def _default_transport(method: str, url: str, payload: dict) -> dict:
    """Real HTTP transport (urllib). Replaced by a recording stub in dry runs."""
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", "replace")
        return {"error": {"message": body, "code": error.code}}


class MetaAdapter(BaseAdapter):
    """Meta Graph API: Facebook Page feed + Instagram Business publish.

    One adapter instance serves one target: ``"facebook"`` publishes
    to the Page feed, ``"instagram"`` publishes through the IG media
    container flow. The hub builds one instance per network so a
    Facebook fan-out never also posts to Instagram (and vice versa).
    """

    network = "meta"

    def __init__(self, transport=None, target: str = "facebook") -> None:
        # transport(method, url, payload) -> response dict. Injectable so
        # a dry run can record calls without any request leaving the machine.
        self.transport = transport or _default_transport
        self.target = target
        self.network = target

    def status(self, company: str) -> AdapterStatus:
        state = meta_status(company)
        if state.status != AdapterStatus.CONFIGURED:
            return state
        if self.target == "instagram":
            _, _, ig_user_id = self._company_credentials(company)
            if not ig_user_id:
                return AdapterStatus(
                    AdapterStatus.NOT_CONFIGURED,
                    "Meta not configured for %s: no Instagram user id in the environment"
                    % company,
                )
        return state

    def _company_credentials(self, company: str) -> tuple[str | None, str | None, str | None]:
        token = env(meta_env_name(company, "PAGE_TOKEN")) or env(
            "SANDERS_SIGNAL_META_PAGE_TOKEN"
        )
        page_id = env(meta_env_name(company, "PAGE_ID")) or env(
            "SANDERS_SIGNAL_META_PAGE_ID"
        )
        ig_user_id = env(meta_env_name(company, "IG_USER_ID")) or env(
            "SANDERS_SIGNAL_META_IG_USER_ID"
        )
        return token, page_id, ig_user_id

    def publish(self, post: Post, company: str) -> PublishResult:
        state = self.status(company)
        if state.status != AdapterStatus.CONFIGURED:
            return PublishResult(
                post_id=post.post_id,
                network=self.target,
                company=company,
                status="not_configured",
                reason=state.reason,
            )
        token, page_id, ig_user_id = self._company_credentials(company)
        try:
            if self.target == "facebook":
                response = self.transport(
                    "POST",
                    "%s/%s/feed" % (GRAPH_API_BASE, page_id),
                    {"message": post.text, "access_token": token},
                )
                if isinstance(response, dict) and response.get("error"):
                    return PublishResult(
                        post_id=post.post_id,
                        network="facebook",
                        company=company,
                        status="failed",
                        reason="Facebook publish failed: %s" % (response["error"],),
                    )
                remote_id = str(response.get("id", "")) or None
            else:  # instagram: container, then media_publish.
                container = self.transport(
                    "POST",
                    "%s/%s/media" % (GRAPH_API_BASE, ig_user_id),
                    {"caption": post.text, "access_token": token},
                )
                if isinstance(container, dict) and container.get("error"):
                    return PublishResult(
                        post_id=post.post_id,
                        network="instagram",
                        company=company,
                        status="failed",
                        reason="Instagram container failed: %s" % (container["error"],),
                    )
                published = self.transport(
                    "POST",
                    "%s/%s/media_publish" % (GRAPH_API_BASE, ig_user_id),
                    {
                        "creation_id": container.get("id", ""),
                        "access_token": token,
                    },
                )
                if isinstance(published, dict) and published.get("error"):
                    return PublishResult(
                        post_id=post.post_id,
                        network="instagram",
                        company=company,
                        status="failed",
                        reason="Instagram publish failed: %s" % (published["error"],),
                    )
                remote_id = str(published.get("id", "")) or None
            return PublishResult(
                post_id=post.post_id,
                network=self.target,
                company=company,
                status="published",
                reason="",
                remote_id=remote_id,
                metrics={"views": "NOT_AVAILABLE", "likes": "NOT_AVAILABLE",
                         "comments": "NOT_AVAILABLE", "reach": "NOT_AVAILABLE"},
                published_at=utcnow(),
            )
        except Exception as error:  # transport failure is a failed result, never a crash
            return PublishResult(
                post_id=post.post_id,
                network=self.target,
                company=company,
                status="failed",
                reason="Meta transport failed: %s" % (error,),
            )


class _StubAdapter(BaseAdapter):
    """One not-connected network: returns not_configured, touches nothing."""

    network = "stub"
    display_name = "Stub"

    def __init__(self, extra_reason: str = "") -> None:
        self.extra_reason = extra_reason

    def status(self, company: str) -> AdapterStatus:
        return AdapterStatus(
            AdapterStatus.NOT_CONNECTED,
            "%s not connected: no app/token configured" % self.display_name,
        )

    def publish(self, post: Post, company: str) -> PublishResult:
        reason = "%s not connected: no app/token configured" % self.display_name
        if self.extra_reason:
            reason += " (%s)" % self.extra_reason
        return PublishResult(
            post_id=post.post_id,
            network=self.network,
            company=company,
            status="not_configured",
            reason=reason,
        )


class LinkedInAdapter(_StubAdapter):
    network = "linkedin"
    display_name = "LinkedIn"


class ThreadsAdapter(_StubAdapter):
    network = "threads"
    display_name = "Threads"


class YouTubeAdapter(_StubAdapter):
    network = "youtube"
    display_name = "YouTube"


class TikTokAdapter(_StubAdapter):
    network = "tiktok"
    display_name = "TikTok"


class XAdapter(_StubAdapter):
    network = "x"
    display_name = "X"

    def __init__(self) -> None:
        super().__init__(extra_reason="paid tier required (owner decision pending)")


# Network name -> adapter class. The hub maps facebook/instagram to the
# Meta adapter and every other network to its stub.
ADAPTERS: dict[str, type[BaseAdapter]] = {
    "facebook": MetaAdapter,
    "instagram": MetaAdapter,
    "linkedin": LinkedInAdapter,
    "threads": ThreadsAdapter,
    "youtube": YouTubeAdapter,
    "tiktok": TikTokAdapter,
    "x": XAdapter,
}


def adapter_for(network: str, transport=None) -> BaseAdapter:
    """Build the adapter for one network (Meta gets the transport and
    the network as its target, so it publishes to that destination only)."""
    cls = ADAPTERS.get(network)
    if cls is None:
        return _StubAdapter()
    if cls is MetaAdapter:
        return MetaAdapter(transport=transport, target=network)
    return cls()


__all__ = [
    "BaseAdapter",
    "MetaAdapter",
    "LinkedInAdapter",
    "ThreadsAdapter",
    "YouTubeAdapter",
    "TikTokAdapter",
    "XAdapter",
    "ADAPTERS",
    "adapter_for",
    "GRAPH_API_BASE",
]
