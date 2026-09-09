FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --gid 2000 taximobile && useradd --uid 2000 --gid taximobile --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin taximobile
RUN install -d -o taximobile -g taximobile -m 0700 /var/lib/taximobile/driver-documents
RUN install -d -o taximobile -g taximobile -m 0750 /var/log/taximobile

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
