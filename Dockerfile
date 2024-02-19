FROM python:3.11-slim as base

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    git \
    ffmpeg \
    pkg-config \
    libcairo2-dev \
    portaudio19-dev \
    libsndfile1 \
    libgomp1 \
    libjpeg-dev \
    libpng-dev \
    cmake && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir poetry && \
    poetry --version

ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

COPY . /app

RUN poetry config virtualenvs.create false && \
    poetry install -vvv && \
    rm -rf /root/.cache/pypoetry /root/.cache/pip

RUN echo '#!/bin/sh\n\
if [ -z "$CONFIG_FILE" ]; then\n\
  poetry run owl serve --host 0.0.0.0\n\
else\n\
  poetry run owl serve --host 0.0.0.0 --config "$CONFIG_FILE"\n\
fi' > /entrypoint.sh && \
    chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
