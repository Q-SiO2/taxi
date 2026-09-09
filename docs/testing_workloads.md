# Synthetic HTTP Workload Runbook

This is the executable workload companion to [the phase map](testing.md) and
[GAP-018](gaps.md#gap-018--prove-performance-capacity-availability-and-failover).
It does not authorize traffic against production or a real-user pilot.

## Implemented workload and evidence boundary

`python -m taximobile_api.operations.passenger_workload` executes
`passenger_request_cancel_v1` through real HTTP APIs. Each independent passenger:

1. Registers a unique `load-<run-id>-<index>@taximobile.invalid` account with a
   random, in-memory password and no phone number.
2. Logs in and verifies that `/me` identifies the registered passenger, with no
   driver or administrator role. All accounts must pass admission before rides start.
3. Requests an on-demand estimate in the explicitly selected synthetic city,
   requiring cash capability and the same city in the response.
4. Creates a cash ride, repeats the identical command with its original
   idempotency key, and requires the identical response.
5. Reloads the ride and checks ownership through the authenticated API, city,
   payment method, unassigned driver and `REQUESTED`/`MATCHING` state.
6. Cancels the ride, repeats cancellation with its original key, and compares
   responses. A final fresh GET must confirm the same ride is `CANCELLED`.

Journeys are sequential per passenger and concurrent between passengers. This
is a **closed-loop** workload: slow responses reduce offered request rate. It
is not an open-loop arrival generator, peak-city capacity forecast, completed
trip/payment benchmark, notification delivery test, or UI automation.

The real-HTTP integration test starts Uvicorn on a bound ephemeral loopback
socket, invokes the actual workload CLI as a separate process, and checks fresh
PostGIS facts: four rides, four cancelled offers, four cancellation events,
four cancellation outbox rows, eight idempotency records, and restored driver
availability. A second case confirms that default registration limits refuse
the sixth account before any ride writes. The fixture supplies an active tariff
and inert authorized drivers before measurement. Those SQL fixture facts do not
prove document review or real driver onboarding; the runner has no SQL or admin
access and does not bypass application rate limits.

This workload exposed candidate-set overlocking: one request reserved all nearby
drivers, causing another request to incorrectly end unmatched. Dispatch now
discovers/ranks without those locks and rechecks full eligibility while locking
one candidate at a time. If all discovered candidates are temporarily locked or
changed, a still-matching ride is retried by the matching worker. True empty
discovery and the existing overall matching deadline remain terminal. Three
deterministic PostGIS cases supplement the HTTP run with held-transaction proof,
worker retry and deadline exhaustion.

## Constant-arrival capacity baseline

`python -m taximobile_api.operations.capacity_workload` executes
`passenger_request_cancel_open_loop_v1`. It reuses the exact passenger journey
and HTTP safety boundary above, but releases arrivals against an absolute
constant-rate schedule instead of waiting for the previous response. All
passengers are registered and identity-checked before measurement. `--users` is
the hard actor and HTTP-connection cap; no actor starts a second ride until its
previous ride is authoritatively cancelled. The total schedule is bounded to
1,000 arrivals and the whole run remains bounded by `--duration-seconds`.

Each released arrival waits in a bounded-by-plan task set for an available actor.
The report distinguishes the requested arrival rate from actual journey
throughput and adds arrival p50/p95/p99/max lag, lag-budget failures, peak
in-flight journeys, peak actor waiters, admission time, measured time and total
time. Queue lag therefore exposes saturation instead of letting a closed loop
silently lower demand. A first HTTP, shape or state-invariant failure stops new
arrivals; released work checks the stop condition before obtaining an actor.
Ambiguous writes retain the same-key recovery and unresolved-command rules.

The real CLI/socket/PostGIS test releases four arrivals, then reconciles four
cancelled rides and offers, eight idempotency records, four cancellation events,
four outbox rows and restored driver availability. This proves scheduling,
boundedness and durable reconciliation on a tiny local fixture. It is not a
sustained/burst profile, representative city dataset, multi-replica result,
resource-capacity measurement, approved SLO or failover exercise.

## Reviewed four-phase capacity profiles

`python -m taximobile_api.operations.capacity_plan` executes an immutable
four-phase workload definition rather than a hand-assembled sequence of commands.
The strict JSON profile contains target-independent geography, workload,
monitoring cadence and operational-threshold parameters and must have exactly
this order:

1. `WARMUP` checks readiness and connection establishment at low demand.
2. `STEADY` gathers the reviewed baseline at sustained demand.
3. `BURST` applies the reviewed short peak without changing safety controls.
4. `RECOVERY` returns to low demand and proves latency/backlog recovery.

Copy the deliberately non-runnable
[`capacity-profile.template.json`](../infra/load/capacity-profile.template.json)
into the controlled evidence workspace. Review every value, assign a unique
lowercase `profile_id`, set a controlled `approval_reference`, and change status
from `DRAFT` to `APPROVED` only after product, operations and engineering owners
approve the workload and thresholds. The status text and
`--confirm-approved-profile` flag are mistake-reduction attestations; they do not
prove that approval happened. The signed/reviewed profile and meeting or ticket
evidence remain outside the repository result JSON.

The parser rejects unknown fields, wrong phase order, symbolic/non-finite numbers,
more than 1,000 total arrivals, more than 2,400 reserved seconds, symlinks and
files over 64 KiB. Every phase and target is validated before network I/O. The
executor stops after the first failed phase, reports all unexecuted phases, and
includes a SHA-256 digest of canonical profile semantics without emitting the
target origin, city UUID or coordinates. Each nested phase retains its own run ID,
latency, arrival-lag and unresolved-command evidence.

For an acceptance-oriented run, `--prometheus-url` attaches one protected
Prometheus sampler to every phase. It issues only 22 source-defined aggregate
instant queries: core target availability, HTTP request rate/5xx ratio/p95,
worker success age/error increase, outbox pending/oldest/dead-letter state,
unhandled-error increase, dropped-log increase, log-delivery-failure increase,
database-snapshot availability, connection utilization/active count, waiting
locks, deadlock increase, and per-process pool availability/checked-out/overflow,
checkout-wait p95 and checkout-timeout increase.
The response must be one unlabelled finite vector value per query; redirects,
labels, multiple series, non-200, malformed or larger-than-64-KiB responses fail
closed. The evidence contains summaries, fixed failure codes and the 21 reviewed
thresholds, but no Prometheus origin, expression, target label or response body.
Every query must succeed in every sample round and every threshold must pass for
the phase to be `COMPLETE`; otherwise later phases do not execute.

```powershell
python -m taximobile_api.operations.capacity_plan `
  --profile C:\controlled-evidence\casablanca-pilot-v1.json `
  --base-url https://synthetic-staging.example `
  --confirm-synthetic-target --confirm-nonlocal-target `
  --confirm-approved-profile `
  --prometheus-url https://protected-prometheus.example `
  --confirm-monitoring-target --confirm-nonlocal-monitoring-target
```

`--confirm-harness-without-monitoring` is reserved for deterministic local
unit/integration harness proof. It is mutually exclusive with `--prometheus-url`,
sets `monitoring_evidence_complete` false, and cannot satisfy T5. The current
sampler does not measure host CPU, memory, disk/network, query plans, provider
latency or client crash-free sessions; attach those controlled
sources to the evidence bundle before making a capacity or deployment claim.

Capture the reviewed profile bytes, semantic digest, stdout JSON, process exit,
candidate commit/image/migration identity, infrastructure metrics and database
reconciliation in one evidence bundle. A changed profile is a new workload and
must receive a new review; do not compare results under one profile identifier.

## Paired driver/passenger cash workload

`python -m taximobile_api.operations.cash_workload` executes
`paired_cash_complete_v1`. It shares the bounded HTTP client, configuration and
aggregate metrics with the cancellation runner, but uses separate driver
admission and cash-journey modules. It **writes synthetic payment and earning
records** and requires the additional `--confirm-synthetic-cash` attestation.
It must never be used to manufacture completed rides or cash receipts in a
real-user environment.

The operator supplies exactly one distinct, pre-approved synthetic driver per
passenger through `TAXIMOBILE_WORKLOAD_DRIVERS_JSON`. The environment value is a
JSON list of objects containing only `user_id` and `access_token`; obtain these
short-lived mobile sessions from the isolated target's normal login flow. Do not
put tokens in command arguments, committed files, screenshots or shared logs.
The CLI removes this variable from its own environment after parsing; the caller
must also clear its parent-shell copy after the run. No driver credentials are
printed, refreshed automatically or persisted by the runner.

Before any passenger registration, location update or online command, every
driver must pass read-only admission:

* `/me` matches the configured UUID and has `DRIVER` with no roles outside
  `PASSENGER`/`DRIVER`;
* the driver profile belongs to that user, is active and approved, is offline,
  and has the deliberate `Synthetic ` display-name prefix; and
* the driver's current offer list is empty.

The display-name marker is a mistake-reduction check, not proof of synthetic
identity or a substitute for exclusive environment ownership. The runner never
approves an application, edits a vehicle, changes a tariff or grants driver
authority. Its separate PostGIS test fixture creates approved profile evidence,
vehicle and city-authorization facts before HTTP measurement; this is not real
licensing/document-review evidence.

After passenger admission, the runner executes synchronized waves. Every wave
stages a current synthetic pickup coordinate through the location API and brings
each driver online in the selected city/on-demand service. The backend independently
enforces vehicle, credential, city, polygon and freshness requirements. Passengers
then concurrently request rides; they discover the backend's actual offer owner,
not a client-selected assignment. Driver polling ignores offers for rides outside
the current run. Reads do not reserve a driver; a per-driver lease is held from
matching-offer selection through that journey's final verification. Poll discovery
has at most 50 rounds with a 200 ms interval plus the per-request and whole-run
deadlines. This prevents the harness itself from waiting forever for an offer.

Each paired journey verifies:

1. Estimate, cash capability, create and identical same-key create replay.
2. Unassigned passenger restoration, actual driver acceptance, then passenger
   restoration after acceptance, en-route, arrival and start.
3. Completion and identical same-key completion replay, locked fare/currency,
   completed passenger state and a **pending** payment on the receipt.
4. Driver cash settlement and identical same-key settlement replay, followed by
   a freshly loaded **completed** cash receipt.
5. Estimate/receipt economic amounts and policy versions; only the optional
   scheduling-policy field may be omitted instead of null by receipt serialization.
6. Exactly one earning for the ride in the driver's latest 100 items; currency,
   expected driver net, operator allocation, `net + allocation = passenger total`
   and `gross - fees + adjustments = net`, using decimal strings rather than floats.
7. Confirmed offline drivers after completion. Between successful waves, the
   runner explicitly stages/starts availability again; it never assumes completion
   leaves a driver online.

These synthetic fee examples are automated evidence, **not approved tariffs**:

| Case | Transport fare | Passenger total | Driver net | Operator allocation |
| --- | --- | --- | --- | --- |
| Zero operator fee | 35.00 MAD | 35.00 MAD | 35.00 MAD | 0.00 MAD |
| Flat driver-funded fee of 5.00 MAD | 35.00 MAD | 35.00 MAD | 30.00 MAD | 5.00 MAD |
| Passenger surcharge of 10% | 35.00 MAD | 38.50 MAD | 35.00 MAD | 3.50 MAD |

The actual CLI/socket/PostGIS suite runs two passengers and two drivers through
two waves in each fee case. Fresh database reads require four completed rides,
accepted offers, fare records, financial snapshots and payments, exactly four
unique earnings, conserved amounts and offline drivers. Two additional cases
return HTTP 503 **after** completion or settlement has committed. Both runs must
fail and preserve an unresolved financial-command count. After completion failure
the single payment remains pending with no earning; after settlement failure it
is completed with exactly one earning. This proves post-commit non-2xx handling,
not TCP-reset, process-death or provider-outage handling.

If any stage fails, no new wave starts. Known pre-start rides may be cancelled
with an authoritative confirmation. Once `start` has been attempted, the runner
does **not** cancel, synthesize completion, settle again with a fresh key, refund
or delete records as cleanup. The unresolved count remains until a successful
normal journey proves receipt and earnings. Available drivers may be returned
offline; active-ride driver states are never forced offline. Setup failures also
attempt this bounded offline restoration. `drivers_not_confirmed_offline` exposes
remaining uncertainty. Cleanup shares the original run deadline; deadline/process
interruption requires manual synthetic-state reconciliation.

Example, after loading the approved synthetic driver sessions into the local
environment and completing the common safety prerequisites below:

```powershell
python -m taximobile_api.operations.cash_workload `
  --base-url http://127.0.0.1:8000 `
  --city-id 10000000-0000-4000-8000-000000000003 `
  --pickup 33.5731 -7.5898 --destination 33.58 -7.61 `
  --confirm-synthetic-target --confirm-synthetic-cash `
  --users 2 --journeys-per-user 2 --duration-seconds 120 --p95-budget-ms 1000
```

The same configuration bounds and exit codes apply. Reported load shape is
`CLOSED_LOOP_SYNCHRONIZED_WAVES`; elapsed throughput includes driver/passenger
admission, explicit online/location commands, barriers and cleanup. This is not
independent open-loop driver supply, physical GPS movement, realistic trip time,
real cash custody, bank transfer, payout, refund or national-capacity evidence.
Longer tests still need reviewed supply/location/admission pacing, expiry,
decline/no-show, weak-network, multi-worker and provider scenarios. Do not raise
rate limits or disable freshness to make a synthetic result pass.

## Safety prerequisites

Before starting, record a named test owner and verify all of the following:

* A disposable, isolated **synthetic-only** API/database/provider environment;
  no real passengers, licensed-driver accounts, identity files, money or paging
  destinations. Loopback is not proof of isolation: a tunnel can reach production.
* Migrated head, active synthetic city/operator/service polygon, effective
  tariff/operator-fee policy and cash capability. The compatibility city created
  by migration alone does not supply a working tariff or drivers.
* Enough independently eligible synthetic drivers for concurrent pending rides
  and current location samples inside the pickup radius. For the passenger-only
  cancellation scenario, no driver bot may accept these offers. For the paired
  cash scenario, only the supplied synthetic driver sessions may act on them.
  For sustained runs, synthetic drivers must maintain the normal location
  heartbeat; never disable eligibility/freshness checks to make a run pass.
* Working matching worker for contention retries. Separately monitor all eight
  worker loops when testing the full deployment; this runner does not start them.
* Exact origin, approved test geography, bounded volume/duration, owner-approved
  latency budget and an independently available stop procedure.
* A reconciliation/disposal plan. Accounts, sessions, rides, quotes,
  notifications, audit and idempotency history remain in the disposable database.
  The runner never bulk-deletes data or changes production configuration.

Both local and hosted targets require `--confirm-synthetic-target`. A nonlocal
origin additionally requires HTTPS and `--confirm-nonlocal-target`. These are
explicit operator attestations, **not server-side environment attestation**.
URLs containing credentials, paths, queries, fragments, whitespace or ambiguous
backslashes are rejected. Redirects and environment-derived proxies are disabled;
TLS verification stays enabled. No token/password flag is accepted.

## Run sequence

First prove the harness against the isolated integration database using the
repository's guarded PostGIS test setup (do not point its test variables at a
shared database):

```powershell
# From backend/, after the guarded integration environment is configured:
.venv/Scripts/python.exe -m pytest `
  tests/unit/test_passenger_workload.py `
  tests/unit/test_cash_workload.py `
  tests/unit/test_capacity_workload.py `
  tests/integration/test_passenger_workload_http.py `
  tests/integration/test_cash_workload_http.py `
  tests/integration/test_capacity_workload_http.py `
  tests/integration/test_dispatch_candidate_contention.py -q
```

For a separately provisioned synthetic API, choose the confirmed origin and
synthetic city first. This example uses the migration's Casablanca compatibility
UUID and public synthetic coordinates; it is valid only after its prerequisites
above have been provisioned in the **disposable** target:

```powershell
python -m taximobile_api.operations.passenger_workload `
  --base-url http://127.0.0.1:8000 `
  --city-id 10000000-0000-4000-8000-000000000003 `
  --pickup 33.5731 -7.5898 --destination 33.58 -7.61 `
  --confirm-synthetic-target --users 2 --journeys-per-user 2 `
  --interval-seconds 1 --request-timeout-seconds 5 `
  --duration-seconds 120 --p95-budget-ms 1000
```

The example's 1000 ms budget is an illustrative test setting, not an approved
product SLO. Capture stdout JSON and the exit code as evidence, then reconcile
the database and worker side effects before raising load. Do not repeat a failed
command blindly: a new invocation creates new accounts and new ride commands.

After that closed-loop baseline passes, the following **illustrative** command
checks constant-arrival scheduling. Replace its rate, duration and thresholds
only with a reviewed synthetic workload profile; do not point it at production:

```powershell
python -m taximobile_api.operations.capacity_workload `
  --base-url https://synthetic-staging.example `
  --city-id 10000000-0000-4000-8000-000000000003 `
  --pickup 33.5731 -7.5898 --destination 33.58 -7.61 `
  --confirm-synthetic-target --confirm-nonlocal-target `
  --users 10 --journeys-per-user 5 `
  --arrival-rate-per-second 1 --arrival-lag-budget-ms 250 `
  --request-timeout-seconds 5 --duration-seconds 180 `
  --p95-budget-ms 1000
```

| Control | Default | Enforced range / behavior |
| --- | --- | --- |
| Users | 2 | 1–50; one in-flight journey per user |
| Journeys per user | 2 | 1–100; no unbounded task queue |
| Between-journey interval | 1 second | 0–60 seconds; no sleep after final journey |
| Request deadline | 5 seconds | 0.1–30 seconds, including streamed body consumption |
| Whole-run deadline | 120 seconds | 1–600 seconds, including account admission |
| Per-operation p95 budget | 1000 ms | 1–60000 ms; all measured steps, including admission/recovery |
| Response body | 64 KiB | Oversized or malformed JSON fails the step |
| Redirect/proxy/TLS | Disabled / disabled / verified | Not configurable to unsafe values |

Additional constant-arrival controls:

| Control | Default | Enforced range / behavior |
| --- | --- | --- |
| Arrival rate | 1 journey/second | 0.01–100; absolute constant schedule, not achieved throughput |
| Arrival-lag budget | 250 ms | 1–60000 ms; any started arrival above it fails the run |
| Scheduled arrivals | users × journeys per user | At most 1,000; unreleased work is reported, never silently discarded |
| In-flight limit | users | 1–50 authenticated actors/connections; no overlapping ride per actor |
| Failure behavior | Stop release | Already released tasks finish or stop before issuing a journey; unresolved writes remain visible |

Registration, login and ride-creation limits remain real workload outcomes.
With default settings, rapid admission above five accounts or more than five
ride creates per account per minute should fail. A larger approved exercise
needs a reviewed admission/pacing and rate-limit workload design; increasing
these runner bounds is not permission to weaken production abuse protection.

## Failures, recovery and interpretation

The create/cancel recovery rules in the next four bullets describe
`passenger_request_cancel_v1` and `passenger_request_cancel_open_loop_v1`. The
paired-cash scenario instead follows the
stricter post-start rules in its section above: an unidentified create or any
uncertain started/financial journey stays unresolved for manual reconciliation.

* Any failed HTTP/transport/shape/invariant step prevents new journeys. Already
  active journeys finish or perform bounded recovery; they are not counted as
  successful if a measured step failed.
* If a create response is lost, the runner makes at most one recovery create with
  the **same** payload and key to identify the ride, then attempts cancellation
  and authoritative restore. It never substitutes a fresh key during recovery.
* A failed cancellation can be retried once with its original key in recovery.
  Failure remains in the report even if cleanup succeeds.
* `unresolved_ride_commands` counts create attempts without confirmed cancelled
  state in the cancellation scenario. In the cash scenario it counts create
  attempts without complete financial verification or confirmed safe pre-start
  cancellation. It is deliberately conservative, including ambiguous writes, a terminal
  unmatched result that did not satisfy this scenario, or a failed cleanup.
  Reconcile using the synthetic run prefix and retained database history.
* Whole-run expiry cancels in-flight work and emits a failed partial report.
  It does not extend its deadline indefinitely to clean up. Process interruption
  returns a fixed warning; a report may not exist. Inspect synthetic records
  before retrying. Provider/server commit may outlive a disconnected client.
* HTTP 429, unexpected terminal state, assignment, redirects, and invalid payloads
  are failures, not censored latency samples or automatic retries to success.

The JSON contains run ID, bounded load shape, admission/account counts, planned,
started/completed/not-started/incomplete journeys, request counts, closed outcome
codes, p50/p95/p99/max latency per step, journey latency, deadline/unresolved
counts and per-step budget failures. HTTP failure rates and response-invariant
failures are reported separately: an HTTP 200 can still fail an invariant.
Percentiles use nearest rank and include failed attempts. Threshold comparisons
use unrounded latency. Closed-loop elapsed time and throughput include admission.
The open-loop report provides separate admission, measurement and total time;
its completed throughput uses measurement time, while scheduled rate and arrival
lag remain separate fields. Neither is automatically steady-state throughput.
Low sample counts do not support reliable tail-latency estimates or an approved
service SLO.

No origin, coordinates, passenger/ride identifiers, passwords, tokens, response
bodies or raw transport diagnostics are emitted. The random synthetic run ID is
retained for controlled reconciliation. Unexpected CLI failures return a fixed
nonzero diagnostic; reproduce them in isolated tests rather than enabling raw
credential-bearing response logging.

Exit codes: `0` all planned journeys/invariants and every step budget passed;
`1` incomplete run, failure, unresolved command, deadline or exceeded budget;
`2` invalid configuration; `130` keyboard interruption. Only code 0 plus reviewed
JSON and reconciled side effects counts as passing this **specific** scenario.

## Phase progression and outstanding workload packs

| Pack | Phase / action | Evidence and promotion condition |
| --- | --- | --- |
| LOAD-01 | T1–T2 deterministic fake HTTP | Complete commands, distinct identities, stable idempotency keys, secrets absent, malformed/large/redirect replies, timeouts, cancellation, constant-arrival scheduling/backpressure and budget boundary checks; implemented locally |
| LOAD-02 | T3 two passengers, eligible synthetic supply | Real CLI/socket/PostGIS, four completed cancellation journeys, one offer/cancel event per ride, durable driver release; implemented locally |
| LOAD-03 | T3 admission failure | Sixth synthetic registration receives 429 with no ride writes; implemented locally |
| LOAD-04 | T3 candidate contention | Hold first dispatch open, another request uses a distinct driver; all candidates locked leads to retry, then offer or overall timeout; implemented locally |
| LOAD-05 | T3 broader failure injection | Actual CLI/PostGIS HTTP 503 after completion/settlement commit now covered; true connection loss, HTTP/worker process kill, multiple replicas, stale credentials/location, city pause and admin revocation still require system evidence |
| LOAD-06 | T5 sustained and burst arrival | Constant-rate open-loop passenger arrivals, lag/backpressure metrics, a strict reviewed-profile format, mandatory warmup/steady/burst/recovery execution, fixed privacy-safe application/queue/PostgreSQL/pool Prometheus phase sampling and real CLI/PostGIS reconciliation are implemented. Actual owner approval, representative values/sample sizes, multi-role journeys, hosted series, approved pool thresholds, and host/query-plan/provider resource observations remain open |
| LOAD-07 | T3 baseline toward T5 complete multi-role workload | Paired cash acceptance/start/completion/settlement/receipt/earning checks now implemented for zero, flat driver-funded and percentage passenger-funded fees; independent supply timing, decline/expiry, transfer/refund, scheduled/fixed-route, case/analytics and hosted measurements remain required |
| LOAD-08 | T5 soak and faults | Eight workers, cross-replica transport, pool exhaustion, DB/provider failover, backups/restores, graph/data versions and emergency pause; accepted RPO/RTO/SLO evidence required |
| LOAD-09 | T6 staff rehearsal | Staff observe synthetic journeys, distinguish delay from failure, reconcile records, act on alerts and stop/recover using named ownership; no real transport or money |
| LOAD-10 | T7 closed field cohort | Stop automated synthetic load against the cohort; consented drivers/passengers execute the approved physical/device matrix with staffed response |
| LOAD-11 | T8–T9 real users | All applicable P0 gates closed, approved city thresholds, progressive exposure and rollback/pause owner; observe real service without manufacturing production demand |
| LOAD-12 | T10 expansion | Recalibrate by city geography/supply and national concurrency; do not extrapolate a local two-user pass to country-wide capacity |

Attach each promoted result to immutable commit/image, migration head, target
topology, test owner/time window, synthetic fixture/configuration versions, rate
limits, worker/provider settings, workload parameters, infrastructure metrics,
reconciliation results and defects. Keep sensitive environment inventories in
the controlled evidence store, not in the aggregate workload JSON. Source-local
success is not clean-commit CI, hosted capacity, field approval or launch approval.
