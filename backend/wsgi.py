"""Container entry point for persistent Sanders Dash & Seal services.

Delegates to the canonical root wsgi.py. The previous version imported
``create_native_application`` from ``core_platform.native_runtime``, which
does not define it (and that module does not parse), so this entry point
could never start.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wsgi import app as application
from wsgi import create_native_application

__all__ = ["application", "create_native_application"]
