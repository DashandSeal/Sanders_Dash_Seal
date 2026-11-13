"""Container entry point for persistent Sanders Dash & Seal services.

Single WSGI entry is the repo-root ``wsgi.py`` (``create_native_application``,
Stripe webhook gateway). The previous import from
``core_platform.native_runtime`` is removed: that module defines no
``create_native_application`` and cannot be imported (see
core_platform/native_runtime.py status in the deploy notes).
"""
import os
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from wsgi import application  # noqa: E402,F401  (single entry point)
