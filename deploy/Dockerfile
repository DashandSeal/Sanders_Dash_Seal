# Sanders Dash & Seal — real Dockerfile (systemd+gunicorn is the preferred
# deploy path; this image exists only as the Docker alternative).
# NOT BUILD-TESTED: no Docker daemon was available where this was written.
# Root Dockerfile in this repo is NOT a Dockerfile (230 lines of Python);
# do not use it. Build from the repo root:
#   docker build -f deploy/Dockerfile -t sanders-dash-seal:deploy .
#   docker run --rm -p 127.0.0.1:8000:8000 \
#     -e STRIPE_WEBHOOK_SECRET='whsec_...' -e STRIPE_LIVEMODE=false \
#     -v sanders-data:/app/data sanders-dash-seal:deploy
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 sanders \
    && useradd --uid 10001 --gid 10001 --no-create-home sanders \
    && mkdir -p /app/data && chown 10001:10001 /app/data

COPY wsgi.py passenger_wsgi.py ./
COPY core_platform/ ./core_platform/
COPY deploy/gunicorn.conf.py ./deploy/

USER 10001:10001

EXPOSE 8000

STOPSIGNAL SIGTERM

CMD ["gunicorn", "--config", "deploy/gunicorn.conf.py", "wsgi:application"]
