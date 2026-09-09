# TaxiMobile — National Operations and City Rollout Specification

## Current standing — 2026-09-07

Phases 12 through 19 are implemented in source, including versioned payment
operations. No city is deployment-accepted: the repository contains no accepted
legal/operator evidence, production provider proof, staffed duty roster,
recruited pilot cohort, measured pilot outcome, or post-launch closeout. A source
readiness decision is a control mechanism, not a claim that its uploaded evidence
is true or sufficient. See [`gaps.md`](gaps.md).

## 1. Purpose and status

This document defines the approved target for expanding TaxiMobile from one
pilot into a Morocco-wide platform deployed city by city. It covers the
web-based operations control plane, city activation, driver applications,
city-scoped pricing, published fixed routes, scheduled bookings, transparent
operator fees, and privacy-bounded operational data.

This is the approved target contract. Phases 12 through 19 now deliver the
national control plane and repeatable rollout foundation: market/operator/city scope,
service-area and coherent configuration versions, readiness decisions, scoped
grants, isolated operations sessions, versioned city driver requirements,
applicant-owned city applications, reviewed city authorizations, privacy-bounded
onboarding aggregates, scoped tariff/operator-fee/scheduling policies, immutable
ride economics, fixed routes, scheduled bookings, privacy-bounded analytics,
staged readiness, versioned payment operations, audited APIs, and their mobile/web
surfaces. Per-city legal,
provider, staffing, driver-cohort, pilot, and production evidence remains an
operator responsibility rather than a source-code completion claim.

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

Entry to `PILOT` is a backend operation and must fail closed unless the active
configuration has a current `PASSED` decision for each of these ten gates:

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

The concrete allowlist is `LEGAL_AND_OPERATOR_OWNERSHIP`,
`SERVICE_AREA_AND_TIMEZONE`, `DRIVER_AND_VEHICLE_REQUIREMENTS`,
`TARIFF_AND_OPERATOR_FEE`, `MATCHING_AND_CANCELLATION`,
`PAYMENT_AND_RECONCILIATION`, `SUPPORT_SAFETY_AND_RETENTION`,
`LOCALIZATION_AR_FR_EN`, `MAP_ROUTING_COVERAGE`, and
`SECURITY_MONITORING_AND_ROLLBACK`.

`PILOT` is bounded and is not a synonym for public availability. Moving from
`PILOT` to `ACTIVE` additionally requires `PILOT_SERVICE_AND_FAIRNESS`, recorded
against the active bundle only while the city is in `PILOT`. Its evidence
reference points to the reviewed service/fairness report and agreed thresholds;
the aggregate dashboard itself never authorizes launch. `POST_LAUNCH_REVIEW` is
a separate closeout decision accepted only after the city has reached `ACTIVE`.
It remains visible in the national rollout overview before the next rollout plan
is approved but does not create the circular requirement of reviewing a launch
before it occurs.

An operating city cannot bypass these controls by activating a new configuration:
a replacement in `PILOT` independently requires the ten pilot-entry gates, and
a replacement in `ACTIVE` or `PAUSED` independently requires all public-
activation gates. `ACTIVE → PAUSED` remains the immediate audited emergency
stop; `PAUSED → ACTIVE` revalidates the public-readiness bundle.
For an approved replacement in an already `ACTIVE` or `PAUSED` city, a new
`PILOT_SERVICE_AND_FAIRNESS` decision must reference a reviewed change-impact or
regression report showing why the measured outcome remains representative. The
old row is not copied. Post-launch closeout can pass only on the active bundle.

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

The delivered artifact keeps the two surfaces in separate composition roots.
The protected console includes the sign-in/scope shell, rollout,
city/operator creation, operator status and assignments, service-area version
entry/review, coherent configuration assembly/review/activation, reviewed city
lifecycle commands, typed-confirmed scoped grant create/revoke, expiry review,
and scoped audit. Phase 13 adds
permission-gated requirement-version editing, an oldest-first scoped application
queue, reviewed decisions, and suppression-aware onboarding aggregates. The
public `#/apply` surface provides its own account, city catalog, application,
vehicle, status, and timeline flow without importing operations authority.
The city screen separates pilot-entry, public-activation, and post-launch
evidence, records only `PASSED` or `FAILED` with a bounded non-secret reference,
uses optimistic configuration versions, and reloads after every command.
Service boundaries are entered as bounded WGS84 longitude/latitude rows and
converted to the typed multipolygon request in memory; the browser never offers
an arbitrary JSON configuration field. Configuration assembly resolves exact
same-city/operator/service active tariffs, fee policies, scheduling policies,
payment capabilities, driver requirements, and published routes, while the API
remains the final authority.

Protected driver-document upload, replacement, deletion, and reviewer retrieval
are implemented behind one fail-closed capability. They become visible only when
the encrypted private-volume adapter, independent 32-byte key, and ClamAV service
are configured together. The backend enforces a 10 MiB default limit, PDF/JPEG/PNG
signature matching, malware scanning, applicant ownership, optimistic versions,
request quotas, recent reviewer MFA, city scope, no-store delivery, opaque names,
and access audit. If any dependency is absent or unavailable, neither browser
surface simulates a successful file operation.

Both surfaces call the backend API over HTTPS and never access PostgreSQL or
object storage directly. Hiding a control in the browser is not authorization.

The protected console must provide modules for:

* National rollout overview and city readiness.
* City lifecycle and service-area configuration.
* Operator assignments and scoped staff access.
* Driver, credential, and vehicle application review.
* Tariffs, scheduling surcharges, and operator fee policies.
* Versioned payment capability/recipient activation plus an age-ordered manual-
  transfer reconciliation queue with exact-reference verification/rejection and
  a confirmed-refund reconciliation ledger.
* Fixed-route direction, geometry, stop, publication, and fare management.
* Scheduled-booking operations and exception review.
* Aggregate demand, supply, fulfillment, financial, and onboarding reports.
* Restricted support and safety queues, overdue filtering, assignment,
  participant-safe communication, escalation, resolution, and audit review.
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
PAYMENT_RECONCILER      assigned operator/city settlement scope
SUPPORT_AGENT           assigned queue/city scope
SAFETY_RESPONDER        assigned safety queue/city scope
ANALYST                 aggregate-only assigned scope
```

Permissions, rather than role names alone, authorize each operation. A city
manager cannot read or modify another city merely by changing an ID. A payment
reconciler sees only the minimum claim, fare, recipient, and statement-reference
fields for assigned operators/cities. A reconciler may record a refund only after
a separately accountable approved case and confirmed return evidence; they cannot
change fares, approve their own case, recover driver earnings, or change recipient
versions. An analyst does not inherit document, exact-location, passenger
identity, recipient-account, statement, or payment-provider access. Global access
is exceptional and audited.

The existing bootstrap `ADMIN` remains a transitional deployment authority. The
controlled `taximobile-bootstrap-operations` command maps exactly that active
administrator to the first market-scoped `PLATFORM_ADMIN` grant under an advisory
lock and writes an audit record. Two separately reviewed, already registered
active accounts are then added with `taximobile-bootstrap-operations-quorum`, an
explicit change reference and `--confirm-initial-quorum`. The second command is
also advisory-lock serialized and audited, and refuses further use once three
active non-expiring platform administrators exist. Neither path is an HTTP
endpoint or a routine grant-management mechanism.

Production operations accounts use password plus encrypted authenticator-app
TOTP, single-use recovery codes, short-lived operations access tokens, rotating
secure refresh cookies, and CSRF-bound refresh. Factor enrollment/replacement is
a trusted-terminal procedure; replacement revokes all sessions. Grant changes,
operator authority/status changes, pricing/configuration/city activation, fee
changes, route publication, driver decisions, document access, and legal-hold
changes require MFA no older than ten minutes and are audited. Account-wide
session revocation, suspension, and reactivation additionally require the
`manage_account_security` permission, currently held only by a market-scoped
`PLATFORM_ADMIN`, across every market associated with the target. The path market
must itself be associated with the target. Unrelated targets are hidden and
partial cross-market coverage requires escalation; city-level staff never gain
nationwide account authority. Commands are idempotent and use controlled reason
codes plus `SUP-`, `SAF-`, or `SEC-` case references. Suspension revokes mobile
and operations sessions and push registrations; reactivation revives none of
them. Self-action is refused and every outcome is fixed-field audited. The blocked
command is never implicitly replayed after step-up.

Suspension is ordered against new driver assignments at the database, not by UI
timing. Live acceptance, scheduled acceptance and scheduled handoff hold a shared
lock on the target's global account after their driver lock; containment holds the
exclusive account lock. If containment wins, the stale assignment fails or uses
scheduled fallback. If assignment was already authoritative, it may commit first
and remains in ride history when suspension subsequently revokes all access.
Staff must inspect active ride state and use the approved support/safety runbook;
they must not assume containment silently cancelled or reassigned a passenger.
Session-only revocation blocks later requests but is not a retroactive transaction
cancellation mechanism.

Staff-grant creation and revocation use a dedicated console request queue. The
browser accepts an exact approved user UUID, maps each closed role template to
exactly one selected market/operator/city scope, displays the complete request,
requires typed confirmation, and reloads authoritative state. Revocation remains
non-effective while pending. Queue rows expose action, target, role, scope,
requester, reason and optimistic version; only the maker receives cancellation,
the target cannot decide, and another administrator receives approve/reject.

Every write requires a fresh idempotency key and recent MFA. The backend locks the
market, revalidates live market-admin authority and all reviewed state, and changes
the request plus grant in one transaction. Requester, target and approver are
distinct. Platform-admin revocation must leave two active administrators, and an
expiring platform grant requires two successors that outlast it. Direct mutation
routes remain test/development fixture compatibility only and return conflict in
staging/production. Non-expiring grants are marked for recertification. The
software workflow is implemented; roster ownership, recertification cadence,
hosted staff drill and emergency-recovery acceptance remain open.

The console's account-security module is intentionally case-led rather than a
directory browser. Staff must copy the exact user UUID from an authorized case,
select its association market, choose a controlled reason, enter a `SUP-`, `SAF-`,
or `SEC-` reference, and type the action word. Submission clears that confirmation.
The UI cannot weaken the backend's complete-market-coverage check and does not
retry a failed or MFA-blocked mutation automatically.

---

## 7. Driver application and city authorization

**Phase 13 delivery status (2026-08-31): implemented, including protected
document I/O.** Migrations `20260824_0035` and `20260831_0045`, the shared applicant API, mobile
driver onboarding, standalone public web portal, scoped reviewer console,
authorization-aware online selection, matching enforcement, and small-cell
aggregate suppression are covered by backend and Kotlin tests. This delivery
does not enable production operations password login or a second-city launch.
Production document access remains a deployment gate: the shared encrypted
volume, independent key, private scanner, backup/restore policy, and reviewer
access drill must be configured and verified before traffic is admitted.

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
defined retention policy. Replaced or applicant-deleted documents are soft-deleted
transactionally, then the fixed retention worker erases ciphertext and metadata
and records immutable, content-free erasure evidence. The first policy version
uses a configurable 730-day deadline for retained application documents; deletion
requests become eligible immediately unless another documented legal obligation
supersedes this application-document policy.

An approved driver may hold authorizations for multiple cities, but may be
operationally online in only one city at a time. Going online validates the
driver, vehicle, credentials, current city authorization, service area, and fresh
location. City approval in one jurisdiction never implies eligibility in another.

**Authorization lifecycle delivery (2026-09-05):** scoped reviewers can suspend,
revoke and reinstate existing authorizations through the dedicated decision API
and the application-detail console. The console shows current status and expiry,
requires an allowed reason and the typed authorization ID, and displays the
backend result. Recent MFA, application-version checks, idempotency and a scoped
audit are enforced by the API. A replay rechecks current city access.

Reinstatement applies only to suspended, still-valid authorization after renewed
eligibility checks. It does not extend expiry or set the driver online. Revoked
authority requires a new application. The original application approval remains
history; use its nested authorization status for current permission. Decisions
share the driver lock with assignment and preserve committed rides and future
commitment history. Handoff revalidates eligibility; operations must use existing
support/safety procedures for an already assigned journey.

The 33-case focused backend pack, current full 990-test backend regression and
both 57-case web browser target suites pass locally.
This includes a same-driver/two-city isolation test and actual MFA/scope/replay
checks. Independent-process contention, complete driver-facing notification
delivery, accessibility and staffed incident drills remain acceptance work under
`GAP-018` and `RACE-07`.

The mobile and web applicant views now distinguish recorded active, suspended,
revoked, expired and unknown authorization status, show supplied expiry, and
explain that the server checks eligibility for new work. Staff must not infer
that a driver received or acknowledged a restriction from this display change;
offline freshness, provider delivery and explicit acknowledgment/appeal workflow
still require acceptance before pilot. Each source decision now atomically writes
a generic persistent driver notice and a minimized authorization refresh outbox
event; marking that notice read is not treated as consent or understanding.

Monitoring now attributes pending, leased, aged and dead-lettered outbox work to
the closed `driver_compliance`, `dispatch_operations`, or
`scheduling_operations` owner, with unsupported topics isolated as
`unclassified`. The dead-letter Prometheus rule retains that owner and never
groups by topic, resource, payload or user. Local unit and PostGIS recovery tests
pass; production operations must still configure the collector, Alertmanager
receivers, primary/backup roster, acknowledgement objective and escalation drill
before treating the source label as staffed response.
The provider-neutral deployment package includes an internal-only Prometheus/
Loki/Alloy/Grafana network, Alertmanager-only egress and a guarded runtime validator. Use
the same digest-pinned images and secret files for validation and startup; never
inline a monitoring token, Grafana administrator password or webhook URL. The
provisioned `TaxiMobile Operations` and `TaxiMobile Logs` dashboards are
immutable and deliberately limited to reviewed low-cardinality metric/label
vocabularies; they cannot display or
authorize ride, account, document, payment or city-policy actions. Loopback
dashboards are operator diagnostics, not public endpoints. A green parser/
configuration check does not show that an
alert reached a person—record firing, receipt, acknowledgement, resolution and
backup escalation during the T5/T6 drills in `testing.md`.

API and worker logs are separate bounded JSON files collected read-only by Alloy
and retained in internal single-node Loki for 30 days. Operations must alert on a
missing Loki/Alloy scrape, collector line rejection, delivery retries/drops, and
disk pressure; rejected line contents must never be copied into a ticket. The
single-host volumes are not safe for `docker compose --scale`: use per-replica
volumes/collectors in a larger orchestrator. Before relying on logs as incident
evidence, rehearse read-position restart, time retention, capacity exhaustion,
backup/restore, least-privilege access, and transition to supported HA/object
storage at the measured threshold.

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

**Phase 14 delivery status (2026-08-27): implemented.** Migration
`20260824_0036` scopes fixed tariff, operator-fee, and scheduling-policy versions
to city/operator/service/booking context; provides draft, review, activation,
replacement, optimistic-concurrency, scoped-permission, and audit behavior; and
stores immutable quote economics through ride settlement. The operations web
console can create and edit drafts and issue explicit submit/activate commands
within the selected city and operator. Passenger quotes/receipts and driver
offers/earnings render backend-authored components. No browser or mobile client
performs authoritative money arithmetic. Migration `20260829_0038` expands the
scheduling policy foundation and the delivered Phase 16 aggregate consumes it
for review estimates, immutable booking snapshots, offers, commitments,
cancellation, and handoff.

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

### Launch payment capability and reconciliation

Every city/operator/service configuration publishes an explicit, versioned list
of allowed payment methods. `CASH` is the launch fallback. A city may add
`MANUAL_TRANSFER` only after all of these activation gates pass:

* The legal recipient name and bank account and/or interoperable M-Wallet
  destination have been verified outside the application.
* Account ownership, access, statement format, external fees, transfer limits,
  and expected settlement delay are documented for the operator.
* At least two named operational roles exist: one with protected statement
  access and one accountable for reconciliation/audit review. A small pilot may
  assign both to one authorized administrator temporarily, but that exception is
  recorded and cannot imply national unrestricted access.
* A controlled test transfer proves that the backend-issued reference, amount,
  currency, and time can be located reliably in the recipient statement.
* Passenger support copy explains that submission is awaiting review and does
  not promise that the external bank or wallet charges no fee.
* Cash remains usable if the external institution, statement access, or transfer
  configuration fails.

Migration `20260831_0044` and the protected operations payment module deliver the
national configuration model. Staff with `MANAGE_PAYMENT_CAPABILITIES` create a
city/operator recipient draft, verify it with recent MFA, and progress each
city/operator/service capability through draft, review, approval, and MFA-gated
activation. Cash is mandatory. Manual transfer requires a verified same-scope
recipient. The exact active capability must then be included in the coherent
city-configuration service; child activation alone does not alter passenger
capabilities. Replacing a city bundle marks omitted active capabilities replaced
without changing historical rides. Protected deployment variables remain only
as a disabled-by-default compatibility surface for the deterministic legacy city.

The reconciliation queue is processed from oldest submitted claim first unless
an incident policy says otherwise. The reviewer compares the recipient's
independent statement with all of the following backend-owned values:

```text
unique TM payment reference
exact amount and currency
recipient account/wallet
reasonable transfer time window
optional payer-side reference
```

The console loads this queue through
`GET /operations/payments/manual-transfers`; verify and reject commands use the
matching scoped operations routes and a fresh idempotency key. Configuration and
reconciliation permissions are deliberately separate.

A passenger message, screenshot, client state, or payer-side reference alone is
never proof. On a match, the reviewer records the external settlement reference;
the backend atomically completes the payment, verifies the claim, creates the
driver earning, and audits the action. One settlement reference cannot be reused.
On no match or mismatch, the reviewer records a bounded reason, returns the
payment to pending, and support can ask the passenger to correct the reference or
contact their financial institution. Statements and credentials stay in the
institution's protected operator channel and are not uploaded into ordinary
TaxiMobile support, logs, analytics, or the passenger application.

The responsible operator reviews daily totals by method and status, unresolved
claim age, rejected claims, completed payments, driver earnings, and recipient
statement totals. Exceptions are investigated before payout/export.

For a refund or fare correction, support first records the passenger's dispute
and the responsible administrator records an approval in the controlled case
system. Money is then returned through cash or an external transfer. Only after
the reviewer independently verifies the signed cash-handover reference or the
outbound institution reference may they call
`POST /operations/payments/{payment_id}/refunds` with a new idempotency key and
recent operations MFA. The
reviewer must verify payment ID, original amount/currency, cumulative prior
refunds, approved reason, returned amount, settlement method, and evidence
reference. The API rejects pending payments, over-refunds, duplicate evidence,
and unapproved reason values.

The operator reviews `GET /operations/payments/refunds` against daily cash/outbound
statement totals and the audit trail. The transfer queue and refund ledger are
filtered in SQL by the conjunction of the reconciler's authorized city/operator
grants before pagination. A `PAYMENT_RECONCILER` cannot edit recipients,
capabilities, fares, or city configuration. The launch record allocates the complete
refund to the operator and zero to driver recovery; staff must not offset a
driver payout manually or edit the original earning. Mistakes are escalated for
an append-only correction policy rather than deleting or changing a refund row.
Settlement references and private notes remain restricted operational data;
passenger communication uses the closed reason plus confirmed amount and date.

CMI/card processing is deferred until the working launch system has an approved
merchant contract, hosted-entry protocol, authenticated callback specification,
cancellation/refund/dispute policy, and operational reconciliation proof.

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

For immediate work, “outside” is evaluated against server time at candidate
selection and again after the driver lock at offer acceptance. A commitment that
currently contains that instant blocks the offer/assignment; a released or
cancelled commitment does not. The reciprocal scheduled acceptance check refuses
a current-window commitment if an active live ride already won the driver lock.
This does not yet estimate whether a live ride accepted before the window will
finish before it; that conservative duration policy must be approved and tested
before pilot scheduling thresholds are accepted.

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
* Support/safety category counts under the access and retention policy below;
  never free text, case notes, participant identities, or report-level exports.

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

### Delivered Phase 17 operating contract

Migration `20260829_0039` and the `analytics` worker implement the initial
PostgreSQL-first foundation. Every refresh serializes on one advisory lock,
captures eligible/available supply only at `CITY_WIDE`/hour scope, removes expired
snapshots, and recomputes a versioned materialized fact view from normalized
records. Recompute-through-retention is the explicit late-event policy; source
watermarks and computation timestamps make stale data visible. The default
refresh interval is five minutes and deployments may set only 30–3,600 seconds.

`GET /operations/analytics/definitions` publishes the purpose/source/owner/unit/
retention contract. `GET /operations/analytics/facts` requires one authorized
city and never accepts a national unscoped read. Cells below five source records
or entities return their dimensions and `suppressed=true`, with every count,
money, duration, score, and work-distribution measure removed. Operations staff
must not total suppressed cells, infer participants, or use the dashboard to
change assignment, eligibility, payment, or rollout authority.

---

## 13. Support and safety operations

Ordinary service handling and safety response are separate queues. A support
agent must not classify threatening behavior, assault, harassment, unsafe
driving, discrimination, or vehicle danger as an ordinary ticket merely to keep
it in a less restricted queue. `POST /operations/support/tickets/{id}/escalate-safety`
creates a separate safety record while preserving the source ticket and audit
chain; it never changes a rating or payment by itself.

### Responsible roles and scoped authority

Every operating shift names all of the following in the protected duty roster:

```text
support case owner       ordinary queue, participant acknowledgement, resolution
safety responder         restricted safety queue and participant communication
safety incident lead     urgent escalation and external-policy decision
security response lead   cyber/account/provider containment and evidence timeline
communications lead      approved regulatory/user/partner communication decisions
operations liaison       service pause, staffing and city/operator coordination
postmortem owner          conclusion evidence and tracked follow-up ownership
operations manager       overdue queue and staffing accountability
privacy/retention owner  access review, legal hold, expiry and deletion evidence
```

One person may cover more than one role during a controlled small pilot, but the
exception and shift times are recorded. Operations reads and mutations require
an active operations session plus a matching city-scoped `SUPPORT_AGENT` or
`SAFETY_RESPONDER` grant; a market-scoped `PLATFORM_ADMIN` may cover authorized
cities. The assignee must also be active and hold the matching exact-city grant
at command time. The legacy `/admin` routes remain compatibility-only pilot
surfaces and do not establish national authority. Production access additionally
requires the MFA/browser-session hardening described in `security.md`.

Security incidents use a distinct market-scoped register rather than support or
safety free text. Initially, only a market-scoped platform administrator has
`manage_security_incidents`; expanding this permission requires an approved role
and roster decision. The reporting administrator becomes the initial security
response lead. Four closed responsibilities are tracked independently: security
response lead, communications lead, operations liaison and postmortem owner.
There is one active assignee per responsibility, while every released tenure
remains visible. The lead records evidence links, containment actions, communication decisions,
recovery and postmortem work as append-only timeline facts, then advances the
incident through the documented forward-only lifecycle. Account/session and
staff-grant containment continue through their own separately authorized APIs;
provider credential rotation remains an external secret-manager action. The
timeline links those audit/runbook references but never copies credentials or
raw provider payloads.

An assignment is not a staff-directory search or a grant. The operator enters an
exact UUID already present in the approved roster; the backend accepts it only
when that user is active and holds a live platform-administrator grant in the
incident's exact market. Absent, inactive, expired, revoked and wrong-market
candidates receive one generic refusal. Every assignment cites the roster, shift
or incident-command reference, requires recent MFA/idempotency/current version,
and appends a generated responsibility-change fact. Reassigning the response lead
updates the incident lead. Assignment stops after postmortem completion.

Closing sets a required postmortem deadline but does not itself satisfy it. The
lead completes the postmortem once with a controlled outcome, conclusion time,
optimistic version and immutable audit/runbook evidence. Remaining remediation
uses `FOLLOW_UP_REQUIRED` and must link its approved external work reference;
completion is not permission to erase or silently abandon that work. Corrections
are appended to the timeline and never overwrite the completion fact.

The protected operations web workspace hides the incident destination unless
that permission is present. It provides a bounded market queue, market/city
incident creation, detail and immutable timeline review, controlled referenced
timeline entries, active/released responsibility review and assignment, and only
the next valid lifecycle transition. Every mutation
requires an explicit typed confirmation; recent-MFA and stale-version failures
reload authority but never replay the command. This workspace is a coordination
and evidence surface. It includes the one-time postmortem completion control but
does not page responders, rotate keys, call providers,
notify affected users, or execute containment actions.

The protected API and worker scrapes independently query aggregate incident
deadline state with a five-second timeout. They expose availability and zero-
filled SEV1-SEV4 counts for open incidents, missed containment targets, pending
postmortems and missed postmortem targets. Infrastructure reduces duplicate role
snapshots with `min`/`max`; it never adds them. SEV1/SEV2 open or overdue-
containment conditions are critical, SEV3/SEV4 containment breaches and every
overdue postmortem are warnings, and any snapshot loss is critical. These rules
route to the platform-duty default receiver only after deployment supplies its
approved secret. Source rules do not prove a receiver, named responder,
acknowledgement, escalation or resolution SLO.

### Response targets

Targets run from the backend `created_at` to the first participant-visible
acknowledgement. They are triage targets, not promises that an investigation,
refund, legal process, or emergency response will finish within that time.

| Queue/category | Priority | Target |
| --- | --- | --- |
| Support `ACCOUNT_ACCESS` | High | 4 hours |
| Support `RIDE_PROBLEM` or `FARE_DISPUTE` | Normal | 24 hours |
| Support `OTHER` | Low | 72 hours |
| Manually reprioritized urgent support | Urgent | 1 hour |
| Safety `IMMEDIATE_DANGER` | Urgent | 5 minutes |
| Every other safety category | High | 30 minutes |

Reprioritizing a support case may shorten but cannot extend its existing
deadline. The duty owner opens the unassigned and `overdue=true` queues at shift
start, after every handoff, and at least every 15 minutes while a pilot is live.
The `case_alerts` worker durably creates one overdue alert per case/deadline,
retries bounded delivery to a configured HTTPS pager, and records acknowledgement
through a city-scoped idempotent operations command. A disabled or failed pager
never counts as successful delivery. Free testing intentionally has no external
pager and therefore cannot support a live safety pilot.

### Ordinary support runbook

1. Claim the case with priority, a participant-visible acknowledgement, and a
   separate minimal internal note. Never paste passwords, tokens, statements,
   bank credentials, document images, or unrelated personal data.
2. Verify ride association and authoritative ride/payment facts through the
   restricted system. A participant statement is context, not authorization to
   change a fare, refund, earning, driver eligibility, or account status.
3. If the content is a safety concern, stop ordinary handling and create the
   linked safety record. The copied description remains protected.
4. Resolve with one controlled code and a plain participant message. A mistaken
   or disputed resolution returns to `IN_PROGRESS`; no note is edited or deleted.
5. Close only after the participant communication and required operational
   action are recorded. Closure starts the retention projection.

### Assigned-ride coordination runbook

The passenger and assigned driver can exchange only the six closed pickup/status
signals defined in `rides.md`. Operations staff cannot send a signal as either
participant, inspect a participant transcript, disclose a personal phone number,
or treat a push receipt as proof that the other person saw it.

1. When a participant cannot locate the other, first ask them to use the relevant
   fixed signal while stopped and safe; do not ask a driver to interact while
   moving.
2. If the signal is delayed or unavailable, use the approved support fallback and
   verify the authoritative ride state. Never repeatedly trigger or replay a
   participant command from staff tooling.
3. If repeated signals, harassment, threats, unsafe driving, discrimination, or
   immediate danger are reported, create/use the controlled safety path. The
   signal channel is not an emergency service.
4. During a provider outage, communicate that in-app history/refresh may still
   recover committed state, follow the feature-disable/fallback procedure, and
   record only bounded operational facts—not coordinates, contact details or a
   reconstructed signal sequence.
5. Any real pilot requires a named support owner, tested escalation contact,
   approved retention/erasure policy, and the T6/T7 evidence in `testing.md`.

### Safety runbook

1. For every new report, verify ride ownership server-side, claim it through the
   `ACKNOWLEDGED` transition, and send a participant-safe message. Do not reveal
   the reported person's identity, internal reasoning, staff identity, or action
   that has not occurred.
2. `IMMEDIATE_DANGER` is moved to the front of the queue. Tell the participant
   that TaxiMobile is not an emergency service and, if possible, to move to a
   safe place and contact local emergency services. The app does not dispatch
   emergency help or infer a current emergency location.
3. Notify the named safety incident lead through the protected operator channel.
   Contact with authorities, insurers, or other outside parties occurs only
   under an approved jurisdiction-specific policy; record the controlled
   resolution code but do not copy sensitive external correspondence into an
   ordinary ticket or analytics.
4. Escalate when specialist review is required. Resolve only after the documented
   platform action or `NO_PLATFORM_ACTION` decision. Reopen to `ACKNOWLEDGED` if
   material information arrives; close only after a final participant message.
5. Any suspected staff misuse, data disclosure, queue outage, or missed urgent
   target becomes a security/operations incident with preserved audit IDs and a
   handoff to the privacy owner.

### Privacy, retention, and review

Internal and participant notes are append-only through the API. Audit events
store actor, resource, status, assignment, priority, resolution, and whether a
public message was recorded; they never copy note bodies. Support closes under
`support-launch-v1` with a 730-day projection. Safety closes under
`safety-launch-v1` with a 1,825-day projection. Legal hold and local law override
automated expiry. A market-scoped `PLATFORM_ADMIN` with
`manage_case_retention` may place one active legal hold per case using a
controlled reason, bounded non-secret authority reference, and review deadline;
release is a separate idempotent, audited command with a controlled reason.

The fixed `case_retention` worker processes only closed cases whose
`retention_until` has elapsed and rechecks the absence of an active hold in the
same locked transaction. It irreversibly removes participant and ride links,
assignment, free text, latest public messages, and notes. It retains only a
non-identifying case shell and one immutable `PERSONAL_DATA_ERASED` action with
city, policy version, due/execution timestamps, and erased-note count so audits,
aggregate categories, and support-to-safety referential integrity do not break.
Processed cases disappear from participant and operations case APIs. The
operations console exposes scoped hold/release controls and erasure evidence;
it never restores erased content. Production certification still requires the
deployment's legal-review ownership, encrypted backup-expiry policy, and a
staging restore exercise proving held records survive and expired erased fields
cannot be recovered after backup expiry.

The operations manager reviews daily: unassigned cases, overdue targets,
reopened/closed counts, safety escalation age, access/audit anomalies, and
active holds approaching or past review, retention actions, and retention items
due. Reports use aggregate controlled categories only and apply
the same small-cell and scope rules as other operational analytics.

## 14. Scaling model

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

## 15. Delivery invariants

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
