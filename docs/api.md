# TaxiMobile — API Specification

## 1. Purpose

This document defines the HTTP API used by TaxiMobile clients and backend services.

The API is the primary communication interface between:

* Android application.
* iOS application.
* Desktop/web clients where applicable.
* Backend services.
* Administrative interfaces.

The API should be designed independently of any particular mobile UI implementation.

The Kotlin Multiplatform application must communicate with the backend through this API rather than directly accessing the PostgreSQL database.

---

# 2. Architecture

The basic communication model is:

```text
Kotlin Multiplatform App
        │
        │ HTTPS
        ▼
   Backend API
        │
        ├── Authentication
        ├── Ride Service
        ├── Driver Service
        ├── Passenger Service
        ├── Payment Service
        ├── Cooperative Service
        └── Notification Service
        │
        ▼
    PostgreSQL
```

The mobile application must never connect directly to PostgreSQL.

---

# 3. API Base URL

Development:

```text
http://localhost:<PORT>/api/v1
```

Production:

```text
https://<production-domain>/api/v1
```

The actual production domain will be defined later.

The API version should be included in the URL.

Example:

```text
/api/v1/rides
```

This allows future versions to coexist when breaking changes are required.

---

# 4. Transport

The production API must use HTTPS.

HTTP may be used during local development.

The API should use JSON for request and response bodies unless a specific endpoint requires another format.

---

# 5. Content Type

Requests containing JSON should use:

```text
Content-Type: application/json
```

Responses should normally use:

```text
Content-Type: application/json
```

File uploads should use an appropriate multipart format.

All API, error, and operational HTTP responses are non-cacheable. They carry
`Cache-Control: no-store` and browser hardening headers so identity, ride,
location, and financial state are not retained by shared intermediaries or
ordinary browser history caches. Production HTTPS responses additionally carry
a bounded HSTS policy; TLS termination must preserve the trusted forwarded
scheme for that decision.

When an explicit browser origin is configured, CORS preflight supports the
documented `GET`, `POST`, `PATCH`, and `DELETE` methods plus `Authorization`,
`Content-Type`, `Idempotency-Key`, and `X-Request-ID`. Staging and production
accept only exact HTTPS origins. Native Android and iOS clients do not use CORS.

---

# 6. Authentication

Authenticated requests should use an access token.

Conceptually:

```text
Authorization: Bearer <access_token>
```

The backend is responsible for validating the token.

The mobile application must not attempt to determine authorization by itself.

---

# 7. Authentication Lifecycle

The general authentication flow is:

```text
Register/Login
      │
      ▼
Backend authenticates user
      │
      ▼
Access token returned
      │
      ▼
Mobile stores token securely
      │
      ▼
Authenticated API requests
```

The exact token implementation may use:

* JWT.
* Opaque access tokens.
* Short-lived access tokens with refresh tokens.

The final implementation should prioritize security and revocation capability.

---

# 8. Authentication Endpoints

## POST /auth/register

Creates a basic user account.

Request:

```json
{
  "display_name": "Example Passenger",
  "phone_number": "+212600000000",
  "email": "user@example.com",
  "password": "a-long-password"
}
```

Response:

```json
{
  "user": {
    "id": "uuid",
    "phone_number": "+212600000000",
    "email": "user@example.com"
  }
}
```

The production implementation must apply appropriate validation.

---

## POST /auth/login

Authenticates an existing user.

Request:

```json
{
  "identifier": "+212600000000",
  "password": "password"
}
```

Response:

```json
{
  "access_token": "token",
  "refresh_token": "token",
  "token_type": "Bearer",
  "expires_in": 900
}
```

---

## POST /auth/refresh

Obtains a new access token.

Request:

```json
{
  "refresh_token": "token"
}
```

Response:

```json
{
  "access_token": "token",
  "refresh_token": "rotated-token",
  "token_type": "Bearer",
  "expires_in": 900
}
```

Registration and login normalize supported Moroccan phone spellings to the
stored `+212` form. The initial API accepts canonical `+212`, `00212`, and
domestic leading-zero forms with ordinary separators; it does not silently
accept arbitrary international numbering plans.

Refresh tokens are rotated. The client must replace its securely stored refresh
token with the returned value before making another refresh request. Reuse of a
previously rotated token revokes the active session family and requires a fresh
login; independent device sessions remain valid.

---

## POST /auth/logout

Invalidates the current session/token where supported.

Response:

```json
{
  "success": true
}
```

---

# 9. Current User

## GET /me

Returns information about the authenticated user.

Response:

```json
{
  "id": "uuid",
  "roles": [
    "PASSENGER"
  ],
  "profile": {
    "display_name": "Example"
  }
}
```

The response should expose only information appropriate to the authenticated user.

---

# 10. Passenger API

## GET /passenger/profile

Returns the passenger's profile.

---

## PATCH /passenger/profile

Updates passenger profile information.

Example:

```json
{
  "display_name": "Example"
}
```

---

# 11. Driver Application

## POST /drivers/apply

Creates a driver application for the authenticated user.

Request:

```json
{
  "display_name": "Driver Name"
}
```

Response:

```json
{
  "driver_id": "uuid",
  "verification_status": "NOT_STARTED",
  "account_status": "PENDING"
}
```

---

# 12. Driver Profile

## GET /drivers/me

Returns the authenticated driver's profile.

Response:

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "display_name": "Driver Name",
  "verification_status": "APPROVED",
  "account_status": "ACTIVE",
  "availability_status": "OFFLINE"
}
```

---

# 13. Driver Verification

## GET /drivers/me/verification

Returns the current verification state.

`submitted_at` is `null` until a verification submission exists. GET and POST
use the same response shape so a client does not infer submission time from a
local action.

Response:

```json
{
  "status": "UNDER_REVIEW",
  "submitted_at": "2026-08-10T10:00:00Z"
}
```

---

## POST /drivers/me/verification

Submits or resubmits driver verification information.

The MVP records a driver application's explicit submission and changes its
verification state to `SUBMITTED`; it is rate-limited and safe to repeat while
already submitted. This is a request for human/cooperative review, not proof of
credentials. Approval is rejected until submission exists. Secure document
upload and the jurisdiction-specific required-document format remain unavailable
until their legal requirements and protected storage adapter are selected.

---

# 14. Driver Credentials

## GET /drivers/me/credentials

Returns the driver's credentials.

Response:

```json
{
  "credentials": [
    {
      "id": "uuid",
      "type": "DRIVER_LICENSE",
      "status": "VERIFIED",
      "expires_at": "2028-01-01T00:00:00Z"
    }
  ]
}
```

Sensitive credential numbers should not be returned unnecessarily.

The implemented self endpoint returns only credential identity, configurable
type, backend verification status, and optional issue/expiry timestamps. It never
returns a credential number, document reference, or document URL. A caller must
own the driver profile; an account without one receives `404`.

---

# 15. Vehicle API

## GET /drivers/me/vehicles

Returns the driver's vehicles.

Response:

```json
{
  "vehicles": [
    {
      "id": "uuid",
      "make": "Example",
      "model": "Example",
      "color": "White",
      "status": "ACTIVE",
      "verification_status": "VERIFIED"
    }
  ]
}
```

---

## POST /drivers/me/vehicles

Registers a vehicle.

Request:

```json
{
  "make": "Example",
  "model": "Example",
  "year": 2025,
  "color": "White",
  "registration_number": "XXXXXX",
  "taxi_identifier": "XXXX"
}
```

---

## PATCH /drivers/me/vehicles/{vehicle_id}

Updates vehicle information while the driver is offline. Any change marks the
vehicle `PENDING` for fresh cooperative verification, so an owner cannot alter
a dispatch-eligible vehicle and remain eligible without review. Duplicate
registration or taxi identifiers are rejected.

---

## DELETE /drivers/me/vehicles/{vehicle_id}

Removes or deactivates a vehicle where permitted.

The MVP never physically deletes a vehicle because rides retain its historical
reference and passenger-facing assignment snapshot. It marks the vehicle
`INACTIVE` while the driver is offline and clears it as the active vehicle if
necessary. An inactive vehicle cannot be selected or used for dispatch.

---

# 16. Driver Availability

## POST /drivers/me/availability/online

Requests that the driver become available.

The backend must verify:

* Driver account is active.
* Verification is valid.
* Required credentials are valid.
* Driver has an eligible vehicle.
* Driver has selected a vehicle.

The current policy treats any recorded non-`VERIFIED` or expired professional
credential as invalid. An empty set remains eligible until the cooperative
defines the jurisdiction-specific required credential types. Credential
eligibility is checked again by matching and offer acceptance.

Response:

```json
{
  "status": "AVAILABLE",
  "vehicle_id": "uuid"
}
```

---

## POST /drivers/me/availability/offline

Requests that the driver go offline.

If the driver is currently completing a ride, the backend should reject the request unless the ride lifecycle permits it.

---

## GET /drivers/me/availability

Returns the current availability state.

---

# 17. Driver Vehicle Selection

## POST /drivers/me/active-vehicle

Selects the vehicle currently being used.

Request:

```json
{
  "vehicle_id": "uuid"
}
```

The backend must verify that the vehicle belongs to the driver and is eligible for use.

The MVP rejects a pending, rejected, expired, or inactive vehicle. A driver can
register a vehicle but cannot make it dispatch-eligible; an authorized
administrator must verify it through `POST /admin/vehicles/{vehicle_id}/verify`.
That decision is auditable, and selecting an eligible vehicle returns the
server-confirmed availability state and active vehicle ID.

---

# 18. Driver Location

## POST /drivers/me/location

Submits the driver's current location.

Request:

```json
{
  "latitude": 34.0209,
  "longitude": -6.8416,
  "observed_at": "2026-08-10T10:00:00Z",
  "accuracy": 8.5,
  "heading": 120.0,
  "speed": 8.2
}
```

Response:

```json
{
  "accepted": true,
  "server_time": "2026-08-10T10:00:00Z"
}
```

The backend should validate:

* Coordinate ranges.
* Timestamp freshness.
* Driver authorization.
* Driver availability/state.

An approved driver with a selected verified active vehicle may submit one
foreground location while `OFFLINE`. This stages the fresh observation required
by `POST /drivers/me/availability/online`; it does not make the driver available
or visible for dispatch. Going online is rejected when the latest accepted
observation is missing or older than the configured matching-freshness interval.

---

# 19. Ride Creation

## POST /rides

Creates a passenger ride request.

Request:

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

Response:

```json
{
  "ride": {
    "id": "uuid",
    "status": "REQUESTED",
    "pickup": {
      "latitude": 34.0209,
      "longitude": -6.8416
    },
    "destination": {
      "latitude": 34.0333,
      "longitude": -6.8326
    }
  }
}
```

---

# 20. Ride Retrieval

## GET /rides/{ride_id}

Returns the current state of a ride.

Response:

```json
{
  "id": "uuid",
  "status": "ACCEPTED",
  "passenger": {
    "id": "uuid",
    "display_name": "Passenger"
  },
  "driver": {
    "id": "uuid",
    "display_name": "Driver",
    "vehicle": {
      "make": "Example",
      "model": "Example",
      "color": "White"
    }
  }
}
```

The backend must only expose information the requesting user is authorized to see.
The authenticated passenger and assigned driver may retrieve the shared ride
detail needed by their mobile coordinators; unrelated passengers, unrelated
drivers, and administrators using this participant endpoint receive `403`.

For an assigned ride, the passenger response includes the assigned driver's
display name and the vehicle snapshot (`make`, `model`, `color`, and optional
taxi identifier). Acceptance atomically binds the driver's verified active
vehicle and copies this limited passenger-facing data to the ride, so later
profile edits or active-vehicle selection cannot rewrite the safety information
for an accepted journey. It does not
expose personal contact details, home address, credentials, or financial data.

While that passenger's assigned ride is in `ACCEPTED`, `DRIVER_EN_ROUTE`,
`DRIVER_ARRIVED`, or `IN_PROGRESS`, the response may also contain:

```json
{
  "last_known_driver_location": {
    "latitude": 34.0209,
    "longitude": -6.8416,
    "observed_at": "2026-08-13T12:00:00Z",
    "accuracy_meters": 7.5
  }
}
```

This is one latest backend-accepted observation, not a live stream. It must have
been submitted by the assigned driver after ride acceptance. Pre-assignment
dispatch observations are never exposed, arbitrary users cannot read the ride,
and terminal ride responses return `null` rather than retaining passenger-visible
location history. Clients must show `observed_at` and must not animate or label
the value as live.

---

# 21. Passenger Ride History

## GET /rides

Returns rides visible to the authenticated user.

Query parameters may include:

```text
?page=1
&limit=20
&status=COMPLETED
```

`status`, when present, must be one exact documented ride-state value. The
`total` applies to the authenticated passenger and selected status filter; an
unknown status is rejected rather than ignored. Collection items never include
the active driver's last-known location—only the authorized detailed ride read
can return that sensitive observation.

Response:

```json
{
  "items": [],
  "page": 1,
  "limit": 20,
  "total": 0
}
```

---

# 22. Ride Cancellation

## POST /rides/{ride_id}/cancel

Cancels a ride where cancellation is permitted.

Request:

```json
{
  "reason": "PASSENGER_CHANGED_MIND"
}
```

Response:

```json
{
  "id": "uuid",
  "status": "CANCELLED"
}
```

The backend determines whether cancellation is permitted.

The mobile client must not decide this independently.

## POST /rides/{ride_id}/driver-cancel

Records a cancellation by the assigned driver before the ride has started.
The request body has the same required `reason` field as passenger
cancellation. The backend verifies the caller owns the assigned driver profile
and the ride is `ACCEPTED`, `DRIVER_EN_ROUTE`, or `DRIVER_ARRIVED`; it records
the actor, previous state, timestamp, and reason in the ride event history.

The MVP makes this terminal: it does not silently re-dispatch the passenger.
It returns the driver to `AVAILABLE`, creates a participant-owned passenger
notification, and sends a best-effort `RIDE_CANCELLED` refresh hint after the
transaction commits. Re-dispatch needs a separate passenger communication and
offer-expiry policy. This endpoint requires the normal 16â€“128-character
`Idempotency-Key` header.

---

# 23. Driver Ride Offers

## GET /drivers/me/ride-offers

Returns currently available ride offers.

Response:

```json
{
  "server_time": "2026-08-10T10:00:20Z",
  "offers": [
    {
      "id": "uuid",
      "ride_id": "uuid",
      "pickup": {
        "latitude": 34.0209,
        "longitude": -6.8416
      },
      "estimated_pickup_distance_meters": 1200,
      "estimated_pickup_time_seconds": 300,
      "estimated_fare": {
        "amount": "35.00",
        "currency": "MAD"
      },
      "matching_algorithm_version": "mvp-v1",
      "issued_at": "2026-08-10T10:00:15Z",
      "expires_at": "2026-08-10T10:01:00Z"
    }
  ]
}
```

Pickup distance/time are backend estimates captured when the offer is created;
the fare is the ride's locked server quote. They inform the driver but do not
advance the ride or alter pricing. WebSocket/FCM hints prompt the app to reload
this authorized collection; polling remains a recovery path.

`server_time`, `issued_at`, and `expires_at` form the authoritative display-timing
envelope. A client may derive a countdown from the server-relative remaining and
total durations, then advance it only with local monotonic elapsed time. At local
zero it disables Accept and refreshes this collection; it must not mark the offer
expired, alter availability, or advance matching itself. The backend remains
authoritative and rejects late acceptance atomically.
If any value in the timing envelope is malformed or the issued-to-expiry duration
is non-positive, the client also disables Accept, presents timing as unavailable,
and requests one authoritative collection refresh. It must not fall back to the
device wall clock or expose an undated offer as safely acceptable.

---

# 24. Accept Ride Offer

## POST /ride-offers/{offer_id}/accept

Attempts to accept a ride offer.

Response:

```json
{
  "ride_id": "uuid",
  "status": "ACCEPTED"
}
```

The backend must perform this operation atomically.

If another driver has already accepted the ride, the request must fail with an appropriate conflict response.

---

# 25. Decline Ride Offer

## POST /ride-offers/{offer_id}/decline

Declines an offer.

Request:

```json
{
  "reason": "DRIVER_DECLINED"
}
```

Response:

```json
{
  "success": true
}
```

Declining a ride must not corrupt the ride state.

The transaction marks this offer `DECLINED`, restores the driver to `AVAILABLE`
without resetting the existing `available_since`, records the event, and offers
the ride to the highest-ranked eligible driver who has not already received it.
If no untried candidate remains, the ride becomes `UNMATCHED`. A periodic,
replica-safe processor applies the same continuation after offer expiry.

---

# 26. Driver Arrived

## POST /rides/{ride_id}/arrived

Indicates that the driver has reached the pickup area.

Response:

```json
{
  "ride_id": "uuid",
  "status": "DRIVER_ARRIVED"
}
```

The backend should validate that:

* The driver is assigned to the ride.
* The ride is in an appropriate state.
* The driver's location is reasonably compatible with the pickup location where applicable.

## POST /rides/{ride_id}/en-route

Moves an assigned ride from `ACCEPTED` to `DRIVER_EN_ROUTE`. This explicit driver command keeps the published ride-state sequence intact before the arrival transition.

---

# 27. Start Ride

## POST /rides/{ride_id}/start

Starts the ride.

Response:

```json
{
  "ride_id": "uuid",
  "status": "IN_PROGRESS",
  "started_at": "2026-08-10T10:05:00Z"
}
```

Only the assigned driver should normally be able to start the ride.

---

# 28. Complete Ride

## POST /rides/{ride_id}/complete

Completes the ride.

Request:

```json
{
  "latitude": 34.0333,
  "longitude": -6.8326
}
```

Response:

```json
{
  "ride_id": "uuid",
  "status": "COMPLETED",
  "fare": {
    "amount": 35.00,
    "currency": "MAD"
  }
}
```

The backend should calculate and finalize the fare.

The client must not be trusted to submit the final fare.

## POST /rides/{ride_id}/payments/cash/settle

The assigned driver confirms settlement of a pending cash payment after the ride has completed. The backend verifies driver ownership, completed ride state, payment method, and pending payment status before recording settlement.

---

# 29. Ride State Machine

The backend must enforce the ride lifecycle.

Conceptually:

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
DRIVER_ARRIVED
    │
    ▼
IN_PROGRESS
    │
    ▼
COMPLETED
```

Cancellation may occur from appropriate states:

```text
REQUESTED ───────► CANCELLED
MATCHING ────────► CANCELLED
ACCEPTED ────────► CANCELLED
DRIVER_ARRIVED ──► CANCELLED
```

The backend must reject invalid state transitions.

`MATCHING` may also transition to terminal `UNMATCHED` after the bounded
candidate set is exhausted. This is distinct from cancellation, lets the
passenger start a new request, and prevents a request from remaining in
`MATCHING` indefinitely.

---

# 30. Fare Estimate

## POST /rides/estimate

Provides an estimated fare before a passenger confirms a ride.

Request:

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

Response:

```json
{
  "estimate": {
    "amount": 35.00,
    "currency": "MAD",
    "pricing_rule_version": "v1"
  }
}
```

An estimate is not necessarily the final fare.

For the MVP fixed-tariff model, the same server-selected tariff is persisted when
the passenger creates the ride. `GET /rides/{ride_id}/fare` returns the finalized
amount, tariff version, and only the components recorded in that fare's immutable
snapshot to that ride's passenger. A tariff activated later cannot change this
ride's locked tariff or its historical fare record.

## GET /rides/{ride_id}/receipt

Returns the authenticated passenger's finalized receipt after the ride has
completed. It combines server-owned fare and payment records; it does not
create, settle, or adjust a payment.

```json
{
  "ride_id": "uuid",
  "completed_at": "2026-08-10T18:30:00Z",
  "fare": {
    "amount": "35.00",
    "currency": "MAD",
    "pricing_rule_version": "v1",
    "components": [
      {"code": "BASE_FARE", "label": "Base fare", "amount": "35.00"}
    ]
  },
  "payment": {
    "method": "CASH",
    "status": "PENDING"
  }
}
```

The endpoint returns `404` until the completed ride has both a finalized fare
and a payment record. It deliberately excludes payment IDs, provider references,
and any other participant's private data. A `PENDING` cash status means only
that the driver has not yet completed the separate backend-authorized settlement
action; the client must not describe it as paid.

---

# 31. Ratings

## POST /rides/{ride_id}/rating

Creates a rating after an eligible ride.

Request:

```json
{
  "score": 5,
  "comment": "Good service."
}
```

The backend should verify that:

* The ride exists.
* The ride is completed or otherwise eligible.
* The requester participated in the ride.
* The requester has not already submitted the relevant rating.

### MVP rating policy

The initial implementation permits exactly one **passenger-to-assigned-driver**
rating for a completed ride. It stores a score from 1 through 5 and an optional
comment. The passenger and the assigned driver may retrieve the rating for that
ride, but the response intentionally does not expose reviewer or reviewed-user
identifiers. A rating is ordinary service feedback: it does not alter matching,
driver eligibility, earnings, or cooperative governance. Safety reports and
support cases are separate protected domains.

---

## GET /rides/{ride_id}/ratings

Returns ratings that the requester is authorized to view.
The integration gate proves that the assigned driver can read the passenger's
score and comment, an unrelated driver receives `403`, and the response contains
no reviewer or reviewed-user identifiers.

---

# 32. Driver Earnings

## GET /drivers/me/earnings

Returns driver earnings.

Query parameters:

```text
?from=2026-08-01
&to=2026-08-10
```

Response:

```json
{
  "currency": "MAD",
  "gross": 1200.00,
  "fees": 120.00,
  "adjustments": 0.00,
  "net": 1080.00,
  "settled_through": "2026-08-10T18:00:00Z",
  "count": 1,
  "page": 1,
  "limit": 20,
  "items": [
    {
      "id": "uuid",
      "ride_id": "uuid",
      "gross": 1200.00,
      "fees": 120.00,
      "adjustments": 0.00,
      "net": 1080.00,
      "currency": "MAD",
      "settled_at": "2026-08-10T18:00:00Z"
    }
  ]
}
```

Totals and `count` cover the complete authorized date filter; `items` is the
bounded page selected by `page` and `limit` (maximum 100). Every amount and
settlement timestamp is an immutable backend accounting fact. The exact revenue
policy remains defined in `payments.md`.

---

# 33. Driver Ride History

## GET /drivers/me/rides

Returns rides completed or handled by the driver.

Query parameters may include:

```text
?page=1
&limit=20
&status=COMPLETED
```

---

# 34. Cooperative Membership

## GET /cooperative/membership

Returns the authenticated user's current non-ended cooperative membership. The
membership is looked up independently of driver approval and account roles. A
caller without a current membership receives `404`. If inconsistent data would
produce more than one current membership, the API returns `409` instead of
silently choosing one.

Response:

```json
{
  "cooperative_id": "uuid",
  "cooperative_name": "Example Taxi Cooperative",
  "status": "ACTIVE",
  "joined_at": "2026-01-01T00:00:00Z",
  "membership_number": "MEMBER-123"
}
```

---

# 35. Cooperative Proposals

Future governance functionality may include:

## GET /cooperative/proposals

Returns proposals visible to the authenticated member.

## POST /cooperative/proposals

Creates a proposal where the member has permission to do so.

## POST /cooperative/proposals/{proposal_id}/vote

Records a member's vote.

Request:

```json
{
  "vote": "YES"
}
```

The backend must verify voting eligibility.

---

# 36. Notifications

## GET /notifications

Returns notifications for the authenticated user.

Query parameters:

```text
?page=1
&limit=20
&unread=true
```

---

## POST /notifications/{notification_id}/read

Marks a notification as read.

---

# 37. Device Registration

## POST /devices

Registers a mobile device for push notifications.

Request:

```json
{
  "platform": "ANDROID",
  "registration_kind": "FIREBASE_INSTALLATION_ID",
  "registration_id": "firebase-installation-id"
}
```

Possible platforms:

```text
ANDROID
IOS
```

New Android and iOS clients register Firebase Installation IDs (FIDs), following
the current FCM direct-targeting contract. `LEGACY_FCM_TOKEN` remains a temporary
stored registration kind only so rows created by an older application can still
be delivered during upgrade. The server selects the HTTP v1 `fid` or deprecated
`token` target field from the stored kind.

A provider registration has one current TaxiMobile account owner. Re-registering the
same kind and identifier while authenticated as another account atomically transfers that
single device row, reactivates it, and preserves its stable device ID. It never
leaves both accounts able to address the same app installation.

## DELETE /devices

Revokes background delivery to the submitted device for the authenticated
owner. The request uses the same `platform`, `registration_kind`, and
`registration_id` fields as registration
and returns `204 No Content`. Revocation is idempotent and always returns the
same response when the registration is absent, already revoked, or owned by another
account or session, preventing ownership probing. Mobile logout attempts this operation
before revoking the session, but local logout still completes if the network is
unavailable.

Registration binds the installation to the current authenticated session. A
newer session may reclaim the same installation, but a `DELETE /devices` request
from the older session then has no effect. `POST /auth/logout` also revokes every
active push registration still bound to the session in the same database
transaction as session revocation.

### MVP notification policy

The backend persists minimal notification history for ride offers and driver
assignment, and a user may list or mark only their own notifications as read.
Payload data is limited to resource IDs that the receiving user must still
authorize through the normal API. Device registration stores an Android or iOS
FID (or transitional legacy token) for the configured FCM adapter. It does not imply that Firebase credentials
are configured or that delivery occurred. The transactional-outbox processor
reloads current authorized ride data before sending best-effort WebSocket and FCM
refresh hints. FCM `UNREGISTERED`, invalid-registration, and FID `NOT_FOUND`
responses revoke the stored registration;
transient failures use bounded outbox retry. A delivery response is not a claim
that a person saw a notification.

After the deployment-configured maximum attempt count, the refresh hint enters a
terminal dead-letter state and is no longer claimed automatically. This does not
alter the notification or ride exposed through the API. Operators inspect only
event identifiers, topics, attempt counts, timestamps, and fixed outcome codes;
replay is an explicit incident action after the provider or credential failure is
resolved.

The native clients must tolerate Firebase producing an installation ID before an
authenticated TaxiMobile session exists. They keep the latest ID in volatile
process memory and retry this endpoint after successful login/session restore;
the same installation is registered again when a different account signs into the same
running app. Device registration remains best effort and cannot make login or
account creation fail.

The native receive path treats FCM data as a bounded wake-up hint, not a state
transition. Android `onMessageReceived` and the iOS background notification
delegate accept only `RIDE_OFFER_AVAILABLE`, `DRIVER_ASSIGNED`, `RIDE_CANCELLED`,
or `RIDE_UNMATCHED` with a canonical ride UUID. The process retains at most the
latest unconsumed hint and an authenticated screen responds by reloading through
the normal ownership-checked APIs. Unknown fields, unknown event types, and
malformed identifiers do not trigger a refresh and are not logged.

---

# 38. Support

## POST /support/tickets

Creates a support ticket.

Request:

```json
{
  "category": "RIDE_PROBLEM",
  "subject": "Problem with ride",
  "description": "Description of the problem.",
  "ride_id": "uuid"
}
```

---

## GET /support/tickets

Returns the authenticated user's support tickets.

---

## GET /support/tickets/{ticket_id}

Returns a support ticket the user is authorized to access.

### MVP support policy

The initial API creates and returns only tickets owned by the authenticated
participant. A ticket may reference a ride only when the requester is that
ride's passenger or assigned driver; arbitrary ride IDs are rejected. The
allowed categories are `RIDE_PROBLEM`, `FARE_DISPUTE`, `ACCOUNT_ACCESS`, and
`OTHER`, and new tickets begin as `OPEN`. The implementation intentionally does
not expose administrative triage, assignment, priority, safety reporting, or
financial adjustment endpoints until their operating policies are defined.

---

# 39. Error Format

API errors should use a consistent structure.

Example:

```json
{
  "error": {
    "code": "RIDE_ALREADY_ACCEPTED",
    "message": "This ride has already been accepted.",
    "details": {}
  }
}
```

The `code` should be machine-readable.

The `message` should be safe to display or translate.

`details` may contain additional structured information.

Validation failures expose only each rejected field location and a stable
machine-readable validation code. Pydantic's raw `input`, validator context, and
submitted values are removed before serialization, so a rejected password,
token, coordinate, contact identifier, or free-text field is never reflected in
the error response.

Unexpected server failures return the same envelope with code `INTERNAL_ERROR`
and the safe message `An unexpected error occurred.` They include an
`X-Request-ID` response header for support correlation. Exception messages,
tracebacks, credentials, provider payloads, and private business data are never
returned to the client. The backend records only allowlisted request metadata and
the exception class for this failure path.
Clients may supply a canonical UUID in `X-Request-ID`; malformed, non-canonical,
or free-text values are replaced with a server-generated UUID before entering a
response or log.

## Operational metrics

`GET /internal/metrics` is outside the public versioned API and excluded from
OpenAPI. When `TAXIMOBILE_MONITORING_TOKEN` is configured, it requires that value
as a bearer token and returns Prometheus-compatible per-process request counts,
latency histograms, and unhandled-error counts. With no token in development it
returns `404`; invalid credentials return `401`. Staging and production refuse to
start without a 32+ character token.

Metric labels contain only a controlled HTTP method, the FastAPI route template,
status class, histogram boundary, or safe exception class. Raw URL paths, query
strings, request IDs, account identifiers, ride IDs, coordinates, provider
details, and exception messages are never labels.

---

# 40. HTTP Status Codes

The API should use conventional HTTP status codes.

Examples:

```text
200 OK
201 Created
204 No Content
400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
409 Conflict
422 Unprocessable Entity
429 Too Many Requests
500 Internal Server Error
```

The exact status should reflect the actual failure.

---

# 41. Authorization

Authentication and authorization are separate.

A valid authenticated user must not automatically have permission to perform every operation.

For example:

```text
Passenger
 ├── Can create ride
 ├── Can cancel own ride
 └── Cannot accept driver offers

Driver
 ├── Can accept own offers
 ├── Can update own location
 └── Cannot modify another driver's profile

Admin
 └── Has additional administrative permissions
```

Authorization must be enforced by the backend.

---

# 42. Object Ownership

The backend must verify ownership for user-specific resources.

For example:

```text
GET /drivers/me/rides
```

must only return the authenticated driver's rides.

A client must not be able to change:

```text
driver_id=another_driver
```

simply by modifying a request body.

---

# 43. Idempotency

Operations that can safely be repeated should support idempotency where necessary.

This is especially important for:

* Ride creation.
* Payment operations.
* Ride completion.
* Cancellation.

Example:

```text
Idempotency-Key: unique-client-generated-value
```

A repeated request with the same key should not accidentally create duplicate business operations.

The MVP requires an `Idempotency-Key` header containing 16–128 characters for
`POST /rides`, `POST /rides/{ride_id}/cancel`,
`POST /rides/{ride_id}/driver-cancel`,
`POST /rides/{ride_id}/complete`, and
`POST /rides/{ride_id}/payments/cash/settle`. A retry with the same authenticated
user, operation, key, and request body returns the original response. Reusing a
key for a different request is rejected. Clients must preserve the key for a
network retry of the same user action and generate a new key for a new action.

---

# 44. Concurrency

The backend must assume that multiple clients may act on the same resource simultaneously.

Example:

```text
Driver A ── accept ──┐
                     ├──► Ride
Driver B ── accept ──┘
```

Only one driver may successfully obtain the ride.

This must be enforced server-side using appropriate transaction and concurrency mechanisms.

---

# 45. Pagination

Collection endpoints should support pagination.

Example:

```text
?page=1&limit=20
```

Responses should provide enough metadata for clients to navigate results.

Large datasets must not be returned in a single request.

---

# 46. Filtering

Where appropriate, collection endpoints may support filtering.

Example:

```text
GET /rides?status=COMPLETED
```

Filtering parameters must be validated by the backend.

Clients must not be able to construct arbitrary database queries through filter parameters.

---

# 47. Sorting

Collection endpoints may support controlled sorting.

Example:

```text
?sort=created_at
&order=desc
```

The backend should use an allowlist of sortable fields.

---

# 48. Rate Limiting

The API should implement rate limiting.

Particularly sensitive endpoints include:

* Login.
* Registration.
* Password operations.
* Ride creation.
* Ride cancellation.
* Verification submission.
* Support creation.

Rate limits should be configurable.

The initial deployment reads explicit positive limits from environment settings
for registration, login, ride creation, support-ticket creation, driver
location updates, verification submission, and routing. The API never trusts a mobile
application to self-enforce an abuse threshold.

Development and isolated tests use an in-process fixed-window adapter. Staging
and production use a shared PostgreSQL adapter with atomic bucket updates and
database-authoritative time, so adding an API instance does not multiply a
caller's quota. Bucket identities are persisted only as SHA-256 digests. A shared
limiter failure returns the standard safe `503 DEPENDENCY_UNAVAILABLE` envelope;
the endpoint does not fail open.

---

# 49. Routing

## POST /routing/route

Returns a normalized driving route from the configured backend routing adapter.
Self-hosted Valhalla is the default; self-hosted GraphHopper is the implemented
approved replacement selected through validated deployment configuration. The
endpoint is authenticated and rate-limited; clients never receive provider
credentials or depend on either provider's native response format.

Request:

```json
{
  "origin": {"latitude": 34.0209, "longitude": -6.8416},
  "destination": {"latitude": 34.0333, "longitude": -6.8326},
  "language": "fr"
}
```

`language` is optional and is restricted to `ar`, `en`, or `fr`; omission defaults
to `en`. It selects provider narration only and cannot affect geometry, ride state,
matching, or fare authority. The Valhalla adapter maps French to `fr-FR` and
English to `en-US`. The currently pinned Valhalla narration catalog does not
support Arabic, so `ar` keeps route geometry but receives safe English provider
narration until an Arabic-capable adapter passes the routing acceptance gate.
The GraphHopper adapter forwards the closed `ar`, `en`, or `fr` locale value; a
deployment must verify that its pinned GraphHopper version and translation bundle
produce acceptable narration before selecting it.

Response:

```json
{
  "distance_meters": 2100,
  "duration_seconds": 420,
  "geometry": [
    {"latitude": 34.0209, "longitude": -6.8416},
    {"latitude": 34.0333, "longitude": -6.8326}
  ],
  "maneuvers": [
    {
      "instruction": "Drive east.",
      "distance_meters": 2100,
      "duration_seconds": 420,
      "begin_shape_index": 0,
      "end_shape_index": 1
    }
  ]
}
```

Coordinates outside latitude/longitude bounds, unsupported languages, or unknown fields are rejected.
`geometry` is an ordered list suitable for a MapLibre route line. Maneuver shape
indices refer to that normalized list. Distance and duration are guidance only;
they cannot advance a ride, assign a driver, finalize a fare, or settle payment.
The API returns `503 Service Unavailable` with a safe error when the configured
routing service times out, rejects the route, or returns an invalid response.

---

# 50. Real-Time Communication

Ride-hailing requires near-real-time updates.

The system should eventually support a realtime channel for events such as:

```text
DRIVER_ASSIGNED
DRIVER_LOCATION_UPDATED
DRIVER_ARRIVED
RIDE_STARTED
RIDE_CANCELLED
RIDE_COMPLETED
RIDE_OFFER
```

The first implementation uses authenticated WebSockets for live ride events while an app is connected, and Firebase Cloud Messaging (FCM) for background or disconnected devices. WebSocket and FCM messages are hints to refresh or retrieve the affected resource; they do not perform state changes and are not the source of truth. Push delivery is best-effort and contains only minimized event metadata.

### `WS /api/v1/events`

Connected native clients authenticate with their normal `Authorization: Bearer`
header when opening the socket. The server validates the access token and its
unrevoked server-side session before accepting the connection. Messages contain
only a type and a ride ID, for example:

```json
{
  "type": "DRIVER_ASSIGNED",
  "ride_id": "uuid"
}
```

The transactional-outbox processor emits
`RIDE_OFFER_AVAILABLE` to the selected driver and `DRIVER_ASSIGNED` to the
passenger only after the corresponding database transaction commits and the
worker reloads the relevant records. Driver/passenger cancellation similarly
enqueues `RIDE_CANCELLED` in the business transaction. In staging and production,
a private PostgreSQL notification carries only version, authorized user ID, ride
ID, and allowlisted event type to every API process; it is validated before the
named user's local sockets receive it. Socket input never executes commands. On
every message, reconnect, foregrounding, or error, the client must retrieve the
resource from the REST API and reauthorize it. FCM delivery also
requires environment-provided server credentials and valid Android/APNs projects.
For an authenticated command error, the client executes no automatic retry of the
command. It performs one read-only authoritative restore, renders that result,
and retains the original operation error for the user unless reauthorization
rejects the session.
Before dispatch, each mobile root admits at most one authenticated UI action and
rejects overlapping taps locally. This presentation gate reduces accidental
duplicates but is not a protocol guarantee; every command must retain its
documented server-side idempotency, authorization, and conflict handling.

The normal REST API remains the authoritative interface for state changes.

---

# 51. Client Synchronization

The mobile client should assume that local state can become stale.

For example:

```text
Mobile app
    │
    │ sees ride as AVAILABLE
    │
    ▼
Backend
    │
    └── ride was already accepted
```

The client must handle authoritative backend responses and refresh its local state when conflicts occur.

---

# 52. API Security Principles

The API must:

* Validate all input.
* Authenticate protected requests.
* Authorize every protected resource.
* Never trust client-submitted prices.
* Never trust client-submitted user IDs.
* Never trust client-submitted driver IDs.
* Never trust client-submitted ride states.
* Protect sensitive documents.
* Rate-limit abuse-prone endpoints.
* Use HTTPS in production.
* Avoid leaking internal errors.

---

# 53. API Versioning

The initial API version is:

```text
v1
```

Example:

```text
/api/v1/rides
```

Breaking changes should require a new API version.

Non-breaking additions may be introduced within the existing version when compatible.

---

# 54. API Documentation

The backend should generate machine-readable API documentation where possible.

OpenAPI should be used if compatible with the selected backend framework.

The generated API documentation should describe:

* Endpoints.
* Authentication.
* Request schemas.
* Response schemas.
* Error responses.
* Status codes.

The documentation should remain synchronized with the implementation.

---

# 55. Development Environment

During development, the API should be accessible locally.

Example:

```text
http://localhost:8000/api/v1
```

The exact port is configurable.

The Kotlin application should obtain the API base URL from configuration rather than hard-coding production URLs throughout the codebase.

---

# 56. API Testing

Every important endpoint should have automated tests.

Tests should cover:

* Successful requests.
* Invalid input.
* Unauthorized requests.
* Forbidden requests.
* Missing resources.
* Ownership violations.
* Concurrent operations.
* State-transition violations.
* Rate limiting where appropriate.

Ride acceptance and cancellation deserve particular attention because they involve concurrency.

---

# 57. Minimum Viable API

The first implementation should prioritize:

### Authentication

```text
POST /auth/register
POST /auth/login
POST /auth/refresh
POST /auth/logout
GET  /me
```

The mobile registration form sends a display name, password, and at least one
contact identifier to this contract. It never sends roles, account status, or a
driver approval assertion; those remain backend-controlled.

### Passenger

```text
GET   /passenger/profile
PATCH /passenger/profile
```

`GET /passenger/profile` and `PATCH /passenger/profile` operate only on the
authenticated user's passenger profile. The update contract currently accepts only
`display_name`; contact identifiers and account roles remain account-management and
server-controlled data.

### Driver

```text
POST /drivers/apply
GET  /drivers/me
GET  /drivers/me/verification
GET  /drivers/me/vehicles
POST /drivers/me/vehicles
POST /drivers/me/availability/online
POST /drivers/me/availability/offline
POST /drivers/me/location
```

### Rides

```text
POST /rides
GET  /rides
GET  /rides/{ride_id}
POST /rides/{ride_id}/cancel
```

### Driver rides

```text
GET  /drivers/me/ride-offers
POST /ride-offers/{offer_id}/accept
POST /ride-offers/{offer_id}/decline
POST /rides/{ride_id}/arrived
POST /rides/{ride_id}/start
POST /rides/{ride_id}/complete
```

### Financial

```text
POST /rides/estimate
GET  /drivers/me/earnings
```

### Routing

```text
POST /routing/route
```

Electronic CMI session and callback endpoints are intentionally excluded from
the minimum API until the merchant integration kit and cancellation/refund policy
define their signed request, state-transition, and reconciliation contracts.

### Administration

```text
POST /admin/drivers/{driver_id}/approve
POST /admin/pricing-rules
POST /admin/pricing-rules/{pricing_rule_id}/activate
POST /admin/users/{user_id}/sessions/revoke
POST /admin/users/{user_id}/suspend
POST /admin/users/{user_id}/reactivate
GET  /admin/audit-logs
```

These endpoints require the server-side `ADMIN` role. They do not bootstrap an
administrator: initial administrative access is a controlled deployment operation,
never a public API capability. Driver approval records a verification decision and
grants only the `DRIVER` role. Tariffs are first created inactive; activation is
audited and closes an earlier overlapping active tariff at the new tariff's effective
time. The API never rewrites historical fare records.

This is the implemented single-scope compatibility surface. It is not the
national operations console contract. The planned `/operations` namespace and
scoped grants in Section 58 replace broad `ADMIN` assumptions incrementally;
the legacy routes must not be extended into cross-city management merely by
adding a `city_id` parameter.

Account-security actions require a bounded non-blank reason and write an audit
record. Revoking sessions invalidates every active server-side session and push
registration owned by the target account. Suspension performs that revocation in
the same transaction and immediately blocks access-token validation, refresh,
and login. Reactivation never revives old sessions: the user must authenticate
again. Administrators cannot suspend their own account through this endpoint,
and a deactivated account cannot be restored through suspension recovery.

`GET /admin/audit-logs` is restricted to the server-side `ADMIN` role and uses
the standard bounded `page`/`limit` response. Exact optional filters are
available for actor, action, resource type, and resource ID. Results use a
deterministic newest-first order and expose only backend-created audit fields;
there is no public, passenger, or driver audit-log read path and no mutation
endpoint for audit records.

The deployment command `taximobile-bootstrap-admin` (also available as
`python -m taximobile_api.cli.bootstrap_admin`) creates the initial administrator
only after explicit operator confirmation and hidden password entry. It is not an
HTTP endpoint. It serializes concurrent attempts, refuses to elevate an existing
ordinary account, and refuses a different administrator after bootstrap.

---

# 58. National Expansion API (planned)

These endpoint families are the approved target contract for
`operations.md`. They are not present in the current OpenAPI document and must
be delivered incrementally with migrations, generated OpenAPI, negative scope
tests, and client contract updates. Existing v1 behavior must not be broken
silently; any incompatible request/response change requires an additive endpoint
or a new API version.

## 58.1 Public city and fixed-route catalog

```text
GET /cities
GET /cities/{city_id}
GET /cities/{city_id}/fixed-routes
GET /fixed-route-directions/{direction_version_id}
```

Catalog responses expose only publicly activated city identity/status, localized
route names, explicit direction, start/finish, optional ordered stops, static
geometry, flat fare/currency, effective dates, and whether booking is currently
enabled. A paused city may retain route visibility with booking disabled.

These endpoints never return online-driver locations, counts, identities,
candidate lists, queues, or supply heatmaps. Catalog access is bounded,
cacheable by immutable version/ETag where appropriate, and rate-limited against
scraping/abuse. Publication state is backend authority.

## 58.2 Passenger immediate and scheduled service

Existing point-to-point ride creation remains compatible. National expansion
adds an optional published `fixed_route_direction_version_id` only through a
reviewed additive contract; when supplied, the backend derives city/operator,
start/finish, geometry version, and flat fare and rejects conflicting arbitrary
coordinates.

Scheduled bookings use their own resources:

```text
POST /scheduled-bookings
GET  /scheduled-bookings
GET  /scheduled-bookings/{booking_id}
POST /scheduled-bookings/{booking_id}/cancel
```

Creation requires `Idempotency-Key` and includes either validated point-to-point
locations or one published direction version plus `scheduled_for`. The response
contains backend-resolved city/operator/service, lifecycle status, city timezone
presentation data, transport fare, scheduling surcharge, passenger-funded
operator fee if any, passenger total, policy versions, cancellation terms, and
whether a driver has committed. It never promises a taxi merely because the
booking was accepted.

Cancellation is backend-authorized, idempotent, and returns explicit financial
outcomes such as no charge, retained surcharge, pending refund, or completed
refund according to the snapshotted policy. The client cannot submit those
outcomes.

## 58.3 Driver city applications and scheduled work

```text
GET  /drivers/recruiting-cities
GET  /drivers/recruiting-cities/{city_id}/requirements
POST /drivers/me/city-applications
GET  /drivers/me/city-applications
GET  /drivers/me/city-applications/{application_id}
PATCH /drivers/me/city-applications/{application_id}
POST /drivers/me/city-applications/{application_id}/documents
DELETE /drivers/me/city-applications/{application_id}/documents/{document_id}
POST /drivers/me/city-applications/{application_id}/submit
POST /drivers/me/city-applications/{application_id}/withdraw

GET  /drivers/me/scheduled-offers
PATCH /drivers/me/scheduled-offer-preference
POST /scheduled-offers/{offer_id}/accept
POST /scheduled-offers/{offer_id}/decline
GET  /drivers/me/scheduled-commitments
```

The same applicant-owned contract serves driver mobile and public web clients.
No request field grants a role, approval, city authorization, or online state.
Application responses expose the requirement version and applicant-safe status,
not reviewer-private notes or another applicant's data.

The recruiting requirements response contains only the active public requirement
version, typed item codes, localized explanations, allowed evidence types, and
whether each item is required. Application creation snapshots that version.
PATCH accepts only typed answers and owned profile/vehicle/credential references
defined by that requirement version while the application is editable; it cannot
set status, reviewer fields, roles, or authorization. Submit validates a complete
snapshot and is idempotent. Withdraw is applicant-owned, idempotent, allowed only
before approval, and never deletes the audit/retention record.
Document upload is a bounded authenticated `multipart/form-data` request through
the backend's protected storage adapter; it enforces declared and detected media
type, byte limit, hash, malware-scan quarantine, ownership, requirement-item
membership, and rate limit before evidence can satisfy a requirement. It never
returns a durable object-store URL. Deletion is allowed only in editable states,
is idempotent, and follows the retention/audit policy. These endpoints stay
disabled until the protected storage and scanning dependencies are configured
and verified; no client may simulate a successful upload.

The scheduled-offer preference is city-scoped and backend-confirmed. Enabling it
does not make the driver immediately available or passenger-visible. Disabling
it stops new future offers and does not cancel accepted commitments.

Scheduled offers contain server time, pickup time, city/service, point-to-point
or fixed-route direction, offer/commitment expiry, cancellation terms, transport
fare, scheduling surcharge, operator fee/funding mode, and expected driver net.
Acceptance atomically checks expiry, city/vehicle/credential eligibility and
schedule conflicts. Decline is non-punitive and advances the configured offer
process.

## 58.4 Protected operations control plane

The operations console uses a dedicated `/operations` namespace so participant
routes do not accidentally inherit administrative reads. Collection, resource,
and command paths are explicit; clients must not invent a generic mutation
endpoint:

```text
POST            /operations/auth/login
POST            /operations/auth/mfa/verify
POST            /operations/auth/refresh
POST            /operations/auth/logout

GET/POST       /operations/cities
GET/PATCH      /operations/cities/{city_id}
POST           /operations/cities/{city_id}/lifecycle-transitions
GET/POST       /operations/operators
GET/PATCH      /operations/operators/{operator_id}
GET/POST       /operations/operator-city-assignments
POST           /operations/operator-city-assignments/{assignment_id}/retire
GET/POST       /operations/administrative-grants
DELETE         /operations/administrative-grants/{grant_id}

GET/POST       /operations/cities/{city_id}/service-area-versions
GET/PATCH      /operations/service-area-versions/{version_id}
GET/POST       /operations/cities/{city_id}/driver-requirement-versions
GET/PATCH      /operations/driver-requirement-versions/{version_id}
POST           /operations/driver-requirement-versions/{version_id}/submit
POST           /operations/driver-requirement-versions/{version_id}/activate

GET/POST       /operations/cities/{city_id}/configuration-versions
GET/PATCH      /operations/city-configuration-versions/{version_id}
POST           /operations/city-configuration-versions/{version_id}/submit
POST           /operations/city-configuration-versions/{version_id}/approve
POST           /operations/city-configuration-versions/{version_id}/activate

GET             /operations/driver-applications
GET             /operations/driver-applications/{application_id}
GET             /operations/driver-applications/{application_id}/documents/{document_id}
POST            /operations/driver-applications/{application_id}/decisions

GET/POST         /operations/cities/{city_id}/pricing-rules
GET/PATCH        /operations/pricing-rules/{version_id}
POST             /operations/pricing-rules/{version_id}/submit
POST             /operations/pricing-rules/{version_id}/activate
GET/POST         /operations/cities/{city_id}/operator-fee-policies
GET/PATCH        /operations/operator-fee-policies/{version_id}
GET/POST         /operations/cities/{city_id}/scheduling-policies
GET/PATCH        /operations/scheduling-policies/{version_id}

GET/POST         /operations/cities/{city_id}/fixed-routes
GET/PATCH        /operations/fixed-routes/{route_id}
POST             /operations/fixed-routes/{route_id}/versions
GET/PATCH        /operations/fixed-route-versions/{version_id}
POST             /operations/fixed-route-versions/{version_id}/publish
POST             /operations/fixed-route-versions/{version_id}/retire

GET              /operations/scheduled-bookings
GET              /operations/scheduled-bookings/{booking_id}
GET              /operations/rollout-overview
GET              /operations/cities/{city_id}/operational-aggregates
GET              /operations/audit-logs
```

Additive fields may be refined before each slice is implemented, but methods,
resource ownership, and command semantics change only through a documented API
revision. The following contract cannot be weakened:

* Every operation requires a named permission plus validated market/operator/city
  scope; `ADMIN` text alone is insufficient for the target model.
* Lists are paginated and automatically constrained to the caller's grants.
* Aggregate endpoints do not return account rows, exact driver/passenger
  locations, documents, support text, or provider-payment secrets.
* Draft, review, activation, publication, and lifecycle transition are distinct
  commands with optimistic version/conflict handling.
* Configuration activation validates its immutable component references and
  updates the city active pointer atomically; activating one child policy alone
  never silently changes a live city's coherent bundle.
* Financial/configuration activation and grant/review decisions are idempotent,
  audited, and never rewrite history.
* Driver-document reads require scoped review permission, reauthentication,
  no-store delivery, and a document-access audit; list responses never contain
  storage keys or reusable download URLs.
* Browser CORS accepts only the exact operations origin. Administrative session,
  MFA, CSRF, and content-security boundaries must be finalized before the first
  production console release.

Operations authentication issues a dedicated administrative audience and never
accepts a normal mobile bearer token as sufficient. Exact MFA method, recovery,
step-up lifetime, and refresh-cookie protocol must be fixed and threat-modeled in
`auth.md`/`security.md` before these endpoint schemas are implemented; the route
names above reserve the boundary rather than inventing an identity-provider
protocol.

## 58.5 City resolution and response scope

Ride/booking requests may include a catalog-selected city identifier, but the
backend verifies it against pickup/service geometry and policy. A mismatch is a
safe validation error, not a fallback to another city. Responses include the
resolved city/service/operator identifiers and relevant immutable version IDs so
clients can display facts without selecting rules.

Cross-city object identifiers return `404` or `403` according to the documented
enumeration policy, never data from another grant. Database filtering is applied
before pagination/counting so totals cannot leak another city's records.

## 58.6 Expansion idempotency and concurrency tests

Required tests include:

```text
Two operators cannot become authoritative for one city/service/time.
Two active equal-specificity financial policies cannot overlap.
Publishing a route version never mutates the old version.
Submitting or withdrawing one application cannot approve or alter another.
Two drivers cannot commit to one scheduled booking.
One driver cannot accept overlapping scheduled commitments.
Handoff creates at most one live ride and revalidates eligibility.
A City A manager cannot count, read, or mutate City B records.
A passenger cannot enumerate online drivers through any catalog or error.
Passenger total, driver net, and operator allocation reconcile exactly.
```

---

# 59. API Design Principles

## Endpoint delivery checklist

Implement one endpoint family at a time. For every endpoint, define authentication, ownership, validation, idempotency, concurrency behavior, error shape, and the focused test. The client must never declare authoritative business state. If an endpoint needs a new field or transition, update the domain and persistence contract in the same slice or split the contract from implementation explicitly.

The Kotlin gateways are handwritten, so route compatibility is enforced from
their actual Ktor call sites. `infra/scripts/validate_mobile_api_contract.py`
extracts each `client.<method>(api.endpoint("..."))` operation, expands only the
reviewed finite driver transition segment, and compares method/path pairs with
FastAPI's generated OpenAPI contract. It separately checks the live-event
WebSocket because WebSocket routes are not represented in OpenAPI. A gateway
must keep using the versioned endpoint builder and literal route structure; an
unparsed call or unreviewed runtime path segment fails CI rather than being
silently omitted from the contract gate. This proves route and method presence,
not request/response schema compatibility, authorization behavior, or runtime
provider availability; focused gateway and backend tests retain those duties.

### Principle 1 — Backend authority

The backend is authoritative for business state.

### Principle 2 — Thin client

The mobile application should not contain critical business rules that the backend needs to enforce.

### Principle 3 — Explicit state

Ride and driver state transitions must be explicit.

### Principle 4 — Secure by default

Protected resources require authentication and authorization.

### Principle 5 — Consistency

Similar resources should use consistent endpoint and response conventions.

### Principle 6 — Versionability

The API must be capable of evolving without unnecessarily breaking existing clients.

### Principle 7 — Idempotency

Important operations must be safe against duplicate network requests.

### Principle 8 — Concurrency safety

The backend must remain correct when multiple users act simultaneously.

### Principle 9 — Observable operations

Important state changes should generate appropriate events and audit records.

### Principle 10 — Platform independence

The API must not assume that the client is Android, iOS, or any other specific platform.
