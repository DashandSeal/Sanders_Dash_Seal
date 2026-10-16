"""Local atomic artifact staging adapter for the Sanders Dash & Seal sidecar.

This is a filesystem staging executor, NOT a production process manager or
an independent authorization, AI inference, or OS sandbox service.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile


class LocalUpgradeExecutor:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _component_dir(self, record):
        name = record["component"]
        if not isinstance(name, str) or not name or not all(
            c.isascii() and (c.isalnum() or c in "_-") for c in name
        ):
            raise ValueError("Invalid component")
        directory = self.root / name
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def _state(self, directory):
        state = directory / "state.json"
        if not state.exists():
            return {}
        return json.loads(state.read_text(encoding="utf-8"))

    def _write_state(self, directory, state):
        fd, tmp = tempfile.mkstemp(dir=directory, prefix=".state-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(state, stream, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, directory / "state.json")
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def stage(self, record, artifact_path):
        directory = self._component_dir(record)
        if self._state(directory).get("pending"):
            raise ValueError("Unverified upgrade already staged")
        source = Path(artifact_path)
        if not source.is_file() or source.is_symlink():
            raise ValueError("Regular source required")
        payload = source.read_bytes()
        actual = hashlib.sha256(payload).hexdigest()
        if actual != record["artifact_hash"]:
            raise ValueError("Artifact digest mismatch")
        current = directory / "current.bin"
        previous = directory / "previous.bin"
        if current.exists():
            shutil.copyfile(current, previous)
        fd, tmp = tempfile.mkstemp(dir=directory, prefix=".artifact-")
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, current)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        self._write_state(directory, {
            "pending": True, "digest": actual,
            "previous": previous.exists(), "version": record["version"]
        })
        return {"staged": True, "sha256": actual, "mode": "local-dark"}

    def verify(self, record):
        directory = self._component_dir(record)
        state = self._state(directory)
        current = directory / "current.bin"
        if not state.get("pending") or not current.exists():
            return {"healthy": False}
        digest = hashlib.sha256(current.read_bytes()).hexdigest()
        if digest != record["artifact_hash"] or digest != state.get("digest"):
            return {"healthy": False}
        state["pending"] = False
        self._write_state(directory, state)
        return {"healthy": True, "sha256": digest, "scope": "artifact-integrity-only"}

    def rollback(self, record):
        directory = self._component_dir(record)
        state = self._state(directory)
        previous = directory / "previous.bin"
        current = directory / "current.bin"
        if not state.get("previous") or not previous.exists():
            return {"restored": False, "reason": "no prior baseline"}
        os.replace(previous, current)
        state["pending"] = False
        state["digest"] = hashlib.sha256(current.read_bytes()).hexdigest()
        state["previous"] = False
        self._write_state(directory, state)
        return {"restored": True, "sha256": state["digest"]}
