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
service, secret store, or alert-delivery provider. Those remain deployment-owner
decisions. The base manifest enforces the application boundaries; the optional
`compose.monitoring.yaml` overlay supplies a no-license-cost self-hosted
Prometheus, Alertmanager, Loki, Alloy, and Grafana path without making any of
those services public.

## Required inputs

Set deployment values through the host/orchestrator secret and configuration
boundary. In particular:

* `TAXIMOBILE_API_IMAGE` must be an immutable registry reference containing an
  `@sha256:` digest, not `latest` or a mutable tag.
* `TAXIMOBILE_CLAMAV_IMAGE` must likewise be an immutable reviewed image digest.
  ClamAV is private, has no host port, and receives neither document ciphertext
  nor its encryption key at rest; uploads are streamed to it before persistence.
* `TAXIMOBILE_DATABASE_URL` points to migrated managed PostgreSQL/PostGIS and is
  never exposed to mobile clients. `TAXIMOBILE_DATABASE_POOL_SIZE`,
  `TAXIMOBILE_DATABASE_POOL_MAX_OVERFLOW`, and
  `TAXIMOBILE_DATABASE_POOL_TIMEOUT_SECONDS` are explicit per-process bounds.
  Before changing replicas, prove `(pool size + maximum overflow) * replica count`
  fits the server connection budget with migration, monitoring, maintenance and
  emergency reserve.
* JWT and monitoring tokens are independent 32+ character secrets. Only the API
  receives the JWT signing secret; the worker receives the monitoring token and
  workload identity needed for its private operations and FCM delivery.
* `TAXIMOBILE_OPERATIONS_MFA_ENCRYPTION_KEY` is an independent, base64url-
  encoded 32-byte secret supplied only to the API. The production manifest
  forces `TAXIMOBILE_OPERATIONS_SECURE_COOKIE_ENABLED=true`; do not override it.
* `TAXIMOBILE_DRIVER_DOCUMENT_ENCRYPTION_KEY` is a different base64url 32-byte
  secret supplied to API and worker. Both mount the same private document volume;
  only ClamAV mounts its signature volume. Back up ciphertext and key through
  separate protected channels and exercise restore and key recovery before use.
* `TAXIMOBILE_CORS_ORIGINS` contains only reviewed exact HTTPS browser origins.
  Host the operations web and API on the same registrable site (for example
  `operations.example.ma` and `api.example.ma`) or behind one reverse proxy so
  the strict refresh cookie can be sent. Unrelated-site hosting fails closed.
* `TAXIMOBILE_ROUTING_PROVIDER` is exactly `valhalla` or `graphhopper`, and
  `TAXIMOBILE_ROUTING_BASE_URL` is the corresponding private production service.
  Valhalla is the default architecture choice; selecting GraphHopper requires its
  own pinned Morocco graph and route/narration acceptance evidence.
* Geocoding stays fail-closed with `TAXIMOBILE_GEOCODING_PROVIDER=disabled` until
  provider, data-license, privacy, capacity, multilingual quality and field
  acceptance are recorded. Enabling `nominatim` requires a reviewed HTTPS
  `TAXIMOBILE_GEOCODING_BASE_URL`, identifying user agent, bounded timeout and
  explicit search/reverse limits. Production startup rejects the shared public
  Nominatim host; geocoding configuration belongs only to the API process.
* `TAXIMOBILE_FIREBASE_PROJECT_ID` identifies the production Firebase project;
  FCM authorization comes from workload identity/application default credentials.
  FCM and Crashlytics are no-cost Spark-plan products; this deployment does not
  add metered Firebase database, function, storage, hosting, phone-auth, or
  Analytics services.
* Manual bank/M-Wallet transfer is disabled unless
  `TAXIMOBILE_MANUAL_TRANSFER_ENABLED=true`,
  `TAXIMOBILE_TRANSFER_RECIPIENT_NAME` is verified, and at least one of
  `TAXIMOBILE_TRANSFER_BANK_ACCOUNT` or `TAXIMOBILE_TRANSFER_WALLET_ID` is set.
  These API-only values come from protected deployment configuration and are a
  single-recipient pilot surface, not the national multi-operator model.
* `TAXIMOBILE_TRUSTED_PROXY_CIDRS` contains only the actual TLS proxy addresses.
* Monitoring deployments require digest-pinned `TAXIMOBILE_PROMETHEUS_IMAGE`,
  `TAXIMOBILE_ALERTMANAGER_IMAGE`, `TAXIMOBILE_GRAFANA_IMAGE`,
  `TAXIMOBILE_LOKI_IMAGE`, and `TAXIMOBILE_ALLOY_IMAGE` values.
  Pinning must follow image/security review; do not copy the parser-test versions
  from CI without that review.
* `TAXIMOBILE_MONITORING_TOKEN_FILE` contains the exact same 32+ character value
  as `TAXIMOBILE_MONITORING_TOKEN`. Prometheus reads the file as a Docker secret;
  API and worker continue to read the deployment secret environment value.
* Platform-duty, dispatch, scheduling and driver-compliance webhook URL file
  variables each identify a protected file containing one absolute HTTPS URL.
  The URL is never committed or placed directly in Alertmanager YAML. Receivers
  may initially point to the same staffed endpoint, but ownership and backup
  escalation must still be recorded explicitly.
* `TAXIMOBILE_GRAFANA_ADMIN_PASSWORD_FILE` identifies a protected file containing
  a unique 20+ character administrator password with upper, lower, numeric and
  special characters and no quote or backslash characters. It must not equal any
  application, monitoring, pager or MFA secret. Grafana consumes this file only
  when its database creates the
  initial administrator; replacing the file does **not** rotate an account in an
  existing Grafana volume. Record and rehearse the approved in-product/admin-CLI
  rotation and active-session revocation procedure before field use.

The API is bound to host loopback so a same-host TLS reverse proxy is the only
public ingress. API and background worker use the same immutable image but
different closed process roles. Both containers are read-only, drop Linux
capabilities, disallow privilege escalation, and use the unprivileged image user.
The API runs one Uvicorn process and never owns durable processor loops in
production. The separate worker owns matching, outbox, credential lifecycle,
scheduling handoff, privacy-bounded analytics refresh, durable case-alert paging,
legal-hold-aware case retention, and driver-document erasure loops and exposes only authenticated operations endpoints on host loopback port
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
requires its supervisor and one successful matching, outbox, credential,
scheduling, analytics, case-alert, case-retention, and driver-document-retention
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
Manual-transfer recipient settings belong only to the API, which advertises and
snapshots them; the worker has no reconciliation or statement capability.

`prometheus-alerts.yaml` supplies provider-neutral initial rules for unhandled
errors, sustained 5xx ratio, the documented 500 ms p95 latency budget, unavailable
outbox and PostgreSQL snapshots, high database connection utilization, waiting
locks, deadlocks, outbox dead letters/delivery stalls, and failed or stalled matching
outbox, credential-lifecycle, scheduling, analytics, case-alert, case-retention,
and driver-document-retention worker loops. It also detects missing API, worker,
Loki, or Alloy targets, rejected log lines, and collector retry/drop failures.
Load it only into the
restricted monitoring deployment that scrapes TaxiMobile replicas. The deployment
also alerts when the standalone worker series disappear entirely; API-only
processes intentionally omit worker series so they cannot mask a failed worker
scrape with zero-valued placeholders. The deployment
owner must route `warning` and `critical` severities to named responders and add a
separate authenticated or network-restricted probe for `/ready`; Prometheus alert
rules cannot infer that deployment-specific probe label. CI validates the rule
shape and required alert set. The staging monitoring stack must additionally run
`promtool check rules` (or its managed-service equivalent) before promotion.

### Self-hosted monitoring overlay

`prometheus.yaml`, `alertmanager.yaml`, `loki.yaml`, `alloy/config.alloy`, the files under `grafana/`, and
`compose.monitoring.yaml` implement the repository-owned collector, routing and
diagnostic-dashboard baseline. Prometheus scrapes the API, worker, Loki, and
Alloy. It reaches the API and
private worker through a dedicated internal-only network and reads the bearer
credential from `/run/secrets`; every operator port binds only to host loopback.
Prometheus has no external network. Alertmanager alone also joins a dedicated
alert-egress bridge so it can reach the configured HTTPS receivers; no
application, worker, collector or dashboard joins that egress network.
Alertmanager groups by alert name and fixed operational owner, routes the three
known owner classes independently, sends `unclassified` and all non-owner alerts
to platform duty, bounds webhook batches, and emits resolved notifications.
Prometheus removes user/driver/passenger/device/ride/resource/authorization/
payload/topic labels before an alert can leave the collector. This is defense in
depth; emitting those labels remains forbidden at source.
Grafana has immutable internal Prometheus and Loki datasources plus two file-
provisioned dashboards. The 26-panel `TaxiMobile Operations` dashboard covers target
health, HTTP rate/error/latency, fixed-worker progress/errors, outbox visibility,
owner backlog/age/dead letters, database snapshot/connection/lock/deadlock state,
per-process pool availability/checked-out/overflow state, checkout-wait p95 and
checkout timeouts, legacy-administration served/blocked attempts,
and normalized unhandled-error classes. It has no
anonymous access, signup, telemetry, update checks, plugin downloads or Grafana-
managed alerting. The three-panel `TaxiMobile Logs` dashboard shows bounded API/
worker volume, query-time error level, and recent structured events. Neither
dashboard contains variables or external links; each can query only its reviewed
low-cardinality vocabulary.

API and worker write allowlisted JSON lines to separate named volumes. The
application image owns both paths as UID/GID `2000`; active and rotated files are
mode `0640`, default to 10 MiB each, and retain five backups. Alloy runs as UID
`473` with only supplemental group `2000`, mounts both role volumes read-only,
and has no Docker socket, host-log directory, remote configuration, or outbound
egress beyond internal Loki. It rejects malformed JSON and lines over 16 KiB,
extracts event time, and indexes only fixed `service=api|worker`. Loki runs as
UID `10001` in single-binary filesystem mode with one private volume, TSDB v13,
30-day ingestion/query/retention limits, and compactor retention. Loki has no
authentication layer, so its internal network and loopback operator port are
mandatory boundaries.

This file-volume topology supports one API and one worker container on the
provider-neutral single host. Do not use `docker compose --scale` with these
shared role files. A multi-replica orchestrator must give each replica its own
application-owned volume and local collector/sidecar, or an equivalently isolated
reviewed transport, while preserving the JSON allowlist, fixed labels, size/
retention bounds, and internal-only store.

Create secret files outside the repository—`infra/deploy/secrets/` is ignored as
a last-resort local path—and export these paths without printing their contents:

```text
TAXIMOBILE_MONITORING_TOKEN_FILE=<protected monitoring-token file>
TAXIMOBILE_GRAFANA_ADMIN_PASSWORD_FILE=<protected Grafana administrator password file>
TAXIMOBILE_PLATFORM_ALERT_WEBHOOK_URL_FILE=<protected HTTPS URL file>
TAXIMOBILE_DISPATCH_ALERT_WEBHOOK_URL_FILE=<protected HTTPS URL file>
TAXIMOBILE_SCHEDULING_ALERT_WEBHOOK_URL_FILE=<protected HTTPS URL file>
TAXIMOBILE_DRIVER_COMPLIANCE_ALERT_WEBHOOK_URL_FILE=<protected HTTPS URL file>
```

Validate actual secret-file parity, all five immutable monitoring images, the
merged Compose model, Prometheus rules, Alertmanager routes, Loki and Alloy native
configuration, both dashboard privacy contracts, disposable hardened Grafana,
real Loki/Alloy HTTP readiness, application-volume ownership, and bounded two-
role ingestion with the same pinned images that will run in the environment:

```powershell
.\infra\scripts\validate-monitoring-runtime.ps1
```

Then start the application and monitoring services together:

```powershell
docker compose `
  --env-file <deployment-env> `
  -f infra/deploy/compose.production.yaml `
  -f infra/deploy/compose.monitoring.yaml `
  up -d api worker loki alloy alertmanager prometheus grafana
```

Use Grafana only from host loopback or an approved authenticated operator tunnel
at `http://127.0.0.1:${TAXIMOBILE_GRAFANA_PORT:-3000}` and sign in as
`taximobile-admin` with the protected password. Do not publish the port or place
this HTTP listener directly on a shared network. A real environment must define
its authenticated TLS access path, named staff accounts/least privilege, session
expiry and credential recovery before operators rely on it.

The fixed internal API host is accepted by the application only so Prometheus can
scrape across the internal network. The TLS reverse proxy must reject that host
on public ingress. Prometheus data, Alertmanager notification state, Loki chunks/
index/WAL, Alloy read positions, and Grafana account/preferences state use
separate named volumes; the committed dashboards remain file-provisioned. Define
backup, restore, capacity, and retention requirements before
relying on any volume for incident evidence. The software has no license fee, but
consumes host CPU, memory and disk. It does not close GAP-015 until target uptime,
dashboard correctness, secure staff access, receiver delivery, primary/backup
acknowledgement and failure-injection drills pass in staging.

## Controlled release

Start from a reviewed clean commit. Validate documentation and generate the
source-candidate evidence record before building or promoting artifacts:

```powershell
python .\infra\scripts\validate_docs.py
python -m unittest discover -s .\infra\scripts\tests -p 'test_*.py'
python .\infra\scripts\generate_release_evidence.py `
  --label <release-candidate-label> `
  --output <protected-evidence-directory>\source-evidence.json
```

The evidence command fails on modified or untracked files. `--allow-dirty` is
only for a visibly labeled `WORKSPACE_SNAPSHOT`; that output is never a release
candidate. Source evidence records identity and hashes, not city, provider,
security, legal, payment, device, or real-user acceptance.

Build and package the public applicant/operations web compatibility distribution
without public source maps:

```powershell
.\TaxiMobile\gradlew.bat --no-daemon -p .\TaxiMobile `
  :webApp:jsBrowserTest `
  :webApp:wasmJsBrowserTest `
  :webApp:composeCompatibilityBrowserDistribution
python .\infra\scripts\package_web_release.py `
  --input .\TaxiMobile\webApp\build\dist\composeWebCompatibility\productionExecutable `
  --output <new-empty-output-directory>
```

The package command validates the compatibility loader, rejects remote or inline
boot resources, enforces the reviewed JS/Wasm/total raw-size ceilings, excludes
browser source maps, and writes `release-manifest.json` with every packaged file
hash. Configure the hosting layer from that manifest's requirements, replacing
the CSP template's broad HTTPS/WebSocket connection class with the exact API and
live-event hosts. Do not publish a Gradle distribution directory directly.

First render and review the fully resolved manifest without printing it into a
public CI log when it contains secrets:

```powershell
.\infra\scripts\validate-production-inputs.ps1
python .\infra\scripts\validate_production_compose.py
docker compose --env-file <deployment-env> -f infra/deploy/compose.production.yaml config --quiet
```

When the monitoring overlay is part of the candidate, run
`validate-monitoring-runtime.ps1` instead of the first command and render both
Compose files together. The runtime validator executes `promtool`, `amtool`, Loki
config verification, and Alloy validation from the exact digest-pinned images;
it provisions both dashboards and runs a disposable two-stream ingestion smoke.
It does not send an alert or satisfy hosted acceptance.

Back up the managed database and verify the restore procedure. Apply migrations
as a distinct release operation before changing the API image:

```text
docker compose --env-file <deployment-env> -f infra/deploy/compose.production.yaml run --rm migrate
```

The migration job uses a fail-fast database advisory lock: overlapping executors
are refused before schema work. Do not start API/worker rollout after a nonzero
migration exit. Keep one controlled migrator and investigate its result before a
bounded retry; never edit version rows or automatically terminate other sessions.

The migration service alone receives these optional non-secret controls:

| Variable | Default | Allowed value |
| --- | --- | --- |
| `TAXIMOBILE_MIGRATION_LOCK_TIMEOUT_SECONDS` | 5 | Whole seconds, 1–120 |
| `TAXIMOBILE_MIGRATION_STATEMENT_TIMEOUT_SECONDS` | 300 | Whole seconds, 1–7200, greater than lock timeout |

Unset values use defaults; empty/malformed/zero/out-of-range values are refused.
Limits apply per lock wait and per statement within the migration transaction,
not to total job duration, connection setup or idle Python work. Supply an outer
orchestrator deadline and measure settings against a production-like dataset
before rollout. A lock timeout means review blockers/maintenance; statement
cancellation means review load and the migration plan. Do not blindly raise the
limits or restart-loop a failed migration. Generated offline SQL contains the
same transaction-local limits and ownership guard; execute it intact as one
transaction with stop-on-error enabled (for `psql`, `-v ON_ERROR_STOP=1`).

On the first deployment, create the single bootstrap administrator and map its
reviewed market-scoped grant. Register and independently verify two additional
active staff accounts, add them as the second and third initial quorum members,
then enroll MFA for all three from a trusted interactive terminal:

```text
docker compose --env-file <deployment-env> -f infra/deploy/compose.production.yaml run --rm api taximobile-bootstrap-admin --email operator@example.ma --confirm-initial-admin
docker compose --env-file <deployment-env> -f infra/deploy/compose.production.yaml run --rm api taximobile-bootstrap-operations --admin-email operator@example.ma --market-code MA --confirm-market-scope
docker compose --env-file <deployment-env> -f infra/deploy/compose.production.yaml run --rm api taximobile-bootstrap-operations-quorum --user-email operator-b@example.ma --market-code MA --change-reference CHG-INITIAL-QUORUM-B --confirm-initial-quorum
docker compose --env-file <deployment-env> -f infra/deploy/compose.production.yaml run --rm api taximobile-bootstrap-operations-quorum --user-email operator-c@example.ma --market-code MA --change-reference CHG-INITIAL-QUORUM-C --confirm-initial-quorum
docker compose --env-file <deployment-env> -f infra/deploy/compose.production.yaml run --rm api taximobile-enroll-operations-mfa --email operator@example.ma --confirm-enrollment
docker compose --env-file <deployment-env> -f infra/deploy/compose.production.yaml run --rm api taximobile-enroll-operations-mfa --email operator-b@example.ma --confirm-enrollment
docker compose --env-file <deployment-env> -f infra/deploy/compose.production.yaml run --rm api taximobile-enroll-operations-mfa --email operator-c@example.ma --confirm-enrollment
```

The first command prompts twice for the password; enrollment prints a provisioning
URI and then the recovery codes exactly once. Use a private terminal, save codes
offline, and record the reviewer/owner without copying any secret into release
logs. Factor recovery requires the same command with `--replace-existing` only
after the security-owner identity check; replacement revokes all sessions. The
quorum command audits its external change reference, creates only members two and
three, and permanently closes after the third administrator. Every later grant
creation/revocation uses the maker-checker operations queue; staging and
production reject direct grant mutation, and platform-admin revocation cannot
leave fewer than two active non-expired administrators.

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
