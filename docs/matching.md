# TaxiMobile — Ride Matching and Dispatch Specification

## Current standing — 2026-09-03

Deterministic eligibility, ordered offers, decline/expiry handling, leases,
fairness counters, aggregate simulation, worker execution, and city/service
configuration are implemented and locally tested. The system has not passed
representative production load, multi-replica soak, field dispatch, weak-network,
supply-scarcity, or pilot fairness review. A foreground-only online heartbeat is
implemented in source, but its device battery, weak-network and field dispatch
outcomes are not accepted. See [`gaps.md`](gaps.md).

The 2026-09-05 immediate-authority follow-up verifies city suspension/revocation
against immediate offer creation and acceptance in independent PostGIS sessions.
A restriction that wins the driver lock prevents new acceptance; an assignment
that commits first remains history. A locked candidate is skipped for bounded
retry rather than declared absent. Dispatch repeats eligibility after obtaining
driver/global account authority and only then finalizes the candidate. A
regression that previously asserted when global suspension won after discovery
now chooses other eligible supply or safely defers to the matching worker.
The 30-case focused pack is local evidence only; hosted concurrency, performance,
notification timing and field acceptance remain open in `testing.md`.

## 1. Purpose

This document defines how TaxiMobile connects passenger ride requests with available taxi drivers.

The matching system must prioritize:

* Fair access to rides.
* Efficient dispatch.
* Driver livelihoods.
* Passenger reliability.
* Taxi availability.
* Predictable behavior.
* Transparency.
* Resistance to manipulation.
* Regulatory compatibility.

The system must not blindly copy the driver-dispatch incentives used by conventional ride-hailing platforms.

---

# 2. Core Principle

TaxiMobile is designed to support taxi drivers rather than treat drivers as interchangeable gig workers.

The dispatch system should therefore optimize for:

```text
Reliable service
+
Fair distribution of work
+
Efficient passenger pickup
+
Sustainable driver income
```

rather than simply:

```text
Lowest possible driver cost
+
Maximum platform extraction
```

---

# 3. Matching Architecture

The basic flow is:

```text
Passenger
   │
   │ requests ride
   ▼
Ride Service
   │
   ▼
Matching Service
   │
   ├── Find eligible drivers
   ├── Calculate candidate scores
   ├── Apply fairness rules
   ├── Create ride offers
   │
   ▼
Driver(s)
   │
   └── Accept / decline
          │
          ▼
     Ride assigned
```

The matching service is part of the backend.

The mobile application must not perform authoritative matching.

---

# 4. Ride Request

A passenger creates a ride request containing at minimum:

```json
{
  "pickup": {
    "latitude": 34.0209,
    "longitude": -6.8416
  },
  "destination": {
    "latitude": 34.0333,
    "longitude": -6.8326
  }
}
```

The backend creates a unique ride ID.

Initial state:

```text
REQUESTED
```

---

# 5. Matching States

The matching lifecycle is:

```text
REQUESTED
    │
    ▼
MATCHING
    │
    ├── driver found
    │      │
    │      ▼
    │   OFFERED
    │      │
    │      ▼
    │   ACCEPTED
    │
    └── no driver
           │
           ▼
       UNMATCHED
```

The exact internal states may differ from the public ride states.

---

# 6. Eligible Driver

A driver is eligible for matching only if all required conditions are satisfied.

At minimum:

```text
Driver account = ACTIVE
Verification = VALID
Every recorded professional credential = VERIFIED and unexpired
Vehicle = VALID
Driver availability = ONLINE
Driver not currently assigned to another ride
Location = sufficiently recent
Vehicle eligible for requested ride
```

Additional eligibility rules may be added later.

---

# 7. Location Freshness

Driver locations become stale.

The matching system must not treat an old location as current.

Example:

```text
Location age < 10 seconds
    → highly reliable

Location age 10–30 seconds
    → usable with reduced confidence

Location age > configured threshold
    → driver may be excluded
```

The exact thresholds should be configurable.

The system should account for GPS/network conditions rather than assuming perfect location updates.

---

# 8. Geographic Search

The matching system should first identify drivers within a configurable geographic radius.

Example:

```text
Passenger
   │
   ├──── search radius ────┐
   │                       │
   │     Driver A          │
   │
   │           Driver B    │
   │
   │                   Driver C
```

The initial radius should be relatively small.

If no suitable driver is found, the search radius may expand.

---

# 9. Search Expansion

Example:

```text
Radius 1
   │
   └── no suitable driver
          │
          ▼
       Radius 2
          │
          └── no suitable driver
                 │
                 ▼
              Radius 3
```

The expansion must be bounded.

The system must not continuously search indefinitely.

---

# 10. Candidate Filtering

Before scoring candidates, the system should remove drivers who are clearly unsuitable.

Example filters:

```text
Inactive driver
    → exclude

Stale location
    → exclude

Currently on another ride
    → exclude

Invalid vehicle
    → exclude

Driver outside maximum radius
    → exclude
```

Filtering should happen before expensive scoring operations.

---

# 11. Candidate Scoring

Eligible candidates may then be scored.

A conceptual scoring function:

```text
score =
    proximity_score
  + availability_score
  + fairness_score
  + idle_time_score
  + service_compatibility_score
  + geographic_efficiency_score
```

The exact weighting must remain configurable.

---

# 12. Proximity

Drivers closer to the passenger should generally receive a higher proximity score.

However:

> Proximity must not be the only matching criterion.

A system that always selects the nearest driver can repeatedly favor the same drivers in dense areas.

---

# 13. Fairness

The system should incorporate a fairness component.

Drivers who have been waiting for work longer should receive additional consideration.

Conceptually:

```text
Driver A
Idle: 2 minutes
Proximity: 400m

Driver B
Idle: 25 minutes
Proximity: 650m
```

Driver B may be preferable even though Driver A is slightly closer.

---

# 14. Idle Time

Idle time represents how long an available driver has been waiting without receiving a ride.

The system should track:

```text
available_since
```

and calculate:

```text
idle_duration = current_time - available_since
```

Idle time should influence matching.

---

# 15. Fairness Objective

A long-term goal is to prevent situations where:

```text
Driver A gets ride
Driver A gets ride
Driver A gets ride
Driver A gets ride
Driver B waits
Driver B waits
Driver B waits
```

simply because Driver A happens to be slightly closer to each passenger.

The system should instead seek a balance between:

```text
Efficiency
and
Fair distribution
```

---

# 16. Fairness Must Not Override Safety

Fairness must never cause the system to select an unsuitable driver.

For example:

```text
Invalid vehicle
        │
        └── excluded regardless of fairness score
```

Eligibility comes before fairness.

---

# 17. Dispatch Modes

The system should support multiple dispatch strategies.

Initial strategy:

```text
Ranked offers
```

Future strategies may include:

```text
Sequential offer
Broadcast offer
Zone dispatch
Queue dispatch
Cooperative dispatch
```

Scheduled dispatch is now an approved national-expansion strategy. It remains a
separate strategy from the implemented immediate ranked-offer algorithm and must
not be silently enabled by changing one timeout.

The matching engine should be designed so that the strategy can be changed without rewriting the entire ride system.

---

# 18. Initial Dispatch Strategy

The recommended MVP strategy is a small ranked candidate set.

Example:

```text
Ride request
     │
     ▼
Find 10 eligible drivers
     │
     ▼
Rank candidates
     │
     ▼
Offer to best candidate(s)
```

The number of simultaneous offers should be configurable.

---

# 19. Offer Strategy

A ride offer contains:

```text
Ride ID
Pickup location
Estimated pickup distance
Estimated pickup time
Estimated fare
Offer expiration
```

Example:

```json
{
  "id": "offer-uuid",
  "ride_id": "ride-uuid",
  "pickup": {
    "latitude": 34.0209,
    "longitude": -6.8416
  },
  "estimated_pickup_distance_meters": 500,
  "estimated_pickup_time_seconds": 120,
  "estimated_fare": {
    "amount": 35,
    "currency": "MAD"
  },
  "expires_at": "2026-08-10T10:01:00Z"
}
```

---

# 20. Offer Expiration

Every offer must expire.

Example:

```text
Offer created
    │
    ├── driver accepts → ACCEPTED
    │
    ├── driver declines → DECLINED
    │
    └── timeout → EXPIRED
```

The expiration period should be configurable.

---

# 21. Driver Acceptance

When a driver accepts an offer, the backend must atomically verify:

```text
Ride still available?
Driver still eligible?
Offer still valid?
Driver not assigned elsewhere?
```

If all conditions are true:

```text
Ride → ACCEPTED
Driver → ASSIGNED
Offer → ACCEPTED
```

---

# 22. Race Conditions

Two drivers may attempt to accept the same ride simultaneously.

Example:

```text
Driver A ── ACCEPT ──┐
                     │
                     ▼
                  Backend
                     │
Driver B ── ACCEPT ──┘
```

Only one request may succeed.

This must be enforced using a database transaction or equivalent concurrency mechanism.

The client must never determine the winner.

Live command transactions lock and refresh the ride before its offer and driver
rows. This applies to acceptance, decline, passenger cancellation and expiry;
assigned-driver transitions/completion also reload the locked ride and profile.
The ORM's pre-wait cached state cannot authorize a transition. Acceptance's
active-ride lookup is read-only under the driver lock, avoiding a second ride
lock in the opposite order. Matching dispatch admits only `REQUESTED` or
`MATCHING`, never an already operational ride.

Global account containment is also assignment authority. Discovery requires an
active `users` row in addition to the operational driver-profile state. After a
candidate or accepting driver is locked, the command takes `FOR SHARE` on that
user row and retains it through commit; account suspension takes `FOR UPDATE`.
A suspension that wins first removes the candidate or rejects the stale offer.
An assignment that owns shared authority first is allowed to commit before the
subsequent suspension, which revokes later access without erasing ride history.
Clients, bearer-token age and cached profile state cannot choose that winner.

Seven observed two-session PostgreSQL races cover cancellation/acceptance in
both orders, duplicate acceptance, decline before acceptance, offline before
acceptance, and start/cancellation in both orders. Unlike a scheduled booking
after handoff, a live ride remains passenger-cancellable after acceptance until
it starts: acceptance then cancellation are both valid, with an audited terminal
cancellation and released driver. Start that wins first rejects cancellation;
cancellation that wins first rejects start. These are source transaction proofs.
A separate account-authority pack covers candidate exclusion and both
suspension/assignment lock orders for live and scheduled work; neither pack is
independent-process, load, device or public-road acceptance.

---

# 23. Failed Acceptance

If another driver has already accepted the ride:

```text
HTTP 409 Conflict
```

may be returned.

Example:

```json
{
  "error": {
    "code": "RIDE_ALREADY_ACCEPTED",
    "message": "This ride is no longer available."
  }
}
```

The driver application should remove the offer and refresh relevant state.

---

# 24. Declining

Drivers may decline offers.

A decline should not automatically be treated as misconduct.

Drivers may decline because:

* Pickup is inconvenient.
* Passenger destination is unsuitable.
* Driver is about to go offline.
* Driver has another legitimate reason.

The system should distinguish between declining a ride and failing to respond.

---

# 25. No-Penalization Principle

A driver should not be economically punished merely for declining individual rides.

The system should avoid creating a situation where drivers feel forced to accept undesirable trips to protect their account.

An individual driver's decline history or raw acceptance rate must not feed
ranking, eligibility, earnings, access, or account discipline. Service-reliability
review may use accepted-ride cancellations, fraud evidence, safety events, and
other separately governed facts; it must not re-label ordinary declines as
misconduct.

---

# 26. Acceptance Rate

Individual acceptance rate must not be used as a criterion for:

* Account suspension.
* Reduced visibility.
* Reduced earnings.
* Punitive dispatch.
* Loss of access to the platform.

Offer outcomes may be reported only as privacy-bounded city/operator aggregates
for capacity planning. They are not an individual driver score or dispatch input.

---

# 27. Cancellation

Passenger and driver cancellations should be tracked separately.

Example:

```text
PASSENGER_CANCELLED
DRIVER_CANCELLED
SYSTEM_CANCELLED
```

Cancellation reasons may also be recorded.

---

# 28. Driver Cancellation

Drivers should be allowed to cancel an assigned ride when legitimate circumstances arise.

The MVP records this as a terminal `DRIVER_CANCELLED` outcome through the
driver-authorized cancellation endpoint; it does not automatically penalize the
driver or immediately re-offer the cancelled journey. A future re-dispatch rule
must be transparent to both participants and preserve the original cancellation
event.

The system should monitor patterns of abuse without automatically assuming that every cancellation is misconduct.

Potential signals include:

```text
Repeated acceptance followed immediately by cancellation
Repeated suspicious behavior
Fraud indicators
```

These should trigger review rather than automatic punishment where practical.

---

# 29. Passenger Cancellation

Passengers may cancel according to the application's cancellation rules.

Potential cancellation states:

```text
CANCELLED_BY_PASSENGER
CANCELLED_BY_DRIVER
CANCELLED_BY_SYSTEM
```

Cancellation fees, if any, belong to the pricing/payment system and must not be hard-coded into matching logic.

---

# 30. Driver Queue Model

Taxi drivers may operate within geographic queues or taxi stands.

The architecture should support queue-based dispatch in the future.

Conceptually:

```text
Taxi Stand
───────────────
1. Driver A
2. Driver B
3. Driver C
4. Driver D
```

A ride request associated with that stand may be assigned according to queue rules.

---

# 31. Queue Fairness

If a queue model is implemented, drivers who have waited longer should generally receive priority.

The system must define what happens when:

* A driver leaves the queue.
* A driver rejects a ride.
* A driver temporarily goes offline.
* A driver receives a ride outside the queue.
* A driver changes vehicle.
* A driver enters another zone.

These rules must be explicit.

---

# 32. Geographic Zones

The system may divide a city into dispatch zones.

Example:

```text
+---------+---------+
| Zone A  | Zone B  |
|         |         |
+---------+---------+
| Zone C  | Zone D  |
|         |         |
+---------+---------+
```

Zones can be used for:

* Dispatch.
* Analytics.
* Queue management.
* Demand forecasting.
* Driver positioning.

Zones must not prevent drivers from receiving legitimate rides outside their preferred zone unless explicitly configured.

---

# 33. Taxi Stands

Taxi stands may be represented as geographic entities.

A stand could contain:

```text
id
name
latitude
longitude
capacity
active
zone_id
```

Future functionality may allow:

* Drivers to join a stand queue.
* Passengers to request a taxi from a stand.
* Dispatch to prioritize queued drivers.

---

# 34. Street Hailing

The architecture should leave room for traditional street-hail taxi journeys.

A driver may potentially create a ride after picking up a passenger outside the application.

Example:

```text
Passenger flags taxi
        │
        ▼
Driver accepts passenger
        │
        ▼
Driver starts TaxiMobile ride
```

This is important because TaxiMobile should complement existing taxi operations rather than require every passenger interaction to originate inside the app.

---

# 35. Scheduled Bookings

Scheduled service is an approved expansion capability and uses a separate
booking aggregate. It must not place an active ride in `MATCHING` hours or days
before pickup or keep a driver operationally busy for the entire lead time.

Example:

```json
{
  "pickup_time": "2026-08-11T09:00:00Z",
  "pickup": {},
  "destination": {},
  "service_type": "ON_DEMAND"
}
```

The backend validates the city scheduling policy, lead time, horizon, service
area, quote, cancellation terms, and optional fixed-route direction before
accepting the booking. “Scheduled” confirms receipt of a future request, not a
guaranteed driver.

---

# 36. Scheduled Booking Assignment

The city policy defines when offers open, how long they last, when a driver
commitment is due, conflict buffers, fallback matching, and dispatch handoff:

```text
SCHEDULED
    │
    ▼
OFFERING ── decline/expire ──► next eligible driver
    │
    ▼
DRIVER_COMMITTED
    │
    ▼
DISPATCH_HANDOFF
    │
    ├── committed driver revalidated and atomically assigned
    └── documented fallback matching / UNFULFILLED
```

Direct handoff now requires the committed driver to be `AVAILABLE` in the booked
city/service with a current observation inside the active service area, in
addition to professional eligibility and no conflicting active ride. Observation
age uses the configured matching threshold and existing 60-second future-skew
tolerance. If this fails, the first fallback dispatch excludes that committed
driver so the failed direct check cannot be bypassed by immediately offering
the same ride back. Subsequent ordinary matching cycles still check current
eligibility. Normal matching also rejects observations beyond the future-skew
bound. Fallback creates an offer, not an assignment or a guaranteed taxi.

Scheduled offers disclose pickup time, city/service type, pickup and destination
or fixed-route direction, fare/fee/earning components, commitment terms, and
expiration. Drivers have sufficient notice and may accept or decline without a
raw-acceptance-rate penalty. An acceptance transaction rejects overlapping
commitments after configured travel/buffer time. Outside protected windows, a
committed driver may continue receiving ordinary rides.

An **active scheduled protected window at the decision instant** removes that
driver from immediate candidate discovery. Matching repeats the check after it
owns the driver lock, and immediate offer acceptance repeats it again so an
offer created before the window began cannot become an overlapping assignment.
Scheduled acceptance takes the reciprocal driver lock: when its proposed window
already contains the current instant, a concurrently committed active live ride
wins and the scheduled acceptance is refused. If scheduling owns the driver,
matching uses `SKIP LOCKED`, leaves the immediate ride matching, then evaluates
the committed window on retry. Cancellation/release makes the driver eligible
again; terminal commitment history is not deleted.

This instant-of-decision rule does not predict the completion time of an
immediate ride accepted shortly before a future protected window. A wider guard
requires an approved, conservative live-trip-duration/route policy and field
evidence; the backend must not invent an ETA or silently extend city conflict
buffers. Until that policy exists, operations and pilot tests must measure and
stop on immediate rides intruding into committed pickup windows.

Scheduled candidate discovery uses a separate city-scoped driver opt-in and does
not require or imply immediate `AVAILABLE` status. Opt-in is not assignment or
passenger-visible supply. Disabling it blocks new future offers but does not
erase an accepted commitment.

---

# 37. Demand and Supply

The matching system should eventually track:

```text
Demand
= number of ride requests

Supply
= number of eligible available drivers
```

This can help identify:

* Underserved areas.
* Excess driver concentration.
* Peak demand periods.
* Taxi shortages.

Supply observations are internal operational aggregates. They must not power
passenger-facing online-taxi markers, counts, or candidate heatmaps.

---

# 38. Driver Positioning

The system may eventually provide drivers with informational recommendations such as:

```text
High demand nearby
```

However, the system should not forcibly relocate drivers.

Recommendations should remain informational unless a cooperative governance model explicitly defines another mechanism.

---

# 39. Surge Pricing

The initial system should not automatically implement aggressive demand-based surge pricing.

Pricing should be defined independently in `pricing.md`.

Matching may use demand information for dispatch purposes without automatically increasing passenger prices.

---

# 40. Anti-Gaming

The system should anticipate attempts to manipulate matching.

Potential abuse includes:

```text
Fake location
Fake availability
Fake ride requests
Repeated accept/cancel cycles
Multiple accounts
Automated acceptance
GPS spoofing
```

The backend should detect suspicious patterns.

However:

> Anti-abuse mechanisms must not become automatic punishment systems without safeguards.

---

# 41. Location Spoofing

The mobile application cannot be trusted to report truthful GPS coordinates.

The backend should consider:

* GPS consistency.
* Speed.
* Timestamp progression.
* Impossible movement.
* Device signals where legally and technically appropriate.

Suspicious behavior should be flagged.

---

# 42. Fake Ride Requests

The system should protect drivers from malicious passenger accounts generating repeated fake requests.

Potential protections:

* Account verification.
* Rate limiting.
* Behavioral monitoring.
* Cancellation monitoring.
* Fraud detection.

---

# 43. Multiple Accounts

The system should be capable of identifying suspicious account patterns without automatically assuming that every shared device or phone is fraudulent.

Any account-linking mechanism must respect privacy and applicable law.

---

# 44. Driver Privacy

Passenger-facing location information should be minimized.

Passengers generally need enough information to:

* Identify the approaching taxi.
* Estimate arrival.
* Follow the ride.

They do not necessarily need:

* Driver's home location.
* Historical routes.
* Personal phone number.
* Continuous location after the ride.

Before one driver accepts, passengers receive no driver location, online count,
identity, queue position, or candidate list. After acceptance, only the existing
assigned-driver last-known-location contract applies. Published fixed-route
geometry is static catalog data, not evidence of live supply.

---

# 45. Passenger Privacy

Drivers should receive only information necessary to perform the ride.

For example:

```text
Pickup location
Destination
Passenger display information
Relevant ride instructions
```

Unnecessary personal information should not be exposed.

Passengers always retain access to active published fixed-route directions,
start/finish points, and flat fares for their selected city even when no driver
is online. That catalog must clearly distinguish “route is published” from
“driver is assigned.”

---

# 46. Matching Events

Important matching events should be recorded.

Examples:

```text
RIDE_MATCHING_STARTED
DRIVER_CANDIDATE_FOUND
RIDE_OFFER_CREATED
RIDE_OFFER_ACCEPTED
RIDE_OFFER_DECLINED
RIDE_OFFER_EXPIRED
DRIVER_ASSIGNED
MATCHING_FAILED
```

These events support debugging, analytics, and dispute resolution.

---

# 47. Matching Failure

If no suitable driver can be found:

```text
MATCHING
   │
   ▼
No eligible drivers
   │
   ▼
UNMATCHED
```

The passenger should receive a clear status.

The system may optionally continue searching for a configurable period.

---

# 48. Passenger Experience During Matching

The passenger application should display an understandable state.

Example:

```text
Finding a nearby taxi...
```

If matching fails:

```text
No available taxis were found nearby.
```

The application should not claim that a driver is coming until a driver has actually been assigned.

It also does not expose which drivers are online or considering the request.
Fixed-route and scheduled requests use service-specific status copy while
preserving the same privacy boundary.

---

# 49. Driver Experience During Matching

The driver should receive enough information to make an informed decision.

At minimum:

```text
Pickup location
Approximate pickup distance
Estimated pickup time
Estimated fare
Offer expiration
```

Fixed-route offers add direction/start/finish and locked flat fare. Scheduled
offers add pickup time, commitment and cancellation terms, scheduling surcharge,
operator fee, and expected driver net supplied by the pricing/settlement domains.

The driver should not be required to accept blindly.

---

# 50. Transparency

The system should eventually expose useful information to drivers about dispatch.

Possible information:

```text
Why an offer was presented
Approximate pickup distance
Current queue position
Approximate waiting time
```

The exact transparency level may evolve through cooperative governance.

---

# 51. Algorithm Configuration

Matching parameters must not be hard-coded throughout the application.

Configurable values may include:

```text
Initial search radius
Maximum search radius
Location freshness threshold
Offer expiration
Maximum simultaneous offers
Fairness weighting
Idle-time weighting
Proximity weighting
```

These should be centralized.

National configuration is versioned per city and service type. A worker must
load the configuration version captured for the ride/booking; it must not apply
another city's radius, offer timing, or fairness settings.

---

# 52. Algorithm Versioning

Matching logic should have an identifiable version.

Example:

```text
matching_algorithm_version = "v1"
```

When the algorithm changes significantly, the version should change.

This makes it possible to determine which rules produced a historical dispatch decision.

---

# 53. Algorithm Changes

Changes to matching should be tested before production deployment.

Important metrics include:

```text
Average pickup time
Average passenger wait time
Driver idle time
Ride completion rate
Cancellation rate
Ride distribution between drivers
```

Optimization must consider the entire system rather than maximizing one metric.

---

# 54. Fairness Metrics

The system should eventually measure distribution of work.

Possible metrics:

```text
Rides per driver
Revenue per available hour
Average idle duration
Offer count per driver
Acceptance count
Geographic distribution
```

These metrics should be evaluated across appropriate time periods.

---

# 55. Avoiding Perverse Incentives

The system must be careful when using metrics to rank drivers.

For example:

```text
Driver accepts everything
      ↓
Gets higher ranking
      ↓
Accepts even more
      ↓
Other drivers receive fewer rides
```

This creates a feedback loop.

The system should avoid metrics that reward behavior simply because the metric itself causes more opportunities.

---

# 56. Cooperative Governance

Because TaxiMobile is intended to support taxi drivers, significant changes to dispatch rules should eventually be subject to cooperative governance.

Possible process:

```text
Proposal
   │
   ▼
Testing
   │
   ▼
Driver feedback
   │
   ▼
Cooperative decision
   │
   ▼
Deployment
```

The technical architecture should make such changes possible without rebuilding the entire system.

---

# 57. MVP Matching Algorithm

The initial algorithm should be deliberately simple.

Conceptually:

```text
1. Receive ride request.

2. Find eligible drivers within radius.

3. Remove drivers with stale locations.

4. Calculate:
   - pickup distance
   - estimated pickup time
   - idle duration
   - fairness score

5. Rank candidates.

6. Offer ride to configured candidate(s).

7. Wait for acceptance.

8. If accepted:
      assign ride atomically.

9. If declined/expired:
      continue matching.

10. If no candidates remain:
      mark ride unmatched.
```

---

### Implemented deterministic policy

The MVP selects at most the nearest configured candidate-set size (default 10)
after all eligibility filters, then ranks that bounded set using normalized
components:

```text
proximity = 1 - min(pickup_distance / search_radius, 1)
idle      = min(idle_seconds / idle_cap_seconds, 1)
fairness  = 1 / (1 + accepted_assignments_in_lookback)

ranking = weighted_average(proximity, idle, fairness)
```

Defaults are `0.55` proximity, `0.30` idle, and `0.15` fairness, with a
30-minute idle cap and 24-hour accepted-assignment lookback. They are deployment
configuration, not mobile policy. Acceptance rate and declines are deliberately
excluded from the fairness input. Exact ties resolve by longer idle duration,
shorter distance, then stable driver UUID order. The assumed pickup speed is
used only to present an ETA; it is not navigation or fare evidence.

Each offer records the component snapshot and `matching_algorithm_version`.
Only one offer is pending at a time in this initial strategy. Decline or expiry
returns that driver to availability without erasing accumulated wait, excludes
the driver from another offer for the same ride, and immediately advances the
search. Candidate discovery/ranking is read-only; dispatch then tries candidates
in that order, locking and refreshing one driver's full eligibility query at a
time with `SKIP LOCKED`. It does not reserve the whole candidate set. If all
discovered candidates are locked or have changed, the ride remains `MATCHING`
without an offer until the worker retries. A genuinely empty discovery remains
terminal, and the existing overall deadline still bounds deferred searches.
The expiration processor claims a bounded set of rides with due offers or
matching rides without a pending offer
using `SKIP LOCKED`, then locks/rechecks their pending expired offers and driver
profiles in ride-first order. A locked ride is left for a later pass, not processed
through an offer-first lock inversion. The batch bound counts rides, while the
processed count reports expired offers plus offerless matching retry attempts.
Multiple replicas cannot handle the same
claimed ride simultaneously. Exhaustion produces an
explicit terminal `UNMATCHED` ride, notification, and refresh hint. A configured
overall matching timeout (five minutes by default) also bounds a search even if
new drivers continue appearing.

---

# 58. Example Candidate Ranking

Example:

```text
Driver A
Pickup: 300m
Idle: 2 min
Fairness: low

Driver B
Pickup: 500m
Idle: 18 min
Fairness: high

Driver C
Pickup: 800m
Idle: 7 min
Fairness: medium
```

The system should not automatically choose Driver A merely because 300m is the smallest distance.

A weighted ranking may instead select Driver B.

The exact weights should be configured and tested.

---

# 59. Important Constraint

The matching algorithm must never directly manipulate driver earnings in order to optimize dispatch.

Matching determines:

```text
Who receives the opportunity.
```

Pricing determines:

```text
What the passenger pays.
What the driver receives.
```

These concerns should remain separate.

---

# 60. Matching and Pricing Separation

The architecture should be:

```text
Ride Request
      │
      ├──────────────► Pricing Service
      │
      └──────────────► Matching Service
                              │
                              ▼
                         Driver Offer
```

The matching service may read the fare estimate.

It must not independently modify the fare.

---

# 61. Matching and Payments Separation

The matching service must not directly process payments.

Payment functionality belongs to the payment subsystem.

Matching may provide ride information required by payment processing.

---

# 62. Testing

The matching engine must have automated tests for:

### Eligibility

```text
Inactive driver excluded
Stale driver excluded
Busy driver excluded
Invalid vehicle excluded
```

### Ranking

```text
Closer driver ranks appropriately
Idle driver receives fairness consideration
```

### Concurrency

```text
Two drivers accept simultaneously
Only one succeeds
```

### Expiration

```text
Expired offer cannot be accepted
```

### Cancellation

```text
Cancelled ride cannot be accepted
```

### Failure

```text
No available drivers
```

### National expansion

```text
Passenger cannot list online drivers or candidate locations
City A request never offers to City B-only driver
Fixed-route request requires matching city/route authorization
Scheduled offer rejects an overlapping commitment
Scheduled handoff revalidates driver and vehicle eligibility
Decline/expiry advances without punitive ranking input
Unfulfilled schedule remains distinct from a cancelled live ride
```

---

# 63. Simulation

Before deploying the matching algorithm, it should be possible to simulate rides.

A simulation should generate:

```text
Passengers
Drivers
Locations
Ride requests
Acceptances
Declines
Cancellations
```

The purpose is to test whether the algorithm produces unintended behavior.

The repository provides `taximobile-matching-simulation` (or
`python -m taximobile_api.operations.matching_simulation`) for this gate. It
reuses the production scoring function and generates a seeded synthetic city,
drivers, passengers, requests, acceptance/decline decisions, and cancellations.
Inputs are explicit command arguments so policy versions can be compared with
the same seed. The tool has no database/provider dependency and reports only
aggregate results; generated coordinates and participant identifiers are never
written to output.

---

# 64. Simulation Metrics

A simulation should measure:

```text
Passenger wait time
Driver pickup time
Driver idle time
Ride completion rate
Ride distribution
Driver utilization
Cancellation rate
```

It should also identify extreme cases.

The current report includes mean/p50/p95/maximum timing, completion,
cancellation and unmatched rates, completed rides per driver, a ride-distribution
Gini coefficient, mean/minimum/maximum driver utilization, and longest-wait,
pickup, and idle extremes. Simulation is evidence for policy review, not a
production capacity test or proof that its simplified behavior assumptions match
real demand.

---

# 65. Long-Term Goal

The long-term matching system should optimize for a healthy transportation ecosystem rather than maximizing platform extraction.

The target system is:

```text
Passenger
    │
    │ reliable service
    ▼
Taxi Driver
    │
    │ sustainable income
    ▼
Cooperative / Taxi Network
    │
    │ sustainable operation
    ▼
TaxiMobile
```

TaxiMobile should function as infrastructure supporting the participants rather than as a system that requires participants to become economically dependent on the platform.

---

# 66. Matching Principles

### Principle 1 — Backend authority

The backend determines matching results.

### Principle 2 — Eligibility before ranking

Unsuitable drivers cannot win through a high score.

### Principle 3 — Fairness matters

Dispatch should account for driver waiting time and distribution of opportunities.

### Principle 4 — Proximity is not everything

The closest driver is not automatically the fairest choice.

### Principle 5 — No blind punishment

Declining individual rides should not automatically damage a driver's livelihood.

### Principle 6 — Atomic assignment

Only one driver can successfully claim a ride.

### Principle 7 — Transparency

Drivers should eventually understand enough about dispatch to trust the system.

### Principle 8 — Configurability

Matching rules must be configurable rather than scattered throughout the codebase.

### Principle 9 — Measurability

The system must measure both passenger and driver outcomes.

### Principle 10 — Governance

Major changes to dispatch should eventually be compatible with cooperative decision-making.
