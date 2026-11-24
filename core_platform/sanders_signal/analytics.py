"""Sanders Signal — analytics: aggregate publish metrics.

Metrics come only from real publish results. Missing metrics are
recorded as ``NOT_AVAILABLE``, never invented.
"""
from __future__ import annotations

from .models import PublishResult

METRIC_FIELDS = ("views", "likes", "comments", "reach")


def collect_metrics(results: list[PublishResult]) -> dict:
    """Aggregate metrics per network and per company.

    Returns ``{"by_network": {...}, "by_company": {...}}`` where each
    entry maps a metric field to a summed number, or ``NOT_AVAILABLE``
    when no result carried a real value for that field.
    """
    by_network: dict[str, dict[str, object]] = {}
    by_company: dict[str, dict[str, object]] = {}
    for result in results:
        metrics = result.metrics or {}
        for bucket, key in ((by_network, result.network), (by_company, result.company)):
            entry = bucket.setdefault(key, {})
            for field in METRIC_FIELDS:
                value = metrics.get(field, "NOT_AVAILABLE")
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    previous = entry.get(field, 0)
                    if isinstance(previous, (int, float)):
                        entry[field] = previous + value
                else:
                    entry.setdefault(field, "NOT_AVAILABLE")
    return {"by_network": by_network, "by_company": by_company}


__all__ = ["METRIC_FIELDS", "collect_metrics"]
