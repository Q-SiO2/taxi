# TaxiMobile — Pricing and Fare Specification

## Current standing — 2026-09-02

Versioned city/operator/service tariffs, flat fixed-route fares, scheduling and
operator-fee policies, server-authoritative estimates, and immutable
ride/payment/earning snapshots are implemented in source. No city tariff has
been approved against current local regulation or an operator agreement, and no
controlled field receipt/reconciliation exercise has been accepted. See
[`gaps.md`](gaps.md).

## 1. Purpose

This document defines how TaxiMobile calculates, displays, records, and settles fares for taxi rides.

The pricing system must support the project's central objective:

> TaxiMobile should provide useful digital infrastructure for taxi drivers without requiring artificially low fares or extracting value from drivers through opaque pricing mechanisms.

Pricing must therefore prioritize:

* Transparency.
* Predictability.
* Regulatory compliance.
* Driver sustainability.
* Passenger clarity.
* Separation from ride matching.
* Accurate fare records.
* Auditable calculations.

---

# 2. Core Principle

TaxiMobile is not intended to win customers by artificially making taxi rides cheaper than the underlying taxi market.

The platform should compete primarily through:

```text
Better access
+
Better dispatch
+
Better information
+
Better reliability
+
Better digital services
```

rather than:

```text
Artificially subsidized fares
+
Driver income reduction
```

---

# 3. Pricing and Matching Are Separate

Matching determines:

> Which driver receives the ride?

Pricing determines:

> What does the ride cost?

These must remain separate subsystems.

```text
                    Ride Request
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
       Matching Service       Pricing Service
              │                     │
              ▼                     ▼
        Driver selected       Fare calculated
              │                     │
              └──────────┬──────────┘
                         ▼
                    Ride Offer
```

The matching system must not modify the fare.

---

# 4. Fare and Charge Components

The regulated or configured **transport fare** remains distinct from booking and
operator charges:

```text
base fare
+ distance component
+ time component
+ approved transport supplements
- applicable transport discounts
= transport fare

transport fare
+ scheduling surcharge when applicable
+ passenger-funded operator service fee when configured
+ approved passenger extras
- passenger discounts/subsidies
= passenger total
```

A driver-funded operator fee is already inside the transport fare and appears in
settlement, not as another passenger charge. The exact transport components and
allowed extras depend on the applicable taxi regulations and operating model;
the backend returns each authoritative amount separately.

---

# 5. Regulatory Authority

Where TaxiMobile operates under regulated taxi fares, the application must not invent independent prices that conflict with applicable regulations.

The pricing engine must support configurable regulatory rules.

Examples may include:

* Metered fares.
* Fixed tariffs.
* Zone-based tariffs.
* Airport tariffs.
* Night tariffs.
* Approved supplements.

The final implementation must be validated against the laws and regulations of each operating jurisdiction.

---

# 6. Pricing Models

The architecture should support multiple pricing models.

Initial supported concepts:

```text
METERED
FIXED
ESTIMATED
```

Future models may include:

```text
ZONE_BASED
CONTRACTED
COOPERATIVE_RATE
```

Scheduling is a booking type with its own explicit surcharge policy, not an
ambiguous fare model. It may use a fixed, estimated, metered, or fixed-route
transport fare according to city policy.

---

# 7. Metered Pricing

For a metered taxi, the application may represent the meter state without necessarily replacing the physical meter.

Conceptually:

```text
Ride starts
    │
    ▼
Meter active
    │
    ├── distance changes
    ├── time changes
    └── fare changes
    │
    ▼
Ride ends
    │
    ▼
Final fare
```

If TaxiMobile is ever used as the legally authoritative taximeter, that functionality must be treated as a separate regulated subsystem.

The MVP should not assume that a phone application automatically qualifies as a legal taximeter.

---

# 8. Fixed Fare

A fixed fare may be used when the applicable pricing rules define a known price.

Example:

```text
Airport → City Center
```

could have a configured tariff.

The passenger should see the applicable price before confirming the ride whenever legally and technically possible.

A published fixed-route direction always references a versioned flat transport
fare. Outbound and inbound directions are priced explicitly even when they share
geometry. The first fixed-route release prices the complete selected direction;
it does not infer segment fares from optional stops. Route/fare edits create new
versions and never alter historical bookings.

Route geometry and fare review are separate permissions, but the immutable
direction and fare must form an exact one-to-one link before either can go live.
Both review sequences are supported without guessing identifiers:

```text
Fare first
draft/review unbound FIXED_ROUTE fare
→ route version binds that fare while DRAFT
→ activate fare
→ submit/publish route version

Geometry first
create unpriced DRAFT route direction
→ pricing editor selects that direction ID when creating the fare
→ submit/activate fare
→ submit/publish route version
```

An unpriced direction may exist only as a draft. A fixed-route fare may remain
unbound only in `DRAFT` or `IN_REVIEW`; activation requires the reciprocal
direction link. Route submission requires a linked reviewed fare, and
publication requires an active fare whose effective range covers the complete
route-version range. Activating another direction's fare in the same city and
operator does not replace the first direction's fare.

---

# 9. Estimated Fare

When the final fare depends on variables that are not yet known, the application may display an estimate.

Example:

```text
Estimated fare:
35–45 MAD
```

The UI must clearly distinguish:

```text
Estimated
```

from:

```text
Final
```

The system must never present an estimate as a guaranteed final fare unless it actually is one.

---

# 10. Fare Calculation

The pricing engine should be deterministic.

Given the same:

```text
Tariff version
+
Ride parameters
+
Applicable rules
```

the calculation should produce the same result.

This makes fares reproducible and auditable.

---

# 11. Example Calculation

A simplified example:

```text
Base fare:        10 MAD
Distance:         8 MAD
Time:              5 MAD
Supplement:        0 MAD
------------------------
Total:            23 MAD
```

This is only an example.

Actual values must come from the applicable tariff configuration.

---

# 12. Currency

The initial operating currency is expected to be:

```text
MAD
```

The currency must not be hard-coded throughout the application.

Currency should be represented explicitly in pricing records.

Example:

```json id="o3j8x0"
{
  "amount": 35.00,
  "currency": "MAD"
}
```

---

# 13. Monetary Representation

Money must not be represented internally using floating-point numbers where precision matters.

Prefer:

```text
integer minor units
```

For example:

```text
3500
```

could represent:

```text
35.00 MAD
```

The exact minor-unit representation should follow the currency requirements.

---

# 14. Rounding

Rounding rules must be explicit.

The pricing engine must define:

* When rounding occurs.
* What precision is used.
* Which rounding method is used.

Rounding should occur at defined stages rather than inconsistently throughout the application.

---

# 15. Tariff Configuration

Pricing rules must be configuration-driven.

A tariff should conceptually contain:

```text
Tariff
├── id
├── city_id
├── operator_id
├── service_type
├── optional_fixed_route_direction_id
├── name
├── currency
├── effective_from
├── effective_until
├── base_fare
├── distance_rules
├── time_rules
├── supplements
└── version
```

Pricing selection is scoped by city, operator, service type, booking type,
optional fixed-route direction, and effective time. At most one active rule may
match the same specificity and time. The backend resolves scope from validated
service data rather than trusting a client to choose a cheaper city or policy.

---

# 16. Tariff Versioning

Every ride should be associated with the tariff version used to calculate its fare.

Example:

```text
Tariff v3
effective: 2026-08-01
```

If the tariff changes later:

```text
Tariff v4
effective: 2026-10-01
```

historical rides must remain associated with v3.

Historical fares must never change simply because the current tariff changed.

---

# 17. Effective Dates

A tariff should define when it becomes active.

Conceptually:

```text
Tariff v1
───────────────
Jan 1 → Jun 30

Tariff v2
───────────────
Jul 1 → Dec 31
```

The backend chooses the correct tariff based on the ride's applicable time.

---

# 18. Pricing Snapshot

When a ride begins or reaches a relevant pricing state, the system should preserve a pricing snapshot.

The snapshot should contain the information necessary to explain the fare later.

Example:

```json id="f2g5j4"
{
  "tariff_version": "v3",
  "currency": "MAD",
  "base_fare": 1000,
  "distance_amount": 1800,
  "time_amount": 700,
  "supplements": 0,
  "discounts": 0,
  "total": 3500
}
```

---

# 19. Final Fare

The final fare is determined when the ride reaches its completed pricing state.

Conceptually:

```text
Ride completed
      │
      ▼
Collect final ride data
      │
      ▼
Calculate final fare
      │
      ▼
Freeze fare
```

Once finalized, the fare should not silently change.

Corrections must be represented as explicit adjustments.

---

# 20. Fare Adjustments

Sometimes a fare must be corrected.

Examples:

* Meter malfunction.
* Incorrect route data.
* Approved discount.
* Administrative correction.
* Refund.

The original fare should remain auditable.

Instead of overwriting:

```text
35 MAD → 30 MAD
```

the system should represent:

```text
Original fare: 35 MAD
Adjustment:    -5 MAD
Final charge:  30 MAD
```

The launch implementation supports a post-settlement downward correction as an
append-only payment refund with reason `FARE_CORRECTION`. It never rewrites the
finalized fare and does not support a post-ride increase or automatic new debit.
Before settlement, the client cannot alter the finalized amount; an exceptional
case enters support rather than creating local adjusted pricing.

---

# 21. Fare Breakdown

Passengers should be able to understand what they paid.

A completed ride should expose a breakdown such as:

```text
Base fare                 10 MAD
Distance                   8 MAD
Time                       5 MAD
Supplement                 0 MAD
Scheduling surcharge       0 MAD
Operator service fee       0 MAD
--------------------------------
Total                     23 MAD
```

The exact breakdown depends on the tariff.

For the delivered fixed-tariff model, the completed-fare and receipt APIs expose
an immutable `TRANSPORT_FARE` component, any nonzero scheduled surcharge, and a
nonzero operator fee only when the passenger funds it. Driver-funded operator
fees remain visible in the economics snapshot and driver settlement but are not
presented as a passenger charge. The APIs do not invent distance, time,
supplement, or adjustment components that were not part of the stored
calculation.

---

# 22. Driver Earnings

The amount charged to the passenger and the amount received by the driver must be represented separately.

Conceptually:

```text
Passenger fare
      │
      ├── Driver amount
      │
      └── Platform/cooperative/service amount
```

The system must not assume that the entire passenger payment is automatically platform revenue.

---

# 23. Operator Service Fee

TaxiMobile's approved national model calls this the **operator service fee** and
requires an explicit versioned city/operator policy. Each policy chooses exactly
one calculation mode:

```text
PERCENTAGE_OF_TRANSPORT_FARE
FLAT_PER_COMPLETED_BOOKING
```

The percentage uses a bounded decimal rate and a documented eligible
transport-fare subtotal. Undefined “profit,” tips, tolls, scheduling surcharges,
subsidies, refunds, and payment-provider costs are not the calculation base.
The policy also fixes exact rounding and a non-negative driver-net floor.
A percentage must be at least zero and below 100%; a flat amount must be
non-negative and use the ride currency. An invalid combination is rejected
before activation/quotation. The backend does not silently cap or reinterpret a
fee unless that cap is itself an explicit versioned policy rule.
Each policy also chooses one funding mode:

```text
DRIVER_SETTLEMENT_DEDUCTION
PASSENGER_SURCHARGE
```

With a settlement deduction, the fee is already within the transport fare and
is shown when calculating driver net. With a passenger surcharge, it is added as
a separate passenger-visible component and does not reduce the driver's
transport-fare credit. The first release permits only one operator service fee
per ride, preventing hidden national/local fee stacking.

Example policies (illustrative only):

```text
Transport fare:                 40 MAD
Operator fee (5%, deduction):    2 MAD
Driver net before adjustments:  38 MAD
Passenger total:                40 MAD
```

or, for a passenger-surcharge policy:

```text
Transport fare:                 40 MAD
Operator service fee (flat):     2 MAD
Driver transport-fare credit:   40 MAD
Passenger total:                42 MAD
```

Every quote, offer, completed fare, earning, and settlement snapshots policy
version, base, rate or flat amount, funding mode, currency, and calculated
amount. An explicit zero-fee policy is stored when the operator charges nothing.

## 23.1 Scheduling surcharge

A city may configure a separate flat scheduling surcharge for future bookings.
The passenger sees it before confirmation along with its cancellation/refund
conditions. Its allocation and collection timing are explicit and it is excluded
from the operator percentage base by default. Scheduling a ride never permits an
arbitrary client-provided fee.

---

# 24. No Hidden Operator Fee or Commission

The system should not silently deduct an undisclosed percentage from driver earnings.

Any operator service fee must be:

* Defined.
* Visible.
* Auditable.
* Configurable.
* Communicated to drivers.
* Communicated to passengers when it changes their total.
* Scoped to the applicable city/operator/service.
* Snapshotted independently from the tariff.

---

# 25. Cooperative Model

If the project eventually operates through a cooperative or driver-owned structure, the financial model may differ.

For example:

```text
Passenger payment
       │
       ▼
Cooperative
       │
       ├── Driver compensation
       ├── Operating costs
       ├── Infrastructure
       └── Cooperative reserve
```

The pricing architecture should not assume a conventional venture-capital platform model.

---

# 26. Driver Compensation

The driver compensation system must be separate from the matching algorithm.

Matching decides:

```text
Who receives the ride?
```

Compensation determines:

```text
What amount is credited to the driver?
```

This separation prevents dispatch optimization from silently changing driver pay.

---

# 27. Discounts

Discounts should be explicitly represented.

Example:

```json id="k6ew2p"
{
  "type": "PROMOTIONAL",
  "amount": 500
}
```

Discounts must not modify the underlying tariff.

The system should preserve:

```text
Original fare
Discount
Final passenger charge
Driver compensation
```

according to the applicable business rules.

---

# 28. Promotions

Promotional pricing should not be used to systematically undercut taxi drivers.

Promotions must have:

* Start date.
* End date.
* Eligibility rules.
* Maximum usage.
* Funding source.

The system should know who is absorbing the cost of a promotion.

---

# 29. Subsidies

If an external organization subsidizes rides, the subsidy should be recorded explicitly.

Example:

```text
Actual fare:          40 MAD
Passenger pays:       30 MAD
Subsidy:               10 MAD
Driver compensation:  defined by agreement
```

This prevents subsidized fares from being confused with the actual economic cost of the ride.

---

# 30. Dynamic Pricing

The initial system should avoid uncontrolled dynamic pricing.

In particular, the system should not automatically multiply fares because:

```text
Demand ↑
Supply ↓
```

unless such a mechanism is explicitly permitted and governed.

Matching and demand forecasting may use supply/demand information without automatically changing passenger fares.

---

# 31. Surge Pricing

No automatic surge pricing should be enabled by default.

If dynamic pricing is ever introduced, it must be:

* Explicitly defined.
* Transparent.
* Legally reviewed.
* Bounded.
* Auditable.
* Communicated before confirmation where required.

---

# 32. Waiting Charges

Waiting charges may exist depending on the applicable taxi tariff.

The system should distinguish:

```text
Driving time
```

from:

```text
Passenger-caused waiting time
```

The exact rules must be configured by tariff.

---

# 33. Cancellation Charges

Cancellation charges belong to the pricing/payment domain rather than matching.

The system may calculate a cancellation amount based on:

```text
Who cancelled
When cancellation occurred
Whether driver was already dispatched
Applicable tariff/rules
```

The rules must be explicit.

---

# 34. Toll and Extra Charges

Certain rides may involve approved additional costs.

Examples:

* Tolls.
* Parking.
* Authorized supplements.

These must be separately represented.

Example:

```text
Fare:          40 MAD
Toll:           5 MAD
---------------------
Total:         45 MAD
```

Drivers should not be able to arbitrarily add charges outside the configured rules.

---

# 35. Manual Fare Entry

If the taxi system legally requires a physical meter or manually determined fare, the application may support recording the final meter amount.

Example:

```text
Driver enters:
Final meter fare = 42 MAD
```

The backend should validate the submitted value against applicable constraints where possible.

---

# 36. Meter Integration

Future versions may integrate with physical taxi meters.

Potential architecture:

```text
Taxi Meter
     │
     ▼
Vehicle / Device Interface
     │
     ▼
TaxiMobile
     │
     ▼
Backend
```

This should be treated as a specialized hardware integration.

The MVP should not depend on it.

---

# 37. Fare Estimation

Before confirming a ride, the application may estimate the fare.

The estimate should use:

```text
Pickup
Destination
Applicable tariff
Estimated route
Expected pricing conditions
```

The estimate should clearly indicate uncertainty when the final fare depends on a meter.

---

# 38. Route Dependence

The estimated distance should use a routing service rather than a simple straight-line distance whenever practical.

Straight-line distance:

```text
A ───────── B
```

does not represent actual road distance.

The routing service should provide an estimated route distance and duration.

---

# 39. Route Changes

A passenger may change destination during a ride.

The pricing engine must support recalculation according to the applicable tariff.

The application should not silently change the fare without recording why.

---

# 40. Destination Changes

Destination changes should create an explicit ride event.

Example:

```text
DESTINATION_CHANGED
```

The system should preserve:

```text
Previous destination
New destination
Timestamp
Actor
```

---

# 41. Pricing Events

Important pricing events should be recorded.

Examples:

```text
FARE_ESTIMATED
RIDE_STARTED
TARIFF_SELECTED
WAITING_STARTED
WAITING_STOPPED
DESTINATION_CHANGED
FARE_FINALIZED
FARE_ADJUSTED
DISCOUNT_APPLIED
REFUND_ISSUED
```

---

# 42. Auditability

Every final fare should be explainable.

Given a completed ride, an administrator should be able to determine:

```text
Which tariff was used?
Which version?
Which components were charged?
Which adjustments occurred?
Who authorized adjustments?
What was the final amount?
```

---

# 43. Pricing API

The backend should expose pricing through a dedicated service.

Conceptually:

```text
POST /pricing/estimate
POST /pricing/calculate
GET  /rides/{id}/fare
```

Exact API design belongs to the backend specification.

---

# 44. Fare Estimate Example

Request:

```json id="4s0l7g"
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

Response:

```json id="6c0b4w"
{
  "estimate": {
    "minimum": 30,
    "maximum": 40,
    "currency": "MAD"
  },
  "tariff_version": "v3"
}
```

The actual API may use a different structure.

---

# 45. Price Locking

If the tariff allows a fixed-price ride, the quoted price should be locked when the passenger confirms the ride.

If the ride is metered, the application must clearly communicate that the displayed amount is an estimate.

---

# 46. Passenger Confirmation

Before a passenger confirms a ride, the application should display:

```text
Pickup
Destination
Fare or fare estimate
Currency
Applicable conditions
```

The passenger should understand what they are agreeing to.

---

# 47. Driver Offer

Drivers should also receive sufficient fare information before accepting a ride.

At minimum:

```text
Estimated/fixed fare
Pickup location
Destination or relevant destination information
```

The backend also returns separate scheduling-surcharge, operator-fee, and
expected driver-net components when applicable. A fixed-route offer identifies
the route direction and locked flat fare. The driver application never
reconstructs these values from a percentage stored in client code.

Subject to privacy and operational requirements.

---

# 48. Fare Disputes

Passengers and drivers should have a mechanism to report a disputed fare.

Example:

```text
Passenger
    │
    ▼
Dispute fare
    │
    ▼
Review
    │
    ├── confirmed
    ├── adjusted
    └── rejected
```

A dispute must not simply overwrite the original fare.

---

# 49. Refunds

Refunds should be represented as financial transactions or adjustments.

Example:

```text
Original charge: 40 MAD
Refund:          10 MAD
Net charge:      30 MAD
```

The original transaction remains intact.

The implemented launch refund taxonomy and authorization are defined in
`payments.md`. A refund is recorded only after confirmed return of funds. Partial
and cumulative amounts are exact two-decimal money, cannot exceed the original
completed payment, and remain operator-funded. Phase 14 city/operator economics
does not infer driver recovery from a passenger refund; any later recovery must
be a separately authorized, append-only driver adjustment.

---

# 50. Payment Separation

Pricing determines what is owed.

Payment determines how money moves.

These are separate concepts.

```text
Pricing
   │
   ▼
Amount owed
   │
   ▼
Payment
   │
   ▼
Financial transaction
```

The pricing engine must not directly handle card details.

---

# 51. Payment Methods

The architecture should eventually support:

```text
CASH
CARD
MOBILE_PAYMENT
OTHER_SUPPORTED_METHOD
```

The MVP may initially support only the payment methods realistically available to the project.

---

# 52. Cash Payments

Cash is important for a taxi platform.

A cash ride may follow:

```text
Ride completed
      │
      ▼
Fare finalized
      │
      ▼
Passenger pays driver
      │
      ▼
Ride marked CASH_SETTLED
```

The application should not claim that a cash payment was received merely because the ride ended.

The driver or appropriate party must explicitly confirm settlement.

---

# 53. Cash Settlement

Cash settlement records should include:

```text
Amount
Currency
Timestamp
Ride ID
Driver
Payment status
```

Potential status:

```text
PENDING
CONFIRMED
DISPUTED
```

---

# 54. Electronic Payments

The launch electronic method is external bank/M-Wallet transfer with a
backend-issued reference and authorized manual reconciliation. This avoids a
TaxiMobile gateway subscription/integration fee; it does not imply that the
passenger's or operator's financial institution charges no transfer or account
fee.

Fare calculation is independent of payment method. The transfer claim cannot
change amount, currency, tariff, scheduling surcharge, operator fee, driver net,
or any other immutable fare component. External financial-institution charges
are excluded from the TaxiMobile fare unless a later lawful, approved, versioned
pricing policy explicitly represents them as a passenger-visible component.

Sensitive card information should not be stored directly by TaxiMobile unless there is a compelling, legally compliant reason to do so.

If card processing is introduced later, prefer an approved hosted/tokenized
provider. CMI is deferred and must not influence the current tariff model.

---

# 55. Payment Provider Independence

The pricing architecture should not become tightly coupled to one payment provider.

Conceptually:

```text
Payment Service
      │
      ├── Cash settlement
      ├── Manual bank/M-Wallet reconciliation
      └── Future hosted provider adapter
```

This makes regional deployment easier.

---

# 56. Financial Records

Completed financial records should be immutable in principle.

Corrections should be represented through:

```text
Adjustment
Refund
Reversal
```

rather than silently editing historical transactions.

---

# 57. Financial Precision

Financial calculations must use exact monetary representations.

Never rely on binary floating-point arithmetic for authoritative financial totals.

---

# 58. Time Zones

Pricing events should use a consistent server-side time representation.

The backend should store timestamps in a standardized format, preferably UTC.

The application may display times in the user's local timezone.

---

# 59. Pricing Localization

Pricing rules should support different operating jurisdictions.

Conceptually:

```text
Country
 └── Region
      └── City
           └── Tariff
```

The implemented MVP supports one implicit jurisdiction. The approved national
expansion makes city/operator scope explicit and deploys one configuration
bundle at a time. A tariff active in one city must never match a ride in another
city merely because currency or effective dates overlap.

---

# 60. Pricing Configuration Security

Only authorized administrators should modify active tariffs.

Changes should be audited.

National operation separates draft/edit, review, and activation permissions by
scoped grant. City managers and pricing managers may act only in assigned cities;
market-wide authority is exceptional. Activating a tariff, operator fee,
scheduling surcharge, or fixed-route fare records the scope, actor, policy
version, effective time, and replaced version. City activation verifies a
complete compatible policy bundle.

An ordinary mobile client must never be able to change:

```text
base_fare
distance_rate
time_rate
currency
```

through an API request.

---

# 61. Tariff Approval

A production tariff should ideally pass through an explicit lifecycle:

```text
DRAFT
  │
  ▼
REVIEW
  │
  ▼
APPROVED
  │
  ▼
ACTIVE
  │
  ▼
EXPIRED
```

The exact governance process depends on the operating structure.

---

# 62. Pricing Algorithm Versioning

The pricing calculation implementation should have a version.

Example:

```text
pricing_algorithm_version = "v1"
```

A historical ride should retain the version used to calculate its fare.

---

# 63. Testing

The pricing engine requires automated tests for:

### Basic calculations

```text
Base fare
Distance
Time
Supplements
```

### Rounding

```text
Small amounts
Boundary values
```

### Tariffs

```text
Old tariff
New tariff
Effective date
```

```text
City/operator isolation
Service-type specificity
Fixed-route direction version
No overlapping active rule at equal specificity
Coherent configuration-bundle activation
```

### Adjustments

```text
Discount
Refund
Correction
```

### Edge cases

```text
Zero distance
Very long ride
Destination change
Cancellation
Missing route data
```

```text
Percentage operator fee rounding
Flat operator fee and insufficient fare policy
Passenger surcharge versus driver deduction
Scheduling surcharge cancellation/refund
Zero-fee policy
Historical policy version after city rate change
```

---

# 64. Pricing Invariants

The following rules should always hold:

```text
A final fare must have a tariff version.

A final fare must have a currency.

A final fare must be reproducible.

A ride and scheduled booking must retain city and operator scope.

Operator fee mode, funding mode, base, and version must be explicit.

A scheduling surcharge must be separate from transport fare and operator fee.

Passenger total, driver net, and operator allocation must reconcile exactly.

Historical fares must not change when tariffs change.

Unauthorized clients cannot modify tariffs.

Matching cannot silently modify fares.

Financial adjustments cannot erase the original transaction.
```

---

# 65. MVP Pricing System

The first implementation should aim for:

```text
Tariff configuration
Fare estimation
Fare calculation
Fare breakdown
Tariff versioning
Fare finalization
Fare adjustments
Cash payment recording
Basic electronic payment abstraction
```

Advanced payment integrations can be added later.

---

# 66. Future Pricing Features

Potential future features:

* Physical meter integration.
* Cooperative pricing governance.
* Subscription programs.
* Institutional accounts.
* Corporate transportation.
* Accessibility supplements.
* Tourism/airport tariffs.
* Integrated electronic payments.

Multiple city tariffs, fixed-route flat fares, scheduled-booking surcharges, and
percentage-or-flat operator fees are approved national-expansion scope rather
than unspecified future features. More complex segment fares, pooled-seat
pricing, recurring-booking discounts, and multi-operator revenue sharing remain
future policy work.

---

# 67. Pricing Principles

### Principle 1 — Transparency

Passengers and drivers should understand the fare.

### Principle 2 — No hidden deductions

Driver compensation must be explicit.

### Principle 3 — Regulatory compliance

The system must respect applicable taxi regulations.

### Principle 4 — Reproducibility

Historical fares must be explainable.

### Principle 5 — Separation

Pricing, matching, and payments are separate systems.

### Principle 6 — Driver sustainability

Pricing must not be designed around systematically suppressing driver income.

### Principle 7 — No artificial race to the bottom

TaxiMobile should compete through service and infrastructure rather than unsustainable fare reductions.

### Principle 8 — Auditability

Financial changes must leave an auditable trail.

### Principle 9 — Exact arithmetic

Authoritative monetary values must use precise representations.

### Principle 10 — Configurability

Tariffs must be changeable without rewriting application logic.

## Delivered tariff and city-economics administration

The backend supports fixed tariffs only. An authorized scoped operator creates a
draft, versioned rule, submits it for review, and explicitly activates it.
Activation is audited and
prevents overlapping active schedules by ending an earlier active rule at the new
rule's effective time. Retrospective activation is rejected so a new configuration
cannot silently alter which tariff a historical fare would have selected.

Phase 14 adds city/operator/service/booking scope, optimistic concurrency,
percentage-or-flat operator-fee policies, driver-deduction-or-passenger-surcharge
funding, an explicit zero-fee compatibility policy, and the scheduling-surcharge
foundation. Percentage calculation uses only `TRANSPORT_FARE`, applies the
versioned half-up cent rule, and rejects a result below the configured minimum
driver net instead of silently capping or changing the fee. All authoritative
money uses decimal arithmetic and API decimal strings.

When a passenger confirms a ride, the backend persists the selected tariff,
operator-fee policy, optional scheduling policy, modes, and every exact financial
component in an immutable ride snapshot. Offers reuse that snapshot; completion
finalizes fare and driver earning from it rather than selecting whichever policy
happens to be active later. Database reconciliation constraints cover passenger
total, driver gross/deduction/net, operator allocation, and funding mode.

The legacy administrator tariff endpoints remain a compatibility surface. New
city economics uses the permission-gated `/api/v1/operations` contracts and the
operations web editor. Phase 15 extends those contracts with independently
reviewed, one-to-one complete-direction fixed-route fares and reciprocal draft
link validation. Scheduling policy configuration here still does not make the
scheduled-booking lifecycle available before Phase 16.
