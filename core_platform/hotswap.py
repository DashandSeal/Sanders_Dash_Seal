"""
Module: core_platform.hotswap
Architectural Layer: L15+ Upgrade Orchestration Primitives (Docker Hotswap Engine)
Description: Dependency-safe zero-downtime hot-swap deployment coordinator.
             Performs safe multi-stage rollouts, continuous health sweeps,
             and automated zero-downtime microservice cutovers.
"""

from dataclasses import dataclass
import hashlib
import json
import re
from .upgrade_sidecar import require_core_laws

class HotSwapDenied(Exception):
    pass

DIGEST = re.compile(r'^(?:sha256:)?[A-Za-z0-9_.-]{8,}(?:@[A-Fa-f0-9]{64})?$')
IDENT = re.compile(r'^[A-Za-z0-9_-]{1,127}$')

@dataclass(frozen=True)
class Workload:
    name: str
    role: str
    current_image: str
    candidate_image: str
    dependencies: tuple = ()

    def validate(self):
        if not IDENT.fullmatch(self.name) or self.role not in ('frontend', 'backend', 'sidecar'):
            raise HotSwapDenied("Invalid workload identity or role")
        if not DIGEST.fullmatch(self.current_image) or not DIGEST.fullmatch(self.candidate_image):
            raise HotSwapDenied("Only immutable container image digests are permitted")
        if not isinstance(self.dependencies, tuple) or any(not isinstance(d, str) for d in self.dependencies):
            raise HotSwapDenied("Invalid dependency inventory profile")

@dataclass(frozen=True)
class UpgradePlan:
    release_id: str
    workloads: tuple
    inversion_record: dict

    def ordered(self):
        """Resolves topological dependencies cleanly using clear nonlocal tracking scopes."""
        by_name = {}
        for w in self.workloads:
            w.validate()
            if w.name in by_name:
                raise HotSwapDenied("Duplicate workload identifier discovered")
            by_name[w.name] = w

        ordered = []
        visited = set()
        visiting = set()

        def visit(name):
            # Explicitly claim parent scope context bounds to prevent UnboundLocalError crashes
            nonlocal ordered, visited, visiting

            if name in visiting:
                raise HotSwapDenied("Circular dependency cycle detected inside container matrix")
            if name in visited:
                return
            if name not in by_name:
                raise HotSwapDenied("Missing dependency declaration element across runtime layout")

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
        payload = {
            "release_id": self.release_id,
            "workloads": [
                {
                    "name": w.name,
                    "role": w.role,
                    "current_image": w.current_image,
                    "candidate_image": w.candidate_image,
                    "dependencies": list(w.dependencies)
                } for w in ordered
            ],
            "inversion_record": self.inversion_record
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

class GovernedHotswap:
    """Deploy dependency order, health-check, cut-over, verify, rollback loop matrix."""

    def __init__(self, deployment, routing, audit, authorize, core_laws=None):
        if core_laws is not None:
            require_core_laws(core_laws)
        self.deployment = deployment
        self.routing = routing
        self.audit = audit
        self.authorize = authorize

    def run(self, plan):
        if not isinstance(plan, UpgradePlan):
            raise HotSwapDenied("Invalid upgrade plan blueprint parameters")

        ordered = plan.ordered()
        fingerprint = plan.fingerprint()

        if self.authorize(plan, fingerprint) is not True:
            raise HotSwapDenied("Independent Twin-Gate / PBD production authorization failure")

        started = []
        switched = []
        try:
            self.audit.preserve({"stage": "UPGRADE_START", "release_id": plan.release_id, "fingerprint": fingerprint})

            # Step 1: Sequential Canary Deployment & Health Verification
            for w in ordered:
                self.deployment.start_candidate(w)
                started.append(w)
                if not self.deployment.healthy(w):
                    raise HotSwapDenied(f"Workload canary verification health metrics dropped: {w.name}")

                self.routing.cutover(w)
                switched.append(w)
                if not self.routing.verified(w):
                    raise HotSwapDenied(f"Traffic routing loop check verification failed: {w.name}")

                self.audit.preserve({"stage": "COMPONENT_HOTSWAP_SUCCESS", "workload": w.name})

            return "LIVE_VERIFIED"

        except Exception as error:
            # Step 2: Strict Fail-Closed Safe Rollback Sequences
            self.audit.preserve({"stage": "UPGRADE_CRITICAL_FAILURE", "error": str(error)})
            rollback_errors = []

            for w in reversed(switched):
                try:
                    self.routing.rollback(w)
                except Exception as exc:
                    rollback_errors.append((w.name, "routing", type(exc).__name__))

            for w in reversed(started):
                try:
                    self.deployment.stop_candidate(w)
                except Exception as exc:
                    rollback_errors.append((w.name, "deployment", type(exc).__name__))

            if rollback_errors:
                self.audit.preserve({"stage": "ROLLBACK_CORRUPTED", "errors": rollback_errors})
                raise HotSwapDenied("Rollback incomplete: cluster configuration split-brain state detected") from error
            raise

if __name__ == "__main__":
    pass
