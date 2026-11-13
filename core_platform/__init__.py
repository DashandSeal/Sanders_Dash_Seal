"""Sanders Dash & Seal core platform package.

Added in the Daedalus rebuild (2026-11-13) so ``core_platform`` is a
regular package: its modules use relative imports and previously only
loaded as a PEP 420 namespace package from the repo root.

Daedalus public names are exported lazily (PEP 562) so importing the
package itself stays cheap and never pulls a provider client: the
names resolve to their modules only on first attribute access.
"""
from __future__ import annotations

from typing import Any

__all__: list[str] = [
    "DaedalusEngineConfig",
    "DaedalusSettings",
    "VoiceTurnRunner",
    "build_engine",
    "build_voice_runner",
    "describe",
]

_LAZY_EXPORTS: dict[str, str] = {
    "DaedalusEngineConfig": ".daedalus_engine",
    "DaedalusSettings": ".daedalus_config",
    "VoiceTurnRunner": ".daedalus_engine",
    "build_engine": ".daedalus_engine",
    "build_voice_runner": ".daedalus_engine",
    "describe": ".daedalus_engine",
}


def __getattr__(name: str) -> Any:
    module_name = _LAZY_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    module = importlib.import_module(module_name, __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
