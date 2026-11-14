# Clip2Easy backend image — used for both the API and the Celery workers.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
# FFmpeg/FFprobe are required for media probing and rendering.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
COPY alembic.ini start-single-node.sh ./
RUN pip install .

RUN useradd --create-home --uid 10001 app && mkdir -p /app/.data && chown -R app /app/.data
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -fsS http://localhost:8000/health || exit 1
# Default: single-node mode (migrations + API + worker in one container), e.g. Railway.
# docker-compose.yml overrides the command to run API and worker as separate services.
CMD ["bash", "start-single-node.sh"]
