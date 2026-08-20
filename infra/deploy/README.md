# TaxiMobile production deployment contract

For managed pre-production user testing, use
[`RENDER_STAGING.md`](RENDER_STAGING.md) and the separate
[`render.staging.yaml`](render.staging.yaml) Blueprint. That topology preserves
the API/worker/database/routing boundaries here while using Render-generated
staging secrets and private networking. It is not the production manifest and
must not be promoted by changing `TAXIMOBILE_ENV`.

When no testing budget exists, the isolated temporary alternative is documented
in [`RENDER_FREE_TESTING.md`](RENDER_FREE_TESTING.md) and
[`render.free-testing.yaml`](render.free-testing.yaml). It combines API and
workers on one sleeping free web instance and uses public fair-use Valhalla, so
it is restricted to small synthetic tests and expires with the free database.

This directory is a provider-neutral single-host Linux deployment template. It
does not choose a registry, cloud, DNS provider, TLS proxy, managed PostgreSQL
service, secret store, or monitoring platform. Those remain deployment-owner
decisions. The template does enforce the repository's application boundaries.

## Required inputs

Set deployment values through the host/orchestrator secret and configuration
boundary. In particular:

* `TAXIMOBILE_API_IMAGE` must be an immutable registry reference containing an
  `@sha256:` digest, not `latest` or a mutable tag.
* `TAXIMOBILE_DATABASE_URL` points to migrated managed PostgreSQL/PostGIS and is
  never exposed to mobile clients.
* JWT and monitoring tokens are independent 32+ character secrets. Only the API
  receives the JWT signing secret; the worker receives the monitoring token and
  workload identity needed for its private operations and FCM delivery.
* `TAXIMOBILE_ROUTING_PROVIDER` is exactly `valhalla` or `graphhopper`, and
  `TAXIMOBILE_ROUTING_BASE_URL` is the corresponding private production service.
  Valhalla is the default architecture choice; selecting GraphHopper requires its
  own pinned Morocco graph and route/narration acceptance evidence.
* `TAXIMOBILE_FIREBASE_PROJECT_ID` identifies the production Firebase project;
  FCM authorization comes from workload identity/application default credentials.
* `TAXIMOBILE_TRUSTED_PROXY_CIDRS` contains only the actual TLS proxy addresses.

The API is bound to host loopback so a same-host TLS reverse proxy is the only
public ingress. API and background worker use the same immutable image but
different closed process roles. Both containers are read-only, drop Linux
capabilities, disallow privilege escalation, and use the unprivileged image user.
The API runs one Uvicorn process and never owns durable processor loops in
production. The separate worker owns matching, outbox, and credential lifecycle
loops and exposes only authenticated operations endpoints on host loopback port
`${TAXIMOBILE_WORKER_PORT:-8001}`. Horizontal API replicas share abuse quotas
and minimized WebSocket refresh hints through private PostgreSQL; monitoring must
scrape API and worker separately. Rides, fares, payments, and authorization never
move into pub/sub.

Compose health for both long-running containers is readiness-based. The API
probe requires PostgreSQL through `/ready` and sends the first exact
`TAXIMOBILE_ALLOWED_HOSTS` entry as its HTTP `Host`, so the same production host
filter that protects public traffic does not reject an otherwise valid loopback
probe. Wildcard, URL-shaped, port-bearing, and malformed allowed-host values are
rejected before startup. The worker probe additionally
requires its supervisor and one successful matching, outbox, and credential
lifecycle iteration. `/health` remains a process-liveness diagnostic and must
not be substituted into the container healthchecks. The worker receives a longer
startup allowance so a normal first database iteration is not treated as a
restart-worthy failure. CI validates these probe targets together with loopback
ports, process-role separation, least-privilege environment boundaries, and
container hardening before it renders the manifest with Docker Compose.

The Compose environment anchors enforce least privilege: the worker is not given
the API JWT secret, public host/CORS policy, or routing endpoint, while the API is
not given the Firebase project configuration used by push delivery. Both receive
only the database, monitoring, and matching policy required by their roles.

`prometheus-alerts.yaml` supplies provider-neutral initial rules for unhandled
errors, sustained 5xx ratio, the documented 500 ms p95 latency budget, unavailable
outbox snapshots, dead letters, delivery stalls, and failed or stalled matching
outbox, and credential-lifecycle worker loops. Load it only into the
restricted monitoring deployment that scrapes TaxiMobile replicas. The deployment
also alerts when the standalone worker series disappear entirely; API-only
processes intentionally omit worker series so they cannot mask a failed worker
scrape with zero-valued placeholders. The deployment
owner must route `warning` and `critical` severities to named responders and add a
separate authenticated or network-restricted probe for `/ready`; Prometheus alert
rules cannot infer that deployment-specific probe label. CI validates the rule
shape and required alert set. The staging monitoring stack must additionally run
`promtool check rules` (or its managed-service equivalent) before promotion.

## Controlled release

First render and review the fully resolved manifest without printing it into a
public CI log when it contains secrets:

```powershell
.\infra\scripts\validate-production-inputs.ps1
python .\infra\scripts\validate_production_compose.py
docker compose --env-file <deployment-env> -f infra/deploy/compose.production.yaml config --quiet
```

Back up the managed database and verify the restore procedure. Apply migrations
as a distinct release operation before changing the API image:

```text
docker compose --env-file <deployment-env> -f infra/deploy/compose.production.yaml run --rm migrate
```

Then start/update the API and run the non-mutating verification from a trusted
operator machine:

```powershell
docker compose --env-file <deployment-env> -f infra/deploy/compose.production.yaml up -d api worker
$env:TAXIMOBILE_MONITORING_TOKEN = <load-from-secret-store>
.\infra\scripts\verify-deployment.ps1 `
  -ApiBaseUrl https://api.example.ma `
  -WorkerBaseUrl http://127.0.0.1:8001 `
  -ConfirmAuthorizedTarget
```

Before routing traffic to a newly built graph or routing-service version, run the
fixed-scenario gate from the same trusted network. A non-local target requires an
exact hostname confirmation; do not put credentials in the URL:

```powershell
taximobile-routing-acceptance `
  --provider graphhopper `
  --base-url http://routing.internal.example:8989 `
  --confirm-host routing.internal.example
```

Promotion requires exit code `0`. The bounded JSON report contains scenario IDs
and stable failure codes only. Archive it with the selected engine version, graph
artifact checksum, OSM extract date/source, and review approval; it does not by
itself prove MapLibre tile/style acceptance or mobile-device navigation.

Do not put secret values into committed files, shell history, screenshots, or
support tickets.

## Rollback

Keep the previous API image digest and its compatibility assessment before every
rollout. If post-deployment verification fails, stop routing traffic to the new
container and restore the previous image digest only when it is compatible with
the already-applied schema. Never run an automatic Alembic downgrade and never
restore an old database backup over new production facts merely to roll back code.
If the schema is not backward compatible, follow the migration's reviewed forward
repair plan. Re-run health, readiness, API identity, metrics, and a controlled
staging lifecycle before restoring public traffic.
