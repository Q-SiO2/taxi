# Alpine supplies a materially smaller runtime than the Debian slim image and lets
# the release gate receive distribution security fixes without inheriting the
# unfixable Debian util-linux/perl findings. Keep this as a supported CPython
# image rather than a floating third-party runtime.
FROM python:3.12-alpine@sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apk upgrade --no-cache \
    && addgroup --gid 2000 --system taximobile \
    && adduser --uid 2000 --system --disabled-password --no-create-home --ingroup taximobile taximobile \
    && mkdir -p /var/lib/taximobile/driver-documents /var/log/taximobile \
    && chown -R taximobile:taximobile /var/lib/taximobile /var/log/taximobile \
    && chmod 0700 /var/lib/taximobile/driver-documents \
    && chmod 0750 /var/log/taximobile

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
