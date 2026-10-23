FROM python:3.11-slim-bookworm
WORKDIR /function
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 sanders \
    && useradd --uid 10001 --gid 10001 --no-create-home sanders
COPY integrated.py ./
USER 10001:10001
ENTRYPOINT ["/usr/local/bin/fdk", "/function/integrated.py", "handler"]
