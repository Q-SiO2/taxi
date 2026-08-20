# Implementation Blueprint

This document fixes the implementation choices required to turn the TaxiMobile product documents into working software. It is subordinate to the domain rules in `product.md`, `auth.md`, `rides.md`, `matching.md`, `pricing.md`, and `payments.md`. If a technical choice conflicts with one of those rules, the domain rule wins and the conflict must be resolved in documentation first.

## 1. Repository Structure

TaxiMobile remains one repository with four deliberate top-level areas:

```text
Projects/
|- TaxiMobile/                 # Kotlin Multiplatform passenger and driver clients
|- backend/                    # Python modular-monolith API, worker, migrations, tests
|- infra/                      # local Compose and deployment configuration
`- docs/                       # authoritative product and technical decisions
```

`TaxiMobile/` is retained as the mobile build root. `backend/` and `infra/` are separate because Python and deployment tooling must not be coupled into the Kotlin build. Generated files, local databases, credentials, and build output are never committed.

## 2. Mobile Clients

The product has two mobile applications with different operational roles:

* **Passenger** requests and follows rides.
* **Driver** manages eligibility, availability, ride offers, and active rides.

They share one Kotlin Multiplatform codebase. Android starts with two product flavors in `TaxiMobile/androidApp`; iOS starts with two targets/schemes that embed the same shared framework. This produces separate installable apps without duplicating business or API code. Desktop and web targets are retained only as development and UI-test surfaces until a product decision promotes either to a supported client.

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
engine and an iOS Keychain token store. Its Swift shell reads the app role and
API base URL from target build settings, keeping production URLs and role choice
out of shared Kotlin code. The checked-in default URL is deliberately invalid;
an iOS release must inject a TLS URL through protected configuration.

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
omits numbers and all document/storage references. Secure upload, encrypted
document storage, retention, and administrator verification remain policy-gated.
Driver verification reads and submissions also return the authoritative optional
`submitted_at` timestamp documented by the API instead of making the client infer
it from local state.
Android and iOS load credential metadata through the shared driver gateway and
render it only in the private driver account sheet.
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
an explicit one-shot lookup. iOS uses Core Location with when-in-use authorization
and `requestLocation`. Neither app requests background location or subscribes to
continuous updates in this phase. A denial, timeout, or disabled provider returns
control to the shared UI without submitting a coordinate; map-tap and validated
manual entry remain available. Passenger pickup, driver operational updates, and
ride completion each require a separate user action before backend submission.
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

The shared mobile `RideGateway` exposes fare estimation as a backend call. A client may render the returned amount and tariff version, but it does not calculate, select, or lock the authoritative fare; the API locks the quote when the passenger creates the ride.

## 4. Real-Time and Background Work

The API writes the business transaction first. Beginning with ride offers and notifications, it writes an outbox record in that same transaction. A worker delivers the resulting WebSocket and push notifications, retries safely, and records delivery outcomes. A failed notification never rolls back a ride or payment fact.

The MVP persists `ride.offer.created` and `ride.accepted` events in an
`outbox_events` table in the same transaction as their source state changes.
The records deliberately carry only IDs; the delivery worker authorizes and
loads current notification data rather than trusting a copied business payload.

Matching runs as a separate authoritative background processor alongside the
non-authoritative delivery worker. The ranked MVP filters eligibility in
PostGIS, takes a bounded nearest candidate set, and applies versioned configurable
proximity, uninterrupted idle-time, and recent-assignment fairness weights. New
offers persist distance, ETA, component scores, recent assignment count, and the
algorithm version. Decline and expiry preserve the driver's waiting timestamp,
exclude already-tried drivers for that ride, and advance sequentially. The
processor claims expired offers with row locks and `SKIP LOCKED`, so horizontal
replicas cannot both expire the same offer. Candidate exhaustion records
`UNMATCHED`; it never leaves the passenger in an indefinite matching state.

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

The support-ticket MVP allows an authenticated passenger or driver to create,
list, and retrieve only their own tickets. A ticket can link to a ride only when
the caller participated in it. Support text is not logged, and ticket creation
is rate-limited. Administrative triage and safety-response workflows are
deliberately deferred because they require documented operational authority,
not just a database status field.

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

Production starts with a small Linux deployment containing one public API
container, one private background-worker container owning matching, outbox, and
credential lifecycle, one private self-hosted routing service loaded
with versioned Morocco extracts (Valhalla by default or the approved GraphHopper
replacement), managed
PostgreSQL/PostGIS with encrypted backups, object storage only when verified driver
documents are implemented, and managed TLS/load balancing or a standard reverse
proxy. PostgreSQL and the selected routing engine are private to application
services. Secrets live in the deployment secret store, never in images, source,
or mobile builds. MapLibre
tile/style configuration is public client configuration but still varies by
environment. CMI and FCM credentials remain backend/deployment secrets.

`infra/deploy/compose.production.yaml` is the provider-neutral single-host release
template. It requires an immutable API image digest and externally supplied
managed PostGIS, a validated routing provider and private URL, Firebase,
host/proxy, JWT, and monitoring configuration. It never starts migrations as part
of API boot. The API is
loopback-bound for same-host TLS proxying, read-only, capability-free, and fixed
to one Uvicorn worker per container so metrics remain independently scrapeable.
PostgreSQL fanout permits multiple replicas behind a load balancer. The guarded
input validator rejects mutable image tags, loopback production databases,
wildcard hosts/proxies, short or reused secrets, and malformed Firebase IDs.

The API image runs as an unprivileged `taximobile` user and includes a local
health check only; readiness remains the deployment's database-aware gate. The
application image does not run migrations automatically in production. A
release pipeline must run `alembic upgrade head` as a controlled pre-rollout
step, then roll out a compatible API image.

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
Every launcher disables Uvicorn's separate raw access log because the application
already emits one privacy-bounded structured completion event. This prevents
duplicate per-request I/O and avoids reintroducing raw paths outside the reviewed
logging boundary.

The matching, outbox, and credential-lifecycle loops share one cancellation-safe polling
runtime. Every successful or failed iteration updates fixed-name, low-cardinality
metrics; successful iterations also update processed-item counters and a
last-success timestamp. A failed iteration logs only the fixed worker name and
Python exception class before the configured retry delay. Exception messages,
provider responses, event payloads, user/resource IDs, coordinates, and tokens
never enter worker telemetry. Matching/outbox poll intervals are constrained to
0.1–60 seconds and credential polling to 1–300 seconds, so Prometheus can
reliably alert on new iteration errors and on a worker that has not completed an
iteration for five minutes.

Each authenticated scrape also reads one aggregate outbox snapshot: pending,
dead-lettered, and currently locked row counts plus the oldest pending age. It
never selects payloads, topics, user IDs, ride IDs, or device registrations. A
database/driver failure leaves HTTP process telemetry available but emits only
`taximobile_outbox_metrics_available 0`; it does not publish misleading zero
counts. The deployment verifier requires an available snapshot and all four
gauges, while alerting should treat any dead-letter count, prolonged oldest age,
or unavailable snapshot as an operational incident.

The provider-neutral deployment directory includes initial Prometheus alert
rules for those outbox and worker conditions, unhandled errors, sustained 5xx ratio, and the
documented 500 ms p95 latency budget. CI validates the required rule structure;
staging must run the selected Prometheus-compatible service's semantic rule
validator and provide a separate `/ready` probe. Alert destinations, named
responders, and escalation timing remain deployment-owner inputs.

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

The backend integration gate drives one complete cash-ride lifecycle through the
HTTP boundary on migrated PostGIS: account creation and login, driver application
and human approval, vehicle verification, fresh location and availability,
tariff activation, geographic matching, atomic offer acceptance, every ride
transition, fare finalization, pending and settled cash receipts, rating, and
driver earnings. The rating portion also proves that the assigned driver can
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
live workspace drill restored migration head `20260813_0029`, matched source
aggregate counts for users, rides, payments, driver credentials, cooperatives,
and memberships,
reported PostGIS 3.5, and accepted `alembic upgrade head` through the application
role. Production backups remain the managed database provider's
encrypted, access-controlled responsibility and must be validated with a staging
restore.

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

No feature is complete because a screen renders, an endpoint returns `200`, or a local cache changed. Completion requires the backend-authoritative behavior, an appropriate test, and the documented failure path.

### UI foundation status

UI polish Wave 1 now has a shared Compose foundation under `feature/ui`: the
approved navy/mustard/feedback palette, spacing and radius scales, motion constants,
Sora/Manrope/IBM Plex Mono typography, and the full approved component catalog:
button, text field, sheet, status pill, fare block, passenger-safe driver card,
offer card, map FAB, toast banner, confirmation dialog, skeleton, and segmented
control. The extended foundation adds specialized email, Moroccan-phone,
password, numeric, OTP, and star-rating controls; reusable cards; a cash
payment-method card; and deterministic code-drawn brand, empty-state, and vehicle
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
authority. Map tap and one-shot location are the production place-selection
controls; exact editable coordinate fields are compiled into Android/iOS debug
presentation by default, with localized selected/unselected summaries retained in
release UI. A native map-style failure promotes the fields in release as the
required non-map fallback. A future geocoding/place-search adapter may replace those summaries
without changing the coordinate contract. The remaining UI test/screenshot matrix
is a later validation slice scheduled in `ui.md`.

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

Handwritten mobile API calls now have a repository-level drift gate. It reads the
actual Ktor gateway call sites, accepts only versioned literal endpoint fragments
plus reviewed identifier/driver-transition interpolation, and compares every
expanded HTTP method/path with FastAPI's generated OpenAPI document. The
live-event WebSocket is checked directly against registered FastAPI routes.
Unknown call shapes fail closed so adding a gateway cannot accidentally bypass
coverage. The gate runs in backend CI and before the portable migrated-database
suite; payload schema behavior remains covered by focused Kotlin and backend API
tests.

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
Valhalla for routing, CMI hosted checkout for cards, FCM for background push, and
the existing explicit cash flow. They remain behind narrow integration interfaces.
GraphHopper is the approved routing fallback behind the same normalized backend
contract. Both server adapters are implemented; Valhalla remains the default and
mobile clients never select or call a routing engine directly. Deployment accepts
only `valhalla` or `graphhopper` and must pair that choice with the corresponding
private base URL and accepted Morocco graph artifact.

Still deferred are the production MapLibre tile/style source, geocoding provider,
CMI merchant-specific protocol and credentials, Firebase project credentials/APNs
configuration, SMS provider, hosting provider, Redis, task queue, and microservice
extraction. Do not invent missing provider contracts or add infrastructure until
the corresponding operational input exists.
