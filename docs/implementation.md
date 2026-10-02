# Implementation Blueprint

For task sequencing and executable verification, use [workflow.md](workflow.md).
For the dated requirement comparison and weighted source-completion estimate,
use [readiness.md](readiness.md). The detailed implementation contract below
remains subordinate to the owning domain rules.

This document fixes the implementation choices required to turn the TaxiMobile product documents into working software. It is subordinate to the domain rules in `product.md`, `operations.md`, `auth.md`, `rides.md`, `matching.md`, `pricing.md`, and `payments.md`. If a technical choice conflicts with one of those rules, the domain rule wins and the conflict must be resolved in documentation first.

## Current implementation standing — 2026-10-02

**Android packaged-artifact follow-up (2026-10-02):** the release verifier no
longer accepts AGP metadata as proof of the actual APK identity. A modular
standard-library Python checker uses installed SDK `aapt2` to inspect the binary
manifest in both role APKs and match package/version to the candidate and metadata.
It requires one non-split output, rejects traversal/absolute/stream references,
linked/junction output paths, malformed or duplicate metadata and duplicate role
bytes, and checks hashes before/after tool inspection. Tool failures are explicit
and redacted; report creation is exclusive. The existing PowerShell entry point
delegates and propagates failure, and CI mutations preserve its blocking step.
The manifest remains non-distributable with signing/provider/device acceptance
false. This tooling does not create keys, prove APK signatures or alter the apps.
See `release_baseline.md` for the verification boundary.

**Protected image-publication follow-up (2026-10-02):** owner-authorized `main`
protection is configured and read back; seven up-to-date GitHub Actions checks
and independent latest-push approval apply to administrators too. GHCR is the
delegated no-cost backend image store, not a hosting choice. Main-only publication
waits for all push verification jobs and transfers the exact scanned image/SBOM
without rebuilding. `infra/scripts/registry_image_evidence.py` checks same-run
source and file hashes before loading, checks image IDs after loading/pulling,
and retains immutable registry-reference provenance with acceptance false.
PR/feature runs cannot publish. Local Docker was unavailable; local protocol and
CI mutation tests do not prove a real registry push. Review, signing and release
approval remain absent; PR 43 is draft/unmerged and all 19 P0 gates remain open.
See [release_baseline.md](release_baseline.md) for policy and retention details.

**Exact OpenAPI evidence follow-up (2026-10-02):** the actual application factory
now exports separate full launch and local-compatibility schemas through a
bounded configuration-isolated subprocess. The local source export has 223
launch HTTP operations versus 244 compatibility operations; neither count is
an authorization guarantee. Whole-schema hashes cover payloads/components as
well as endpoints. CI retains both canonical schemas, their no-acceptance
manifest and backend clean-source binding; mutation gates preserve generation,
both schema bindings and retention. Existing runtime routes, schema and policies
are unchanged. Local verification passes 15 exporter fixture/worker cases and
three CI OpenAPI mutation cases within 222 infrastructure tests, plus 47 focused
backend factory/system API cases. The three new backend tests also have a
fresh zero-failure/error/skip JUnit run. Actual full-schema files and their
manifest match the hashes in an explicit dirty `WORKSPACE_SNAPSHOT` record;
that record is not an immutable release. No new full migrated-database result
is claimed for this tooling-only patch. The exporter requires its own immutable CI and served-staging
contract/authorization evidence before release promotion. Source candidate
`17a94df` now passes both immutable runs in `release_baseline.md`; its retained
schemas/manifest reconcile with the backend binding. This does not certify the
subsequent registry patch or served-staging authorization.

**Android protected-session follow-up (2026-10-02):** the adapter now writes one
encrypted, versioned token-pair envelope with checked synchronous persistence.
Complete legacy pairs migrate only after validation and a successful commit;
partial/corrupt records remain preserved and produce bounded typed errors.
Reading never creates a replacement Keystore key. IO-dispatched operations share
a preference-facility lock and uncertainty fence across store/Activity recreation,
because a failed Android commit can still change process-cached memory. Only an
explicit successful save or clear recovers that uncertainty; unrelated settings
and cancellation semantics are preserved.

Local verification passed **22 adapter cases within 208 Android host tests**,
**235 freshly rerun JVM tests**, both Android debug-role compiles, **204
infrastructure tests** and **41 mobile script tests**, with no test failures,
errors or skips in the native/shared suites. Host cipher/preferences doubles
exercise adapter behavior, not AES-GCM, real Keystore, disk rollback or power-loss
acceptance. The revised T4 catalog retains 56 cases, strengthens three existing
Android cases for both products/roles, and invalidates old catalog bindings.
The template remains `NOT_STARTED`; real native storage, hosted authority,
staff recovery, field and pilot acceptance remain ordered prerequisites.
Android commit `cc19776` now passes both
[push CI](https://github.com/Q-SiO2/taxi/actions/runs/37023593864) and
[PR CI](https://github.com/Q-SiO2/taxi/actions/runs/37023603230), including both
iOS simulator application links, not native iOS test execution. The subsequent
OpenAPI tooling has separate passing immutable CI at `17a94df`, not registry
publication or deployment acceptance. No new
dependency, schema, wire, UI, pricing or provider policy is introduced.

**Server live-session authority follow-up (2026-10-02):** the final socket hop
now owns verified mobile user/session IDs and the JWT deadline, rechecks fresh
SQL session/account authority at admission, before each hint and while idle,
and retains admission/send/monitor/close ownership through cleanup. It shares
the REST authority predicate and changes neither schema nor wire payloads.
Known authority loss closes `4401`; unavailable authority closes `1013`.
Caller cancellation cannot abandon the retained closer, and no inbound frame
executes a business command. HINT-08 documents the read/send race, noncooperative
transport limit and unaccepted fleet-wide budgets rather than claiming immediate
revocation of already buffered frames.

Local verification passed 106 focused backend cases, 199 infrastructure tests
and the network-guarded 20-scenario/66-test T2 pack. The complete guarded
fresh-PostGIS run passed **1,090 tests with zero failures, errors or skips** and
three existing dependency deprecation warnings. Its
`backend/build/live-session-authority-t3-20261002/` bundle requires both migrated
`LIVE_SESSION_AUTHORITY` cases, confirms migration 0052, zero residual clones,
revoked temporary `CREATEDB`, and an 81-table/8,511-row logical restore with target
and dump removal. All six bounded T3 evidence kinds are present; formal phase
and deployment acceptance remain false. Server commit `2d6a68b` passed both
[push CI](https://github.com/Q-SiO2/taxi/actions/runs/37000510927) and
[PR CI](https://github.com/Q-SiO2/taxi/actions/runs/37000515435), including both
iOS Release simulator application links, not native iOS test execution.
It still requires hosted pool/load/multi-replica evidence,
physical device recovery and FCM/APNs delivery acceptance. Source engineering
scope remains approximately 84%; accepted P0 deployment gates remain 0/19.

**Test-toolchain follow-up (2026-10-01):** pytest 9.0.3 and pytest-asyncio 1.4.0
replace the vulnerable pytest 8 pair while preserving explicit function-scoped
fixture/test loops. The hash-enforced install, `pip check`, separate local
runtime/development audits, 20-persona/60-test simulation pack, 196 infrastructure
tests and complete migrated-PostGIS regression passed. The fresh regression has
1,011 passing tests with zero failures/errors/skips and three existing
deprecation warnings. Its `backend/build/pytest9-t3-20261001/` bundle confirms
migration 0052, zero residual clones, revoked temporary database authority and a
current-head logical restore matching all 81 tables. CI now separately audits
the development lock plus the reviewed Linux wheel supplement, with removal/
bypass mutation protection. Linux audit execution, immutable remote acceptance,
formal T3 approval and all real-environment/device/provider gates remain distinct
from this local evidence. No business contract or migration changed.

The repository contains the provider-independent implementation described here,
including migrations through `20260908_0052`. Local backend unit/API/integration
tests, Android/shared compilation, JavaScript and Kotlin/Wasm compilation, and
portable source-contract checks have passed in the current workspace. The
dated baseline full fresh-PostGIS run (2026-09-09) passed 992 backend tests with no
failures, errors or skips, including the paired cash workload and deterministic
dispatch-contention cases. That report also includes fixed-owner outbox
aggregation, privacy-bounded Prometheus alert validation, aggregate security-
incident deadline snapshots and real-PostGIS city-authorization provider-failure
recovery. The shared JVM suite contains
183 tests, and contract gates cover 83 mobile HTTP plus one WebSocket operation
and 112 web HTTP operations. The city-authorization slice passed 33
focused backend cases, also included in that full backend regression, and both
web browser suites. These are local dirty-workspace results, not release
certification. Both `jsBrowserDistribution` and `wasmJsBrowserDistribution`
also completed locally from the current source. Six dependency-free runtime
scenarios now execute the static web compatibility loader's supported, update,
forced-upgrade, retry, local-origin and exact-origin/path header-scoping behavior
in CI. The 2026-09-09 compatibility
candidate's 6,104,171-byte JavaScript fallback is within its narrowly reviewed
6,250,000-byte ceiling; startup measurements on target networks remain required
performance evidence. The
current CI definition covers backend, Android/shared, iOS simulator compilation,
documentation/provenance validation, and JavaScript/Wasm browser tests plus a
production compatibility distribution. It also defines immutable-action
dependency review, resolved Gradle graph submission, backend image SPDX SBOM and
source-hash binding, a generated 244-operation/52-migration/22-permission/nine-role
source-contract inventory, and a blocking high/critical image scan. Web and
Android/iOS verification outputs now produce limitation-marked manifests that
are hash-bound to the clean source candidate in CI and retained in its run
summary. The backend job also runs a frozen T2 catalog of 20 simulated persona
and adversarial scenarios over 66 exact unit tests, retains JSON/JUnit evidence,
and explicitly refuses phase or deployment acceptance. The inventory
is deterministic, validates the migration graph and role mapping, is printed in
the CI run summary, and is hash-bound into backend candidate evidence. The new and changed
jobs still require a passing remote run on an immutable commit; their presence in
YAML is not a clean vulnerability report or signed release provenance.

The guarded backend runner and CI definition now also generate bounded T3 JUnit,
database-metadata and system-evidence artifacts. The local run verified migration
0052 on PostgreSQL 16.14/PostGIS 3.5.3, 992 skip-free tests, named lock/race/
worker-reclaim/reconciliation cases, zero residual clone databases and revoked
temporary local `CREATEDB` authority. One stale disposable clone from an earlier
interruption was strictly identified and removed before the successful metadata
check. A guarded custom-format backup subsequently restored 81 public tables and
8,511 aggregate rows into an ephemeral database, matched migration/PostGIS/
schema/table totals before and after a no-op upgrade, and removed the database
and dump. The combined report supports all six T3 evidence kinds and marks
evidence complete; T3 and deployment acceptance remain false pending engineering
sign-off and an ordered phase record.
The production deployment now has an optional hardened Prometheus/Alertmanager/
Loki/Alloy/Grafana overlay with internal-only API/worker scraping, bounded
application-owned JSON log volumes, Docker-secret bearer
authentication, loopback operator ports, fixed owner receivers and digest-pinned
parser/runtime validation in CI. It has passed local structural, mutation,
merged-Compose, `promtool`, `amtool`, Loki/Alloy parser, hardened Grafana
provisioning, and real two-role ingestion checks. The committed immutable
26-panel operations dashboard and three-panel log dashboard use only reviewed
service, worker, fixed-owner and fixed incident-severity telemetry. No hosted
target, populated dashboard
review, webhook receiver, retention/capacity result or on-call drill is thereby
accepted.
The operations web console also includes a modular account-security command
surface backed by the scoped containment API. It is permission-hidden, case-led,
typed-confirmed, and non-replaying; JS/Wasm tests cover permission routing, input
validation, and response decoding. A production-like staff drill remains required.
The staff-access destination now has separate request-validation, gateway,
coordinator, and Compose review modules. It supports all closed backend role
templates, exact selected scope, expiry/manual-recertification display, typed
request/decision confirmation, recent-MFA non-replay and authoritative reload.
Migration `20260907_0049` and the administration service implement a durable
pending queue, distinct maker/target/checker identities, optimistic decisions,
per-market serialization, transactional revalidation, production direct-write
refusal and two-admin continuity. The bounded offline initial-quorum command
closes after the third administrator. GAP-022 remains open only for roster,
recertification, broader sensitive-command policy and real hosted staff evidence.

Migration `20260907_0050` adds a platform-admin-only, market-scoped security
incident register and append-only timeline. The API requires recent MFA and
idempotency for every write, uses optimistic versions for a strict forward-only
lifecycle, permits evidence links only to same-scope immutable audits or bounded
external references, and keeps timeline narrative out of audit metadata. A
focused unit/PostGIS coverage passed. Migration `20260907_0051` adds a one-time,
versioned postmortem completion command with controlled outcome, completion
actor/time, same-scope audit or bounded external evidence, append-only timeline
fact and database completion-shape checks. The protected web workspace now adds
permission-hidden queue loading, incident creation/detail, append-only timeline
forms, exact next-state actions, postmortem completion, typed confirmation, stale
reload and MFA non-replay behavior; both browser targets pass 57 tests. Migration
`20260908_0052` adds four closed responsibility types, one active assignee per
type, immutable assignment facts with a one-time release transition, initial-lead
backfill and generated responsibility timeline events. Assignment accepts only an
exact active user with live platform-administrator authority in the incident
market, requires a controlled roster/shift reference and updates the response
lead/version atomically. The protected web workspace displays active and released
tenures and uses a fail-closed four-value route selector. Both
protected scrape roles now run a five-second-bounded aggregate deadline query and
emit only SEV1-SEV4 open, containment-overdue, postmortem-pending and postmortem-
overdue counts. Five immutable Prometheus rules and three dashboard panels cover
snapshot failure, high-severity open incidents and deadline breaches. Real
receiver delivery/escalation acceptance, containment orchestration, notification
approval, authoritative duty-roster staffing and a hosted drill remain open under
GAP-031.

This is not a production-readiness statement. The repository has no accepted
hosted environment, real city evidence, signed mobile release, provider
credentials, production operations roster, or completed security/capacity/device
acceptance. [`gaps.md`](gaps.md) is the authoritative open-work register.

## 1. Repository Structure

TaxiMobile remains one repository with four deliberate top-level areas:

```text
Projects/
|- TaxiMobile/                 # Kotlin Multiplatform mobile clients and operations web
|- backend/                    # Python modular-monolith API, worker, migrations, tests
|- infra/                      # local Compose and deployment configuration
`- docs/                       # authoritative product and technical decisions
```

`TaxiMobile/` is retained as the client build root. `backend/` and `infra/` are separate because Python and deployment tooling must not be coupled into the Kotlin build. Generated files, local databases, credentials, and build output are never committed.

## 2. Mobile Clients

The product has two mobile applications with different operational roles:

* **Passenger** requests and follows rides.
* **Driver** manages eligibility, availability, ride offers, and active rides.

They share one Kotlin Multiplatform codebase. Android starts with two product flavors in `TaxiMobile/androidApp`; iOS starts with two targets/schemes that embed the same shared framework. This produces separate installable apps without duplicating business or API code. Desktop remains a development/UI-test surface. The approved national expansion promotes `TaxiMobile/webApp` to the operations and driver-application web client described below.

The shared module evolves toward this feature-first structure:

```text
TaxiMobile/shared/src/commonMain/kotlin/<package>/
|- app/                 # app composition, role routing, navigation contracts
|- core/                # result/error types, time, configuration interfaces
|- data/                # API client, DTO mapping, repository implementations
|- domain/              # entities, use cases, repository interfaces
`- feature/
   |- auth/
   |- app/              # root state router plus shared secondary sections
   |- passenger/        # map-first passenger home and passenger-only presentation
   |- driver/           # map-first operational home and driver-only presentation
   |- maps/             # shared contract with platform MapLibre implementations
   |- notifications/
   |- ui/               # theme tokens and dumb reusable components
   |- rides/
   `- profile/
```

### Operations web application

`TaxiMobile/webApp` no longer calls the passenger/driver `App()` root. Phase 12
boots a dedicated `OperationsApp`; Phase 13 adds a separate public applicant
composition root selected by `/apply` or `#/apply`. The module may reuse shared
localization, exact-money/coordinate types, API error mapping, and approved UI
tokens, but it must not import mobile ride-screen composition or mobile
secure-storage assumptions.

Implemented Phase 12–17 structure:

```text
TaxiMobile/webApp/src/
|- webMain/kotlin/<package>/
|  |- main.kt                         # browser composition root
|  |- application/
|  |  |- OperationsEnvironment.kt     # local/same-origin API resolution
|  |  `- WebSurface.kt                # explicit operations/applicant routing
|  |- applicant/
|  |  |- state/ApplicantPortalCoordinator.kt
|  |  `- ui/                          # account, catalog, application editor/status
|  `- operations/
|     |- model/OperationsModels.kt    # DTOs, scope, permissions, destinations
|     |- model/ControlPlaneModels.kt  # typed create/transition contracts + geometry validation
|     |- model/PricingEconomicsModels.kt # exact-string policy contracts
|     |- model/AnalyticsModels.kt    # strict definitions/facts and nullable suppressed measures
|     |- data/OperationsGateway.kt    # Ktor API boundary and bounded read batches
|     |- data/ControlPlaneGateway.kt  # city/operator/assignment/area/config commands
|     |- data/PricingEconomicsGateway.kt # isolated scoped economics API
|     |- state/OperationsCoordinator.kt
|     `- ui/
|        |- OperationsApp.kt          # auth/scope/navigation shell
|        |- OperationsComponents.kt
|        |- OperationsScreens.kt      # rollout/city/operator + Phase 18 staged readiness
|        |- ControlPlaneEditors.kt    # bounded control-plane dialogs and bundle resolver
|        |- DriverRecruitmentScreen.kt # delivered Phase 13 module
|        |- PricingEconomicsScreen.kt # delivered Phase 14 module
|        |- PricingEconomicsEditors.kt # small draft/editor components
|        |- ScheduledExceptionsScreen.kt # delivered Phase 16 scoped inspection
|        `- AnalyticsScreen.kt        # Phase 17 filters, summaries, fact table, definitions
`- webTest/                            # routing, permission, state, formatting tests
```

Driver review and applicant packages now exist because their Phase 13 backend
slice is delivered. Phase 14 adds a separate pricing-economics model, gateway,
screen, and editor package rather than enlarging the general operations files.
Fixed-route and scheduled-booking packages now exist as their owning roadmap
slices are delivered. Phase 17 adds a separate analytics model and screen rather
than enlarging the control-plane files. The
scheduling-policy editor covers the full Phase 16 timing, conflict, cancellation,
refund, and fallback contract, while the exception screen remains read-only and
scope-authorized.
This keeps the browser module reviewable for a smaller context window and
prevents dead navigation from implying unavailable authority. Applicant
bearer/refresh tokens are memory-only; page refresh signs out. Protected document
controls remain disabled until the backend advertises and actually provides the
reviewed secure storage boundary.

Phase 18 deliberately reuses the market/configuration aggregate instead of
creating a second rollout state machine. Backend constants define separate
pilot-entry and public-activation gate sets plus post-launch evidence. Lifecycle
commands choose the set by target state; configuration replacement uses the
city's current state. `OperationsScreens.kt` presents the three stages, while the
gateway/coordinator own the typed optimistic command and authoritative reload.
The same application and schema therefore deploy every city without a city fork.
The city/operator destinations are no longer inspection-only: authorized staff
can create a city and operator, activate/deactivate the operator, create or
retire exact-scope service assignments, enter a WGS84 polygon without editing
GeoJSON, review the service-area lifecycle, and assemble a configuration from
compatible active authoritative versions. The browser disables incomplete
bundles and displays missing policy/payment/recruitment/route dependencies; the
backend independently revalidates scope, lifecycle, effective time, optimistic
version, and recent MFA before mutation.

The browser client calls only HTTPS `/api/v1` contracts. Administrative access
uses a dedicated audience/session policy, exact operations origin, mandatory MFA
before national production, no persistent browser bearer token, and the CSRF/CSP
boundary in `security.md`. The selected scope in the UI is presentation input;
the backend grant remains authority. Operations web releases are built/tested and
promoted separately from Android/iOS artifacts.

Compose screens present state and dispatch user intent. View models and use cases perform application work. Repository implementations call the backend; no UI component may directly issue network requests. Ktor Client and kotlinx serialization are the selected shared HTTP/serialization stack. Secure token storage, location, push registration, permissions, and maps are interfaces in shared code with implementations in Android and iOS source sets. Sensitive tokens never go into normal preferences or logs.

The root `TaxiMobileScreen` is intentionally limited to authentication, session,
offline, driver-application gates, and routing authoritative `AppUiState` to one
role home. Passenger and driver homes remain separate files/packages and consume
small shared sections for notifications, support, and coordinate formatting. Do
not merge role implementations back into a single scrolling screen or retain old
renderers after a replacement is routed; this boundary keeps each feature small
enough to review and test without loading the entire mobile product.

Android currently supplies an AES-GCM Android Keystore implementation of the secure token store and constructs its Ktor client with the OkHttp engine. Each product flavor supplies a development API base URL through build configuration; staging and production builds must inject a TLS URL through their protected build/deployment configuration rather than altering shared client code.

iOS uses the same shared gateway/coordinator composition with Ktor's Darwin
engine and an iOS Keychain token store. The Keychain implementation replaces one
versioned, length-delimited access/refresh envelope atomically, constructs real
Core Foundation dictionaries/data rather than casting Kotlin objects, checks
Security-framework status codes, and releases every object it owns. Storage
failures are translated by the shared authentication coordinator and a failed
login save triggers best-effort revocation of the newly issued backend session.
Its Swift shell reads the app role and API base URL from target build settings,
keeping production URLs and role choice out of shared Kotlin code. The checked-
in default URL is deliberately invalid; an iOS release must inject a TLS URL
through protected configuration.

iOS Release builds enforce the same fail-closed boundary as Android. Both
targets require explicit HTTPS API and MapLibre style URLs, positive numeric
build/marketing versions, target-matching ignored Firebase configuration, code
signing, and an externally supplied Apple development team. A post-resource
build phase validates and installs only the selected role's Firebase plist.
Shared entitlements select development APNs for Debug and production APNs for
Release, and the application declares the remote-notification background mode.
CI may explicitly bypass signing and missing Firebase only for non-distributable
simulator compiler verification; URL and version validation still runs.

The Xcode project supplies separate `TaxiMobile Passenger` and `TaxiMobile
Driver` targets and shared schemes, with distinct bundle identifiers and app
role build settings. Both targets intentionally compile the same Swift shell and
shared framework so API and business behavior cannot drift between products.

The Android debug manifest permits cleartext only for the standard emulator host
`10.0.2.2` and `127.0.0.1`. The latter supports a USB-connected physical device
through `adb reverse tcp:8000 tcp:8000`; it does not expose a development API on
the local network. Build that debug APK with
`-PtaximobileDebugApiBaseUrl=http://127.0.0.1:8000`. Release builds retain
Android's TLS-default policy and resolve `taximobileReleaseApiBaseUrl` to a TLS
URL; the repository's invalid default prevents accidental production use.
`TaxiMobile/scripts/run-android-device.ps1` is the preferred physical-device
entry point (invoke it with `powershell -NoProfile -ExecutionPolicy Bypass
-File .\scripts\run-android-device.ps1 -Role passenger`): it verifies backend
health, requires exactly one authorized device, establishes and verifies the
reverse tunnel, injects the loopback debug URL, builds and installs only the
selected role flavor, and launches its activity.
With `-RegistrationSmoke -ConfirmClearAppData -EvidencePath <new-json>`, the same
launcher now records a bounded T4 Android registration/login report containing
SDK/ABI/model/locale/screen/package metadata and backend-confirmed journey
results. It does not record raw serials, screenshots, credentials or submitted
values and cannot claim broader device-matrix or T4 acceptance.
The broader T4 laboratory is frozen in a 56-case machine-readable catalog with
eight cases per phase evidence kind. A dependency-free validator checks platform
targets, browser/locale/RTL coverage, device/browser fidelity flags, safety,
retained artifact metadata and no-acceptance boundaries. The committed run
template is intentionally 0/56 `NOT_STARTED`.
After compilation it waits a bounded 120 seconds for the same authorized device
serial to recover from a transient USB/ADB reset, re-establishes the reverse
tunnel, and refuses to install on a replacement device.
This makes an emulator-only `10.0.2.2` APK an explicit configuration choice
instead of a silent phone-testing failure.

The same launcher has an explicitly destructive-to-debug-data registration
acceptance mode gated by both `-RegistrationSmoke` and
`-ConfirmClearAppData`. It requires `/ready`, establishes ADB reverse, rebuilds
with device loopback, clears only the selected debug package, then drives the
localized registration and login UI with unique synthetic local credentials.
Its accessibility hierarchy remains in memory and its safe output contains no
credentials or raw UI dump. Pure parser/catalog/input tests run in CI; a real
pass still requires an authorized physical Android device.

A separate additive local UX seed command creates four unique synthetic accounts
behind explicit confirmation and refuses every non-development or non-loopback
database. The rich passenger/approved-driver pair shares an en-route ride and
includes history, pending/settled cash receipts, rating, notification, support,
vehicle, credential, cooperative, and earnings data. Pending-driver and empty-
passenger accounts cover the corresponding gates. The command never deletes or
rewrites an existing account and is development review tooling, not a production
seed path. Assigned-driver ride-detail access is covered in the migrated
PostGIS lifecycle because the driver mobile coordinator requires that participant
read; unrelated drivers and administrators remain forbidden.

Android release variants are fail-closed build products. They require explicit
HTTPS API and MapLibre style URLs, positive release version metadata,
flavor-aware Firebase configuration, and a complete externally supplied signing
configuration. They also require the explicit
`taximobileCrashReportingEnabled=true` release input. Partial signing
configuration is rejected. Both products disable
application backup and cleartext traffic, run fatal lint, and enable R8 code and
resource shrinking. Signing keys and passwords enter Gradle only through the
release secret boundary and are ignored by source control; matching R8 mappings
must be retained securely for crash deobfuscation. CI may use the two explicitly
named verification-only escape properties to compile unsigned artifacts without
provider files, but those APKs are non-distributable.

Firebase Crashlytics supplies native crash/error monitoring for both role apps
without Firebase Analytics. Android uses the pinned `3.0.7` Gradle plugin and the
Firebase BoM-managed SDK; the plugin is applied only when a flavor-aware Firebase
configuration exists, so distributable release builds upload the matching R8
mapping while providerless local/CI compilation stays possible. Android Debug
sets `firebase_crashlytics_collection_enabled=false`.

The pinned Firebase Apple package exposes both Messaging and Crashlytics to each
iOS role target. Debug sets `FirebaseCrashlyticsCollectionEnabled=NO`; Release
reads the explicit `TAXIMOBILE_CRASH_REPORTING_ENABLED` switch, which validation
requires to be `YES` except for the existing providerless CI path. A final target
build phase invokes the package's Crashlytics uploader only when collection is
enabled and the target-matching plist has been installed. It fails closed if the
uploader or plist is absent. No source sets a Crashlytics user ID, custom key,
manual log, or Analytics breadcrumb. The portable crash-reporting validator
locks these constraints for both targets.

Source wiring is not operational acceptance. Promotion still requires approved
Firebase processing/retention/access policy and privacy notice, controlled
staging crashes in all four role/platform applications, project-isolation proof,
and symbolication evidence. R8 mappings and dSYMs are protected release artifacts.

The client uses REST for reads and commands, and authenticated WebSockets only to learn that current data may need refresh. On reconnect, foregrounding, and any rejected command, it retrieves the backend-authoritative ride or driver state. It does not queue irreversible ride, payment, or availability changes as successful while offline.

Android and iOS wire the shared `Retry connection` action to secure session
restoration. The UI shows the restoring state during that request and then reloads
the relevant backend-owned passenger or driver data. Retry never assumes the
failed command succeeded and never submits it again automatically.
Both native roots also own a lifecycle-bounded connectivity observer: Android
requires a validated default network and iOS uses the Network framework path
monitor. Their common transition policy ignores initial/repeated availability and
requests exactly one normal restoration after an unavailable-to-available edge.
The platform signal remains advisory and cannot acknowledge API reachability or a
business command.

Both roots use the common Compose lifecycle for foreground recovery. A tested
`ForegroundRecoveryPolicy` arms only after `ON_STOP`, consumes that arm on the
next `ON_START`, and ignores initial or repeated start events. An authenticated
foreground return calls the same coordinator restoration and retained-state
reducer as reconnect, push, and manual refresh; signed-out foregrounding does not
make an unnecessary authenticated request and no failed mutation is replayed.
Authenticated UI actions also pass through one shared one-shot recovery helper.
It invokes the action once; if the coordinator returns an uncertain/rejected
offline result while a session is active, it invokes `restore()` once as a
read-only reconciliation and never invokes the action again. A successful restore
replaces stale ride/driver content while preserving the original localized
operation error in the sticky banner. An authoritative session rejection signs
the user out and clears retained content.
The platform roots synchronously acquire `AppActionGate` before launching that
helper. While the coroutine is suspended, a resource-aware `AppAction` is passed
through shared Compose: the initiating `TaxiButton` renders its loading state and
all competing backend controls are disabled. Duplicate and conflicting taps are
discarded locally, and a `finally` block releases the gate after every normal or
exceptional completion. The gate controls admission only; it never acknowledges
a command or replaces backend idempotency and authorization.
The portable mobile-recovery validator locks Android's validated-network callback,
iOS's satisfied-path monitor, both lifecycle event pairs, the session guard, every
authenticated action callback, synchronous pre-coroutine admission,
resource-specific loading presentation, and the retained authoritative reducer
for hosts that cannot compile iOS.

The shared action boundary emits a monotonic `AppActionCompletion` only when a
coordinator returns non-error authenticated state. Shared Compose uses that event
for an accessible 320 ms check-draw and static cash/rating confirmation. Support
and vehicle forms reset only from the matching completion sequence, so an API
rejection, session expiry, or uncertain network outcome never erases user input
or displays optimistic success.

The signed-out account surface distinguishes registration outcomes explicitly.
A backend-confirmed account creation clears the password, prefills the submitted
identifier, and exposes one merged polite success live region; a rejected
registration retains its non-secret form values and exposes an assertive error
live region. This prevents successful registration from being styled or announced
as a failure.

`AppStatePresentation` retains the last authenticated backend-confirmed screen
when a later coordinator call returns a network or operation failure, while carrying the
localized failure separately to the shared sticky top banner. A successful
restore replaces the retained screen and clears that issue. Initial restoration
without usable content still reaches the dedicated offline screen. No failed
ride, driver availability, cash-settlement, or payment mutation is persisted for
automatic replay.
After a successful passenger cancellation command, the client reloads the ride
collection instead of retaining the terminal ride as active. The cancelled ride
remains in backend-confirmed history while pickup/destination controls become
available for a genuinely new request.

MapLibre Native is the Android/iOS map renderer. Platform source sets own SDK
lifecycle, permissions, user-location presentation, and platform attribution UI;
shared presentation code owns selected coordinates and provider-neutral route
state. Native GeoJSON sources and layers are declared only inside the
`MaplibreMap` style-composition scope; a portable source gate enforces this on
both platforms because composing a source before that scope is entered is a
fatal runtime error. Debug device builds default to the restrained OpenFreeMap
Positron style instead of MapLibre's colorful demonstration style. A failed or
missing configured style switches to a bundled neutral JSON background with no
sprite, glyph, font, image, or remote-source dependency; route and point overlays
remain visible, the sheet reports reduced map detail, and passenger manual
coordinate entry is promoted even outside debug mode. Release style/tile URLs
remain explicit environment configuration. The mobile client calls
`POST /api/v1/routing/route`; only backend provider adapters understand Valhalla
or GraphHopper response shapes. A closed environment selector chooses exactly one
adapter per deployment, with Valhalla as the default. Geocoding is a separate
future adapter.
Routing graph promotion now has a guarded provider-neutral acceptance command.
It sends only three fixed public Morocco city scenarios through the selected real
adapter in English, French, and Arabic; validates plausible distance, duration,
speed, Morocco-bounded geometry, endpoint snapping, maneuver ranges, and distinct
localized narration; and reports only scenario IDs and stable failure codes.
Non-local targets require exact hostname confirmation. The command deliberately
fails Valhalla 3.8.3 for unsupported Arabic narration instead of certifying its
English fallback, while GraphHopper must prove Arabic script using its promoted
graph and catalog.
Both provider adapters reject non-finite or negative route metrics, invalid
coordinate bounds, empty maneuver text, and maneuver indices outside normalized
geometry. Provider rejection, malformed JSON, and invalid normalized data all
collapse to the same safe routing-unavailable boundary.
Local Compose now provides mutually exclusive `routing-valhalla` and
`routing-graphhopper` profiles. The GraphHopper path builds a repository-reviewed
non-root/read-only image from the official 11.0 Maven JAR and a digest-pinned Java
17 base; both executable artifacts are SHA-256 pinned. Its dated Geofabrik input
is SHA-256 verified before atomic placement, and PBF/graph names include that
digest so a changed extract cannot silently reuse an older graph. Guarded startup
sets the matching backend adapter URL, checks a fixed Casablanca route, and may
run the complete provider-neutral acceptance command inside the API container.
Both profiles intentionally claim host-loopback port `8002`, making accidental
dual activation fail while each provider retains its native private container
port. The guarded launcher selects exactly one profile and injects only that
provider's internal URL into the API process.
The passenger product reloads the authorized detailed ride after creation and on
later refreshes, then requests the normalized pickup-to-destination route for its
active MapLibre view. This visualizes the journey but does not claim live driver
position; status and assigned-driver information still come only from the ride
API. An active assigned passenger ride may additionally carry one latest driver
observation submitted after acceptance. Android and iOS render it as a distinct
static MapLibre marker, display its server observation time, and expose an
explicit ride refresh. The API omits pre-assignment and terminal-ride driver
locations, so this adds bounded last-known visibility without creating public
location history or pretending foreground one-shot updates are a live stream.

Passenger ride-history summaries retain the backend-returned pickup and
destination coordinates plus optional display addresses. When no ride is active,
the request sheet derives at most three unique recent destinations from completed
rides, in backend history order. Selecting one only fills the destination; the
passenger must still select a pickup and request a fresh backend fare estimate.
The client creates no separate destination-history store.

Passenger activity rows are explicit actions rather than static labels. Opening
a row reloads that owned ride through `GET /rides/{ride_id}` and, for a completed
ride, loads its backend-finalized receipt. The selected detail is ephemeral UI
state, preserves optional backend display addresses, and never grants access
beyond the API's participant authorization.

Driver history rows use the same explicit, owner-authorized detail pattern. A
selection reloads the ride and, only for a completed ride, requests
`GET /rides/{ride_id}/ratings`. The private driver account renders the score and
optional passenger comment returned by that endpoint without reviewer identity,
client-side aggregation, or one rating request per list row.

Cooperative identity and membership are persisted independently from driver
verification, account roles, and dispatch eligibility. The authenticated
`GET /cooperative/membership` endpoint exposes only the caller's single current
non-ended membership and cooperative display name. It returns `404` when none
exists and fails with `409` if multiple current memberships need administrative
resolution; it does not invent membership administration or governance policy.
Android and iOS use the same optional shared membership gateway and show the
backend result only in the driver's private account sheet.

Professional credentials now have an ownership-indexed, privacy-minimized table
and `GET /drivers/me/credentials` self-read endpoint. Credential types remain
configurable because jurisdictional requirements are not yet fixed; the response
omits numbers and all document/storage references. Those reusable credential
records remain metadata-only. City-application document upload is a separate
implemented boundary using encrypted private-volume storage, malware scanning,
retention, and MFA-gated administrator retrieval; it does not add raw files or
storage references to the credential endpoint.
Driver verification reads and submissions also return the authoritative optional
`submitted_at` timestamp documented by the API instead of making the client infer
it from local state.
Android and iOS load credential metadata through the shared driver gateway and
render it only in the private driver account sheet.
City-application document controls use native bounded file selection on both
platforms: Android's storage access framework and iOS's security-scoped document
picker accept only PDF/JPEG/PNG files up to 10 MiB, hold bytes transiently, and
then call the same authenticated shared upload mutation. Cancellation makes no
request, invalid local input is rejected, and the backend independently repeats
type, size, ownership, version, and malware checks.
That sheet also presents the backend profile name, verification status, and
account status instead of dropping those already-authorized profile fields.
Backend availability, matching, and offer acceptance reject any recorded
credential that is not `VERIFIED` or has expired according to backend time. An
empty set remains eligible until the policy owner defines required types; active
rides are not interrupted by a mid-ride credential change.
A bounded credential lifecycle worker uses row locking and the persisted warned
expiry value to produce one pre-expiry notification per credential date. It
marks due credentials `EXPIRED`, writes a distinct notification, and enqueues
only a credential-ID FCM refresh hint. Poll interval and warning days are bounded
environment settings, and the worker has the same low-cardinality success/error
telemetry as matching and outbox processing.

Android uses runtime coarse/fine foreground permission and `LocationManager` for
one-shot lookup. iOS uses Core Location with when-in-use authorization and
`requestLocation`. Neither app requests background location or subscribes to
continuous OS updates. A denial, timeout, or disabled provider returns control to
the shared UI without submitting an invented coordinate; map-tap and validated
manual entry remain available. Passenger pickup, the driver's initial staged
location, manual driver fallback, and ride completion require explicit user
actions before backend submission.

After backend-confirmed online entry, a tested shared policy schedules the same
one-shot adapter every 15 seconds for `AVAILABLE`/`OFFERED_RIDE` and every 10
seconds for active-ride states. Android/iOS lifecycle callbacks disarm it on
background; offline/paused/disconnected state, an active platform lookup, or an
ordinary pending command suppresses each attempt. The automatic requester never
opens permission UI. Unavailable observations trigger localized guidance and a
60-second backoff. The backend continues to decide freshness, movement,
service-area validity, eligibility and matching.
Automatic completion is separately guarded by
`ForegroundDriverLocationResultGuard`: both successful coordinates and null
results must still belong to the original operational context. Native roots
invalidate immediately on background, connectivity change, admitted command and
composition disposal; completion rechecks foreground, usable network, absence of
an ordinary command, and unchanged availability/vehicle/city/service/ride. A
background/network return or logout/login cannot revive the earlier lookup.
Discarding a result does not revoke permission, cancel OS work, retain a trail or
change backend authority. The next eligible sampling attempt remains governed by
the existing cadence and one-shot gate.
Both platform requesters use the tested common `OneShotLocationGate`: a second
tap is rejected instead of calling the first pending callback with failure or
launching another permission/location request. Shared passenger and driver
controls remain disabled with an accessible loading state until that callback
returns, after which the gate is released.
After the backend accepts a driver update, shared presentation code retains only
that latest coordinate in process memory so authoritative availability, offer,
and ride refreshes can recompute pickup or destination guidance. It is cleared
at account boundaries, is never persisted as client-side location history, and
does not replace backend freshness, movement, or dispatch validation.

## 3. Backend

The backend is a Python 3.12+ FastAPI modular monolith. It is intentionally not
microservices for the MVP. One deployable API owns the public contract, and the
same image runs a separate private worker now that outbox and matching processing
exist.

```text
backend/
|- pyproject.toml                # pinned, reproducible Python project metadata
|- alembic.ini
|- migrations/
|- src/taximobile_api/
|  |- main.py
|  |- core/                      # settings, logging, errors, auth primitives
|  |- db/                        # SQLAlchemy engine/session/base metadata
|  |- api/v1/                    # router assembly and common dependencies
|  |- domains/                   # domain-owned routes, schemas, services, models
|  |- integrations/              # replaceable map, payment, push, storage adapters
|  `- workers/                   # transactional outbox consumers when needed
`- tests/
   |- unit/
   |- integration/
   `- api/
```

The national phases add domain modules inside this monolith rather than new
deployables by default:

```text
domains/
|- markets/             # market/operator/city and configuration lifecycle
|- administration/      # scoped grants and audited control-plane commands
|- driver_applications/ # city requirements, applications, authorizations
|- fixed_routes/        # immutable route/direction/stop publication
|- scheduled_bookings/  # future booking, offers, commitments, handoff
|- pricing/             # city tariffs, scheduling surcharge, operator fees
`- analytics/           # typed facts and privacy-bounded aggregates
```

Existing `auth`, `drivers`, `rides`, `matching`, `payments`, and `outbox`
modules remain owners of their current rules. New modules call those boundaries;
they do not duplicate identity, assignment, fare, or payment state. Every
operational aggregate stores/derives city scope, but analytics never becomes a
command source of truth.

Migration delivery follows the roadmap and is intentionally split:

```text
market/operator/city + service-area/configuration versions + backfill
→ scoped grants
→ city requirement versions + protected application evidence/authorizations
→ city financial policy versions
→ fixed-route versions/directions
→ scheduled bookings/offers/overlap-safe commitments
→ typed aggregate facts/views
→ city-scoped support/safety cases → durable overdue alerts
→ legal holds + verified case minimization evidence
→ operations MFA → versioned payment capabilities + scoped reconciliation
```

These slices are delivered as `20260824_0033` (control-plane records
and deterministic compatibility backfill), `20260824_0034` (scoped grants,
operations sessions, and scoped audit columns), and `20260824_0035` (versioned
city driver requirements, applications/evidence/decisions/authorizations,
city/service online scope, and compatibility backfill), `20260824_0036`
(city/operator/service pricing, fee and scheduling-policy versions plus
immutable ride economics), and `20260827_0037` (published fixed routes,
directions/stops, reciprocal direction-scoped fares, city route allowlists, and
route-scoped rides), and `20260829_0038` (expanded scheduling policies, scheduled
bookings/offers/events, city-scoped driver preferences, exclusion-protected
commitments, and one scheduled-booking link per live ride), and
`20260829_0039` (coarse hourly supply snapshots, an allowlisted typed-event SQL
projection, and refreshable privacy-bounded aggregate facts), `20260830_0040`
(immutable support/safety city scope and city-aware queue indexes), and
`20260830_0041` (durable deduplicated overdue-case alert delivery and
acknowledgement state), and `20260830_0042` (city-scoped legal holds, nullable
post-erasure participant/ride links, case retention state, and immutable
minimization evidence), and `20260830_0043` (encrypted operations TOTP,
single-use recovery codes, bounded password challenges, accepted-counter replay
state, CSRF-bound operations sessions, and MFA method state), and
`20260831_0044` (verified city/operator recipient accounts,
city/operator/service payment-capability versions, coherent configuration links,
and ride/payment/refund settlement provenance), `20260831_0045` (protected
driver-document retention state/evidence), `20260902_0046` (expiring,
single-use mobile account-recovery code digests), `20260903_0047`
(closed-code active-ride coordination messages), `20260903_0048`
(one active live ride per driver, with conflict-refusing preflight), and
`20260907_0049` (staff-grant maker-checker state and uniqueness), and
`20260907_0050` (scoped security incidents, immutable timeline and lifecycle
constraints), and `20260907_0051` (one-time security-incident postmortem
completion and deadline indexes), and `20260908_0052` (closed incident
responsibilities, one-active-role uniqueness, append-visible tenure history and
initial response-lead backfill). The Phase 15 constraint compares Phase 14's
new native-enum lifecycle values through their text representation so a clean
multi-revision PostgreSQL `upgrade head` remains valid without revising the
delivered Phase 14 migration.

Backfills use reviewed deterministic mappings for existing pilot data and retain
historical IDs/amounts. A migration must not guess a city from an old arbitrary
coordinate or promote a legacy administrator to national access without an
explicit bootstrap mapping.

The selected persistence stack is PostgreSQL 16+ with PostGIS 3.4+, SQLAlchemy 2.x, asyncpg, and Alembic. PostgreSQL stores all durable business facts. PostGIS geography uses WGS84 coordinates and supports proximity operations. UUID primary keys, UTC timestamps, explicit constraints, optimistic/version checks or transaction locks where appropriate, and migration-only schema changes are mandatory. Money is represented with fixed-precision `NUMERIC` values and explicit currency; never floating-point values.

All APIs use `/api/v1`, JSON, FastAPI-generated OpenAPI, and the error model in `api.md`. The Kotlin client is handwritten against the published contract in the MVP. Code generation is deferred until the contract has proven stable.

The API process owns authentication, authorization, validation, ride state, assignment, fares, and payment status. Integration adapters receive only the minimum data required. Provider callbacks are verified, idempotent, recorded, and never directly trusted as client authority.

Password login performs one Argon2 verification whether the submitted identifier
maps to an active, suspended, or missing account. Missing accounts use a random
process-local dummy hash that cannot authenticate. A successful login upgrades
outdated Argon2 parameters transactionally before issuing the session. Access
JWTs require the fixed TaxiMobile issuer/mobile audience and every subject,
session, type, issued-at, and expiration claim in addition to HS256 signature
validation; server-side session and user-status checks remain authoritative.

Account recovery is isolated behind a separate shared `AccountSecurityGateway`
instead of expanding the login/session gateway. The backend owns recovery-code
generation, hashing, expiry, consumption, password replacement, and revocation;
Compose owns only shape validation and conditional generic presentation. Android
and iOS inject the same Ktor gateway. The signed-out recovery form and both
authenticated account sheets connect password-reauthenticated code creation,
one-time code display, session list/confirmed revocation, and password change.
Current-session revocation and password change clear native secure-token storage
and return to sign-in. The one-time bundle now requires an explicit saved-all-
codes acknowledgement before a local clear action removes it from passenger or
driver render state; the app does not silently copy secrets to a clipboard.
Physical-device save, background/process-death, accessibility, screenshot and
secret-lifecycle acceptance remain deployment work.

The shared mobile `RideGateway` exposes fare estimation as a backend call. A client may render the returned amount and tariff version, but it does not calculate, select, or lock the authoritative fare; the API locks the quote when the passenger creates the ride.

The same gateway now exposes a closed-code coordination command and decodes the
latest authorized message from detailed ride state. A dedicated backend
`ride_communications` domain owns role/code policy, authorization, active-state
validation, idempotency, rate/cap enforcement, persistence, recipient
notification, and minimized outbox creation. The mobile coordinator sends one
command and then performs a full authoritative refresh; it never appends a local
message optimistically. A modular shared Compose section renders the latest
signal and only the three actions for the current role. The action resource key
contains both ride ID and code, so only the initiating button shows progress
while competing choices stay readable but disabled. English, French, and Arabic
resources localize every known code; unknown future values fail to generic text
and are never offered as actions.

National quotes extend that response with backend-resolved city/operator,
service type, scheduling surcharge, operator fee calculation/funding mode,
passenger total, expected driver net, and immutable policy versions. Fixed-route
requests reference a published direction version. Scheduled requests use a
separate gateway/aggregate and do not add a long-lived scheduled state to the
live `Ride` model. The scheduled gateway first obtains a non-mutating review
estimate. Confirmation echoes the reviewed policy versions, and the backend
rejects stale terms before persisting the immutable booking snapshot.

## 4. Real-Time and Background Work

The API writes the business transaction first. Beginning with ride offers,
notifications, and ride-coordination signals, it writes an outbox record in that
same transaction. A worker delivers the resulting WebSocket and push
notifications, retries safely, and records delivery outcomes. A failed
notification never rolls back a ride, coordination message, or payment fact.

The MVP persists `ride.offer.created` and `ride.accepted` events in an
`outbox_events` table in the same transaction as their source state changes.
The records deliberately carry only IDs; the delivery worker authorizes and
loads current notification data rather than trusting a copied business payload.
For `ride.coordination.message`, the worker rechecks active ride state and a
five-minute freshness bound, then emits only the generic
`RIDE_COORDINATION_MESSAGE` hint. The persistent message/notification and the
subsequent authorized REST reload, not live delivery, are the user-visible truth.

Matching runs as a separate authoritative background processor alongside the
non-authoritative delivery worker. The ranked MVP filters eligibility in
PostGIS, takes a bounded nearest candidate set, and applies versioned configurable
proximity, uninterrupted idle-time, and recent-assignment fairness weights. New
offers persist distance, ETA, component scores, recent assignment count, and the
algorithm version. Decline and expiry preserve the driver's waiting timestamp,
exclude already-tried drivers for that ride, and advance sequentially. The
processor claims rides having expired pending offers with row locks and
`SKIP LOCKED`, then rechecks/locks their offers before the driver; horizontal
replicas cannot both expire the same claimed ride's offer. Candidate exhaustion records
`UNMATCHED`; it never leaves the passenger in an indefinite matching state.

`rides/locking.py` supplies current-state ride, owned-offer and driver locks.
Acceptance, decline, cancellation and expiry use ride-first order; assigned
driver cancel/transition/complete also refresh their locked profile. Acceptance
checks competing active rides without locking another aggregate after the driver.
Dispatch's state allowlist prevents re-opening en-route, arrived or in-progress
rides, and locked candidate profile rows refresh the ORM identity map. Eleven
isolated migrated-database cases in `test_live_ride_concurrency.py` cover seven
observed lock-wait races, expiry-worker skip/retry and three operational-state
dispatch rejections. The synthetic ORM fixture tests service/transaction behavior,
not the complete recruitment/HTTP/provider journey. No schema migration or new
dependency was required. Independent processes, broader administrative
revocation races and representative load remain open in `GAP-018`.

The subsequent assignment-invariant slice adds a database backstop:
`uq_rides_one_active_per_driver` covers all four active states across city and
booking origin. Its transactional migration refuses duplicate active data without
rewriting history and requires a measured maintenance window for the index build.
Two service races prove one winner for competing drivers or rides. Two mixed
scheduled/immediate races reuse the API-built city/booking fixture and a synthetic
outstanding live offer; each waits on the driver lock, refreshes stale state and
produces one active assignment. Four direct-write cases verify index enforcement
and terminal slot release, and a downgrade/conflict-refusal/reapply case proves
the migration does not silently repair records. These tests add defense and
bounded local evidence, not certification of all competing writers or workloads.

The scheduled-booking phase uses a separate lease-safe processor for opening
offer windows and performing dispatch handoff. It uses database time, row locks,
idempotent transitions, and bounded batches. A commitment does not change the
driver's live availability outside its configured protected window. Candidate
discovery requires the separate city-scoped scheduled-offer preference and
never treats immediate `AVAILABLE` state, push reachability, or passenger-facing
state as scheduling authority. Acceptance writes an active commitment with the
configured protected `tstzrange`; the transaction-safe overlap constraint/lock
rejects conflicting work and concurrent acceptance by another driver. At handoff,
the processor revalidates city authorization, active account/approved driver
verification, selected/owned/active/verified vehicle, known credentials and
active-ride conflicts, then creates at most one live ride or records the documented
fallback/unfulfilled outcome. The professional checks are shared with offering
and acceptance in `scheduled_bookings/eligibility.py`. The separate
`scheduled_bookings/readiness.py` guard requires available state, matching live
city/service and a fresh, bounded-clock-skew observation inside the active
PostGIS service area. Readiness failure uses the configured fallback/unfulfilled
path; the initial fallback candidate query excludes the failed committed driver.
Normal candidate filtering now also bounds future observations to the same
60-second online-admission tolerance. `GAP-007` retains device/field acceptance.

Scheduling mutations now acquire the booking lock before offer/commitment/driver
locks and refresh ORM state after waiting. Direct service callers use the same
lock helper as HTTP/worker paths. Driver online/offline/location and vehicle
mutation routes also lock and reload their profile; changing the active vehicle
is offline-only. Five deterministic two-session PostgreSQL races in
`tests/integration/scheduling_concurrency.py` prove a real lock wait with
`pg_blocking_pids`, retain deliberately stale ORM references, commit both actors
and inspect durable outcomes. They cover duplicate handoff, both cancellation
orders, offline-before-handoff and cancellation-before-acceptance. They do not
replace multi-instance HTTP/load or cross-domain revocation testing.

The separate `scheduled_acceptance_fixtures.py` fixture enables synthetic
on-demand scheduling and uses the real preference, quote, creation and offering
services. Five cases in `test_scheduled_acceptance_concurrency.py` prove one
winner per booking, one active commitment per buffered driver window, allowed
exact adjacency, committed cancellation releasing capacity, and the database
exclusion backstop against a concurrent direct writer. Four ASGI/PostGIS cases
in `test_scheduled_acceptance_http.py` cover overlap `409`, successful adjacent
acceptance and duplicate rejection, a real foreign-key failure, and rollback
after notification/outbox SQL flush. Nine metadata-classification unit cases
cover the narrow translation in `scheduled_bookings/conflicts.py`. Unexpected
integrity failures now remain sanitized internal errors instead of a misleading
overlap conflict. These source tests do not change the scheduling policy,
database schema, public endpoint set, or live availability, and do not prove
physical-device behavior or independent API-process failover.

`scheduled_bookings/protection.py` now supplies the one correlated Postgres range
predicate used by matching discovery, post-driver-lock selection and live-offer
acceptance. Scheduled acceptance performs the reciprocal current-window active-
ride check under the same driver lock. This closes the currently overlapping
assignment race without adding client authority or changing a commitment into a
live ride. Seven migrated-PostGIS service/concurrency cases and three authenticated
ASGI cases cover exact half-open boundaries, candidate exclusion, cancellation
release, stale offers, both acceptance orderings, `SKIP LOCKED`, client errors,
and allowed work outside the current window. Predicted immediate-trip overlap,
independent processes and device/field behavior remain open.

`auth/authority.py` now defines global account-status predicates and the paired
PostgreSQL locks used at assignment commit points and account containment.
Matching discovery filters inactive users; locked candidate selection, live-offer
acceptance, scheduled-offer acceptance and scheduled handoff hold `FOR SHARE` on
the user row. Both administration surfaces suspend through the refreshing
`FOR UPDATE` helper and the existing all-session/device revocation transaction.
Seven unit cases verify closed status and SQL lock shape. Six isolated PostGIS
cases verify suspended candidate/offer behavior plus both observed-wait winner
orders for live acceptance and scheduled handoff. This narrows the account subset
of `RACE-07`; it does not prove credential/vehicle/configuration races, independent
processes, device behavior or operational incident acceptance.

The location subset of `RACE-07` now has two migrated PostGIS contention cases
in `test_scheduled_location_authority.py`. Location writes and handoff already
serialize on the driver row. The tests prove that a waiting handoff sees a newer
outside-area observation and records unfulfilled/no-supply, while a handoff that
owns the lock first retains its accepted ride when the next location arrives.
Both inspect durable commitment, ride, notification and outbox results after an
observed lock wait. A reusable handoff fixture also serves the account tests;
the combined 15-case authority pack passed on 2026-09-05. Device, independent
process, service-area configuration and field acceptance remain required.

`driver_applications/authorization_lifecycle.py` and `authorization_router.py`
implement suspension, revocation and reviewed reinstatement of city authority.
The API uses existing review permission/scope, recent MFA, application versions,
idempotency with a fresh scope check even on replay, and transactional audit.
The reviewer console adds a separate status/expiry panel and typed confirmation.
Reinstatement rechecks global/professional status, owned vehicle, credentials,
application evidence, reviewed services, validity and competing authorization.
Approval now locks the driver before checking for active city authority, closing
its race with reinstatement. The focused 33-case backend run and JS/Wasm browser
tasks pass; the full 992-test backend regression includes this slice. Operational
acceptance remains open in `testing.md`. No schema change or automated live-ride
cancellation is added.

The immediate-authority follow-up adds ten city-restriction tests and two global
account/dispatch tests. It closes a reproduced assertion when discovery saw an
active global account but its later shared authority lock observed suspension:
the proposed driver is now separate from the selected candidate. Dispatch
rechecks its full eligibility query in a fresh statement snapshot after acquiring
driver/global authority, then finalizes selection only after all guards pass.
It can select other ranked eligible supply or leave the ride for bounded retry
without creating an offer for the rejected driver. All 30 focused tests pass;
full regression evidence is tracked in `testing.md`. No API/schema/UI change is
required. Independent-process and other revocation/configuration races remain.

Mobile and applicant web share `CityAuthorizationSummary` for localized recorded
status, supplied expiry and the server-eligibility/refresh notice. The presence
of an authorization no longer renders it as verified/active; unknown status has
an explicit unavailable label. Shared resources stay inside the shared module,
with a public composable rather than exposing generated resource internals to
web. Two shared tests cover the status mapping; all 183 shared tests, both Android
role compiles and 47 tests in each web browser target pass. EN/FR/AR catalogs
have parity at 610 strings. Physical-device refresh and accessibility remain
acceptance requirements, not inferred from compilation or model tests.

Every city-authorization decision now writes a generic driver-owned notification
and `driver.city_authorization.changed` outbox event in the same transaction as
status, application version and audit. The event contains only authorization ID;
delivery reloads the authorization/profile to derive the user and publishes the
allowlisted `DRIVER_CITY_AUTHORIZATION_CHANGED` push refresh. The mobile relay
causes a complete authenticated restore, and EN/FR/AR inbox copy avoids embedding
possibly stale action/status. Replay adds no rows and an injected failure after
outbox flush rolls everything back. The focused 71-test backend pack, 183 shared
tests and both Android role compiles pass. Provider/device delivery and explicit
human acknowledgment remain operational gaps.

`test_city_authorization_notification_delivery.py` exercises the real migrated
outbox row and processor. A failing push provider produces `DELIVERY_RETRY`,
clears worker lease fields and retains the singular inbox notice. After making
the bounded retry due, a newly constructed processor delivers it and records two
attempts without duplicating source state. The related 27-test focused pack
passes. This is in-process processor-lifetime recovery; a separate-process death
and real-provider drill remains a T5 gate.

The companion OS-process case starts a child using the production outbox
processor, waits until its claim transaction commits, forcibly terminates it,
then starts a distinct replacement process with an immediately stale test lease.
The replacement derives the driver from migrated source records and delivers the
same minimized hint once. Tests assert no database URL in child output and no
user/reason/status in the hint. This validates disconnect plus lease recovery;
it does not substitute for separate deployed services, orchestration metrics or
real-provider/device acceptance.

Scheduling notifications are persisted with the booking transaction and now
enqueue one of five classified push-refresh topics for offer, commitment,
dispatch, fallback matching, or unfulfilled outcomes. The worker reloads the
offer/booking, rejects expired or superseded state, and addresses only the
authoritative driver/passenger. Shared mobile code allowlists those hints and
localizes their persistent inbox copy in English, French, and Arabic. Authorized
polling and inbox history remain the fallback; no scheduled notification is
assignment authority.

A central notification policy is the only source of approved outbox hints. It
defines channels, urgency, maximum delivery age, fallback, quiet-hour eligibility,
and dead-letter ownership. Live and FCM allowlists derive from it, FCM applies a
bounded Android TTL, iOS queue expiration, and informational versus immediate
Android priority, and the worker
consumes expired events before provider access. Unclassified topics raise a fixed
error for bounded retry/dead-letter visibility instead of disappearing as
successful delivery. Live failure does not suppress the push attempt; a partial
failure still retries, so duplicate hints are expected. The worker passes an
absolute deadline derived from durable event creation and capped by offer or
coordination source expiry. FCM recomputes remaining Android TTL before each HTTP
attempt, preserves the absolute APNs deadline and suppresses expired/sub-second
submissions, including after credential refresh. Per-device failures no longer
skip later registrations, but durable per-device retry progress and measured
device-visible expiry remain open in GAP-028.

City configuration activation emits an invalidation hint containing only city
and immutable configuration version. Replicas still load and validate the
authoritative version from PostgreSQL. A paused city prevents new requests and
bookings while allowing active rides, approved support flows, and history to
complete according to documented emergency policy.

The repository-owned matching simulation reuses that pure production scoring
function in a deterministic, seeded synthetic city. It generates demand,
locations, acceptance/decline decisions, cancellations, and driver occupancy,
then emits aggregate timing, outcome, work-distribution, Gini, utilization, and
extreme-case metrics. It has no database or provider access and never emits its
synthetic participant identifiers or coordinates. Policy review should compare
candidate configurations with the same seed; simulation does not replace staged
PostGIS concurrency, routing, or physical-device tests.

Ordinary completed-ride feedback is similarly persisted as a narrow,
passenger-to-assigned-driver `ride_ratings` record. The database enforces one
rating per reviewer and ride plus the 1–5 score range; the API enforces
completion and participant ownership. Ratings do not feed matching, eligibility,
or earnings. Safety reports and support cases must remain separate domains with
their own access rules.

An authenticated passenger or driver can create, list, and retrieve only their
own support tickets. Ride association requires participation. Creation is
rate-limited and idempotent. Restricted support routes add priority, response
deadline, active-administrator assignment, append-only internal/participant
notes, a strict lifecycle, controlled resolution codes, overdue filters, fixed-
field audit, and a 730-day post-closure retention projection. First triage must
include a participant-visible acknowledgement.

Safety is a separate module and table family. A reporter submits only a ride,
controlled category, and description; the backend derives the other participant.
Reporter-facing responses omit description, identities, priority, assignment,
deadlines, retention, and notes. Restricted transitions require a public message
every time and support an audited one-to-one escalation from a ride-linked
support case. `IMMEDIATE_DANGER` receives an urgent five-minute acknowledgement
target; other safety categories receive a high-priority 30-minute target. The
app explicitly says reporting is not an emergency service. Migration
`20260824_0032` owns this schema. City-scoped case authority, durable paging, and
legal-hold-aware retention are added by `0040`–`0042`. The retention processor
erases direct personal links, free text, and notes from due closed cases only
after a locked active-hold check, then records immutable non-content evidence.
Placement/release belongs only to market-scoped platform administrators through
the operations API and requires the implemented recent-MFA step-up. Named legal-
review ownership, pager drills, and backup-expiry proof remain release gates.

Ride-offer and driver-assignment transactions also create durable participant
notification records. The API exposes only the owner's notification history and
read state, while device registration remains provider-neutral. FCM is the
selected background transport. Its adapter receives only the recipient's active
Firebase Installation ID (or a transitional legacy token) plus minimized event metadata; applications always refresh the
backend-authoritative ride resource after receiving a message.

Firebase can issue or rotate its installation ID before a user has authenticated. Each
native client therefore retains only the latest FID in process memory and
retries `POST /devices` after every successful login or session restore,
including driver application states. Android enables FID registration mode and
calls `FirebaseMessaging.register()` after authentication; Android's
`onRegistered` and iOS's `didReceiveRegistration` callbacks supply the current
FID. Registration failure is silent best-effort delivery degradation: it
must never block authentication, rides, or payments, and registration values are not
written to application logs or ordinary local storage.

Android's FCM service and iOS's background remote-notification callback pass
only `type` and `resource_id` into a shared process-local relay. The relay accepts
only the four server-owned ride event types and a canonical UUID, buffers at most
the latest unconsumed hint, and never exposes it as business state. An active
authenticated Compose screen consumes the hint by reloading its complete
backend-authorized product state. Unknown or malformed provider payloads are
ignored without logging them; app startup/session restore remains the recovery
path if a process is terminated before consuming a hint.

The iOS package reference is pinned to Firebase Apple SDK `12.17.0`, rather than
an open `12.x` range. The FID registration API used by the application first
appears in `12.16.0`; its CI compiler gate therefore selects Xcode `26.2`
explicitly. Android shared host tests run in the mobile CI job alongside JVM
tests so the bounded receive relay is continuously verified.

The database gives each Firebase registration kind and identifier one global current owner.
`POST /devices` uses a PostgreSQL conflict update to transfer an installation
atomically across account switches, while ownership-scoped `DELETE /devices`
marks it revoked during normal logout. The shared coordinator serializes
registration and revocation so an in-flight token callback cannot race logout;
push cleanup remains best effort and cannot prevent local credential removal.

Each API registration also stores the authenticated session ID. The conflict
update transfers account and session ownership together. Device deletion is
session-scoped, and `/auth/logout` revokes registrations still bound to that
session in the same database transaction; an older same-account session cannot
erase a newer installation claim.

The local combined process and the standalone production worker start a
lease-based transactional-outbox processor. It claims due events with a worker lease,
reloads current ride/offer records rather than trusting copied recipient data,
and emits only best-effort `RIDE_OFFER_AVAILABLE`, `DRIVER_ASSIGNED`,
`RIDE_CANCELLED`, and `RIDE_UNMATCHED` refresh hints. Delivery attempts use
bounded retry and record a safe outcome code; a
failed hint never rolls back a ride or payment fact. The in-memory connection
hub contains no business state and does not accept commands. Staging and
production publish a versioned, four-field hint through private PostgreSQL
`LISTEN/NOTIFY`; every API process validates it and addresses only the named
user's local sockets. FCM delivery requires environment-provided application default
credentials, bounded retry, invalid-registration revocation, and device validation.

`PostgresLiveEventListener` now observes established connection termination and
probes liveness every 15 seconds with a five-second operation bound. Connection
establishment is bounded to ten seconds; retry waits one second after cleanup.
Registration, removal and graceful close are individually bounded, with hard
termination if close cannot finish. Per-attempt identity guards ignore late old
callbacks. Process shutdown/disconnect cancels cooperative socket dispatch tasks
rather than awaiting stalled sends indefinitely. One listener has one process
owner; readiness clears throughout loss, cleanup and retry and returns only
after successful re-registration. These defaults are not an accepted field SLO.
Hosted API `/ready` checks listener health before and after its SQL probe and
returns the existing sanitized `503 DEPENDENCY_UNAVAILABLE` on either failure.
Local/test processes without the PostgreSQL listener retain SQL-only readiness.
The dedicated migrated integration case terminates only its owned listener PID,
checks replacement `LISTEN` registration and addressed-recipient delivery, then
verifies cleanup. Hosted failover remains separate work under GAP-009/GAP-028.

The final local hop now separates `EventHub` registry/fanout from
`core/live_sessions.py` per-socket ownership and
`domains/auth/session_authority.py` fresh SQL read authority. Token parsing
provides verified mobile IDs and a UTC access deadline without retaining the raw
JWT. REST and socket admission/idle/send paths reject ownership mismatch,
revocation, database-session expiry and suspended users. Every hint rechecks
authority; there is no positive-result cache. Session refresh requires socket
replacement rather than extending the old verified deadline.

Each connection owns one idle monitor, serialized sends, admission and a retained
closer. Closing withdraws broadcast authority before cooperative cancellation;
cancelled callers cannot abandon cleanup. Hub shutdown also joins admitting and
already-closing sessions. Raw ASGI receive handles text/binary/disconnect without
racing the server's close state; no incoming frame has command authority. Known
authority loss closes `4401`, unavailable authority closes `1013`, and fixed logs
omit identity/credentials. Idle/operation defaults are 15/five seconds, with
earlier JWT-deadline wake-up. No database lock spans a network send; a read/send
race cannot recall in-flight bytes. Noncooperative cancellation is reported, not
claimed force-killed. HINT-08 covers the tests and remaining hosted/device/SLO
acceptance, including the increased database/pool demand from active sockets.

The mobile recovery layer now separates one-attempt `LiveEventGateway` transport
from `LiveUpdateSubscription` ownership/retry policy. Both native roots derive
admission from foreground, advisory connectivity and pending security commands.
The authentication coordinator serializes credential operations and exposes only
`LocalSessionLifetime` generation/activity/ending as one atomic value. Persisted
credential replacement cancels the old owner; ordinary REST reads preserve it. Logout closes admission
before push cleanup and prevents a late restore from reopening it. Native callbacks
reject cancelled, obsolete or ineligible REST results before applying state.
The supervisor bounds handshake to ten seconds and each catch-up to fifteen,
requests catch-up on admission/hints/failure/normal closure, and retries expected
failures with 0.5–1-second initial jitter capped at 15–30 seconds. Healthy idle
sockets have no artificial lifetime limit; only useful hints reset flapping
backoff. Cancellation is never a network-retry signal. Shared behavioral tests
and a mutation-tested native source-wiring gate are defined in the HINT-06 pack;
neither proves physical Android/iOS, push-provider or hosted acceptance. The
existing API and business-command non-replay contracts are unchanged.

The 2026-10-02 local mobile slice passed 31 focused new cases within complete
235-test JVM and 186-test Android host suites, both Android debug-root compiles,
57 tests per browser target, 41 mobile script tests with 21 native-wiring
mutations and 197 infrastructure tests. Docs, source credentials, mobile/web
contracts, phase evidence, CI security, production Compose and existing mobile
recovery checks pass. It changes no backend business/schema contract and does
not claim a fresh PostGIS run. Its immutable remote and macOS compile/link checks
remain separate for that mobile slice. Immutable `8f92e51` now passes its push
and PR workflows, including macOS native compile and both Release simulator app
links; it does not execute the blocked native iOS test link or physical devices.
The subsequent server-authority slice has its own fresh 1,090-test full PostGIS
bundle described above and still requires its own immutable CI evidence.
Device, provider and deployment acceptance remain open.

The 2026-10-01 local recovery slice passed 78 focused unit/API cases and the full
1,042-test guarded migrated backend regression with zero failures/errors/skips.
Its named live recovery case is mandatory in the T3 report. The same run verified
zero residual clones, revoked temporary database authority and an 81-table
logical restore with cleanup; all six bounded evidence kinds are present without
phase or deployment acceptance. Infrastructure tests passed 197 and T2 passed
20 personas/60 selected tests. New immutable CI, hosted failover and physical
subscription/session acceptance remain separate from these local results.

The same supervisor owns scheduling handoff and operational-analytics refresh
loops. Analytics takes a transaction-scoped PostgreSQL advisory lock, records
only coarse `CITY_WIDE` eligible/available supply, purges expired supply
snapshots, and refreshes `operational_metric_facts_hourly_v1` from normalized
records. The default cadence is 300 seconds and is bounded to 30–3,600 seconds.
Recomputation through the 730-day retention window incorporates late events and
provides deterministic reconciliation; the materialized view is reporting-only.

`TAXIMOBILE_OUTBOX_MAX_ATTEMPTS` is a required positive deployment setting
(default `8`). A failed event is rescheduled with bounded exponential backoff
until that limit, then marked with `dead_lettered_at` and the fixed
`DELIVERY_DEAD_LETTERED` code. Dead-letter rows are excluded from claims and stay
available for payload-minimized operational inspection. They are never silently
discarded or automatically replayed; an operator must correct the dependency and
explicitly requeue an identified event under the deployment incident process.
The repository command for that action requires 1–100 unique UUIDs, an exact
database host/name confirmation, a bounded incident reference, and an explicit
execution switch. It locks and validates metadata only, refuses the whole batch
if any row is missing, delivered, or not dead-lettered, and never selects payloads
or prints database errors.

The initial multi-instance transport uses private PostgreSQL notifications because
payloads are tiny, best-effort refresh hints and PostGIS is already required.
Redis is introduced only if measured notification or queue throughput outgrows
that design. Either transport is a delivery aid, never the authoritative location
of rides, fares, payments, or permissions.

## 5. Infrastructure and Environments

Local development supports Docker Compose and a Windows workspace-contained
runtime. The portable path downloads checksum-pinned PostgreSQL/PostGIS archives,
keeps binaries, data, logs, and process metadata under `.tools/`, binds only to
IPv4 loopback, reuses ignored generated local secrets, and provides guarded
setup/start/test/stop scripts. Its test command applies the complete migration
chain and runs the HTTP lifecycle against the explicitly isolated
`taximobile_ci` database. An optional checksum-pinned Python 3.12.10 embeddable
runtime installs only the exact hash-verified Windows CPython 3.12 wheels
represented by `requirements.lock`, writes a marker bound to both archive and
lock hashes, and refuses replacement while that interpreter is active. Container
and CI installs also require hashes; Linux consumes the small reviewed
`requirements-linux.lock` supplement for Uvicorn's CPython 3.12 x86_64/aarch64
event-loop wheels. Development/test tooling is separately hash-locked in
`requirements-dev.lock`. This provides local parity with the production
interpreter line but is not a release artifact. Development and tests use the
closed `all` process role so the API and bounded workers may run together in
Compose or directly from the locked Python environment. Staging and production
use separate `api` and `worker` roles from the same image. Configuration is
environment-based; local, staging, and production values are separate.
The production manifest also separates environment capabilities: JWT signing,
public host policy, and routing belong only to the API; Firebase delivery and
poll scheduling belong only to the worker. Database, monitoring, and matching
policy are the deliberately shared inputs.
Development configurations must use isolated databases and sandbox provider
credentials.

Country-scale deployment does not begin with a database or application fork per
city. API replicas remain stateless behind the load balancer, and worker claims
remain database-lease safe. Every operational index/query is reviewed for
`city_id`; city/service/date keys lead the busiest matching, booking, route,
pricing, and aggregate paths. Immutable catalogs/configuration versions may use
bounded cache headers or a shared cache later, while current assignment,
eligibility, booking, fare, payment, and grant state always returns to
PostgreSQL. Read replicas, partitioning, Redis, a queue, and a warehouse require
measured thresholds plus stale-read/failure/restore runbooks.

The operations web bundle is hosted on an exact HTTPS origin separate from the
public API origin where practical. Production response headers include a reviewed
Content Security Policy and no-store for authenticated pages/API responses.
Public fixed-route catalog versions may be cached; driver applications,
operations pages, city drafts, reports, and exports are not shared-cacheable.

Production starts with a small Linux deployment containing one public API
container, one private background-worker container owning matching, outbox,
credential lifecycle, scheduling, analytics refresh, case-alert paging, and
case retention and driver-document retention, one private self-hosted routing service loaded
with versioned Morocco extracts (Valhalla by default or the approved GraphHopper
replacement), managed
PostgreSQL/PostGIS with encrypted backups, a shared private volume containing
only AES-256-GCM driver-document ciphertext, a private ClamAV service and signature
volume, and managed TLS/load balancing or a standard reverse
proxy. PostgreSQL and the selected routing engine are private to application
services. Secrets live in the deployment secret store, never in images, source,
or mobile builds. MapLibre
tile/style configuration is public client configuration but still varies by
environment. FCM credentials, manual-transfer recipient configuration, and any
future payment-provider credentials remain backend/deployment secrets.

`infra/deploy/compose.production.yaml` is the provider-neutral single-host release
template. It requires immutable API and ClamAV image digests and externally supplied
managed PostGIS, a validated routing provider and private URL, Firebase,
host/proxy, JWT, monitoring, and independent driver-document encryption
configuration. API and worker mount the same document volume; ClamAV has no host
port and never receives the encryption key. It never starts migrations as part
of API boot. The API is
loopback-bound for same-host TLS proxying, read-only, capability-free, and fixed
to one Uvicorn worker per container so metrics remain independently scrapeable.
PostgreSQL fanout permits multiple replicas behind a load balancer. The guarded
input validator rejects mutable image tags, loopback production databases,
wildcard hosts/proxies, short or reused secrets, and malformed Firebase IDs.

The API image runs as an unprivileged `taximobile` user and includes a local
health check only; readiness remains the deployment's database-and-listener gate. The
application image does not run migrations automatically in production. A
release pipeline must run `alembic upgrade head` as a controlled pre-rollout
step, then roll out a compatible API image.

`operations/migration_lock.py` now guards all online Alembic execution with a
fail-fast PostgreSQL transaction advisory lock before version reads or schema
changes. The fixed two-integer namespace is stable between releases and scoped
to the connected database. Contention produces a fixed actionable Alembic error;
the free-testing startup path remains fail-closed before opening the public port.
Generated offline SQL includes the equivalent lock check inside its transaction.
Commit, rollback and connection loss release ownership without a stale lock file.
The chain must stay in one transaction; source checks reject known explicit
commit/autocommit/per-migration transaction APIs. Future nontransactional DDL
requires a new reviewed lock lifetime. This does not authorize parallel migration
jobs or remove the need to measure DDL lock/build time under hosted traffic.
Tests include actual upgrade/downgrade subprocess refusal and recovery after a
separate lock-owner process is terminated, not only mocked command return codes.

`operations/migration_limits.py` adds validated transaction-local lock-wait and
statement limits for online Alembic and generated offline SQL. Defaults are 5s
and 300s; configurable bounds are 1–120s and 1–7200s respectively, with statement
greater than lock wait. Zero/invalid configuration is refused before engine
creation without echoing values. Known PostgreSQL lock/statement cancellation
states become fixed actionable Alembic messages. Production Compose exposes the
two timeout variables only to the migration service; API/worker DB limits are
unchanged. Tests exercise a real CLI upgrade blocked by an ordinary writer,
unchanged schema/version after timeout, ownership release, successful retry,
online/offline statement cancellation, setting restoration and invalid CLI
configuration. Outer process/connection/idle deadlines and hosted maintenance
acceptance remain deployment responsibilities.

The modular synthetic workload
entrypoint `operations/passenger_workload.py` uses `operations/workload/` for
configuration, aggregate evidence and real passenger HTTP journeys. It creates
only explicitly confirmed synthetic test accounts, exercises ordinary quote,
request, idempotent replay, restore and cancellation endpoints, and never writes
SQL or uses administrative authority. Its test fixture separately provisions
tariff/eligible driver facts in isolated PostGIS. Per-step and whole-run
deadlines, bounded same-key recovery, admission limits and conservative unresolved
command counts prevent failed runs from being mistaken for success. The actual
CLI/socket test found and fixed dispatch locking the entire nearby candidate
set. Dispatch now rechecks individual ranked candidates under profile locks;
offerless matching rides are retried by the worker within the original matching
deadline. Source/location/provider/field limitations and the executable phases
are in [testing_workloads.md](testing_workloads.md).

`operations/capacity_workload.py` now adds the first open-loop capacity baseline
without changing the journey contract. It pre-admits bounded synthetic passengers,
releases up to 1,000 request/cancel arrivals on an absolute constant-rate schedule,
uses the actor pool as the hard in-flight limit, and reports schedule lag,
backpressure, admission/measurement time and peak concurrency separately from
HTTP latency. A first failed invariant halts new release, while already ambiguous
writes remain subject to conservative same-key recovery and reconciliation. Unit
tests cover bounded/private evidence, saturation, fail-fast release and invalid
controls; an actual child CLI/Uvicorn/fresh-PostGIS test reconciles all four local
arrivals. Sustained/burst mixes, multi-role load, resource telemetry, multiple
replicas, soak and failover remain open under GAP-018.

The capacity runner now also has a strict target-independent profile and
`operations/capacity_plan.py` orchestrator. It requires exactly four ordered
WARMUP/STEADY/BURST/RECOVERY phases, approved-status and evidence-reference
attestations, validates every phase before I/O, and caps the combined plan at
1,000 arrivals and 2,400 seconds. Unknown fields, unsafe files and non-finite or
out-of-range controls fail closed. Aggregate evidence contains a canonical
profile SHA-256 and unexecuted phases but no target origin, city UUID or
coordinates. Unit tests cover profile mutation, bounds, file safety, complete
execution and fail-stop behavior; a real CLI/Uvicorn/PostGIS case executes and
reconciles all four phases. The DRAFT template is not an approved workload.

The profile now binds monitoring cadence and 21 operational thresholds into the
same semantic digest. `operations/workload/monitoring.py` samples 22 fixed,
aggregate-only Prometheus expressions concurrently during each phase and emits
only numeric summaries and closed failure codes. It refuses credentials/paths,
requires HTTPS plus explicit confirmation for nonlocal targets, disables
redirects and environment proxies, bounds responses to 64 KiB, rejects all
series labels and requires one finite value per expression per round. A threshold
breach or missing sample marks the phase incomplete and stops the plan. Unit
coverage includes malformed/labelled/oversized/multiple/non-finite responses,
counter restarts, target guards, all four monitored phases and sampler cleanup;
the local real-HTTP/PostGIS case explicitly declares itself a harness run without
monitoring. `db/metrics.py` adds one five-second-bounded aggregate PostgreSQL
statement over the current database: snapshot availability, connection count and
server limit, active connections, ungranted locks and the database deadlock
counter. Rendering has no database/session/user/query labels; malformed, timed-out
or failed snapshots expose only an availability zero and omit stale values. The
same endpoint adds fixed per-process pool availability, configured size,
checked-in, checked-out and overflow gauges, a cumulative checkout-wait
histogram and timeout counter without caller or connection labels. API and worker
settings now explicitly bound pool size, maximum overflow and checkout timeout;
deployment owners must budget `(size + overflow) * replicas` below PostgreSQL's
connection limit with migration and operator reserve. Eight immutable database/
pool alerts and nine dashboard panels cover snapshot and pool availability,
utilization, checked-out connections, overflow, checkout-wait p95, checkout
timeouts, lock waiters and deadlocks. Unit and real isolated-PostGIS tests cover
the database collector and prove a size-one pool records one bounded timeout
while a connection is held. Host resources, query-plan telemetry and
representative hosted thresholds are intentionally not claimed.

That full regression initially exposed a clone-teardown race rather than a
product assertion failure: the database-owner test role attempted to terminate a
transient superuser auxiliary and received insufficient privilege. The integration
fixture now disables new clone connections, terminates only owner client sessions,
and retries SQLSTATE `55006` while auxiliary work drains; it does not grant
superuser authority. Three repetitions of the exact former failure, the initial
941-test, 952-test, 956-test, 957-test and 970-test reruns, and the current
992-test rerun passed.

`operations/cash_workload.py` extends that evidence with paired driver/passenger
cash journeys. `workload/client.py` is the shared bounded HTTP boundary;
`drivers.py` handles distinct secret-supplied synthetic identities, read-only
preflight, normal location/online commands and run-owned offer discovery;
`cash_journey.py` checks acceptance through completion, idempotent cash settlement,
receipt and exact driver/operator economic conservation. Driver polling reads
do not hold a lease, avoiding synchronized opposite-offer starvation inside
the test harness. Only optional scheduling-version null/absence is normalized
between estimate and receipt; required fields and monetary values remain strict.
The normal backend eligibility and financial authority are unchanged. Real
CLI/socket/PostGIS tests cover three fee modes and two post-commit HTTP failures;
unconfirmed active/financial state stays failed and visible without manufactured
completion, money movement or destructive cleanup. Full hosted, physical,
independent-supply, manual-transfer/refund and provider acceptance remain open.

Each API replica and the separate worker expose authenticated
Prometheus-compatible metrics at `/internal/metrics` on their own operations
surface. The deployment scrapes them individually using the dedicated monitoring
secret and aggregates counters using restart-aware queries. Worker readiness
requires PostgreSQL plus one successful iteration from every fixed loop; the
public API cannot make a non-running worker look healthy.
API-only metric registries omit worker series entirely. The committed alert set
therefore detects both stale worker heartbeats and the disappearance of the
standalone worker scrape target, instead of accepting API-emitted zero series as
false evidence that a worker exists.
Initial alerts should cover new unhandled errors, sustained `5xx` rate, latency
budget violations, readiness failure, and dead-letter growth. Structured request
logs retain the request ID needed to investigate an alert without copying private
data into metric labels. Request and exception logs use the same bounded route
templates as metrics and collapse unknown paths to `_unmatched`, so ride/user IDs
and attacker-controlled paths do not become observability labels or fields.
The request boundary separately detects only the exact configured legacy
administration namespace and records a fixed `served` or `blocked` outcome. It
never labels or logs a blocked raw path. Local/test routed responses are marked
deprecated, a client-source scanner rejects new mobile/web callers, and the
production alert set treats any served legacy route as critical.
Every launcher disables Uvicorn's separate raw access log because the application
already emits one privacy-bounded structured completion event. This prevents
duplicate per-request I/O and avoids reintroducing raw paths outside the reviewed
logging boundary.

Production API and worker processes additionally configure separate
`/var/log/taximobile/events.jsonl` sinks. `SecureRotatingFileHandler` keeps the
active file and rollover chain at mode `0640`; configuration bounds one file to
10 MiB and five backups by default. The Linux image fixes the application owner
at UID/GID `2000`. Production Compose mounts one role-specific named volume into
each process, never a shared API/worker file.

Alloy runs as UID `473` with supplemental group `2000`, mounts both log volumes
read-only, tails `events.jsonl*`, parses event time/level, drops malformed JSON
and lines over 16 KiB, and retains only `service=api|worker` as an index label.
It has no Docker socket, host log path, remote import, public network, or alert-
egress network. Loki runs as UID `10001`, stores TSDB v13 index/chunks/WAL in its
own volume, rejects data older than and queries beyond 30 days, and enables
compactor retention. It has no authentication and therefore remains internal
with loopback-only operator access. The runtime validator uses candidate images
to prove native config parsing, HTTP readiness, Linux volume permissions, two
queryable role streams, and rejection of malformed/oversized fixtures; CI mirrors
the ingestion smoke.

The matching, outbox, credential-lifecycle, scheduling, analytics, case-alert,
and case-retention loops share one cancellation-safe polling
runtime. Every successful or failed iteration updates fixed-name, low-cardinality
metrics; successful iterations also update processed-item counters and a
last-success timestamp. A failed iteration logs only the fixed worker name and
Python exception class before the configured retry delay. Exception messages,
provider responses, event payloads, user/resource IDs, coordinates, and tokens
never enter worker telemetry. Matching/outbox poll intervals are constrained to
0.1–60 seconds and credential polling to 1–300 seconds, so Prometheus can
reliably alert on new iteration errors and on a worker that has not completed an
iteration for five minutes. Analytics polling is separately bounded to 30–3,600
seconds because its materialized-view rebuild is intentionally less frequent.
Case-alert polling is bounded and its HTTPS pager uses a separately configured
token and timeout. Missing configuration means durable alerts remain pending; it
never produces a false delivery. Case-retention polling is bounded to a slower
300–86,400 second interval with a 1–1,000 row batch per case kind; each claim is transaction-
locked and skips active legal holds. Production requires a complete pager URL/token
pair on the worker and the API process receives neither value.

Each authenticated scrape also reads one aggregate outbox snapshot: pending,
dead-lettered, and currently locked row counts plus the oldest pending age. It
never selects payloads, topics, user IDs, ride IDs, or device registrations. A
database/driver failure leaves HTTP process telemetry available but emits only
`taximobile_outbox_metrics_available 0`; it does not publish misleading zero
counts. The deployment verifier requires an available snapshot and all four
gauges, while alerting should treat any dead-letter count, prolonged oldest age,
or unavailable snapshot as an operational incident.

The provider-neutral deployment directory includes Prometheus alerts for those
outbox and worker conditions, unhandled errors, sustained 5xx ratio, the
documented 500 ms p95 latency budget, all four scrape targets, collector line
rejection, Loki write retry/drop failures, and any routed legacy-administration
request. CI validates the required rule structure;
staging must run the selected Prometheus-compatible service's semantic rule
validator and provide a separate `/ready` probe. Alert destinations, named
responders, and escalation timing remain deployment-owner inputs.

The same optional overlay provisions Grafana with internal Prometheus and Loki
datasources plus immutable `TaxiMobile Operations` and `TaxiMobile Logs`
dashboards. It runs as the
image's fixed unprivileged UID with read-only root, a dedicated state volume and
loopback-only UI; its initial administrator password comes from a separate Docker
secret. Anonymous access, signup, telemetry, plugin/update traffic and duplicate
Grafana-managed alerting are disabled. Offline validation rejects unknown/private
query dimensions or panel drift, while the runtime preflight starts disposable
hardened components and fails on readiness, provisioning, ownership, ingestion,
or filter errors. This proves the package starts and preserves its source
boundary, not that real staging series, retention/capacity, backup/restore, or
staff diagnosis are accepted.

Continuous integration provisions an isolated PostGIS service, applies the full
migration chain live, also renders offline migration SQL for review, runs the
backend suite, audits the pinned Python runtime dependencies for known
vulnerabilities, rejects high-confidence committed credential material without
printing values, and builds the production backend image. The credential gate
uses Git-tracked files in CI; its no-Git fallback excludes ignored local secret
files and generated/runtime directories. A separate integrity
job validates every committed Gradle wrapper JAR against Gradle's trusted
checksums; the wrapper also verifies the SHA-256 of the selected Gradle
distribution before execution. Dependabot monitors the Python, Gradle, Actions,
and Docker manifests weekly. Mobile CI runs shared JVM
tests, assembles both debug product flavors, compiles minified unsigned release
variants with explicit non-production HTTPS configuration, and verifies the two
release APK application IDs, variant names, versions, and distinct files. A
macOS job compiles/tests the shared iOS target and builds both Xcode schemes in
Release mode with explicit safe test URLs/versions and the narrowly scoped
unsigned/providerless verification switches. This is the required compiler gate
for Core Location, MapLibre, FCM, APNs entitlements, and release validation; it
does not create distributable archives.

The backend integration gate clones the pristine migrated `taximobile_ci`
template per integration test and drops each clone afterward; the guarded local
entry point grants and always revokes the test role's temporary `CREATEDB`
authority. This prevents administrator/session/catalog state from leaking across
otherwise independent lifecycle evidence. The gate drives one complete cash ride and a second
manual-transfer ride through the
HTTP boundary on migrated PostGIS: account creation and login, driver application
and human approval, vehicle verification, fresh location and availability,
tariff activation, geographic matching, atomic offer acceptance, every ride
transition, fare finalization, pending and settled cash receipts, rating, and
driver earnings. The transfer portion proves capability advertisement, immutable
recipient/reference receipt data, rejection of the cash endpoint, idempotent
passenger submission without completion, forbidden passenger reconciliation,
administrator queue/rejection/retry/verification, and exactly reconciled earnings.
The rating portion also proves that the assigned driver can
read the passenger feedback while an unrelated driver receives `403` and no
reviewer identity is returned. It includes the negative proof that an eligible driver still
cannot go online without a backend-accepted fresh location. The test is guarded
against accidental execution on any database not explicitly named as the isolated
`taximobile_ci` test database.

Required operational behavior before public use:

* Structured logs without credentials, tokens, document contents, or detailed location histories.
* `/health` and readiness checks that do not expose private internals.
* Tested automated database backup and restore procedure.
* Migration applied before application rollout, with a compatible rollback plan.
* Rate limiting for authentication and abuse-prone endpoints.
* A staging environment using non-production provider credentials.

The repository now includes an explicit managed user-testing path at
`infra/deploy/render.staging.yaml`, with its operator runbook in
`infra/deploy/RENDER_STAGING.md`. GitHub stores the private source repository and
triggers deployments; Render hosts the public HTTPS API, isolated worker,
managed PostgreSQL/PostGIS database, and private disk-backed Valhalla service.
The Blueprint cannot be treated as free hosting, does not create preview copies,
and must remain `TAXIMOBILE_ENV=staging`. A guarded entrypoint converts only
Render-generated private connection values into the existing application
configuration formats without logging them or weakening normal startup checks.

For an owner with no staging budget, `infra/deploy/render.free-testing.yaml` is
the deliberately reduced, zero-cost acceptance path. It runs API and workers in
one free Render web process, uses one expiring free PostgreSQL/PostGIS database,
and routes only low-volume synthetic test coordinates through the public
Valhalla fair-use demo with an identifying client header. Sleep/cold starts,
stopped background loops while asleep, no database backups, 30-day expiry, and
public-routing availability are accepted test limitations—not production
architecture. Because the free service has no interactive shell, its startup
accepts owner-supplied Blueprint secrets and invokes the existing first-admin
bootstrap after migrations. The transaction-locked bootstrap is idempotent only
for the same administrator, refuses promotion/replacement, and removes the
plaintext password from the child API environment before serving traffic.
`infra/deploy/RENDER_FREE_TESTING.md` is the controlling runbook.

The production Compose container-health contract now probes `/ready`, not the
weaker liveness endpoint. API health therefore includes PostgreSQL reachability
and supplies the first exact configured allowed host while connecting over
loopback, preserving `TrustedHost` enforcement without breaking the probe;
worker health also requires a running supervisor and at least one successful
iteration from every fixed durable loop. A repository validator rejects drift to
`/health`, public container port bindings, privilege-boundary regressions, or
loss of the read-only/capability hardening before Docker renders the template.

The non-mutating deployment verifier requires explicit target confirmation and
HTTPS for non-loopback hosts. It checks health, database readiness, TaxiMobile v1
identity, and authenticated bounded metrics without submitting business commands.
Rollback keeps the already-applied schema and restores a previous image only when
its reviewed compatibility permits; migrations are never automatically downgraded.

The repository-owned asynchronous performance smoke command sends only bounded
GET requests, enforces explicit p95/error budgets, and emits aggregate JSON. It
refuses non-local targets without an explicit staging confirmation and never
prints bearer tokens, response bodies, or transport exception details. Local
`/health` execution proves the harness and HTTP path work; release capacity still
requires representative authenticated reads, readiness/database load, routing,
and full ride-lifecycle scenarios in an isolated staging environment.

The request audit is a body-agnostic pure ASGI middleware rather than the
compatibility `BaseHTTPMiddleware` wrapper. On the workspace's production-line
Python interpreter, the direct 1,000-request ASGI check at concurrency 20 reached
508 requests/second with 3.01 ms p95, and the Windows loopback check at
concurrency 10 completed 400 requests with zero errors and 192.59 ms p95. The
same workstation's loopback socket path remains unstable above that concurrency
and does not satisfy the 500 ms gate at 20 connections; this is retained as
failed local transport evidence, not presented as production capacity proof.

The adjacent response-security layer is also pure ASGI and body-agnostic. It
marks every response non-cacheable, adds MIME/referrer/frame protections, and
emits HSTS only for production requests whose trusted scheme is HTTPS. Optional
browser CORS remains an exact-origin allowlist, but now covers the documented
`DELETE` method and required `Idempotency-Key` command header as well as the
existing authentication, content-type, and correlation headers.
The private worker operations surface uses the same non-buffering response
protections, while remaining loopback-bound and outside the public API router.

Abuse-rate-limit calls use a deterministic in-memory adapter only in development
and isolated tests. Staging and production automatically use atomic PostgreSQL
buckets shared by every API instance. The stored key is a digest, database time
defines each fixed window, and a database failure returns a safe `503` rather
than granting an unchecked request.

A fresh database is made administrable with the operator-only
`taximobile-bootstrap-admin` command after migrations. Its transaction-level lock
and refusal rules preserve the no-self-assigned-role boundary; it is not a general
administrator-management interface.

The repository supplies guarded local Compose backup and restore scripts under
`infra/scripts/`, now shared by the Compose and portable PostGIS paths. Portable
restore requires an explicit confirmation, creates only a new database with a
guarded `taximobile_restore_` name, and never drops or overwrites a database.
`verify-portable-restore.ps1` independently requires one source migration head,
checks PostGIS, compares privacy-bounded aggregate counts, and runs a no-op
migration using the application role without printing credentials or row data. A
historical live workspace drill restored migration head `20260813_0029`, matched source
aggregate counts for users, rides, payments, driver credentials, cooperatives,
and memberships,
reported PostGIS 3.5, and accepted `alembic upgrade head` through the application
role. Production backups remain the managed database provider's
encrypted, access-controlled responsibility and must be validated with a staging
restore. That historical drill predates the current `20260908_0052` head and must
not be treated as current-head restore acceptance.

Continuous integration runs Python compilation/tests and migration SQL generation,
then the shared JVM test suite and both Android product-flavor Kotlin compiles with
the documented Android API 36 SDK. This keeps backend contracts and both mobile
products from drifting independently.

## 6. Build Order and Quality Gates

Implement in the order in `roadmap.md`. The immediate foundation slice creates the backend project, local PostGIS Compose service, settings/secrets boundary, health endpoints, migration baseline, API error envelope, Kotlin HTTP configuration, secure-storage interface, and CI commands. It must not yet pretend to implement registration, dispatch, maps, payments, or a polished UI.

For every later capability, complete this gate before moving on:

1. Confirm the roadmap phase and read the relevant domain, API, database, security, and design documentation.
2. Define or update the API contract and migration before relying on new state.
3. Implement the backend rule and a focused unit, integration, or API test.
4. Implement the shared mobile repository/use case and UI state; add focused tests where business or presentation state changes.
5. Exercise the real migration and endpoint path against local PostGIS.
6. Check negative authorization, invalid transition, and duplicate-request behavior for sensitive operations.
7. Update documentation only when the delivered design changes a documented contract.

National-expansion slices add these mandatory gates:

1. Prove a caller scoped to City A cannot read, count, export, mutate, or infer
   City B data before adding the positive UI path.
2. Prove a passenger cannot enumerate online drivers through catalogs, matching,
   errors, WebSockets, metrics, or maps.
3. Reconcile passenger total, driver net, operator allocation, and scheduling
   surcharge with exact arithmetic and immutable policy snapshots.
4. Run migration/backfill tests from the current single-city head; never assume a
   fresh national database only.
5. Exercise two-city PostGIS fixtures and concurrent fixed-route/scheduled
   acceptance/handoff behavior.
6. Validate operations web keyboard/RTL/loading/conflict behavior and generated
   OpenAPI compatibility separately from mobile clients.
7. Activate features behind backend city configuration only after the
   corresponding city readiness gate; clients do not contain city allowlists.

No feature is complete because a screen renders, an endpoint returns `200`, or a local cache changed. Completion requires the backend-authoritative behavior, an appropriate test, and the documented failure path.

### UI foundation status

UI polish Wave 1 now has a shared Compose foundation under `feature/ui`: the
approved navy/mustard/feedback palette, spacing and radius scales, motion constants,
Sora/Manrope/IBM Plex Mono typography, and the full approved component catalog:
button, text field, sheet, status pill, fare block, passenger-safe driver card,
offer card, map FAB, toast banner, confirmation dialog, skeleton, and segmented
control. The extended foundation adds specialized email, Moroccan-phone,
password, numeric, OTP, and star-rating controls; reusable cards; a cash
and manual-transfer payment-method card; and deterministic code-drawn brand, empty-state, and vehicle
placeholders. Optional raster assets are enhancements rather than screen
dependencies. Session restoration and account creation use a dedicated dark progress
surface; signed-out and offline states use the light product chrome and shared
controls. Registration validation and all backend-authoritative state transitions
are unchanged. The bundled font binaries come from the upstream Google Fonts
repositories and their OFL license texts ship beside the resources.

The first passenger Wave 2 slice is also implemented: `PassengerReady` renders a
full-screen MapLibre surface, draggable peek/half/expanded sheet, map-selected
pickup/destination flow, one-shot location FAB, backend fare estimate and route,
backend-confirmed active-ride/driver status, explicit cancellation confirmation,
final receipt/payment facts, account/support/history, and inbox access. It does
not render fake nearby cars or treat route, push, fare, cash, or payment display as
authority. Map tap, one-shot location, and the provider-neutral place-search
picker are the production place-selection controls; exact editable coordinate fields are compiled into Android/iOS debug
presentation by default, with localized selected/unselected summaries retained in
release UI. A native map-style failure promotes the fields in release as the
required non-map fallback. Search is city-focused, debounced and explicitly
retryable; results distinguish address/street/locality/landmark, expose provider
attribution, and disable an outside-area result when pickup is selected. A
settled map point has an explicit reverse-address action; the returned label never
replaces its authoritative coordinate. Disabled/provider-failure/no-match states
retain map/manual selection. Search results remain selectable only while their
city and normalized query match the visible input; query edits hide old or late
responses immediately. A reverse request captures its city/target/coordinate,
and completion labels only that still-selected point without moving coordinates
or displaying stale guidance after a city/point change or a live ride starts.
Saved-place labels remain deferred. The remaining UI test/screenshot matrix
is a later validation slice scheduled in `ui.md`.

The account surface also presents a visually separate safety section for
passenger and driver roles. It can bind a report to the active, selected, or
recent authorized ride, cycles only through the backend category vocabulary,
shows reporter-safe status/public messages, and cannot submit without a ride and
description. English, French, and Arabic carry the same emergency-service
warning. Internal notes and reported-user identity have no mobile model fields.

The Android and iOS MapLibre surfaces now share deterministic camera-focus
rules: a backend route takes priority, otherwise selected endpoints are framed,
and an empty map returns to the documented Casablanca context center. Geometry
changes refocus automatically and both role homes expose an accessible explicit
recenter action. Native route layers use the approved 5 dp `navy.900` stroke
over a white halo, with a mustard pickup, navy destination, and navy/mustard
driver marker. Camera focus is presentation only and cannot alter selected coordinates
or backend route facts.

The first driver Wave 3 slice is implemented on the same full-screen MapLibre and
shared-sheet foundation. It presents explicit offline/online text status, checks
for a selected verified active vehicle and submitted location before enabling the
local Go Online intent, focuses one backend offer, exposes only the next valid ride
intent, requires reviewed completion coordinates, and separates cash-received
confirmation from ride completion. Destructive decline, cancellation, and cash
settlement intents require confirmation; the backend remains authoritative for
eligibility and every transition. Earnings render only server-provided gross, fee,
adjustment, and net values. The driver account also presents the API's complete
filtered settlement count, settled-through timestamp, and bounded recent earning
rows; it never derives these from ride history.

The offer API supplies `server_time`, `issued_at`, and `expires_at`. The driver UI
derives an honest total and initial remaining duration from those server values,
then advances the countdown with process-monotonic elapsed seconds. At zero it
disables Accept and requests an authoritative refresh; it never mutates offer,
availability, or matching state locally. Invalid or non-positive timing also
disables Accept, presents a localized timing-unavailable state, and requests one
authoritative refresh; it never falls back to device wall time or treats a raw
expiry string as sufficient acceptance evidence. Physical-device
screenshots and accessibility automation remain validation gates. A newly
focused offer also emits one platform-managed haptic per offer identity; it uses
Compose's action-oriented haptic path so operating-system settings and device
capability remain authoritative rather than requiring vibration permission or a
custom waveform.

Critical shared UI semantics now run on the supported JVM Compose UI test
harness. They cover switching from login to registration with a disabled invalid
submit, completing the valid form and dispatching its trimmed identity plus
unchanged password without inventing an absent optional phone number, offline
retry intent dispatch, retained loaded content under a sticky connectivity
warning, backend-assigned passenger driver/status
rendering, production hiding of editable raw passenger coordinates, pending cash
never appearing paid, explicit driver cash-settlement confirmation, expired-offer
accept disabling plus refresh, and the driver readiness gate that disables Go
Online without a verified selected vehicle and submitted location. Stable test tags are limited to
mutation controls where repeated visible labels would make semantic selection
ambiguous. Shared status pills are polite accessibility live regions, and
informational/error banners announce politely/assertively respectively, so
backend-confirmed ride, availability, payment, and error changes are not exposed
only as color or silent text replacement. The shared sheet also reads the system
font scale: a requested peek is promoted to half at `1.3×`, and any compact state
is promoted to expanded at `1.6×`, while explicit expansion is preserved. Pure
policy tests and a Compose height test lock this behavior for passenger and driver
because both products use the same `TaxiSheet`. Passenger Account/Inbox and driver
Account/Inbox also retain the active ride's backend-derived live status pill above
their secondary content; focused Compose tests cover both products. This desktop semantics coverage does
not replace Android/iOS physical-device screenshots, platform accessibility
services, permission dialogs, or MapLibre native rendering acceptance.

Android passenger and driver builds now package role-specific adaptive and
legacy launcher resources around the shared flat taxi mark. The driver variant
adds the approved wheel badge while both use the fixed navy background. Android
12 and newer use the role launcher inside a `navy.950` system splash; earlier
versions use the same navy starting theme. `verifyRoleLauncherAssets`, attached
to `preBuild`, rejects missing role resources, unapproved background color,
identical role foregrounds, or loss of the starting theme. Physical-device icon
mask and splash screenshots remain a release acceptance gate.

iOS mirrors that role distinction with separate `AppIcon` and `DriverAppIcon`
catalogs generated from the same repository-owned flat taxi geometry; the
driver catalog adds the wheel badge. The shared `UILaunchScreen` uses the
`LaunchBackground` asset fixed to `navy.950`. The portable
`verify_ios_role_assets.py` gate validates catalog declarations, opaque RGB
1024-pixel source images, target-to-catalog assignment, role distinction, and
the launch color before macOS CI compiles both Xcode targets. Device icon masks
and launch capture remain release acceptance checks.

Later UI work should consume these tokens rather than add feature-local colors,
spacing, shapes, or default platform typography.

The original Compose starter greeting/platform probes and duplicate legacy ride
models have been removed. They had no product references and are not alternative
domain contracts; all ride and platform behavior now lives under the documented
TaxiMobile packages.

Handwritten mobile and operations-web API calls now have repository-level drift
gates. They read actual Ktor call sites, accept only versioned literal endpoint
fragments plus reviewed identifiers and finite fail-closed transitions, and
compare every expanded HTTP method/path with FastAPI's generated OpenAPI
document. The mobile live-event WebSocket is checked directly against registered
FastAPI routes. Operations gateways share `OperationsApiEndpoints`, which
requires an HTTP(S) base ending in exactly one `/api/v1` and rejects absolute,
query-bearing, fragmented, or empty-segment route input. This removed duplicate
version-prefix construction from the control-plane and payment modules.

Unknown calls, arbitrary runtime routes, and unreviewed action selectors fail
closed so a new gateway cannot silently bypass coverage. Both gates run in
backend CI and before the portable migrated-database suite; payload-schema and
authorization behavior remain covered by focused Kotlin and backend API tests.

Promotion evidence now has a separate executable control under `infra/testing/`.
Its closed T0–T10 catalog defines environment/population boundaries, exact
evidence classes, approval functions and P0 prerequisites. The standard-library
validator requires one clean hash-addressed candidate, ordered predecessor
acceptance, controlled evidence references, defect disposition and all GAP-001–
GAP-019 closure references before T8. It refuses public users before T9, live
money before T8, real-user evidence before T8 and intentional failure injection
in field/user phases. CI validates the catalog and deliberately empty template;
only authorized people verifying retained external evidence can accept a phase.

The release lifecycle now has an executable source boundary. Android passenger,
Android driver, iOS passenger, iOS driver, applicant web and operations web each
send a strict numeric version and positive build under a closed surface header.
Production-like settings require a complete minimum/recommended map for all six
surfaces and cannot disable compatibility enforcement. The command-free
preflight runs before mobile session restoration and before either web workspace;
mobile renders localized mandatory-upgrade/retry states and web renders branded
reload/retry states. The same backend policy still rejects every ordinary v1
request and live-event connection, so bypassing the presentation cannot bypass
enforcement. Release web packaging and Android/iOS release guards validate the
metadata shape. This advances GAP-036 in source; approved support windows,
distribution channels, signed obsolete/current artifacts and a hosted policy
raise/rollback drill remain external T4/T5 evidence.

Shared presentation copy is now externalized into exact-parity English, French,
and Arabic Compose catalogs. `UiMessage` keeps resource identity and substitution
arguments in coordinator/authentication state so network and business state do
not freeze an English sentence before rendering. The application root derives
layout direction from the active platform locale, and JVM UI tests exercise both
French resource selection and Arabic right-to-left control order. Known durable
notification event types are also rendered from the local catalog; the server's
bounded title/body remain a compatibility fallback for an unknown future event.
`scripts/validate_localization.py`, included in the existing Python CI discovery,
requires catalog key and placeholder parity and scans the covered presentation
sources for newly embedded static copy. Valhalla-generated street narration is
provider content rather than application copy. Mobile route requests now send a
closed `ar`/`en`/`fr` platform-language value through the normalized backend
contract; Valhalla receives `fr-FR` or `en-US`. Because the pinned Valhalla
narration catalog does not support Arabic, Arabic requests retain valid geometry
but currently receive English provider narration. Arabic-capable spoken guidance
therefore remains a route-provider acceptance gate, not a completed claim.

## 7. Selected and Deferred Integrations

The selected integrations are MapLibre Native for map rendering, self-hosted
Valhalla for routing, FCM for background push, explicit cash settlement, and
external bank/M-Wallet transfer with manual reconciliation. They remain behind
narrow integration interfaces.
GraphHopper is the approved routing fallback behind the same normalized backend
contract. Both server adapters are implemented; Valhalla remains the default and
mobile clients never select or call a routing engine directly. Deployment accepts
only `valhalla` or `graphhopper` and must pair that choice with the corresponding
private base URL and accepted Morocco graph artifact.

Still deferred are the production MapLibre tile/style source, acceptance and
operation of a production geocoding deployment/data license,
CMI and every card-provider merchant protocol/credential, Firebase project
credentials/APNs configuration, SMS provider, hosting provider, Redis, task queue,
and microservice extraction. CMI is deferred until well after the functional
cash/transfer launch and must not be represented by a simulator or fake success.
Do not invent missing provider contracts or add infrastructure until the
corresponding operational input exists.

The geocoding source boundary itself is implemented. The backend exposes
authenticated `GET /places/search` and `GET /places/reverse`, normalizes an
approved Nominatim-compatible response, applies independent per-account limits,
and uses the active versioned PostGIS city polygon for pickup serviceability.
`TAXIMOBILE_GEOCODING_PROVIDER=disabled` is the default; selecting `nominatim`
requires a base URL, timeout and identifying user agent. Hosted environments
require HTTPS and reject `nominatim.openstreetmap.org`. This is source closure,
not provider, license, coverage, capacity, privacy, or field acceptance.

Migration `20260820_0030` adds `MANUAL_TRANSFER`, immutable recipient snapshots,
and append-oriented transfer claims. The estimate endpoint advertises only methods
available from fail-closed backend settings; ride creation stores the selected
method. Completion creates a pending payment. Passenger submission changes it to
processing only, while isolated administrative verify/reject routes own statement
reconciliation. Verification and driver-earning creation share one locked,
idempotent, audited transaction. Mobile renders the returned instructions and
authoritative pending/processing/completed states without collecting financial
credentials or images.

Migration `20260824_0031` adds append-only `payment_refunds` with closed reason
and settlement-method enums, unique evidence, positive-money and launch-funding
constraints, and administrator/payment ownership. The administrator create
command locks the completed payment, totals earlier refunds, rejects duplicate or
excess evidence, records audit and idempotency state in the same transaction, and
marks only a fully exhausted payment `REFUNDED`. The passenger receipt exposes
safe refund totals/items while retaining the original fare. Shared mobile UI
localizes reason/status presentation. Launch refunds are fully operator-funded;
driver earnings remain immutable until the later city economics phase defines a
separate driver-adjustment authority.

Migration `20260831_0044` replaces deployment-wide payment selection for every
non-legacy city with versioned city/operator/service capabilities and verified
recipient accounts. An active city-configuration service must reference the exact
active/effective capability; estimate and ride creation resolve it independently
and fail closed on any mismatch. Ride, payment, and refund facts retain explicit
city/operator provenance, while ride/payment rows also retain capability and
recipient provenance. The four manual-transfer environment variables remain only
as a disabled-by-default compatibility fallback for the deterministic legacy
city. Cash remains mandatory in every capability.

The operations application includes a payment module for recipient and
capability lifecycle commands, scoped manual-transfer reconciliation, and the
append-only refund ledger. Configuration requires
`MANAGE_PAYMENT_CAPABILITIES`; settlement requires `RECONCILE_PAYMENTS`.
Recipient verification/retirement, capability activation, and refund recording
require recent operations MFA as applicable, and all mutations preserve backend
scope, optimistic concurrency, idempotency, and audit authority.

FCM and Crashlytics remain because Firebase lists both as no-cost Spark-plan
products. This implementation does not use Firestore, Realtime Database, Cloud
Functions, Storage, Hosting, phone authentication, or Firebase Analytics. Adding
one requires a separate cost/privacy/architecture decision; push failure never
blocks WebSocket refresh or authoritative API behavior.
