"""Container entry point for persistent Sanders Dash & Seal services.

Rewired to the root ``wsgi.py`` factory, the only ``create_native_application``
that exists in the repository. (The previous import from
``core_platform.native_runtime`` named a factory that file never defined;
``native_runtime`` is now a thin shim over the deployment boundary.)
In the container this file is served as ``backend.wsgi`` with the repository
root on the path, so ``wsgi`` resolves to the root entry point, not to this
file; ``backend/Dockerfile`` must therefore keep this file at
``backend/wsgi.py`` and not copy it over the root ``wsgi.py``.
"""
from wsgi import create_native_application

application = create_native_application()
