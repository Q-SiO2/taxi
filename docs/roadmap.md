# TaxiMobile — Roadmap

## Purpose

Define the intended development order and prevent the coding agent from implementing future features prematurely.

The roadmap is directional rather than a rigid schedule.

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
* Initial electronic payment integration when appropriate
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

---

# Phase 10 — Driver Experience

Improve:

* Ride offer interface
* Driver navigation
* Earnings information
* Ride history
* Availability controls
* Driver notifications

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

# Future Features

These are explicitly not MVP requirements:

* Scheduled rides
* Taxi-stand queues
* Advanced dispatch zones
* Cooperative governance features
* Advanced fraud detection
* Demand forecasting
* Institutional/corporate accounts
* Multiple cities
* Multiple countries
* Advanced payment providers
* Physical taxi-meter integration
* Advanced analytics

Future features should not be implemented merely because the architecture can support them.

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
```

## Current implementation gates

The repository has delivered the provider-independent MVP foundation: secure
accounts and sessions, driver eligibility and vehicles, authoritative rides and
versioned fairness-aware matching with sequential decline/expiry handling,
seeded aggregate-only matching simulation,
fixed-tariff fares, cash settlement, receipts, ratings, support,
notification history, shared passenger/driver applications, migrations, local
Compose infrastructure, shared production abuse limits, and CI build/test coverage. The CI backend gate now
includes a migrated PostGIS end-to-end cash ride from registration through
settlement and earnings. This statement is not a
release certification; every deployment still needs the gates below.

CI independently validates the committed Gradle wrapper JAR against Gradle's
trusted checksums, while the wrapper pins the Gradle distribution itself by
SHA-256. This protects the build entry point without pretending that dependency
updates are safe to deploy without review.
The backend CI and portable backend test entry points also run a source credential
hygiene gate. CI scans Git-tracked files and rejects provider configuration,
signing containers, private keys, service-account documents, and high-confidence
live token formats without echoing credential values; local ignored environment
files and generated runtime directories are not read by the no-Git fallback.
Those same entry points extract the actual handwritten Kotlin Ktor operations and
compare every method/path with FastAPI OpenAPI, plus the registered live-event
WebSocket. Unknown call structures and unreviewed dynamic route segments fail
closed, preventing a newly added gateway from silently escaping route-drift
coverage. Payload schemas and authorization behavior remain focused-test gates.

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
Valhalla service by default for routing and turn-by-turn instructions, CMI for
electronic card payments, and Firebase Cloud Messaging (FCM) for background push.
The approved GraphHopper replacement is implemented behind the same route contract,
and cash remains a first-class payment method. These selections do not remove the
operational proof required before release:

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
| Electronic payments | CMI hosted card payment and cash are selected. Obtain CMI's merchant integration kit, sandbox credentials, signed-callback specification, settlement reports, and operational dispute/reconciliation rules. | Sandboxed CMI integration, authenticated callback tests, reconciliation evidence, and payment failure/retry tests. |
| Refunds and fare adjustments | Define the cooperative authority, reason taxonomy, accounting treatment, and passenger communication policy. | Immutable adjustment/refund records, authorization/audit tests, and reconciliation evidence. |
| Background push and multi-instance delivery | The PostgreSQL cross-instance hint transport, FID-based Android/iOS registration, authorized FCM HTTP v1 `fid` targeting with legacy-token migration support, invalid-registration revocation, bounded retry, persistent dead-letter state, reviewed replay procedure, and allowlisted Android/iOS receive-to-authoritative-refresh path are implemented. Create separate development/staging/production Firebase projects, configure Android and APNs credentials, and define credential rotation. | Existing transport/adapter/ownership/revocation/receive tests plus migrated PostGIS fanout and Android/iOS device validation with environment credentials. |
| Safety/support triage | Define responsible roles, escalation paths, retention, privacy, and response-time policy. | Restricted workflow, audit/authorization tests, and an operational runbook. |

The integration gate remains required even for provider-independent work. CI is
configured to apply the migration chain against isolated PostGIS, render offline
SQL, run tests, and build the backend image; that workflow must pass. A release
environment must additionally run the migration and readiness checks against its
own documented database. The checksum-pinned workspace-local Windows
PostgreSQL/PostGIS runtime has applied every migration and passed the full backend
suite, including the complete registration-to-cash-settlement lifecycle. This is
live local database evidence, not release certification. The selected Valhalla or
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

The administrative security workflow now supports audited account-wide session
revocation, suspension, and suspension recovery. Suspension atomically revokes
server sessions and push registrations, blocks existing access tokens, refresh,
and login, and never restores old credentials on reactivation. Administrative
self-suspension and restoration of deactivated accounts are refused. Broader
role management and support/safety escalation remain separate policy-gated work.
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

The workspace-contained database path also completed a guarded backup/restore
drill. The restored database matched migration head, PostGIS version, and selected
aggregate counts and accepted the application role plus a no-op migration to
head. The reusable verifier now covers users, rides, payments, driver credentials,
cooperatives, and memberships at head `20260813_0029`. This validates the
repository scripts locally; encrypted managed-provider
backup retention and a staging restore remain release gates.

The repository also contains a hardened provider-neutral production Compose
template, guarded non-secret input validation, an explicit one-shot migration
service, non-mutating deployment verification, and forward-only rollback guidance.
It runs the public API and the matching/outbox/credential processor supervisor as
separate closed process roles from the same immutable image. API and worker have
independent loopback operations surfaces; deployment verification requires API
identity/readiness and positive heartbeats from all three worker loops. PostgreSQL
fans minimized hints across horizontally scaled API replicas. A real registry, TLS proxy, managed PostGIS restore drill, secret store,
monitoring collector, and staging/production rollout remain deployment evidence,
not facts that source files alone can prove.

Both long-running production containers now report Compose health from their
readiness boundary. The API requires PostgreSQL; the worker also requires its
supervisor and one successful iteration from matching, outbox, and credential
lifecycle. CI rejects replacement with liveness-only probes and also checks the
manifest's loopback ingress, process roles, least-privilege environments, and
container hardening before Docker Compose rendering.

The public API and private worker operations surface also apply a shared pure-ASGI
response-security boundary: responses are non-cacheable and carry MIME,
referrer, and frame protections, with HSTS limited to production HTTPS. Optional
browser CORS is exact-HTTPS-origin only and permits the documented `DELETE` and
`Idempotency-Key` contract without allowing arbitrary origins.
