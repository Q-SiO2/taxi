# TaxiMobile — Testing and Deployment Acceptance Map

## 1. Purpose

This document defines how TaxiMobile progresses from source code and simulated
users to a bounded real-city service. It is the testing companion to
[`gaps.md`](gaps.md): the gap register says what is missing, while this map says
how each implementation and operational claim must be tested and promoted.
Use the shorter [`testing_execution_map.md`](testing_execution_map.md) as the
phase-control board; this document remains the detailed scenario authority. The
machine-readable phase catalog and empty evidence template under `infra/testing/`
are validated by `infra/scripts/validate_test_phase_evidence.py`. That gate checks
promotion metadata and exposure boundaries; it does not authenticate external
evidence or approve a phase.

**Current standing (refreshed 2026-09-28):** automated backend, PostGIS, shared/mobile,
source-contract, and local web compilation coverage is broad. CI definitions now
include pinned dependency review, resolved Gradle graph submission, backend image
SBOM/provenance and a blocking high/critical image scan. The complete push and
pull-request workflows passed at immutable `de69829a`; this is not independent
review, signed release, provider, hosted, or phase acceptance. CI also structurally validates the
self-hosted monitoring overlay, renders it with the production manifest, parses
Prometheus/Alertmanager/Loki/Alloy configuration with digest-pinned official
tools, provisions both Grafana dashboards, and runs a hardened two-role
structured-log ingestion smoke. Initial in-app Wasm browser smoke testing covers
operations/applicant entry rendering and narrow/wide applicant layout; it found
and closed one nested-scroll runtime defect. A separate packaged-release
collector passed four bounded boot and preflight scenarios in each of local
Chrome 152 and Firefox 155 with retained screenshots. It deliberately does not
claim browser-egress isolation, a complete T4 catalog case, or Safari/critical-
journey/accessibility acceptance. The project is in **Phase T2/T3**, depending
on the subsystem, with a small part of T4 started. It has not passed the full
browser matrix, hosted
staging, provider, physical-device, staff-rehearsal, closed-cohort, or real-user
promotion gates.

The current-head recovery slice has fresh-PostGIS proof for offline-code
creation, expiry, replay rejection, staff exclusion, generic reset responses,
password change, session listing/revocation and account-wide session/device
revocation. Shared JVM tests cover the localized signed-out recovery form. This
is T1–T3 source evidence only: the source acknowledgment/clear gate is covered,
while real secure-save behavior, verified contact delivery, statistical timing,
physical devices, compromised-account
support, and real-user comprehension remain unaccepted.

Latest completed full-suite evidence (2026-09-09): an isolated PostGIS rebuild through migration
`20260908_0052` passed 992 backend tests with no failures, errors or skips; place authority,
assigned-ride coordination, notification policy, fixed-owner outbox telemetry
and real live-event fanout are
included in that run alongside deadline/device-failure contracts and scheduling
eligibility/readiness, successful handoff/fallback transaction rollback/replay and
twelve observed two-session scheduling lock races, four account-containment/
assignment lock races, two location/handoff lock races, city restriction versus
immediate acceptance/dispatch races, seven live-command lock races,
expiry-worker skip/retry, three operational-state dispatch guards, competing and
mixed-origin assignments, direct-write uniqueness, migration conflict refusal and
ownership/CLI-contention/transaction-process-release checks, validated migration
limits, blocked-DDL rollback/retry and online/offline statement cancellation.
That full run also includes rotating structured-log configuration/file-mode
coverage, 29 monitoring deployment contract/mutation cases, 21 immutable
alert-rule cases, fixed outbox/PostgreSQL/pool operational metrics, and one-time
security-incident postmortem completion, responsibility assignment/history and
aggregate deadline telemetry. It completed in 464.24 seconds with 175 dependency
deprecation warnings; the duration is not capacity evidence. The separate
candidate-image runtime preflight proved Linux UID/GID `2000:2000`, mode `0640`,
bounded rollover, Loki/Alloy HTTP readiness, two queryable role streams, and
malformed/oversize rejection. That runtime proof is not part of the pytest count.
The full run includes 41 passenger-workload, 23 paired-cash, 12 open-loop
capacity and 44 capacity-profile/monitoring/plan unit cases, two passenger CLI/socket/
PostGIS cases, five paired-cash CLI/socket/PostGIS cases and two capacity CLI/
socket/PostGIS cases.
The latter cover three fee configurations and two post-commit HTTP failure
scenarios. Three deterministic dispatch-contention cases are also included;
they prove distinct-candidate locking, offerless worker retry and overall
matching timeout.
Mobile/backend contract
validation covers 83 HTTP and one WebSocket operation, and web/backend validation
covers 112 HTTP operations. The shared JVM suite contains 183 tests; its
place-serviceability, recovery-code acknowledgment, foreground driver-location
policy, coordination, scheduled-notification, release-identity and compatibility
gate cases, both Android role compiles, and JS/Wasm
compilation are locally verified in the latest supported Windows run. Both web
production target distributions also build locally; this does not replace the
packaged compatibility release or hosted browser checks. Record
these again from an immutable candidate before they may satisfy a promotion gate.
The latest 992-test evidence is the guarded JUnit run; the preceding 956-test
full backend JUnit report remains
`backend/build/security-incident-full-tests.xml`. Separate focused runs of all 74
workload/contention cases also passed in
`backend/build/cash-workload-focused-tests.xml`, and all 28 scheduled-acceptance and
live-protection cases passed in `backend/build/scheduled-live-protection-focused-tests.xml`.
All 13 account-assignment authority cases passed in
`backend/build/account-assignment-authority-focused-tests.xml`. These are generated
evidence, not committed release artifacts. Localization parity covers 610
EN/FR/AR strings, and 50 infrastructure-script unit tests, 29 monitoring-
deployment contract/mutation cases, six dependency-free static web compatibility-
loader runtime scenarios, and 21 Prometheus alert-rule regression cases pass.
Dependency deprecation warnings remain.

The bounded T2 simulated-persona catalog currently executes 20 stable scenarios
through 60 exact unit-test nodes with no external target, real users, providers,
or live money. Its latest local run passed with zero failures/errors/skips. The
result deliberately keeps T2 evidence incomplete until adversarial review,
durable state/money reconciliation, data-minimization evidence, and required
engineering/security sign-offs exist.

Migration `20260908_0052` is now the repository head. Sixteen dedicated security-
incident unit/static cases and two migrated PostGIS API/database cases pass as part
of the 992-test complete regression. They cover one-time postmortem completion,
evidence requirements, idempotent replay, fixed severity buckets, aggregate
deadline transitions, unavailable snapshots, privacy-safe rendering, exact
alert-expression mutation refusal, initial response-lead assignment, exact-market
responder eligibility, concurrent one-winner reassignment/version authority, generated timeline facts
and append-visible assignment-history protection.

The city-authorization slice passed 33 focused backend cases in
`backend/build/city-authorization-complete-focused-tests.xml`, including actual
MFA and six observed lock waits, plus JS/Wasm compilation and both browser test
tasks. All 33 cases are also included in the passing 992-test full backend run.
The earlier 750-test location-authority report predates this endpoint and is
retained only as historical evidence.

The applicant-status and authorization-notice follow-up passed a 71-test focused
backend pack (`backend/build/city-authorization-notification-focused-tests.xml`),
all 178 shared JVM tests, both Android
role compiles, and 47 tests in each JS/Wasm browser target. Two shared tests
verify the recorded authorization labels and fail-closed unknown-status mapping.
Mobile and web now use one localized shared summary with recorded expiry and a
server-eligibility/refresh notice; a historical approval or authorization record
is not displayed as automatic current permission. These tests do not establish
actual delivery of restriction notices, screen-reader behavior or device refresh
timing. Browser JUnit reports are under `TaxiMobile/webApp/build/test-results/`
and shared JVM reports under `TaxiMobile/shared/build/test-results/jvmTest/`.

The current staff-access dual-control slice passed four real-PostGIS scenarios,
focused backend unit/API/contract checks, migration 0049 downgrade/re-upgrade,
and both JS and Wasm browser tasks with 57 tests each. It covers request/replay,
maker/checker/target separation, approval, revocation, rejection, cancellation,
stale decisions/targets, bounded quorum bootstrap, last-admin refusal and expiry
continuity. The web/backend source-contract gate covers 112 HTTP operations. This
slice is included in the passing 992-test full current-head backend regression.
This is component evidence only; authoritative roster, hosted MFA/CSP, accessibility,
concurrent staff drills and recertification remain promotion gates.

The foreground driver-location slice adds pure policy coverage for the 15-second
available/offer cadence, 10-second active-ride cadence, command suppression,
background stop/foreground re-arm and 60-second unavailable-location backoff.
Both Android role compiles pass with the no-prompt authorized-location path.
This does not replace the Android/iOS physical-device traces, battery and weak-
network measurements, privacy/store review, spoofing checks or dispatch-
freshness acceptance required by T4–T7.

The assigned-ride coordination slice adds six role-bound closed signals, exact
participant and active-state authorization, idempotency, rate/cap limits,
persistent notification, minimized outbox delivery, latest-message REST state,
and localized shared mobile actions. Fresh-PostGIS lifecycle tests and the source
gates below pass. Provider delivery, physical devices, accessibility, retention,
staff escalation, closed-road pickup effectiveness, and real-user thresholds are
still unaccepted and keep `GAP-023` open.

No test phase may be skipped because a later phase appears to cover more. A real
user finding does not replace a unit test; a passing unit test does not authorize
use of real identity documents, location, transport, or money.

## 2. Testing principles

1. **Backend-confirmed state is authoritative.** UI success is checked against
   API, database, audit, payment, and notification facts.
2. **Promote one variable at a time.** Move from stubs to real providers, then
   from staff to a closed cohort, then to public users.
3. **Failure paths are first-class.** Every critical journey includes timeout,
   duplicate, cancellation, permission denial, stale state, and recovery tests.
4. **No production personal data in lower environments.** Synthetic users and
   documents must be visibly fictional and structurally valid.
5. **Evidence is immutable.** Every report identifies commit, build, migration,
   environment, configuration versions, device/browser, data set, tester, time,
   and result.
6. **Accessibility and localization are continuous.** They are not a final
   visual-polish phase.
7. **Privacy boundaries are tested negatively.** Cross-user, cross-city,
   cross-operator, expired-session, and unauthorized-document attempts are
   required.
8. **A phase has stop conditions.** Severe safety, privacy, money, authorization,
   data-loss, or unexplained reconciliation defects stop promotion immediately.
9. **Real pilots remain reversible.** Emergency city pause, provider disablement,
   rollback, support escalation, and data preservation are rehearsed first.
10. **Source completion and deployment acceptance remain separate.** A test may
    close source work while provider, city, legal, or human evidence stays open.

## 3. Phase map

```text
T0 Static and source gates
        |
T1 Unit and component behavior
        |
T2 Simulated personas and contract tests
        |
T3 Local multi-role system tests on fresh PostGIS
        |
T4 Emulator, browser, and physical-device lab
        |
T5 Production-like hosted staging and failure/load/security tests
        |
T6 Trained staff rehearsal with synthetic journeys
        |
T7 Closed cohort and non-public field validation
        |
T8 Bounded real-user city pilot
        |
T9 Public city launch with guarded expansion
        |
T10 Repeatable second-city and national scale
```

Promotion always moves downward one phase. A subsystem may be demoted when its
code, provider, configuration, city policy, threat model, or evidence expires.

### 3.1 Client release compatibility matrix

Run this matrix for all six client surfaces. A row is required whenever client
code, API behavior, release metadata, policy configuration, distribution, or the
supported-version decision changes.

| Case | T0/T1 expectation | T4 expectation | T5/promotion expectation |
| --- | --- | --- | --- |
| Missing/unknown identity | API `426 CLIENT_IDENTITY_REQUIRED`; socket `4406`; no auth/business work | Packaged artifacts never omit metadata | Hosted ingress preserves headers and safe CORS response |
| Malformed version/build | Parser and release package fail closed; preflight safe `400` | No blank/crashing startup; action remains blocked | Rejection has bounded logs/metrics and no reflected attacker value |
| Version below minimum | Preflight `UPGRADE_REQUIRED`; ordinary API `426`; socket `4406` | Mobile shows localized upgrade gate; web shows reload gate; no sign-in/action | Intentionally obsolete signed artifact is blocked after policy raise |
| Minimum to recommended | `UPDATE_AVAILABLE`; requests allowed | Existing sessions restore and critical journeys remain usable | Optional update communication does not become a forced outage |
| At/above recommended | `SUPPORTED`; controlled response headers | Install, upgrade, restart and session restore pass | Candidate and policy revision map to immutable artifacts |
| Policy rollback/forward-fix | Complete six-surface config remains valid | Supported artifact recovers without local-data deletion | Owner records decision, communication, timing and observed recovery |

Build identity is evidence metadata, not authentication. Repeat token, role,
scope, eligibility and command authorization negatives with a forged
current-version header to prove compatibility cannot bypass security.

## 4. Universal evidence record

Every manual, automated, provider, or field run records:

```text
Test run ID:
Phase and scenario IDs:
Date/time and tester/owner:
Commit and tree status:
Backend image/web bundle/mobile artifact digests:
Migration head and database instance:
Environment and city/configuration version IDs:
Provider graph/style/Firebase/scanner/pager versions:
Device OS/model or browser/version:
Network profile and permissions:
Synthetic or real-data classification:
Expected result:
Observed result:
API/resource/audit references without secret or excess personal data:
Screenshots/log/metric links with retention classification:
Defects and severity:
Pass/fail/blocked decision:
Independent reviewer where required:
```

Screenshots and logs must not become an uncontrolled copy of identity files,
precise participant locations, payment instructions, tokens, recovery codes, or
safety narratives.

## 5. Phase T0 — static and source gates

### Scope

Run on every pull request and release candidate before executing application
code. Inputs are source files and locked dependencies only.

### Required checks

* Git and Gradle wrapper integrity.
* Python compilation and dependency lock/hash installation.
* Kotlin/Compose compilation for shared, Android, iOS simulator, JavaScript and
  Kotlin/Wasm targets.
* Generated OpenAPI against every handwritten mobile/web gateway operation;
  unknown call forms and dynamic route variables fail closed, and web URLs must
  pass the exactly-once `/api/v1` endpoint-builder contract.
* Alembic graph has one head, ordered revisions, reversible policy metadata, and
  offline SQL generation.
* Documentation links, standing blocks, gap sequence, current migration head,
  and trailing whitespace.
* Credential and forbidden-file scan.
* Python, Gradle, JavaScript and container vulnerability scans.
* SBOM and source/artifact evidence manifest generation.
* Graphic asset manifest/runtime parity, localization catalog parity, release
  environment guards, mobile role identity, map composition, crash-reporting
  boundaries, Compose/Prometheus validation, and pinned action/image review.
* No release artifact may use unsigned-build or missing-provider bypass flags.

### Promotion gate

All required checks pass on a clean immutable commit. Critical/high dependency
findings are fixed or have time-bounded security-owner acceptance. The release
manifest maps every output to the same commit and configuration inputs.

### Primary gaps addressed

GAP-001, GAP-013, GAP-014, GAP-016, GAP-033 and GAP-034.

## 6. Phase T1 — unit and component behavior

### Backend

Test each state machine, authorization decision, calculation, retry policy,
retention projection, provider normalization, and error mapping without a network.
Use fixed clocks/IDs and property/boundary cases for money, time, pagination,
geometry and concurrency tokens.

Required negative classes:

* malformed, oversized, duplicated, replayed and out-of-order commands;
* wrong role, participant, city, operator, service, state and recent-MFA age;
* stale tariff/configuration/route/schedule/payment version;
* zero/negative/overflow/rounding money values;
* expired offer/session/token/credential/document/policy;
* path traversal, content-type mismatch, scanner failure and storage failure;
* provider timeout, invalid response, partial response and unavailable fallback;
* retention with active/released legal holds; and
* redaction of errors, logs, metrics, audit fields and notification hints.

### Clients

Test coordinators, reducers, validation, decoding, localization keys, navigation
guards and component states using fake gateways. Every screen must represent:
loading, empty, backend error, conflict/stale state, offline, permission denied,
success, and backend-confirmed refresh.

### Promotion gate

Each business rule has deterministic positive and negative coverage. Money,
authorization, matching, lifecycle and retention tests prove invariants rather
than only snapshots.

## 7. Phase T2 — simulated personas and contract tests

### Persona catalog

| Persona | Variants that must be simulated |
| --- | --- |
| Passenger | new/returning, EN/FR/AR, RTL, denied location/push, weak network, cash/manual transfer, cancellation, accessibility user |
| Driver applicant | no driver profile, incomplete/complete requirements, clean/rejected/replaced document, expired requirement version |
| Authorized driver | offline/online, stale location, standard/fixed-route authorization, scheduled opt-in, occupied, suspended, expired credential |
| Recruitment reviewer | city-limited, document permission/no permission, recent-MFA/stale-MFA, approve/reject/resubmit |
| Dispatcher/support | one-city/multi-city grants, assigned/unassigned cases, overdue queue, safety handoff |
| Finance reviewer | configuration-only, reconciliation-only, stale MFA, transfer verify/reject, partial/full refund |
| Market/city administrator | scoped/global, maker/reviewer, lifecycle pause/resume, replacement bundle, legal hold |
| Access administrator | market-scoped, different maker/approver, self-target, duplicate, expiring/non-expiring grant, joiner/mover/leaver |
| Adversary | cross-user ID, cross-city scope, replay, stolen session, malicious document, fabricated payment/location/provider response |

### Required simulation journeys

* Registration, login, refresh rotation, logout, operations containment and
  recovery: mobile/operations/push revocation, suspension, revoked-session
  refresh, unrelated-account hiding, idempotent replay and partial cross-market
  denial.
* Ordinary-account recovery: password-reauthenticated code rotation, one-time
  display/acknowledgement, expired/invalid/replayed/concurrently submitted code,
  absent/suspended/staff identity, password reuse, all-session/device revocation,
  generic localized response, rate limiting and secret-redaction checks.
* Staff access: every role-template/scope pairing, active/missing/suspended target,
  cross-market target, self-create/self-revoke, duplicate grant, malformed/past
  expiry, expired grant/session, stale MFA, concurrent revoke and list, and
  authoritative refresh after success/conflict. A step-up challenge must execute
  nothing and must never replay the original command automatically.
* Driver profile/vehicle/credential/application/document/review/authorization.
* Immediate estimate/request, ordered offer decline/expiry/acceptance, pickup,
  ride start, completion, cash settlement, receipt and rating.
* Manual-transfer submit/reject/correct/verify and partial/full refund.
* Published fixed-route catalog in both directions, flat-fare request, driver
  authorization and receipt provenance.
* Scheduled estimate/confirm/cancel, driver opt-in/offer/commitment, overlap,
  opening, handoff, fallback and unfulfilled outcome.
  Repeat with account suspension, rejected/expired driver verification, changed
  vehicle ownership/selection, inactive/unverified/expired vehicle and a known
  credential that expires after commitment. Never convert a prior commitment
  into authority to bypass current professional facts. Direct handoff also needs
  missing/stale/future/outside-area location, offline/paused/offered status and
  wrong city/service cases. Source admission now enforces these checks, with the
  configured freshness threshold and a 60-second future-skew allowance; field
  readiness and concurrency remain separate gates.
* Support and safety report, assignment, notes, transitions, safety handoff,
  overdue page/acknowledgement, legal hold and retention.
* City/operator creation, service area, pricing/payment/route/schedule bundle,
  evidence review, pilot activation, replacement, pause/resume and closeout.
* Analytics refresh, definition/version display, suppression and scope isolation.

### Contract checks

The same closed values, routes, error envelope, version fields, money strings and
state names must be accepted by OpenAPI, backend serializers, Kotlin models and
UI mappings. Unknown future values show a safe generic state and trigger
authoritative refresh; they never become success.

### Promotion gate

All personas complete applicable journeys with deterministic fakes. Every
privilege boundary includes a denied simulation. No test bypass is reachable in
a release build.

## 8. Phase T3 — local multi-role system tests

### Environment

Use a fresh isolated PostGIS database at migration head, real API/worker process
roles, and local provider adapters or controlled stubs. Run all eight worker loops
and at least two API replicas for cross-instance paths where practical.

The guarded local runner accepts all-or-none JUnit, database-metadata, backup/
restore and system-evidence paths. Its generated T3 report requires at least 900 skip-free
tests; named migration-lock, authority-race, worker-termination/reclaim and
state/money reconciliation cases; one exact migration head; PostGIS; zero
residual clone databases; and revoked temporary local clone authority. The
2026-09-09 run passed 992 tests and these checks. The guarded logical rehearsal
then restored 81 public tables and 8,511 aggregate rows, matched schema/table/
PostGIS facts through a no-op migration to head, and deleted the restore target
and dump. The combined report supports all six required T3 evidence kinds and
marks evidence complete, while T3 and deployment acceptance remain false pending
engineering sign-off and ordered promotion evidence.

### Database lifecycle

* Empty database upgrade through every migration.
* Offline SQL generation and one-head verification.
* Targeted downgrade/re-upgrade for the newest risky migrations.
* Constraint/index/PostGIS query behavior with same-city and cross-city data.
* Transaction rollback after injected failure.
* Backup/restore to a newly named isolated database, then application readiness.
* Retention/legal-hold processing with time advanced beyond policy boundaries.

### Multi-role end-to-end suites

The [synthetic HTTP workload runbook](testing_workloads.md) provides executable
passenger write/dispatch/cancel and paired-driver cash completion/settlement
baselines, exact fixture requirements, economic checks and post-commit failure
cases. These complement the broader journeys below rather than replacing them.

Use API-level synthetic users to execute every T2 journey and reconcile:

```text
client state
  = authorized API representation
  = database business facts
  = append-oriented audit facts
  = payment/earning/refund conservation
  = notification/outbox consequences
  = analytics aggregate consequences after refresh
```

Test parallel acceptance, duplicate idempotency keys, worker lease expiry,
process restart, dead-letter/replay, database reconnect, stale client commands,
city pause during active work and one-city isolation.

### Live-command concurrency regression and promotion track

`backend/tests/integration/test_live_ride_concurrency.py` seeds synthetic,
non-loginable users, driver/vehicle/authorization facts and rides into an isolated
current-head PostGIS clone. It is a service/database fixture, not a substitute for
API onboarding or city-readiness proof. Seven two-session cases deliberately keep
old ORM references; an observer must see the loser in `pg_blocking_pids` before
releasing the winner. Final state and notification/outbox counts are read after
both actors commit. No provider delivery is inferred.

| Case | Ordering under test | Required result | Current evidence |
| --- | --- | --- | --- |
| LIVE-RACE-01 | Passenger cancellation before acceptance | Cancelled ride/offer, available driver, acceptance conflict, one cancellation outbox event | T3 PostgreSQL passed |
| LIVE-RACE-02 | Acceptance before passenger cancellation | Both commands allowed before start; accepted audit/hint followed by terminal cancellation, available driver | T3 PostgreSQL passed |
| LIVE-RACE-03 | Acceptance before duplicate acceptance | One assignment and one addressed passenger notification/outbox; duplicate conflict | T3 PostgreSQL passed |
| LIVE-RACE-04 | Decline before acceptance | Declined offer, no assignment, driver released; acceptance conflict | T3 PostgreSQL passed; HTTP redispatch tested separately |
| LIVE-RACE-05 | Driver offline before acceptance | Refreshed offline scope remains offline; no assignment; pending offer can expire normally | T3 PostgreSQL passed |
| LIVE-RACE-06 | Start before cancellation | In-progress ride and on-ride driver; cancellation conflict, no cancellation event | T3 PostgreSQL passed |
| LIVE-RACE-07 | Cancellation before start | Cancelled ride and released driver; start conflict | T3 PostgreSQL passed |
| LIVE-RACE-08 | Worker expiry while another transaction holds the ride | Worker skips without waiting; after release expires once, proceeds to no-supply outcome, repeat does nothing | T3 real worker/PostgreSQL passed |
| LIVE-RACE-09 | Dispatch replay against en-route, arrived and in-progress rides | No new offer or matching transition; original operational state preserved | Three T3 PostgreSQL cases passed |
| LIVE-RACE-10 | Competing drivers for one ride or one driver accepting two rides | One assignment and one passenger notification/outbox; loser conflicts after a proven lock wait | Two T3 PostgreSQL cases passed |
| LIVE-RACE-11 | Immediate acceptance versus scheduled handoff, each winning first | One active ride; immediate win makes no-supply schedule unfulfilled, scheduled win rejects the immediate acceptance | Both T3 service/PostgreSQL orders passed |
| LIVE-RACE-12 | Writer bypasses the service locks for each active status | Unique index rejects second active assignment; cancelling the first releases the slot without deleting history | Four T3 direct-write cases passed |
| LIVE-RACE-13 | Upgrade encounters conflicting legacy active assignments | Fixed diagnostic, no automatic data changes; reviewed fixture resolution allows reapply; downgrade preserves rides | T3 downgrade/preflight/reapply passed |
| LIVE-RACE-14 | Administrative suspension/revocation, settlement and independent-process mixed load | Authorized winning state, bounded failure, no contradictory financial effects, measured contention | Global account-status subset passed in T1/T3; credential/configuration, financial and independent-process matrix open |

The additional pack lives in `test_assignment_invariants.py` and
`assignment_concurrency.py`; mixed-origin cases are selected with `-k mixed` in
`test_published_fixed_routes.py`. The latter retains the city/policy/commitment
created by the existing API fixture, then injects an adversarial old live offer
while the driver is available. It proves defense against that overlap, not an
ordinary end-to-end dispatch journey. The driver lock is observed before release,
both command transactions commit, and fresh reads confirm one active assignment.

#### Account-suspension assignment authority pack

Authentication and assignment commit are separate transactions. This pack proves
that global account status is checked again under a database lock rather than
trusting the bearer token or active driver-profile row cached at request start.
The six integration cases use fresh migrated PostGIS clones and four observed
`pg_blocking_pids` waits; the seven unit cases verify the closed status set and
PostgreSQL lock modes.

| Case | Ordering or state | Required durable result | Current evidence |
| --- | --- | --- | --- |
| ACCOUNT-RACE-01 | Active, suspended, deactivated and missing user; ordinary/shared/exclusive SQL shape | Only `ACTIVE` is eligible; assignment emits `FOR SHARE`; containment emits refreshing `FOR UPDATE` | Seven T1 unit cases passed |
| ACCOUNT-RACE-02 | Globally suspended user with operationally active/available driver profile | Candidate query creates no offer and reaches explicit no-supply outcome | T3 PostGIS passed |
| ACCOUNT-RACE-03 | Globally suspended user retains an old scheduled offer | Acceptance conflicts; booking/offer remain uncommitted and no commitment exists | T3 PostGIS passed |
| ACCOUNT-RACE-04 | Suspension owns user row before immediate acceptance | Acceptance waits, reloads suspension, produces no assignment/notification/outbox | T3 observed-wait PostGIS passed |
| ACCOUNT-RACE-05 | Immediate acceptance owns shared user authority before suspension | One assignment commits; suspension waits, then revokes future access without rewriting the ride | T3 observed-wait PostGIS passed |
| ACCOUNT-RACE-06 | Suspension owns user row before scheduled handoff | Handoff waits, reloads suspension, releases commitment and records fallback/no-supply unfulfilled with no ride | T3 observed-wait PostGIS passed |
| ACCOUNT-RACE-07 | Scheduled handoff owns shared user authority before suspension | One scheduled ride commits; suspension waits, then blocks future access while preserving the ride | T3 observed-wait PostGIS passed |

Run from `backend/` only against the guarded disposable integration database:

```text
python -m pytest tests/unit/test_account_authority.py tests/integration/test_account_assignment_authority.py -q --tb=short --junitxml=build/account-assignment-authority-focused-tests.xml
```

T4 repeats stale immediate/scheduled screens on separate driver/passenger devices:
after containment, refresh and reconnect must sign the driver out and must not
display a successful losing action. T5 separates operations/API/worker processes,
injects latency and process loss in both lock orders, distinguishes session-only
revocation from account suspension, and records lock wait/p95/p99/deadlock data.
T6 staff rehearse containment both before and just after assignment and follow the
active-ride support/safety path without editing history. T7 uses synthetic or
closed non-public journeys only; do not suspend a working driver during an
occupied public-road test. T8–T10 stop promotion on any post-suspension new
assignment, restored revoked credential, hidden stuck ride, duplicate side effect,
unbounded wait or staff assumption that containment itself cancelled the ride.

Migration `20260903_0048` has a write-blocking transactional index build. T5 must
measure upgrade duration on representative history and traffic, prove bounded
maintenance/rollback, and rehearse conflict investigation using synthetic data.
The local empty-database CLI sequence `upgrade head`, `downgrade 20260903_0047`,
`upgrade head`, `current` also passed at the time and returned the sole
`20260907_0049` head. The later migration 0050 separately passed downgrade to
0049, re-upgrade and `current`, which returned sole head `20260907_0050`.
Migration 0051 then passed downgrade to 0050, re-upgrade and `current`, which
returned sole head `20260907_0051`.
Migration 0052 subsequently passed downgrade to 0051, re-upgrade and `current`,
which returned the sole repository head `20260908_0052`.
That verifies revision bookkeeping on an empty test database, not live upgrade
duration or recovery under production traffic.
Enforce one migrator at deployment and explicitly test duplicate job/startup
attempts in T5. The Alembic environment now has a fail-fast database transaction
advisory lock; local CLI contention and owner-release cases pass, but hosted
orchestration and DDL/build-time acceptance remain separate requirements.
Never bypass the migration diagnostic by deleting or arbitrarily cancelling real
rides. Keep the database constraint alongside application locking; neither a
successful index build nor a passing local race replaces load/operational gates.

Run the focused file with integration mode and the guarded isolated migrated
database setup; also run the complete backend suite. T2 scripts must preserve
command IDs, actors and expected outcomes. T4 replays acceptance/cancel/offline/
start from two devices with stale screens, lost responses, reconnect and retries;
confirm no start button can resurrect cancelled work. T5 drives the same races
through separate API/worker processes with latency, worker restart, database
reconnect and mixed city load; inspect lock waits, retries, p95/p99 and duplicate
durable effects. A local coroutine race alone does not pass that gate.

T6 staff rehearse a cancellation immediately after assignment and a rejected
cancellation after start, checking support/safety alternatives without overriding
ride history. T7 uses trained participants and controlled non-public conditions
to compare device state with actual pickup/start decisions. T8 real-user pilots
require prior safety gates, monitoring and stop criteria for duplicate assignment,
unauthorized start, lost cancellation or unexplained driver state. Do not inject
unsafe races into occupied public-road rides. T9/T10 repeat affected cases per
release/city and retain the immutable candidate, migration head, JUnit output,
redacted traces and named acceptance decision.

### Migration ownership, failure and release pack

`test_migration_lock.py` provides six unit/source checks, and
`test_migration_serialization.py` provides seven isolated PostgreSQL cases. The
latter runs actual Alembic subprocesses with inherited test-only database
configuration, never credentials on command arguments. A synthetic owner holds
the exact application advisory lock, and a separate test terminates its actual
process after an explicit lock-held signal. No filesystem lock or guessed sleep
is treated as evidence of ownership.

| Case | Scenario | Required outcome | Current evidence |
| --- | --- | --- | --- |
| MIGRATE-01 | Upgrade or downgrade while another transaction owns the migration lock | Fast nonzero exit, fixed retry diagnostic, unchanged version/index; upgrade retry succeeds after release | Two actual CLI/PostgreSQL cases passed |
| MIGRATE-02 | Owning transaction commits or rolls back | Another connection can acquire ownership; no persistent lock-file cleanup | Two PostgreSQL cases passed |
| MIGRATE-03 | Owning database connection is invalidated | Lock released after server observes disconnect; bounded successful reacquisition | PostgreSQL case passed |
| MIGRATE-04 | Lock-owner process is terminated | Competing CLI is first refused, then succeeds after owner death without manual unlock | Separate-process/PostgreSQL case passed |
| MIGRATE-05 | Generated-script guard runs while online executor owns the lock | Same namespace refuses execution before schema work; succeeds after release | PostgreSQL guard execution passed; SQL rendering inspected |
| MIGRATE-06 | Missing outer transaction, unknown acquisition result, or transaction-breaking migration API | Fail closed; keep chain-wide ownership; no accidental switch to per-revision/autocommit execution | Unit/source gate passed; future DDL design still requires review |
| MIGRATE-07 | Duplicate deployment jobs, old/new API and worker traffic during index build, provider/database restart | One controlled migrator, measured maintenance duration, compatible readers/writers, bounded recovery and retry ownership | Hosted T5 gate open |
| MIGRATE-08 | Manual DDL bypasses the cooperative guard or an operator strips the generated SQL transaction | Prevent through roles/runbook/review; do not claim the advisory lock makes arbitrary writers safe | Operational/security review open |
| MIGRATE-09 | Missing, zero, malformed, oversized or conflicting timeout configuration | Safe defaults for absent values; invalid values rejected before DB connection without reflecting input; limits scoped to migration service | 21 unit limit cases, one Compose scope check and an actual CLI refusal passed |
| MIGRATE-10 | Ordinary writer blocks the index upgrade's table lock | Configured lock timeout, fixed CLI diagnostic, unchanged version/index, released migration ownership, successful retry after blocker exits | Real Alembic/PostgreSQL case passed |
| MIGRATE-11 | SQL exceeds its statement limit using online or generated-script settings | Database cancellation, transaction rollback, restored prior settings and released advisory lock | Two real PostgreSQL statement-cancellation cases passed; not a large-index timing benchmark |
| MIGRATE-12 | Connection stall, idle migration code, or many individually bounded statements exceed total rollout budget | Separate outer deployment deadline and a reviewed stop/recovery procedure | Hosted orchestration gate open |

The timeout additions are in `test_migration_limits.py` and
`test_migration_timeouts.py`. Defaults are 5s per lock wait and 300s per statement;
neither timeout may be disabled with zero. Calibration in T5 must use representative
data and the agreed maintenance budget. Do not treat a successful retry on an
empty local database as proof that increasing a timeout makes a live upgrade safe.
Run generated SQL as one transaction with stop-on-error enabled, preserving both
the advisory guard and timeout statements.

T0 checks migration source and offline SQL; T1 checks fail-closed acquisition.
T2/T3 run synthetic data, actual subprocess contention and the release matrix
above. T5 repeats with the deployed DB role/provider, representative history,
traffic and failure injection, capturing version, exit status, lock ownership,
upgrade duration, API errors and recovery time without personal data. T6 staff
must distinguish a busy migrator, a data-conflict refusal and a failed migration,
identify the owner and authorize a bounded retry without editing version rows.
T7/T8 promotion requires this rehearsal before a controlled client-version rollout
and real-user pilot. T9/T10 re-run upgrade/compatibility/restore acceptance for each
release and city expansion; never inject conflicting data or kill a production
migrator as an unapproved live experiment. The advisory lock is not a DDL timeout
or evidence that a migration can be run without a maintenance window.

### Security-incident system matrix

At T2, simulate compromised passenger, driver and staff accounts plus a leaked
provider credential. Cover missing/reused idempotency keys, malformed and
timezone-naive timestamps, invalid lifecycle jumps, stale versions, manual use
of lifecycle-only timeline kinds, missing references, cross-market/city access,
cross-scope audit links, hostile summaries and ordinary participant tokens.

At T3, run real PostGIS cases for concurrent timeline append/transition, unique
sequence assignment, transaction rollback, exact-scope list counts, append-only
`UPDATE`/`DELETE` trigger refusal, account/session containment audit linking and
maker-checker grant-revocation linkage. Reconcile incident state, timeline and
general audit metadata; narrative can exist only on the restricted incident
record/timeline and must not appear in general audit, logs, metrics or errors.

T4 adds the protected web workspace: keyboard/screen-reader operation, 200% zoom,
RTL, stale refresh, MFA step-up, network loss and no automatic command replay. T5
must create a synthetic incident from a real hosted alert and exercise a
disposable provider-secret rotation, synthetic session containment, pager
delivery, failover and bounded evidence preservation. T6 named staff then run
four tabletop/technical drills without database edits and record containment
time, communication decision, recovery and postmortem owner. T7 exercises field
pause/support with consenting staff devices; T8/T9 require signed incident review
for each real-user exposure window and stop immediately on any S0 event.

### Promotion gate

Every fresh-database suite passes repeatedly without order dependence. Backup/
restore reaches the current head. No cross-scope row or personal payload appears
in logs, metrics, live hints or aggregate analytics.

## 9. Phase T4 — emulator, browser, and physical-device lab

### Supported matrix definition

Before running, approve minimum/supported Android and iOS versions, representative
low/mid/high devices, screen sizes/densities, and Chrome/Firefox/Safari versions.
Include at least one lower-memory Android device and one real iPhone. Emulators do
not replace camera/file picker, location, push, background, battery or map proof.

The executable source of this matrix is
`infra/testing/t4-lab-catalog.json`, validated by
`infra/scripts/validate_t4_lab_evidence.py`. It contains 56 closed cases, eight
for each phase-required evidence class. A populated evidence record must preserve
catalog order, attach a controlled reference, SHA-256, UTC timestamp and tester
reference to every case, and link every failed/blocked case to a defect. Evidence
classes can complete independently, but T4 is complete only at 56/56; this
validator never grants phase or deployment acceptance.

The current MapLibre Compose 0.14.0 iOS KLIB contains a publisher-runner
framework path (upstream issue `maplibre-compose#824`). Until a reviewed upstream
fix or dependency upgrade removes it, CI compiles Kotlin production/test sources
and links both role apps through Xcode but does not execute the Gradle native
test binary. That limitation is recorded in the run summary and cannot be
treated as T4 evidence.

### Mobile matrix

For passenger and driver artifacts separately test:

* clean install, first launch, registration/login, relaunch and token refresh;
  on iOS verify that before-first-unlock Keychain unavailability is explicit and
  does not claim success, then verify save/restore/logout while unlocked, after
  relock, after process kill and across an interrupted/retried save; prove no
  split token pair, stale pre-release item or silent Security-framework failure
  remains;
* create/save/rotate recovery codes, reset while signed out, revoke another and
  the current session, change password, process death while a secret is shown,
  screenshots/clipboard/accessibility exposure, and recovery with no network;
* upgrade from previous supported build and incompatible-minimum-version state;
* EN/FR/AR, RTL, largest font, screen reader, contrast, reduced motion and touch
  target behavior;
* location denied, approximate/precise where supported, services off, stale fix,
  permission re-enable, foreground 15/10-second cadence, ordinary-command
  priority, 60-second failure backoff, app background/foreground transitions and
  proof that no automatic request opens permission UI or emits in background;
* push denied/granted/revoked, foreground/background/terminated delivery, token
  rotation, duplicate/out-of-order notification and authoritative refresh;
* MapLibre production/fallback style, pickup/destination, route overlay,
  narration, reroute, tunnel/GPS loss and provider outage;
* Wi-Fi/mobile transition, high latency, packet loss, offline, server timeout,
  retry, app kill and process recreation during every ride state;
* document picker MIME/size/error, scanner pending/rejected, review retrieval and
  no local sensitive-file leakage;
* cash/manual transfer/refund/support/safety/fixed-route/scheduled surfaces; and
* intentional crash, symbol upload, symbolicated report and privacy review.

For the first bounded Android evidence slice, run each role separately through
`run-android-device.ps1` with `-RegistrationSmoke -ConfirmClearAppData` and a
new `-EvidencePath`. The report records Android SDK, ABI, manufacturer/model,
locale, screen dimensions, package identity/version and backend-confirmed
registration/login gates. It deliberately captures no raw serial, screenshots,
credentials or submitted values and sets T4/deployment acceptance false. This
smoke is not evidence for ride, map, push, lifecycle, network-failure,
accessibility, crash, iOS or browser behavior.

### Browser matrix

Test public applicant and protected operations routes separately:

* routing cannot boot the wrong composition root;
* registration/login, cookie security, CSRF rotation, MFA/recovery code,
  recent-MFA step-up, logout and expired session;
* keyboard-only and screen-reader operation, visible focus, 200% zoom, RTL,
  responsive layouts and table alternatives;
* scope switching and cross-scope denial;
* every operations module's loading/empty/error/conflict/success states;
* document upload/retrieval/no-store behavior;
* CSP, frame, MIME, referrer, cache and source-map headers;
* back/forward/reload/deep-link behavior without replaying sensitive commands;
* supported-browser fallback from Wasm to JavaScript; and
* network/provider outage with no invented success or leaked raw error.

### Promotion gate

All critical journeys pass on the approved matrix. No P0/P1 accessibility,
security, crash, data-loss or state-authority defect remains. Screenshots and
recordings are reviewed in all launch languages.

## 10. Phase T5 — production-like hosted staging

T5 cannot start from an informal cloud-console checklist. The protected target
record must pass `infra/scripts/validate_production_environment_inventory.py`
with `--inventory <record> --require-accepted`, binding the immutable source
commit to distinct environment boundaries, exact DNS/TLS origins, reviewed
network/IAM policy, digest-pinned core images, secret rotation, cost ownership and
rollback evidence. This accepts only GAP-002; the phase index must still establish
every T5 evidence class and sign-off.

Database claims use the separate protected GAP-003 record. It must pass
`infra/scripts/validate_managed_postgis_evidence.py` with
`--evidence <record> --require-accepted` after the real provider's current-head
migration, encrypted PITR restore, failover, least-privilege, capacity and
retention-expiry exercises. Passing the record accepts only GAP-003; it does not
replace the T5 `RESTORE_FAILOVER_ROLLBACK_REPORT`, `RPO_RTO_AND_COST_ACCEPTANCE`,
security retest, or phase sign-off.

The executable [synthetic HTTP workload runbook](testing_workloads.md) maps
LOAD-01 through LOAD-12 onto T1–T10. Its passenger request/cancel and paired cash
completion scenarios are T3 write/dispatch/financial regression baselines. A
bounded constant-rate passenger runner now provides open-loop arrival scheduling,
queue-lag and peak-concurrency evidence plus a four-arrival real-HTTP/PostGIS
reconciliation. A strict target-independent profile now executes mandatory
WARMUP/STEADY/BURST/RECOVERY phases, produces a semantic digest, and stops later
phases after failure. When connected to protected Prometheus, every phase samples
22 fixed aggregate application/worker/queue/log-delivery/PostgreSQL/pool expressions
and checks 21 profile-bound thresholds; missing, labelled, malformed, oversized or
non-finite results make monitoring evidence incomplete and stop promotion. Its
DRAFT template is not owner approval. These tools are not the sustained
full-service, actually approved or hosted capacity and host-resource evidence
required in this phase. The PostgreSQL subset now covers snapshot availability,
connection use/limit, active connections, waiting locks and deadlocks without
database, session, user or query labels. Per-process pool gauges cover pool
availability, size, checked-in, checked-out and overflow plus checkout-wait p95
and timeout increases, while explicit startup settings bound size, overflow and
checkout timeout. A local real-PostGIS test exhausts a size-one pool and proves
the timeout path; host resources, query plans and approved hosted thresholds
remain open. The five real-HTTP cash cases include zero/flat/percentage fees and
non-2xx responses after completion/settlement commit; they do not prove real cash
collection, payout, physical trip durations or the remaining transfer/refund paths.

### Fidelity requirements

Staging uses the same topology, TLS/proxy rules, image digests, migration process,
secret boundary, monitoring, routing engine, tile/style source, document storage/
scanner class, Firebase/APNs integration and pager class intended for production.
It uses separate accounts, keys, recipients and data.

### Reliability and capacity

Define a workload from the bounded pilot and projected city peak. Measure p50,
p95 and p99 latency; errors; database CPU/IO/connections/locks; worker loop age;
offer expiry; queue/dead-letter depth; push delivery; route latency; and client
crash-free sessions. Test sustained and burst load with privacy-safe synthetic
geography.

Inject:

* API replica and worker process loss;
* database connection exhaustion, restart and failover;
* delayed/duplicate worker execution and expired leases;
* routing, tiles, geocoding, FCM/APNs, scanner and pager timeout/outage;
* object-storage denial/full quota;
* dead-letter accumulation;
* clock boundaries for fares, schedules, MFA and retention;
* deployment with failed migration/readiness; and
* rollback/forward-fix plus emergency city pause.

### Monitoring and alert-routing acceptance

Run these cases against the actual staging image digests and protected receiver
endpoints. Parser/configuration checks are T0/T1 evidence only; screenshots of a
green Prometheus target without the corresponding failure/receipt trace are not
acceptance.

| Case | Injection and required result | Evidence required |
| --- | --- | --- |
| MON-T5-01 | Run `validate-monitoring-runtime.ps1` with the candidate image and secret files; any mutable image, mismatched bearer file, weak/reused Grafana credential, non-HTTPS receiver, invalid rule/route/Loki/Alloy/dashboard, failed hardened component readiness, failed two-role ingestion/filter check, Grafana startup, or merged Compose error stops deployment | Redacted command result, five monitoring image digests plus hashes of collector/rule/route/log/provisioning artifacts, bounded two-stream result, zero secret values |
| MON-T5-02 | Scrape API and worker separately; correct bearer succeeds, absent/wrong bearer returns `401`, and neither metrics endpoint is reachable from public ingress | Target state/history, private-network probe, external denial trace |
| MON-T5-03 | Stop the API while worker remains healthy, then reverse roles; API and worker labels remain distinct and zero series from one process cannot mask the missing target | `up` timeline, firing and resolved alert timestamps |
| MON-T5-04 | Break database access without killing processes; readiness fails and database/outbox availability alerts fire while process and pool telemetry remain scrapeable | Readiness/metric/alert timeline and sanitized logs |
| MON-T5-05 | Stall and terminate each of the eight worker loops/processes; missing/error/stalled alerts identify only the fixed worker label and recover after restart | Eight-case matrix, primary receipt and resolution timestamps |
| MON-T5-06 | Create one reviewed dead letter for dispatch, scheduling and driver compliance, plus one unsupported synthetic topic; each reaches only its owner receiver and `unclassified` reaches platform duty | Four receiver payload digests, queue facts and owner acknowledgements without business payloads |
| MON-T5-07 | Make one receiver return timeout, `429` and `500`, then recover; Alertmanager retries without losing other owner notifications and duplicate delivery is safely tolerated | Receiver request IDs/counts, retry timing, no leaked URL/token |
| MON-T5-08 | Restart Prometheus and Alertmanager separately and together during firing alerts; persisted time-series/notification state respects the documented repeat interval and emits resolution after recovery | Volume/config identity, before/after alerts, duplicate analysis |
| MON-T5-09 | Exhaust the reviewed Prometheus storage ceiling and age data past retention; service remains bounded, capacity alerts/runbook act before loss of required incident evidence | Disk-growth curve, retention proof, stop/expand decision |
| MON-T5-10 | Attempt public access to ports 9090/9093/3000/3100/12345 and all internal metric/log aliases; only loopback/approved authenticated operator tunnel works and the public TLS proxy rejects internal Host values | Network scan, proxy logs and access-control review |
| MON-T5-11 | Inject metric/alert names and application errors resembling identifiers or secrets; source normalization plus alert relabeling prevents user/driver/passenger/device/ride/resource/authorization/payload/topic data reaching receivers | Captured scrape and receiver payload review with synthetic canaries |
| MON-T5-12 | Disable the primary receiver during a critical alert; the approved external receiver/on-call policy reaches backup duty within the target, and T6 staff acknowledge/escalate from the runbook | Primary failure, backup receipt, acknowledgement and escalation timeline |
| MON-T5-13 | Start Grafana from a fresh named volume with the candidate digest; login succeeds only with the secret-file administrator credential, the internal datasource is healthy, and the immutable `TaxiMobile Operations` dashboard contains exactly the 26 reviewed panels after restart | Image/config/dashboard hashes, health/login trace, datasource result, panel inventory before/after restart |
| MON-T5-14 | Inspect every provisioned query and inject privacy canaries into source errors and request paths; only normalized route/status/error, fixed worker and fixed owner dimensions appear, with no private label, external link, variable or browser-side datasource request | Exported dashboard JSON hash, Prometheus query audit and canary capture reviewed by privacy owner |
| MON-T5-15 | Repeat API loss, worker stall/error, latency/5xx, unavailable database/outbox/pool snapshots, pool checkout/overflow, owner backlog/age/dead-letter and recovery injections while staff use the dashboard; each panel changes consistently with its alert and no missing series is interpreted as healthy zero | Synchronized dashboard/alert/source timeline, diagnosis worksheet and false-positive/false-negative findings |
| MON-T5-16 | Verify anonymous, wrong-password, public-network and unauthorized staff access fail; approved named staff use the protected tunnel/TLS path, then rotate the existing-volume administrator credential and revoke old sessions without deleting dashboard evidence | Access matrix, network trace, named-role review, rotation/session-revocation record with secrets redacted |
| MON-T5-17 | Fill/restart/restore the Grafana state volume and remove/recreate only disposable staging state; file-provisioned dashboard identity returns, account/preferences recovery follows the approved backup policy, and changing only the initial secret file is not mistaken for credential rotation | Capacity curve, backup/restore record, dashboard UID/hash and credential-behavior evidence |
| MON-T5-18 | Start the candidate API and worker as UID/GID 2000 with fresh separate volumes; emit enough events to cross every rotation boundary, then read as Alloy UID 473 plus group 2000 | File inventory proving owner `2000:2000`, mode `0640`, no more than active plus configured backups, valid JSON in every file, role isolation, and collector read-only denial of writes |
| MON-T5-19 | Feed valid API/worker JSON, malformed JSON, invalid timestamps, a 16-KiB boundary line, and an over-16-KiB line through the real Alloy/Loki pair | Query result contains only allowed lines under exactly `service=api|worker`; rejection counters/alerts rise without rejected contents entering logs, tickets, labels, or receiver payloads |
| MON-T5-20 | Add synthetic user/driver/ride/location/token canaries to forbidden logger extras, exception text, raw URLs, and direct tamper fixtures | Application JSON allowlist omits forbidden extras/raw paths; collector creates no dynamic label; dashboard/query/export review finds no canary; any direct malformed/tampered line is rejected or incident-contained |
| MON-T5-21 | Stop Loki during sustained bounded log production, restore it before and after retry pressure, then force a terminal rejected batch | Alloy retry and dropped-entry alerts fire/resolved at reviewed thresholds; buffered resource use stays bounded; accepted events are neither silently lost nor duplicated beyond the documented at-least-once contract |
| MON-T5-22 | Restart Alloy before/while/after file rotation and restart Loki with unflushed/current data; repeat with the Alloy position volume present, restored, corrupt, and absent | Position/WAL evidence, expected replay window, no unexplained gaps, duplicate count, recovery timing, and runbook decision for restoring versus recreating collector state |
| MON-T5-23 | Age synthetic logs across 30 days and run compactor cycles; separately attempt stale ingestion and over-lookback queries | Stale writes are rejected, queries cannot exceed 30 days, expired chunks/index entries are deleted after the documented delay, and required incident/legal evidence policy is reconciled with this limit |
| MON-T5-24 | Fill Loki storage progressively, deny writes, corrupt a disposable copy, back up and restore to a fresh instance | Capacity alert precedes exhaustion; API/worker continue safely; restore yields an integrity-checked query set and measured RPO/RTO; unrecoverable state triggers the documented evidence-loss incident rather than silent reset |
| MON-T5-25 | Exercise the immutable three-panel log dashboard against normal volume, ERROR/CRITICAL events, empty role, stopped collector/store, delayed data, and rejected lines | Panel/query/alert timeline, no missing series interpreted as healthy, fixed service-only selectors, bounded result size, and diagnosis worksheet completed by an authorized operator |
| MON-T5-26 | Attempt anonymous, wrong-role, public-network, direct-Loki, path traversal, datasource edit, dashboard edit, and export access; rotate named staff credentials and terminate sessions | Access-denial traces, immutable provisioning hashes, audit/rotation/session evidence, and confirmation that Loki's lack of native auth is contained by network and Grafana rather than publicly exposed |
| MON-T5-27 | Request one disabled `/api/v1/admin/*` path and verify only `blocked` rises, then enable compatibility in an isolated test process and make one routed request; `served` rises, deprecation headers appear, and the critical legacy-route alert fires without a raw path or identifier entering metrics/logs | Source scan, two fixed metric series, response headers, alert/resolve timeline and redacted request evidence |
| MON-T5-27 | Deploy two API and two worker replicas using per-replica volumes and collectors; rotate/restart replicas independently and correlate a synthetic journey by server request ID without indexing it | Four-source inventory with only fixed role labels, no shared-file rotation races, complete bounded journey trace, replica-loss alert, resource/cost curve, and approved threshold for moving from single-node filesystem Loki to HA/object storage |

Stop T5 on a publicly reachable monitoring surface, cross-owner delivery,
missing critical resolution, secret/private label disclosure, unbounded storage,
unauthorized dashboard access, unexplained accepted-line loss/duplication,
shared-file replica races, dashboard/alert disagreement, failed credential
rotation, or an alert that remains invisible to both primary and backup duty.

### Security and privacy

Run the `SEC-01` through `SEC-11` packs in
[`threat_model.md`](threat_model.md): threat-model review, SAST,
dependency/container scans, SBOM validation, DAST,
authorization/IDOR tests, CSRF/CSP/cookie checks, upload attacks, rate-limit abuse,
session/grant/key revocation, log/metric redaction, backup access and independent
penetration testing. Re-test findings against the same candidate.

### Promotion gate

Agreed SLO/RPO/RTO and capacity headroom pass. Alerts reach primary and backup
responders. Current-head restore, credential rotation and rollback are measured.
No unresolved critical/high finding lacks approved bounded mitigation.

## 11. Phase T6 — trained staff rehearsal with synthetic journeys

### Participants

Named market/city administrators, recruitment reviewers, finance reviewers,
support/safety staff, release operator, database/infrastructure responder and
privacy/legal observer. All use production-like least-privilege accounts and MFA.

### Rehearsal day

Run a scripted “city in a day” without real customers or documents:

1. Bootstrap, two-person joiner/mover/leaver grant review, bounded-expiry and
   recertification review, MFA recovery, leaver revocation, attempted self-grant,
   and a witnessed cross-market account-containment/recovery exercise.
2. Configure city/service area/operator/tariff/payment/fixed-route/schedule.
3. Process fictional driver applications and safe synthetic documents.
4. Activate a pilot bundle through maker/reviewer controls.
   The configuration submitter must be rejected from both configuration approval
   and readiness decisions; use an independently authorized reviewer and retain
   the controlled evidence record with accountable owners and review/expiry dates.
5. Run immediate, fixed-route and scheduled synthetic rides.
6. Reconcile cash/transfer/refund and explain every ledger fact.
7. Handle routine support and urgent safety cases with pager and shift handoff.
8. Diagnose injected API/worker/provider failure from dashboards and runbooks.
9. Pause the city, preserve active-state safety, recover, and resume.
10. Restore a backup, execute release rollback/forward-fix and close the review.

### Promotion gate

Staff complete procedures without developer/database intervention except where a
documented break-glass runbook requires it. Response and recovery times meet
targets. Access, audit, communication and residual-risk reviews are signed.

## 12. Phase T7 — closed-cohort, non-public field validation

### Purpose and boundaries

Validate real devices, roads, GPS, routing, driver workflow and operational
coordination before carrying paying public passengers. Participants are trained,
consenting staff and a small invited group of licensed drivers. Use empty-car,
shadow, or staff-only journeys under approved insurance/legal conditions. Do not
collect production driver documents or money until the corresponding P0 gates are
accepted.

### Field scenarios

* dense center, edge of service area, narrow/one-way roads, roundabouts,
  station/landmark pickups, weak coverage and GPS obstruction;
* driver offline/online/location freshness, competing offers, decline/expiry,
  navigation to pickup, arrival/start/complete and stale route;
* passenger and driver app kill/restart, battery use and long shift;
* push delay/loss and fallback refresh;
* Arabic/French/Latin place discovery and spoken maneuver comprehension;
* fixed-route stop/direction/geometry recognition;
* scheduled punctuality, overlap and fallback;
* dispatcher/support contact and vehicle/participant mismatch handling; and
* monitoring, pause and rollback while devices are in the field.

### Promotion gate

Route and pickup accuracy, location freshness, battery, notification delivery,
crash rate, task completion, driver comprehension and support response meet the
pre-approved thresholds. All participants can stop and report safely. Findings
are reviewed with drivers before a real-user pilot.

## 13. Phase T8 — bounded real-user city pilot

### Preconditions

All applicable P0 gaps in [`gaps.md`](gaps.md) are deployment-accepted. Legal,
privacy, insurance, tariff, payment, safety, provider and operator approvals are
current. Signed production artifacts and the exact active configuration bundle
are frozen. A public support contact, incident roster, city pause owner and
go/no-go board are active.

### Cohort and rollout

Start with a small invited passenger cohort and licensed driver cohort in one
bounded service area and operating window. Increase users, hours, geography and
features independently. Keep fixed routes, scheduling or manual transfer disabled
until their own acceptance evidence is complete. Cash remains available.

### Pilot observation

Measure only approved aggregate definitions:

* availability, estimate/request success and assignment time;
* offer acceptance/decline/expiry and fairness distribution;
* pickup ETA error, cancellation and completion;
* route/navigation failures and geocoding correction;
* cash/transfer/refund reconciliation and unresolved aging;
* scheduled fulfillment and fixed-route comprehension;
* app crash, API availability, worker lag, push delivery and provider errors;
* support/safety volume and acknowledgement/resolution time;
* onboarding completion/rejection reasons with suppression; and
* passenger/driver accessibility, trust, task success and qualitative feedback.

### Stop conditions

Immediately pause expansion, and pause the city when appropriate, for:

* safety incident linked to system behavior;
* cross-user/city/operator data exposure or account compromise;
* unreconciled or misdirected customer money;
* wrong-driver/ride assignment or authority bypass;
* systemic stale location, route, notification or outage with unsafe impact;
* inability to page/respond to urgent cases;
* database loss/corruption or failed recovery boundary;
* materially excessive crash/failure rate; or
* legal/provider approval withdrawal.

### Promotion gate

Complete the pre-declared observation period and minimum privacy-safe sample.
Resolve launch-blocking defects, reconcile all rides/money/cases, review driver
and passenger feedback, complete post-launch readiness evidence, and obtain a
recorded independent go/no-go decision.

## 14. Phase T9 — guarded public city launch

Use percentage/invitation/geographic rollout where platform distribution allows.
Monitor release, provider and operational SLOs continuously. Review daily during
initial launch and weekly afterward. Preserve previous compatible mobile/web
artifacts, database forward-fix plan, city pause and participant communication.

Do not add an untested feature while increasing cohort size. A new tariff,
payment recipient, route, schedule policy or configuration bundle repeats the
relevant T2–T8 subset and receives a new readiness decision.

Exit requires a completed city post-launch review, stable SLOs, reconciled money,
closed/owned cases, accepted residual risk, trained replacement staff and a clear
decision on whether the model is repeatable.

## 15. Phase T10 — second city and national scale

Treat every city as new evidence, not a clone. Repeat legal, operator, service
area, tariff, provider coverage, recruitment, location, routes, language,
payments, safety staffing and pilot acceptance. Run adversarial multi-city tests
before activation and prove one city can pause/fail without leaking data or
degrading another.

Expansion adds capacity only after measured need. Test multi-replica leases,
PostGIS plans, pools, queues, analytics suppression and staff scope at projected
national load. Complete cooperative review of fairness, fees and driver outcomes
before materially changing dispatch or economics.

## 16. Place-discovery acceptance track

This track closes the source-to-field portion of `GAP-008`. It supplements, and
does not replace, the universal phase gates above. Each test case uses a stable
identifier so a city-readiness record can link to evidence without embedding a
query, precise participant location, or provider payload.

### 16.1 Corpus and measurement contract

Before T2, create a reviewed, versioned fixture corpus for Rabat and the first
pilot city. Each city corpus must contain all of the following in Arabic script,
French/Latin spelling, common transliteration, and representative misspelling:

* central station, airport, hospital, university, government office and major
  landmark;
* full address, street without number, neighborhood, municipality and duplicate
  street names in different neighborhoods;
* named pickup entrance distinct from a building centroid;
* inside-boundary, boundary-edge, outside-boundary and wrong-city coordinates;
* punctuation, diacritic, whitespace and mixed-script variants; and
* deliberately absent, ambiguous and provider-malformed cases.

Every expected result records the acceptable place set, not one brittle provider
rank, plus expected result kind, language quality, coordinate tolerance,
serviceability, safe fallback, and whether correction is required. Corpus source,
license, reviewer, capture date and provider data snapshot/version are mandatory.
Real home/work labels or participant histories are prohibited.

Before T5, product, operations, privacy and engineering approve numeric thresholds
for search success, top-result relevance, coordinate/pickup error, correction
rate, latency, availability, quota headroom, task completion, accessibility,
abandonment and provider cost. The threshold sheet records numerator,
denominator, percentile, sample size, segment, observation window, owner and stop
condition. A threshold chosen after viewing results is exploratory evidence only
and cannot authorize promotion.

### 16.2 T0/T1 — source and adapter gates

| ID | Test | Required proof |
| --- | --- | --- |
| `PLACE-T0-01` | OpenAPI/mobile route contract | Search and reverse paths, closed languages, bounds, error envelope and normalized fields match. |
| `PLACE-T0-02` | Deployment configuration | Provider defaults to disabled; invalid provider/URL/user agent/limits fail startup; hosted HTTP and shared public Nominatim fail closed; keys are API-only. |
| `PLACE-T1-01` | Search normalization | Whitespace and language normalize; country/viewbox constraints, limit, address details and attribution are forwarded exactly once. |
| `PLACE-T1-02` | Provider response hostility | Empty, duplicate, missing coordinate/name, oversized, wrong type, non-finite coordinate, invalid JSON/status and timeout responses become bounded normalized results or safe unavailability. |
| `PLACE-T1-03` | Reverse authority | Returned coordinate is exactly the requested map point even when provider centroid differs; no result remains a usable unnamed point. |
| `PLACE-T1-04` | UI reducer/coordinator | Debounce, explicit retry, stale response, pending action, no results, unknown kind, outage and selected-coordinate preservation use deterministic fakes. |
| `PLACE-T1-05` | Localization/accessibility source | EN/FR/AR keys match, RTL/LTR text is safe, controls have semantic names and outside-pickup results are disabled without color-only meaning. |

### 16.3 T2 — simulated passenger matrix

Run each corpus family as a new and returning passenger in EN, FR and AR. Repeat
with denied location, no location fix, slow network, provider `503`, rate `429`,
no result, city switch and an out-of-order older response. Verify:

1. opening search never moves or invents a map coordinate;
2. debounce produces one bounded request and explicit retry is possible;
3. selecting a result preserves the backend coordinate and readable label;
4. an outside-area result cannot become pickup but can remain a destination;
5. reverse lookup adds a label without replacing the selected map point;
6. attribution remains visible with results;
7. failure keeps map/manual selection usable and never claims a successful lookup;
8. changing city invalidates results from the previous city; and
9. query text, provider IDs and raw payloads do not enter telemetry, audit facts,
   screenshots or user-visible errors.

Evidence is the deterministic test report, request counts, normalized snapshots
and privacy canary scan. It must not contain the original free-text queries.

### 16.4 T3 — fresh PostGIS and multi-instance authority

On a newly migrated isolated database, prove `PLACE-T3-01` through `PLACE-T3-08`:

* only a `PILOT`/`ACTIVE` city with an active configuration, active effective
  service area, enabled `ON_DEMAND` service and active effective operator
  assignment can be searched;
* polygon holes, boundary points, near-edge precision and outside points use
  exact `ST_Covers` authority rather than provider locality text or bounding box;
* replacing a city configuration/service-area version changes subsequent
  decisions without rewriting a prior selected coordinate;
* same place candidates in two cities receive independent city decisions;
* disabled/paused/retired/expired configurations fail without calling the
  external provider;
* account quotas are independent, shared across API replicas, and fail closed
  when their shared storage cannot be checked;
* timeout/malformed/no-result paths neither commit application rows nor leak
  queries in database/audit/application/proxy logs; and
* concurrent search/reverse requests preserve ordering metadata at the client
  boundary and never alter ride/pricing authority.

Capture SQL test IDs, migration head, query plans at projected corpus batch size,
redacted logs and provider-stub call counts.

### 16.5 T4 — emulator and physical-device usability

Use the approved Android/iOS matrix with low/mid/high devices and largest text,
screen reader, RTL, portrait/landscape, light/dark display and reduced motion.
For each language, a participant must find station, landmark, full address and
neighborhood; correct an ambiguous result; choose a map fallback; identify an
outside pickup; reverse-label a pin; and recover after process death and network
loss. Test fast typing, deleting, IME search, touch targets, scroll/keyboard
occlusion and long labels.

Record anonymized task completion, time, corrections, abandonments, assistance,
selected-coordinate error and comprehension. Screen recordings require consent
and redaction. A crash, inaccessible critical control, silent coordinate change,
wrong-city pickup, or inability to use the fallback is an S0/S1 stop.

### 16.6 T5/T6 — real provider and operations rehearsal

In production-like staging, pin the provider deployment/image and data snapshot.
Run the full corpus at sustained and burst pilot load, then inject DNS failure,
TLS failure, timeout, `429`, `5xx`, malformed body, stale data, restart and quota
exhaustion. Measure p50/p95/p99 end-to-end and provider latency, normalized error
rate, cache behavior if later approved, connection/resource saturation and quota
headroom. Verify the public API never becomes a generic proxy and cannot target a
caller-supplied host.

Privacy/legal review must cover data/extract license, attribution placement,
provider terms, query egress and jurisdiction, retention, subprocessors,
deletion/incident process and documented purpose. Operations then rehearses
provider disablement, fallback communication, alert triage, credential rotation,
data refresh, rollback and recovery without database editing. Do not enable
production search merely because the adapter can reach staging.

### 16.7 T7 — closed-road validation

Consenting staff and invited licensed drivers run empty-car or staff-only pickup
exercises at dense streets, station entrances, landmarks, one-way roads, service
edges, GPS-obstructed locations and weak-network zones. Compare searched and
reverse-labeled points with the safe legal pickup actually used. Test Arabic,
French and common Latin transliterations in each zone and record correction
reason categories without retaining a participant route history.

Promotion requires the pre-approved relevance, pickup-error, correction,
completion and accessibility thresholds, no unresolved unsafe-pickup pattern,
successful outage fallback, and joint sign-off from engineering, operations,
privacy and representative drivers.

### 16.8 T8/T9 — bounded real users and launch monitoring

Enable by frozen city/configuration and cohort, never nationally at once. Monitor
privacy-safe aggregate search availability, latency, no-result, correction,
map-fallback, booking continuation and support-contact rates by city/language and
app version. Suppress small cohorts and prohibit query text, result labels or
precise coordinates from analytics. Compare against the frozen T5/T7 baseline.

Pause geocoding or city expansion for systematic wrong-city/unsafe pickup,
silent coordinate mutation, provider/license withdrawal, privacy leakage,
threshold breach over the declared window, unusable fallback or provider failure
that threatens ride safety. T9 exit requires a signed review of every threshold,
incident, correction cluster and open defect. T10 repeats the corpus, provider
coverage and field gates for every new city; success in Casablanca or Rabat does
not prove another city.

### 16.9 Required evidence bundle

The immutable bundle for `GAP-008` contains corpus version/digest, license and
privacy decisions, provider/data/image versions, configuration digest, automated
reports, PostGIS plan and boundary results, device matrix, usability summary,
staging load/chaos report, field report, approved threshold sheet, monitoring
dashboard definition, incident/disablement rehearsal and signed go/no-go record.
Absent evidence is recorded as absent and keeps the gap open; it is never replaced
with a source-code assertion.

## 17. Participant-coordination acceptance track

This track closes `GAP-023`. The tested product is the six-code, assigned-ride
signal channel documented in `rides.md` and `api.md`; adding free text, phone
exposure, or calling changes the risk model and requires a new design and test
plan. Use synthetic rides through T6. T7 may use consented closed-cohort road
journeys under the field safety plan; T8 is the first bounded real-user service.

### 17.1 T0–T1 — source, schema, unit, and component gates

Required automated evidence:

* the migration upgrades a fresh database and downgrades/re-upgrades in the
  repository migration harness without losing unrelated ride data;
* the database and API accept exactly six codes, and OpenAPI/mobile decoders
  tolerate an unknown future response value without presenting it as an action;
* message rows contain no body, phone, recipient contact, attachment, arbitrary
  metadata, or provider payload;
* passenger and driver code policy is exhaustive and role-disjoint;
* all four allowed active states and all pre-assignment/terminal states are unit
  tested, including a state change at the command boundary;
* idempotent replay creates one message, notification and outbox event, while a
  reused key with changed input is rejected;
* minute limiting and the 100-message sender/ride cap have boundary, reset and
  independent-passenger/driver tests;
* detailed ride serialization returns only the latest signal while active and no
  signal when terminal;
* worker tests cover exact recipient, generic payload, stale suppression,
  terminal suppression, retry and dead-letter behavior;
* English, French, and Arabic catalogs have exact key parity, RTL-safe text, and
  localized notification mapping for every code; and
* Compose component tests prove three role-correct actions, no raw unknown action,
  selected-action progress identity, disabled competing actions, and preserved
  cancellation/transition controls.

Exit requires green source/format/security validators, backend tests, shared JVM
tests, both Android role compiles, JS/Wasm compilation, and macOS iOS compilation
from the same immutable candidate.

### 17.2 T2 — simulated persona and adversarial contract matrix

Build deterministic fixtures for a passenger, assigned driver, unrelated driver,
unrelated passenger, suspended account, operations staff account, and rides in
every state. Execute both roles against each of their three valid codes and then
cover:

* each role sending every opposite-role code and unknown/malformed codes;
* no driver, replaced driver, unrelated same-city user, different-city user,
  staff token, wrong token audience, expired session and suspended account;
* missing ride, malformed UUID, unexpected JSON fields, missing/short/long
  idempotency keys, same-key replay and same-key/different-body conflict;
* one below, at, and above the rate threshold; independent rides and users;
  absolute cap at 99, 100 and 101 accepted messages;
* simultaneous passenger/driver sends, duplicate concurrent sends, cancellation
  or completion racing the command, and repeated reads during those races;
* recipient notification type/resource identity for all six codes and no
  notification to the sender, unrelated users, candidates or staff;
* generic live/push hints with no code, text, contact, coordinate, fare or identity;
* delayed, duplicate and out-of-order hints followed by one authoritative reload;
* app reconnect/foreground refresh without automatic command replay; and
* logging, metrics, audit and error-body inspection for message/contact leakage.

Record exact expected status/error code for every case. Any cross-participant
read/write, role escape, duplicate durable command, or sensitive payload is S0.

### 17.3 T3 — migrated PostGIS multi-role lifecycle and concurrency

Run against a fresh isolated PostGIS database at current migration head with the
real FastAPI transaction and outbox worker. The suite must create and assign a
ride through the normal lifecycle, exchange all six signals, verify exact sender
and recipient rows, reload latest state, and close the ride. It must additionally:

* prove city/service scope cannot substitute for ride participation;
* verify row locking under send-versus-cancel, send-versus-complete, and parallel
  cap-boundary races;
* prove idempotent replay across separate API sessions/instances;
* fan out through the PostgreSQL cross-instance transport to only authorized
  connected sessions;
* process retry, invalid registration, dead letter and safe replay without
  duplicating the durable message;
* suppress worker delivery when database time makes the event older than five
  minutes or the ride terminal;
* verify query/index plans for latest-message and sender-cap reads at a reviewed
  realistic per-ride volume; and
* inspect structured logs and aggregate metrics to prove payload minimization.

Archive migration output, test report, query plans, sanitized database assertions,
worker trace and configuration digest. Local success is T3 evidence only.

### 17.4 T4 — Android/iOS device and accessibility laboratory

Use the supported Android/iOS version and form-factor matrix, at least one low-end
Android device, and release-like passenger and driver builds. Test each code in
English, French and Arabic/RTL with default and largest supported text, dark/light
appearance where supported, TalkBack/VoiceOver, switch/keyboard access where
applicable, reduced motion, and screen magnification. Verify:

* critical cancel/transition actions remain visible and operable before signals;
* only the selected action reports progress and alternatives remain understandable;
* announcements identify sender meaning without exposing a raw enum;
* foreground, background, force-stopped/terminated and restored apps converge to
  the same server state after FCM delivery, delay, duplication or loss;
* airplane mode, packet loss, 2G/high-latency simulation, Wi-Fi/cellular handoff,
  process death during send and server timeout produce no optimistic success or
  automatic replay;
* explicit retry with the same operation result does not duplicate a message;
* terminal transition removes actions/latest presentation after refresh and an
  obsolete notification cannot restore them;
* notification permission denial leaves in-app/history refresh usable;
* screenshots, notification previews, crash reports and accessibility trees
  contain no phone number, free text, coordinate or unrelated identity; and
* battery, memory, layout, tap-target, focus order and crash behavior remain
  inside the approved device budgets.

Capture device/OS/build IDs, locale, network profile, screen recording with
synthetic data, accessibility report, notification timestamps, API correlation
IDs and result. A single repeated crash, inaccessible critical action, wrong
participant, or false send confirmation blocks promotion.

### 17.5 T5 — hosted staging reliability, privacy, and abuse

Deploy immutable API/worker/web/mobile candidates across at least two API
instances with production-like PostgreSQL, shared rate-limit storage, TLS,
monitoring, and separate staging FCM/APNs projects. Execute normal load and burst
load at the agreed active-ride concurrency. Inject API-instance loss, worker loss,
database failover/reconnect, rate-store failure, FCM/APNs rejection/latency,
PostgreSQL notification loss, outbox retry exhaustion and clock-skew boundaries.

Required results are no authorization broadening, no message loss after committed
success, no duplicate durable records, bounded recovery, observable pending/dead
letter state, and authorized REST catch-up when all hints fail. Verify rate-limit
fail-closed behavior, alert ownership, safe replay, dashboard thresholds and
provider-disablement procedure. Run security abuse tests for enumeration, IDOR,
token substitution, flooding, replay, malformed payloads and telemetry leakage.

The privacy/legal owner must approve purpose, retention duration, erasure timing,
legal-hold treatment, backup expiry, notification-preview policy and processor
inventory. Exercise deletion/expiry against primary and restored staging data;
source omission from terminal ride detail is not data erasure proof.

### 17.6 T6 — trained staff synthetic rehearsal

Passenger, driver, dispatcher/support and safety-duty staff rehearse synthetic
pickup failures: passenger not visible, driver at wrong side, passenger delayed,
notification provider down, participant repeatedly signaling, ride cancelled
during a signal, app offline and participant asking for emergency help. Staff must
explain the channel's limits, use documented fallback/escalation, avoid requesting
personal phone disclosure, distinguish support from emergency response, and close
the synthetic case with an auditable handoff.

Measure acknowledgement time, incorrect advice, escalation time, unresolved
handoff, privacy deviation and staffing coverage. Exit requires a named on-call
owner, shift handoff, provider-outage runbook, abuse/report path, emergency wording
and completed corrective actions from a second rehearsal.

### 17.7 T7 — consented closed-cohort road validation

Use invited licensed drivers and test passengers on pre-reviewed routes, without
public booking and without production money unless separately authorized. Every
journey has a safety observer/stop contact, declared check-in window, withdrawal
right and no requirement to share a personal number. Balance day/night, noisy and
quiet pickup points, both road sides, weak coverage, all supported languages and
participants with representative accessibility needs.

Compare a frozen baseline procedure with the signal channel. Predefine and record:

* pickup found/not-found rate and time from assignment to mutual location;
* signals sent per journey, delivery/visibility latency and missing/duplicate rate;
* code comprehension without facilitator help and wrong-code selection;
* cancellation, fallback support contact and personal-number exchange attempts;
* driver distraction or unsafe interaction while moving;
* harassment, repeated-signal, privacy, accessibility and safety events; and
* participant confidence, perceived control and requested missing meanings.

Do not infer success from anecdotes or average latency alone. Segment results by
language, device/OS, network, route type and participant role with small-cohort
privacy suppression. Stop immediately for unsafe driving, unauthorized data
exposure, severe misunderstanding, inaccessible safety-critical controls, or an
unhandled support/escalation event. Repeat affected scenarios after fixes.

### 17.8 T8 — bounded real-user city pilot

Enable only for the approved city, service, app versions, driver roster and
passenger cohort. Freeze the six codes and configuration for the measurement
window. The owner-approved threshold sheet must define at least pickup success,
end-to-end signal visibility latency percentiles, command failure, duplicate
durable record, support-contact, cancellation, code misunderstanding, abuse and
safety-incident limits, including minimum sample size and observation period.

Monitor privacy-safe aggregates and sampled support outcomes daily; never log code
sequences with precise coordinates or build participant behavior profiles. Staff
must be on duty with provider and feature-disable procedures. A threshold breach,
S0/S1 event, systematic language/accessibility disparity, notification outage
without usable fallback, or unsupported emergency reliance pauses the pilot.
Expansion requires a signed review of incidents, support load, participant
feedback, retention operation, open defects and threshold results.

### 17.9 T9–T10 — guarded launch and city replication

Public launch remains city/configuration/version bounded with staged cohort
increments and rollback/disable authority. Compare each increment with the frozen
pilot baseline and stop rules. Review abuse and support capacity as volume grows;
the absence of free text does not remove repeated-contact or pickup safety risk.

Before a second city, rerun language, network, device, pickup-environment,
provider, staffing and legal/retention acceptance for that city. Prior-city
success cannot certify different streets, participant expectations, connectivity,
regulation or operator procedures. National expansion requires comparable
city-level evidence and an approved cross-city fairness/privacy review.

### 17.10 Required evidence bundle and closure rule

The immutable `GAP-023` bundle contains the policy/code-set decision, migration and
OpenAPI digests, automated reports, authorization/privacy matrices, device and
accessibility results, staging load/failure/security reports, retention/erasure
approval and drill, staff rehearsal, closed-road report, pilot threshold sheet,
dashboard/alert definition, incidents/defects and signed go/no-go decision. Every
artifact identifies build, environment, configuration, owner, date and result.

`GAP-023` closes only when the accountable product, engineering, security/privacy,
operations/safety, accessibility/localization and city/operator reviewers accept
their evidence. Missing evidence is recorded as missing. A source-complete feature,
provider dashboard screenshot, or successful notification on one phone is not a
substitute.

## 18. Notification-delivery acceptance track

This track closes `GAP-028` and supplies provider evidence for `GAP-009`. Use the
event matrix in `api.md` and the closed backend policy registry as the inventory.
A provider acknowledgement proves submission only; client visibility and human
comprehension require separate evidence. A notification must never authorize a
ride, assignment, fare, payment, or credential decision.

### 18.1 T0–T2 — policy, producer, and simulated-recipient gates

1. Assert every literal outbox producer has a classified policy; dynamic credential
   topics have explicit tests. Compare the backend push set with the mobile
   allowlist exactly and round-trip every live type through the real encoder.
2. Test every policy's channels, age, urgency, fallback, quiet-hour eligibility and
   owner; reject unknown hints before provider credential/network access. Confirm
   unknown topics become bounded retries/dead letters, not successful no-ops.
3. Verify business state, persistent notification, and outbox rows commit or roll
   back together. Replay an idempotent source command without duplicating rows.
4. Test just-before/at/after age and offer-expiry boundaries, superseded booking
   states, missing records, cancelled offers, revoked registrations, account
   switches, and unrelated recipient attempts. Never deliver an offer after its
   source expiry even if the event-age window is longer at worker submission.
   Assert original-source deadline propagation through every registration and
   401 refresh, floored remaining Android TTL and unchanged APNs expiry. Inject
   credential latency that exhausts the budget and prove no HTTP send. Include
   exact expiry, sub-second remainder and distant-deadline policy capping.
   Distinguish queue configuration from device-visible expiry: network and OS
   timing still require field traces and authoritative state reload.
   Test missing/cancelled parent bookings even with a pending offer row.
5. Mock provider success, 401 refresh, invalid registration, 429, 5xx, timeout,
   duplicate delivery and total loss. Verify bounded attempts, fixed error codes,
   priority/TTL, no private payload, and authoritative reload after duplicate or
   out-of-order hints. Fail live and push independently and together: both
   channels must be attempted, partial success must retry, and worker cancellation
   must stop further delivery. Test Android duration and iOS absolute queue
   expiration independently. Inject failure on the first of multiple devices and
   prove remaining devices are attempted even if the first send or invalid-token
   revocation fails. Aggregate failure must retry without renewing source lifetime;
   document duplicate behavior until durable per-device progress is implemented.
6. Check all persistent event copy in EN/FR/AR, including five scheduled events,
   six coordination codes and unknown-event fallback. Test the one-hint relay
   before login, after logout, during account switch and while no collector exists.

### 18.2 T3 — real PostGIS and worker lifecycle

Use current-head isolated PostGIS. Run every allowed live event through actual
PostgreSQL publish/listen fanout and verify only the addressed session receives
it. Create scheduled offer/commitment/handoff/fallback/unfulfilled events through
normal service transactions, then inspect minimized outbox IDs, current recipient,
state suppression and retry metadata. Race cancellation/offer acceptance with
delivery, restart workers during leases, and prove recovery without duplicate
durable commands. Verify an unknown topic reaches a visible bounded dead letter.

Current source evidence is deliberately narrower than this whole gate:

| Scheduled event | Verified database evidence | Still required |
| --- | --- | --- |
| Offer created | API commit contains one notification/outbox pair; post-flush injected failure rolls back; creation replay adds no rows | Concurrent opening workers and exact recipient/privacy matrix |
| Driver committed | Commit contains one pair; post-flush failure rolls back; duplicate acceptance is rejected without new rows | Concurrent competing drivers and recipient checks |
| Dispatch started | Successful durable assigned ride and passenger notification/outbox pair; actual worker recipient lookup; post-flush rollback; repeated handoff adds no rows; two-session duplicate handoff and both cancellation orders | Independent-worker/process and broader eligibility races; device-visible driver/passenger UX |
| Fallback matching | Successful candidate offer to another eligible driver after suspension, vehicle expiry or known credential expiry; unassigned matching ride; passenger notification/outbox pair; worker recipient lookup; post-flush rollback and repeat handoff; no-supply rollback | Multi-worker race, fallback candidate acceptance/rejection after eligibility changes, and device-visible UX |
| Unfulfilled | Commit contains one pair; post-flush failure rolls back; repeated worker run adds no rows | Multi-worker races and recipient checks |

The assertions live in `backend/tests/integration/test_published_fixed_routes.py`
and use a newly cloned migrated database, actual services and fresh-connection
reads. They inject failure only after a real outbox enqueue and SQL flush; a fake
enqueue counter would not establish transactional rollback. Do not relabel the
unverified cells as passed merely because the enclosing lifecycle test passes.
Fourteen isolated lifecycle variants cover original no-supply behavior, successful
direct handoff, and successful fallback for suspended account, expired vehicle
verification, expired known professional credential, missing/stale/future location,
outside-area position, offline/paused/offered status and wrong city/service.
A second fixture driver
shares the city's existing active requirement version (creating a second active
version would violate the real database constraint). No provider success is
inferred from these database and recipient-boundary tests.

Five additional isolated variants exercise scheduling lock waits; two more cover
mixed immediate/scheduled assignment, making twenty-one variants in this lifecycle
file. The scheduling-only helper is
`backend/tests/integration/scheduling_concurrency.py`. Both actors use independent
database sessions; the observer must see the losing PID blocked by the winner
through `pg_blocking_pids` before releasing the winner. The loser retains old ORM
objects deliberately, and final assertions use a fresh session after both commits.
Timeouts bound failures; task start order or a fixed sleep is not the race proof.

For a focused replay after the guarded test environment has created an empty
`taximobile_ci...` database and migrated it to head, run from `backend/`:

```text
python -m pytest tests/integration/test_published_fixed_routes.py -k race -q --tb=short
```

This requires `TAXIMOBILE_ENV=test`, `TAXIMOBILE_RUN_INTEGRATION=1`, the isolated
test database URL and the test role's clone capability. Never point it at a
development, staging or production data database: the fixture creates and drops
its own per-case clones. Record the complete backend run as well as the focused
result, migration head, source revision/dirty status and generated JUnit report.

#### Scheduling concurrency progression

| Case | First lock holder / competing command | Required durable result | Current evidence |
| --- | --- | --- | --- |
| RACE-01 | Handoff / handoff | One live ride and one passenger notification/outbox pair; both return the same ride | T3 two-session PostgreSQL passed |
| RACE-02 | Cancellation / handoff | Cancelled booking, no ride, no dispatch or unfulfilled hint; handoff conflict | T3 two-session PostgreSQL passed |
| RACE-03 | Handoff / cancellation | One live ride; booking cancellation conflict, no duplicate dispatch | T3 two-session PostgreSQL passed |
| RACE-04 | Driver offline / handoff | Reload offline state, no forced availability or assignment; unfulfilled in no-supply fixture | T3 two-session PostgreSQL passed |
| RACE-05 | Cancellation / offer acceptance | Cancelled offer/booking, no commitment or ride; acceptance conflict without deadlock | T3 two-session PostgreSQL passed |
| RACE-06 | Two drivers accepting one booking; one driver accepting overlapping bookings | At most one valid commitment for the booking/window; loser has actionable conflict | T3 observed-wait PostgreSQL passed, including adjacency, cancellation release and direct-write exclusion; independent HTTP-process/device evidence still required |
| RACE-07 | Location, credential/vehicle/account revocation or city configuration change / handoff | Explicit linearization policy, current eligibility and scope, no unauthorized assignment | Global account-status subset passed with six observed waits including alternate-supply/retry; location boundary crossing passed with two; city suspension/revocation passed against handoff and immediate acceptance/dispatch, plus two approval/reinstatement waits; remaining credential/configuration, statement-snapshot, independent-process and device matrix open |
| RACE-08 | Worker/process restart, lease expiry or HTTP retry during handoff | One durable result after recovery, no lost outbox work, bounded retry/deadlock handling | Independent-process/load evidence still required |

In T2, use scripted synthetic passengers/drivers and preserve command IDs and
expected states. In T3, run the database barriers above and assert ride,
commitment, driver, notification and outbox state, not just response codes. In T4,
repeat cancellation/offline from two physical devices, including delayed responses
and reconnect; active-vehicle changes while online/assigned must remain rejected.
T5 repeats the matrix through separate API/worker processes under the agreed load,
with restarts and latency injection. T6 staff rehearse resolving the losing
command without overriding authority. T7 trained closed-road participants confirm
that displayed state and pickup decisions match the winning transaction. T8
real-user pilots start only after earlier safety/operations gates pass, with stop
criteria for duplicate assignment, stale driver state or lost cancellation.
Do not deliberately inject unsafe races during public-road passenger rides.
T9/T10 retain regression evidence and repeat the relevant matrix for each release
and city rollout. Source-level tests alone do not close those phases.

#### Location update versus scheduled handoff pack

`test_scheduled_location_authority.py` runs real location-write and handoff
commands against separate sessions in migrated PostGIS clones. The shared
`scheduled_handoff_fixtures.py` prepares an accepted commitment, one available
driver and no replacement supply. Its initial observation is just inside the
synthetic service-area boundary; a newer observation crosses about 188 metres
over ten seconds, passing the production timestamp and movement guards.
Each case observes `pg_blocking_pids` before releasing the first transaction.

| Case | First driver-lock holder | Required durable result | Evidence |
| --- | --- | --- | --- |
| LOCATION-RACE-01 | Location write crosses outside the active area | Waiting handoff reads the new observation, releases commitment with `DRIVER_OUTSIDE_SERVICE_AREA`, records unfulfilled/no-supply, creates no ride, and emits exactly one passenger notice and outbox result | T3 PostGIS passed |
| LOCATION-RACE-02 | Handoff assigns using the fresh in-area observation | Waiting location command refreshes the driver to `EN_ROUTE` and records the newer observation; one accepted ride, fulfilled commitment and dispatch notice/outbox remain | T3 PostGIS passed |

The two-case focused run and combined 15-case account/location authority run
passed on 2026-09-05. Their reports are
`backend/build/scheduled-location-authority-tests.xml` and
`backend/build/assignment-authority-focused-tests.xml`. Run from `backend/`
with the complete guarded local test environment, integration mode and a migrated
empty `taximobile_ci...` template configured:

```text
python -m pytest tests/unit/test_account_authority.py tests/integration/test_account_assignment_authority.py tests/integration/test_scheduled_location_authority.py -q --tb=short --junitxml=build/assignment-authority-focused-tests.xml
```

T2 scripts cover crossing in both directions, duplicate and out-of-order
observations, invalid coordinates, excessive speed, missing fixes and freshness
expiry. Preserve expected booking states and synthetic observation times.
T3 proves both lock orders, reads final rows from a fresh session and checks
commitment reason, ride pointer, driver status and exactly-once persisted effects.
These two cases cover a valid inside-to-outside update; they do not close the
remaining T2 inputs or configuration changes during the same transaction.

T4 replays the transition on separate passenger/driver devices with delayed
uploads, lost responses, foreground/background changes and reconnect. Confirm
that the passenger sees the authoritative booking outcome and that an assigned
driver continues location updates. T5 repeats through separate API/worker
processes with process loss, database reconnect and bounded mixed-city load;
record lock waits, retry counts and p95/p99 latency. Include service-area version
activation while handoff waits as a separate configuration race.

T6 staff rehearse an unfulfilled boundary case and a driver leaving the area
after assignment, using the existing ride/support workflow. T7 uses supervised
non-public journeys and reviewed service-area geometry to compare device fixes,
reported accuracy and pickup readiness. T8 begins only after the applicable
P0 gates and these device/operations checks are accepted. Stop promotion on an
assignment using an observation superseded before its driver lock, missing or
duplicate booking effects, contradictory device state or an unbounded wait.
T9/T10 replay affected tests for each release and city boundary version; retain
build identity, configuration version, command IDs, timestamps and reviewer
decision with minimized location evidence.

#### City-authorization restriction and reinstatement pack

The command is `POST /operations/driver-applications/{application_id}/authorization/decisions`.
It is implemented with scoped driver-review permission, recent MFA, a closed
action/reason set, an expected application version and required idempotency key.
The console adds a current status/expiry panel and typed authorization-ID review.
Backend state remains authoritative. The 33-case focused pack passed locally on
2026-09-05; its evidence covers the following claims.

| Case | Required result | Current evidence |
| --- | --- | --- |
| AUTHZ-01 | Only explicit state transitions; wrong reasons, invalid versions, expiry/scope injection and unknown actions rejected | 17 T1 cases |
| AUTHZ-02 | Suspend/reinstate/revoke preserves original approval, expiry, future commitment history and other driver authority; revoked authority cannot be reinstated | T3 PostGIS lifecycle |
| AUTHZ-03 | Expired authorization, suspended global user, unverified vehicle or stale application version prevents reinstatement without partial audit/state | Four T3 PostGIS cases |
| AUTHZ-04 | Suspension or revocation holds driver lock before handoff; waiting handoff creates no assigned ride | Two T3 observed-wait cases |
| AUTHZ-05 | Handoff holds driver lock before suspension or revocation; exactly one committed ride remains history | Two T3 observed-wait cases |
| AUTHZ-06 | Real password/TOTP operations session can decide; unauthenticated request and stale MFA cannot | T3 ASGI/PostGIS with real MFA |
| AUTHZ-07 | Same key/payload replays the same result; changed payload or stale version conflicts; scope removed after original command blocks cached replay | T3 ASGI/PostGIS |
| AUTHZ-08 | Failure after audit flush rolls authorization, application version and idempotency back; retry can succeed | T3 injected-fault ASGI/PostGIS |
| AUTHZ-09 | New application approval versus reinstatement, either winning first, yields one active city authorization | Two T3 observed-wait cases |
| AUTHZ-10 | Restrict one city for a driver authorized in two; real eligibility query still accepts the other city's authorization | T3 synthetic two-city PostGIS fixture |
| AUTHZ-11 | Console offers reinstatement only for suspended status and sends reviewed application version without expiry/scope fields | JS/Wasm model tests and compilation |
| AUTHZ-12 | Both applicant clients distinguish recorded active/suspended/revoked/expired/unknown status, show supplied expiry, and do not equate a record with permission | Two shared label tests, shared JVM suite, both Android role compiles and JS/Wasm browser suites; rendered device/accessibility and refresh acceptance still required |
| AUTHZ-13 | Suspension/revocation versus immediate acceptance in both orders: restriction-first rejects the old offer without assignment effects; acceptance-first preserves exactly one committed ride and notification/outbox pair | Four T3 observed-wait PostGIS cases |
| AUTHZ-14 | Discovery sees an uncommitted restriction: skip the locked driver without blocking or declaring no supply; worker retry after commit excludes the driver | Two bounded T3 two-session cases |
| AUTHZ-15 | Restriction committed before discovery excludes the driver and produces no offer | Two T3 PostGIS cases |
| AUTHZ-16 | Dispatch holds the driver first: restriction waits for the offer commit, but the old offer cannot be accepted after restriction | Two T3 observed-wait PostGIS cases |
| AUTHZ-17 | Global suspension wins after discovery: post-lock rejection neither crashes nor offers to that driver; choose alternate eligible supply or defer safely for worker retry | Two T3 observed-wait PostGIS cases |

The immediate-authority follow-up adds 12 tests in
`backend/tests/integration/test_city_authorization_immediate.py`; all pass with
the existing dispatch-contention, account-assignment and city-lifecycle tests
(30 cases in `backend/build/immediate-authority-focused-tests.xml`). Its global
authority case first reproduced an assertion in dispatch: a rejected provisional
candidate remained non-null while its score was unselected. Dispatch now only
finalizes a candidate after all guards pass, and repeats the eligibility query
in a fresh statement snapshot after the driver/global-account locks. The current
992-test run includes this matching-service change; the earlier
783-test report does not.

Run with the complete guarded local test configuration and migrated disposable
PostGIS template, from `backend/`:

```text
python -m pytest tests/unit/test_city_authorization_policy.py tests/integration/test_city_authorization_lifecycle.py tests/integration/test_city_authorization_http.py tests/integration/test_city_authorization_approval_races.py -q --tb=short --junitxml=build/city-authorization-complete-focused-tests.xml
```

T2 synthetic staff/driver journeys must exercise each action, existing immediate
offers and future commitments, rejected reinstatement, reapplication after
revocation and subsequent approval. T3 service tests now cover immediate
acceptance and candidate selection versus restriction in the table above. The
remaining matrix includes independent HTTP/process races, additional
credential/vehicle/configuration changes, duplicate and lost-response requests,
document evidence expiry, and the interval between statement snapshots and
lock acquisition. These deterministic cases do not prove the full matrix.

T4 uses separate reviewer browsers and driver phones. Check role-hidden controls,
typed confirmation, expiry display, stale tabs, keyboard/screen-reader behavior,
EN/FR/AR comprehension, offline refresh and current authorization display after
reconnect. Browser model tests do not prove those interactions. The source now
creates a durable generic inbox notice and minimized refresh hint for every
authorization change. Physical delivery, driver comprehension, explicit
acknowledgment/appeal semantics and staff escalation remain required before pilot.

T5 repeats restrictions, reinstatement and concurrent approval across independent
API/worker processes under mixed-city load, with rollback, process death and
database reconnect. Include suspension after candidate discovery both with and
without alternative supply; verify worker recovery, not just the API response.
Measure the additional post-lock eligibility query with representative candidate
limits and history: query count, PostGIS plan, lock duration, pool occupancy and
p95/p99 offer latency. Passing small fixtures does not establish its capacity
cost. Capture command IDs, lock wait/deadlock/retry measurements
and final authoritative state. T6 staff rehearse a restriction before assignment
and after assignment, using the ride/support procedure for the latter. Review
reasons, appeals and restoration decisions must have a named operational owner.
T7 uses supervised non-public journeys; do not strand a driver and passenger by
injecting restrictions during public-road rides. T8 requires accepted T4–T7
evidence and all applicable P0 closures. Stop on cross-city loss of permission,
assignment after a winning restriction, duplicate active authorization, failed
revocation communication, unauthorized reinstatement or rewritten ride history.
T9/T10 repeat the affected pack on each release/city and retain minimized,
immutable build/configuration/test evidence and a named acceptance decision.

##### City-authorization notification acceptance (source implemented; acceptance open)

Assignment denial and applicant status labels do not close communication of a
restriction. The source uses the existing transactional inbox and outbox; it
does not call a provider inside the reviewer transaction. The durable
notice is history; a push is only a minimized prompt to reload current authority.
An inbox `read_at` value records the existing read action, not legal consent,
understanding, human contact or acceptance of a decision. Any explicit
acknowledgment/appeal workflow must have its own reviewed semantics and evidence.

| Case | Required evidence before promotion |
| --- | --- |
| AUTHZ-N01 | Successful suspend/revoke/reinstate writes exactly one driver-owned notice and one classified outbox event with the authorization/audit transaction; idempotent replay adds neither | T3 lifecycle and real-MFA HTTP/PostGIS passed |
| AUTHZ-N02 | Failure after notification/outbox flush rolls back authorization, application version, audit, notice, outbox and command receipt; retry succeeds once | T3 injected post-outbox fault passed |
| AUTHZ-N03 | Delivery reloads the owning driver from source records, ignores supplied recipient fields, refuses a missing source and sends only an allowlisted authorization-ID refresh | T1 policy/delivery tests passed; malformed/inconsistent migrated-source cases remain |
| AUTHZ-N04 | Source age, duplicate/reordered delivery, later reinstatement/revocation, missing provider and provider failure preserve authoritative inbox history and do not display obsolete permission as current | Generic status-neutral notice/policy age implemented; real PostGIS provider-failure retry preserves one inbox row; remaining matrix open |
| AUTHZ-N05 | EN/FR/AR inbox copy, authorized read action, current-status refresh, signed-out/account-switch behavior, offline/reconnect and screen-reader/RTL paths on both driver platforms | 610-key localization parity, shared presentation/relay tests and Android compiles passed; T4 device acceptance open |
| AUTHZ-N06 | Separate API/outbox workers, process death after commit and provider outage recover without lost durable notices; retries/dead letters are visible to the named compliance owner | T3 processor recreation/provider retry and a real child-process claim/forced termination/replacement-process recovery pass. Fixed-owner gauges, privacy-bounded PromQL and validator mutation tests pass; a real PostGIS failed/recovered notice appears only under `driver_compliance`. Independently deployed API/worker, collector/Alertmanager, real provider and staff receipt remain T5/T6. |
| AUTHZ-N07 | T6/T7: staff distinguish sent, provider-accepted, device-visible, read and explicitly acknowledged; rehearse an unreachable driver and a restriction after an already committed ride without stranding participants. |
| AUTHZ-N08 | T8–T10: owner-approved delivery/response thresholds, staffed escalation, privacy/retention and appeal procedures are accepted before pilot and repeated on city expansion. |

Rows explicitly marked open remain required. Source completion and local passing
rows do not establish FCM/APNs delivery or human acknowledgment. The latest web
verification also passes 47 tests in each JS and Wasm browser target.
The processor-recovery case is in
`backend/tests/integration/test_city_authorization_notification_delivery.py`;
its 27-case notification/worker focused report is
`backend/build/city-authorization-worker-recovery-focused-tests.xml`.
A second focused report,
`backend/build/city-authorization-process-recovery-focused-tests.xml`, proves the
two recovery cases directly, including forced termination after the durable claim.

#### Scheduled commitment acceptance pack

This pack narrows `RACE-06` without treating a scheduling conflict as a server
failure or a server fault as a driver's mistake. The small fixture uses
synthetic city policy and approved driver evidence, then real preference,
quote, booking and offer services. It does not certify recruitment or tariff
approval. Five race cases require an observed `pg_blocking_pids` dependency
before the first transaction is released; a sleep or task launch order is not
accepted as proof. Fresh sessions inspect durable results after both actors.

| Case | Required test and outcome | Local source evidence |
| --- | --- | --- |
| ACCEPT-01 | Two drivers accept one booking; stale loser sees committed booking/cancelled offer; one pointer, commitment, lifecycle event, passenger notice and outbox result | T3 PostgreSQL |
| ACCEPT-02 | One driver accepts two bookings whose transport periods touch but buffers overlap; one succeeds, losing booking stays offering with pending offers and no phantom side effects | T3 PostgreSQL |
| ACCEPT-03 | Exactly adjacent `[start,end)` protected windows allow both commitments; each retains its own passenger recipient and snapshots | T3 PostgreSQL |
| ACCEPT-04 | Cancellation updates an existing commitment while a new overlapping acceptance waits; capacity is released only after commit; old cancelled history remains | T3 PostgreSQL |
| ACCEPT-05 | A concurrent writer bypasses booking/driver service locks and attempts an overlapping insert; the named exclusion constraint rejects it without second commitment or booking pointer | T3 PostgreSQL |
| ACCEPT-06 | Actual overlap through authenticated acceptance API returns `409`; all losing changes roll back | T3 ASGI/PostGIS |
| ACCEPT-07 | Inject a real foreign-key failure on a new commitment; return sanitized `500`, preserve internal-error telemetry, do not falsely say overlap; retain no partial booking/offer/event/delivery changes | T3 ASGI/PostGIS |
| ACCEPT-08 | Fail after commitment, booking, offer, event, notification and outbox SQL flush; the transaction rolls everything back, preserving the first unrelated successful booking | T3 ASGI/PostGIS |
| ACCEPT-09 | Adjacent acceptance API returns `200`; repeat returns `409` without a duplicate commitment, event or notification | T3 ASGI/PostGIS |
| ACCEPT-10 | Recognize exact exclusion name and SQLSTATE; refuse missing/wrong metadata and exception-text inference | T1 nine unit cases |

The 18-case focused run passed on 2026-09-04. Re-run from `backend/` only after
the guarded isolated PostGIS environment is configured:

```text
python -m pytest tests/unit/test_scheduled_conflicts.py tests/integration/test_scheduled_acceptance_concurrency.py tests/integration/test_scheduled_acceptance_http.py -q --tb=short --junitxml=build/scheduled-acceptance-focused-tests.xml
```

The HTTP cases use ASGI transport and real database/authentication transactions,
not a separate socket or reverse proxy. T4 repeats the winning/losing acceptance
and authoritative reload on two physical driver devices, including response
loss, expiry and screen-reader copy. T5 repeats through independent API and
worker processes, proxy failure and process termination under reviewed load;
record lock waits, timeouts, retry behavior and durable state. This pack does not
prove predicted completion-time admission before a future protected window, all
administrative revocation races or database failover.

T6 staff must distinguish an ordinary `409` from an internal `500`, use the
request ID and authoritative booking/commitment list, and never insert a
replacement commitment manually. T7 supervised participants verify future
pickup times and buffers without manufacturing conflicting public-road rides.
T8–T10 retain the regression pack and stop promotion on duplicate commitments,
wrong-passenger notifications, lost cancellation history or unexplained
conflict/error handling. Every promoted record still needs immutable build,
policy/window versions, environment, timestamp, owner and signed acceptance.

#### Scheduled/live protected-window pack

This cross-domain pack checks the rule that a commitment is not live driver
availability, while its active protected range still prevents conflicting
immediate work. It uses server time and the database half-open range; clients do
not submit eligibility or resolve races. The 28-case focused run includes the 18
acceptance cases above, seven new PostGIS service/concurrency cases and three new
authenticated ASGI/PostGIS cases.

| Case | Required test and outcome | Local source evidence |
| --- | --- | --- |
| PROTECT-01 | At range lower bound and one microsecond before upper, active commitment blocks; exact upper and cancelled status do not | T3 PostGIS |
| PROTECT-02 | Current commitment removes the only eligible driver from candidate discovery and produces no offer; cancellation restores ordinary dispatch | T3 PostGIS |
| PROTECT-03 | Immediate offer created before the window is refused at acceptance; after authoritative commitment cancellation, that still-pending offer can be accepted | T3 PostGIS |
| PROTECT-04 | Live acceptance owns the driver first; scheduled acceptance waits, refreshes, detects the active live ride and leaves booking/offers uncommitted | T3 observed-wait PostgreSQL |
| PROTECT-05 | Scheduled acceptance owns the driver first; live acceptance waits, refreshes, detects the current commitment and leaves ride/offer unassigned | T3 observed-wait PostgreSQL |
| PROTECT-06 | While scheduling owns the driver lock, matching returns promptly via `SKIP LOCKED`, creates no offer and leaves the ride matching; after commit, retry sees true ineligibility | T3 concurrent PostgreSQL |
| PROTECT-07 | Authenticated immediate acceptance after the scheduled winner returns generic race-safe `409`, leaks no credential and leaves one scheduled commitment | T3 ASGI/PostGIS |
| PROTECT-08 | Authenticated scheduled acceptance after the live winner returns `409`, leaks no credential and leaves no scheduled commitment | T3 ASGI/PostGIS |
| PROTECT-09 | Active commitment hours outside the current protected range does not block an authenticated immediate acceptance | T3 ASGI/PostGIS |
| PROTECT-10 | Candidate discovery may still offer ordinary work when an active commitment's protected range starts hours later | T3 PostGIS |

Run the full focused pack only against a guarded disposable PostGIS database:

```text
python -m pytest tests/unit/test_scheduled_conflicts.py tests/integration/test_scheduled_acceptance_concurrency.py tests/integration/test_scheduled_acceptance_http.py tests/integration/test_scheduled_live_protection.py tests/integration/test_scheduled_live_protection_http.py -q --tb=short --junitxml=build/scheduled-live-protection-focused-tests.xml
```

T4 repeats stale-offer/current-window conflicts on separate physical driver and
passenger devices and verifies authoritative reload, localization, accessibility
and response-loss behavior. T5 uses independent API/worker processes, multiple
replicas, clock-boundary injection and transaction/process termination. It must
also adopt an owner-approved conservative immediate-trip duration or route-time
policy and prove that rides accepted before a future window do not intrude into
the protected pickup period; the current implementation intentionally does not
invent that duration.

T6 staff rehearse both conflict directions and distinguish temporary lock retry,
ordinary offer loss and a committed scheduling reservation. T7 uses supervised,
non-public road scenarios to calibrate the duration guard and buffer without
creating knowingly conflicting passenger trips. T8–T10 stop promotion on double
assignment, a missed current window, repeated pre-window intrusion, incorrect
participant state or staff override of backend authority. Evidence must retain
server/DB timestamps, policy and graph versions, both command IDs, immutable
build identity, owner, result and residual risk without raw location trails.

#### Scheduled readiness regression and field replay pack

Run these cases first with synthetic participants on PostGIS, then replay them
on physical driver/passenger devices in T4 and trained-staff journeys in T6.

| Case | Input at handoff | Required result |
| --- | --- | --- |
| READY-01 | Available, correct scope, fresh in-area observation | Exactly one assigned ride, fulfilled commitment, passenger hint, and safe repeat handoff |
| READY-02 | No observation | No direct assignment; replacement offer or explicit unfulfilled |
| READY-03 | Age just inside/at/outside configured freshness | Inside/at allowed if other checks pass; outside denied |
| READY-04 | Observation 60 seconds ahead versus beyond 60 seconds | Existing skew allowance preserved at boundary; excessive future timestamp denied |
| READY-05 | Fresh position outside active service-area geometry | No direct assignment even with a valid city authorization |
| READY-06 | Offline, paused or already offered another ride | No forced online/available transition; normal fallback/unfulfilled |
| READY-07 | Different/missing live city or service | No scope reassignment to make the old commitment appear valid |
| READY-08 | Handoff fails, original driver otherwise matches candidate SQL | Initial fallback must exclude that driver; another eligible driver gets only an offer |
| READY-09 | Failure after successful fallback outbox SQL flush | Booking, ride, offer, driver availability, notification and outbox changes roll back together |
| READY-10 | Configuration unavailable | Explicit error without silently choosing a default freshness policy or assigning a ride |

Pure boundaries use `test_scheduled_readiness.py`; migrated service scenarios use
`test_published_fixed_routes.py`. Missing scope, non-available statuses beyond the
three device-facing cases, and exact time bounds have unit coverage. Do not
assume every pure case has a corresponding database/device trace. Add T5 races
for location, city-configuration activation, availability, live offers and
concurrent handoff. T6 staff must explain an unfulfilled schedule without claiming
that the old commitment guaranteed a taxi. T7 measures false readiness,
replacement delay and pickup completion before T8 real-user enrollment.

### 18.3 T4–T5 — physical devices and production-like providers

Use separate staging FCM/APNs projects and both signed release-like role apps.
Cross Android/iOS version, foreground/background/terminated state, notification
permission, battery saver, low-data mode, device reboot, registration rotation,
network handoff and prolonged offline periods. For every event record source
commit, outbox claim, provider submission, callback, REST refresh and visible-state
timestamps without content or personal identifiers in telemetry.

Inject multi-replica loss, provider outage, rate throttling, invalid credentials,
database reconnect, dead-letter replay and delayed queues. Verify source expiry
and device queue TTL, Android priority behavior, APNs background limitations,
inbox/poll fallback, bounded battery use and no false success. Before preference
UI ships, test eligible quiet-hour deferral across timezones and daylight-saving
changes; active dispatch events must not inherit informational suppression.
Scrape both API and private worker targets, force one dead letter in each fixed
owner class, and verify a separate alert instance retains only its reviewed
owner label. `unclassified` must page the platform duty owner as an unsupported
topic defect. Confirm absent scrapes trigger availability/missing-metric alerts,
resolved queues clear alerts, and no topic, resource, authorization, payload,
device or user value appears in metrics, annotations or router grouping keys.
The committed overlay and offline tests establish the topology and routing
contract only. T5 must run it against independently deployed API/worker services,
measure scrape gaps and storage growth, restart both monitoring processes, verify
retention, and capture receiver-visible firing/resolution timestamps without
alert content containing personal data.

### 18.4 T6–T10 — staff, field, pilot, and expansion

T6 staff rehearse a missed immediate offer, delayed scheduled handoff, cancellation
during pickup, lost credential notice, invalid registration and provider outage.
Each dead-letter class has a named owner, acknowledgement target, safe replay or
discard decision, Alertmanager receiver, backup escalation and measured receipt/
acknowledgement timing. Staff never treat push as emergency paging.

T7 closed-cohort journeys measure event-specific callback/visibility latency,
miss rate, duplicate/confusing notice rate, fallback use, pickup delay and driver
distraction by device/language/network. T8 freezes thresholds, sample sizes and
observation windows before real-user enrollment; S0/S1 incidents, sustained
missed-critical-event thresholds or unusable fallback pause the cohort. T9 stages
public city volume and confirms support capacity. T10 repeats provider/device,
timezone/language and operator staffing acceptance per new city.

The closure bundle includes policy/configuration digests, producer/allowlist
reports, transaction/fanout tests, provider/device matrix, per-event timestamp
distributions, quiet-hour/preference tests, redaction review, dead-letter drill,
field findings and signed SLO/go-no-go decisions. Source tests do not close the
provider or operational portions of this gap.

## 19. Critical journey coverage matrix

| Journey | T1 | T2 | T3 | T4 | T5 | T6 | T7 | T8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Accounts/sessions/suspension/recovery | Hash/state/rate rules | Missing/staff/replay personas | API/DB concurrency and revocation | Secret lifecycle on devices/browser | Timing/abuse/redaction | Staff plus user recovery | Cohort login/revoke | Real support without override |
| Driver application/documents | Unit/adapters | Applicant/reviewer | PostGIS/storage stub | Picker/browser/device | Real-class storage/scanner | Reviewer drill | Invited drivers | Production cohort |
| Immediate ride/matching | State rules | Passenger/driver | Multi-role/worker | Devices | Load/failure | Staff dispatch | Field roads | Real rides |
| Assigned-ride coordination | Code/role/state/rate rules | Participant/adversary matrix | PostGIS/outbox/concurrency | Device/push/a11y/language | Multi-instance/provider/retention | Pickup/support rehearsal | Closed-road pickup metrics | Bounded thresholds |
| Notification delivery | Topic/age/priority policy | Producer/allowlist/recipient contracts | PostGIS fanout/leases | OS lifecycle/permission/TTL | FCM/APNs outage/load | Dead-letter ownership drill | Event visibility metrics | Event-specific SLOs |
| Map/geocode/navigation/location | Normalization | Fake provider | Local adapter | Device lab | Real provider/chaos | Operations outage | Field benchmark | Real metrics |
| Cash/manual transfer/refund | Conservation | Finance personas | Transaction lifecycle | UX/device/browser | Controlled recipient | Finance drill | No money or approved micro-test | Reconciled real money |
| Fixed routes | Rules | Directions/personas | PostGIS geometry | Map/device/browser | Provider/load | Publication drill | Field route | Bounded users |
| Scheduling | Time/overlap/readiness | Booking and cancellation personas | Handoff/rollback plus observed lock races | Device notifications/offline/cancel | Independent processes, revocation and clock/failure/load | Exception and losing-command drill | Controlled pickup/state agreement | Bounded users with assignment/cancellation stop criteria |
| Support/safety | State/authorization | Participant/staff | Pager stub/retention | Mobile/web UX | Real pager/alerts | Incident drill | Field contact | Real staffed cases |
| Operations control plane and staff access | Scope/state/self/expiry rules | Staff and adversary personas | Multi-city/concurrent grant DB | Browser/MFA/a11y | Hosted security and approval | Two-person city-in-a-day | Field monitoring/access review | Real readiness/recertification |
| Analytics/readiness | Definitions | Aggregate fixtures | Refresh/suppression | Web table/a11y | Data quality/load | Decision drill | Field baseline | Pilot decision |

## 20. Defect severity and promotion rules

| Severity | Examples | Promotion rule |
| --- | --- | --- |
| **S0 stop** | safety harm, authorization/data exposure, wrong assignment, money loss/misdirection, unrecoverable corruption | Stop test/rollout, preserve evidence, activate incident procedure; no promotion until fixed and independently retested. |
| **S1 critical** | core journey unavailable, repeated crash, missing urgent page, broken rollback, inaccessible critical action | No phase promotion; fix and run affected regression plus failure path. |
| **S2 major** | material delay/confusion, localized/RTL failure, reconciliation/manual workaround, poor degraded mode | Requires owner disposition; generally blocks T7/T8 when user-facing. |
| **S3 minor** | cosmetic or low-frequency issue with safe workaround | May be scheduled with owner/date and measured cohort impact. |

Severity is based on impact, exposure and recoverability, not implementation
difficulty. Repeated S2 defects may become S1 when they undermine operations.

## 21. Test data and participant safety

* Synthetic emails/phones use reserved or clearly fictional ranges and cannot
  reach uninvolved people.
* Synthetic identity documents contain a visible `TEST — NOT A REAL DOCUMENT`
  watermark and no real number, face, signature or address.
* Test payment recipients are environment-labeled; production recipient details
  never enter screenshots, fixtures or source control.
* Route/location fixtures use approved public coordinates and never reconstruct
  a real person's history.
* Safety narratives avoid real victim details. Real pilot cases follow restricted
  access and retention policy.
* Automated load never targets public or production systems without explicit
  authorization, rate bounds and stop controls.
* Real participants receive purpose, data use, support, withdrawal, compensation
  and emergency limitation information in a language they understand.

## 22. Test ownership

| Evidence | Accountable reviewer |
| --- | --- |
| Source, unit, contract and integration | Engineering |
| Threat model, scans, penetration and incident retest | Security owner/independent reviewer |
| Privacy, retention, participant consent and real-data use | Privacy/legal owner |
| Tariff, payment, cash, refund and payout reconciliation | Finance/operator owner |
| Driver eligibility, field procedure and supply | City/operator representative |
| Accessibility, localization and usability | Product owner plus representative users |
| Support/safety roster, page and escalation drill | Operations/safety owner |
| Provider graph/style/push/scanner availability | Engineering and operations jointly |
| Pilot metrics, fairness and expansion | Product, operator and cooperative decision body |

Engineering cannot approve its own legal authority, penetration test, real money
reconciliation, accessibility experience, or city launch readiness.

## 23. Immediate execution order

1. Complete `PLACE-T0-01` through `PLACE-T3-08` and freeze the first reviewed
   multilingual place corpus without real home/work data.
2. Run the account-recovery T2–T4 matrix, including secure-save acknowledgement,
   process death, accessibility, screenshot/clipboard and physical-device checks.
3. Run the implemented T0 web, documentation and release-evidence CI gates on
   a clean immutable candidate; local results do not satisfy remote provenance.
4. Make T3 current-head backup/restore and multi-role suites reproducible from a
   clean checkout.
5. Accept or reject the implemented foreground-only driver-location model using
   Android/iOS lifecycle traces, battery, weak-network and dispatch-freshness
   evidence; do not add background capability merely to bypass a failed test.
6. Execute coordination T2/T3 adversarial and concurrency packs, then its T4
   device/accessibility/network matrix before any closed-road use.
7. Complete notification T2/T3 transaction/state/retry coverage for every event,
   then the T4 OS/provider matrix. Policy and fanout unit/integration successes
   do not prove the five scheduled producers' complete transactional lifecycle.
8. Provision production-like staging and select real map/routing/geocoding/push/
   document/pager boundaries.
9. Define the device/browser matrix, SLO/RPO/RTO, coordination/pickup thresholds,
   stop criteria and evidence
   owners before T4/T5 execution.
10. Run T6 staff rehearsal, including coordination/provider-outage scenarios,
   before recruiting a real cohort.
11. Complete non-public T7 road validation before any real passenger pilot.
12. Enter T8 only when every applicable P0 gap has an accepted closure record.
