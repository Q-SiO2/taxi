# TaxiMobile Backend

This is the Python FastAPI modular monolith specified in [`../docs/implementation.md`](../docs/implementation.md).

## Local foundation

1. Generate the ignored local environment with `../infra/scripts/new-local-env.ps1`.
2. On Windows, optionally run `setup-portable-python.ps1` for a verified
   Python 3.12 interpreter matching the production runtime line, then run
   `setup-portable-postgis.ps1` and
   `start-portable-stack.ps1` from `../infra/scripts/` for a checksum-pinned,
   workspace-contained PostGIS/API stack that does not require Docker.
3. Run `test-portable-backend.ps1` to apply every migration and execute the full
   suite against the isolated `taximobile_ci` PostGIS database.
4. Alternatively, use `../infra/compose.yaml`, or configure a direct PostGIS
   instance and run Alembic, Pytest, and Uvicorn from this directory.

The API exposes `/health`, `/ready`, `/api/v1/meta`, an authenticated best-effort live-event socket at `/api/v1/events`, and generated OpenAPI at `/api/v1/openapi.json`. The documented v1 contract includes accounts, passenger and driver profiles, driver availability/locations, rides and offers, fixed-tariff pricing, cash settlement, driver earnings, ratings, support tickets, notification history, administration, and audit records. Run `pytest` and `alembic upgrade head --sql` before declaring a backend change verified.

Local development and tests use `TAXIMOBILE_PROCESS_ROLE=all`, so the API owns
the bounded matching, outbox, and credential loops. Staging and production
default the public application to `api`; the deployment template explicitly
runs `taximobile_api.worker:app` with role `worker` as a separate process from
the same immutable image. The worker exposes only `/health`, `/ready`, and the
token-protected `/internal/metrics` operations surface—never public business API
routes.

`GET /internal/metrics` is an OpenAPI-hidden, Prometheus-compatible endpoint
protected by `TAXIMOBILE_MONITORING_TOKEN`. It exports bounded route-template,
status, latency, and safe exception-class metrics only. Staging and production
require the dedicated 32+ character token; additionally restrict the path at the
deployment network boundary.

Runtime and development installations use `--require-hashes`. The canonical
Windows-generated locks are `requirements.lock` and `requirements-dev.lock`;
Linux additionally consumes `requirements-linux.lock` for Uvicorn's
platform-specific event loop. The Linux supplement contains only reviewed
CPython 3.12 x86_64/aarch64 wheel hashes. CI also runs
`python -m pip_audit --no-deps --requirement requirements.lock`. Known published
vulnerabilities fail the build and must be reviewed rather than silently ignored.
CI and the portable backend test command also run
`../infra/scripts/validate_source_credentials.py`, which rejects committed
provider/signing files, private keys, service-account documents, and recognized
live-token formats without emitting matched values.

They also run `../infra/scripts/validate_mobile_api_contract.py`. This extracts
the actual handwritten Ktor method/path calls and compares them with FastAPI's
OpenAPI document, while checking `/api/v1/events` against the registered
WebSocket routes. Unknown client call shapes and unreviewed dynamic route
segments fail closed instead of silently escaping compatibility coverage.

Alembic reads the same `TAXIMOBILE_DATABASE_URL` as the API when it is set; the
URL in `alembic.ini` is only the local fallback. The opt-in
`tests/integration/test_mvp_lifecycle.py` test refuses to run unless
`TAXIMOBILE_ENV=test`, `TAXIMOBILE_RUN_INTEGRATION=1`, and the configured database
name contains `taximobile_ci`. CI provisions that isolated PostGIS database,
applies every migration, and then proves the complete registration-to-cash-
settlement lifecycle through HTTP.

The matching gate uses a versioned deterministic ranked policy rather than
nearest-only dispatch. Environment configuration controls the bounded candidate
set, proximity/idle/fairness weights, recent-assignment lookback, ETA assumption,
offer duration, and expiration poll. Declined and expired offers advance to an
untried candidate; exhausted searches end as `UNMATCHED` instead of remaining in
`MATCHING` indefinitely.

Development and isolated tests use an in-memory abuse limiter. Staging and
production automatically use migration-backed PostgreSQL buckets shared across
API instances. Only bucket-key digests are stored, and protected requests return
a safe `503` if the shared quota cannot be checked.

Selective outbox recovery is available through
`python -m taximobile_api.operations.outbox_replay`. It is intentionally not a
public API endpoint: operators must supply explicit reviewed event IDs, exact
target host/database confirmation, an incident reference, and the execution
switch. See `../infra/README.md` for the non-payload inspection procedure.

Routing is exposed only through the normalized authenticated API contract.
`TAXIMOBILE_ROUTING_PROVIDER` accepts exactly `valhalla` (the default) or
`graphhopper`; `TAXIMOBILE_ROUTING_BASE_URL` must identify the corresponding
private service. Mobile clients do not select an engine or parse provider-native
responses. A deployment must validate its pinned Morocco graph and narration
before promotion.

## Matching simulation

Evaluate the exact production ranking score against a deterministic synthetic
city before changing dispatch configuration:

```powershell
python -m taximobile_api.operations.matching_simulation `
  --seed 20260812 --drivers 100 --rides 1000
```

The command accepts search radius, candidate limit, policy weights, behavior
probabilities, and demand timing as explicit arguments. It emits aggregate JSON
for passenger wait, pickup time, driver idle time, completion/cancellation/
unmatched rates, ride-distribution Gini, utilization, and extreme cases. It does
not connect to the database or emit generated coordinates or participant IDs.

## Initial administrator

Administrator role assignment is never exposed by the public API. After applying
the migrations to a new database, create the one initial administrator from a
trusted operator terminal. The command asks for the password twice through a
hidden prompt; do not place it in an environment variable or shell history.

For the local Compose stack, from `infra/`:

```powershell
.\scripts\bootstrap-local-admin.ps1 -Email admin@example.com
```

For a directly configured backend environment:

```powershell
python -m taximobile_api.cli.bootstrap_admin --email admin@example.com --confirm-initial-admin
```

The command is idempotent only for the same existing initial administrator. It
refuses to create a second administrator or promote an existing ordinary account.
Later role management requires a separately authorized and audited workflow.

## Performance smoke test

Run the bounded GET-only harness against the local API:

```powershell
python -m taximobile_api.operations.performance_smoke `
  --base-url http://127.0.0.1:8000 --path /health `
  --requests 200 --concurrency 20 --p95-budget-ms 500
```

It exits nonzero when the error-rate or p95 latency budget is exceeded and emits
aggregate JSON suitable for CI artifacts. A non-local target is refused unless
`--confirm-nonlocal-target` is supplied; that flag confirms an authorized,
non-production staging target. For an authenticated read, load a short-lived
staging token into `TAXIMOBILE_PERF_BEARER_TOKEN` through the secret boundary.
The token, response bodies, and transport exception text are never printed.
