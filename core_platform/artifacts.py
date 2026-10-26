"""
Module: core_platform.artifacts
Architectural Layer: MASTER 13 - Source Artifact Compilation Runner
Description: Validates and executes verified development-only source snapshots.
             Enforces absolute path resolution and structural sandboxing boundaries.
"""

from dataclasses import dataclass
import json
import pathlib
from security import Denied

@dataclass(frozen=True)
class SignedPythonArtifact:
    name: str
    source: bytes
    manifest_json: str

    @classmethod
    def read_pair(cls, root, name):
        root_path = pathlib.Path(root).resolve(strict=True)
        relative_path = pathlib.Path(name)
        
        if relative_path.is_absolute() or '..' in relative_path.parts or relative_path.suffix != '.py':
            raise Denied('Invalid artifact path')
            
        path = root_path / relative_path
        manifest = path.with_name(path.name + '.pbd.json')
        
        # FIX: Explicitly resolve absolute filesystem strings to guarantee robust boundary tracking
        root_str = str(root_path)
        for candidate in (path, manifest):
            resolved_candidate = candidate.resolve()
            if candidate.is_symlink() or resolved_candidate.is_symlink():
                raise Denied('Symlink artifact path')
                
            # Verify absolute layout encapsulation boundaries cleanly
            if not str(resolved_candidate).startswith(root_str):
                raise Denied('Artifact outside approved root')
                
        return cls(str(relative_path.as_posix()), path.read_bytes(), manifest.read_text())

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
        # Validate the exact immutable snapshot immediately before compilation
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
