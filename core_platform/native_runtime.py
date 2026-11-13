"""Thin composition root for the Sanders Dash & Seal WSGI application.

This module REPLACES the previous native_runtime.py (185 lines, 2026-11-13
cleanup report). That file could not run at all: it had a syntax error at
line 130 (positional argument after a keyword argument), imported roughly
19 factory names that do not exist in their target modules, called
``RuntimeBindings`` positionally with 8 arguments against a keyword-only
dataclass, called ``create_pipeline_app`` with 7 arguments against a
4-parameter definition, referenced ``self.payments`` before assignment, and
provided no WSGI routing despite its docstring.

Repairing that file in place was not possible: the factories it depended on
do not exist anywhere in the repository, so a repair would have meant
inventing the platform's service layer. Instead this module delegates to
the one composition root that does exist and is now verified importable:
``deploy.deployment.create_application`` / ``load_application``.

``create_native_application`` is the factory historically imported by
``passenger_wsgi.py`` and ``backend/wsgi.py``. With no factory reference it
returns the diagnostic-only application: /healthz answers, static assets
serve, and every authority-gated route fails closed (503) until the owner
supplies trusted production bindings through a factory reference. That is
the same fail-closed behaviour ``deployment.create_application`` documents.
No credentials are read here; production bindings are supplied only through
the administrator-installed factory path in ``deployment.load_application``.
"""

from deploy.deployment import create_application, load_application

__all__ = ["create_native_application", "create_application", "load_application"]


def create_native_application(factory_reference=None, *, transaction_db=None):
    """Return the WSGI application for this deployment.

    With no arguments this is the diagnostic-only application. Pass a
    trusted ``"module:factory"`` reference (and optionally a transaction
    database path) to load owner-supplied runtime bindings.
    """
    return load_application(factory_reference, transaction_db=transaction_db)
