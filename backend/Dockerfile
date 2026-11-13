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

COPY backend/wsgi.py backend/wsgi.py.pbd.json ./
# Native runtime imports backend.auth_session for room-scoped WebRTC verification.
RUN mkdir -p /app/backend
COPY backend/auth_session.py /app/backend/auth_session.py
RUN touch /app/backend/__init__.py

# Level 10 Sovereign Core Platform Additions
COPY core_platform.py ./core_platform.py
COPY security/sovereign_runtime.py ./security/sovereign_runtime.py
RUN chmod +x /app/core_platform.py && chmod +x /app/security/sovereign_runtime.py

USER 10001:10001

EXPOSE 8000

STOPSIGNAL SIGTERM

CMD ["gunicorn", "--config", "deploy/gunicorn.conf.py", "wsgi:application"]
