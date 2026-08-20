FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system taximobile && useradd --system --gid taximobile --home-dir /nonexistent --shell /usr/sbin/nologin taximobile

COPY requirements.lock requirements-linux.lock ./
RUN pip install --require-hashes --requirement requirements.lock --requirement requirements-linux.lock

COPY pyproject.toml README.md alembic.ini ./
COPY migrations ./migrations
COPY src ./src
RUN pip install --no-deps .

EXPOSE 8000
# Health is role- and orchestrator-specific: production Compose probes API/worker
# readiness separately, while managed staging probes the Render-assigned API port.
USER taximobile
CMD ["uvicorn", "taximobile_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
