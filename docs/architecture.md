# TaxiMobile — System Architecture

## 1. Purpose

This document defines the technical architecture of TaxiMobile.

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
separate production operations application. It hosts the public driver
application portal and protected operations console, does not render the mobile
passenger/driver root, and never receives business authority from browser state.
It reuses approved design tokens and narrow shared value types without coupling
mobile navigation to desktop administration.

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

---

# 9. Real-Time Communication

Ride-hailing requires real-time information.

Examples include:

* Driver location.
* Driver availability.
* Ride acceptance.
* Driver arrival.
* Ride status.
* Passenger cancellation.
* Driver cancellation.
* Dispatch notifications.

REST alone is insufficient for all of these use cases.

The architecture should therefore support a real-time communication mechanism, likely using WebSockets.

Conceptually:

```text
Passenger App
      │
      │ WebSocket
      ▼
Backend Real-Time Service
      ▲
      │ WebSocket
      │
Driver App
```

The system should not assume that a connection is permanently available.

Mobile applications must be able to recover from:

* Network loss.
* Application suspension.
* Connection timeout.
* Server restart.
* Temporary cellular/Wi-Fi failure.

The server remains the authoritative source of ride state.

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

MapLibre does not provide geocoding. Address search and reverse geocoding remain a
separate, replaceable integration and are not prerequisites for coordinate or
map-tap selection. Route distance is advisory and does not grant the client
authority over pricing, ride state, or driver assignment.

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

CMI is the selected electronic card-payment provider. TaxiMobile uses CMI's hosted
payment experience so payment-card details are entered into CMI-controlled pages
and never traverse or reside in TaxiMobile clients, logs, API requests, or storage.
The exact request signing, callback verification, and reconciliation contract must
come from the CMI merchant integration kit; it must not be inferred from public
marketing pages. Cash remains supported and uses the explicit backend settlement
flow.

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

Notifications should not be the sole source of truth for ride state.

For example:

```text
Notification:
"Driver accepted your ride."

Authoritative state:
ride.status = ACCEPTED
```

If the notification is lost, the application should still obtain the correct state from the backend.

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
Native application crash and ANR reporting uses Firebase Crashlytics because the
same role- and environment-separated Firebase projects are already required for
FCM. Firebase Analytics is not linked. Crashlytics is an operational adapter and
does not become a source of ride, payment, identity, or authorization truth.

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
