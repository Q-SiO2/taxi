# TaxiMobile — System Architecture

## 1. Purpose

This document defines the technical architecture of TaxiMobile.

**Current standing (2026-09-07):** the provider-independent architecture is
implemented as a Kotlin Multiplatform client suite, Compose web surfaces,
FastAPI modular monolith, PostGIS database, and separate worker role. Production
provider, hosting, capacity, device, and operational acceptance remain open; see
[`gaps.md`](gaps.md).

TaxiMobile is a cooperative taxi ride-hailing platform consisting of:

* A passenger mobile application.
* A driver mobile application.
* A public driver-application and protected national operations web platform.
* A backend API.
* A PostgreSQL database with geographic capabilities.
* Real-time communication infrastructure.
* Mapping and routing services.
* Payment infrastructure.
* Cooperative administration tools.

The architecture should prioritize:

* Reliability.
* Security.
* Maintainability.
* Privacy.
* Low operating cost.
* Platform independence.
* Cooperative ownership of data.
* The ability to scale from a small initial deployment to multiple cities.

---

# 2. High-Level Architecture

The system is divided into five major layers:

```text
┌─────────────────────────────────────────────┐
│                  CLIENTS                    │
│                                             │
│  Passenger App       Driver App             │
│  Driver Web Portal   Operations Console     │
│       │                   │                 │
└───────┼───────────────────┼─────────────────┘
        │                   │
        │ HTTPS             │ HTTPS
        ▼                   ▼
┌─────────────────────────────────────────────┐
│                BACKEND API                  │
│                                             │
│              FastAPI / Python               │
│                                             │
│ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐│
│ │ Auth   │ │ Rides  │ │Drivers │ │Payments││
│ └────────┘ └────────┘ └────────┘ └────────┘│
│                                             │
└──────────────────────┬──────────────────────┘
                       │
             ┌─────────┴─────────┐
             │                   │
             ▼                   ▼
┌────────────────────┐  ┌────────────────────┐
│     PostgreSQL     │  │  Real-Time Layer   │
│                    │  │                    │
│      PostGIS       │  │ WebSockets / etc.  │
└────────────────────┘  └────────────────────┘
             │
             │
             ▼
┌─────────────────────────────────────────────┐
│             EXTERNAL SERVICES               │
│                                             │
│ Maps / Routing / Geocoding                  │
│ Payment Provider                            │
│ Push Notifications                          │
│ SMS / Email                                 │
└─────────────────────────────────────────────┘
```

The mobile applications should never communicate directly with the database.

All application data access should go through the backend API.

---

# 3. Mobile Application

## 3.1 Technology

The mobile application will use:

* Kotlin.
* Kotlin Multiplatform.
* Compose Multiplatform.

The project currently contains:

```text
shared/
androidApp/
iosApp/
desktopApp/
webApp/
```

The passenger-service production targets are:

* Android.
* iOS.

Desktop and web targets may remain available for development or future applications but are not initial production targets.

The approved national expansion promotes the existing `webApp` module to a
separate operations application. Phase 12 replaced the mobile root with a
dedicated protected console shell, and Phase 13 delivered the separate public
driver-application route group. The web application never receives business authority
from browser state. It reuses approved design tokens and narrow shared value
types without coupling mobile navigation to desktop administration.

---

# 4. Shared Mobile Architecture

The majority of application logic should reside in:

```text
shared/src/commonMain/
```

The shared layer should contain:

* UI components where practical.
* Screens.
* Navigation abstractions.
* Data models.
* Repository interfaces.
* API clients.
* Authentication state.
* Ride state.
* Driver state.
* Business logic.
* Validation.
* Localization abstractions.

Platform-specific functionality should be implemented in:

```text
shared/src/androidMain/
shared/src/iosMain/
```

when common code cannot provide the required functionality.

Examples of potentially platform-specific functionality include:

* Push notifications.
* Location services.
* Secure credential storage.
* Maps SDK integration.
* Biometric authentication.
* Platform-specific permissions.

Foreground location adapters are one-shot and admit only one active request per
application. A shared admission gate prevents repeated UI taps from replacing an
active platform callback; the shared UI owns loading/disabled presentation. This
does not authorize or submit a coordinate—the backend-facing action remains
separate and authoritative.

The driver roots also use a pure shared foreground scheduler after backend-
confirmed online entry. Lifecycle, connectivity, availability, platform-request
and app-action inputs gate every attempt. It requests only through an already-
authorized no-prompt path, gives normal commands priority, uses a bounded failure
backoff, and stops outside foreground operational states. Android and iOS still
declare no background-location capability.

---

# 5. Mobile Internal Architecture

The mobile application should use a layered architecture.

Conceptually:

```text
UI
 │
 ▼
ViewModel / Presentation State
 │
 ▼
Use Cases / Business Logic
 │
 ▼
Repositories
 │
 ▼
Data Sources
 │
 ├── REST API
 ├── WebSocket
 └── Local Storage
```

The selected mobile and backend implementation stack is defined in `implementation.md`; responsibilities remain separated as the implementation evolves.

UI components should not directly perform network requests.

---

# 6. Backend

## 6.1 Chosen Technology

The initial backend will use:

* Python 3.12 or later.
* FastAPI and Pydantic for the HTTP and WebSocket boundary.
* SQLAlchemy 2.x with asyncpg for PostgreSQL access.
* Alembic for the only supported schema-migration path.
* PostgreSQL 16 or later with PostGIS 3.4 or later.

The backend is responsible for:

* Authentication.
* Authorization.
* Driver verification.
* Passenger accounts.
* Ride management.
* Driver availability.
* Dispatching.
* Pricing rules.
* Payments.
* Notifications.
* Ride history.
* Cooperative administration.
* Market, operator, city, and service-area configuration.
* Fixed-route publication and scheduled-booking policy.
* City-scoped tariffs, scheduling surcharges, and operator fee policies.
* Purpose-limited operational aggregation and rollout evidence.
* Data protection.
* Audit logging.

---

# 7. Backend Architecture

The first backend is a **modular monolith**, not a collection of deployable microservices. It is one API process, one database, and--only when asynchronous delivery is required--one worker process built from the same codebase. Domain boundaries are enforced in code so that a later extraction is possible only if measured operational needs justify it.

The required structure is:

```text
backend/
├── app/
│   ├── auth/
│   ├── users/
│   ├── drivers/
│   ├── vehicles/
│   ├── rides/
│   ├── dispatch/
│   ├── payments/
│   ├── maps/
│   ├── notifications/
│   ├── cooperative/
│   ├── operations/
│   ├── cities/
│   ├── fixed_routes/
│   ├── scheduling/
│   ├── analytics/
│   └── administration/
│
├── database/
├── core/
├── tests/
└── main.py
```

The detailed required structure is defined in `implementation.md`; the diagram above is retained only as a domain map. New code must use the required structure there.

## 7.1 National control plane and city-scoped data plane

The protected operations console is a control plane. It creates and activates
versioned city/operator configuration, reviews scoped applications, and reads
authorized aggregates. Immediate rides, matching, bookings, fares, and payments
form the data plane. Both initially remain modules in the same backend and
PostgreSQL database; this boundary does not justify premature microservices.

Every data-plane request resolves one authoritative city and operator assignment.
Every control-plane mutation carries an explicit permission and scope check,
configuration version, and audit record. City activation publishes one coherent
configuration bundle so API replicas and workers never select an arbitrary mix
of old tariff, fee, matching, route, or scheduling rules.

The public driver portal and protected console may share a web deployment, but
their route trees, session requirements, API permissions, and response data are
separate. The console uses an exact configured browser origin, strengthened
administrative authentication, and backend-enforced scope. It does not connect
to the database, payment provider, or document store directly.

This boundary is implemented inside the existing modular monolith through
the `markets` and `administration` domains. It includes isolated operations-token
audience/session validation, SQL scope-before-pagination filtering, audited
configuration commands, and the compatibility Casablanca control-plane records.
Migration `20260830_0043` adds password-to-TOTP challenges, encrypted factors,
single-use recovery, counter replay prevention, recent-MFA step-up, rotating
secure refresh cookies, and CSRF binding. Password-only/JSON refresh remains
explicit local/test compatibility and is rejected by production configuration.
The same environment boundary applies to the older global `/admin` routers:
they are included only by the v1 router factory when the local/test compatibility
switch is enabled. Staging and production configuration reject enablement and
expose only scoped `/operations` authority. This removes accidental global
authority. Vehicle verification now occurs only inside an authorized city
application review. Account-wide containment now begins at an associated market
but requires a dedicated `PLATFORM_ADMIN` permission across every market in the
target's participant or staff history. Unrelated targets and partial coverage
fail closed, so a city/market grant cannot silently gain nationwide suspension
authority. The operations UI is a separate case-linked command module with no
broad account search and no automatic replay. Release work still includes access
review, independent incident rehearsal, and final legacy-caller/removal evidence.

---

# 8. API

The mobile applications communicate with the backend through an authenticated API.

The initial API style will be REST over HTTPS.

Example:

```text
POST   /auth/register
POST   /auth/login

GET    /drivers/me
PATCH  /drivers/me

POST   /rides
GET    /rides/{id}
POST   /rides/{id}/cancel

POST   /rides/{id}/accept
POST   /rides/{id}/start
POST   /rides/{id}/complete

GET    /rides/history
```

The exact endpoints will be defined in `api.md`.

The API should use versioning from the beginning.

Example:

```text
/api/v1/...
```

Breaking API changes should result in a new API version rather than silently changing existing behavior.

## 8.1 Client release compatibility boundary

Release compatibility is one backend-owned boundary shared by HTTP and the
live-event socket. Each packaged client declares one of six closed surfaces, a
strict numeric version and a positive build. Staging and production fail startup
if enforcement is disabled or any surface lacks minimum/recommended policy.

```text
Packaged client identity
        |
        +--> unauthenticated compatibility preflight
        |          |
        |          +--> supported/optional update --> session restoration
        |          +--> mandatory update ----------> blocked client UI
        |
        +--> every v1 HTTP/socket request
                   |
                   +--> middleware/socket gate --> normal auth and business rules
```

The compatibility endpoint is command-free and deliberately available before
authentication. Compatibility headers are self-declared routing/release facts,
not proof of identity, app integrity, role, city, or permission. Authentication,
session status, authorization, eligibility, assignment, pricing and money remain
separate server-owned checks. Policy changes are operational releases: they need
a new policy revision, accepted old/current client tests, staged observation and
a rollback or forward-fix decision. Build numbers support artifact traceability
but do not replace immutable artifact hashes or signatures.

---

# 9. Real-Time Communication

Ride state, offers, participant coordination, and other business commands use
authenticated REST. PostgreSQL remains authoritative; WebSocket and push paths
are non-authoritative hints that tell a client to reload the authorized REST
resource.

```text
Authenticated command
        │
        ▼
API transaction ── business row + notification + outbox row
        │ commit
        ▼
Outbox worker ── PostgreSQL cross-instance hint / generic FCM hint
        │
        ▼
Authorized client reloads REST state
```

This transaction-first design covers driver availability, ride offers,
acceptance, arrival, cancellation, status changes, and active-ride coordination.
A failed or duplicate delivery cannot invent, acknowledge, or roll back a ride
fact. Each API replica can notify locally connected clients after PostgreSQL
fanout, while a mobile client that misses every hint catches up at foreground,
reconnect, or explicit refresh.

Every staging/production API process owns one dedicated PostgreSQL listener.
Established termination clears listener readiness; periodic bounded liveness
probes detect half-open transports. The process cleans up the old connection and
pending best-effort dispatches before retrying and registering `LISTEN` again.
Callbacks from an old connection cannot invalidate or dispatch through its
replacement. API `/ready` requires both SQL availability and listener readiness;
`/health` remains process liveness. This is source health/recovery behavior, not a
guarantee that disconnected clients received hints or that hosted failover meets
an accepted recovery budget. Authoritative REST catch-up remains mandatory.

Each mobile composition root admits hint listening only while the authenticated
product is foreground, the advisory network is not unavailable, and no logout,
session-revocation or password-change action is pending. A common single-owner
supervisor observes a non-secret local session-generation flow: credential
replacement cancels the old attempt before starting the new one, while an
ordinary same-session restore leaves the generation unchanged. Authentication
restores are serialized so parallel foreground/push/reconnect reads do not rotate
one refresh credential twice. Logout closes admission before push cleanup and
suppresses late restore reactivation. This local lifetime is not proof of server
authentication or authorization and never contains tokens or account identifiers.
Generation, activity and the ending phase are one atomic value, preventing a
late restore from committing activity after logout closes admission.

After socket admission, every hint and transport loss/normal close, the client
requests authoritative REST state. Expected transport/rejection failures retry
with cancellable exponential jitter, initially 0.5–1 second and capped at
15–30 seconds. Handshake and individual catch-up are bounded to ten and fifteen
seconds; a healthy idle socket is not periodically disconnected. A meaningful
hint resets backoff; an instant handshake/close does not. Background/offline
ownership changes cancel the subscription, not replay commands. Catch-up results
apply only while their owner remains current and eligible. A catch-up timeout
retains prior render state and permits later hints; it does not prove delivery.
Connected-server socket expiry/revocation checks and physical/provider recovery
acceptance remain open; local cancellation does not substitute for them.

Participant coordination uses the same boundary. The passenger and assigned
driver may send only six documented closed codes during allowed active states.
The command persists the code and a recipient notification; live and FCM paths
carry only `RIDE_COORDINATION_MESSAGE`. No free text, phone number, identity
payload, or transcript travels through the hint. The client localizes the latest
authorized message after a REST reload. Terminal-state and stale-event checks
suppress obsolete delivery.

The system must not assume that a connection is permanently available. Mobile
applications recover from network loss, suspension, timeout, server restart, and
temporary cellular/Wi-Fi failure by re-reading server state. Failed commands are
not replayed automatically, and connection restoration is never treated as
command success.

---

# 10. Ride State

A ride should have an explicit state machine.

A conceptual version is:

```text
REQUESTED
    │
    ▼
MATCHING
    │
    ▼
ACCEPTED
    │
    ▼
DRIVER_EN_ROUTE
    │
    ▼
DRIVER_ARRIVED
    │
    ▼
IN_PROGRESS
    │
    ▼
COMPLETED
```

Cancellation can occur from appropriate states:

```text
REQUESTED ───────► CANCELLED
MATCHING ────────► CANCELLED
ACCEPTED ────────► CANCELLED
DRIVER_EN_ROUTE ─► CANCELLED
```

The exact cancellation rules will be defined in `rides.md`.

The backend, rather than the client application, should validate whether a state transition is legal.

---

# 11. Geographic Architecture

Geographic information is fundamental to TaxiMobile.

The system will need to represent:

* Driver positions.
* Passenger pickup locations.
* Destinations.
* Ride routes.
* Service areas.
* Taxi operating areas.
* Markets, cities, and versioned city service boundaries.
* Published fixed-route directions, stops, and static geometry.

PostgreSQL with PostGIS should be used for geographic database operations.

Locations should be represented using geographic types rather than simply storing latitude and longitude as unrelated floating-point values.

The system should be able to perform queries such as:

```text
Find available participating drivers
within X kilometers of a pickup location.
```

The city is resolved from the validated pickup point or selected fixed-route
direction, not trusted solely from a client field. Available-driver geometry is
private dispatch data. Passenger catalog queries may return public city
boundaries and published route geometry but never online-driver locations or
counts. High-volume geographic indexes include city scope so one city's dispatch
does not scan the national fleet.

---

# 12. Mapping

The application will require external mapping infrastructure for:

* Map display.
* Geocoding.
* Reverse geocoding.
* Routing.
* Estimated travel time.
* Distance calculation.

MapLibre Native is the selected renderer for the Android and iOS applications.
The style URL, tile sources, attribution, and optional offline packs are deployment
configuration rather than hard-coded application policy. Production must select a
tile/style source whose Morocco coverage, attribution, privacy, capacity, and
offline terms are acceptable to the cooperative.

Valhalla is the default routing and turn-by-turn engine and should be self-hosted
from controlled OpenStreetMap-derived data. GraphHopper is the implemented,
approved replacement if Valhalla cannot satisfy deployment or Morocco-routing
requirements. `TAXIMOBILE_ROUTING_PROVIDER` is a closed server-side selector for
`valhalla` or `graphhopper`; its base URL points to that deployment's private
service. A deployment runs one authoritative adapter, never competing client-side
engines.

Mobile clients call the authenticated provider-neutral backend routing endpoint;
they do not call either engine directly. Both adapters normalize route geometry,
distance, duration, and maneuvers into the same public contract. Changing the
selected engine therefore requires server configuration and provider acceptance,
not a mobile release.

MapLibre does not provide geocoding. TaxiMobile now has a separate authenticated,
provider-neutral place-discovery boundary with a closed `disabled|nominatim`
server selector. `disabled` is the fail-closed default. The Nominatim-compatible
adapter is intended for an approved, preferably self-hosted deployment; staging
and production configuration rejects the shared public Nominatim host. Mobile
clients never receive provider credentials or native payloads and never select a
provider.

Search requires one public, booking-capable city. Its active versioned service
area supplies only a ranking viewbox; a provider city label is never authority.
Every returned point is checked in PostGIS against the exact active polygon and
marked for pickup eligibility. Reverse lookup preserves the exact user-selected
coordinate even when the geocoder describes a nearby indexed object. Search and
reverse requests are authenticated, account-rate-limited, bounded, localized to
`ar|en|fr`, and not persisted or included in request logs. Provider attribution
travels in the normalized response. Provider timeout, malformed output, no match,
or disabled configuration leaves map tap and manual coordinates usable.

Saved Home/Work labels and local recent-place persistence remain separate future
features. No personal label is sent to the provider by this source slice. Route
and geocoder output is advisory display data and grants no authority over pricing,
ride state, city resolution, or driver assignment.

---

# 13. Payments

Payments should be isolated as a separate backend domain.

The payment system should support, where legally and technically available:

* Cash.
* Electronic payment.
* Digital receipts.
* Payment status.
* Refunds where applicable.
* Payment reconciliation.

The backend should never store raw payment card information unless there is a compelling legal and technical reason to do so.

The launch architecture supports cash and an optional provider-independent manual
bank/M-Wallet transfer adapter. The backend advertises transfer only when it has a
verified recipient and at least one destination, issues a unique reference, and
snapshots the instructions on the ride. A passenger claim moves the payment only
to `PROCESSING`; an authorized, audited reconciliation against the recipient's
independent settlement statement is the sole launch path to `COMPLETED`. Completion
and driver-earning creation occur atomically. Cash remains available regardless of
transfer configuration or external-service availability.

Migration `20260831_0044` makes the national path authoritative: an enabled
city-configuration service references one active/effective payment capability for
the same city, operator, and service. That capability always includes cash and
may reference one immutable verified recipient account for manual transfer.
Estimate and ride creation resolve the exact active bundle independently and
fail closed on mismatch. Rides and payments snapshot capability/recipient
provenance; payments and refunds retain city/operator provenance. The deployment-
wide recipient settings remain only as a disabled-by-default legacy-city
compatibility layer and cannot configure a new city or operator.

Refunds are append-only settlement facts in the same payment domain, not edits to
rides, fares, or earnings. The launch command is restricted to administrators,
locks a completed payment, requires unique independent return evidence, and
prevents cumulative over-refund. Passenger receipts receive only safe aggregate
and closed-reason fields. The launch allocation is wholly operator-funded; a
future driver recovery belongs to the versioned city economics ledger rather than
being inferred from the refund.

CMI and every hosted card processor are deferred provider adapters. If one is
approved later, its hosted entry surface keeps card data outside TaxiMobile and
its signed callback or authoritative status query—not a browser return—controls
payment state. The adapter contract, credentials, cancellation/refund rules, and
reconciliation format must come from the merchant agreement; they must not be
invented from public material.

---

# 14. Authentication and Authorization

Authentication determines who a user is.

Authorization determines what that user is allowed to do.

These must remain separate concepts.

The system will eventually support roles such as:

```text
PASSENGER
DRIVER
COOPERATIVE_MEMBER
ADMIN
```

A user may have more than one role if the cooperative model requires it.

Authorization must be enforced by the backend.

The client application should never be trusted to enforce permissions by itself.

National operations add scoped administrative grants such as platform
administrator, operator administrator, city manager, driver reviewer, pricing
manager, support agent, and aggregate-only analyst. A role name without its
market/operator/city scope is insufficient. The current `ADMIN` is transitional
bootstrap authority; it must not become an implicit unrestricted national data
reader. `auth.md` and `operations.md` define the target grant model.

The restricted support and safety modules currently depend on that active
`ADMIN` authority and bind later transitions to the assigned administrator.
They are separate persistence/API domains: ordinary support may escalate to one
linked safety record, but participant responses, notes, categories, lifecycles,
response targets, and retention versions remain distinct. National rollout must
replace this dependency with scoped support/safety grants rather than adding
client-side checks or duplicating the domains into a new service.

---

# 15. Driver Availability

Driver availability is different from simply being logged in.

A driver may be:

```text
OFFLINE
AVAILABLE
OFFERED_RIDE
EN_ROUTE
AT_PICKUP
ON_RIDE
PAUSED
```

The backend should maintain the authoritative state.

Location updates should be processed according to the driver's current state.

For example, a driver who is offline should not appear in passenger dispatch results even if their last known GPS location is recent.

---

# 16. Dispatch System

The dispatch system is responsible for finding appropriate drivers for a ride.

Initial factors may include:

* Geographic proximity.
* Driver availability.
* Current ride status.
* Service area.
* Vehicle eligibility.
* Driver eligibility.
* Relevant cooperative dispatch rules.
* Authoritative city and service type.
* Fixed-route eligibility or scheduled commitment when applicable.

The first implementation should favor a simple, understandable dispatch algorithm.

Optimization can be introduced later after real-world behavior is understood.

The dispatch system should not initially rely on opaque machine-learning decisions.

Passengers never receive the candidate set, online-driver count, queue, or
pre-assignment positions. Every service type creates an expiring driver offer;
the driver chooses whether to accept. Scheduled commitments use a separate
booking lifecycle until dispatch handoff so future work does not occupy a live
ride state.

---

# 17. Notifications

The system may use:

* Push notifications.
* In-app notifications.
* SMS where necessary.
* Email where appropriate.

Firebase Cloud Messaging is the selected background push transport for both
Android and iOS. FCM is a best-effort wake-up/refresh channel only. The backend
sends minimized event type and resource identifiers; the authenticated client
reloads the authorized resource before displaying sensitive or current state.

FCM remains selected because Cloud Messaging is available at no charge on
Firebase's Spark plan and does not require replacing the authoritative backend.
Crashlytics is also a no-cost Firebase product under that plan. TaxiMobile must
not add Firestore, Cloud Functions, Storage, Hosting, phone authentication, or
another metered/paid Firebase service merely to enable push or crash reporting;
any such service requires a separate cost, privacy, and architecture decision.
WebSocket refresh remains usable when Firebase configuration is absent.
The deployment owner must recheck Firebase's official [plan
documentation](https://firebase.google.com/docs/projects/billing/firebase-pricing-plans)
and [product pricing table](https://firebase.google.com/pricing) before promotion;
the architecture does not rely on a promotional credit or a Blaze-only service.

Notifications should not be the sole source of truth for ride state.

For example:

```text
Notification:
"Driver accepted your ride."

Authoritative state:
ride.status = ACCEPTED
```

If the notification is lost, the application should still obtain the correct state from the backend.

Transactional delivery is governed by one closed policy registry shared by the
outbox worker, live-event encoder, and FCM adapter. Every topic declares its
allowlisted hint, channel, urgency, maximum age, fallback, quiet-hour eligibility,
and dead-letter owner. Immediate ride events use high-priority bounded-TTL push
and live refresh where a ride WebSocket exists. Scheduled-booking and credential
events use bounded push plus persistent inbox/API polling; they never pretend a
ride WebSocket is a booking channel. Informational credential and future
commitment notices may respect quiet hours, while active dispatch, cancellation,
matching, coordination, and handoff events do not.

The worker suppresses new submissions after the policy age or stricter source
expiry and reloads current state before addressing a participant. The same
absolute source deadline reaches every push call, credential refresh and retry.
Android uses the floored remaining duration and APNs the absolute Unix deadline;
expired/sub-second submissions are suppressed. Provider/OS timing and changing
business state still require an authoritative reload before any action.
Live and push attempts are independent, with bounded retry on
partial failure and duplicate refreshes permitted. A failed device does not skip
later devices; durable per-device delivery progress remains open. An unknown topic is a
bounded dead-lettered operational defect, not a successful no-op. The mobile
allowlist contains the same public hint vocabulary and performs one complete
authenticated restore; it does not interpret the resource ID as business state.
User-configurable quiet-hour scheduling still requires implementation; measured
provider delivery SLOs require staging and field acceptance.

---

# 18. Database

PostgreSQL will be the primary persistent data store.

PostGIS will provide geographic functionality.

The database should contain logically separated domains including:

```text
Users
Drivers
Vehicles
Cooperative Membership
Markets / Operators / Cities
Scoped Administrative Grants
Driver City Applications / Authorizations
Rides
Scheduled Bookings
Published Fixed Routes
Ride Locations
Payments
Ratings
Notifications
Audit Logs
```

The exact schema will be defined in `database.md`.

---

# 19. Caching and Temporary State

A caching system such as Redis may eventually be introduced.

Potential uses include:

* Temporary driver availability.
* Real-time dispatch state.
* Rate limiting.
* Short-lived sessions.
* Distributed locks.
* Temporary geographic indexes.

Redis should not become the authoritative database for important business information.

Critical data must remain recoverable from persistent storage.

Redis is an optimization and coordination layer, not the source of truth.

---

# 20. Background Processing

Some operations should not block API requests.

Potential background jobs include:

* Sending notifications.
* Processing payment events.
* Generating receipts.
* Cleaning expired temporary data.
* Processing analytics.
* Administrative reports.
* Opening scheduled-offer and dispatch-handoff windows.
* Building privacy-bounded city/route/time aggregates from typed domain events.

The initial implementation should avoid unnecessary infrastructure.

A background task system should only be introduced when there is a concrete need.

---

# 21. External Service Abstraction

External providers should be isolated behind application interfaces.

For example:

```text
MapProvider
PaymentProvider
NotificationProvider
```

The application should depend on these interfaces rather than directly embedding provider-specific logic throughout the codebase.

Conceptually:

```text
Application
    │
    ▼
MapProvider
    │
    ├── Provider A
    ├── Provider B
    └── Local/Test Provider
```

This also makes automated testing easier.

---

# 22. Security Architecture

Security must be considered throughout the system rather than added after development.

The system should include:

* HTTPS.
* Secure authentication.
* Password hashing.
* Access control.
* Input validation.
* Rate limiting.
* Secure token handling.
* Protection against common web vulnerabilities.
* Audit logging for sensitive administrative actions.
* Secure storage of secrets.
* Minimal collection of personal data.

Secrets must never be committed to Git.

Examples include:

* API keys.
* Database passwords.
* JWT signing secrets.
* Payment credentials.
* Third-party service credentials.

Development secrets should be stored separately from source code.

---

# 23. Data Flow

A typical ride request should follow this path:

```text
Passenger
    │
    │ Create ride
    ▼
Passenger App
    │
    │ HTTPS
    ▼
FastAPI
    │
    ├── Authenticate passenger
    ├── Validate request
    ├── Determine pricing rules
    ├── Create ride
    │
    ▼
PostgreSQL/PostGIS
    │
    │ Find eligible drivers
    ▼
Dispatch System
    │
    │ Ride offer
    ▼
Driver App
    │
    │ Accept
    ▼
FastAPI
    │
    ▼
PostgreSQL
    │
    ▼
Real-Time Service
    │
    ▼
Passenger App
```

The backend remains authoritative throughout the process.

---

# 24. Failure Handling

The system must assume that components will fail.

Examples:

* Passenger loses internet connection.
* Driver loses internet connection.
* GPS becomes unavailable.
* Mapping provider becomes unavailable.
* Payment provider becomes unavailable.
* Backend temporarily becomes unavailable.
* WebSocket connection drops.
* Push notification is delayed.
* Mobile application is terminated.

The application should distinguish between:

```text
Temporary failure
```

and:

```text
Business failure
```

For example:

```text
Network unavailable
```

does not necessarily mean:

```text
Ride cancelled
```

The client should synchronize with the backend when connectivity returns.

---

# 25. Offline Behavior

The application should support limited offline behavior.

The client should be able to:

* Display previously loaded information.
* Preserve appropriate unsent state locally.
* Detect connectivity changes.
* Reconnect to the backend.
* Synchronize state after reconnection.

The application should not allow critical business operations to be considered successful solely because they were performed locally.

For example, a passenger cannot assume a ride request was successfully created merely because the request was stored locally.

Android observes the validated default network and iOS observes the system
network path. These platform signals are advisory: they can trigger presentation
and recovery, but they do not prove that the TaxiMobile API or a provider is
healthy and they never acknowledge a command. If connectivity is lost after an
authenticated screen has loaded, the application retains that last
backend-confirmed state and overlays a persistent localized warning. A startup or
session restore with no usable authenticated state may instead render the
dedicated offline screen.

Only a genuine unavailable-to-available transition triggers automatic recovery,
and it triggers one ordinary authoritative state restore. Repeated native
callbacks and initial availability do not duplicate startup restoration. Failed
ride, matching, availability, cash, or electronic-payment commands are not queued
for automatic replay; the refreshed backend state determines their outcome.
All authenticated Android and iOS screen actions cross a shared one-shot command
boundary. An uncertain/rejected result causes exactly one ordinary REST restore;
the command itself is never called a second time. Backend state replaces stale
content, while the original localized operation failure remains visible. A
session rejection clears authenticated content instead.
Each native root also acquires a common one-at-a-time presentation gate before it
launches the command coroutine. This makes rapid repeated or conflicting taps a
local no-op, exposes the exact pending resource to shared Compose loading states,
and releases reliably in `finally`. It is interaction control only: server-side
idempotency, authorization, and authoritative state remain mandatory.

Foreground recovery follows the same boundary. The shared lifecycle observes an
actual background (`ON_STOP`) before arming the next foreground (`ON_START`), so
initial composition and duplicate start callbacks do not duplicate startup work.
Only an authenticated session triggers the restore, and its result passes through
the same retained-state presentation rule. Foregrounding never replays a command.

---

# 26. Observability

The production system should eventually provide:

* Structured logs.
* Error reporting.
* Health checks.
* Performance monitoring.
* Database monitoring.
* API metrics.
* Ride lifecycle metrics.

Observability should avoid unnecessarily collecting sensitive personal information.

Backend observability remains self-hosted structured logs, authenticated
Prometheus metrics, health/readiness, and aggregate business/worker signals.
Outbox gauges preserve aggregate compatibility while also attributing pending,
leased, aged and dead-lettered work to a closed operational-owner vocabulary.
Unknown topics use one fail-closed `unclassified` bucket. Topic, resource,
payload, authorization, device and user values are forbidden as metric or alert
grouping labels. Prometheus rules may retain the owner for downstream routing,
but Alertmanager receivers, staff rosters and human acknowledgement remain
deployment configuration and acceptance evidence.
Security-incident telemetry follows the same boundary with one closed
`incident_severity` label. API and worker independently expose aggregate open,
containment-overdue, postmortem-pending and postmortem-overdue SEV1-SEV4
snapshots. Dashboard and alert queries reduce the duplicate role samples with
`min`/`max`, never sum them; snapshot failure omits counts and becomes an
explicit availability alert.
The provider-neutral single-host template supplies Prometheus, Alertmanager,
Loki, Alloy, and Grafana as an optional hardened overlay. Scrape, log-ingestion,
and dashboard query traffic use
an internal monitoring network
with fixed API/worker aliases; operator ports bind to loopback, configuration and
secret files are read-only, and time-series/notification/dashboard state use
separate volumes. Prometheus, Loki, Alloy, and Grafana have no external network. Alertmanager
alone joins a dedicated
egress bridge to reach HTTPS receivers and reads one webhook URL file per fixed
owner. The public TLS proxy must reject the internal scrape hostname. A larger
orchestrator may replace this topology only if it preserves the same
authentication, label, routing, egress and evidence contracts.
Grafana's Prometheus/Loki datasources and operations/log dashboards are immutable
file-provisioned artifacts. Each datasource reaches only its internal service.
Dashboard queries
are statically restricted to emitted low-cardinality service, normalized route/
status, fixed-worker, fixed-owner, fixed incident-severity and normalized-error
labels; there are no
business selectors, external links or query variables. Anonymous access, signup,
telemetry, plugin update traffic and duplicate Grafana alerting are disabled.
This diagnostic dashboard does not replace the separately governed aggregate
national analytics surfaces below.

Each authenticated application/worker scrape also performs one time-bounded,
fixed current-database capacity query. It exposes snapshot availability,
connection count/limit/utilization, active connections, ungranted locks and the
database deadlock counter without database, role, session or query dimensions.
Failure omits all stale values and emits only availability zero. Each process
also exposes fixed, unlabelled SQLAlchemy pool availability, configured size,
checked-in, checked-out and overflow gauges, a cumulative checkout-wait
histogram and timeout counter. Pool size, maximum overflow and
checkout timeout are explicit bounded settings on API and worker engines; the
deployment must reserve `(size + overflow) * replicas` plus migration,
maintenance and emergency connections below the server limit. This makes the
single managed database dependency and its application pools observable without
adding an exporter credential or host mount. Host CPU/IO/storage and query plans
remain deployment-owned T5 evidence; pool thresholds still require an approved
representative hosted workload.

The application writes a second copy of its allowlisted JSON events to bounded
rotating files only when an absolute deployment path is configured. API and
worker have distinct application-owned volumes; the image fixes their owner to
UID/GID `2000`, while Alloy has supplemental group-read permission and read-only
mounts. Alloy tails only those paths, has no container socket or host log access,
drops malformed or over-16-KiB lines, and indexes only fixed `service` values.
Request IDs and other allowlisted fields stay inside the JSON line rather than
becoming index labels. Loki is an internal unauthenticated single-binary TSDB v13
filesystem store with a 30-day query/ingest/compactor-retention boundary. Its
loopback port is an operator diagnostic surface, never public ingress.

The committed Compose log path is deliberately a one-API/one-worker single-host
baseline. Multi-replica deployment must use a per-replica volume and collector
sidecar/agent, or an equivalent reviewed transport; multiple processes must not
rotate one shared file. National scale also requires measured log volume,
capacity alarms, restore, and a supported highly available/object-storage Loki
topology before the single-node filesystem store becomes a bottleneck or evidence
risk.
Native application crash and ANR reporting uses Firebase Crashlytics because the
same role- and environment-separated Firebase projects are already required for
FCM. Firebase Analytics is not linked. Crashlytics is an operational adapter and
does not become a source of ride, payment, identity, or authorization truth.
Its no-cost Spark availability does not remove the provider-processing, privacy,
symbol-upload, retention, or release-acceptance gates below.

Mobile debug builds and providerless verification artifacts disable collection.
A distributable release must explicitly enable it and upload its matching Android
R8 mapping or iOS dSYM. The app must not attach a TaxiMobile account ID, contact
identifier, ride/payment/location data, custom business keys, or Analytics
breadcrumbs. Provider processing terms, retention, access control, incident
ownership, privacy notice, and role/environment isolation remain release gates.

National operational dashboards consume low-cardinality city, operator, service,
route-direction, booking-type, policy-version, time-bucket, and outcome
aggregates. Metrics and charts do not contain user identifiers, exact location
histories, driver documents, support text, or payment credentials and cannot
authorize business actions.

---

# 27. Testing Strategy

The system should use multiple levels of testing.

### Unit tests

Test individual pieces of logic.

Examples:

* Fare calculation.
* Ride state transitions.
* Driver eligibility.
* Validation.

### Integration tests

Test interactions between components.

Examples:

* API + database.
* Authentication + database.
* Ride creation + dispatch.

### End-to-end tests

Test complete user flows.

Example:

```text
Passenger registers
        ↓
Driver registers
        ↓
Driver becomes available
        ↓
Passenger requests ride
        ↓
Driver accepts
        ↓
Ride starts
        ↓
Ride completes
        ↓
Payment recorded
```

The exact testing framework will be selected during implementation.

---

# 28. Development Environments

The project should eventually have separate environments for:

```text
Development
Testing
Production
```

Development configuration must never accidentally point to production databases or payment systems.

Environment-specific configuration should be external to source code.

---

# 29. Deployment

The backend should initially be deployable using conventional Linux server infrastructure.

The architecture should avoid requiring expensive cloud infrastructure during early development.

The system should be capable of running on:

* A development computer.
* A small VPS.
* Larger infrastructure when required.

Docker Compose is the required local integration environment. It starts the PostGIS database and optional local-only support services. The API may run in the Compose stack or directly from a Python virtual environment. Production is packaged as immutable API and worker images and uses managed TLS termination or a standard reverse proxy; it must not expose PostgreSQL publicly.

The operations web application is a separately deployable static/browser
artifact on an exact HTTPS origin with a restrictive content-security policy.
Its deployment is independently promotable from the mobile applications and
backend, while API compatibility and permission tests remain release gates.

---

# 30. Scalability

The first version should optimize for simplicity, while the approved growth
target is country-wide operation through isolated city rollouts.

The architecture should nevertheless avoid obvious blockers to future growth.

Potential future scaling areas include:

```text
API servers
    ↓
Load balancer
    ↓
Multiple backend instances
    ↓
Shared PostgreSQL
    ↓
Redis / background workers
```

National scale begins with stateless API replicas, lease-safe workers, and one
managed PostgreSQL/PostGIS source of truth whose operational rows and indexes
carry city scope. Immutable configuration/catalog versions may be cached;
current ride, assignment, booking, eligibility, and money state may not.
Workers may partition claims by city while preserving database concurrency
guards. Read replicas, table partitioning, Redis, a durable queue, a reporting
warehouse, or domain extraction require measured thresholds and documented
failure/recovery behavior. The system must not create a code or database fork
per city or introduce distributed infrastructure merely because national scale
is planned.

---

# 31. Source of Truth

Different components have different authoritative responsibilities.

```text
PostgreSQL
    → persistent business data

Backend
    → business rules and authorization

Mobile applications
    → user interface and local presentation state

Real-time layer
    → communication, not permanent business truth

External providers
    → provider-specific services such as payments or maps
```

No client application should be considered authoritative for important business state.

---

# 32. Architectural Principles

The following principles apply to the project:

## Delivery discipline

Implement one bounded capability at a time. Identify the authoritative owner of the state, affected API and persistence contracts, failure behavior, and the smallest useful automated test before changing code. `implementation.md` defines the repository structure and quality gates for these slices.

### Principle 1 — Backend authority

Important business rules are enforced on the backend.

### Principle 2 — Shared mobile logic

Common application logic should be shared between Android and iOS whenever practical.

### Principle 3 — Minimal dependencies

A dependency should have a clear purpose.

### Principle 4 — Replaceable services

External providers should not be deeply embedded throughout the application.

### Principle 5 — Privacy by design

Collect and expose only information required for legitimate functionality.

### Principle 6 — Cooperative ownership

The architecture should not create unnecessary technological lock-in.

### Principle 7 — Simple before complex

Start with understandable systems and introduce complexity only when required.

### Principle 8 — Test business rules

Critical business behavior should be independently testable.

### Principle 9 — Document decisions

Significant architectural decisions should be recorded in the relevant
authoritative document listed in `README.md`. If an ADR collection is introduced
later, it must be indexed there rather than referenced as a missing file.

### Principle 10 — AI-readable architecture

The codebase and documentation should be structured so that AI coding tools can understand the system without relying on undocumented assumptions.
