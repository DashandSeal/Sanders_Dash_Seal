"""L15+ upgrade orchestration primitives: dependency-safe Docker workload cutover.

Development implementation. The deployment adapter must be independently authorized
under the MASTER Twin-Gate/PBD, and must not expose an unrestricted Docker socket.
"""
from dataclasses import dataclass
from hashlib import sha256
import json
import re
from .upgrade_sidecar import require_core_laws

class HotSwapDenied(Exception):
    pass

DIGEST = re.compile(r"^[a-z0-9][a-z0-9._/-]*@sha256:[0-9a-f]{64}$")
IDENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")

@dataclass(frozen=True)
class Workload:
    name: str
    role: str
    current_image: str
    candidate_image: str
    dependencies: tuple = ()

    def validate(self):
        if not IDENT.fullmatch(self.name) or self.role not in ("frontend", "backend", "sidecar", "worker"):
            raise HotSwapDenied("Invalid workload identity or role")
        if not DIGEST.fullmatch(self.current_image) or not DIGEST.fullmatch(self.candidate_image):
            raise HotSwapDenied("Only immutable container image digests are permitted")
        if not isinstance(self.dependencies, tuple) or any(not isinstance(x, str) for x in self.dependencies):
            raise HotSwapDenied("Invalid dependency inventory")

@dataclass(frozen=True)
class UpgradePlan:
    release_id: str
    workloads: tuple
    invention_record: dict

    def ordered(self):
        if not IDENT.fullmatch(self.release_id) or not self.workloads:
            raise HotSwapDenied("Invalid release")
        if not isinstance(self.invention_record, dict):
            raise HotSwapDenied("Invention provenance required")
        required = ("inventor", "intended_owner", "confidentiality", "source_commit", "design_reference")
        if any(not isinstance(self.invention_record.get(k), str) or not self.invention_record[k].strip()
               for k in required):
            raise HotSwapDenied("Incomplete patent-protection provenance")
        by_name = {}
        for w in self.workloads:
            w.validate()
            if w.name in by_name:
                raise HotSwapDenied("Duplicate workload")
            by_name[w.name] = w
        ordered, visited, visiting = [], set(), set()
        def visit(name):
            if name not in by_name or name in visiting:
                raise HotSwapDenied("Missing dependency or dependency cycle")
            if name in visited:
                return
            visiting.add(name)
            for dep in by_name[name].dependencies:
                visit(dep)
            visiting.remove(name)
            visited.add(name)
            ordered.append(by_name[name])
        for name in by_name:
            visit(name)
        return tuple(ordered)

    def fingerprint(self):
        ordered = self.ordered()
        payload = {"release_id": self.release_id,
                   "workloads": [dict(name=w.name, role=w.role,
                                      current_image=w.current_image,
                                      candidate_image=w.candidate_image,
                                      dependencies=list(w.dependencies)) for w in ordered],
                   "invention_record": self.invention_record}
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

class GovernedHotSwap:
    """Deploy dependency order; health-check, cut over, verify; rollback reverse order.

    All external adapters must be independently verified. This module does not
    mint leases, create signatures, or decide production authority itself.
    """
    def __init__(self, deployment, routing, audit, authorize, core_laws):
        require_core_laws(core_laws)
        self.deployment, self.routing, self.audit, self.authorize = deployment, routing, audit, authorize

    def run(self, plan):
        ordered = plan.ordered()
        fingerprint = plan.fingerprint()
        if self.authorize(plan, fingerprint) is not True:
            raise HotSwapDenied("Independent Twin-Gate/PBD production authorization required")
        started, switched = [], []
        try:
            self.audit.preserve({"stage": "UPGRADE_INTENT", "release": plan.release_id,
                                 "fingerprint": fingerprint, "invention_record": plan.invention_record})
            for w in ordered:
                self.deployment.start_candidate(w)
                started.append(w)
                if self.deployment.healthy(w) is not True:
                    raise HotSwapDenied("Candidate unhealthy: " + w.name)
                self.routing.cutover(w)
                switched.append(w)
                if self.routing.verified(w) is not True:
                    raise HotSwapDenied("Cutover verification failed: " + w.name)
                self.audit.preserve({"stage": "COMPONENT_VERIFIED", "release": plan.release_id,
                                     "component": w.name, "candidate_image": w.candidate_image})
            self.audit.preserve({"stage": "UPGRADE_VERIFIED", "release": plan.release_id,
                                 "fingerprint": fingerprint})
            return "LIVE_VERIFIED"
        except BaseException:
            rollback_errors = []
            for w in reversed(switched):
                try:
                    self.routing.rollback(w)
                except BaseException as exc:
                    rollback_errors.append((w.name, type(exc).__name__))
            for w in reversed(started):
                try:
                    self.deployment.stop_candidate(w)
                except BaseException as exc:
                    rollback_errors.append((w.name, type(exc).__name__))
            self.audit.preserve({"stage": "UPGRADE_SHELTER", "release": plan.release_id,
                                 "rollback_errors": rollback_errors})
            if rollback_errors:
                raise HotSwapDenied("Rollback incomplete; shelter and human intervention required")
            raise
