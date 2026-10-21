FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY platform-source.json unpack.py ./
RUN python unpack.py && rm platform-source.json unpack.py \
    && python -m pip install --no-cache-dir -r requirements-server.txt \
    && groupadd --gid 10001 sanders \
    && useradd --uid 10001 --gid 10001 --no-create-home sanders \
    && mkdir /app/data && chown 10001:10001 /app/data
COPY wsgi.py wsgi.py.pbd.json ./
USER 10001:10001
EXPOSE 8000
STOPSIGNAL SIGTERM
CMD ["gunicorn", "--config", "deploy/gunicorn.conf.py", "wsgi:application"]
