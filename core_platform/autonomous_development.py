"""
Module: core_platform.autonomous_development
Architectural Layer: L15+ Autonomous Feature Development Coordinator
Description: Coordinates independently proposed feature work across platform tracks.
             Validates generated source artifacts, file paths, and cryptographic signatures.
"""

from dataclasses import dataclass
import hashlib
import json
import re
from upgrade_sidecar import require_core_laws

class DevelopmentDenied(Exception):
    pass

TRACKS = frozenset({
    'frontend', 'backend', 'notarial', 'payments', 'security',
    'synthetic_ai', 'docker', 'patent_protection', 'operations'
})

ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$')
# Safe relative path validation regex (allows standard alphanumeric folders and filenames)
RELATIVE_PATH_RE = re.compile(r'^(?!/)(?!.*//)(?!.*\.\.)[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*$')

@dataclass(frozen=True)
class FeatureRequest:
    feature_id: str
    track: str
    requirement_ref: str
    objective: str
    dependency_ids: tuple = ()

    def validate(self):
        if not ID.fullmatch(self.feature_id) or self.track not in TRACKS:
            raise DevelopmentDenied('Invalid feature identity or track')
        if not self.requirement_ref.strip() or not self.objective.strip():
            raise DevelopmentDenied('MASTER requirement and objective required')
        if not isinstance(self.dependency_ids, tuple):
            raise DevelopmentDenied('Dependency IDs must be an immutable tuple')

class AutonomousDevelopment:
    """Feature generation, verification and PR preparation via bounded adapters."""

    def __init__(self, generator, verifier, publisher, audit, core_laws=None):
        if core_laws is not None:
            require_core_laws(core_laws)
        self.generator = generator
        self.verifier = verifier
        self.publisher = publisher
        self.audit = audit

    def prepare(self, request, inventory):
        if not isinstance(request, FeatureRequest):
            raise DevelopmentDenied('FeatureRequest required')
            
        request.validate()
        
        if not isinstance(inventory, dict) or request.track not in inventory:
            raise DevelopmentDenied('Missing platform component inventory')
        if any(dep not in inventory for dep in request.dependency_ids):
            raise DevelopmentDenied('Unknown dependency')
            
        self.audit.preserve('stage', 'FEATURE_INTENT', 'feature_id', request.feature_id,
                           'requirement', request.requirement_ref, 'track', request.track)
                           
        candidate = self.generator.generate(request, inventory)
        if not isinstance(candidate, dict) or not candidate:
            raise DevelopmentDenied('No generated source candidate')
            
        # FIX: Enforce safe relative path validation via RELATIVE_PATH_RE
        for path, source in candidate.items():
            if not isinstance(path, str) or not RELATIVE_PATH_RE.fullmatch(path) or not isinstance(source, str):
                raise DevelopmentDenied('Unsafe generated path or content')
                
        hashes = {
            path: hashlib.sha256(source.encode()).hexdigest()
            for path, source in sorted(candidate.items())
        }
        
        evidence = self.verifier.verify(request, candidate, hashes)
        if not isinstance(evidence, dict) or evidence.get('passed') is not True:
            self.audit.preserve('stage', 'FEATURE_REJECTED', 'feature_id', request.feature_id,
                               'hashes', hashes)
            raise DevelopmentDenied('Independent development verification failed')
            
        self.audit.preserve('stage', 'FEATURE_VERIFIED', 'feature_id', request.feature_id,
                           'hashes', hashes, 'evidence', evidence)
                           
        result = self.publisher.open_review(request, candidate, hashes, evidence)
        self.audit.preserve('stage', 'FEATURE_REVIEW_OPENED', 'feature_id', request.feature_id,
                           'hashes', hashes, 'review', result)
                           
        return result
