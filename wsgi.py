"""Persistent Sanders Dash & Seal application server entry point."""
from core_platform.native_runtime import create_native_application

# Aligned variable name to match your Dockerfile WSGI boot commands
app = create_native_application()
