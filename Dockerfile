# Sanders Dash & Seal — WSGI application image (Oracle Linux 9 target host).
#
# This file REPLACES the previous root "Dockerfile", which was 230 lines of
# Python (the generate_pipeline_matrix generator, now moved to
# deploy/generate_pipeline_matrix.py) and contained zero Docker instructions,
# so no image could ever build from it.
#
# The image runs the composed WSGI entry point in wsgi.py
# (deployment-boundary app + Stripe webhook app) under gunicorn, bound to
# 127.0.0.1:8000 per deploy/gunicorn.conf.py. The reverse proxy (nginx.conf)
# reaches it as the compose service wsgi-backend:8000.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt requirements-server.txt ./

RUN pip install --no-cache-dir -r requirements-server.txt \
    && groupadd --gid 10001 sanders \
    && useradd --uid 10001 --gid 10001 --no-create-home sanders \
    && mkdir /app/data && chown 10001:10001 /app/data

# Build directly from the source of record; preserve the original photos exactly once.
# The COPY set must cover the whole runtime import closure of wsgi.py
# (verified 2026-11-13): deploy/__init__.py + deploy/deployment.py and
# app/__init__.py + app/customer_app.py are required -- the earlier COPY
# set omitted them, so no image built from it could import wsgi.py at all.
# (.dockerignore must allow-list the same files; it does -- see there.)
COPY core_platform/ ./core_platform/
COPY web/ ./web/
COPY wsgi.py passenger_wsgi.py ./
COPY backend/ ./backend/
COPY deploy/ ./deploy/
COPY app/ ./app/

RUN touch /app/backend/__init__.py

# Gunicorn drops to uid/gid 10001 (see deploy/gunicorn.conf.py, and USER
# below): the copied code must be readable by that user regardless of the
# checkout's umask. A 660 checkout made the live smoke test fail with
# PermissionError on web/*.html and on stripe's lazy submodule imports.
# /app/data stays owned by 10001:10001 (created above) and writable.
RUN chmod -R a+rX /app

USER 10001:10001

EXPOSE 8000

STOPSIGNAL SIGTERM

CMD ["gunicorn", "--config", "deploy/gunicorn.conf.py", "wsgi:application"]
