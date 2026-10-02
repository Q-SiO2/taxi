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

For a candidate run, provide all three fresh output paths so the runner also
retains the full JUnit report, collects secret-free post-run database metadata,
and generates bounded T3 system evidence:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test-portable-backend.ps1 `
  -JUnitPath ..\backend\build\t3-full-backend.junit.xml `
  -DatabaseMetadataPath ..\backend\build\t3-database-metadata.json `
  -BackupRestorePath ..\backend\build\t3-backup-restore.json `
  -EvidencePath ..\backend\build\t3-system-evidence.json
```

The runner refuses partial or existing output paths. Before rebuilding
`taximobile_ci`, it inventories stale clone databases and deletes only names
matching `taximobile_ci_test_` plus a 32-character lowercase hex identifier. It
records that count, requires zero clones after the suite, revokes the local
role's temporary `CREATEDB` authority, and verifies one current migration head
plus PostgreSQL/PostGIS versions. It then creates a custom-format logical backup,
restores it into one random guarded database, compares every public table count
and schema-object totals, applies a no-op migration to head, and removes both
the target and dump. A green combined report supports all six bounded T3
evidence classes and sets `phase_evidence_complete=true`; formal phase and
deployment acceptance remain separate and false.

This entry point first runs `validate_source_credentials.py`. In CI the validator
uses Git-tracked files; in this no-Git workspace it deliberately does not read the
ignored `infra/.env`, `TaxiMobile/local.properties`, builds, caches, backups, or
generated environments. Findings report only a relative path and rule name, never
the matching value.

The T0–T10 promotion map is executable without backend dependencies. CI checks
the closed catalog and deliberately empty template with:

```powershell
backend/.venv/Scripts/python.exe infra/scripts/validate_test_phase_evidence.py
```

For a controlled candidate evidence file, pass `--evidence <path>` and optionally
`--require-through T3` (or another exact phase). The validator checks metadata,
ordered predecessor acceptance, candidate/artifact digests, required evidence
classes, sign-off functions, defects, exposure limits and P0 gap closures. It
does not validate signatures or external artifact truth and cannot promote the
all-`NOT_STARTED` repository template. Do not place credentials, identity files,
precise participant locations or payment instructions in the evidence index.

The bounded T2 simulated-persona baseline is a separate executable input to that
promotion process:

```powershell
backend/.venv/Scripts/python.exe infra/scripts/run_simulated_persona_suite.py `
  --output backend/build/t2-simulated-personas.json `
  --junit-output backend/build/t2-simulated-personas.junit.xml
```

Its committed catalog freezes 20 authentication, passenger, driver, applicant,
matching, ride, route, scheduling, money, staff, support, safety, incident,
notification, and client-lifecycle scenarios over 66 exact test nodes. The
2026-10-02 catalog adds ongoing-session authority to notification personas. It cannot
contact a target or provider, use real users or money, or mark T2 accepted. Its
report identifies the remaining T2 database/money reconciliation, adversarial-
security, and data-minimization evidence instead of silently claiming coverage.

The T4 device/browser laboratory is also a closed executable map:

```powershell
backend/.venv/Scripts/python.exe infra/scripts/validate_t4_lab_evidence.py
backend/.venv/Scripts/python.exe infra/scripts/validate_t4_lab_evidence.py `
  --evidence <t4-lab-run.json>
```

`infra/testing/t4-lab-catalog.json` contains 56 cases: eight for each required
supported-matrix, Android, iOS, browser, accessibility/RTL, degraded-network/
lifecycle and crash-symbolication evidence class. The validator cross-checks
Android SDK 24/36 and iOS 18.2 against build source, requires Chrome/Firefox/
Safari plus EN/FR/AR and Arabic RTL, rejects public users/live money/production
credentials/real personal data, and forbids raw serial or sensitive evidence
keys. The committed template remains `NOT_STARTED`; a complete evidence class is
credited only after all eight cases have retained passing facts, and even 56
passes cannot mark T4 or deployment accepted.

The provider-neutral production environment inventory is the executable GAP-002
control record:

```powershell
backend/.venv/Scripts/python.exe infra/scripts/validate_production_environment_inventory.py
backend/.venv/Scripts/python.exe infra/scripts/validate_production_environment_inventory.py `
  --inventory <protected-production-inventory.json> --require-accepted
```

The committed template remains `NOT_STARTED` and contains no provider choice or
secret. A protected accepted copy must reference distinct development, staging
and production boundaries, exact DNS/TLS and application-origin policy, immutable
core images, private service/network policy, secret rotation, cost ownership,
rollback timing and five required approval functions. Passing it closes no
T5 or deployment gate by itself. See
[`deploy/README.md`](deploy/README.md#gap-002-environment-inventory).

Managed PostGIS, PITR, restore, failover and backup-expiry acceptance use a
separate GAP-003 record:

```powershell
backend/.venv/Scripts/python.exe infra/scripts/validate_managed_postgis_evidence.py
backend/.venv/Scripts/python.exe infra/scripts/validate_managed_postgis_evidence.py `
  --evidence <protected-managed-postgis-evidence.json> --require-accepted
```

The committed form is `NOT_STARTED`. A real accepted copy links back to the
GAP-002 environment, records only bounded references and aggregate timings, and
must prove the current migration head, PostgreSQL/PostGIS compatibility, private
encryption, role separation, capacity reserve, PITR, isolated restore, failover,
RPO/RTO, legal holds and expired-data backup removal. Local T3 logical restore
reports cannot be relabeled as this evidence. See
[`deploy/README.md`](deploy/README.md#gap-003-managed-postgis-evidence).

The real city/operator decision uses a separate GAP-004 launch-approval record:

```powershell
backend/.venv/Scripts/python.exe infra/scripts/validate_pilot_city_launch_approval.py
backend/.venv/Scripts/python.exe infra/scripts/validate_pilot_city_launch_approval.py `
  --approval <protected-pilot-city-approval.json> --require-accepted
```

The committed record remains `NOT_STARTED`. An accepted protected copy binds one
real Moroccan city and legal operator to the exact active configuration, public
terms, accountable functions, bounded cohort, cash-inclusive payment scope, all
ten independent readiness reviews and six approvals including explicit product-
owner pilot authorization. It stores references rather than legal documents or
personal data and accepts neither T6 nor deployment. See
[`deploy/README.md`](deploy/README.md#gap-004-pilot-city-launch-approval).

Production operations identity and governance use a separate GAP-005 record:

```powershell
backend/.venv/Scripts/python.exe infra/scripts/validate_operations_identity_governance.py
backend/.venv/Scripts/python.exe infra/scripts/validate_operations_identity_governance.py `
  --governance <protected-operations-governance.json> --require-accepted
```

The committed form remains `NOT_STARTED`. An accepted protected copy requires
an authoritative staff roster/JML process, three-person platform-admin quorum,
explicit maker/checker and sensitive-duty assignments, independently reviewed
TOTP custody for every assigned account, bounded access-review/leaver policy,
eight exercised control drills, fixed audit references and four owner approvals.
It contains no names, contacts, credentials, recovery codes or copied documents
and accepts neither T5 nor deployment. See
[`deploy/README.md`](deploy/README.md#gap-005-operations-identity-and-governance).

Production maps, routing and device navigation use the separate GAP-006 record:

```powershell
backend/.venv/Scripts/python.exe infra/scripts/validate_maps_routing_navigation.py
backend/.venv/Scripts/python.exe infra/scripts/validate_maps_routing_navigation.py `
  --evidence <protected-maps-routing-navigation.json> `
  --routing-report <exact-redacted-routing-report.json> `
  --require-accepted
```

The committed form remains `NOT_STARTED` and chooses no provider or city. An
accepted protected copy binds one approved Moroccan city configuration to
immutable MapLibre style/tile and routing graph artifacts, licensing,
attribution, cache/offline/privacy/cost, refresh, traffic and rollback controls,
six route benchmark categories, four Android/iOS passenger/driver surfaces in
Arabic/French/English, seven drills and six approvals. The separately supplied
backend routing report must match the recorded SHA-256 and pass every language
for the selected Valhalla or GraphHopper target. The record stores references,
not raw routes, provider queries, credentials or personal data, and accepts
neither T5 nor deployment. See
[`deploy/README.md`](deploy/README.md#gap-006-production-maps-routing-and-navigation).

After packaging a reviewed web distribution, collect bounded real-browser boot
evidence without editing the 56-case laboratory record:

```powershell
backend/.venv/Scripts/python.exe infra/scripts/run_t4_browser_smoke.py `
  --release-dir backend/build/t4-web-release `
  --browser chrome --browser firefox `
  --candidate-label local-reviewed-web `
  --output backend/build/t4-browser-smoke.json `
  --artifact-dir backend/build/t4-browser-smoke-artifacts
```

The output and artifact directory must not already exist. The collector requires
valid screenshots and the exact compatibility/boot network boundary for every
scenario. Its test origin is loopback, but browser egress is not independently
firewalled. Safari and full authenticated/accessibility/hosted journeys remain in
the T4 catalog, so this command never completes a catalog case or accepts T4.

Production-like manifests also fail closed on client lifecycle configuration.
They require `TAXIMOBILE_CLIENT_COMPATIBILITY_ENFORCED=true`, one controlled
policy revision, and minimum/recommended versions for all six Android/iOS/web
surfaces. Keep the API and worker environment boundaries distinct: compatibility
policy belongs on the public API only. The production Compose validator rejects
missing surfaces, disabled enforcement, or policy copied onto the worker. The
`baseline-1`/`1.0.0` examples are not an approval to support that version in a
real launch; freeze and test the actual policy through the T0/T4/T5 matrix before
promotion.

It then runs `validate_mobile_api_contract.py` and
`validate_web_api_contract.py`, which extract the real handwritten Kotlin
gateway operations and prove that every HTTP method/path is present in FastAPI
OpenAPI. The mobile live-event WebSocket is checked against the application
route table because OpenAPI does not represent WebSockets. The web gate also
requires the shared exactly-once `/api/v1` URL builder and finite rejecting
action selectors. A new unparsed call, runtime route variable, or unreviewed
dynamic route segment stops the suite.

The test script uses only the isolated `taximobile_ci` database. It recreates
that exact CI database as a pristine migrated template, temporarily grants the
application test role database-creation authority, clones one database per
integration test, and revokes the authority in a `finally` boundary. Each clone
is terminated and dropped after its test, so bootstrap administrators, sessions,
rate limits, and lifecycle records cannot contaminate another case. The script
starts and stops PostgreSQL itself when the development stack is not already running. Stop
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
existing data. It prints one generated password and five unique local-only
emails: rich passenger, approved active driver, pending driver application,
empty passenger, and a city-scoped operations recruitment reviewer. The rich
pair shares an en-route ride and has completed rides, cash receipt states,
notifications, support tickets, a verified vehicle and credential, cooperative
membership, rating, and settled earnings. Additional submitted applications
produce both visible and suppressed onboarding aggregate cells for reviewer UX
testing. These are synthetic review records—not migration seeds or production
fixtures.

### Docker Compose stack

With Docker Desktop installed and running, start and health-check all services
with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-local-stack.ps1
```

Newly generated local environments also create an independent driver-document
encryption key and enable the `driver-documents` profile. That profile starts a
private ClamAV daemon, persists only its signature database in a separate volume,
and mounts the encrypted document volume into the API. The scanner has no host
port. Existing `.env` files keep uploads safely disabled until all three
`TAXIMOBILE_DRIVER_DOCUMENT_STORAGE_ROOT`,
`TAXIMOBILE_DRIVER_DOCUMENT_ENCRYPTION_KEY`, and
`TAXIMOBILE_DRIVER_DOCUMENT_CLAMAV_HOST` values are deliberately added; the
startup script rejects partial configuration. The portable Windows stack does
not silently install ClamAV, so its document capability remains unavailable.

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
database, Firebase, manual-transfer recipient configuration, or future payment-
provider secret.

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

Operational aggregate refresh uses `TAXIMOBILE_ANALYTICS_POLL_SECONDS`
(30–3,600; default 300). The worker snapshots only city-wide supply and rebuilds
the reporting materialized view from normalized records; this interval does not
change ride, payment, eligibility, or rollout authority.

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

Place discovery is a separate API-only boundary and is disabled by default.
Set `TAXIMOBILE_GEOCODING_PROVIDER=nominatim` only with a reviewed compatible
deployment, then provide `TAXIMOBILE_GEOCODING_BASE_URL`, the bounded timeout,
an identifying `TAXIMOBILE_GEOCODING_USER_AGENT`, and the search/reverse request
limits. Staging and production require HTTPS and reject the shared public
`nominatim.openstreetmap.org` host. The provider supplies display candidates;
the exact selected coordinate and active PostGIS service-area polygon remain
authoritative. Provider outage returns a safe fallback to map/manual selection.
This wiring does not approve an extract, license, privacy terms, capacity, or
city-language quality; those require the acceptance track in `../docs/testing.md`.

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

To exercise the Phase 12 operations console, first set the exact local browser
origin in `.env` and restart the API:

```text
TAXIMOBILE_CORS_ORIGINS=http://127.0.0.1:8080
TAXIMOBILE_OPERATIONS_PASSWORD_LOGIN_ENABLED=true
TAXIMOBILE_OPERATIONS_SECURE_COOKIE_ENABLED=false
```

Then map the same reviewed bootstrap administrator to the first Morocco-scoped
platform grant:

```powershell
docker compose exec api python -m taximobile_api.cli.bootstrap_operations `
  --admin-email admin@example.com `
  --market-code MA `
  --confirm-market-scope
```

For a hosted-style local rehearsal, register and review two additional active
staff accounts, then establish the bounded initial quorum from the trusted
terminal:

```powershell
docker compose exec api python -m taximobile_api.cli.bootstrap_operations_quorum `
  --user-email operator-b@example.com `
  --market-code MA `
  --change-reference CHG-INITIAL-QUORUM-B `
  --confirm-initial-quorum

docker compose exec api python -m taximobile_api.cli.bootstrap_operations_quorum `
  --user-email operator-c@example.com `
  --market-code MA `
  --change-reference CHG-INITIAL-QUORUM-C `
  --confirm-initial-quorum
```

This bootstrap path closes after three platform administrators and cannot be used
for ongoing access management. Enroll MFA for each member and use the operations
maker-checker queue for all later grant creation/revocation. Staging and
production reject the direct mutation routes.

The password-only switch is local/test scaffolding and production configuration
rejects it. See `../backend/README.md` for the operations session boundary and
`../TaxiMobile/README.md` for the web launch command.

Hosted staging/production instead sets password-only mode to `false`, secure
cookies to `true`, an independent base64url-encoded 32-byte
`TAXIMOBILE_OPERATIONS_MFA_ENCRYPTION_KEY`, and one exact HTTPS operations web
origin. After the initial three-person scoped quorum is established, enroll every
operations account through the trusted-terminal command in
`../backend/README.md`. The API and operations
web origins must be same-site (for example `api.example.ma` and
`operations.example.ma`) or be placed behind one HTTPS reverse proxy; the strict
refresh cookie is intentionally not sent across unrelated sites.

Local development may leave the external case pager disabled; overdue alerts
remain durable and visible in the operations console. A live staging/production
pilot must configure the worker-only `TAXIMOBILE_CASE_PAGER_URL` as HTTPS
and an independent 32+ character `TAXIMOBILE_CASE_PAGER_TOKEN`, plus the
bounded poll/attempt/timeout settings shown in `.env.example`. A missing or
failed adapter never marks an alert delivered.

The `case_retention` loop uses
`TAXIMOBILE_CASE_RETENTION_POLL_SECONDS` (300–86,400; default 3,600) and
`TAXIMOBILE_CASE_RETENTION_BATCH_SIZE` (1–1,000 per case kind; default 100). It minimizes only
closed due cases after a transaction-locked active-hold check. Local demo data
must not be used to claim that production backup expiry or legal-review
operations have been proved.

## Legacy-city manual-transfer compatibility

Cash requires no provider configuration. The following variables are disabled by
default and can advertise external bank/M-Wallet transfer only for the
deterministic legacy city:

```text
TAXIMOBILE_MANUAL_TRANSFER_ENABLED=true
TAXIMOBILE_TRANSFER_RECIPIENT_NAME=<verified recipient>
TAXIMOBILE_TRANSFER_BANK_ACCOUNT=<bank destination, optional with wallet>
TAXIMOBILE_TRANSFER_WALLET_ID=<wallet destination, optional with bank>
```

An enabled configuration requires the recipient and at least one destination;
startup otherwise fails rather than publishing incomplete instructions. These
values are displayed to the owning passenger after a transfer ride, so they are
not authentication credentials. They are still controlled operational
configuration: do not commit them and never put a bank password, wallet PIN, OTP,
statement login, or provider secret in them.

Every new city/operator/service must instead use a verified recipient account,
active payment-capability version, and exact active city-configuration link
managed through the operations platform. The legacy variables never satisfy that
requirement.

After a passenger submits a transfer claim, use only the authenticated scoped
operations reconciliation API and the recipient institution's independent
statement. A claim is `PROCESSING`, not paid. Verification requires a unique
external settlement reference and creates the earning atomically; rejection
returns the payment to pending. The transitional `/admin/payments` routes exist
for the legacy administrator only; national operations use
`/operations/payments` with city/operator grants and recent MFA where required.

Leave `TAXIMOBILE_FIREBASE_PROJECT_ID` empty for WebSocket-only local development.
When set, the worker sends minimized data messages through FCM HTTP v1 and obtains
OAuth credentials from Google Application Default Credentials. Prefer workload
identity in hosted environments. If a service-account file is unavoidable for
local staging, keep it outside the repository and expose it only through the
process/container secret boundary. Never copy it into the image or `.env`.

FCM and Crashlytics are no-cost Firebase Spark-plan products. This stack does not
need Firestore, Realtime Database, Cloud Functions, Storage, Hosting, phone auth,
or Analytics. Do not enable a metered Firebase product without a separate cost,
privacy, and architecture decision. WebSockets remain the foreground fallback
when FCM is absent.

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
Fixed low-cardinality `taximobile_outbox_owner_pending_events`,
`taximobile_outbox_owner_dead_letter_events`,
`taximobile_outbox_owner_locked_events`, and
`taximobile_outbox_owner_oldest_pending_age_seconds` series attribute work to
`dispatch_operations`, `scheduling_operations`, `driver_compliance`, or the
fail-closed `unclassified` bucket. Topic, payload, resource and user labels are
deliberately absent. Dead-letter alerts retain the owner label for routing.
The same protected endpoint emits an unlabelled current-database capacity
snapshot: `taximobile_database_metrics_available`, connections, active
connections, server connection limit, utilization ratio, waiting locks and a
deadlock counter. Collection is bounded to five seconds. On timeout, permission,
driver or malformed-result failure, only availability zero is emitted; database
name, role/session identity and query text are never selected or rendered. The
same endpoint exposes fixed, unlabelled per-process pool availability, configured
size, checked-in, checked-out and overflow gauges, a cumulative checkout-wait
histogram and timeout counter. Production API/worker engines
receive explicit bounded size, maximum-overflow and checkout-timeout settings;
budget their worst-case connection count across all replicas before scaling.
These series support staging load diagnosis but do not replace host CPU/IO/
storage or query-plan evidence, and their thresholds still require approval and
measurement under a representative hosted workload.
The provider-neutral self-hosted collector/routing template is documented in
`deploy/README.md` and composed by layering `deploy/compose.monitoring.yaml` over
the base production manifest. The same overlay provisions the immutable
`TaxiMobile Operations` and `TaxiMobile Logs` Grafana dashboards from reviewed
files and keeps Grafana on the internal monitoring network. Prometheus,
Alertmanager, Loki, Alloy, and Grafana bind
only to host loopback and are not part of the local development stack. Run
`infra/scripts/validate-monitoring-runtime.ps1` with the exact candidate images
and secret files before staging startup; this includes native config parsers,
disposable hardened Grafana provisioning, real Loki/Alloy readiness, role-volume
ownership, and malformed/oversize-filtering ingestion. Loki remains an
unauthenticated internal single-node filesystem service; it must not be exposed
publicly or mistaken for a high-availability national log service.

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
