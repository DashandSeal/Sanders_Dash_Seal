"""WSGI server entry point; default service APIs remain unavailable."""
import os
from core_platform.deployment import load_application

application = load_application(None)
