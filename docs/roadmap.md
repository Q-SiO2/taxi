# TaxiMobile — Roadmap

## Purpose

Define the intended development order and prevent the coding agent from implementing future features prematurely.

The roadmap is directional rather than a rigid schedule.

Use [workflow.md](workflow.md) to execute a scoped task and promote evidence
through the existing test phases. [readiness.md](readiness.md) measures weighted
engineering implementation separately from deployment gate closure; phase counts
must not be used as a completion percentage.

## Current standing — 2026-09-09

This roadmap distinguishes repository delivery from real-world acceptance.
Phases 1–10 and 12–19 are **implemented in source**. Phase 11 has substantial
source hardening, but its production outcome cannot be complete until a real
environment and city pilot satisfy the open evidence in [`gaps.md`](gaps.md).

| Phase | Repository standing | Deployment standing |
| --- | --- | --- |
| 1–7 Foundation through payments | Implemented and locally exercised through end-to-end PostGIS lifecycles. | Real accounts, recipient/cash controls, hosted environment, and operational ownership open. |
| 8 Maps and navigation | MapLibre, normalized place search/reverse lookup, and Valhalla/GraphHopper contracts implemented. | Production tiles/style, routing graph, geocoding provider/data/license and multilingual quality acceptance, narration, and device navigation open. |
| 9–10 Passenger and driver experience | Shared role-specific product surfaces, foreground-only online driver-location heartbeat, and closed-code assigned-ride coordination implemented. | User research, accessibility, signed-device, battery/dispatch location acceptance, coordination delivery/usability, privacy/store review, and physical-device acceptance open. |
| 11 Production hardening | CI, rate limits, secure release guards, six-surface client compatibility enforcement and preflight UI, monitoring endpoints, backup scripts, Compose blueprint, and failure recovery implemented in source. | Approved support/deprecation policy, signed old/current client drill, security review, capacity, HA, managed backups, alerting/on-call, incident drills, and production promotion open. |
| 12–19 National control plane through payment operations | Migrations, APIs, web/mobile surfaces, and focused integration coverage implemented in source. | No city bundle has real legal/provider/operational evidence or measured pilot outcomes. |

No phase status authorizes a public launch. The prioritized release blockers and
acceptance criteria live in [`gaps.md`](gaps.md).

---

# Phase 1 — Foundation

Goal: establish a working project architecture.

```text
Project structure
Shared Kotlin code
Android application
iOS application
Backend
Database
Authentication
API foundation
```

At the end of this phase, the applications should be able to communicate with the backend.

---

# Phase 2 — Accounts

Implement:

* Passenger registration
* Passenger login
* Driver registration
* Driver login
* Authentication
* Basic profiles
* Roles and permissions

---

# Phase 3 — Driver System

Implement:

* Driver profile
* Vehicle information
* Driver verification status
* Online/offline state
* Driver location
* Driver availability

---

# Phase 4 — Basic Rides

Implement:

* Pickup selection
* Destination selection
* Ride creation
* Ride states
* Driver assignment
* Driver acceptance
* Ride cancellation
* Ride completion

---

# Phase 5 — Matching

Implement the initial matching system defined in `matching.md`.

Start with a simple, deterministic implementation.

Do not prematurely implement sophisticated machine-learning-based dispatch.

---

# Phase 6 — Pricing

Implement:

* Tariff configuration
* Fare estimation
* Fare calculation
* Fare breakdown
* Final fare
* Adjustments

Follow `pricing.md`.

---

# Phase 7 — Payments

Implement:

* Cash payment recording
* Payment states
* Payment abstraction
* External bank/M-Wallet transfer with backend reference and manual
  reconciliation
* Refund/adjustment support

---

# Phase 8 — Maps and Navigation

Implement:

* Map display
* Location selection
* Driver location
* Route display
* Pickup navigation
* Destination navigation

The specific map provider should remain replaceable.

---

# Phase 9 — Passenger Experience

Improve:

* Ride tracking
* Driver information
* Notifications
* Ride history
* Receipts
* Ratings
* Basic support/dispute flows
* Ride-bound safety reporting distinct from support
* Participant-safe case acknowledgements and status history
* Closed-code coordination with the assigned driver during active ride states

---

# Phase 10 — Driver Experience

Improve:

* Ride offer interface
* Driver navigation
* Earnings information
* Ride history
* Availability controls
* Driver notifications
* Closed-code coordination with the assigned passenger during active ride states

---

# Phase 11 — Production Hardening

Before public deployment:

* Security review
* Performance testing
* Crash/error monitoring
* Database backups
* API rate limiting
* Abuse protection
* Payment testing
* Offline/network failure handling
* Automated testing
* Deployment infrastructure

---

# Phase 12 — National Control-Plane Foundation

Goal: introduce city scope without breaking the proven single-city lifecycle.

**Status: foundation and production authentication protocol delivered.**
Migrations `20260824_0033`, `20260824_0034`, and `20260830_0043`, the scoped
operations API, compatibility backfill, Compose web console, encrypted TOTP and
single-use recovery, recent-MFA step-up, secure refresh cookie, CSRF rotation,
and guarded factor replacement are implemented and covered by migrated PostGIS
integration tests. Hosted release still requires the deployed web CSP, named
access/recovery reviewers, enrolled operator accounts, and incident/access-review
evidence; source delivery alone does not authorize privileged production use.

Implement in bounded migrations/slices:

* Market, operator, city, service-area, and city-lifecycle records.
* Versioned coherent city configuration bundles.
* Scoped administrative grants and operations authentication boundary.
* Dedicated operations API namespace.
* `webApp` operations shell with market/operator/city scope presentation.
* Cross-city negative authorization, pagination-count, and audit tests.
* Compatibility migration for existing rides, tariff, cooperative, and bootstrap
  administrator data; no historical rewrite.

Delivered Phase 12 console modules are rollout; city/operator creation;
operator status; exact-scope assignment creation/retirement; service-area
creation/review; compatible coherent-configuration assembly/review/activation;
city lifecycle/readiness; typed-confirmed scoped grant create/revoke and expiry
review; and scoped audit visibility. Independent grant approval and automated
recertification remain deployment work rather than a Phase 12 source claim.
The editor accepts WGS84 point rows instead of raw geometry/configuration JSON,
shows missing authoritative dependencies, and reloads backend state after every
accepted command. Driver recruitment and the public applicant portal are delivered in
Phase 13, pricing policy editors in Phase 14, and published fixed routes in Phase
15. Scheduling and broader analytics remain in their later phases rather than
appearing as non-functional navigation.

Do not activate a second city until every high-volume ride, matching, driver,
pricing, payment, and worker query has an explicit city ownership rule.

---

# Phase 13 — City Driver Recruitment and Review

**Status: application, review, and protected document lifecycle delivered
(2026-08-31).** Migrations `20260824_0035` and `20260831_0045`, public/applicant and scoped operations APIs, the driver-mobile
onboarding flow, separate public web portal, permission-gated review console,
city/service online enforcement, matching eligibility, and suppression-aware
onboarding aggregates are implemented and tested. Protected PDF/JPEG/PNG upload,
replacement, deletion, encrypted private-volume storage, ClamAV scanning,
retention erasure, recent-MFA/no-store reviewer retrieval, access audit, Android
and iOS native selection, and JavaScript portal selection are implemented. The capability still
fails closed when its root, independent encryption key, or private scanner is not
configured. JavaScript and Kotlin/Wasm use bounded browser file APIs, but both
still require browser acceptance testing; no client substitutes a free-text file
reference or claims an upload succeeded.

Implement:

* Public recruiting-city catalog.
* Driver city application draft/edit/evidence/submit/withdraw/status flows from
  mobile and web through one API.
* Versioned city requirement sets and protected document-storage boundary.
* Scoped reviewer queues, decisions, reasons, and audit.
* City authorizations and one-city-at-a-time online enforcement.
* Vehicle/credential/service eligibility per city where policy requires it.
* Onboarding funnel aggregates without document or identity leakage.

---

# Phase 14 — City Pricing and Operator Economics

**Status: city pricing and operator economics delivered (2026-08-27).**
Migration `20260824_0036`, scoped operations APIs and web editors, immutable
ride financial snapshots, exact quote/offer/receipt/earning components, and
passenger/driver presentation are implemented and tested. The scheduling-policy
foundation delivered here is expanded and consumed by the separate Phase 16
scheduled-booking lifecycle.

Implement:

* City/operator/service-scoped tariff versions.
* Draft, review, activation, replacement, and rollback-compatible history.
* Operator service fee modes: percentage of documented transport fare or flat
  per completed booking.
* Funding mode: transparent driver settlement deduction or passenger surcharge.
* Explicit zero-fee policy.
* Scheduling surcharge policy foundation.
* Quote, offer, receipt, earning, operator-allocation, and reconciliation
  components with exact-money tests.

No city rate can go live without an audited complete policy and no mobile/web
client calculates a fee.

---

# Phase 15 — Published Fixed Routes

**Status: published fixed routes delivered (2026-08-29).** Migration
`20260827_0037`, direction-scoped flat fares, scoped operations lifecycle APIs
and editor, public supply-private catalog, passenger immediate booking, and
driver fixed-route authorization/offers/history are implemented. Clean
migration upgrade, Phase 15 downgrade/re-upgrade, same-city multi-fare PostGIS
integration, shared/mobile UI tests, and operations-web contract compilation are
the delivery evidence. Phase 16 now consumes published directions for scheduled
fixed-route bookings without changing the supply-private catalog.

Implement:

* City route/version/direction/stop/geometry model.
* Separate outbound/inbound direction publication.
* One flat complete-direction fare in the first release.
* Public route catalog visible independently of live supply.
* Passenger direction detail and immediate fixed-route request.
* Driver fixed-route eligibility, informed offers, and normal accept/decline.
* Operations route editor, review, publication, retirement, and audit.
* Explicit proof that no catalog/API exposes online drivers or counts.

Segment fares, seat pooling, and intercity route regulation remain out of scope.

---

# Phase 16 — Scheduled Bookings

**Status: scheduled bookings delivered (2026-08-29).** Migration
`20260829_0038`, non-mutating review estimates with version-checked confirmation,
immutable booking economics/policy snapshots, passenger cancellation, city-scoped
driver opt-in/offers/commitments, overlap protection, lease-safe opening/handoff,
eligibility revalidation, normal-matching fallback, explicit unfulfilled state,
scoped operations exception inspection, localized mobile surfaces, demo data,
and focused PostGIS lifecycle tests are implemented. Recurring bookings remain
out of scope.

Implement:

* Separate scheduled-booking lifecycle and immutable quote/policy snapshots.
* City lead time, horizon, offer, commitment, handoff, conflict, cancellation,
  surcharge, and refund policies.
* Passenger schedule/review/upcoming/cancel states with honest guarantee copy.
* Driver scheduled offers and upcoming commitments with non-punitive decline.
* City-scoped scheduled-offer opt-in independent of immediate online status.
* Transaction-safe overlap checks and one live ride per handoff.
* Revalidation/fallback matching and explicit unfulfilled outcome.
* Immediate and fixed-route scheduling only where the city enables them.

Recurring bookings are not part of this phase.

---

# Phase 17 — Operations Data and Rollout Intelligence

**Status: delivered in the repository on 2026-08-29.** Migration
`20260829_0039`, the analytics refresh worker, scoped aggregate-only API, and
operations-web rollout-intelligence module implement this phase. Production
acceptance still requires the Phase 18 pilot evidence and monitoring review.

Implement:

* Typed operational domain events with approved city/operator/service/policy
  dimensions.
* Aggregate demand, supply, fulfillment, fixed-route, scheduling, onboarding,
  financial, and fairness facts.
* Coarse geographic/time buckets and small-cell suppression.
* Scoped aggregate-only analyst APIs and operations dashboards.
* Metric definitions, retention, late-event behavior, data-quality tests, and
  reconciliation to source-of-truth records.
* No arbitrary analytics payload, participant trail, document, support text,
  or payment credential collection.

PostgreSQL aggregate views/fact tables come first. A warehouse or stream system
requires measured need.

---

# Phase 18 — Repeatable City Pilot and National Expansion

**Status: delivered in the repository on 2026-08-29.** The obsolete Phase 12
second-city block has been replaced by backend-authoritative staged readiness,
audited operations-web evidence controls, public-activation protection, safe
configuration replacement rules, emergency pause/resume, post-launch closeout,
and a migrated two-city integration proof. Real legal approval, provider
coverage, driver recruitment, pilot observations, and production monitoring
remain deployment evidence for each city; repository tests cannot fabricate
those decisions.

For each city:

1. Complete legal/operational review and assign accountable operator/staff.
2. Configure service area, requirements, tariffs/fees, matching, payments,
   fixed routes, scheduling, localization, support, safety, and retention.
3. Run synthetic and isolated pilot data; verify maps/routing/provider coverage.
4. Recruit/review a bounded driver cohort.
5. Enter `PILOT`, measure agreed service and fairness gates, and resolve issues.
6. Activate publicly only through the audited readiness bundle.
7. Monitor, preserve an emergency city-pause path, and conduct a post-launch
   review before starting the next city.

The ten configuration and operations gates are required before `PILOT`.
For initial launch, `PILOT_SERVICE_AND_FAIRNESS` can pass only on the active
bundle while the city is actually in `PILOT`, and is additionally required
before `ACTIVE`. An approved replacement in an already `ACTIVE` or `PAUSED` city
requires a new decision and evidence that the measured outcome remains
representative under the proposed bundle; evidence is never copied.
`POST_LAUNCH_REVIEW` is a separately visible closeout decision that can pass
only after the city has reached `ACTIVE`; it cannot be falsely used as a
pre-launch gate. An operating city's replacement configuration must independently
pass the readiness stage appropriate to the city's current lifecycle before it
can become active.

There is one application and schema, not a fork per city.

---

# Phase 19 — Versioned Payment Operations

**Status: delivered in the repository on 2026-08-31.** Migration
`20260831_0044`, scoped backend APIs, the protected operations payment module,
and clean migrated integration tests implement this phase. Production acceptance
still requires a verified real recipient, controlled external transfer,
statement reconciliation, named duty ownership, MFA enrollment/recovery, and
city-specific legal and commercial approval.

Delivered behavior:

* Immutable-after-verification recipient accounts scoped to city and operator.
* Versioned cash/manual-transfer capabilities scoped to city, operator, and
  service type with review, approval, activation, and replacement history.
* Exact capability linkage in coherent city-configuration services; non-legacy
  activation, estimates, and ride creation fail closed without it.
* Immutable ride/payment capability and recipient provenance plus non-null
  city/operator provenance on payments and refunds.
* Separate configuration and reconciliation permissions, grant-constrained SQL
  pagination, idempotent transfer decisions/refunds, recent-MFA controls, and
  append-oriented audit evidence.
* A protected web console for recipient/capability lifecycle, transfer queue,
  and refund ledger without exposing financial credentials to mobile clients.
* A legacy-city-only environment fallback; no new city/operator may use
  deployment-wide recipient configuration.

CMI/card processing remains deferred. Cash remains mandatory and a controlled
external bank/M-Wallet transfer remains the only current electronic method.

---

# Future Features

These are explicitly not MVP requirements:

* Taxi-stand queues
* Advanced dispatch zones
* Cooperative governance features
* Advanced fraud detection
* Demand forecasting
* Institutional/corporate accounts
* Multiple countries
* Advanced payment providers
* Physical taxi-meter integration
* Advanced analytics
* Recurring scheduled bookings
* Fixed-route segment pricing and pooled-seat inventory
* Multi-operator revenue sharing on one ride
* Intercity regulatory workflows

Future features should not be implemented merely because the architecture can support them.

Multiple Moroccan cities, the operations web platform, city driver applications,
fixed-route catalogs, single scheduled bookings, transparent percentage-or-flat
operator fees, and privacy-bounded rollout aggregates are approved expansion
phases above. They remain post-hardening scope and are not claims about current
implementation.

---

# Development Rule

At any point, prioritize:

```text
Working core functionality
        ↓
Correctness
        ↓
Security
        ↓
Testing
        ↓
Performance
        ↓
Additional features
```

Do not sacrifice the core ride system to build optional features.

## Required implementation sequence

Each phase is complete only when its documented behavior, migrations, focused tests, and API contract are present. A later phase must not be started merely because it is technically possible: it depends on the earlier source of truth being stable. The concrete repository and deployment work for each phase is defined in `implementation.md`.

The implementation sequence is:

```text
foundation → accounts → drivers → rides → matching → pricing → payments
          → maps → passenger experience → driver experience → hardening
          → national control plane → city recruitment → city economics
          → fixed routes → scheduling → rollout data → repeatable city pilots
          → versioned payment operations
```

## Current implementation gates

The repository has delivered the provider-independent MVP foundation: secure
accounts and sessions, driver eligibility and vehicles, authoritative rides and
versioned fairness-aware matching with sequential decline/expiry handling,
seeded aggregate-only matching simulation,
fixed-tariff fares, cash/manual-transfer settlement, append-only operator-funded
refunds, receipts, ratings, support,
notification history, shared passenger/driver applications, migrations, local
Compose infrastructure, shared production abuse limits, and CI build/test coverage. The CI backend gate now
includes a migrated PostGIS end-to-end cash ride from registration through
settlement and earnings. This statement is not a
release certification; every deployment still needs the gates below.

CI independently validates the committed Gradle wrapper JAR against Gradle's
trusted checksums, while the wrapper pins the Gradle distribution itself by
SHA-256. This protects the build entry point without pretending that dependency
updates are safe to deploy without review.
Pull requests now reject newly introduced high/critical dependency findings, and
trusted pushes submit the Gradle action's resolved dependency graph rather than a
hand-maintained catalog. The backend build emits an SPDX JSON SBOM from the built
image, records its digest in source-candidate evidence, and blocks on high or
critical OS/library findings. All actions use immutable commit SHAs and a local
validator protects the blocking/provenance settings. These controls need a clean
remote candidate run and do not yet cover every mobile/web artifact or replace
independent security review.
The backend CI and portable backend test entry points also run a source credential
hygiene gate. CI scans Git-tracked files and rejects provider configuration,
signing containers, private keys, service-account documents, and high-confidence
live token formats without echoing credential values; local ignored environment
files and generated runtime directories are not read by the no-Git fallback.
Those same entry points extract the actual handwritten mobile and operations-web
Ktor operations and compare every method/path with FastAPI OpenAPI, plus the
registered mobile live-event WebSocket. Unknown call structures, arbitrary route
variables, unreviewed dynamic segments, and operations calls outside the single
exactly-once `/api/v1` builder fail closed, preventing a new gateway from silently
escaping route-drift coverage. Payload schemas and authorization behavior remain
focused-test gates.

Android CI also compiles both minified release flavors with fatal lint and checks
that the resulting passenger and driver APKs have distinct expected application
IDs and explicit version metadata. Real promotion remains gated on protected
signing material, environment-specific Firebase files, production HTTPS API/map
configuration, secure retention of R8 mappings, and physical-device acceptance;
the CI artifacts are intentionally unsigned and non-distributable.

Physical Android account acceptance now has a guarded repeatable runner that
requires backend/database readiness, one authorized device, ADB reverse, and an
explicit confirmation before clearing only the selected debug app. It submits
the real localized registration form with synthetic local credentials, logs in,
and waits for the backend-authorized product-role gate without persisting a UI
dump or printing credentials. Its parser and safety contract run in CI; execution
on the supported device matrix remains release evidence rather than a source-only
claim.

iOS CI applies an equivalent Release compiler gate to both schemes: explicit
HTTPS configuration and numeric versions are always validated, while narrowly
named switches allow only unsigned/providerless simulator verification. Public
archives still require target-matching ignored Firebase plists, production APNs
entitlements, Apple signing/team configuration, and physical-device acceptance.

The cooperative has selected MapLibre for mobile map rendering, a self-hosted
Valhalla service by default for routing and turn-by-turn instructions, external
bank/M-Wallet transfer as the launch electronic-payment path, and Firebase Cloud
Messaging (FCM) for background push. The approved GraphHopper replacement is
implemented behind the same route contract, and cash remains a first-class
payment method. CMI/card processing is explicitly deferred until well after the
functional launch flow. These selections do not remove the operational proof
required before release:

The mobile presentation layer now includes exact-parity English, French, and
Arabic catalogs, Arabic RTL layout, localized known notification events, and
debug-only editable raw passenger coordinates. Route requests carry a closed
language value; the Valhalla adapter supplies French or English narration. The
pinned Valhalla catalog lacks Arabic narration, so Arabic spoken guidance remains
part of the route-provider acceptance gate instead of silently falling back as a
completed localized feature.

| Requirement | Gate before implementation | Required proof |
| --- | --- | --- |
| Map display, place selection, routes, and navigation | MapLibre rendering, normalized Valhalla and GraphHopper adapters, a closed deployment selector, one-shot foreground mobile permission flows, privacy-bounded post-assignment last-known driver visibility, and an opt-in pinned local Valhalla Morocco graph build are implemented. Select one production engine, a MapLibre style/tile source, and approve routing-data refresh, retention, attribution, and artifact-promotion policy. Geocoding and continuous background tracking remain separate optional adapters/capabilities. | Existing provider normalization/configuration and assigned-location authorization/lifecycle tests plus a successful pinned Morocco graph build for the selected engine, tile/style acceptance, narration acceptance in required languages, and Android/iOS device tests. |
| Electronic payments | Cash plus the provider-independent manual bank/M-Wallet transfer claim, verified recipient accounts, versioned city/operator/service capabilities, exact active-bundle linkage, immutable settlement provenance, scoped reconciliation, and protected operations UI are implemented. The deployment-wide recipient is now a legacy-city-only compatibility fallback. Before enabling a pilot, verify the real recipient, transfer limits/fees, statement reference fidelity, scoped reviewers, support ownership, reconciliation cadence, MFA recovery, and cash fallback. CMI/card remains deferred. | Existing unit/API/web/mobile tests and clean migrated payment/national lifecycle tests plus a controlled external transfer located by exact reference/amount/currency, idempotent verify/reject evidence, earning reconciliation, operator runbook exercise, and unresolved-claim alert/ownership proof. |
| Refunds and fare adjustments | Append-only confirmed refunds are implemented for completed payments with a closed reason taxonomy, cash/external-transfer evidence, payment locking, cumulative over-refund protection, idempotent audited administrator commands, passenger-safe receipt totals, and an explicit launch allocation of zero driver recovery/full operator funding. Before pilot use, assign approval/reconciliation staff and exercise the controlled case, cash-handover/outbound-statement, and passenger-communication runbook. Post-ride increases and driver recovery remain prohibited until a later versioned policy exists. | Existing service/schema/OpenAPI/mobile and migrated two-party lifecycle tests plus a controlled real refund reconciled by exact payment/amount/currency/evidence reference, duplicate/over-refund rejection evidence, daily refund-list/audit reconciliation, and operator ownership proof. |
| Background push and multi-instance delivery | The PostgreSQL cross-instance hint transport, FID-based Android/iOS registration, authorized FCM HTTP v1 `fid` targeting with legacy-token migration support, invalid-registration revocation, bounded retry, persistent dead-letter state, reviewed replay procedure, and allowlisted Android/iOS receive-to-authoritative-refresh path are implemented. FCM and Crashlytics are no-cost Spark-plan products; do not add metered Firebase databases, functions, storage, hosting, phone auth, or Analytics. Create separate development/staging/production Firebase projects, configure Android and APNs credentials, and define credential rotation. | Existing transport/adapter/ownership/revocation/receive tests plus migrated PostGIS fanout and Android/iOS device validation with environment credentials. |
| Passenger-driver coordination | Six role-specific closed signals, active-assignment authorization, required idempotency, rate/cap controls, durable recipient notification, generic live/push refresh, latest-message ride detail, and shared localized UI are implemented. Free text, direct phone exposure, and calling are intentionally absent. Approve retention/erasure, support/abuse handling, emergency limitations, and whether this minimal channel meets launch needs. | Existing policy/API/outbox/mobile and fresh-PostGIS lifecycle tests plus physical-device delivery, accessibility/localization, weak-network/provider-failure traces, staff rehearsal, closed-road pickup metrics, and signed pilot thresholds. |
| Safety/support triage | Separate participant support and safety records, immutable city scope, controlled lifecycles, city-scoped operations queues and mutations, active scoped assignee checks, append-only notes, minimal support-to-safety handoff, durable overdue paging, pager acknowledgement, fixed-field audit, mobile/operations status surfaces, response targets, versioned retention projections, city-scoped legal holds, and verified personal-data minimization are implemented. The operations console exposes hold/release controls and immutable erasure evidence. Before a live pilot, name the duty and legal-review rosters, enroll MFA factors, exercise recovery and the case runbook, prove real pager routing, and approve backup-expiry/restore policy. | Focused service/schema/OpenAPI/web/mobile tests and expanded lifecycle/national-control-plane/MFA integrations pass against migrated PostGIS at `20260831_0044`, including secure-cookie/CSRF rotation, held support data, released-hold processing, safety-case minimization, and payment provenance. Deployment evidence still requires a controlled support acknowledgement, urgent safety page/drill, escalation, legal-hold review, factor-recovery drill, audit-redaction review, backup-expiry/restore exercise, and shift handoff without exposing internal text. |

The integration gate remains required even for provider-independent work. CI is
configured to apply the migration chain against isolated PostGIS, render offline
SQL, run tests, and build the backend image; that workflow must pass. A release
environment must additionally run the migration and readiness checks against its
own documented database. The checksum-pinned workspace-local Windows
PostgreSQL/PostGIS test runtime has applied through migration `20260908_0052`; the
backend suites include complete registration-to-payment/refund, support/safety,
legal-hold, and case-retention lifecycles. This is local evidence, not release
certification.
The selected Valhalla or
GraphHopper deployment still requires a separate routing-data build and route
acceptance gate; generated migration SQL and mocked provider tests do not replace
that proof. The repository now supplies a guarded fixed-scenario acceptance
command that checks three Morocco routes, geometry and maneuver integrity, route
plausibility, and English/French/Arabic narration through the selected real
adapter without logging route data. It requires exact confirmation for non-local
hosts and intentionally fails the pinned Valhalla catalog's English fallback for
Arabic. Mutually exclusive local Compose profiles now provision either pinned
Valhalla 3.8.3 or a non-root GraphHopper image built from the checksum-verified
official 11.0 JAR. GraphHopper verifies a dated Morocco extract by SHA-256 and
names its graph cache by that digest before the guarded launcher can run full
acceptance. An actual successful graph/catalog run and mobile navigation matrix
remain deployment evidence.

Production-hardening tooling now includes a bounded asynchronous GET-only
performance smoke command with p95 and error-rate budgets. Its localhost run is a
harness check, not capacity evidence; release still requires agreed workload and
latency targets exercised against isolated staging with production-like PostGIS,
routing data, and provider configuration.

Offline/network failure handling now includes native Android and iOS connectivity
observers, a tested shared unavailable-to-available transition policy, retention
of the last authenticated backend-confirmed screen under a localized sticky
warning, and exactly one authoritative restore after reconnect. Initial failures
without usable state retain the dedicated retry screen. Connectivity is never
treated as command acknowledgement, and failed ride, driver availability, cash,
or electronic-payment commands are not replayed automatically. Every authenticated
Android/iOS action now crosses a tested shared boundary that executes it once and,
on an uncertain/rejected result, performs one read-only authoritative restore
while retaining the original operation error. Both roots now synchronously gate
authenticated UI actions before coroutine launch; exact initiating controls show
loading, competing backend actions are disabled, and tested `finally` release
prevents a failure from wedging the UI. Android and shared
host compilation cover the implementation on Windows; macOS CI and physical
Android/iOS network-loss testing remain release evidence.
The same source gate now covers foreground recovery: only a real
background-to-foreground transition with an authenticated session restores state;
initial/repeated lifecycle callbacks do not duplicate startup and never replay a
failed command.
The mobile source gate also locks one-shot location admission: Android and iOS
ignore repeated current-location taps without cancelling the first callback, and
shared Compose exposes disabled/loading semantics until the platform result.
Driver offer timing now fails closed for malformed/non-positive server envelopes:
Accept is disabled and one authoritative refresh is requested instead of using
device wall time or presenting the offer as safely actionable.
Backend-confirmed action feedback now uses a sequenced common event: cash and
rating render the specified 320 ms success check, while confirmed support and
vehicle creation reset their drafts. Error and uncertain outcomes emit no success
and retain editable input.
Account creation feedback follows the same authority boundary: confirmed
registration is a polite success announcement with identifier prefill and password
clearing, while rejected registration remains an assertive error and retains the
editable account form.

Mobile crash/error monitoring now uses Firebase Crashlytics in the same separated
Firebase environments already required for FCM, without Firebase Analytics.
Debug and providerless verification collection is disabled; distributable
releases require an explicit collection switch and matching Android R8/iOS dSYM
upload wiring. A portable source gate rejects identity/custom-business telemetry
and missing role integration. Release remains gated on approved processor,
retention, access, incident-response, and privacy policy plus controlled,
symbolicated staging crashes for passenger and driver on both platforms.

Authenticated monitoring now includes privacy-bounded aggregate outbox gauges
for pending, dead-lettered, and locked events, oldest pending age, and snapshot
availability. Database failures omit potentially misleading count values while
leaving process telemetry scrapeable. The deployment verifier requires the
outbox snapshot, and the migrated PostGIS suite exercises the aggregate query;
production alert routing and response ownership remain deployment-policy gates.
Matching and outbox loops also expose fixed-name iteration, processed-item, and
last-success telemetry. Bounded JSON failure logs omit exception messages, and
the committed alert set detects retries, five-minute worker stalls, and a missing
standalone worker scrape target.

The same authenticated surface now exposes a five-second-bounded security-
incident deadline snapshot using only fixed SEV1-SEV4 buckets. Reviewed rules
alert on snapshot loss, open SEV1/SEV2 incidents, severity-split containment
breaches and overdue postmortems; immutable dashboard panels show open and
deadline state without incident or scope identifiers. Real receiver delivery,
acknowledgement, escalation timing and staffed drills remain release gates.

Security incidents now also have four closed responsibility types with one
active exact-market-authorized assignee per type and append-visible reassignment
history. The protected web workspace can review and assign those roles using an
approved roster/shift reference. This is source coordination, not a production
duty roster: T5 must prove alert delivery, T6 must prove named role handoff and
containment/communications/postmortem ownership, and no real-user phase may start
without both accepted.

The administrative security workflow now supports audited account-wide session
revocation, suspension, and suspension recovery. Suspension atomically revokes
server sessions and push registrations, blocks existing access tokens, refresh,
and login, and never restores old credentials on reactivation. Administrative
self-suspension and restoration of deactivated accounts are refused. Broader
scoped role management remains policy-gated. Support/safety reads, mutations,
assignee validation, and overdue alerts now enforce active city-scoped grants;
the old `/admin` family remains compatibility-only.
Administrators can now review the resulting append-oriented audit trail through
a bounded, exact-filtered read endpoint; ordinary users have no audit-log access
and the API exposes no audit mutation path.

Login hardening now removes the dominant missing-account timing shortcut by
performing one Argon2 verification for active, suspended, and absent identifiers.
Successful authentication opportunistically upgrades older valid Argon2
parameters. Access JWTs are closed to TaxiMobile's issuer, mobile audience,
access type, and complete identity/lifecycle claims before the existing
server-side session and account-status checks run.

The request-audit path now avoids framework response buffering and duplicate raw
Uvicorn access events. Direct ASGI performance at concurrency 20 and Windows
loopback performance at concurrency 10 pass the repository's 500 ms p95 budget
with no errors. Twenty-connection Windows loopback measurements remain above
budget even though direct application measurements pass; staging on the Linux
release image must establish the real concurrency and latency envelope before
release rather than weakening the budget to fit one development host.

The workspace-contained database path previously completed a guarded
backup/restore drill at migration `20260813_0029`. The restored database matched
that head, PostGIS version, and selected aggregate counts and accepted the
application role plus a no-op migration. The reusable verifier covers users,
rides, payments, driver credentials, cooperatives, and memberships, but the
current migration head is `20260908_0052`. A current-head production-like restore,
encrypted managed-provider backup retention, and a staging restore therefore
remain release gates.

The repository also contains a hardened provider-neutral production Compose
template, guarded non-secret input validation, an explicit one-shot migration
service, non-mutating deployment verification, and forward-only rollback guidance.
It runs the public API and the matching/outbox/credential/scheduling/analytics/case-alert/case-retention/driver-document-retention processor supervisor as
separate closed process roles from the same immutable image. API and worker have
independent loopback operations surfaces; deployment verification requires API
identity/readiness and positive heartbeats from all eight fixed worker loops. PostgreSQL
fans minimized hints across horizontally scaled API replicas. A real registry, TLS proxy, managed PostGIS restore drill, secret store,
monitoring collector, and staging/production rollout remain deployment evidence,
not facts that source files alone can prove.

Both long-running production containers now report Compose health from their
readiness boundary. The API requires PostgreSQL; the worker also requires its
supervisor and one successful iteration from matching, outbox, credential,
scheduling, analytics, case alerts, case retention, and driver-document retention. CI rejects replacement with liveness-only probes and also checks the
manifest's loopback ingress, process roles, least-privilege environments, and
container hardening before Docker Compose rendering.

The public API and private worker operations surface also apply a shared pure-ASGI
response-security boundary: responses are non-cacheable and carry MIME,
referrer, and frame protections, with HSTS limited to production HTTPS. Optional
browser CORS is exact-HTTPS-origin only and permits the documented `DELETE` and
`Idempotency-Key` contract without allowing arbitrary origins.
