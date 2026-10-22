# Reviewed deployment candidate. A base-image digest must be recorded at release.
FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt requirements-server.txt ./
RUN python -m pip install --no-cache-dir -r requirements-server.txt \
    && groupadd --gid 10001 sanders \
    && useradd --uid 10001 --gid 10001 --no-create-home sanders \
    && mkdir /var/lib/sanders && chown 10001:10001 /var/lib/sanders
COPY core_platform/ ./core_platform/
COPY web/ ./web/
COPY wsgi.py wsgi.py.pbd.json ./
COPY deploy/gunicorn.conf.py deploy/gunicorn.conf.py.pbd.json ./deploy/
USER 10001:10001
EXPOSE 8000
STOPSIGNAL SIGTERM
CMD ["gunicorn", "--config", "deploy/gunicorn.conf.py", "wsgi:application"]
