# TaxiMobile — National Operations and City Rollout Specification

## 1. Purpose and status

This document defines the approved target for expanding TaxiMobile from one
pilot into a Morocco-wide platform deployed city by city. It covers the
web-based operations control plane, city activation, driver applications,
city-scoped pricing, published fixed routes, scheduled bookings, transparent
operator fees, and privacy-bounded operational data.

This is a target contract, not a claim that these capabilities are already
implemented. Delivery must follow `roadmap.md`, with migrations, API contracts,
authorization tests, and backend authority completed before UI surfaces are
enabled.

The existing cooperative purpose remains unchanged. An operator may be a taxi
cooperative, an authorized local operating entity, or the organization operating
the national platform. The software must identify which entity is responsible
for each city and fee instead of treating “the operator” as an implicit global.

---

## 2. Terminology

* **Market** — the country-level TaxiMobile deployment. Morocco is the first
  market.
* **City** — the smallest independently activated operating jurisdiction. A
  deployment owner may map this to the legally appropriate city, province, or
  service jurisdiction after review.
* **Operator** — a cooperative or other approved entity responsible for one or
  more city services.
* **City assignment** — the audited relationship granting an operator authority
  for specified services in a city.
* **Service area** — a versioned PostGIS boundary within which a city service is
  offered.
* **On-demand ride** — an immediate point-to-point request.
* **Fixed route** — a published, directional route with a known start, finish,
  geometry, and flat transport fare.
* **Scheduled booking** — a future pickup reservation with its own lifecycle;
  it is not an active ride until the dispatch handoff window.
* **Operator service fee** — an explicit operator allocation calculated either
  as a percentage of an eligible transport-fare subtotal or as a flat amount.
* **Scheduling surcharge** — a separate passenger-visible amount charged for
  reserving future service when city policy permits it.

“Percentage of profit” is not an auditable calculation base and must not be used
in code or contracts. Percentage policies use an explicitly named fare subtotal.
An operator that is an existing TaxiMobile cooperative references that
cooperative; it does not duplicate membership or governance records. Operator
staff authority and cooperative membership remain separate relationships.

---

## 3. Operating hierarchy

The configuration hierarchy is:

```text
Market (Morocco)
  └── City
       ├── Service-area versions
       ├── Operator assignments
       ├── Driver requirement versions
       ├── Matching-policy versions
       ├── Tariff and fee-policy versions
       ├── Scheduling-policy versions
       └── Published fixed-route versions
```

Operators and cities are separate entities. The data model may support more
than one operator assignment over time, but the initial national release must
have one unambiguous active operator for each `(city, service type, effective
time)` combination. A passenger request must never be subject to two competing
fee or tariff authorities.

The backend determines the city from the validated pickup or selected published
route. A client-supplied city identifier is a hint or explicit catalog selection,
not authority; it must agree with the service boundary.

Every operational record that can differ by city must carry or derive an
immutable `city_id`. Financial and historical records additionally snapshot the
operator and policy versions used at the time.

---

## 4. City lifecycle and gradual rollout

Cities use an explicit lifecycle:

```text
DRAFT
  ↓
CONFIGURING
  ↓
PILOT
  ↓
ACTIVE
  ├──→ PAUSED ──→ ACTIVE
  └──→ RETIRED
```

* `DRAFT` — internal record only; no public booking.
* `CONFIGURING` — boundaries, operators, requirements, prices, routes, and
  support ownership are being prepared.
* `PILOT` — explicitly allowlisted participants may test the city.
* `ACTIVE` — the city is available to its intended public audience.
* `PAUSED` — new bookings are disabled without deleting history. Published
  fixed-route information may remain visible with a clear unavailable status.
* `RETIRED` — no new service; historical rides and policy snapshots remain.

Activation is a backend operation and must fail closed unless the city has:

1. An approved service boundary and timezone.
2. One active operator assignment for every enabled service.
3. Approved driver and vehicle requirements.
4. An active tariff and explicit operator-fee policy, including an explicit
   zero-fee policy when no fee is charged.
5. Matching, cancellation, scheduling, payment, support, safety, and retention
   ownership appropriate to enabled capabilities.
6. Required Arabic, French, and English public copy.
7. Tested routing/map coverage and operational readiness.
8. An audit record identifying the actor and configuration bundle.

City configuration is versioned and activated as a coherent bundle. A rollout
must not expose a new tariff while still using an incompatible old fee or
scheduling policy.

---

## 5. National operations web platform

The existing `TaxiMobile/webApp` module becomes the initial host for a dedicated
operations application. It must not render the passenger/driver mobile root.
It may reuse shared localization, money/coordinate types, and approved design
tokens, while owning browser-specific navigation, tables, forms, maps, and
authorization state.

The web platform has two deliberately separated surfaces:

1. **Public driver application portal** — account creation, city selection,
   application submission, protected document upload when available, and
   applicant-owned status.
2. **Protected operations console** — national/city administration, review,
   configuration, audit, and aggregate reporting.

Both surfaces call the backend API over HTTPS and never access PostgreSQL or
object storage directly. Hiding a control in the browser is not authorization.

The protected console must provide modules for:

* National rollout overview and city readiness.
* City lifecycle and service-area configuration.
* Operator assignments and scoped staff access.
* Driver, credential, and vehicle application review.
* Tariffs, scheduling surcharges, and operator fee policies.
* Fixed-route direction, geometry, stop, publication, and fare management.
* Scheduled-booking operations and exception review.
* Aggregate demand, supply, fulfillment, financial, and onboarding reports.
* Support/safety queues only after their restricted workflows are defined.
* Append-oriented audit review and security incident actions.

The console preserves TaxiMobile's navy, mustard, white, typography, feedback
colors, and restrained map style. Desktop density may use a sidebar, scope
switcher, tables, charts, and drawers rather than copying mobile bottom sheets.
`ui.md` and `extended_ui.md` remain the visual authority.

---

## 6. Scoped administration

A single unrestricted `ADMIN` role is not sufficient for national operation.
The target authorization model combines a role template with an explicit scope:

```text
PLATFORM_ADMIN          market scope
OPERATOR_ADMIN          operator and assigned-city scope
CITY_MANAGER            one or more city scopes
DRIVER_REVIEWER         assigned city/application scope
PRICING_MANAGER         assigned city pricing scope
SUPPORT_AGENT           assigned queue/city scope
ANALYST                 aggregate-only assigned scope
```

Permissions, rather than role names alone, authorize each operation. A city
manager cannot read or modify another city merely by changing an ID. An analyst
does not inherit document, exact-location, passenger identity, or payment-provider
access. Global access is exceptional and audited.

The existing bootstrap `ADMIN` remains a transitional deployment authority. A
future migration must create the first scoped platform grant without allowing
public role assignment or silently turning every existing administrator into a
national data reader.

Production operations accounts require stronger session policy and MFA before
national rollout. Pricing activation, city activation, fee changes, route
publication, driver decisions, document access, and grant changes are audited.

---

## 7. Driver application and city authorization

A person has one TaxiMobile account and one driver identity, but eligibility is
city-specific. The target model separates:

```text
Driver identity
  └── City application
       ├── requirement-version snapshot
       ├── credential/document submissions
       ├── review decisions
       └── city authorization
```

A driver may apply from the driver mobile app or public web portal through the
same backend workflow. The applicant selects a published recruiting city; the
backend records the requirements that applied at submission. A successful form
does not grant `DRIVER`, city authorization, vehicle eligibility, or online
status.

Applications retain the existing human-review states and add an applicant-owned
`WITHDRAWN` terminal state before approval. Reviewers see only applications
within their grants. Decisions
record reason, reviewer, requirement version, and time. Sensitive documents use
protected object storage, malware/type checks, least-privilege retrieval, and a
defined retention policy before upload is enabled.

An approved driver may hold authorizations for multiple cities, but may be
operationally online in only one city at a time. Going online validates the
driver, vehicle, credentials, current city authorization, service area, and fresh
location. City approval in one jurisdiction never implies eligibility in another.

---

## 8. City pricing and operator compensation

Pricing selection is scoped by:

```text
city
+ operator
+ service type
+ booking type (immediate or scheduled)
+ optional fixed-route direction
+ effective time
```

At most one active rule may match at the same specificity and time. Drafting,
review, approval, activation, replacement, and retirement are audited. Activation
never rewrites historical rides or bookings.

The passenger breakdown is calculated from explicit components:

```text
transport fare
+ scheduling surcharge (when scheduled)
+ passenger-funded operator service fee (when configured)
+ approved extras
- discounts/subsidies
= passenger total
```

Operator compensation has exactly one calculation mode per policy version:

* `PERCENTAGE_OF_TRANSPORT_FARE` — bounded decimal percentage applied to the
  documented eligible transport-fare subtotal.
* `FLAT_PER_COMPLETED_BOOKING` — fixed currency amount per completed booking.

The policy fixes rounding, currency, and a non-negative driver-net floor. Invalid
percentage/flat combinations are rejected before activation and a fee is never
silently capped or reinterpreted without an explicit versioned rule.

It also has one funding mode:

* `DRIVER_SETTLEMENT_DEDUCTION` — included within the passenger transport fare
  and deducted transparently when calculating driver net earnings.
* `PASSENGER_SURCHARGE` — added as a separate passenger-visible line and does
  not reduce the transport-fare amount credited to the driver.

The first release permits one operator service fee per ride. It must not stack
an undisclosed national fee and local fee. Scheduling surcharge allocation is a
separate policy and is excluded from the percentage base by default. Tolls,
tips, refunds, subsidies, and payment-provider charges are excluded unless a
future documented policy explicitly and legally includes them.

Every quote, booking, ride, receipt, driver earning, and operator settlement
stores the tariff, scheduling, and operator-fee policy versions and exact
component amounts. Zero values remain explicit.

---

## 9. Published fixed routes

A fixed route is a city service catalog, not a live map of taxis. Its hierarchy
is:

```text
Fixed route
  └── Published version
       ├── Direction (outbound/inbound are separate)
       ├── Start and finish
       ├── Ordered optional stops
       ├── Static route geometry
       ├── Flat fare and currency
       └── Effective/publication dates
```

Both directions require separate direction records even if they share a road.
The first implementation charges one flat transport fare for the complete
selected direction. Segment-based fares are not inferred from intermediate
stops and require a later explicit policy.

Passengers can always browse active published routes for a selected active or
paused city, including direction, start, finish, stops, route line, and current
flat fare. This catalog remains visible when zero drivers are online. In a
paused city it clearly states that new booking is unavailable.

Booking a fixed route creates an immediate request or scheduled booking that
references the immutable published direction version. Eligible drivers receive
the route name, direction, start/finish, pickup timing, flat passenger fare,
their fee/earning breakdown, and expiration. Drivers choose accept or decline
under the same non-penalization and atomic-assignment rules as other offers.

Route publication and fare activation are separate reviewed actions but must be
compatible before booking is enabled. Editing a published route creates a new
version; it never changes a historical booking's geometry or fare.

---

## 10. Scheduled bookings

Scheduled service uses a separate reservation aggregate so future work does not
put a driver or ride into an active operational state prematurely:

```text
SCHEDULED          → OFFERING
SCHEDULED          → CANCELLED
OFFERING           → DRIVER_COMMITTED | UNFULFILLED | CANCELLED
DRIVER_COMMITTED   → DISPATCH_HANDOFF | CANCELLED
DISPATCH_HANDOFF   → LIVE_RIDE_CREATED | UNFULFILLED | CANCELLED
```

City scheduling policy defines:

* Minimum lead time and maximum booking horizon.
* Supported service types, including whether fixed routes are schedulable.
* Offer-open time, response expiration, commitment deadline, and dispatch
  handoff window.
* Driver conflict buffers and fallback matching behavior.
* Passenger/driver cancellation cutoffs, scheduling-surcharge refund rules,
  no-show handling, and support ownership.
* City timezone for user presentation; authoritative timestamps remain UTC.

“Scheduled” means the backend accepted a future request, not that a driver is
guaranteed. The passenger sees distinct states for request received, driver
committed, dispatch approaching, and unfulfilled. The system must not display a
driver as reserved until the backend confirms that commitment.

Drivers receive scheduled offers with enough information to decide and may
accept or decline without a raw-acceptance-rate penalty. A driver cannot accept
overlapping commitments after configured travel/buffer time. The driver remains
eligible for ordinary work outside protected windows. At handoff, the backend
revalidates driver, vehicle, credentials, city authorization, and conflicts. It
then creates/assigns the live ride atomically or follows the documented fallback
matching policy.

Receiving future offers is an explicit city-scoped preference separate from
immediate `AVAILABLE` status. Opting in does not make a driver online or visible,
and opting out prevents new scheduled offers without cancelling accepted
commitments. Candidate selection and acceptance still revalidate city
authorization, credentials, suitable vehicle/service, conflicts, and notification
delivery policy. Push remains best effort; authorized polling/reload is the
fallback and notification reachability never becomes assignment authority.

The scheduling surcharge is quoted and version-locked when the passenger
confirms the booking. Whether it is collected at booking, authorization, ride
completion, cancellation, or refund depends on the approved payment policy; a
client return page never decides that state.

---

## 11. Passenger supply privacy and driver autonomy

Before assignment, passenger surfaces and APIs must not expose:

* Online taxi locations or markers.
* Counts of online/available drivers.
* Driver identities or vehicles.
* Candidate lists, rankings, queue positions, or movement.
* Heatmaps precise enough to infer individual drivers.

The passenger may see only the service catalog, published fixed routes, fare
information, their request/booking state, and honest generic matching progress.
After one driver accepts, the existing limited driver/vehicle identity and
post-assignment last-known location rules apply.

Driver availability remains private operational input. Every immediate,
fixed-route, and scheduled assignment is an offer the driver can accept or
decline. Declines do not by themselves reduce eligibility, pay, or access.

No public endpoint named “nearby taxis,” “online drivers,” or equivalent may be
introduced. Internal operations access to aggregate supply follows scoped,
minimum-cell-size reporting and never becomes a passenger feature.

---

## 12. Operational data foundation

Data collection exists to operate and improve the taxi network, not to build a
market in personal movement data. Authoritative domain events should carry typed
identifiers and approved dimensions rather than arbitrary analytics payloads.

Required operational dimensions include:

* City, operator, service type, booking type, fixed-route direction, and time
  bucket.
* Tariff, scheduling-policy, operator-fee, route, and matching versions.
* Outcome classes such as offered, accepted, declined, expired, unmatched,
  cancelled, completed, settled, or unfulfilled.

Initial aggregate measures include:

* Requests, completions, unmatched rate, wait/pickup time, and cancellations.
* Eligible/available supply by coarse city zone and time bucket.
* Offer outcomes and work distribution without punitive interpretation.
* Fixed-route request volume and fulfillment by direction.
* Scheduled lead time, commitment, fallback, and fulfillment outcomes.
* Driver application funnel counts and review duration by city.
* Transport fare, scheduling surcharge, operator fee, driver net, payment
  method/status, and reconciliation totals.
* Support/safety category counts only after access and retention policies exist.

The source-of-truth tables remain normalized PostgreSQL records. Transactional
domain events feed versioned aggregate views or fact tables. A separate warehouse
or stream processor is introduced only after measured volume requires it.

Analytics must not contain credential documents, free-text support content,
contact identifiers, payment credentials, exact long-term movement histories,
or arbitrary copied API bodies. Geographic reporting uses approved zones or
coarse cells with suppression thresholds. Public route discovery telemetry is
off by default; if later enabled, it uses documented first-party aggregate
counters and never reveals driver supply.

Every dashboard metric defines its source event, dimensions, time semantics,
late-event behavior, retention, and responsible owner. A chart is not allowed to
become authority for rides, money, eligibility, or city activation.

---

## 13. Scaling model

National scale begins as a city-scoped modular monolith, not premature
microservices or one database per city:

* Stateless API replicas sit behind a load balancer.
* PostgreSQL/PostGIS remains the transactional source of truth.
* Every high-volume operational query is city-scoped and indexed accordingly.
* Worker claims are lease/lock safe and may be partitioned by city without
  changing business ownership.
* Routing uses versioned Morocco-wide data or reviewed regional extracts behind
  the provider-neutral adapter.
* Configuration and catalogs are cacheable by immutable version; current driver,
  ride, booking, and payment state is not made authoritative in a cache.
* Read replicas, table partitioning, Redis, queues, and domain extraction require
  measured thresholds and failure/runbook design before introduction.

No city deployment receives a fork of the application. Differences live in
versioned data and policy. Emergency city pause must stop new work without
affecting other cities or corrupting active/history records.

---

## 14. Delivery invariants

The national expansion is accepted only when all of these remain true:

1. City and operator scopes are enforced in backend queries and negative tests.
2. Published route visibility never exposes live taxi supply.
3. Driver acceptance remains explicit for every service type.
4. Scheduled booking state is separate from active ride/availability state.
5. City rates, fixed-route fares, scheduling surcharges, and operator fees are
   versioned, explicit, reproducible, and historically immutable.
6. Passenger totals, driver net earnings, and operator allocations reconcile
   exactly using fixed-precision money.
7. Configuration activation and sensitive reads are audited.
8. Operational analytics are aggregate, purpose-bound, and unable to authorize
   business actions.
9. Existing mobile visual identity is extended rather than replaced.
10. A city cannot become public until its legal, operational, security, support,
    mapping, payment, and rollback gates are explicitly accepted.
