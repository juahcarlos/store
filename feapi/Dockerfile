FROM harbor.bluemotion-packer.com/proxy_cache/library/python:3.9.14-slim

WORKDIR /app/

RUN pip --no-cache-dir install poetry==1.2.0 && poetry config virtualenvs.create false

WORKDIR /app/bluelib
COPY bluelib/pyproject.toml pyproject.toml
RUN poetry install --no-root

WORKDIR /app/feapi
COPY feapi/pyproject.toml pyproject.toml
RUN poetry install --no-root

WORKDIR /app/bluelib
COPY bluelib .
RUN poetry install

WORKDIR /app/feapi
COPY feapi .
RUN poetry install
