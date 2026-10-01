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

The API exposes `/health`, `/ready`, `/api/v1/meta`, the command-free
`/api/v1/client-compatibility` preflight, an authenticated best-effort live-event
socket at `/api/v1/events`, and generated OpenAPI at `/api/v1/openapi.json`.
The documented v1 contract includes accounts, provider-independent offline
recovery codes, password/session controls, provider-neutral place search/reverse
lookup, passenger and driver profiles, driver availability/locations, rides and
offers, fixed-tariff pricing, cash settlement, optional manually reconciled
bank/M-Wallet transfer, driver earnings, ratings, support tickets, separate
safety reports, notification history, administration, and audit records. Run
`pytest` and `alembic upgrade head --sql` before declaring a backend change
verified.

Staging and production require client compatibility enforcement for Android/iOS
passenger and driver apps plus applicant/operations web. Configure a controlled
`TAXIMOBILE_CLIENT_POLICY_REVISION` and both `MINIMUM_VERSION` and
`RECOMMENDED_VERSION` variables for all six surfaces shown in
`../infra/.env.example`. Values are strict `major.minor.patch[.revision]`
versions. The checked-in `baseline-1`/`1.0.0` defaults are source-safe starting
values, not an approved public support window. Missing/malformed identity and
below-minimum clients are rejected before auth/business work; these forgeable
headers never grant authority. See `../docs/api.md` and `../docs/testing.md`.

Cash is mandatory. New cities advertise methods only from the exact active
city/operator/service payment capability referenced by their active configuration
bundle. Recipient accounts and capability versions are managed through the scoped
`/api/v1/operations` API and protected web console. To opt only the deterministic
legacy city into the compatibility transfer path, set all required values through
the deployment boundary:

```text
TAXIMOBILE_MANUAL_TRANSFER_ENABLED=true
TAXIMOBILE_TRANSFER_RECIPIENT_NAME=<verified legal recipient>
TAXIMOBILE_TRANSFER_BANK_ACCOUNT=<optional when wallet is present>
TAXIMOBILE_TRANSFER_WALLET_ID=<optional when bank account is present>
```

Startup rejects an enabled but incomplete configuration. The passenger submits a
claim through `/api/v1/rides/{ride_id}/payments/manual-transfer/submit`; that
changes the payment only to `PROCESSING`. A scoped reconciler uses
`/api/v1/operations/payments`; the `/api/v1/admin/payments` routes remain a
transitional legacy-administrator surface. Verification requires a unique settlement
reference and atomically creates the driver's earning. Never place bank/wallet
credentials, OTPs, or statements in these settings or API bodies. This
deployment-wide configuration cannot authorize a newly created city or operator.

Completed refunds use the scoped
`POST /api/v1/operations/payments/{payment_id}/refunds` command and bounded
`GET /api/v1/operations/payments/refunds` reconciliation list. The command requires
idempotency, a closed reason, confirmed cash/outbound-transfer evidence, and a
unique settlement reference plus recent operations MFA. It cannot exceed the original completed payment.
Launch refunds are operator-funded and do not edit driver earnings; passenger
receipts expose only safe refund totals and reason rows.

Ordinary support creation and ride-bound safety-report creation require
idempotency and participant authorization. Participant support responses omit
triage fields and internal notes; safety responses additionally omit description
and both party identities. Compatibility queues live under
`/api/v1/admin/support` and `/api/v1/admin/safety`; active operations clients use
city-scoped `/api/v1/operations/support`, `/operations/safety`, and
`/operations/case-alerts` with matching grants and assignee checks. First support
triage and every safety transition require a
participant-visible message alongside a separate internal note. Never paste
credentials, statements, documents, or unrelated personal data into case text.
See `../docs/operations.md` for response targets, escalation, retention, and the
duty runbook. TaxiMobile safety reporting is not an emergency service.

Market-scoped platform administrators manage legal holds through
`/api/v1/operations/case-retention/holds`; the read-only `actions` collection
exposes immutable non-content minimization evidence. The fixed retention worker
processes only due closed cases without active holds and erases participant/ride
links, assignment, free text, latest public messages, and notes. Processed cases
are no longer returned by participant or operations case APIs. Authority
references must be bounded non-secret identifiers, never copied legal text.

Market-scoped platform administrators use
`/api/v1/operations/security-incidents` for the dedicated incident register,
forward-only lifecycle and append-only evidence timeline. Writes require recent
MFA and idempotency; manual entries must cite a same-scope audit ID or bounded
external runbook reference. The register coordinates separately authorized
containment actions but does not rotate provider credentials, page staff, or
notify users by itself. Never place secrets, raw provider payloads or unnecessary
participant identifiers in incident summaries.

After the incident is closed, the lead uses the one-time
`/{incident_id}/postmortem/complete` command with the current version, controlled
outcome, completion timestamp and linked evidence. `FOLLOW_UP_REQUIRED` must name
the bounded external work reference. The command appends an immutable timeline
fact and cannot be used to overwrite a completed postmortem.

The same incident resource exposes a bounded `responsibilities` collection and
an assignment command for security response lead, communications lead,
operations liaison and postmortem owner. Opening assigns the reporter as response
lead. Reassignment requires the current incident version, exact active responder
UUID, live platform-administrator authority in the incident market and an
approved roster/shift reference. It releases the previous tenure once, preserves
history and appends a generated timeline fact; completed postmortems are read-only.
There is intentionally no broad responder-search endpoint. A production duty
roster and staffed handoff drill are still required before live use.

The protected operations web application exposes the register only to callers
with `manage_security_incidents`. It supports a bounded queue, creation,
detail/timeline review, referenced append-only facts, and only the next valid
lifecycle transition plus postmortem completion with typed confirmation. A recent-MFA or stale-version
failure reloads authority and never replays the pending command. Provider
rotation, responder paging, user notification and containment execution remain
separate approved operational actions.

Local development and tests use `TAXIMOBILE_PROCESS_ROLE=all`, so the API owns
the bounded matching, outbox, credential, scheduling, analytics, case-alert, and
case-retention loops. Staging and production
default the public application to `api`; the deployment template explicitly
runs `taximobile_api.worker:app` with role `worker` as a separate process from
the same immutable image. The worker exposes only `/health`, `/ready`, and the
token-protected `/internal/metrics` operations surface—never public business API
routes.

`GET /internal/metrics` is an OpenAPI-hidden, Prometheus-compatible endpoint
protected by `TAXIMOBILE_MONITORING_TOKEN`. It exports bounded route-template,
status, latency, safe exception-class metrics and fail-closed aggregate
operational snapshots only. Staging and production
require the dedicated 32+ character token; additionally restrict the path at the
deployment network boundary.
The same endpoint exports only fixed `served`/`blocked` outcomes for requests
addressed to the transitional `/admin` namespace. A production alert treats any
served legacy route as critical, while blocked probes never become raw-path
labels. CI separately runs `validate_legacy_admin_retirement.py` and rejects a
maintained mobile or browser source file containing a legacy endpoint literal.
Security-incident gauges expose only snapshot availability and fixed SEV1-SEV4
open/containment/postmortem deadline counts. Both roles expose the same database
snapshot; reviewed Prometheus/Grafana queries use `min`/`max`, never addition.
Failures omit counts instead of reporting false zeroes. The alert rules do not
prove webhook delivery, acknowledgement, escalation ownership or a staffed drill.

Production Compose also sets `TAXIMOBILE_LOG_FILE` separately for API and worker.
The application writes the same allowlisted JSON format used on stdout to an
application-owned rotating file: defaults are 10 MiB, five backups, and mode
`0640`. Configure bounds with `TAXIMOBILE_LOG_FILE_MAX_BYTES` and
`TAXIMOBILE_LOG_FILE_BACKUP_COUNT`; the path must be absolute. The production
image has fixed UID/GID `2000`, and the collector receives group-only read access
to separate role volumes. Never add request bodies, raw paths, provider responses,
coordinates, tokens, business payloads, or identity fields to this sink.

Runtime and development installations use `--require-hashes`. The canonical
Windows-generated locks are `requirements.lock` and `requirements-dev.lock`;
Linux additionally consumes `requirements-linux.lock` for Uvicorn's
platform-specific event loop. The Linux supplement contains only reviewed
CPython 3.12 x86_64/aarch64 wheel hashes. CI runs separate blocking audits of
`requirements.lock` and `requirements-dev.lock` plus `requirements-linux.lock`.
On Windows audit the canonical runtime/development locks without the Linux-only
supplement; its reviewed wheel hashes are not Windows/source-distribution hashes.
Known published vulnerabilities fail the build and must be reviewed rather than
silently ignored. The test toolchain pins pytest 9.0.3 with pytest-asyncio 1.4.0;
both fixture and test event loops are explicitly function-scoped. A runner/plugin
upgrade must pass the complete guarded migrated-PostGIS suite and restore
rehearsal, not just a selected unit slice, before promotion.
CI and the portable backend test command also run
`../infra/scripts/validate_source_credentials.py`, which rejects committed
provider/signing files, private keys, service-account documents, and recognized
live-token formats without emitting matched values.

They also run `../infra/scripts/validate_mobile_api_contract.py` and
`../infra/scripts/validate_web_api_contract.py`. These extract the actual
handwritten Ktor method/path calls and compare them with FastAPI's OpenAPI
document, while the mobile gate checks `/api/v1/events` against registered
WebSocket routes. The web gate additionally enforces the central exactly-once
`/api/v1` URL builder and finite rejecting action selectors. Unknown client call
shapes, runtime route variables, and unreviewed dynamic segments fail closed
instead of silently escaping compatibility coverage.

Release CI also runs `../infra/scripts/generate_source_contract_inventory.py`.
The deterministic JSON report lists every generated OpenAPI method/path/operation
ID, WebSocket path, Alembic revision/parent/root/head and server-owned role-to-
permission mapping. Ambiguous migrations, duplicate operation IDs, omitted role
templates and unknown permissions fail generation. The report contains no
configuration or database values and is hash-bound into the backend candidate
evidence alongside the SPDX SBOM; it does not claim deployment acceptance.

Alembic reads the same `TAXIMOBILE_DATABASE_URL` as the API when it is set; the
URL in `alembic.ini` is only the local fallback. The opt-in
`tests/integration/test_mvp_lifecycle.py` test refuses to run unless
`TAXIMOBILE_ENV=test`, `TAXIMOBILE_RUN_INTEGRATION=1`, and the configured database
name contains `taximobile_ci`. CI provisions that isolated PostGIS database,
applies every migration, and then proves the complete registration-to-payment
lifecycle, refund and bank/M-Wallet reconciliation, support/safety authorization,
case transitions, privacy projections, escalation, audit redaction, active-hold
blocking/release, and verified support/safety data minimization through HTTP and
the fixed worker.

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

Place discovery is also exposed only through normalized authenticated API
contracts. It is fail-closed by default:

```text
TAXIMOBILE_GEOCODING_PROVIDER=disabled
TAXIMOBILE_GEOCODING_BASE_URL=
TAXIMOBILE_GEOCODING_TIMEOUT_SECONDS=5
TAXIMOBILE_GEOCODING_USER_AGENT=TaxiMobile/0.1 (https://github.com/Q-SiO2/taxi)
TAXIMOBILE_PLACE_SEARCH_RATE_LIMIT_PER_MINUTE=20
TAXIMOBILE_PLACE_REVERSE_RATE_LIMIT_PER_MINUTE=30
```

Selecting `nominatim` requires an approved base URL. Hosted environments require
HTTPS and reject the shared `nominatim.openstreetmap.org` endpoint. Prefer a
reviewed self-hosted service. Queries are bounded and not persisted; each search
coordinate receives an independent PostGIS pickup-serviceability decision from
the active city polygon. This configuration does not itself approve an OSM data
extract, license/attribution plan, privacy terms, capacity or production use.

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

## Phase 12–15 operations, recruitment, pricing, and fixed routes

After the initial administrator exists, map that exact account to the first
Morocco market-scoped operations grant from a trusted terminal:

```powershell
python -m taximobile_api.cli.bootstrap_operations `
  --admin-email admin@example.com `
  --market-code MA `
  --confirm-market-scope
```

`taximobile-bootstrap-operations` is the equivalent installed command. It uses a
database advisory lock, is idempotent only for the same reviewed mapping, and
refuses to replace another initial platform administrator. There is no public
grant-bootstrap endpoint.

Before hosted staff access is opened, register and independently verify two more
active staff accounts, then add only those second and third reviewed members from
a trusted terminal. Use a unique external change/ticket reference for each:

```powershell
python -m taximobile_api.cli.bootstrap_operations_quorum `
  --user-email operator-b@example.com `
  --market-code MA `
  --change-reference CHG-INITIAL-QUORUM-B `
  --confirm-initial-quorum

python -m taximobile_api.cli.bootstrap_operations_quorum `
  --user-email operator-c@example.com `
  --market-code MA `
  --change-reference CHG-INITIAL-QUORUM-C `
  --confirm-initial-quorum
```

`taximobile-bootstrap-operations-quorum` is the installed-command equivalent.
The command locks the market, requires the original first administrator, creates
only quorum members two and three, audits the supplied reference, and permanently
refuses a fourth member. Enroll MFA for all three accounts. Every later staff
grant creation or revocation must use the operations maker-checker request queue;
staging and production reject direct grant mutations. The requester, target and
approver must be distinct, and a platform-administrator revocation cannot leave
fewer than two active non-expired market administrators.

For the local Compose/webpack console, configure the backend process with the
exact browser origin before starting it:

```powershell
$env:TAXIMOBILE_CORS_ORIGINS = "http://127.0.0.1:8080"
$env:TAXIMOBILE_OPERATIONS_PASSWORD_LOGIN_ENABLED = "true"
python -m uvicorn taximobile_api.main:app --host 127.0.0.1 --port 8000
```

Development defaults permit the password-only boundary, but setting it explicitly
makes the local intent reviewable. Production startup rejects this switch.
Operations access uses separate 10-minute access tokens, rotating eight-hour
refresh sessions, active scoped grants, and the `taximobile-operations` audience;
mobile bearer tokens are invalid. Hosted mode requires encrypted RFC 6238 TOTP,
single-use recovery codes, replay prevention, ten-minute recent-MFA step-up, a
`Secure`/`HttpOnly`/`SameSite=Strict` refresh cookie, and a rotating in-memory
CSRF token. Access tokens and CSRF values remain only in browser process memory.
Factor enrollment and explicit replacement use a guarded trusted-terminal
command; replacement revokes every live operations session.

After migrations and scoped-grant bootstrap, configure an independent unpadded
base64url 32-byte `TAXIMOBILE_OPERATIONS_MFA_ENCRYPTION_KEY`, then enroll from a
trusted terminal:

```powershell
python -m taximobile_api.cli.enroll_operations_mfa `
  --email operator@example.com `
  --confirm-enrollment
```

Store the one-time recovery-code output offline. After the security owner has
completed the account-recovery identity check, add `--replace-existing` to
confirm a new authenticator, replace old recovery material, audit the event, and
revoke every operations session. Never put the MFA key, provisioning URI,
authenticator code, or recovery codes in source, logs, screenshots, shell
arguments, or support tickets.

The delivered API covers markets, cities and lifecycle, operators and
assignments, service-area/configuration versions and readiness, scoped grants,
rollout summary, and scoped audit. Phase 13 adds the public recruiting catalog,
applicant-owned city applications, typed answers/evidence, versioned city
requirements, scoped oldest-first review and decisions, city/service driver
authorizations, online/matching enforcement, and privacy-suppressed onboarding
aggregates. Phase 14 adds city/operator/service-scoped tariff, operator-fee, and
scheduling-surcharge policy lifecycles; configuration references; immutable ride
financial snapshots; exact quote/offer/receipt/earning components; and scoped
operations APIs. Phase 15 adds immutable route/version/direction/stop geometry,
one-to-one direction-scoped fares, city-configuration route allowlists, a
supply-private public catalog, immediate passenger requests, and informed
fixed-route driver offers/history. The route and fare draft workflows may begin
in either order, but fare activation and route publication fail closed until the
reciprocal link and effective ranges are valid. Phase 16 adds authoritative
scheduled estimates/bookings/offers/commitments/handoff and Phase 17 adds typed,
privacy-suppressed operational facts, reconciliation refresh, scoped APIs, and
the operations dashboard. Migrations `20260830_0040` through `20260830_0043` add
immutable support/safety city scope, scoped operations mutations/UI, and durable
overdue-alert paging, legal holds, immutable minimization evidence, and
production operations MFA. Migration `20260831_0044` adds versioned payment
capabilities, verified recipients, coherent configuration links, and scoped
financial provenance/reconciliation.

Driver-document upload/read/delete routes use an all-or-none protected adapter.
Set `TAXIMOBILE_DRIVER_DOCUMENT_STORAGE_ROOT`, an independent base64url-encoded
32-byte `TAXIMOBILE_DRIVER_DOCUMENT_ENCRYPTION_KEY`, and
`TAXIMOBILE_DRIVER_DOCUMENT_CLAMAV_HOST` together. Otherwise the capability
remains disabled and ownership is authorized before `503` is returned. Enabled
uploads accept only signature-matched PDF/JPEG/PNG files within the configured
limit, scan before AES-256-GCM persistence, create evidence transactionally, and
clean up storage on a database race. Reviewer reads require scoped permission and
recent MFA, are audited and rate-limited, and use opaque no-store downloads.
Replacement/deletion feeds the `driver_document_retention` worker, which erases
ciphertext and metadata and writes content-free immutable erasure evidence.

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

## Synthetic passenger write workload

`python -m taximobile_api.operations.passenger_workload --help` describes the
bounded concurrent passenger request/cancel runner. Unlike the GET smoke test,
it creates durable synthetic accounts and ride history, exercises idempotent
replays, and verifies cancellation through a fresh read. It requires explicit
synthetic-target confirmation and an already provisioned test city, tariff,
cash capability and eligible synthetic driver supply. Do not run against a real
user environment. See the [workload runbook](../docs/testing_workloads.md) for
commands, bounds, cleanup/reconciliation, failure semantics and phased acceptance.

`python -m taximobile_api.operations.cash_workload --help` adds paired synthetic
driver/passenger completion, cash settlement, receipt and earning verification.
It requires `--confirm-synthetic-cash` as well as synthetic-target confirmation,
and pre-approved synthetic driver sessions through the local secret environment
variable `TAXIMOBILE_WORKLOAD_DRIVERS_JSON`. See the same runbook before use:
this writes persistent synthetic money records and never proves real cash custody.

`python -m taximobile_api.operations.capacity_workload --help` uses the same
request/cancel invariants with constant-rate open-loop arrivals. It caps the actor
pool and schedule, measures arrival queue lag separately from HTTP and journey
latency, stops release after the first failed invariant, and emits aggregate-only
JSON. Its tiny local PostGIS test is a harness proof, not an approved city load,
SLO, multi-replica soak or failover result.

`python -m taximobile_api.operations.capacity_plan --help` runs a strict approved
WARMUP/STEADY/BURST/RECOVERY JSON profile. The repository template remains DRAFT
and cannot execute. A semantic profile digest and unexecuted-phase list make
results comparable and fail-closed. Acceptance-oriented runs require a protected
Prometheus origin and explicit monitoring confirmation; 22 fixed aggregate
queries and 21 profile thresholds are checked per phase, including fixed
current-database connection, lock, deadlock and per-process pool occupancy,
checkout-wait p95 and timeout evidence. Pool
size, maximum overflow and checkout timeout are explicit bounded settings; plan
their per-replica connection budget before scaling. The explicit
`--confirm-harness-without-monitoring` alternative is local harness proof only.
Neither confirmation flag is evidence that product or operations owners actually
signed off; follow the workload runbook.
