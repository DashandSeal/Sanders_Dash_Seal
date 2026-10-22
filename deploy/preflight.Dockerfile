FROM node:20.12.2-bookworm-slim AS node-runtime

FROM python:3.12-slim-bookworm AS validation
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/validation
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 libatomic1 git \
    && rm -rf /var/lib/apt/lists/*
COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node-runtime /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm
WORKDIR /validation
COPY requirements.txt requirements-server.txt ./
RUN python -m pip install --no-cache-dir -r requirements-server.txt
COPY . .
RUN cd worker && npm ci --ignore-scripts --no-audit \
    && groupadd --gid 10002 sds-validation \
    && useradd --uid 10002 --gid 10002 --no-create-home sds-validation
USER 10002:10002

FROM validation AS node-tests
WORKDIR /validation/worker
CMD ["npm", "test"]

FROM validation AS python-tests
WORKDIR /validation
CMD ["python", "-m", "unittest", "discover", "-s", "tests", "-v"]
