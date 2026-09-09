# TaxiMobile — Payments

## Current standing — 2026-09-02

Cash, manually reconciled bank/M-Wallet transfer claims, verified/versioned
recipient configuration, scoped operations review, idempotent settlement
decisions, immutable payment provenance, earnings, and operator-funded refunds
are implemented in source. No real recipient, controlled external
transfer/refund, reconciliation roster, statement import, cash-control procedure,
or operator-to-driver payout ledger is deployment-accepted. CMI/card remains
deferred. See [`gaps.md`](gaps.md).

The [synthetic workload runbook](testing_workloads.md) now includes paired
passenger/driver cash completion, same-key settlement replay, receipt and earning
conservation checks over real HTTP/PostGIS. Its zero/flat/percentage fee fixtures
and post-commit HTTP-error cases are local software evidence only; no real cash,
recipient, refund or payout has been accepted by those tests.

## Purpose

Define how TaxiMobile records and processes payments without coupling payment logic to rides, pricing, or the mobile applications.

## Core Principles

* Pricing determines how much is owed.
* Payments determine how money is transferred.
* Payment records must be auditable.
* Cash must be supported.
* Payment providers must be replaceable.
* Sensitive payment information must not be stored unnecessarily.

## Payment Methods

The implemented launch methods are:

* `CASH`, always available.
* `MANUAL_TRANSFER`, an external bank-transfer or interoperable M-Wallet flow
  advertised only when the backend has a verified recipient and destination.

`CARD` and `MOBILE_PAYMENT` remain reserved provider-adapter values. They are not
passenger capabilities and must not be advertised until an approved provider,
commercial agreement, full signed protocol, and reconciliation policy exist.

The fare estimate response is the capability source for a new ride. For every
non-legacy city, the backend resolves the exact active city-configuration service,
its operator assignment, and its referenced `ACTIVE` and currently effective
payment-capability version. A client may render only the returned methods and
sends the selected method with `POST /rides`. Ride creation resolves the same
authority again and snapshots the city, operator, capability, selected method
and, for `MANUAL_TRANSFER`, verified recipient account and displayable
destination. Later configuration changes must not alter those instructions.

Ride completion creates exactly one pending payment using the snapshotted method.
Completing the ride does not settle cash or prove that an external transfer moved.

## Payment Lifecycle

```text
FARE_FINALIZED
      ↓
PAYMENT_PENDING
      ↓
PAYMENT_PROCESSING
      ↓
PAYMENT_COMPLETED
```

Possible failure states:

```text
PAYMENT_FAILED
PAYMENT_CANCELLED
PAYMENT_DISPUTED
```

`PROCESSING` has a precise launch meaning for `MANUAL_TRANSFER`: a passenger has
submitted a claim and an authorized operator has not yet reconciled it. It must
never be presented as paid.

## Cash

For cash rides:

```text
Ride completed
      ↓
Fare finalized
      ↓
Passenger pays driver
      ↓
Driver confirms payment
      ↓
CASH_SETTLED
```

A ride ending must not automatically mean that a cash payment was received.

The passenger receipt read exposes the server-owned `CASH` method and `PENDING`
or `COMPLETED` status after ride completion. It is informational only: neither
participant can alter payment state through the receipt, and `PENDING` must not
be presented as successful payment.

## Cost and Provider Decision Record

As reviewed for the August 2026 launch plan, no card gateway satisfied all of
these requirements at once: Moroccan merchant support, MAD settlement, a complete
obtainable integration contract, and zero setup/subscription/transaction cost.
Stripe's official [global availability list](https://stripe.com/global) does not
list Morocco. PayPal publishes [Morocco merchant
fees](https://www.paypal.com/ma/business/paypal-business-fees), and MAD is absent
from its [standard checkout currency reference](https://developer.paypal.com/reference/currency-codes/).
Neither is a zero-cost MAD replacement for CMI.

Bank Al-Maghrib documents interoperable M-Wallet transfer and merchant-payment
rails under the national mobile-payment ecosystem
([official report](https://www.bkam.ma/content/download/743809/8449478/RSMPIF%202020-V6-web.pdf)).
That establishes a usable external rail, not a promise that every issuer or
account is fee-free. Commercial terms, limits, reference behavior, and recipient
eligibility must be verified with the actual institution before activation.
Provider availability and terms are time-sensitive and must be rechecked before
any later provider decision.

## External Bank and M-Wallet Transfer

There is no assumption that a regulated online payment processor is universally
free. The launch electronic path avoids a TaxiMobile gateway subscription or
per-transaction integration fee by directing the passenger to their existing
bank or M-Wallet application. The passenger's bank, wallet issuer, recipient
institution, or future operator may still charge fees under its own terms. The UI
must not promise a fee-free transfer.

The backend creates a non-secret, unique `TM-...` payment reference and returns
the immutable amount, currency, recipient and configured bank account and/or
M-Wallet destination in the finalized receipt. The passenger performs the
transfer outside TaxiMobile and includes that reference where the external
service permits it. TaxiMobile never asks for a card number, CVV, bank password,
wallet PIN, OTP, statement login, or screenshot of financial information.

The passenger may then submit an optional bounded payer-side reference. This is
only an assertion:

```text
PENDING
  -> passenger submits claim
PROCESSING
  -> authorized operator finds exact amount/currency/reference in the
     recipient's authoritative bank or wallet settlement statement
COMPLETED
```

Submitting a claim cannot produce `COMPLETED`, a receipt marked paid, or a driver
earning. The operator verification command supplies a unique settlement reference,
is idempotent, is audited, and creates the immutable driver earning in the same
transaction as payment completion. A rejected claim records a bounded reason,
returns the payment to `PENDING`, and permits a corrected claim. Only one active
submitted claim may exist for a payment, and a settlement reference cannot settle
two payments.

## Versioned City and Operator Configuration

Migration `20260831_0044` delivers the national payment-configuration authority.
A recipient account belongs to exactly one city and operator, starts as `DRAFT`,
and must contain a recipient name plus a bank account and/or M-Wallet identifier.
Draft fields may be corrected. Verification requires recent operations MFA and
makes the destination immutable; a verified recipient can be retired only when
no active capability references it.

A payment-capability version belongs to exactly one city, operator, and service
type. Its lifecycle is:

```text
DRAFT -> IN_REVIEW -> APPROVED -> ACTIVE -> REPLACED
```

Cash is mandatory in every capability. Manual transfer is enabled only with a
same-city, same-operator verified recipient account. Activation requires an
active operator, a current operator/city/service assignment, a current effective
range, recent MFA, and scoped `MANAGE_PAYMENT_CAPABILITIES` authority. Optimistic
versions reject stale edits and commands. Activating a capability does not expose
it to passengers: the exact capability ID must also be referenced by the active
city-configuration service. Non-legacy cities fail closed when this link is
absent, mismatched, inactive, or outside its effective range.

Replacing an active city configuration marks payment capabilities omitted from
the replacement bundle as `REPLACED`. Historical rides and payments retain their
capability/recipient foreign keys and copied display instructions, so replacement
never rewrites an earlier settlement.

The following environment variables remain only as compatibility for the single
deterministic legacy city:

```text
TAXIMOBILE_MANUAL_TRANSFER_ENABLED
TAXIMOBILE_TRANSFER_RECIPIENT_NAME
TAXIMOBILE_TRANSFER_BANK_ACCOUNT
TAXIMOBILE_TRANSFER_WALLET_ID
```

That legacy fallback fails closed unless explicitly enabled, a recipient is
present, and at least one destination is present. Values are deployment secrets
or protected configuration and must not be committed. No newly created city or
operator may use the fallback.

Configuration staff and settlement staff are separate authorities. Platform,
operator, or city configuration roles with `MANAGE_PAYMENT_CAPABILITIES` manage
recipient/capability versions. A `PAYMENT_RECONCILER` has only
`RECONCILE_PAYMENTS`: it receives a database-paginated queue restricted to the
conjunction of its city/operator grants, verifies or rejects transfer claims,
and records confirmed refunds. Verification and refund recording require a fresh
idempotency key; refund recording also requires recent MFA. Every command is
audited with city/operator provenance. The transitional `/admin/payments/...`
surface remains for the legacy administrator, while the national console uses
the scoped `/operations/payments/...` routes.

## Deferred Card Processing

CMI integration is deferred until well after the cash and manual-transfer product
is functionally and operationally proven. No CMI session, callback, credential,
logo, or simulated success flow belongs in the current product.

Any future card adapter remains behind the payment service interface. Card entry
must use the provider's hosted experience so raw card data never traverses
TaxiMobile. Exact request signing, callback authentication, state mapping,
cancellation/refund behavior, and reconciliation must come from the provider's
merchant integration kit. A browser return URL can never prove payment; only an
authenticated provider event or authoritative provider query may change state.
Cash must continue to work during every provider outage.

## Payment Record

A payment should contain at minimum:

```text
id
ride_id
city_id
operator_id
payment_capability_version_id
payment_recipient_account_id
amount
currency
method
status
created_at
completed_at
provider_reference
```

For `MANUAL_TRANSFER`, `provider` is `MANUAL_RECONCILIATION` and
`provider_reference` is the backend-issued passenger reference. Passenger claims
are separate auditable records containing claimant, optional payer reference,
claim status, review actor/time/reason, and the unique external settlement
reference. Claim data is not payment proof by itself.

## Refunds

The launch refund contract records money only after it has actually been returned.
A passenger opens a `FARE_DISPUTE` support ticket when review is needed; neither
the passenger nor the driver can create, approve, or complete a refund. An
administrator must compare the approved case with independent cash-handover or
outbound-transfer evidence before calling the refund command.

The closed launch reason taxonomy is:

```text
FARE_CORRECTION
DUPLICATE_PAYMENT
SERVICE_RECOVERY
OTHER_APPROVED
```

The settlement method is `CASH` or `EXTERNAL_TRANSFER`. Every completed refund
requires a globally unique, bounded settlement reference. For cash, this is the
controlled signed handover/receipt reference; for an external transfer, it is the
outbound institution reference. The private operator note and settlement
reference are restricted to administrators and must not appear in passenger
receipts, mobile logs, support exports, push payloads, or analytics.

Refunds create append-only `payment_refunds` records. They do not overwrite the
original fare, payment amount, completion timestamp, or earning:

```text
Original payment: 40 MAD
Refund:           10 MAD
Net:              30 MAD
```

Only a `COMPLETED` payment can be refunded. Cumulative refund amount cannot exceed
the immutable payment amount. A partial refund leaves payment status `COMPLETED`
and exposes the refund total and net paid amount on the passenger receipt. When
the cumulative amount reaches the complete payment amount, the payment becomes
`REFUNDED` and records `refunded_at`. A refund cannot create a post-ride debit or
increase the finalized fare.

The launch funding policy is deliberately operator-funded: every refund records
`driver_recovery_amount = 0` and `operator_funded_amount = refund amount`.
Therefore a refund never silently edits or claws back a settled driver earning.
Phase 14 now snapshots the versioned city/operator economics used for the ride,
but it deliberately does not implement refund recovery from the driver. Any such
future recovery requires a separately authorized append-only driver adjustment
linked to that snapshot. The
refund command is idempotent and audited; duplicate settlement evidence is
rejected.

## Driver Settlement

Driver earnings must be recorded separately from the passenger charge.

```text
Passenger charge
       ↓
Financial settlement
       ├── Driver amount
       └── TaxiMobile/cooperative amount
```

The operator-fee and scheduling-revenue policy is defined in `pricing.md` and
`operations.md`; provider payout timing and general-ledger integration remain
separate operational decisions.

For national operation, settlement is derived only from the immutable fare and
fee snapshots defined in `pricing.md` and `operations.md`. It records, as
separate exact-money components:

```text
transport fare
scheduling surcharge and beneficiary
operator service fee and funding mode
driver gross
driver adjustments
driver net
operator allocation
```

The operator service fee may be a percentage of the documented transport-fare
subtotal or a flat per-completed-booking amount. It may be funded by a driver
settlement deduction or a passenger-visible surcharge. Payment and settlement
code must not guess the mode from an amount or merge the scheduling surcharge
into commission.

A scheduled booking may create a payment authorization or fee obligation before
a live ride exists only after the city policy defines collection, cancellation,
expiry, refund, and reconciliation behavior. “Driver not yet committed” and
`UNFULFILLED` are explicit cases; a browser return page or mobile client cannot
decide whether the scheduling surcharge is retained or refunded.

## Security

Payment credentials must never be trusted from the client.

The backend is authoritative for payment status.

Manual-transfer verification requires administrative authorization and evidence
from the recipient's independent settlement source; a passenger assertion is not
evidence. Access to recipient-account statements is an operational privilege and
must not be exposed to mobile clients or copied into ordinary logs.

Future webhook events from payment providers must be authenticated and processed
safely.

## MVP earning records

When a cash payment is explicitly settled, TaxiMobile records a separate immutable
driver-earning fact linked to its driver, ride, and payment. The MVP records zero
platform fees and zero adjustments explicitly; it does not infer earnings from a
completed ride. `GET /drivers/me/earnings?from=YYYY-MM-DD&to=YYYY-MM-DD` reports
settled earnings only. Its aggregate totals and count cover the complete date
filter, while its bounded page contains owner-scoped immutable earning rows and
authoritative `settled_at` timestamps. `GET /drivers/me/rides` separately
provides the driver's own paginated operational ride history. Launch refunds are
operator-funded records and therefore do not alter these earning rows or totals.

## Invariants

* A payment belongs to a ride.
* A payment has exactly one currency and immutable amount.
* Historical payments are not silently modified.
* Refunds and adjustments remain auditable.
* Only confirmed returned money creates a refund record.
* Cumulative refunds cannot exceed the immutable completed payment amount.
* Launch refunds are operator-funded and never imply a driver earning recovery.
* The client cannot declare a payment successful by itself.
* A manual-transfer claim never completes its payment.
* Manual-transfer completion and driver earning creation are one authorized,
  idempotent reconciliation transaction.
* Cash remains available when transfer configuration or an external institution
  is unavailable.
* Every financial record retains city, operator, and applicable policy versions.
* A non-legacy ride uses only the payment capability referenced by its exact
  active city-configuration service.
* A verified recipient is immutable and cannot be retired while an active
  capability references it.
* Passenger total, driver net, and operator allocation reconcile from immutable components.
* Scheduling surcharge and operator service fee are distinct records/components.
* A city/operator change never rewrites a historical settlement.
