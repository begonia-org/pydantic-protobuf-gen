FROM python:3.11.12-bookworm
ARG PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple/"
# Add parameter to control whether to use Tsinghua Ubuntu mirror
ARG USE_MIRROR_UBUNTU="true"
ARG DEFAULT_VENV=/opt/.uv.venv
ENV PYTHON_VERSION=3.11
WORKDIR /app
COPY . .
RUN if [ "$USE_MIRROR_UBUNTU" = "true" ]; then \
    sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources; \
    fi && \
    apt-get update && apt-get install -y --no-install-recommends gnupg ca-certificates apt-transport-https \
    git \
    curl \
    wget \
    protobuf-compiler libprotobuf-dev \
    && python3.11 -m pip install --upgrade pipx \
    && pipx install -i $PIP_INDEX_URL uv --global \
    && uv venv --seed $DEFAULT_VENV \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
ENV UV_LINK_MODE=copy \
    PIP_INDEX_URL=$PIP_INDEX_URL \
    VIRTUAL_ENV=$DEFAULT_VENV \
    UV_PROJECT_ENVIRONMENT=$DEFAULT_VENV \
    UV_PYTHON=$DEFAULT_VENV/bin/python3 \
    UV_INDEX=$PIP_INDEX_URL \
    UV_DEFAULT_INDEX=$PIP_INDEX_URL
RUN pip config set global.index-url $PIP_INDEX_URL && \
    pip config set global.trusted-host $(echo "$PIP_INDEX_URL" | sed -E 's|^https?://([^/]+).*|\1|') && \
    . $DEFAULT_VENV/bin/activate  && \
    uv sync -v --active --all-packages --default-index $PIP_INDEX_URL --index-strategy unsafe-best-match --prerelease=allow --no-build-isolation && \
    echo "/app" >> /opt/.uv.venv/lib/python${PYTHON_VERSION}/site-packages/pyskeleton.pth