# TaxiMobile Infrastructure

This directory holds reproducible portable/Compose local infrastructure and
deployment configuration. Its required boundaries, environment rules, and
rollout requirements are defined in
[`../docs/implementation.md`](../docs/implementation.md).

Copy `.env.example` to `.env` before using `compose.yaml`. `.env` contains a local development password and is ignored by Git. No provider credentials, production configuration, or live data belongs here.

## Starting the local stack

Generate the ignored `.env` file and its local-only secrets once:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\new-local-env.ps1
```

There are two supported local database paths.

### Windows portable stack (no Docker)

The portable path downloads pinned PostgreSQL 16.14 and PostGIS 3.5.3 archives,
verifies their SHA-256 checksums, and installs them only under the workspace
`.tools/` directory. It neither requires administrator rights nor changes system
software. The workspace-local `backend/.venv` must already contain the locked
backend dependencies.

For interpreter parity with the production Python 3.12 line, set up the optional
checksum-pinned Python 3.12.10 embeddable development runtime. Its wheels come
from the hash-enforced `backend/requirements.lock`; the setup refuses packages
whose artifacts do not match the lock. It is not a production distribution and
the container remains the release runtime:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-portable-python.ps1
```

Run database setup once, then start the database, apply migrations, and launch
the API. Startup prefers the verified portable Python marker and otherwise falls
back to `backend/.venv`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-portable-postgis.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-portable-stack.ps1
```

Exercise all unit/API tests and the full migrated PostGIS lifecycle with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test-portable-backend.ps1
```

This entry point first runs `validate_source_credentials.py`. In CI the validator
uses Git-tracked files; in this no-Git workspace it deliberately does not read the
ignored `infra/.env`, `TaxiMobile/local.properties`, builds, caches, backups, or
generated environments. Findings report only a relative path and rule name, never
the matching value.

It then runs `validate_mobile_api_contract.py`, which extracts the real
handwritten Kotlin gateway operations and proves that every HTTP method/path is
present in FastAPI OpenAPI. The live-event WebSocket is checked against the
application route table because OpenAPI does not represent WebSockets. A new
unparsed client call or unreviewed dynamic route segment stops the suite.

The test script uses only the isolated `taximobile_ci` database. It starts and
stops PostgreSQL itself when the development stack is not already running. Stop
the development API and database with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\stop-portable-stack.ps1
```

Runtime data, logs, process metadata, and downloaded archives remain beneath
`.tools/`. Credentials remain in the ignored `infra/.env` and are not printed.

### Local UX demo data

With the portable development API running, create an additive synthetic UX
dataset with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\seed-ux-demo.ps1 -ConfirmLocalDemoData
```

The two-step guard allows only `TAXIMOBILE_ENV=development` with loopback
PostgreSQL. Each invocation creates new accounts instead of deleting or rewriting
existing data. It prints one generated password and four unique local-only
emails: rich passenger, approved active driver, pending driver application, and
empty passenger. The rich pair shares an en-route ride and has completed rides,
cash receipt states, notifications, support tickets, a verified vehicle and
credential, cooperative membership, rating, and settled earnings. These are
synthetic review records—not migration seeds or production fixtures.

### Docker Compose stack

With Docker Desktop installed and running, start and health-check all services
with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-local-stack.ps1
```

The default command starts PostgreSQL/PostGIS and the API without downloading a
routing dataset. Select exactly one engine to download the configured dated
Morocco OSM extract into its own named volume, build a graph, and verify a real
Casablanca route. Valhalla 3.8.3 remains the default architecture choice:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-local-stack.ps1 `
  -RoutingProvider valhalla -WaitTimeoutSeconds 3600
```

The backward-compatible `-WithRouting` switch selects Valhalla, but new commands
should name the provider. GraphHopper 11.0 is the approved Arabic-capable path and
can run the full graph/catalog acceptance gate during startup:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-local-stack.ps1 `
  -RoutingProvider graphhopper -RunRoutingAcceptance -WaitTimeoutSeconds 3600
```

Both alternatives expose the same host-loopback port `8002`; this makes accidental
dual-profile activation fail instead of leaving two routing engines running. Their
private container ports remain provider-native, and mobile clients never see
either service.

The first graph build is CPU-, memory-, disk-, and network-intensive. It is
triggered only by an explicit provider selection; ordinary local startup never
silently downloads map data. Both provider URLs must be credential-free HTTPS
URLs naming a dated extract rather than mutable `latest`. GraphHopper additionally
requires the exact lowercase `GRAPHHOPPER_OSM_SHA256`; its download, graph cache,
and image JAR are checksum-addressed. The checked-in example uses Geofabrik's
dated Morocco extract.
Existing ignored `.env` files created before the GraphHopper profile was added
need only the two non-secret `GRAPHHOPPER_OSM_*` lines copied from `.env.example`;
do not recreate or disclose the existing generated secrets. Validate the
committed routing infrastructure without downloading or starting either engine:

```powershell
.\backend\.venv\Scripts\python.exe .\infra\scripts\validate_local_routing.py
```
Review OpenStreetMap/Geofabrik attribution and ODbL obligations before publishing
or redistributing any derived graph artifact. Production should build, checksum,
scan, version, and promote a graph artifact separately rather than downloading
mutable `latest` data during application rollout.

The provider startup check above proves only that one English route can be
returned. Before a graph artifact or routing service is promoted, run the provider-neutral release
gate from the repository root. It exercises three fixed public Morocco routes
through the real adapter in every required application language and validates
route plausibility, geometry bounds, endpoint snapping, maneuver indices, and
localized narration:

```powershell
.\backend\.venv\Scripts\python.exe -m taximobile_api.operations.routing_acceptance `
  --provider valhalla --base-url http://127.0.0.1:8002
```

For an authorized private staging host, add `--confirm-host` with that exact
hostname. The command accepts no user coordinates and outputs no target URL,
geometry, instructions, provider response, or exception detail. Exit code `0`
means every check passed, `1` means the graph/catalog failed acceptance, and `2`
means the command or target guard was invalid. The pinned Valhalla catalog is
expected to fail the required Arabic narration check; this is an explicit release
gap, not permission to record English fallback as Arabic. A GraphHopper candidate
must pass the same command with `--provider graphhopper` and its own accepted,
versioned Morocco graph.

The generated file is never printed, never overwrites an existing `.env`, and
is ignored by Git. The execution-policy bypass applies only to that PowerShell
process; it does not change the machine's execution policy. Both startup paths
remain workspace-scoped. The Compose script reports a missing or stopped Docker
engine explicitly. For a USB-connected Android test device, leave the API bound
to the development computer and run
`adb reverse tcp:8000 tcp:8000` before opening a debug app built with
`http://127.0.0.1:8000`.

The environment generator also creates a dedicated monitoring bearer token without
printing it. `GET /internal/metrics` requires that token and should be scraped only
from a restricted monitoring network. Staging and production require a separate
32+ character `TAXIMOBILE_MONITORING_TOKEN`; it must not be reused as the JWT,
database, Firebase, or CMI secret.

The matching radius, location freshness, candidate limit, idle cap, fairness
lookback, assumed pickup speed, score weights, algorithm version, processor poll
interval, overall matching timeout, offer duration, and abuse limits are
centralized in `.env`. Bounds,
non-negative weights, a positive total weight, and a safe version label are
validated at API startup rather than permitting disabled or ambiguous dispatch.
Changing weights or their meaning requires a new reviewed algorithm version and
staging simulation/device acceptance.

Professional credential expiry scanning is configured separately with
`TAXIMOBILE_CREDENTIAL_POLL_SECONDS` (1–300) and
`TAXIMOBILE_CREDENTIAL_EXPIRY_WARNING_DAYS` (1–365). Local defaults are 60
seconds and 30 days; production should choose reviewed operational values.

`TAXIMOBILE_ROUTING_PROVIDER` accepts exactly `valhalla` or `graphhopper`, and
`TAXIMOBILE_ROUTING_BASE_URL` points to the matching private self-hosted service.
Portable scripts deliberately select Valhalla and do not download routing data.
Local Compose has mutually exclusive Valhalla and GraphHopper profiles; the latter
builds a non-root, read-only image from the checksum-verified official 11.0 Maven
artifact and namespaces its downloaded PBF and graph cache by the accepted extract
SHA-256. A production deployment must still supply and validate its own private,
versioned service and promoted Morocco graph artifact.
The repository does not silently download an OSM extract or ship a country data
image. If the selected engine is unavailable or returns an invalid route, the API
stays healthy and the authenticated routing endpoint returns a safe `503`;
ride/payment authority is not transferred to the client.

## Initial administrator

After the API is healthy on a fresh database, run the controlled local bootstrap:

```powershell
.\scripts\bootstrap-local-admin.ps1 -Email admin@example.com
```

The password is read twice from a hidden interactive prompt and is never accepted
as a script argument. The operation uses the same configured PostGIS database,
allows only the first administrator, and never promotes a passenger or driver
account. Run it from a trusted operator terminal before approving drivers or
activating tariffs.

Leave `TAXIMOBILE_FIREBASE_PROJECT_ID` empty for WebSocket-only local development.
When set, the worker sends minimized data messages through FCM HTTP v1 and obtains
OAuth credentials from Google Application Default Credentials. Prefer workload
identity in hosted environments. If a service-account file is unavoidable for
local staging, keep it outside the repository and expose it only through the
process/container secret boundary. Never copy it into the image or `.env`.

`TAXIMOBILE_OUTBOX_MAX_ATTEMPTS` bounds WebSocket/FCM refresh-hint delivery. A
row that reaches the limit is marked `DELIVERY_DEAD_LETTERED` and is not claimed
again automatically. During an incident, inspect metadata without selecting the
JSON payload or device-token table:

The authenticated metrics endpoint exposes aggregate gauges named
`taximobile_outbox_pending_events`, `taximobile_outbox_dead_letter_events`,
`taximobile_outbox_locked_events`, and
`taximobile_outbox_oldest_pending_age_seconds`. It also emits
`taximobile_outbox_metrics_available`; a value of `0` means the database snapshot
failed and the count gauges are intentionally absent. Alert on any dead-letter,
an unavailable snapshot, and a pending age beyond the deployment's reviewed
delivery objective. The deployment verifier requires a successful snapshot.

```sql
SELECT id, topic, attempts, last_error, created_at, dead_lettered_at
FROM outbox_events
WHERE dead_lettered_at IS NOT NULL
ORDER BY dead_lettered_at DESC;
```

Resolve and validate the credential, FCM, network, or worker failure first. Then
use the image's guarded command rather than hand-editing retry/lease columns:

```text
python -m taximobile_api.operations.outbox_replay \
  --event-id <reviewed-uuid> [--event-id <reviewed-uuid> ...] \
  --expected-database-host <exact-host> \
  --expected-database-name <exact-name> \
  --incident-reference <safe-incident-id> \
  --execute-reviewed-replay
```

`TAXIMOBILE_DATABASE_URL` comes only from the secret boundary. The command accepts
at most 100 unique explicit IDs, checks the exact host and database name, locks
metadata without selecting JSON payloads, and atomically refuses the entire set
if any ID is absent, already delivered, or not dead-lettered. A successful replay
resets only delivery attempt, lease, fixed error, dead-letter, and availability
state for those rows. Record the incident and selected IDs in the deployment
audit trail. Do not bulk-replay every row, and do not treat replay or delivery as
evidence that a user saw a notification.

Staging and production must use a non-loopback database host. The API rejects
`localhost`, `127.0.0.0/8`, and `::1` in those environments so a deployment
cannot silently point at an isolated machine-local database.

## Local backup and restore drill

With the Compose database running, create an inspectable SQL backup:

```powershell
.\scripts\backup-postgres.ps1
```

For the portable database, use its pinned `pg_dump` directly:

```powershell
.\scripts\backup-postgres.ps1 -Portable
```

The backup is placed under `infra/backups/`, which must remain outside source
control and is ignored. Restore is intentionally guarded and never drops or
overwrites a database. For Compose, point a clean local verification database at
the backup and run:

```powershell
.\scripts\restore-postgres.ps1 -BackupPath .\backups\taximobile-YYYYMMDD-HHMMSS.sql -ConfirmRestore
```

The portable path creates only a previously nonexistent database whose guarded
name starts with `taximobile_restore_`:

```powershell
.\scripts\restore-postgres.ps1 `
  -BackupPath .\backups\taximobile-YYYYMMDD-HHMMSS.sql `
  -ConfirmRestore -Portable -CreatePortableTarget `
  -TargetDatabase taximobile_restore_YYYYMMDD
```

The restore keeps PostGIS owned by the local cluster administrator while
restoring application objects to the application role. A verified drill must
compare the Alembic head and relevant aggregate counts, confirm `postgis_version()`
and application-role access, and run `alembic upgrade head` against the restored
database. The workspace drill completed those checks at migration
`20260813_0029`, including aggregate parity for privacy-minimized driver
credentials; its successful verification database may be removed after
inspection.

Do not run the restore command against production. A production runbook must use
the managed database provider's encrypted backup/restore mechanism and validate
migrations plus API smoke checks before traffic is restored.
