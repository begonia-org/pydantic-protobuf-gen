FROM python:3.11.10-slim

LABEL MAINTAINER="vforfreedom96@gmail.com"

WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --upgrade pip --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && python3 -m pip install poetry --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && python3 -m poetry config virtualenvs.create false \
    && python3 -m poetry install
