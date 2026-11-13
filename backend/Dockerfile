# ClipMaker backend image — used for both the API and the Celery workers.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
# FFmpeg/FFprobe are required for media probing and rendering.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
COPY alembic.ini ./
RUN pip install .

RUN useradd --create-home --uid 10001 app && mkdir -p /app/.data && chown -R app /app/.data
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -fsS http://localhost:8000/health || exit 1
# Migrations run as a separate one-off step (see docker-compose.yml `migrate`).
CMD ["uvicorn", "clipmaker.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
