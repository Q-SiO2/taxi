# TaxiMobile — Test Execution and Promotion Map

## 1. How to use this map

This is the operational control board for taking TaxiMobile from repository
verification to a deployable city service. The detailed scenario contracts remain
in [`testing.md`](testing.md), workload mechanics in
[`testing_workloads.md`](testing_workloads.md), security packs in
[`threat_model.md`](threat_model.md), and unresolved acceptance criteria in
[`gaps.md`](gaps.md). This map defines sequence, ownership, entry and exit gates,
minimum evidence, and when simulated or real participants may be introduced.

No row is a calendar promise. A phase advances only when its exit gate is signed
for one immutable candidate. Passing a later phase never excuses an earlier one.
Any material code, provider, city configuration, tariff, service-area, routing
graph, map style, mobile artifact, infrastructure topology, or security-policy
change invalidates the affected evidence and sends that scope back to the earliest
impacted phase.

**Current position (standing refreshed 2026-10-02):** most subsystems have broad T1–T3 evidence,
including a fresh migration-through-`20260908_0052` PostGIS run with 1,090 passing
backend tests and no failures, errors or skips. The staff-grant dual-control slice
also has focused PostGIS, API, JS and Wasm evidence. Migration 0050 and its
security-incident workflow, one-time postmortem completion and deadline telemetry
now include four closed responsibilities, exact-market responder eligibility,
one active assignee per responsibility and append-visible reassignment history.
The incident slice has dedicated 16-unit/static and two-PostGIS evidence included
in that complete regression, plus 57 passing tests per JS/Wasm browser target and
112 validated web HTTP operations after the protected incident workspace was
extended. The candidate capacity surface
has 22 fixed Prometheus queries, 21 profile thresholds, explicit per-process
database-pool bounds, 26 validated alert rules and a 26-panel operations
dashboard. Immutable server commit `2d6a68b` passes the complete push and pull-request CI
workflows, including both iOS Release simulator application links. Historical
system/load results remain local unless the remote run explicitly produced them.
Some browser/emulator evidence has started at T4; the GAP-002 through GAP-006
external acceptance records remain `NOT_STARTED`, and no subsystem has complete T4–T8 acceptance.
No real-user phase is authorized.

The latest test-toolchain follow-up passed the complete guarded T3 run with
pytest 9.0.3/pytest-asyncio 1.4.0, explicit function-scoped loops, zero residual
clones, revoked temporary database authority and an 81-table logical restore.
Its local `backend/build/pytest9-t3-20261001/` records cover all six T3 evidence
kinds; they do not accept T3 or establish clean immutable CI execution. The
20-persona/60-selected-test T2 pack also passed with its network guard. Separate
runtime/development audits are locally clean; Linux supplement execution remains
the Linux CI boundary. Formal sign-offs, ordered evidence and external acceptance
remain open.

The live-listener follow-up passed 78 focused unit/API cases, 197 infrastructure
tests and the 20-persona/60-test T2 pack. Its complete guarded T3 regression
passed 1,042 backend tests with zero failures/errors/skips and three existing
deprecation warnings, including actual owned-listener PID termination,
replacement channel registration and addressed-only delivery. Records in
`backend/build/live-event-recovery-t3-20261001/` prove migration 0052, zero residual
clones, revoked temporary database authority and an 81-table/8,511-row logical
restore with cleanup. The system report requires `LIVE_HINT_RECOVERY` and covers
all six T3 evidence kinds without phase/deployment acceptance. This is local
workspace evidence, not hosted failover, real delivery, physical UX or immutable
CI evidence by itself. Immutable `f0824c9` now passes both push and PR workflows,
including backend, mobile, web, documentation/security, Linux dependency audits
and both iOS Release simulator links. The subsequent mobile recovery source
slice requires its own immutable CI runs and physical/hosted acceptance.

The mobile HINT-06 source follow-up locally passes 31 new focused cases inside
235 JVM and 186 Android host tests, both Android debug-root compiles, 57 tests
per JS/Wasm browser target, 41 mobile script tests (21 wiring mutations) and
197 infrastructure tests. The native owner now recovers without changing the
ready category, cancels obsolete/session-ending work and serializes refresh
credentials. These are T0/T1 scope records, not iOS test execution, complete T4,
FCM/APNs delivery or hosted failover. Immutable `8f92e51` now passes both push
and PR workflows, including macOS shared-source/test compilation and both iOS
Release simulator application links. Native iOS test linking/execution and real
devices remain separate limitations. The subsequent server-authority HINT-08
slice has its own local regression below and passing immutable CI recorded in
GAP-001; no real-user phase is authorized and deployment acceptance
remains 0/19 P0 gates.

The server HINT-08 follow-up passes 106 focused backend cases, 199 infrastructure
tests and 20 simulated scenarios/66 exact tests under outbound-network denial.
Its complete fresh-PostGIS regression passes 1,090 backend tests with no
failures/errors/skips and three existing dependency deprecation warnings.
`backend/build/live-session-authority-t3-20261002/` retains JUnit, database,
restore and combined system records. The combined report requires both
`LIVE_SESSION_AUTHORITY` cases independently of listener recovery and verifies
migration 0052, zero residual clones, revoked temporary clone authority and an
81-table/8,511-row restore with cleanup. All six bounded T3 evidence kinds are
present; formal phase acceptance remains false. The ordered HINT-08 pack below
then requires physical multi-device/session testing, independent authority and
listener failure injection, multi-replica fanout, SQL-pool headroom and approved
revocation/delivery budgets before staffed/field/real-user promotion.

## 2. Promotion path

The Android protected-storage follow-up passes 22 adapter cases within 208
Android host tests, 235 freshly rerun JVM tests, both Android debug-role compiles,
204 infrastructure tests and 41 mobile-script tests. Synthetic cipher/preferences
tests prove control flow, not real Keystore or disk persistence. Its own immutable
CI remains required. Revised T4 catalog `2026-10-02` keeps 56 cases but binds
stronger native-storage requirements to a new LF-portable exact-byte hash;
old evidence cannot accept them. All template cases remain `NOT_STARTED`.
The native-storage T1/T4 packs below retain T5 hosted authority, T6 staff recovery,
T7 field and T8 full P0 approval before any real-user promotion.

| Phase | Test population | Environment | Primary question | Exit authority |
| --- | --- | --- | --- | --- |
| T0 | None | Source tree | Is the candidate structurally valid and reviewable? | Engineering |
| T1 | Generated inputs | Unit/component harnesses | Do isolated rules fail safely? | Engineering |
| T2 | Simulated passenger, driver, applicant, staff and attacker personas | In-process/fake-provider contracts | Are complete journeys and hostile inputs specified consistently? | Engineering + security for security packs |
| T3 | Synthetic multi-role accounts | Local fresh migrated PostGIS and real child processes | Do API, database and workers preserve authoritative state under concurrency? | Engineering |
| T4 | Testers on supported devices and browsers | Device/browser laboratory | Can people complete journeys across OS, language, accessibility and network states? | Product + accessibility/device owner |
| T5 | Synthetic accounts only | Hosted production-like staging | Does the deployable topology meet load, security, recovery and provider-failure budgets? | Engineering + security + operations |
| T6 | Trained staff using fictional records and journeys | Hosted staging | Can the operating organization run and recover the service without developers editing data? | Operations + city/operator owners |
| T7 | Consenting staff and invited licensed drivers; no public service | Approved non-public roads/areas | Do devices, GPS, maps, routing and pickup procedures work physically and safely? | Product + operator + safety/legal |
| T8 | Small invited real passenger and driver cohorts | One bounded production city window | Does the service meet frozen safety, reliability, money and support thresholds with real users? | Go/no-go board |
| T9 | Guarded public users | One accepted city | Can exposure expand without violating stop thresholds? | Go/no-go board + city operator |
| T10 | Real users in additional cities | Repeatable national platform | Is isolation, configuration, staffing and capacity repeatable rather than city-specific? | National + each city operator |

## 3. Evidence packet required at every phase

Create one immutable evidence directory per candidate and phase. Its index must
contain:

1. candidate commit and clean-tree statement, image/web/mobile artifact digests,
   dependency lock identities, migration head and build provenance;
2. environment/topology ID, city configuration bundle and versions of tariff,
   payment capability, fixed routes, schedules, service area, map/style, routing
   graph and providers used by the tests;
3. scenario IDs, expected results, data classification, start/end timestamps,
   executor and accountable reviewer;
4. machine-readable test reports, sanitized logs, aggregate metrics, database
   reconciliation and screenshots or recordings where human behavior matters;
5. every defect, severity, affected population, mitigation, retest result and
   explicit pass/fail/blocked decision;
6. stop/rollback actions exercised, actual recovery time, unresolved risk and
   evidence-retention/erasure date; and
7. signatures or controlled ticket references from every authority required by
   the phase. A typed `APPROVED` field or CLI confirmation is not a signature.

Never place tokens, recovery codes, identity documents, precise participant
location histories, unrestricted case text, payment instructions, or provider
credentials in the packet. Preserve controlled references instead.

### 3.1 Executable phase evidence

The ordered catalog at
[`../infra/testing/test-phase-catalog.json`](../infra/testing/test-phase-catalog.json)
turns the T0–T10 boundaries into a machine-readable promotion contract. Start a
candidate packet by copying
[`../infra/testing/test-evidence-index.template.json`](../infra/testing/test-evidence-index.template.json)
to the controlled evidence store; do not overwrite the repository template.
Validate metadata with:

```powershell
backend/.venv/Scripts/python.exe infra/scripts/validate_test_phase_evidence.py `
  --evidence path/to/candidate-test-evidence.json
```

Use `--require-through T3`, for example, only when the release action truly
requires every phase through T3 to be accepted. The validator enforces ordered
promotion, exact evidence kinds and authority functions, clean-candidate
identity, digest-addressed references, defect disposition and the complete
GAP-001–GAP-019 closure register before T8. It also rejects public users before
T9, live money before T8, intentional failure injection in field/user phases,
real-user evidence before T8, and sensitive credential/document/location fields
in the index.

This is a metadata integrity gate, not a signature verifier and not evidence
that an external artifact, person, city, device or provider is genuine. The
default template truthfully reports every phase `NOT_STARTED`; CI validates that
catalog/template pair but cannot promote it. An accepted packet must live in an
access-controlled immutable evidence system whose references and digests are
verified by the named approvers.

### 3.2 Security-incident promotion track

The incident workflow must advance with the product rather than being tested for
the first time during a real breach:

| Phase | Required incident exercise | Promotion evidence |
| --- | --- | --- |
| T1 | Every valid/invalid state transition, all four responsibility values, initial assignment, eligibility/time/reference/version branches, postmortem completion/outcome/evidence branch, fixed-severity deadline bucket, unavailable snapshot, schema bound and narrative-redaction rule | Unit report and controlled payload corpus |
| T2 | Simulated compromised passenger, driver, staff and leaked-provider-credential personas; eligible/inactive/expired/revoked/wrong-market responsibility candidates; replay, stale version, cross-scope and reference-confusion attacks | API/security-pack report with expected status/error matrix and generic candidate-refusal proof |
| T3 | Real PostGIS row locking, concurrent responsibility assignment and timeline appends, one-active-role uniqueness, append-visible tenure trigger, idempotent replay, audit linking, append-only timeline trigger, one-time postmortem completion/deadline transition, account/session containment and staff-grant request linkage | Migrated database report and sanitized responsibility/audit/timeline/metric reconciliation |
| T4 | Security lead reviews and reassigns responsibility in the web workspace with keyboard/screen reader, narrow viewport, stale state, MFA step-up and network loss | Recordings, accessibility report, role-comprehension result and no-replay proof |
| T5 | Hosted synthetic incident and time-shifted deadline produce the exact fixed-severity alerts; responders acknowledge/escalate, rotate a disposable provider secret, revoke synthetic sessions, exercise failover and preserve bounded evidence | Prometheus/receiver/incident timestamps, secret-manager audit reference and RTO/RPO result |
| T6 | Named staff run passenger, driver, staff-account and provider-credential tabletop/technical drills without direct database edits; every exercise assigns response, communications, operations and postmortem ownership from the approved duty roster | Roster/shift references, responsibility handoff history, containment timings, communication decision and postmortem owner |
| T7 | Field exercise invokes pause/support while synthetic or consenting staff devices are active; no public exposure | Device/field trace, safety handoff and recovery acceptance |
| T8 | Real-user pilot monitoring proves incident paging, pause and communications governance for the bounded cohort | Signed incident/no-incident review for every pilot window |
| T9+ | Rehearse one-city containment without leaking or interrupting another city, then repeat on the national duty cadence | Cross-city isolation evidence and closed follow-up actions |

Any exercise that cannot identify the incident lead, current state, next action,
authoritative containment record and communication owner is a failed exercise.
Synthetic incident summaries and references are erased under the approved test
retention policy; immutable audit evidence retains no copied narrative.

## 4. Phase cards

### T0 — source and candidate integrity

**Entry:** a proposed candidate and documented scope exist.

**Execute:** documentation/link/status validators; formatting/lint/static analysis;
OpenAPI and mobile/web contract generation; migration-chain and offline-SQL checks;
deterministic OpenAPI-operation, migration-graph and role-permission inventory;
secret scanning; dependency lock and license checks; Android/iOS/web compile graph;
container build, SBOM, provenance and vulnerability gates; configuration and
production-manifest validators. Validate strict client version/build metadata in
both mobile and web artifacts and a complete six-surface minimum/recommended
policy in every production-like manifest.

Run independent blocking audits for the runtime and development Python locks;
the Linux CI runner includes its reviewed platform supplement. Preserve the
platform-specific hash boundary: Windows checks do not resolve Linux-only wheels
or add source-distribution hashes merely to make that audit pass. Retain both
reports with the candidate; neither one clears browser, container, native SDK or
default-branch findings by implication.

**Exit:** all required jobs pass from the same clean immutable commit; generated
contracts have no unexplained drift; no committed secret; no unreviewed migration;
the generated source-contract inventory is hash-bound to candidate evidence;
high/critical supply-chain findings are fixed or independently accepted within a
bounded non-launch scope.

### T1 — unit, property and component behavior

**Entry:** T0 passes for the changed scope.

**Execute:** state transitions, authorization and city/operator isolation; fare and
fee conservation; matching eligibility/fairness; schedule overlap and time zones;
idempotency/replay; rate and size limits; retention/erasure/hold rules; provider
adapter timeout/malformed/oversized/redirect behavior; localization parity;
accessibility semantics; log/metric/push redaction; workload and monitoring parser
mutation tests.
For mobile hint recovery, run the HINT-06 shared subscription, authentication-
lifetime and Ktor cancellation suites on JVM and Android host targets. Include
unchanged-ready network/foreground return, one socket at a time, credential
replacement/late callbacks, serialized refresh, logout during cleanup, normal
close/flapping jitter and bounded handshake/REST stalls. Mutation-check both
native wiring paths in T0; compile both Android roots and verify iOS compile/link
jobs on macOS. These do not accept native OS/device behavior or server-side
ongoing socket authorization.
For protected native credentials, run the Android adapter source pack and common
authentication storage/lifetime suites from `testing.md`. Distinguish missing
records from initialization/read/decrypt/corruption failures; require checked
save/clear commits, complete legacy migration, cancellation propagation and
sanitized exception chains. Recreate stores sharing the preference facility
during writes and after a failed commit; the shared lock/uncertainty fence must
remain authoritative until a confirmed explicit save/clear. Separate facilities
must not share that failure. Synthetic cipher/prefs tests do not prove Keystore,
AES-GCM, filesystem durability, process-loss or physical-device behavior.
For HINT-08, add server verified-token, final-hop ownership and real ASGI protocol
tests: idle/pre-send authority, JWT/database expiry, one-session/account-wide
revocation, failed/blackholed authority, serialized sends/recipient isolation,
cancelled admission/publisher/closer, already-closing shutdown, late accept and
inbound text/binary rejection. Distinguish cooperative cleanup from a deliberately
cancellation-suppressing adapter; require bounded removal plus a fixed warning,
not a claim that Python forcibly reaped it. See the ordered HINT-08 pack in
`testing.md` for exact executable files and field progression.
For staff authority, generate every request/decision status, identity role,
scope shape, expiry boundary, expected-version mismatch and continuity count;
assert that no intermediate database state satisfies only half a decision.
For security incidents, generate all four responsibility values, every candidate
eligibility failure, same-assignee conflict, backdated/future assignment, stale
version, duplicate idempotency key and completed-postmortem refusal. Prove that a
reassignment changes one active tenure into one released tenure plus one active
tenure without exposing candidate existence outside the authorized market.

**Exit:** deterministic tests cover every changed success, denial, duplicate,
timeout and rollback branch; no client can manufacture authoritative state; all
known S0/S1 defects are closed.

### T2 — simulated personas and adversarial journeys

**Entry:** T1 rules pass and each journey has an expected authoritative end state.

**Execute:** scripted new/returning/disabled passengers; eligible/ineligible/
offline/busy drivers; applicant/reviewer/finance/support/safety/city/platform roles;
cross-user, cross-city and cross-operator attackers; immediate, fixed-route and
scheduled rides; cash and manual-transfer states; cancellation, decline, expiry,
no-supply, stale UI, duplicate command, lost response and provider outage.
Include maker, checker, target, wrong-market, suspended-target, expired-admin and
quorum-bootstrap personas; simulate duplicate pending submissions, competing
approve/reject decisions and an ambiguous response after commit.
Add incident commander, communications lead, operations liaison and postmortem
owner personas. Exercise absent, inactive, expired, revoked and wrong-market
candidates through the same generic refusal, then reconcile the approved roster
reference, current lead, responsibility history and generated timeline facts.

**Exit:** every critical journey has a stable scenario ID; API result, database
facts, audit, notification/outbox and money facts reconcile; the simulator emits
no personal data and cannot bypass backend authority.

**Executable baseline:**
`infra/testing/simulated-persona-catalog.json` freezes 20 source-level scenario
IDs and 66 exact pytest nodes across authentication, inactive accounts, driver
eligibility/recruitment, matching, rides, coordination, fixed routes, scheduling,
cash, transfers, refunds, staff/scope/city authority, notifications, support,
safety, security incidents, and client lifecycle. Run it only through
`infra/scripts/run_simulated_persona_suite.py`. The runner rejects unknown fields,
missing categories, duplicate or non-unit selectors, external-network/real-user/
live-money flags, skips, count drift, and overwritten evidence paths. Its report
always leaves `phase_accepted`, `phase_evidence_complete`, and
`deployment_accepted` false. It supports only the simulated-persona matrix and
critical-journey report; complete T2 still requires separate adversarial review,
state/money reconciliation, test-data-minimization evidence, and both required
sign-offs. A pytest guard denies DNS and non-loopback sockets while allowing only
literal loopback/Unix-local runtime channels; it does not convert these unit tests
into real HTTP evidence.

### T3 — fresh-PostGIS multi-role system tests

**Entry:** T2 scripts and synthetic fixtures are frozen; the isolated database can
be destroyed safely and rebuilt through the current migration head.

**Execute:** full backend suite; real HTTP/CLI/worker child processes; migration
upgrade/downgrade/preflight and concurrent migrator ownership; lock-order races;
worker lease/kill/reclaim; dispatch contention; account/city-authorization changes
during assignment; location/schedule handoff races; cash/transfer/refund database
conservation; backup and current-head restore rehearsal.

The live-channel slice must terminate only the listener's observed owned backend
PID in its disposable migrated database, observe readiness loss, verify a
different replacement PID and actual `LISTEN` channel registration, deliver the
next minimized hint only to its addressed socket, and leave no connection or
dispatch task behind. `generate_t3_system_report.py` requires this named case in
the `LIVE_HINT_RECOVERY` coverage bucket. A TCP reconnection alone is insufficient
evidence of subscription recovery; this does not prove hosted failover.

The final socket hop must also use actual migrated SQL: commit a single-session
revocation, then account suspension, and separately expire a database session.
Fresh reads must deny wrong-user/absent/expired/revoked authority, preserve another
valid session where appropriate and close idle owners without waiting for a hint.
The `LIVE_SESSION_AUTHORITY` bucket requires both exact cases from
`test_live_session_authority.py`; omission of either fails the report. Fake
listener grants and ASGI seams are not substitutes. Include full-suite, clone,
temporary-role and restore evidence in the same T3 bundle.

After any pytest/async-plugin upgrade, repeat this entire T3 pack with explicit
function-scoped fixture and test loops. Retain the exact lock identities, full
skip-free JUnit report, migration/PostGIS metadata, named concurrency and
worker-recovery cases, zero residual clone count, revoked temporary database
authority and the current-head restore report. Mixed synchronous `asyncio.run`
fixtures and marked async tests must still create and dispose engines within
their owning loop. Passing a narrow unit slice or installing a compatible pair
is not sufficient evidence of isolation or transaction correctness. The
existing formal engineering sign-off and ordered promotion record remain
required; upgrading the runner cannot accept T3 by itself.

The staff slice must additionally prove migration 0049 upgrade/downgrade,
partial-unique pending requests, market-lock serialization, stale-authority
revalidation, request/grant/audit atomicity, two-admin continuity and closure of
the offline quorum bootstrap after its third member.

The incident slice must prove migration 0052 upgrade/downgrade/backfill, the
partial unique active-responsibility index, one-time release trigger, concurrent
assignment serialization, lead-field synchronization, generated timeline order,
minimized audit metadata and postmortem-complete mutation refusal.

**Exit:** a fresh database run has zero failures/errors/skips except explicitly
reviewed platform exclusions; every synthetic account/ride/offer/booking/payment/
outbox/audit row reconciles; no orphan process/database remains; evidence is
repeatable from a clean checkout.

The 2026-09-09 bounded local run now has executable JUnit, database metadata and
system-report records. It passed 992 tests, confirmed PostgreSQL 16.14/PostGIS
3.5.3 at migration 0052, removed one stale clone left by an earlier interrupted
run, found zero clones afterward and confirmed local `CREATEDB` authority was
revoked. A subsequent guarded logical backup restored 81 public tables and 8,511
aggregate rows into an ephemeral database, matched PostGIS/schema/table counts,
accepted a no-op upgrade to head, and removed the target and dump. The combined
report supports all six required T3 evidence kinds and marks evidence complete.
It does not accept T3 because engineering sign-off and an ordered promotion
record remain absent; its source binding is a dirty-workspace snapshot, not
immutable CI evidence.

### T4 — device, browser, accessibility and degraded-network lab

**Entry:** signed or release-equivalent candidate artifacts point only to the test
environment; supported OS/browser/device/language matrix and test accounts are
approved.

**Execute:** Android and iOS install/upgrade/restart/background/permission flows;
on a physical iPhone prove before-first-unlock Keychain unavailability is
explicit and does not claim success, then verify save/restore/logout unlocked,
relocked, after process kill, and through an interrupted/retried save with proof
that no split pair, stale pre-release entry, or silent native error remains;
on physical Android devices run the ordered protected-session pack in
`testing.md` for both products. `T4-AND-001` requires real Keystore, persistence
failure, Activity recreation and secret-leak checks; `T4-AND-002` requires
supported legacy migration, corrupt-record preservation and no key creation on
read; `T4-AND-003` requires failed-logout persistence and confirmed explicit
recovery. Only an approved synthetic lab harness may inject native failures;
an unavailable safe injection path is blocked evidence, not a host-test pass;
narrow/wide operations and applicant browsers; EN/FR/AR and RTL; screen reader,
font scaling, contrast, focus and touch targets; account recovery secret storage;
map fallback; GPS freshness/battery; push foreground/background/killed app;
offline/slow/loss/duplicate responses; crash capture and symbols. Exercise a
current, optionally outdated, intentionally obsolete, malformed and unreachable-
preflight build on each applicable surface. Obsolete clients must show the
approved blocked state without sign-in or command execution; current clients
must restore normally.

For staff access, test queue comprehension, keyboard-only selection, focus return,
screen-reader identity/action/version announcements, typed confirmation, narrow
layouts, stale refresh and MFA-step-up without automatic command replay.
For incident responsibility, test recognition of active versus released tenure,
the four role labels, exact-UUID error prevention, confirmation clearing,
stale-version recovery and screen-reader announcement of the authoritative
current assignment without a broad user-search or roster-disclosure surface.

For GAP-009 live subscriptions, disconnect the socket without changing the
ready-state category, then restore network/foreground and explicitly refresh.
Require authoritative REST catch-up **and** an observable replacement subscription
that receives the next hint. Repeat through access-token rotation, account
switch/logout, server restart and denied/re-enabled push permission. Confirm no
hint after session revocation/expiry and no automatic replay of a ride/payment
command. The shared unchanged-ready reconnect/session-ownership path now has
source regressions and mutation-checked native wiring; require actual device
traces rather than promoting those checks into physical acceptance. HINT-08's
server authority now has source and migrated test paths; repeat it with two
independent installations, one-session revocation and account-wide suspension,
idle expiry and refresh, server-close/network races and the next authorized hint.
Field acceptance must acknowledge that already-started/sent frames cannot be
recalled and cannot infer a revocation SLO from source defaults.

For GAP-007 automatic lookup races, first run
`ForegroundDriverLocationResultGuardTest` in T1 with synthetic contexts. At T4,
delay an authorized lookup on each physical Android/iOS driver app, then complete
it after (a) background/foreground return, (b) network loss/recovery, (c) an
availability command, (d) logout/login, (e) a backend-refreshed city, service,
vehicle or ride change, and (f) root disposal/recreation. Repeat with a coordinate
and with null/timeout. The obsolete result must produce neither a location write
nor unavailable guidance in the later context; a newly started eligible lookup
must still work. Check pending-command priority and absence of overlapping native
lookups or recurring permission prompts. Retain sanitized request counts and
screen-state observations, never precise coordinate trails or account tokens.
At T7 repeat the lifecycle/network cases during the approved closed-cohort shift
and measure freshness and battery against frozen thresholds. T1 success does not
accept native timing, T4, T7 or GAP-007; background tracking remains unapproved.

For GAP-008, run the shared reverse-selection and JVM picker regressions before
T4. On each Android/iOS passenger surface in Arabic/French/English, search a
landmark, edit/clear/shorten the query, switch city and deliver an older response.
Only results matching the current city and normalized query may remain
selectable. Delay reverse lookup for both pickup and destination, move the point
or switch city before coordinate/no-result completion, and prove that neither
the new point nor its label is overwritten and no stale completion warning
appears. An unchanged point must receive its label without moving. Repeat under
GPS loss, provider outage and slow network with usable map/manual fallback.
Retain synthetic request/selection assertions, not query or precise participant
trails. T7 then tests real landmark ambiguity and wrong-city pickups against the
approved multilingual benchmark; source checks do not accept provider quality.

**Exit:** all critical journeys are usable on the minimum supported matrix; no
secret or private data leaks through screen, clipboard, cache, logs or analytics;
crashes and accessibility blockers are below approved thresholds; unresolved S2
findings have an owner disposition before T7.

The Android launcher can now retain a bounded registration/login device report
for either role with `-RegistrationSmoke -ConfirmClearAppData -EvidencePath
<new-json>`. It records no raw serial, screenshot, credential or entered value
and recognizes only the two backend-confirmed journeys. This starts
`ANDROID_DEVICE_REPORT`; it does not satisfy the supported matrix, iOS/browser,
accessibility/RTL, degraded-network/lifecycle or crash-symbolication records and
cannot mark T4 accepted.

The machine-readable T4 catalog freezes 56 laboratory cases, exactly eight for
each of the seven required evidence kinds. It cross-checks source platform
targets, physical-device and real-browser requirements, locales, RTL, safety
flags, observations and blocking severity. The evidence validator credits a
kind only when all eight cases pass with retained SHA-256 evidence; failed or
blocked cases require defect references. The committed template remains
`NOT_STARTED` with 0/56 cases and no acceptance claim.
Revision `2026-10-02` strengthens the existing three Android credential cases
without adding new IDs or claiming execution. Validator mutations reject removal
of observations, either product/role, the physical-device boundary, S0 severity
or case identity. The exact catalog-byte hash uses a narrow LF checkout rule;
old revision/hash records must be recollected for affected observations, never
relabeled as new evidence. T5–T7 then require hosted session outcomes, a trained
storage-failure/recovery rehearsal and approved field observations before T8.

`infra/scripts/run_t4_browser_smoke.py` is a narrower executable precursor to
the browser evidence class. It validates a packaged release, serves a loopback
origin with synthetic compatibility responses and runs four fail-closed boot
scenarios per selected Chrome/Firefox family. Every scenario requires the exact
surface/version/build preflight, the expected blocked-or-single-runtime-branch
result and a retained valid screenshot. The report explicitly states that
browser egress is not independently firewalled, lists Safari as missing and
leaves catalog-case, phase and deployment acceptance false. The 2026-09-09 local
run passed 4/4 scenarios in Chrome 152 and 4/4 in Firefox 155; it starts evidence
collection but does not complete any of the eight `BROWSER_COMPATIBILITY_REPORT`
catalog cases.

### T5 — hosted staging, capacity, security and failure recovery

**Entry:** production-like hosted topology, protected monitoring, synthetic data,
named responders, approved SLO/RPO/RTO and an owner-approved workload profile exist.
The target's protected GAP-002 record must pass
`validate_production_environment_inventory.py --inventory <record> --require-accepted`;
the repository's `NOT_STARTED` template is not entry evidence.

T5 entry additionally requires an accepted protected GAP-005 operations identity
and governance record. It must bind the authoritative staff roster/JML source,
three-person platform-admin quorum, independent sensitive duties, reviewed MFA
and recovery custody, current access review, leaver and break-glass drills, audit
references and four approvals. That gap record never accepts T5 or deployment.
Its protected GAP-003 record must also pass
`validate_managed_postgis_evidence.py --evidence <record> --require-accepted`
before database restore/failover/RPO/RTO claims can satisfy T5 entry.

Any T5 map, routing, tile, narration or provider-failure claim additionally
requires the protected GAP-006 record to pass
`validate_maps_routing_navigation.py --evidence <record> --routing-report
<exact-report> --require-accepted`. Its report digest must match the redacted
backend acceptance output from the selected target, with every fixed scenario
passing English, French and Arabic. The same record must bind approved immutable
style/tile/graph artifacts, policy controls, six pilot-city route categories,
four role/platform device surfaces, seven drills and six approvals. This gap
record does not accept T5 and does not replace T4 physical-device or T7 road
evidence.

**Execute:** WARMUP/STEADY/BURST/RECOVERY and soak with independent API/worker
replicas; all critical read/write and worker loops; database plans, locks, pools,
CPU/IO/storage/network; queue/dead-letter/oldest-age; route/geocode/tile/push/
scanner/pager latency and outage; replica kill, connection exhaustion, database
restart/failover, object-store denial, alert receiver failure, restore, rollback,
forward-fix, secret rotation and emergency city pause; SEC-01–SEC-11 plus independent
penetration review. Raise the minimum from an accepted old build to the candidate,
observe HTTP `426` and WebSocket `4406`, verify mobile/web guidance and support
communication, then exercise the approved policy rollback or forward-fix without
weakening authentication or deleting user data.

For live-hint recovery, independently break/blackhole the dedicated listener
while pooled SQL still works. Observe `/ready` fail closed, load-balancer removal,
bounded probe/cleanup/re-registration, healthy re-admission and measured recovery
against the frozen RTO. Exercise database restart/failover under concurrent
commands, duplicate/out-of-order/missed hints and REST reconciliation; verify no
command replay, extra assignment, changed economics or unauthorized recipient.
Retain redacted timing/health/recipient evidence. Repeat mobile unchanged-ready
reconnection, token refresh, logout/revocation and permission/network/lifecycle
recovery in T4 before using real participants; current source does not yet prove
all those subscription/session behaviors.

HINT-08 additionally freezes a revocation/expiry/authority-outage budget. Use two
API replicas, idle and busy sockets for one synthetic user, a stalled receiver,
SQL delay/blackhole distinct from listener loss, and shutdown during admission/
close. Measure detection and cleanup, REST rejection/recovery, active-socket and
hint-rate pool pressure, checkout wait and database connection reserve. Confirm
no authority cache, raw credential/identity logs or business-command replay.
Review the read/send race and cancellation-cooperation limitations against the
intended exposure before staff or real-user promotion.

**Exit:** workload, monitoring and reconciliation all pass the frozen profile;
resource headroom and cost envelope are accepted; primary and backup responders
receive and resolve alerts; restore/failover/rollback meet RPO/RTO; no open critical
or high security issue lacks independently approved bounded treatment.

### T6 — trained-staff synthetic operating rehearsal

**Entry:** T5 passes; named least-privilege staff have MFA, runbooks and on-call
coverage; all data and payment records remain fictional. The protected GAP-004
record passes `validate_pilot_city_launch_approval.py --approval <record> --require-accepted`,
binding the rehearsal to one reviewed city/operator scope
without claiming that T6 or deployment has passed.

**Execute:** city setup and two-person release; driver application/document review;
tariff/payment/fixed-route/schedule publication; immediate and scheduled journeys;
cash/transfer/refund reconciliation; routine support and urgent safety paging;
shift handoff; joiner/mover/leaver and account containment; provider outage,
database restore, release rollback and emergency pause.
Run a shift-handoff incident exercise in which the approved roster changes at
least two responsibilities, the prior tenures remain visible, the new response
lead is authoritative, communications and postmortem ownership are understood,
and no developer or direct SQL intervention is used.

**Exit:** staff diagnose and recover without hidden developer/database edits;
response times meet targets; every privileged action is scoped/audited; finance,
safety, privacy, release and shift-handoff reviews are signed.

### T7 — closed-cohort non-public field validation

**Entry:** legal, insurance, participant-consent and safety plan approved; T4–T6
pass; participants can stop immediately; no public passenger or unapproved money.

**Execute:** dense/edge/weak-network/GPS-obstructed geography; one-way roads and
landmarks; online/location/offer/decline/expiry; pickup/navigation/arrival/start/
completion; fixed-route direction recognition; scheduled punctuality and fallback;
app kill/restart and long-shift battery; delayed/lost push; accessibility/language;
support contact, pause and rollback while devices are in the field.

**Exit:** pre-approved route, pickup, GPS freshness, battery, notification, crash,
task-success, comprehension and response thresholds pass; no safety or privacy
stop event remains unresolved; participant feedback and withdrawals are closed out.

### T8 — bounded real-user city pilot

**Entry:** every applicable P0 gap has a signed closure; production artifacts and
configuration are frozen; public support, duty roster, rollback and city-pause
owners are active; participant limits and exposure steps are approved.

**Execute:** invite a small licensed-driver and passenger cohort for one service
area and operating window. Increase only one of users, hours, geography or feature
set at a time. Monitor assignment, pickup, completion, cancellation, fairness,
payments, provider quality, crashes, support/safety and privacy-safe feedback.

**Exit:** minimum sample/exposure and observation window are met; aggregate service,
safety, money, support and fairness thresholds pass; all incidents and defects have
signed dispositions; rollback/pause remains proven. T8 is not permission for public
city-wide service.

### T9 — guarded public city launch

**Entry:** T8 exit review authorizes a named city/configuration/candidate and sets
daily exposure steps, stop thresholds and decision times.

**Execute:** progressively expand cohort, hours and area; compare every window to
the frozen T5/T7/T8 baseline; review capacity, supply, cancellations, money,
support/safety, provider errors and fairness daily; preserve instant city pause,
feature disablement and rollback.

**Exit:** the defined stabilization window passes with sustainable staffing,
provider capacity, cost, supply and SLOs; post-launch review records corrections
and whether expansion is approved, held or rolled back.

### T10 — second-city and national repeatability

**Entry:** first-city closeout is accepted and the next city has its own legal,
operator, tariff, provider, language, geography, staffing and capacity approvals.

**Execute:** repeat T4–T9 for city-specific behavior; test cross-city/operator data
and authority isolation; simultaneous city peaks and emergencies; national control
plane, analytics suppression, support routing, provider quotas, database growth,
backup/failover and cost forecasts.

**Exit:** at least a second city launches through the same controlled procedure;
city isolation and simultaneous-load thresholds pass; national operations can
pause, support, restore and audit one city without affecting another.

## 5. Stop and rollback rules

Stop the current test immediately for suspected safety harm, wrong assignment,
authorization bypass, cross-scope data exposure, account compromise, money loss
or misdirection, unrecoverable corruption, missing urgent escalation, or inability
to pause/rollback. Freeze new arrivals, preserve minimum necessary evidence, keep
active participants safe, invoke the incident owner, and reconcile authoritative
state before restarting. Do not erase evidence or retry with new idempotency keys
to make an ambiguous result appear successful.

T5–T9 additionally stop when workload monitoring is incomplete, a protected
monitoring surface is publicly reachable, a critical alert reaches neither duty
receiver, capacity/resource headroom falls below its approved floor, or the run
uses a different artifact/configuration/profile than the evidence index records.

## 6. Minimum cohort design before real users

Before T7 or T8, freeze—not infer during the run—the participant count, journey
count, geography, operating hours, device/language/accessibility representation,
driver supply ratio, observation window, thresholds, confidence/decision rule,
withdrawal process and compensation. Product, operator, safety and privacy/legal
owners approve the design. Small samples may discover usability or safety defects,
but must not be presented as statistical proof of national demand, fairness,
reliability or capacity.

Use T7 for physical truth without public service. Use T8 only for questions that
cannot be answered safely with synthetic or trained participants. Never generate
fake production demand, mix automated load with real cohorts, or expose real users
to intentional destructive chaos.

## 7. Current next actions

1. Produce one clean immutable T0/T1/T3 candidate run through migration 0052 and
   retain its provenance, including responsibility migration and concurrency
   evidence, in a validated candidate evidence index.
2. Complete the T4 device/browser matrix and decide the foreground driver-location
   model from measured battery, freshness and dispatch behavior.
3. Provision production-like T5 staging and protected provider credentials.
4. Approve SLO/RPO/RTO and replace the DRAFT capacity profile with a controlled,
   signed pilot-city profile; collect workload, application/queue and host/database
   resource evidence together.
5. Complete independent security review, real alert routing, restore/failover and
   rollback/city-pause exercises.
6. Establish the authoritative incident duty roster and escalation receiver, then
   run the T6 responsibility-handoff/containment rehearsal; only afterward approve
   and recruit a T7 closed cohort.
7. Close every applicable P0 record before requesting a T8 real-user decision.
