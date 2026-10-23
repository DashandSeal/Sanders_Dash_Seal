"""MASTER 13: execute the verified source snapshot, not an unrelated callback.

This runner is explicitly development-only. Python code is not sandboxed; only
trusted, independently approved source may be tested here. A production runner
must verify the dependency/runtime closure and enforce the network jail externally.
"""
from dataclasses import dataclass
import json
from pathlib import Path
from .security import Denied

@dataclass(frozen=True)
class SignedPythonArtifact:
    name: str
    source: bytes
    manifest_json: str

    @classmethod
    def read_pair(cls, root, name):
        root = Path(root).resolve(strict=True)
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts or relative.suffix != '.py':
            raise Denied('Invalid artifact path')
        path = root / relative
        manifest = Path(str(path) + '.pbd.json')
        for candidate in (path, manifest):
            if candidate.is_symlink() or any(parent.is_symlink() for parent in candidate.parents if parent != root):
                raise Denied('Symlink artifact path')
            if not candidate.resolve(strict=True).is_relative_to(root):
                raise Denied('Artifact outside approved root')
        return cls(relative.as_posix(), path.read_bytes(), manifest.read_text())

class DevelopmentArtifactRunner:
    def __init__(self, validator, *, enable_development_execution=False):
        if enable_development_execution is not True:
            raise Denied('Production execution unavailable; development opt-in required')
        self.validator = validator

    def validate(self, artifact, scope):
        if type(artifact) is not SignedPythonArtifact:
            raise Denied('A signed source artifact is required; callbacks are forbidden')
        self.validator.validate(artifact.source, artifact.name, scope,
                                json.loads(artifact.manifest_json))

    def execute(self, artifact, scope, payload):
        # Validate the exact immutable snapshot immediately before compilation.
        self.validate(artifact, scope)
        code = compile(artifact.source, artifact.name, 'exec')
        namespace = {'__name__': '__pbd_development_artifact__'}
        exec(code, namespace)
        function = namespace.get('execute')
        if not callable(function):
            raise Denied('Artifact must define execute(scope, payload)')
        result = function(scope, payload)
        if not isinstance(result, bytes):
            raise Denied('Artifact result must be bytes')
        return result
