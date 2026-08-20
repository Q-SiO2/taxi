# TaxiMobile — Payments

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

The architecture should support:

* `CASH`
* `CARD`
* `MOBILE_PAYMENT`
* Other providers added later.

The MVP may implement only the methods actually available to the project.

The initial TaxiMobile implementation creates a pending `CASH` payment when a tariff-backed ride is completed. A cash payment is not settled merely because the ride completed; it requires a separate backend-authorized settlement action.

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

## Electronic Payments

CMI is the selected electronic card-payment provider. TaxiMobile must use CMI's
hosted payment experience: the backend creates a provider payment session and the
client opens the returned CMI-controlled URL. Raw card numbers, security codes,
and cardholder authentication data must never enter TaxiMobile forms, API bodies,
logs, analytics, or storage.

The CMI adapter remains behind the payment service interface. The exact field
names, request signing, callback authentication, status mapping, timeout behavior,
and reconciliation-file format must be implemented only from the merchant
integration kit supplied during CMI onboarding. Public marketing information is
not a sufficient protocol specification.

The browser/app return URL is user experience only and never marks payment as
complete. Only a cryptographically verified, idempotently processed CMI callback
or a backend-to-CMI status query may change the authoritative payment state.
Unknown or duplicated provider events are recorded safely and do not create a
second charge or earning. Cash remains available independently of CMI outages.

CMI card payment must not be enabled for passengers until the cooperative also
chooses when the charge is authorized/captured relative to dispatch and defines
the cancellation, partial-refund, dispute, and settlement-reconciliation policy.
Those choices determine payment transitions and accounting records and cannot be
guessed from the current cash flow.

## Payment Record

A payment should contain at minimum:

```text
id
ride_id
amount
currency
method
status
created_at
completed_at
provider_reference
```

## Refunds

Refunds must create explicit financial records.

Do not overwrite the original payment.

```text
Original payment: 40 MAD
Refund:           10 MAD
Net:              30 MAD
```

## Driver Settlement

Driver earnings must be recorded separately from the passenger charge.

```text
Passenger charge
       ↓
Financial settlement
       ├── Driver amount
       └── TaxiMobile/cooperative amount
```

The exact revenue model is defined outside this document.

## Security

Payment credentials must never be trusted from the client.

The backend is authoritative for payment status.

Webhook events from payment providers must be authenticated and processed safely.

## MVP earning records

When a cash payment is explicitly settled, TaxiMobile records a separate immutable
driver-earning fact linked to its driver, ride, and payment. The MVP records zero
platform fees and zero adjustments explicitly; it does not infer earnings from a
completed ride. `GET /drivers/me/earnings?from=YYYY-MM-DD&to=YYYY-MM-DD` reports
settled earnings only. Its aggregate totals and count cover the complete date
filter, while its bounded page contains owner-scoped immutable earning rows and
authoritative `settled_at` timestamps. `GET /drivers/me/rides` separately
provides the driver's own paginated operational ride history.

## Invariants

* A payment belongs to a ride.
* A payment has exactly one currency.
* Historical payments are not silently modified.
* Refunds and adjustments remain auditable.
* The client cannot declare a payment successful by itself.
