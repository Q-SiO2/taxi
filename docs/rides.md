# TaxiMobile — Ride System Specification

## Current standing — 2026-09-03

Immediate rides, sequential offers, cancellation/completion, payment linkage,
fixed-route direction booking, and the scheduled-booking-to-live-ride handoff
are implemented with backend-owned state and local automated coverage. No
controlled end-to-end ride with real passengers, licensed drivers, production
routing/push, real money reconciliation, support, and network-loss recovery has
been accepted. Closed-code assigned-ride coordination is implemented in source,
but physical-device delivery and real pickup usability remain unaccepted.
Mainstream address/geocoding provider acceptance also remains open; normalized
search/reverse source paths and map fallbacks are implemented. See
[`gaps.md`](gaps.md).

## 1. Purpose

The ride system manages the complete lifecycle of a taxi ride from passenger request to completion or cancellation.

It is responsible for:

* Creating ride requests.
* Finding eligible drivers.
* Dispatching requests.
* Managing driver acceptance.
* Tracking the ride lifecycle.
* Tracking relevant locations.
* Handling cancellations.
* Recording ride completion.
* Connecting rides to payments.
* Maintaining a permanent ride history.
* Connecting scheduled bookings to live rides at dispatch handoff.
* Preserving fixed-route direction and city/operator policy versions.

The backend is authoritative for ride state.

---

# 2. Ride Participants

Every ride has two primary participants:

```text
Passenger
    │
    │
    ▼
  Ride
    ▲
    │
    │
Driver
```

A ride must have:

* One passenger.
* Zero or one assigned driver before completion.
* Exactly one assigned driver once accepted, unless reassignment occurs according to defined rules.

A ride cannot be completed without an assigned driver.

A scheduled booking may have a future driver commitment without yet being a
live ride. That reservation is a separate aggregate and participant relationship;
it creates or assigns the live ride only during the documented dispatch-handoff
window.

---

# 3. Ride Request

A passenger creates a ride request by providing:

### Required

* Pickup location.
* Destination location.

### Optional

* Additional pickup instructions.
* Passenger notes.
* Accessibility requirements where supported.
* Number of passengers where relevant.
* Other information required by local operating rules.

The backend validates the request before creating the ride.

Each request resolves exactly one city, operator assignment, and service type:

```text
ON_DEMAND
FIXED_ROUTE
```

The backend derives city scope from the validated pickup/service boundary or the
selected published fixed-route direction. A client-provided city ID cannot move
a request into a different tariff, operator, or dispatch pool.

Live cancellation, acceptance and driver-state commands use refreshed row locks,
with the ride acquired before offer/driver rows. A passenger cancellation that
waits behind ride start must reject the now-in-progress ride; it cannot overwrite
it using an earlier matching/arrived view. Acceptance followed by cancellation is
permitted before start, preserving both audit events and releasing the driver.
Duplicate acceptance, acceptance after decline/cancellation/offline, and start
after cancellation cannot revive the closed or unavailable work. Expiry and
dispatch follow the same aggregate lock order. See the live-command race matrix
in `testing.md` for verified source behavior and remaining deployment evidence.

Migration `20260903_0048` also enforces at most one active live ride per driver
directly in PostgreSQL. `ACCEPTED`, `DRIVER_EN_ROUTE`, `DRIVER_ARRIVED` and
`IN_PROGRESS` occupy the slot; terminal history and unassigned matching requests
do not. This applies across immediate and scheduled assignments and city scopes.
It complements current-state application locks, not the other way around.

## 3.1 Fixed-route request

A fixed-route request references an immutable published direction version. That
version supplies the city, operator, start, finish, optional stops, static
geometry, and flat transport fare. Outbound and inbound are separate directions.
The passenger may browse this catalog when no taxi is online, but booking still
requires an eligible driver to accept an offer.

The first fixed-route release books the complete selected direction for one flat
fare. Segment pricing is not inferred from intermediate stops.

## 3.2 Scheduled booking

A future pickup is stored as a scheduled booking rather than adding a long-lived
`SCHEDULED` state to the active ride machine. The booking records service type,
pickup/destination or fixed-route direction, requested pickup time, city/operator,
passenger, quote/policy snapshots, and its own lifecycle:

```text
SCHEDULED          → OFFERING | CANCELLED
OFFERING           → DRIVER_COMMITTED | UNFULFILLED | CANCELLED
DRIVER_COMMITTED   → DISPATCH_HANDOFF | CANCELLED
DISPATCH_HANDOFF   → LIVE_RIDE_CREATED | UNFULFILLED | CANCELLED
```

At handoff, the backend revalidates the committed driver or runs the configured
fallback matching policy and creates/assigns a normal live ride atomically. The
passenger must not be told that scheduling guarantees a taxi before the
corresponding backend state supports that statement.

Scheduled offer creation, acceptance, and handoff share a professional-eligibility
check: the account must be active, driver verification approved, the selected
vehicle owned/active/verified, and every known professional credential verified
and unexpired at the decision time. City/service authorization remains an
additional requirement, not a substitute for those facts. Loss of eligibility
after commitment invokes the snapshotted fallback/unfulfilled policy; it cannot
assign a live ride to the suspended or expired participant.

“Account active” includes both the global `users.status` and the independent
driver-profile operating status. Immediate and scheduled assignment commit points
hold shared global-account authority through their transaction, ordered after
the driver lock. Account suspension holds the exclusive user-row lock. A
suspension that commits first blocks immediate acceptance and sends handoff
through fallback/unfulfilled; if assignment commits first, the later suspension
revokes access but preserves that ride as authoritative history. Automatic ride
cancellation or reassignment on suspension is not invented by this lock rule and
must follow the approved support/safety workflow.

Direct committed-driver handoff additionally requires `AVAILABLE` in the booked
city/service and the newest observation to satisfy the configured matching
freshness window and active PostGIS service-area boundary. The existing online
admission tolerance permits at most 60 seconds of future clock skew. Missing,
older, excessively future-dated or outside-area observations, offline/paused/
offered drivers and mismatched live scope invoke fallback/unfulfilled rather
than direct assignment. Initial fallback excludes the failed committed driver;
a future matching cycle still applies normal current-state eligibility. Missing
readiness configuration raises an explicit conflict without changing the booking.
These server checks do not prove road readiness or physical pickup effectiveness;
device/field acceptance remains required under `GAP-007`.

Scheduling commands acquire and reload the booking row before locking its offer,
commitment or driver. Acceptance, decline, cancellation, opening and handoff must
use this order even when invoked directly by a worker/service caller. Reloading
after a lock wait prevents a cached pre-cancellation/pre-handoff state from
authorizing a second transition. Duplicate successful handoff returns the same
live ride; cancellation that wins first prevents handoff, while cancellation
after a completed handoff is rejected and must use the live-ride workflow.
Driver availability and location commands lock and refresh the driver row;
handoff rechecks that row after waiting. Candidate discovery also excludes an
inactive global user. Immediate acceptance, scheduled acceptance and handoff
recheck that global row under the shared status lock. These guarantees have
bounded two-session PostgreSQL evidence, not certification of every cross-domain
race.

Acceptance also has observed-wait evidence for two drivers competing for one
booking and one driver competing for two buffered windows. Exactly adjacent
half-open windows remain allowed. Cancellation frees a protected window only
when its transaction commits; the old commitment remains as cancelled history.
The database exclusion constraint still protects direct writers. Only that
specific overlap is a scheduling conflict; unrelated integrity failures are
rolled back and reported as sanitized internal errors. The acceptance test pack
in `testing.md` records the remaining device/process/field promotion gates.

Immediate dispatch and acceptance now use the active scheduled commitment's
half-open protected range as current authority. Candidate discovery filters a
driver whose range contains server time; after locking a candidate, matching
loads the commitment again. Acceptance performs the same post-lock check to
reject an offer that crossed into the window. Scheduled acceptance holds that
same driver lock and refuses a current-window commitment if a live ride won the
race first. These rules prevent two currently conflicting assignments without
turning a future commitment into live availability or showing supply to a
passenger.

The initial rule has no authoritative predicted completion time for an immediate
ride accepted before the protected range begins. Preventing that ride from later
intruding into the buffer remains a policy and route-duration acceptance item;
source tests may not claim that current-time exclusion solves it.

---

# 4. Pickup Location

The pickup location should contain:

* Geographic coordinates.
* Human-readable address when available.
* Optional place identifier from the mapping provider.

The backend should treat geographic coordinates as the authoritative location.

The displayed address is informational and may change depending on the mapping provider.

---

# 5. Destination

The destination should similarly contain:

* Geographic coordinates.
* Human-readable address when available.
* Optional mapping-provider place identifier.

The destination may be modified only according to the rules of the current ride state.

For example, a destination may be editable before the ride begins but may require different handling once the ride is already in progress.

The exact rules should be defined before implementation.

---

# 6. Ride States

A ride follows a state machine.

The initial state machine is:

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
DRIVER_ARRIVED ──► CANCELLED
```

Additional states may be introduced if real-world requirements demand them.

---

# 7. State Definitions

## 7.1 REQUESTED

The passenger has submitted a ride request.

At this point:

* The passenger is authenticated.
* Pickup and destination have been validated.
* The ride exists in the database.
* No driver has accepted the ride.

The system may immediately transition to `MATCHING`.

---

## 7.2 MATCHING

The dispatch system is searching for an eligible driver.

The system considers drivers according to the dispatch rules defined below.

A ride should not remain in `MATCHING` indefinitely.

If no driver can be found within an appropriate period, the system should notify the passenger and provide an appropriate outcome.

---

## 7.3 ACCEPTED

A participating driver has accepted the ride.

The ride now has an assigned driver.

The system must prevent another driver from simultaneously claiming the same ride.

The backend must atomically establish the assignment.

---

## 7.4 DRIVER_EN_ROUTE

The driver has accepted the ride and is traveling toward the pickup location.

The passenger may receive:

* Driver identity.
* Vehicle information.
* Driver location.
* Estimated arrival time.
* Relevant ride information.

---

## 7.5 DRIVER_ARRIVED

The driver has arrived at or sufficiently near the pickup location.

The application should provide appropriate feedback to both participants.

The driver may transition the ride to `IN_PROGRESS` according to the ride-start rules.

---

## 7.6 IN_PROGRESS

The passenger has entered the taxi and the ride has started.

The system should:

* Track ride status.
* Record appropriate location information.
* Allow the driver to navigate toward the destination.
* Maintain passenger and driver access to the active ride.

---

## 7.7 COMPLETED

The driver indicates that the passenger has reached the destination and the ride is complete.

The backend should:

* Validate the state transition.
* Record completion time.
* Record final ride information.
* Finalize applicable fare information.
* Create or finalize the payment record.
* Make the ride available in ride history.
* Allow appropriate rating/feedback actions.

---

## 7.8 CANCELLED

A ride may become cancelled according to defined cancellation rules.

Cancellation should record:

* Who cancelled.
* When cancellation occurred.
* The ride state at cancellation.
* Cancellation reason where applicable.

The system should distinguish between:

* Passenger cancellation.
* Driver cancellation.
* System cancellation.
* Administrative cancellation.

---

## 7.9 Participant coordination during an assigned ride

TaxiMobile provides a deliberately constrained coordination channel after a
driver is assigned. It is available only in `ACCEPTED`, `DRIVER_EN_ROUTE`,
`DRIVER_ARRIVED`, and `IN_PROGRESS`, and ends immediately when the ride becomes
terminal. `REQUESTED` and `MATCHING` do not reveal or contact candidate drivers.

Passengers may send only:

* `PASSENGER_AT_PICKUP`
* `PASSENGER_NEEDS_MORE_TIME`
* `PASSENGER_CANNOT_FIND_DRIVER`

Drivers may send only:

* `DRIVER_ON_MY_WAY`
* `DRIVER_AT_PICKUP`
* `DRIVER_CANNOT_FIND_PASSENGER`

There is no free-text field, media attachment, calling feature, or personal phone
number disclosure. This reduces unnecessary personal-data exposure and avoids
creating an unstaffed moderation channel. A later communication mode requires a
separate approved privacy, abuse, retention, provider, and operations policy.

The backend is authoritative. It verifies the caller is the ride passenger or
the assigned driver, locks the ride while validating state, enforces role-specific
codes, idempotency, a per-user/per-ride minute limit, and an absolute per-participant
ride cap. The recipient receives a durable account-owned notification and a
privacy-minimized live/push refresh hint. The client then reloads the ride through
the authorized API; a notification payload never changes ride or communication
state directly.

Only the latest accepted signal is included in an active detailed ride response.
It is omitted after completion or cancellation, and delayed delivery is suppressed
after terminal state or the bounded freshness window. Persistence, deletion, and
backup expiry still require a deployment-approved retention schedule.

These signals are convenience aids, not an emergency service. Safety reporting
remains a separate controlled flow, and participants must use local emergency
services when immediate help is required.

---

# 8. Ride State Authority

Only the backend may authoritatively change ride state.

The mobile application may request a transition.

For example:

```text
Driver App
    │
    │ "Start ride"
    ▼
Backend
    │
    ├── Verify driver owns ride
    ├── Verify ride is DRIVER_ARRIVED
    ├── Validate transition
    │
    ▼
IN_PROGRESS
```

The application should never simply change:

```text
ride.status = IN_PROGRESS
```

and assume the operation succeeded.

The server must confirm the transition.

---

# 9. Driver Eligibility

A driver may only receive ride offers when eligible.

Initial eligibility requirements include:

* Driver account is active.
* Driver has completed required verification.
* Driver is currently available.
* Driver is not already handling another ride.
* Driver's vehicle is active and eligible.
* Driver is within the relevant service area.
* Driver has provided sufficiently recent location information.

Additional eligibility rules may be introduced later.

---

# 10. Driver Availability

Driver availability should be explicitly represented.

Initial states:

```text
OFFLINE
AVAILABLE
OFFERED_RIDE
EN_ROUTE
AT_PICKUP
ON_RIDE
PAUSED
```

A driver must explicitly become available before receiving ordinary ride requests.

Being authenticated does not make a driver available.

---

# 11. Driver Location

An available driver should periodically provide their location to the backend.

Location updates should include:

* Latitude.
* Longitude.
* Timestamp.
* Optional accuracy information.
* Optional heading.
* Optional speed.

The exact update frequency should depend on driver state and battery/network considerations.

For example:

```text
AVAILABLE
→ lower-frequency updates

EN_ROUTE
→ higher-frequency updates

ON_RIDE
→ appropriate active-ride frequency
```

The application should avoid sending unnecessary high-frequency GPS data.

Before assignment, no passenger endpoint or map receives online-driver
locations, identities, counts, candidate positions, or availability heatmaps.
Published fixed-route geometry is static public service information and must not
be confused with a taxi's current position.

After a ride has been accepted, the owning passenger may retrieve only the latest
backend-accepted location submitted by that assigned driver after acceptance. The
value includes its observation timestamp and optional accuracy and is presented
as “last known,” not as continuous or guaranteed-current tracking. The backend
does not expose pre-assignment dispatch history, another driver's location, or a
location on a terminal ride. The first coordinate and any manual fallback remain
explicit driver-reviewed foreground actions. Once the driver is backend-confirmed
online, the mobile apps schedule already-authorized one-shot observations every
15 seconds while available/offered and every 10 seconds during an active ride.
This heartbeat runs only while the driver app is in the foreground, stops when
offline/paused/backgrounded/disconnected, never opens a permission prompt, and
backs off for 60 seconds when a platform observation is unavailable. It is not
background or continuous OS tracking. The backend still validates each sample
and stale coordinates never establish dispatch eligibility. Adding background
tracking requires a separate permission, battery, retention, privacy and store
review.

---

# 12. Location Freshness

A driver's location should have a freshness threshold.

A driver whose last known location is too old should not automatically be considered eligible for dispatch.

Conceptually:

```text
Current time
      │
      ▼
Last driver location
      │
      ▼
Is location recent enough?
      │
   ┌──┴──┐
  YES    NO
   │      │
Eligible  Ignore
```

The exact threshold should be configurable.

---

# 13. Dispatch

The dispatch system identifies eligible drivers for a ride.

The initial dispatch algorithm should prioritize simplicity and transparency.

Possible factors include:

1. Distance from pickup.
2. Driver availability.
3. Driver state.
4. Vehicle eligibility.
5. Service area.
6. Relevant cooperative dispatch rules.
7. Driver workload or recent assignments where appropriate.

The first implementation should avoid opaque machine-learning-based matching.

The cooperative should be able to understand why a driver was offered a ride.

---

# 14. Dispatch Radius

The system should initially search within a configurable geographic radius.

For example:

```text
Pickup
   │
   ▼
Search nearby eligible drivers
   │
   ├── Drivers within radius
   │
   └── No drivers
          │
          ▼
     Expand search
```

The radius may expand if no suitable driver is found.

Exact values should be determined during testing and deployment.

They should not be hard-coded into the mobile application.

---

# 15. Ride Offers

When the dispatch system selects a driver, the driver receives a ride offer.

The offer may contain:

* Pickup location.
* Approximate destination information according to applicable policy.
* Estimated distance.
* Estimated travel time.
* Estimated or applicable fare information.
* Passenger information necessary for the ride.

The amount of passenger information revealed before acceptance should be determined by safety, privacy, and operational requirements.

---

# 16. Offer Expiration

A ride offer should have a limited response period.

If the driver does not respond:

```text
Offer
  │
  ├── Accept → ACCEPTED
  │
  ├── Decline → next driver
  │
  └── Timeout → next driver
```

The exact timeout should be configurable.

The backend must prevent expired offers from being accepted.

---

# 17. Concurrent Acceptance

Multiple drivers may theoretically attempt to accept the same ride simultaneously.

The backend must ensure that only one succeeds.

Conceptually:

```text
Driver A ──┐
           │
           ▼
        Backend
           ▲
           │
Driver B ──┘
```

The database transaction must guarantee that the ride cannot be assigned to two drivers simultaneously.

This is a critical consistency requirement.

---

# 18. Driver Rejection

A driver may decline a ride offer.

Declining should normally:

* Remove the offer from the driver's active offers.
* Return the ride to the dispatch system.
* Allow another eligible driver to be considered.

A decline should not automatically be treated as misconduct.

Any future driver-performance rules must be carefully designed so that they do not recreate coercive platform incentives.

---

# 19. Driver Cancellation

A driver may need to cancel after accepting a ride.

The system should record:

* Driver identity.
* Time.
* Current ride state.
* Reason where appropriate.

The ride may then return to dispatch or become cancelled depending on the circumstances.

### MVP implementation policy

The current API implements `POST /rides/{ride_id}/driver-cancel` for the
assigned driver only. It permits cancellation from `ACCEPTED`,
`DRIVER_EN_ROUTE`, and `DRIVER_ARRIVED`, but never `IN_PROGRESS` or a terminal
state. The backend records the driver actor, prior state, time, and required
reason in the immutable ride-event history, changes the ride to `CANCELLED`,
and restores the driver's explicit availability to `AVAILABLE`.

The first implementation does not re-dispatch a driver-cancelled ride. It
creates a passenger notification and a best-effort authenticated refresh hint
after commit. Automatic re-dispatch is deferred until it has a documented
passenger confirmation, expiry, and fairness policy; it must not be added as a
silent retry of a cancelled journey.

The system should avoid automatically penalizing drivers for legitimate circumstances.

---

# 20. Passenger Cancellation

A passenger may cancel a ride before completion.

The system should record:

* Passenger identity.
* Time.
* Current ride state.
* Reason where applicable.

Any cancellation fee must follow applicable regulations and cooperative policy.

Cancellation fees should never be introduced solely as a revenue-maximization mechanism.

---

# 21. Arrival Detection

The system may assist the driver in determining when they have reached the pickup location.

Possible signals include:

* GPS proximity.
* Manual driver confirmation.

GPS should not automatically be treated as proof that the passenger has been picked up.

The driver should retain the ability to confirm arrival.

---

# 22. Starting a Ride

A ride should transition from `DRIVER_ARRIVED` to `IN_PROGRESS` only through a valid backend operation.

The system may eventually support additional confirmation mechanisms such as:

* Driver confirmation.
* Passenger confirmation.
* Ride PIN.
* QR code.

The initial implementation should use the simplest reliable mechanism.

---

# 23. Ride PIN

A future safety feature may provide a short ride verification code.

Example:

```text
Passenger:
"4827"

Driver:
enters 4827
```

The backend verifies the code before allowing the ride to begin.

This helps reduce accidental passenger/vehicle mismatches.

This feature is optional for the first prototype.

---

# 24. Destination Changes

Passengers may need to change their destination after requesting a ride.

The system should define separate rules for:

* Before driver acceptance.
* After driver acceptance.
* Before ride start.
* During the ride.

A destination change may affect:

* Estimated fare.
* Route.
* Estimated arrival time.
* Driver navigation.

The backend must remain authoritative.

---

# 25. Fare Calculation

Fare calculation should be performed independently of the mobile UI.

Conceptually:

```text
Ride
 │
 ├── Distance
 ├── Duration
 ├── Applicable taxi fare rules
 └── Additional permitted charges
          │
          ▼
      Fare Engine
          │
          ▼
        Fare
```

The exact pricing model depends on the jurisdiction and cooperative policy.

The system should support regulated taxi fares where applicable.

Fare rules should be versioned so that historical rides retain the rules used when the ride occurred.

---

# 26. Fare Transparency

Before confirming a ride, the passenger should receive the clearest legally and operationally appropriate fare information.

Depending on applicable taxi regulations, this may be:

* A fixed fare.
* An estimated fare.
* A metered fare.
* A combination.

The same confirmation also shows separate backend components for any scheduling
surcharge and operator service fee. The operator fee is either a documented
percentage of the eligible transport-fare subtotal or a flat amount, and its
funding mode determines whether it is inside driver settlement or added to the
passenger total. The UI must not collapse these into an unexplained fare.

The application must clearly distinguish an estimate from a final fare.

---

# 27. Ride Completion

The driver indicates that the ride has ended.

The backend should verify:

* Driver is assigned to the ride.
* Ride is currently `IN_PROGRESS`.
* The driver is authorized to complete it.

The backend then records:

* Completion timestamp.
* Final location where appropriate.
* Final fare.
* Payment status.

The ride becomes part of the passenger and driver histories.

---

# 28. Payment Relationship

Payment is related to the ride but should remain a separate domain.

Conceptually:

```text
Ride
 │
 └── Payment
      ├── amount
      ├── method
      ├── status
      └── provider information
```

A ride should not be considered successfully paid merely because the passenger application believes payment succeeded.

The backend must receive authoritative payment confirmation.

Ride creation stores one method from the estimate's backend-advertised capability
list. For `MANUAL_TRANSFER`, it also freezes the recipient name and bank and/or
M-Wallet destination so later account rotation cannot rewrite the ride. Ride
completion creates a pending payment. A passenger transfer claim changes only
that payment to processing; authorized statement reconciliation is required for
completion and earning creation. Cash remains independent and uses driver
settlement confirmation.

---

# 29. Ride History

Passengers should be able to view previous rides.

A ride history entry may contain:

* Date.
* Time.
* Pickup.
* Destination.
* Driver.
* Vehicle.
* Fare.
* Payment status.
* Rating status.
* Service type and city.
* Fixed-route direction or scheduled pickup status where applicable.

For a completed passenger ride, `GET /rides/{ride_id}/receipt` is the
authoritative compact receipt read. It returns the finalized fare and payment
method/status only after both records exist. The mobile client must not compose a
receipt from a quote, locally inferred distance, or a presumed cash settlement.
For a manual transfer it also returns the immutable destination and unique
backend reference. `PENDING` and `PROCESSING` must not be shown as paid.

Drivers should similarly be able to view their own ride history.

Historical information must respect privacy requirements.

---

# 30. Ratings and Feedback

After completion, passengers may be allowed to rate the ride.

Potential feedback includes:

* Rating.
* Optional written feedback.
* Safety report.
* Service complaint.

Drivers may also eventually be allowed to provide appropriate feedback regarding passengers.

The implemented MVP starts with a narrower rule: a passenger may submit one
ordinary 1–5 rating, with an optional comment, after a completed ride with an
assigned driver. The rating is visible only to that passenger and assigned
driver, and it cannot influence dispatch, driver eligibility, or earnings.
Driver-to-passenger feedback is deferred until its purpose, visibility, and
anti-retaliation policy are explicitly decided.

Ratings should not become a mechanism for arbitrary economic punishment.

Any use of ratings in cooperative governance or dispatch should be explicitly documented.

---

# 31. Safety Events

A ride may generate safety-related events.

Examples:

* Passenger reports unsafe behavior.
* Driver reports unsafe passenger behavior.
* Accident reported.
* Emergency assistance requested.
* Vehicle problem.
* Route issue.

Safety events should be recorded separately from ordinary ride comments.

Access to sensitive safety information should be restricted.

---

# 32. Ride Data Retention

Ride information may need to be retained for:

* Passenger history.
* Driver history.
* Payment records.
* Legal requirements.
* Dispute resolution.
* Cooperative accounting.
* Safety investigations.

The exact retention periods will be defined in the privacy/security documentation.

The system should not retain detailed location histories indefinitely without a legitimate reason.

---

# 33. Ride Security

Ride operations must be authorized.

Examples:

A passenger may:

* View their own ride.
* Cancel their own ride where permitted.
* View their own ride history.

A driver may:

* View rides assigned/offered to them.
* Accept eligible offers.
* Update rides assigned to them.
* Complete their own active rides.

An administrator may access additional information according to explicit permissions.

A user must never be able to modify another user's ride by manipulating an ID in an API request.

---

# 34. Ride Event History

Important ride state changes should be recorded.

For example:

```text
Ride created
Ride entered matching
Driver offered ride
Driver declined
Ride offered to another driver
Driver accepted
Driver arrived
Ride started
Destination changed
Ride completed
Payment completed
Fixed-route direction version selected
```

Scheduled booking creation, offering, commitment, cancellation, unfulfilled,
and handoff events belong to the separate booking event history. Only the
handoff/live-ride link enters ride history; this prevents a future reservation
from masquerading as an active ride event.

This event history supports:

* Debugging.
* Dispute resolution.
* Safety investigations.
* Cooperative oversight.
* System auditing.

---

# 35. Ride Event Immutability

Once a significant ride event has been recorded, it should not normally be silently overwritten.

Corrections should create new events or audit records where appropriate.

This provides a reliable historical record.

---

# 36. Initial Ride Lifecycle

The minimum viable ride system should support:

```text
Passenger
   │
   ▼
Request ride
   │
   ▼
Find nearby driver
   │
   ▼
Driver receives offer
   │
   ▼
Driver accepts
   │
   ▼
Driver travels to passenger
   │
   ▼
Driver arrives
   │
   ▼
Ride starts
   │
   ▼
Ride completes
   │
   ▼
Fare recorded
   │
   ▼
Payment recorded
   │
   ▼
Ride history
```

The first implementation should focus on making this lifecycle reliable before adding advanced functionality.

---

# 37. Future Ride Features

Potential future features include:

* Multiple passengers.
* Multi-stop trips.
* Accessibility requests.
* Ride sharing between passengers.
* Corporate accounts.
* Recurring rides.
* Airport-specific workflows.
* Intercity taxi journeys.
* Cooperative priority rules.
* Advanced dispatch optimization.
* Ride PINs.
* Emergency workflows.

These features should not be implemented until the core ride lifecycle is stable.

Single future scheduled bookings and city-published fixed routes are now approved
national-expansion capabilities governed by `operations.md` and `roadmap.md`.
Recurring schedules, segment-based shared fares, pooled seats, and intercity
regulatory workflows remain future features.

---

# 38. Core Ride Principles

### Principle 1 — Backend authority

The backend controls ride state.

### Principle 2 — Explicit state machine

Every ride transition must be defined.

### Principle 3 — Atomic assignment

A ride cannot be assigned to multiple drivers simultaneously.

### Principle 4 — Transparent dispatch

Dispatch should initially use understandable rules.

### Principle 5 — Driver fairness

The dispatch system should not intentionally create exploitative incentives.

### Principle 6 — Passenger safety

Identity, vehicle, ride, and safety information should be available where necessary.

### Principle 7 — Privacy

Location information should only be collected and exposed when necessary.

### Principle 8 — Historical integrity

Important ride events should remain auditable.

### Principle 9 — Regulatory compatibility

Fare and operational rules must be adaptable to local taxi regulations.

### Principle 10 — Simple first

Build the basic ride lifecycle before optimizing it.
