FROM python:3.13-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app/minerva

RUN pip install --no-cache-dir -e /app/minerva && \
    pip install --no-cache-dir -e /app/minerva/extractors/repository-doc-extractor && \
    pip install --no-cache-dir -e /app/minerva/extractors/github-webhook-orchestrator

RUN mkdir -p /data/chromadb /data/repos /data/extracted /data/config /data/logs

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8337/health || exit 1

EXPOSE 8337 8338

WORKDIR /app/minerva

CMD ["/app/minerva/deployment/entrypoint.sh"]
