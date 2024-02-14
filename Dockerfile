FROM python:3.11-slim as builder

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    ffmpeg \
    pkg-config \
    portaudio19-dev \
    cmake \
    gcc \            
    python3-dev && \     
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir poetry

WORKDIR /app

COPY . .

RUN poetry config virtualenvs.create false && \
    poetry install --no-dev -vvv

FROM python:3.11-slim as base

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

WORKDIR /app

RUN echo '#!/bin/sh\n\
if [ -z "$CONFIG_FILE" ]; then\n\
  poetry run untitledai serve --host 0.0.0.0\n\
else\n\
  poetry run untitledai serve --host 0.0.0.0 --config "$CONFIG_FILE"\n\
fi' > /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]


