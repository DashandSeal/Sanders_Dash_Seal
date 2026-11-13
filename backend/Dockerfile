FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

# Build directly from the source of record; preserve the original photos exactly once.
COPY core_platform/ ./core_platform/
COPY web/ ./web/
COPY requirements.txt requirements-server.txt ./

COPY deploy/gunicorn.conf.py deploy/gunicorn.conf.py.pbd.json ./deploy/

RUN pip install --no-cache-dir -r requirements-server.txt \
    && groupadd --gid 10001 sanders \
    && useradd --uid 10001 --gid 10001 --no-create-home sanders \
    && mkdir /app/data && chown 10001:10001 /app/data

# Root entry point: backend/wsgi.py imports its factory from the root
# wsgi.py, so the root file must be present at /app/wsgi.py and this file
# must stay at /app/backend/wsgi.py (copying it over /app/wsgi.py would
# make `from wsgi import ...` a circular self-import).
COPY wsgi.py ./
COPY backend/wsgi.py backend/wsgi.py.pbd.json ./backend/
# Native runtime imports backend.auth_session for room-scoped WebRTC verification.
RUN mkdir -p /app/backend
COPY backend/auth_session.py /app/backend/auth_session.py
RUN touch /app/backend/__init__.py

USER 10001:10001

EXPOSE 8000

STOPSIGNAL SIGTERM

CMD ["gunicorn", "--config", "deploy/gunicorn.conf.py", "backend.wsgi:application"]
