# TaxiMobile — API Specification

## 1. Purpose

This document defines the HTTP API used by TaxiMobile clients and backend services.

**Current standing (2026-09-08):** the implemented FastAPI/OpenAPI surface covers
the mobile MVP and national expansion through versioned payment operations and
protected driver documents, mobile offline-code reset, password change, and
account-owned session controls. OpenAPI and route-contract tests are
implementation authority when this narrative inventory drifts. Provider
callbacks, verified-contact recovery delivery, account deletion/export, and
saved-place persistence are not implemented. A constrained closed-code
participant-coordination API is implemented for assigned active rides; free text,
masked calling, and personal-number disclosure are intentionally absent.
Authenticated normalized place search and reverse geocoding are implemented but
remain fail-closed until an approved provider is configured. See
[`gaps.md`](gaps.md).
Production-like deployments now require a closed client surface, numeric release
version, and positive build identity on every v1 HTTP request and live-event
socket. An unauthenticated command-free compatibility endpoint lets clients
present an upgrade gate before sign-in. This is release lifecycle control, not
authentication or authorization.

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
`Content-Type`, `Idempotency-Key`, `X-Request-ID`, and the three TaxiMobile client
identity headers. Browser responses may expose only the controlled compatibility
policy, minimum-version, and recommended-version headers. Staging and production
accept only exact HTTPS origins. Native Android and iOS clients do not use CORS.

## 5.1 Client release identity and compatibility

Every maintained Android, iOS, applicant-web, and operations-web request sends:

```text
X-TaxiMobile-Client: <closed surface>
X-TaxiMobile-Version: <major.minor.patch[.revision]>
X-TaxiMobile-Build: <positive integer>
```

The closed surfaces are `ANDROID_PASSENGER`, `ANDROID_DRIVER`,
`IOS_PASSENGER`, `IOS_DRIVER`, `WEB_APPLICANT`, and `WEB_OPERATIONS`. Versions
contain three or four non-negative numeric components with no prerelease text;
builds are positive integers no greater than 2,147,483,647. The version selects
compatibility. The build identifies the packaged revision for support and
evidence; it must never grant authority.

Local development may disable enforcement. Staging and production cannot. The
backend owns a complete minimum and recommended version for every surface plus a
controlled policy revision:

| Client version | Preflight result | Ordinary v1 request |
| --- | --- | --- |
| Below minimum | `UPGRADE_REQUIRED` | `426 CLIENT_UPGRADE_REQUIRED` |
| At/above minimum but below recommended | `UPDATE_AVAILABLE` | Allowed |
| At/above recommended | `SUPPORTED` | Allowed |

Missing, malformed, or unknown identity receives `426
CLIENT_IDENTITY_REQUIRED`. A supported ordinary response carries
`X-TaxiMobile-Client-Policy`, `X-TaxiMobile-Minimum-Version`, and
`X-TaxiMobile-Recommended-Version`. Errors disclose the controlled policy and
required versions but do not reflect the caller's supplied value.

`GET /api/v1/client-compatibility` is unauthenticated, command-free, and excluded
from the ordinary compatibility middleware so a client can discover the policy.
It still requires the three identity headers and returns:

```json
{
  "status": "SUPPORTED",
  "surface": "ANDROID_PASSENGER",
  "minimum_version": "1.0.0",
  "recommended_version": "1.0.0",
  "policy_revision": "baseline-1",
  "api_version": "v1"
}
```

Malformed preflight identity returns a safe `400`. The mobile applications run
the preflight before restoring a session and show a retryable unavailable state
or a localized mandatory-upgrade gate. Both browser surfaces block sign-in and
operations until preflight succeeds and show reload/retry guidance. The backend
still enforces every request, because UI gates and self-declared headers are
untrusted. A live-event WebSocket missing a valid supported identity closes with
code `4406` before access-token/session validation.

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

## POST /auth/recovery/reset

Public, provider-independent reset using one previously saved offline recovery
code. The request is rate limited and never returns account/code validity.

```json
{
  "identifier": "passenger@example.test",
  "recovery_code": "23456-789AB-CDEFG-HJKLM",
  "new_password": "a-new-password-with-12-or-more-characters"
}
```

Every syntactically valid absent-account, invalid, expired, replayed, suspended,
staff-account, and successful request returns:

```text
202 Accepted
```

```json
{
  "accepted": true
}
```

A successful reset revokes all mobile/operations sessions and push
registrations. Clients must not turn the generic response into a stronger claim.

## POST /auth/recovery-codes

Requires a mobile bearer token and the current password. Replaces the entire
offline-code set and returns eight codes once; staff identities are rejected.

```json
{
  "current_password": "current-password"
}
```

```json
{
  "codes": ["23456-789AB-CDEFG-HJKLM"],
  "expires_at": "2027-03-01T12:00:00Z"
}
```

The abbreviated array above demonstrates shape only; the implementation returns
eight codes. A client must provide save/copy acknowledgement and must never log
or persist these secrets in ordinary application state.

## POST /auth/password/change

Requires a mobile bearer token and current-password re-authentication. The new
password must differ from the current password. Success revokes every mobile and
operations session plus push registration, so the caller must clear local tokens
and return to sign in.

```json
{
  "current_password": "current-password",
  "new_password": "a-different-password"
}
```

## GET /auth/sessions

Returns up to 100 active, non-expired sessions owned by the authenticated account
with `id`, optional `device_label`, `current`, `created_at`, and `expires_at`.

## DELETE /auth/sessions/{session_id}

Revokes one active session owned by the account and push registrations still
bound to it. An absent, revoked, expired, or other-account ID is not returned as
an active session. Revoking the current session requires the client to clear its
local credentials.

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
credentials. Approval is rejected until submission exists. This legacy global
verification endpoint remains metadata-only; raw files belong to the separately
authorized city-application document routes in Section 59.3, whose exact required
document set comes from the active city requirement version.

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
register a vehicle but cannot make it dispatch-eligible. Staging and production
review the vehicle through
`POST /operations/driver-applications/{application_id}/vehicles/{vehicle_id}/verify`;
the older `/admin` command is local/test compatibility only. The scoped decision
is auditable, and selecting an eligible vehicle returns the
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
  },
  "payment_method": "CASH"
}
```

`payment_method` is a closed value previously advertised by
`POST /rides/estimate`; omission defaults to `CASH` for compatible clients. The
server rejects a known but unavailable method with `409` and never accepts a
client-supplied recipient account or payment status.

Response:

```json
{
  "id": "uuid",
  "status": "MATCHING",
  "pickup": {
    "latitude": 34.0209,
    "longitude": -6.8416
  },
  "destination": {
    "latitude": 34.0333,
    "longitude": -6.8326
  },
  "completed_at": null,
  "driver": null,
  "last_known_driver_location": null,
  "payment_method": "CASH"
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

# 22.1 Active-Ride Participant Coordination

## POST /rides/{ride_id}/messages

Sends one privacy-minimized coordination signal between the passenger and the
assigned driver. The endpoint does not accept free text, contact details, media,
links, or arbitrary metadata. It requires the normal 16–128-character
`Idempotency-Key` header.

Passenger request example:

```json
{
  "code": "PASSENGER_AT_PICKUP"
}
```

Driver request example:

```json
{
  "code": "DRIVER_ON_MY_WAY"
}
```

Response:

```json
{
  "id": "uuid",
  "ride_id": "uuid",
  "sender_role": "PASSENGER",
  "code": "PASSENGER_AT_PICKUP",
  "created_at": "2026-09-03T10:15:30Z"
}
```

Allowed passenger codes are:

* `PASSENGER_AT_PICKUP`
* `PASSENGER_NEEDS_MORE_TIME`
* `PASSENGER_CANNOT_FIND_DRIVER`

Allowed driver codes are:

* `DRIVER_ON_MY_WAY`
* `DRIVER_AT_PICKUP`
* `DRIVER_CANNOT_FIND_PASSENGER`

The backend authorizes only the ride passenger and assigned driver, validates
that the code belongs to the caller's exact role, and accepts messages only while
the ride is `ACCEPTED`, `DRIVER_EN_ROUTE`, `DRIVER_ARRIVED`, or `IN_PROGRESS`.
An unassigned or terminal ride never exposes a communication window. A missing
ride returns `404`; a non-participant returns `403`; a wrong-role code,
pre-assignment/terminal state, or exhausted per-ride cap returns `409`; and a
rate-limit rejection returns `429`.

The default limiter permits 12 attempts per user and ride per minute, with an
operator-configurable upper bound of 60. A separate absolute limit permits no
more than 100 accepted messages from each participant on a ride. Idempotent replay
returns the original response and does not create another message, notification,
or outbox event. Reusing a key for a different command is rejected by the common
idempotency policy.

The command creates a durable closed-code message, a persistent notification for
the other participant, and a transactional outbox event. Push and live delivery
carry only the generic `RIDE_COORDINATION_MESSAGE` refresh hint; clients reload
authorized REST state and localize the closed code themselves. The worker
suppresses delivery after terminal ride state or when the event is more than five
minutes old. Provider loss therefore cannot change the stored message or ride.

Detailed `GET /rides/{ride_id}` responses include
`latest_coordination_message` only for an authorized participant while the ride
is in an allowed active state. It is omitted for terminal rides. This launch
contract intentionally provides neither a transcript API nor a free-text
moderation surface; retention and erasure remain governed by the approved
deployment policy.

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
  },
  "payment_method": "CASH"
}
```

The backend should calculate and finalize the fare.

The client must not be trusted to submit the final fare.

## POST /rides/{ride_id}/payments/cash/settle

The assigned driver confirms settlement of a pending cash payment after the ride has completed. The backend verifies driver ownership, completed ride state, payment method, and pending payment status before recording settlement.

## POST /rides/{ride_id}/payments/manual-transfer/submit

The authenticated passenger who owns a completed `MANUAL_TRANSFER` ride may
submit a claim for operator review. The request requires `Idempotency-Key`; its
body may contain an optional 3–80 character external payer reference using only
ASCII letters, digits, `.`, `_`, `/`, and `-`:

```json
{
  "payer_reference": "BANK-APP-48392"
}
```

The endpoint returns `202` with claim, payment, ride, `SUBMITTED`, and submission
time fields. It changes the payment from `PENDING` to `PROCESSING`; it never marks
the payment paid. A duplicate active claim, wrong participant, wrong method, or
non-completed ride is rejected. An idempotent retry returns the original claim.

## Administrative manual-transfer reconciliation

```text
GET  /admin/payments/manual-transfers?status=SUBMITTED&page=1&limit=20
POST /admin/payments/{payment_id}/manual-transfer/verify
POST /admin/payments/{payment_id}/manual-transfer/reject
```

These routes require the transitional server-side `ADMIN` role. Verification
requires `Idempotency-Key` and a unique 3–120 character settlement-statement
reference. Under a row lock it verifies the active claim, completes the payment,
creates the assigned driver's earning, marks the claim `VERIFIED`, and writes an
audit event in one transaction. Rejection requires `Idempotency-Key` and a
bounded reason; it marks the claim `REJECTED`, returns the payment to `PENDING`,
and allows a corrected passenger claim. Neither route accepts amount or currency
from the client.

## Administrative completed refunds

```text
GET  /admin/payments/refunds?payment_id={uuid}&reason=FARE_CORRECTION&page=1&limit=20
POST /admin/payments/{payment_id}/refunds
```

These routes require the transitional server-side `ADMIN` role. The create
command records money only after the operator has confirmed that it was returned;
a passenger refund request remains a `FARE_DISPUTE` support workflow. The command
requires `Idempotency-Key` and this closed request:

```json
{
  "amount": "5.00",
  "reason": "FARE_CORRECTION",
  "settlement_method": "CASH",
  "settlement_reference": "SIGNED-CASH-RETURN-48392",
  "operator_note": "Approved case reference and controlled evidence summary."
}
```

`reason` is `FARE_CORRECTION`, `DUPLICATE_PAYMENT`, `SERVICE_RECOVERY`, or
`OTHER_APPROVED`; `settlement_method` is `CASH` or `EXTERNAL_TRANSFER`. The
reference is 3–120 characters of bounded ASCII and globally unique. The amount
must be positive, use at most two decimal places, and cannot exceed the completed
payment's remaining refundable amount. Currency, ride, passenger, original
amount, and driver earning come from the backend and cannot be supplied by the
caller.

The response returns the append-only refund fact, payment status, and remaining
refundable amount. In the launch policy `driver_recovery_amount` is always
`0.00`, while `operator_funded_amount` equals the refund. A partial refund leaves
the payment `COMPLETED`; exhausting the original amount sets it to `REFUNDED`.
The bounded list is administrator-only and supports exact payment, reason, and
settlement-method filters.

## Scoped operations payment configuration and reconciliation

The national operations surface uses the operations audience, permission grants,
and database-level city/operator scope filtering:

```text
GET/POST /operations/cities/{city_id}/payment-recipient-accounts
PATCH    /operations/payment-recipient-accounts/{account_id}
POST     /operations/payment-recipient-accounts/{account_id}/verify
POST     /operations/payment-recipient-accounts/{account_id}/retire

GET/POST /operations/cities/{city_id}/payment-capability-versions
PATCH    /operations/payment-capability-versions/{capability_id}
POST     /operations/payment-capability-versions/{capability_id}/submit
POST     /operations/payment-capability-versions/{capability_id}/approve
POST     /operations/payment-capability-versions/{capability_id}/activate

GET      /operations/payments/manual-transfers
POST     /operations/payments/{payment_id}/manual-transfer/verify
POST     /operations/payments/{payment_id}/manual-transfer/reject
GET      /operations/payments/refunds
POST     /operations/payments/{payment_id}/refunds
```

Recipient and capability collections require an exact city and optional exact
operator filter. Configuration commands require
`MANAGE_PAYMENT_CAPABILITIES`; verification, retirement, and capability
activation additionally require operations MFA no older than ten minutes.
Verified recipients are immutable. Capability commands use optimistic versions
and the ordered `DRAFT -> IN_REVIEW -> APPROVED -> ACTIVE` lifecycle. Activation
does not make a method passenger-visible until the capability ID is included as
`payment_capability_version_id` on the matching service in an active city-
configuration version.

Settlement routes require `RECONCILE_PAYMENTS`, not configuration authority.
Their lists apply the conjunction of authorized city/operator grants before
counting and pagination and return city/operator provenance. Verify, reject, and
refund commands require `Idempotency-Key`; refund recording also requires recent
MFA. The legacy `/admin/payments/...` routes are compiled into local development
and test applications only. Staging and production omit them from routing and
OpenAPI and use the scoped operations API.

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
    "amount": "35.00",
    "currency": "MAD",
    "pricing_rule_version": "v1",
    "city_id": "uuid",
    "operator_id": "uuid",
    "economics": {
      "transport_fare": "35.00",
      "scheduling_surcharge": "0.00",
      "operator_service_fee": "0.00",
      "passenger_total": "35.00",
      "expected_driver_net": "35.00",
      "operator_allocation": "0.00",
      "operator_fee_policy_version": "zero-fee-v1",
      "operator_fee_calculation_mode": "FLAT_PER_COMPLETED_BOOKING",
      "operator_fee_funding_mode": "DRIVER_SETTLEMENT_DEDUCTION",
      "scheduling_policy_version": null
    }
  },
  "payment_methods": ["CASH", "MANUAL_TRANSFER"]
}
```

The ordered `payment_methods` array is the server-owned capability list for this
request context. `CASH` is always present. `MANUAL_TRANSFER` is present only when
the deployment is explicitly enabled and has a recipient plus a bank account
and/or M-Wallet destination. `CARD` and `MOBILE_PAYMENT` are not advertised by
the current implementation.

An estimate is not necessarily the final fare.

The backend resolves city, operator, fixed tariff, and explicit operator-fee
policy. It returns money as exact decimal strings; clients display these values
and do not recalculate them. The same server-selected policy bundle and exact
components are persisted when the passenger creates the ride.
`GET /rides/{ride_id}/fare` returns the finalized amount, tariff version, and
only passenger-charge components recorded in that fare's immutable snapshot.
A driver-funded operator deduction remains in `economics` and driver settlement,
not as a second passenger charge. A policy activated later cannot change the
ride's locked economics or historical fare record.

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
      {"code": "TRANSPORT_FARE", "label": "Transport fare", "amount": "35.00"}
    ],
    "economics": {
      "transport_fare": "35.00",
      "scheduling_surcharge": "0.00",
      "operator_service_fee": "0.00",
      "passenger_total": "35.00",
      "expected_driver_net": "35.00",
      "operator_allocation": "0.00",
      "operator_fee_policy_version": "zero-fee-v1",
      "operator_fee_calculation_mode": "FLAT_PER_COMPLETED_BOOKING",
      "operator_fee_funding_mode": "DRIVER_SETTLEMENT_DEDUCTION"
    }
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

For a `MANUAL_TRANSFER` ride, `payment` additionally returns a `manual_transfer`
object with the snapshotted `recipient_name`, optional `bank_account`, optional
`wallet_id`, backend-issued `payment_reference`, and optional
`latest_claim_status`. A latest `REJECTED` claim lets the passenger surface a
safe correction/retry message without exposing reviewer identity or statement
data. `PENDING` permits claim submission; `PROCESSING` means operator review is
outstanding; only `COMPLETED` may be presented as verified. If a legacy/inconsistent transfer ride lacks its
snapshot, the endpoint fails with `503` instead of inventing current account
details or claiming success.

When confirmed refunds exist, `payment` also includes a passenger-safe summary:

```json
{
  "refunds": {
    "refunded_amount": "5.00",
    "net_paid_amount": "30.00",
    "currency": "MAD",
    "items": [
      {
        "id": "uuid",
        "amount": "5.00",
        "currency": "MAD",
        "reason": "FARE_CORRECTION",
        "refunded_at": "2026-08-24T12:00:00Z"
      }
    ]
  }
}
```

The immutable fare remains the original amount. Settlement references,
administrator identity, and the private operator note are never returned to the
passenger. Absence of `refunds` means no confirmed refund record exists; it does
not decide an open support dispute.

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

### Notification delivery policy

The backend persists minimal account-owned notification history and a user may
list or mark only their own rows as read. Payload data is limited to opaque
resource IDs that the receiving user must still authorize through the normal API.
Device registration stores an Android or iOS FID (or transitional legacy token)
for the configured FCM adapter. It does not imply that Firebase credentials are
configured, that delivery occurred, or that a person saw the notification.

Every transactional-outbox topic must exist in the closed source policy registry.
The registry fixes hint type, live/push channels, urgency, maximum delivery age,
fallback, quiet-hour eligibility, and operational dead-letter owner. An unknown
topic fails into bounded retry/dead-letter handling; it is never silently treated
as delivered or forwarded as an arbitrary provider payload.

| Topic | Hint | Channel | Max age | Priority / quiet hours | Authoritative fallback |
| --- | --- | --- | --- | --- | --- |
| `ride.offer.created` | `RIDE_OFFER_AVAILABLE` | live + push | 5 min and exact offer expiry | immediate; no quiet hours | driver offer reload |
| `ride.accepted` | `DRIVER_ASSIGNED` | live + push | 15 min | immediate; no quiet hours | passenger active-ride reload plus inbox |
| `ride.cancelled` | `RIDE_CANCELLED` | live + push | 2 hr | immediate; no quiet hours | participant ride reload |
| `ride.matching.failed` | `RIDE_UNMATCHED` | live + push | 15 min | immediate; no quiet hours | passenger ride reload plus inbox |
| `ride.coordination.message` | `RIDE_COORDINATION_MESSAGE` | live + push | 5 min | immediate; no quiet hours | active-ride reload plus inbox |
| `scheduled.offer.created` | `SCHEDULED_OFFER` | push | 2 hr and exact offer expiry | immediate; no quiet hours | driver scheduled-offer reload plus inbox |
| `scheduled.driver.committed` | `SCHEDULED_DRIVER_COMMITTED` | push | 7 days | informational; quiet hours allowed | passenger booking reload plus inbox |
| `scheduled.dispatch.started` | `SCHEDULED_DISPATCH_STARTED` | push | 2 hr | immediate; no quiet hours | passenger booking/ride reload plus inbox |
| `scheduled.fallback.matching` | `SCHEDULED_FALLBACK_MATCHING` | push | 2 hr | immediate; no quiet hours | passenger booking/ride reload plus inbox |
| `scheduled.unfulfilled` | `SCHEDULED_UNFULFILLED` | push | 24 hr | immediate; no quiet hours | passenger booking reload plus inbox |
| `driver.credential.expiring` | `DRIVER_CREDENTIAL_EXPIRING` | push | 7 days | informational; quiet hours allowed | driver credential reload plus inbox |
| `driver.credential.expired` | `DRIVER_CREDENTIAL_EXPIRED` | push | 7 days | informational; quiet hours allowed | driver credential reload plus inbox |

The worker checks event age before opening business-data or provider boundaries,
then reloads current source records and state. Scheduled offers additionally
require their booking to remain `OFFERING`. FCM Android priority and TTL and the
iOS `apns-expiration` header derive from a single absolute deadline: the durable
outbox creation time plus policy age, capped by exact offer expiry or the
coordination message's five-minute lifetime where applicable. Every push call
requires a timezone-aware deadline. Credential acquisition and the one permitted
401 refresh do not reset it. The adapter floors the remaining lifetime to whole
seconds for Android TTL and suppresses submissions with less than one second
remaining (it does not convert expiry to TTL=0, which requests immediate delivery).
APNs receives the original absolute deadline, rounded down to Unix seconds.
The adapter also caps unusually distant deadlines to the policy maximum.

Network transit, provider handling, OS scheduling and later business-state changes
still mean a device can receive an obsolete hint. It must reload authoritative
state and must never display an offer as actionable from the hint alone; queue
headers are not proof of a strict device-visible deadline. See Firebase's
[message lifespan contract](https://firebase.google.com/docs/cloud-messaging/customize-messages/setting-message-lifespan).

Live and push channels are attempted independently: failure of one does not skip
the other, but still causes bounded outbox retry. The successful channel can
receive duplicate hints. Worker cancellation propagates immediately. Delivery
across multiple registrations is sequential, but a transient failure or a failed
invalid-registration revocation does not skip remaining devices while the source
deadline is valid. Aggregate failure still retries the event. Per-device durable
progress is not yet recorded, so a healthy device can receive duplicate hints.
Quiet-hour eligibility in the matrix is policy metadata, not an implemented
preference or deferral scheduler. FCM `UNREGISTERED`, invalid-registration, and FID
`NOT_FOUND` responses revoke the stored registration; transient failures use
bounded outbox retry.

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
delegate accept only the documented ride, coordination, scheduled-booking, and
credential hint types with a canonical resource UUID. The process retains at most the
latest unconsumed hint and an authenticated screen responds by reloading through
the normal ownership-checked APIs. Unknown fields, unknown event types, and
malformed identifiers do not trigger a refresh and are not logged.

---

# 38. Support

## POST /support/tickets

Creates an ordinary support ticket. `Idempotency-Key` is required and is bound
to the authenticated account, operation, and canonical payload.

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

Participant responses contain the owner's submitted category, subject,
description, optional ride association, server status, timestamps, and latest
participant-visible case message. They never contain priority, assignment,
response deadline, retention metadata, internal notes, or another participant's
identity.

### Support policy

The initial API creates and returns only tickets owned by the authenticated
participant. A ticket may reference a ride only when the requester is that
ride's passenger or assigned driver; arbitrary ride IDs are rejected. The
allowed categories are `RIDE_PROBLEM`, `FARE_DISPUTE`, `ACCOUNT_ACCESS`, and
`OTHER`, and new tickets begin as `OPEN`. A `FARE_DISPUTE` may precede the
separately authorized completed-refund command above, but opening or editing a
ticket cannot approve, create, or imply a refund.

Ordinary support uses `OPEN → IN_PROGRESS → RESOLVED → CLOSED`; a resolved case
may return to `IN_PROGRESS`, while a closed case is terminal. Resolution codes
are `INFORMATION_PROVIDED`, `ACTION_TAKEN`, `REFUND_RECORDED`, `DUPLICATE`,
`OUT_OF_SCOPE`, and `NO_ACTION`.

## GET /admin/support/tickets

Returns the restricted support queue. It accepts exact `status`, `priority`,
`category`, `assigned_to_user_id`, and `overdue` filters plus bounded
pagination. This `/admin` family is a local/test compatibility surface. Staging
and production do not mount it; operations clients use the scoped
`/operations/support` family below.

## GET /admin/support/tickets/{ticket_id}

Returns restricted case detail, including priority, assignee, response target,
retention projection, and append-only `INTERNAL`/`PARTICIPANT` notes.

## POST /admin/support/tickets/{ticket_id}/triage

Requires `Idempotency-Key`, an active administrator assignee, a controlled
priority, a participant-visible acknowledgement, and a separate internal note.
It claims an open case and changes it to `IN_PROGRESS`. Reprioritization may
shorten but never extend the case's existing response deadline.

## POST /admin/support/tickets/{ticket_id}/transition

Requires `Idempotency-Key`; only the assigned acting administrator may advance
the case. Resolution and closure require a controlled resolution code and a
participant-visible message. Audit changes contain fixed status fields and a
message-recorded boolean, never either message body.

---

# 39. Safety Reports

Safety reports are separate from ratings and ordinary support. TaxiMobile's
report endpoint is not an emergency service and does not promise dispatch of
police, medical, or other emergency assistance.

## POST /safety/reports

Requires `Idempotency-Key` and an authenticated passenger or assigned driver.
The caller supplies only a ride they participated in, one controlled category,
and a bounded description:

```json
{
  "ride_id": "uuid",
  "category": "UNSAFE_DRIVING",
  "description": "Description of the safety concern."
}
```

Categories are `IMMEDIATE_DANGER`, `HARASSMENT`, `ASSAULT`, `UNSAFE_DRIVING`,
`DISCRIMINATION`, `VEHICLE_SAFETY`, and `OTHER_SAFETY`. The backend derives the
other ride participant; a client cannot name or replace the reported user.

## GET /safety/reports

Returns only reports submitted by the authenticated account, with pagination.

## GET /safety/reports/{report_id}

Returns the reporter-safe projection: report ID, ride ID, category, status,
latest participant-visible message, and lifecycle timestamps. It omits the
description, reporter/reported identities, priority, assignment, deadline,
retention metadata, and every case note.

The lifecycle is `SUBMITTED → ACKNOWLEDGED → ESCALATED → RESOLVED → CLOSED`;
`ACKNOWLEDGED → RESOLVED` is also valid and a resolved report may be reopened to
`ACKNOWLEDGED`. Closed reports are terminal.

## GET /admin/safety/reports

Returns the highly restricted queue with exact `status`, `category`, `priority`,
`assigned_to_user_id`, and `overdue` filters. This `/admin` family is retained
only in local/test compatibility applications; staging and production do not
mount it. National operations use the city-scoped routes below.

## GET /admin/safety/reports/{report_id}

Returns restricted description, derived parties, assignment, response target,
resolution/retention facts, source support ticket when present, and append-only
notes.

## POST /admin/safety/reports/{report_id}/transition

Requires `Idempotency-Key`, a valid next state, an active administrator
assignee, an internal note, and a participant-visible message on every
transition. Resolution and closure also require one of
`SAFETY_ACTION_TAKEN`, `REFERRED_TO_AUTHORITIES`, `INFORMATION_PROVIDED`,
`DUPLICATE`, or `NO_PLATFORM_ACTION`.

## POST /admin/support/tickets/{ticket_id}/escalate-safety

Creates exactly one separate safety report from a nonterminal, ride-linked
support case, copies the protected description server-side, and makes the
support case urgent/in progress. The idempotent command rejects a second safety
record for the same source ticket. Participant APIs still expose neither
internal note nor copied safety description.

Support tickets and safety reports carry backend-derived immutable `city_id`.
The operations contract is:

```text
GET  /operations/support/tickets
GET  /operations/support/tickets/{ticket_id}
POST /operations/support/tickets/{ticket_id}/triage
POST /operations/support/tickets/{ticket_id}/transition
POST /operations/support/tickets/{ticket_id}/escalate-safety

GET  /operations/safety/reports
GET  /operations/safety/reports/{report_id}
POST /operations/safety/reports/{report_id}/transition

GET  /operations/case-alerts
POST /operations/case-alerts/{alert_id}/acknowledge

GET  /operations/case-retention/holds
POST /operations/case-retention/holds
POST /operations/case-retention/holds/{hold_id}/release
GET  /operations/case-retention/actions
```

Every collection is constrained in SQL to the caller's authorized cities.
Resource commands lock and authorize the city before idempotency replay. Support
requires `manage_support_cases`; safety requires `manage_safety_cases`; alerts
accept either permission but return only the matching case kind. The assignee
must be an active user with the exact-city corresponding role, or an authorized
market-scoped platform administrator. The escalation response is deliberately a
minimal receipt and never returns copied description, reported identity, or
internal notes to a support-only operator.

Case-retention routes require `manage_case_retention`, which is reserved for a
market-scoped `PLATFORM_ADMIN`. Hold and action lists are paginated and
SQL-constrained to authorized cities, with optional exact city/case-kind and
status filters where applicable. Placement requires `Idempotency-Key`, exactly
one existing unprocessed support or safety case, a controlled legal reason, a
3–240 character non-secret authority reference containing only letters, digits,
`.`, `_`, `:`, `/`, or `-`, and a timezone-aware review deadline in the next 366
days. Only one active hold may exist per case. Release is a separate idempotent
command with a controlled release reason. Both commands authorize and lock city
scope before replay and write fixed-field audits without case or legal text.

Retention actions are worker-authored immutable evidence. They expose case/city
identity, `PERSONAL_DATA_ERASED`, policy version, due/execution timestamps, and
erased-note count, never erased data. A processed case is omitted from case
queues and returns no restricted detail; participant ownership also no longer
matches after its participant link is erased. No API restores or edits a
retention action.

---

# 40. Error Format

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

## Operational health and readiness

`GET /health` is process liveness, not dependency or delivery acceptance.
`GET /ready` probes PostgreSQL; in staging/production it additionally requires a
live registered process-owned PostgreSQL hint listener before and after that
probe. Loss, cleanup and retry remain unready until re-registration succeeds.
Either dependency failure returns `503` using the existing
`DEPENDENCY_UNAVAILABLE` envelope and message `The service is not ready.`; no
database, listener, provider or private error detail is disclosed. Success is
`200 {"status":"ready"}`. Local/test processes without that listener use SQL-only
readiness. Worker readiness separately requires SQL, a running supervisor and
successful iterations of all eight fixed worker loops. None of these responses
proves that a device received a hint or that missed hints were replayed.

## Operational metrics

`GET /internal/metrics` is outside the public versioned API and excluded from
OpenAPI. When `TAXIMOBILE_MONITORING_TOKEN` is configured, it requires that value
as a bearer token and returns Prometheus-compatible per-process request counts,
latency histograms, unhandled-error counts and fail-closed aggregate operational
snapshots. With no token in development it
returns `404`; invalid credentials return `401`. Staging and production refuse to
start without a 32+ character token.

Metric labels contain only a controlled HTTP method, the FastAPI route template,
status class, histogram boundary, or safe exception class. Raw URL paths, query
strings, request IDs, account identifiers, ride IDs, coordinates, provider
details, and exception messages are never labels.

The security-incident snapshot performs one five-second-bounded aggregate
database query and reports availability plus fixed `incident_severity` values
`SEV1` through `SEV4` for open, containment-overdue, postmortem-pending and
postmortem-overdue counts. It loads no incident content or identity. Snapshot
failure returns only `taximobile_security_incident_metrics_available 0` and
omits count series. API and worker expose the same authoritative snapshot, so
queries reduce role series with `min` or `max` and never sum them.

---

# 41. HTTP Status Codes

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

# 42. Authorization

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

# 43. Object Ownership

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

# 44. Idempotency

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
`POST /rides/{ride_id}/payments/cash/settle`,
`POST /rides/{ride_id}/payments/manual-transfer/submit`,
`POST /admin/payments/{payment_id}/manual-transfer/verify`, and
`POST /admin/payments/{payment_id}/manual-transfer/reject`, and
`POST /admin/payments/{payment_id}/refunds`,
`POST /support/tickets`, `POST /safety/reports`,
`POST /admin/support/tickets/{ticket_id}/triage`,
`POST /admin/support/tickets/{ticket_id}/transition`,
`POST /admin/safety/reports/{report_id}/transition`, and
`POST /admin/support/tickets/{ticket_id}/escalate-safety`. A retry with the same authenticated
user, operation, key, and request body returns the original response. Reusing a
key for a different request is rejected. Clients must preserve the key for a
network retry of the same user action and generate a new key for a new action.

---

# 45. Concurrency

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

# 46. Pagination

Collection endpoints should support pagination.

Example:

```text
?page=1&limit=20
```

Responses should provide enough metadata for clients to navigate results.

Large datasets must not be returned in a single request.

---

# 47. Filtering

Where appropriate, collection endpoints may support filtering.

Example:

```text
GET /rides?status=COMPLETED
```

Filtering parameters must be validated by the backend.

Clients must not be able to construct arbitrary database queries through filter parameters.

---

# 48. Sorting

Collection endpoints may support controlled sorting.

Example:

```text
?sort=created_at
&order=desc
```

The backend should use an allowlist of sortable fields.

---

# 49. Rate Limiting

The API should implement rate limiting.

Particularly sensitive endpoints include:

* Login.
* Registration.
* Password operations.
* Ride creation.
* Ride cancellation.
* Verification submission.
* Support creation.
* Safety-report creation.

Rate limits should be configurable.

The initial deployment reads explicit positive limits from environment settings
for registration, login, ride creation, support/safety creation, driver
location updates, verification submission, routing, place search, and reverse
geocoding. The API never trusts a mobile
application to self-enforce an abuse threshold.

Development and isolated tests use an in-process fixed-window adapter. Staging
and production use a shared PostgreSQL adapter with atomic bucket updates and
database-authoritative time, so adding an API instance does not multiply a
caller's quota. Bucket identities are persisted only as SHA-256 digests. A shared
limiter failure returns the standard safe `503 DEPENDENCY_UNAVAILABLE` envelope;
the endpoint does not fail open.

---

# 49.5 Place Discovery

These routes are authenticated and provider-neutral. They never return provider
credentials or native response fields, do not persist query text, and are
independently rate-limited per account. Request logs contain the reviewed route
template rather than query strings. `language` is closed to `ar`, `en`, or `fr`.
The fail-closed deployment default returns `503` while geocoding is disabled.

## GET /places/search

Query parameters:

```text
city_id=<public booking-capable city UUID>
query=<2-120 visible characters>
language=ar|en|fr             # optional; default en
limit=1..10                   # optional; default 8
```

Whitespace is normalized before the approved provider is called. The active
city boundary supplies a ranking viewbox, while Morocco remains the adapter's
country filter. The viewbox is not an authorization decision and does not hide a
nearby destination solely because it is outside the polygon. Each candidate is
checked against the exact active service-area version in PostGIS.

```json
{
  "city_id": "city-uuid",
  "query": "Gare Rabat Ville",
  "items": [
    {
      "id": "opaque-24-character-result-id",
      "primary_text": "Gare Rabat Ville",
      "secondary_text": "Hassan, Rabat, Maroc",
      "coordinate": {"latitude": 34.0209, "longitude": -6.8416},
      "kind": "POI",
      "pickup_serviceable": true
    }
  ],
  "attribution": {
    "text": "© OpenStreetMap contributors",
    "url": "https://www.openstreetmap.org/copyright"
  }
}
```

Kinds are `ADDRESS`, `STREET`, `LOCALITY`, `POI`, or `OTHER`. Result IDs are
opaque and ephemeral; clients select the returned coordinate and label rather
than later dereferencing the ID. `pickup_serviceable=false` is an authoritative
warning for pickup selection, not a statement that every destination outside the
polygon is forbidden. Ride estimate/create repeats its own city and policy checks.

## GET /places/reverse

Parameters are `city_id`, bounded WGS84 `latitude`/`longitude`, and optional
closed `language`. The response has the same attribution and one nullable `item`.
The item's coordinate is always the exact requested coordinate, never the nearby
OSM object's centroid; geocoder output supplies only display text/type. A no-match
response is `200` with `item: null`. Provider disablement, timeout, rejection or
malformed output returns a safe `503` explaining that the coordinate remains
usable. An unavailable/inactive city returns `404`; malformed values return
`422`; abuse returns `429`.

Neither route stores saved Home/Work labels. Clients must not transform such
personal labels into provider query text without a separately approved saved-place
privacy design.

---

# 50. Routing

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

# 51. Real-Time Communication

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

# 52. Client Synchronization

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

# 53. API Security Principles

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

# 54. API Versioning

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

# 55. API Documentation

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

# 56. Development Environment

During development, the API should be accessible locally.

Example:

```text
http://localhost:8000/api/v1
```

The exact port is configurable.

The Kotlin application should obtain the API base URL from configuration rather than hard-coding production URLs throughout the codebase.

---

# 57. API Testing

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

# 58. Minimum Viable API

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
GET  /rides/{ride_id}/receipt
POST /rides/{ride_id}/payments/cash/settle
POST /rides/{ride_id}/payments/manual-transfer/submit
GET  /drivers/me/earnings
```

### Routing

```text
POST /routing/route
```

Hosted card-session and callback endpoints, including CMI, are intentionally
excluded. The initial electronic option is external bank/M-Wallet transfer with
manual authoritative reconciliation; it requires no fabricated provider protocol.

### Transitional local/test administration

```text
POST /admin/drivers/{driver_id}/approve
POST /admin/pricing-rules
POST /admin/pricing-rules/{pricing_rule_id}/activate
POST /admin/users/{user_id}/sessions/revoke
POST /admin/users/{user_id}/suspend
POST /admin/users/{user_id}/reactivate
GET  /admin/audit-logs
GET  /admin/payments/manual-transfers
POST /admin/payments/{payment_id}/manual-transfer/verify
POST /admin/payments/{payment_id}/manual-transfer/reject
GET  /admin/payments/refunds
POST /admin/payments/{payment_id}/refunds
```

These endpoints are mounted only when
`TAXIMOBILE_LEGACY_ADMIN_API_ENABLED=true`. That setting defaults to true in
`development` and `test`, defaults to false in `staging` and `production`, and
is rejected if enabled in either production-like environment. They require the
server-side `ADMIN` role. They do not bootstrap an
administrator: initial administrative access is a controlled deployment operation,
never a public API capability. Driver approval records a verification decision and
grants only the `DRIVER` role. Tariffs are first created inactive; activation is
audited and closes an earlier overlapping active tariff at the new tariff's effective
time. The API never rewrites historical fare records.

This is a local fixture and migration aid, not a pilot or production surface.
The `/operations` namespace and scoped grants are the only administrative HTTP
authority permitted in staging and production. Legacy routes must not be
extended into cross-city management merely by adding a `city_id` parameter.

#### Legacy route retirement inventory

The committed OpenAPI contract contains 21 legacy operations when the local/test
switch is enabled. Runtime routing and OpenAPI share one router factory, so a
disabled route cannot remain callable while merely disappearing from the schema.

| Legacy route group | Count | Scoped successor | Standing |
|---|---:|---|---|
| `GET /admin/audit-logs` | 1 | `GET /operations/audit-logs` | Replaced; legacy local/test only. |
| Driver approval | 1 | `POST /operations/driver-applications/{application_id}/decisions` | Replaced by city-scoped application review. |
| Pricing create/activate | 2 | `/operations/cities/{city_id}/pricing-rules` and `/operations/pricing-rules/{version_id}/*` | Replaced by versioned city economics. |
| Payment transfer/refund list and commands | 5 | Same command set under `/operations/payments` | Replaced with city/operator filtering and `RECONCILE_PAYMENTS`. |
| Support queue/detail/triage/transition/escalation | 5 | Same command set under `/operations/support` | Replaced with scoped case authority. |
| Safety queue/detail/transition | 3 | Same command set under `/operations/safety` | Replaced with scoped case authority. |
| `POST /admin/vehicles/{vehicle_id}/verify` | 1 | `POST /operations/driver-applications/{application_id}/vehicles/{vehicle_id}/verify` | Replaced by scoped, MFA-protected application evidence review. |
| User session revocation, suspension, reactivation | 3 | `/operations/markets/{market_id}/users/{user_id}/sessions/revoke`, `/suspend`, and `/reactivate` | Replaced by market-authorized, recent-MFA account containment. |

No web or mobile production client may call `/admin`. CI verifies the deployment
manifests force the switch off and that a disabled application exposes no path
whose prefix is `/api/v1/admin` while retaining representative `/operations`
routes. The protected operations console now exposes the safe commands only to a
session carrying the dedicated permission. Release work still includes proving
zero production callers, rehearsing containment and recovery, and
recording a dated decision to remove the compatibility implementation. None of
that is permission to re-enable the compatibility surface.

The repository also runs an explicit client-source retirement gate. It scans the
maintained Android, iOS, shared and browser source roots for legacy endpoint
literals and fails without printing matching source content. Every HTTP request
addressed to the configured `/admin` namespace increments one fixed `served` or
`blocked` metric. A locally routed compatibility response carries deprecation and
warning headers; a disabled production-like route remains an ordinary safe 404
and does not advertise the old surface. Monitoring treats any `served` increase
as a promotion-stopping critical alert. These controls do not replace a hosted
traffic review or the owner-approved dated code-removal decision.

The scoped account-security commands require an operations token,
`manage_account_security`, MFA no older than the configured recent-MFA window,
and `Idempotency-Key`. Only `PLATFORM_ADMIN` currently carries that permission.
The request has no free-text reason: `reason_code` is one of
`ACCOUNT_COMPROMISE`, `VERIFIED_USER_REQUEST`, `SAFETY_CONTAINMENT`,
`LEGAL_REQUIREMENT`, or `SECURITY_INCIDENT`, and `case_reference` must use an
allowlisted `SUP-`, `SAF-`, or `SEC-` identifier shape.

These are account-wide actions even though the route starts from a market. The
target must have recorded passenger, driver, application, booking, support,
safety, or staff history in that market, and the acting principal must hold the
permission across **every** market associated with the account. An unrelated
target returns the same not-found boundary; incomplete cross-market coverage
fails with conflict and requires escalation to appropriately scoped staff. A
single city grant can never silently become nationwide suspension authority.

Revoking sessions invalidates every active mobile and operations session plus
every push registration owned by the target. Suspension performs that revocation
in the same transaction and immediately blocks access-token validation, refresh,
operations access, and login. Reactivation never revives old credentials: the
user must authenticate again. Self-action is refused, and a deactivated account
cannot be restored through suspension recovery. Every command writes a
fixed-field scoped audit event containing reason code, case reference, old/new
status and affected counts; reusing an idempotency key with another payload fails.
The console deliberately provides no broad account search: staff copy the exact
user UUID from an authorized case, select the association market, choose a closed
reason, enter the controlled case reference, and type an action-specific
confirmation. A recent-MFA rejection opens step-up but never replays the command.

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

# 59. National Expansion API (incremental)

These endpoint families are the approved target contract for `operations.md`.
The Phase 12 control-plane, Phase 13 recruiting/application/review, Phase 14
city-economics, Phase 15 published-fixed-route, Phase 16 scheduled-booking, and
Phase 17 aggregate-analytics subsets are present in generated OpenAPI. Each later
slice requires migrations, generated OpenAPI, negative scope tests, and client
contract updates. Existing v1 behavior must not be broken silently; any
incompatible request/response change requires an additive endpoint or a new API
version.

## 59.1 Public city and fixed-route catalog

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

## 59.2 Passenger immediate and scheduled service

Existing point-to-point ride creation remains compatible. The delivered Phase
15 contract accepts an optional published
`fixed_route_direction_version_id`; when supplied, the backend derives
city/operator, start/finish, geometry version, and flat fare and rejects
conflicting arbitrary coordinates. `POST /rides` still requires a unique
`Idempotency-Key`. Fixed-route estimates and rides cannot be created from an
unpublished direction, disabled configuration, paused city, inactive fare, or
client-supplied substitute coordinates.

Scheduled bookings use their own resources:

```text
POST /scheduled-bookings/estimate
POST /scheduled-bookings
GET  /scheduled-bookings
GET  /scheduled-bookings/{booking_id}
POST /scheduled-bookings/{booking_id}/cancel
```

Estimate and creation include either validated point-to-point locations or one
published direction version plus `scheduled_for`. Estimate is authenticated and
non-mutating; it returns the resolved endpoints, timezone, exact economics, and
cancellation terms used by the passenger review screen. Creation requires
`Idempotency-Key` and may echo the reviewed tariff, operator-fee, and scheduling
policy versions. If any echoed version changed, creation returns `409` and the
client must request a new estimate instead of silently accepting different terms.
The creation response
contains backend-resolved city/operator/service, lifecycle status, city timezone
presentation data, transport fare, scheduling surcharge, passenger-funded
operator fee if any, passenger total, policy versions, cancellation terms, and
whether a driver has committed. It never promises a taxi merely because the
booking was accepted.

Cancellation is backend-authorized, idempotent, and returns explicit financial
outcomes such as no charge, retained surcharge, pending refund, or completed
refund according to the snapshotted policy. The client cannot submit those
outcomes.

## 59.3 Driver city applications and scheduled work

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
GET  /drivers/me/scheduled-offer-preferences
PATCH /drivers/me/scheduled-offer-preference
POST /scheduled-offers/{offer_id}/accept
POST /scheduled-offers/{offer_id}/decline
GET  /drivers/me/scheduled-commitments
```

The same applicant-owned contract serves driver mobile and public web clients.
No request field grants a role, approval, city authorization, or online state.
Application responses expose the requirement version and applicant-safe status,
not reviewer-private notes or another applicant's data.

Phase 13 implements the recruiting-city and city-application routes in this
section. Phase 16 implements the scheduled preference, offer, response, and
commitment routes and exposes them through separate driver mobile navigation.

Scheduled acceptance returns `200` only after its commitment, booking pointer,
offer responses, lifecycle event, passenger notification and outbox work commit
together. A closed/expired/already-accepted offer or a genuine overlap returns
`409`; repeated acceptance is a conflict, not an idempotent success contract.
Buffered commitment windows are half-open, so exact adjacency is allowed.
Only the named driver-window exclusion violation is translated into the overlap
message. Other integrity faults roll back and use the sanitized `500`
`INTERNAL_ERROR` boundary; they must not be attributed to the driver's schedule.

Both live and scheduled acceptance revalidate the driver's current work under a
driver lock. `POST /ride-offers/{offer_id}/accept` returns its existing generic,
race-safe `409` when an active scheduled range now contains server time; it does
not disclose the other booking. `POST /scheduled-offers/{offer_id}/accept`
returns `409` when its proposed range contains server time and the driver already
has an active live ride. Work outside the current range remains eligible. Neither
client may override the result or treat an old offer response as assignment.

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
it stops new future offers and does not cancel accepted commitments. The plural
GET returns persisted per-city state so clients do not infer it from visible
offers or immediate online status.

Scheduled offers contain server time, pickup time, city/service, point-to-point
or fixed-route direction, offer/commitment expiry, cancellation terms, transport
fare, scheduling surcharge, operator fee/funding mode, and expected driver net.
Acceptance atomically checks expiry, city/vehicle/credential eligibility and
schedule conflicts. Decline is non-punitive and advances the configured offer
process.

## 59.4 Protected operations control plane

The operations console uses a dedicated `/operations` namespace so participant
routes do not accidentally inherit administrative reads. Collection, resource,
and command paths are explicit; clients must not invent a generic mutation
endpoint:

Phase 12 currently implements the following `/api/v1` routes:

```text
POST            /operations/auth/login
POST            /operations/auth/mfa/verify
POST            /operations/auth/mfa/step-up
POST            /operations/auth/refresh
POST            /operations/auth/logout
GET             /operations/auth/session

GET             /operations/markets
GET/POST        /operations/cities
GET/PATCH       /operations/cities/{city_id}
POST            /operations/cities/{city_id}/lifecycle-transitions
GET/POST        /operations/operators
GET/PATCH       /operations/operators/{operator_id}
GET/POST        /operations/operator-city-assignments
POST            /operations/operator-city-assignments/{assignment_id}/retire
GET/POST        /operations/administrative-grants
DELETE          /operations/administrative-grants/{grant_id}
GET             /operations/administrative-grant-requests
POST            /operations/administrative-grant-requests/create
POST            /operations/administrative-grant-requests/revoke
POST            /operations/administrative-grant-requests/{request_id}/approve
POST            /operations/administrative-grant-requests/{request_id}/reject
POST            /operations/administrative-grant-requests/{request_id}/cancel
POST            /operations/markets/{market_id}/users/{user_id}/sessions/revoke
POST            /operations/markets/{market_id}/users/{user_id}/suspend
POST            /operations/markets/{market_id}/users/{user_id}/reactivate

GET/POST        /operations/cities/{city_id}/service-area-versions
GET/PATCH       /operations/service-area-versions/{version_id}
POST            /operations/service-area-versions/{version_id}/transitions
GET/POST        /operations/cities/{city_id}/configuration-versions
GET/PATCH       /operations/city-configuration-versions/{version_id}
POST            /operations/city-configuration-versions/{version_id}/submit
POST            /operations/city-configuration-versions/{version_id}/approve
POST            /operations/city-configuration-versions/{version_id}/activate
POST            /operations/city-configuration-versions/{version_id}/readiness-decisions

GET             /operations/rollout-overview
GET             /operations/audit-logs

GET/POST        /operations/security-incidents
GET             /operations/security-incidents/{incident_id}
GET/POST        /operations/security-incidents/{incident_id}/timeline
GET             /operations/security-incidents/{incident_id}/responsibilities
POST            /operations/security-incidents/{incident_id}/responsibilities/{responsibility}/assign
POST            /operations/security-incidents/{incident_id}/transitions
POST            /operations/security-incidents/{incident_id}/postmortem/complete
```

The two direct `/operations/administrative-grants` mutation methods exist only
for explicit development/test fixture compatibility and return `409` in staging
or production. Production staff changes use the request routes. Create snapshots
the requested target/role/scope/expiry; revoke snapshots an exact live source
grant. All write routes require `Idempotency-Key`, recent operations MFA and
`manage_scoped_staff_grants` for the resolved market.

Requests begin at `PENDING` with `optimistic_version=1`. Approve and reject require
a decider different from requester and target; cancel requires the requester.
Each decision body contains `expected_version` and a 3–240 character independent
reason. Approval revalidates live authority, target/scope, expiry, duplicates,
source grant and platform-admin continuity under one market lock. Success changes
the request to `APPROVED`, `REJECTED` or `CANCELLED`, increments its version and
records decision identity/time. Create approval returns `resulting_grant_id`;
revoke approval leaves that field null and revokes `source_grant_id`. Terminal or
stale requests return `409`; unauthorized resources remain hidden as `404`.

Security-incident routes require the dedicated market-scoped
`manage_security_incidents` permission; in the initial source slice only a
market-scoped platform administrator receives it. Every write also requires
recent operations MFA and `Idempotency-Key`. Creation accepts one authorized
market, an optional city in that market, severity/category, a bounded summary,
timezone-aware detection time and an explicit future containment deadline. The
server assigns the reporting administrator as initial lead and generates a
non-personal `SEC-...` reference.

Timeline commands accept only evidence, containment, communication-decision,
recovery or postmortem event kinds. Each manual event must link either an audit
ID visible in the incident scope or a bounded external runbook/reference; raw
secrets and provider payloads are prohibited. Timeline rows are append-only and
ordered by a database-unique sequence. Lifecycle-generated open/transition rows
cannot be submitted as manual event types.

Transitions require `expected_version`, a bounded summary and occurrence time.
The only path is `OPEN` → `CONTAINING` → `CONTAINED` → `RECOVERING` →
`RECOVERED` → `CLOSED`; invalid or stale actions return `409`. Closing also
requires a timezone-aware postmortem deadline after closure and within 90 days.
`POST /operations/security-incidents/{incident_id}/postmortem/complete` is a
one-time closed-incident command. It requires recent MFA, idempotency,
`expected_version`, a controlled outcome, bounded conclusion, timezone-aware
completion time and a same-scope audit ID or bounded external reference.
`FOLLOW_UP_REQUIRED` must link the external approved work reference. The command
increments the incident version and appends a referenced `POSTMORTEM_ACTION`;
completed postmortems cannot be overwritten.

Each incident has four closed responsibility types: security response lead,
communications lead, operations liaison and postmortem owner. Creation assigns
the reporting administrator as the initial security response lead. The
responsibility collection returns current and released tenures; it is bounded and
scope-hidden like the parent incident. Assignment requires the current incident
version, exact assignee UUID, timezone-aware occurrence time and an approved
roster/shift/incident-command reference. The candidate must be an active user with
a live exact-market platform-administrator grant. Missing, inactive, expired,
revoked and wrong-market candidates return the same generic `409`; there is no
candidate search endpoint.

Successful assignment releases the previous active tenure for that responsibility,
creates the replacement, increments the incident version and appends a generated
`RESPONSIBILITY_CHANGED` timeline fact. Reassigning the security response lead
also changes `lead_user_id`. Assigning the same current user, using a stale
version, backdating before opening/current tenure, or assigning after postmortem
completion is refused. Idempotent replay returns the original assignment response.
The general audit record carries controlled role/change flags but no assignee UUID
or roster reference.
Incident narrative is returned only on the restricted incident surface. The
general audit log receives controlled status/category/severity, sequence,
deadline and reference-presence fields rather than copied narrative.

The protected web client implements all nine collection/detail/timeline/
responsibility/transition calls through the shared endpoint builder. Its dynamic
responsibility segment fails closed to the four contract values. The source-contract gate
now validates 112 expanded web HTTP operations against FastAPI; browser-side
permission hiding and typed confirmation are usability defenses, not substitutes
for the API authorization above.

Phase 17 adds the following read-only operations routes:

```text
GET             /operations/analytics/definitions
GET             /operations/analytics/facts?city_id={city_id}
```

Both require `view_scoped_operational_aggregates` through an active operations
session. `facts` requires one exact authorized city, accepts optional timezone-
aware `from`/`to` bounds (a positive window of at most 31 days), and optional
`service_type`/`metric_code` filters. It returns hourly cells and immutable
policy, route-direction, matching-version, service, booking, outcome, category,
and currency dimensions where applicable. Every measure—including counts,
amounts, averages, work-distribution bounds, and Gini—is `null` when the source
cell contains fewer than five records/entities; `suppressed=true` distinguishes
that state from a measured zero.

Definitions publish each code's family, title, unit, allowlisted source, purpose,
owner, semantic version, 730-day retention, minimum cell size, and late-event
policy. Facts expose only aggregates plus source watermark/computation time. They
never expose participant IDs, coordinates, notes, documents, arbitrary payloads,
provider references, or payment credentials, and they can never authorize or
mutate a business record.

The city-scoped support/safety operations slice adds:

```text
GET              /operations/support/tickets
GET              /operations/support/tickets/{ticket_id}
POST             /operations/support/tickets/{ticket_id}/triage
POST             /operations/support/tickets/{ticket_id}/transition
POST             /operations/support/tickets/{ticket_id}/escalate-safety
GET              /operations/safety/reports
GET              /operations/safety/reports/{report_id}
POST             /operations/safety/reports/{report_id}/transition
GET              /operations/case-alerts
POST             /operations/case-alerts/{alert_id}/acknowledge
GET              /operations/case-retention/holds
POST             /operations/case-retention/holds
POST             /operations/case-retention/holds/{hold_id}/release
GET              /operations/case-retention/actions
```

All mutation routes above require `Idempotency-Key`. A scoped resource lookup is
part of the locked SQL statement and precedes replay; losing city authority
therefore makes an old key inaccessible. Alert acknowledgement does not resolve
or transition its case.

The case-retention placement and release mutations also require
`Idempotency-Key`. They lock an authorized city-scoped case/hold before replay.
The retention action list is read-only evidence written by the fixed worker.

Phase 18 makes the existing lifecycle and readiness commands the repeatable city
rollout API. No generic rollout mutation or city-specific endpoint is added.
`POST /operations/city-configuration-versions/{version_id}/readiness-decisions`
accepts only an allowlisted `gate_code`, `PASSED` or `FAILED`, a bounded non-secret
evidence reference, and the expected optimistic configuration version. For an
approved bundle, the backend requires the deciding account to differ from the
recorded configuration submitter. Configuration approval enforces the same
maker/reviewer boundary; retries of an already-completed transition remain
idempotent. The evidence reference points to a controlled record containing the
accountable owners and review or expiry dates rather than copying names, legal
documents, credentials, or participant data into TaxiMobile. For an
initial launch, `PILOT_SERVICE_AND_FAIRNESS` is accepted only on the active
configuration of a city currently in `PILOT`. An approved replacement may
receive a new change-impact decision while its city is already `ACTIVE` or
`PAUSED`; evidence is not inherited. `POST_LAUNCH_REVIEW` can pass only on the
active bundle after the city has reached `ACTIVE`.

Configuration responses expose both `missing_pilot_entry_gates` and
`missing_public_activation_gates`, plus `post_launch_review_status`.
`missing_readiness_gates` remains an additive compatibility alias for the public-
activation set. Rollout city summaries expose passed/required/missing values for
both stages and the post-launch status. Lifecycle transitions revalidate the
stage, active coherent configuration, and current evidence transactionally:

```text
CONFIGURING → PILOT   ten pilot-entry gates
PILOT → ACTIVE        pilot-entry gates + PILOT_SERVICE_AND_FAIRNESS
PAUSED → ACTIVE       full public-activation set (legacy compatibility exception only)
```

Activating a replacement configuration while a city is already operating also
requires that replacement bundle's stage-appropriate gates. Evidence on the old
bundle never transfers implicitly.

Migration `20260831_0044` adds the delivered payment-control routes:

```text
GET/POST        /operations/cities/{city_id}/payment-recipient-accounts
PATCH           /operations/payment-recipient-accounts/{account_id}
POST            /operations/payment-recipient-accounts/{account_id}/verify
POST            /operations/payment-recipient-accounts/{account_id}/retire
GET/POST        /operations/cities/{city_id}/payment-capability-versions
PATCH           /operations/payment-capability-versions/{capability_id}
POST            /operations/payment-capability-versions/{capability_id}/submit
POST            /operations/payment-capability-versions/{capability_id}/approve
POST            /operations/payment-capability-versions/{capability_id}/activate
GET             /operations/payments/manual-transfers
POST            /operations/payments/{payment_id}/manual-transfer/verify
POST            /operations/payments/{payment_id}/manual-transfer/reject
GET             /operations/payments/refunds
POST            /operations/payments/{payment_id}/refunds
```

Each non-legacy enabled configuration service supplies an exact
`payment_capability_version_id`. Activation revalidates that capability's
city/operator/service scope, status, effective range, mandatory cash fallback,
and verified recipient when transfer is enabled. The operations web console uses
these routes and never infers payment methods from deployment-wide settings.

Phase 13 currently implements the following additional routes:

```text
GET             /drivers/recruiting-cities
GET             /drivers/recruiting-cities/{city_id}/requirements
POST            /drivers/me/city-applications
GET             /drivers/me/city-applications
GET/PATCH       /drivers/me/city-applications/{application_id}
POST            /drivers/me/city-applications/{application_id}/submit
POST            /drivers/me/city-applications/{application_id}/withdraw
POST            /drivers/me/city-applications/{application_id}/documents
DELETE          /drivers/me/city-applications/{application_id}/documents/{document_id}

GET/POST        /operations/cities/{city_id}/driver-requirement-versions
GET/PATCH       /operations/driver-requirement-versions/{version_id}
POST            /operations/driver-requirement-versions/{version_id}/submit
POST            /operations/driver-requirement-versions/{version_id}/activate
GET             /operations/driver-applications
GET             /operations/driver-applications/{application_id}
POST            /operations/driver-applications/{application_id}/decisions
POST            /operations/driver-applications/{application_id}/vehicles/{vehicle_id}/verify
GET             /operations/driver-applications/{application_id}/documents/{document_id}
GET             /operations/cities/{city_id}/operational-aggregates
```

The three document routes implement real file transfer when the all-or-none
protected adapter is configured and return `503` when storage or scanning is
disabled/unavailable. Upload accepts exactly one `file`, one
`requirement_item_id`, and one integer `expected_version`; the request is bounded
before multipart parsing and then by the decoded-file limit. Applicant ownership
is checked before capability or body details are exposed. Replacement and deletion
increment the application version. Reviewer retrieval requires the document-read
permission, city scope, recent MFA, a clean scan status, and a per-reviewer limit;
it returns an opaque download name with `Cache-Control: no-store` and
`X-Content-Type-Options: nosniff`, and records an audit event. Driver availability
responses now carry backend-confirmed `city_id` and `service_type`; online
commands require an active matching city/service authorization and matching
selects candidates within the ride's city.

Vehicle verification is bound to the exact scoped application and vehicle
evidence row. It requires a submitted or under-review application, an active
vehicle owned by that application's driver, the application's current optimistic
version, recent operations MFA, `Idempotency-Key`, and the controlled
`VEHICLE_REQUIREMENTS_CONFIRMED` reason. It records market/city/application
provenance in fixed-field audit data and marks the selected evidence accepted.
It cannot verify an unrelated vehicle or use a city grant outside the
application's city. First-time recruitment policies should use `VEHICLE_OWNED`
for submission and let this staff command establish `VERIFIED`; requiring
`VEHICLE_VERIFIED` before first submission is appropriate only for an already
verified vehicle.

Password-only login and JSON refresh tokens are local/test scaffolding only.
Hosted password verification returns a five-minute MFA challenge and no token.
`/mfa/verify` accepts a six-digit RFC 6238 TOTP or one complete recovery code;
five failures consume the challenge. Success returns a ten-minute operations-
audience access token and CSRF token, while the eight-hour rotating refresh token
is set only as a `Secure`, `HttpOnly`, `SameSite=Strict` cookie scoped to the
operations-auth path. `/refresh` requires that cookie plus `X-CSRF-Token`, rotates
both, and returns no refresh token in JSON. Browser requests include credentials,
but no token is persisted in browser storage.

`/mfa/step-up` requires a live operations access token and consumes a fresh TOTP
counter or one recovery code. The session's verified time/method is updated for
the fixed ten-minute high-impact-command window. A blocked command is not
replayed automatically. Production configuration rejects password-only mode,
missing/invalid MFA encryption material, or disabled secure cookies. Access
tokens use the operations audience and cannot be substituted with mobile tokens.

Phase 14 currently implements the following additional operations routes:

```text
GET/POST        /operations/cities/{city_id}/pricing-rules
GET/PATCH       /operations/pricing-rules/{version_id}
POST            /operations/pricing-rules/{version_id}/submit
POST            /operations/pricing-rules/{version_id}/activate
GET/POST        /operations/cities/{city_id}/operator-fee-policies
GET/PATCH       /operations/operator-fee-policies/{version_id}
POST            /operations/operator-fee-policies/{version_id}/submit
POST            /operations/operator-fee-policies/{version_id}/activate
GET/POST        /operations/cities/{city_id}/scheduling-policies
GET/PATCH       /operations/scheduling-policies/{version_id}
POST            /operations/scheduling-policies/{version_id}/submit
POST            /operations/scheduling-policies/{version_id}/activate
```

These collections require an explicit city and operator scope and the named
tariff, operator-fee, or scheduling-policy permission. Draft updates use
`optimistic_version`; submit and activate are separate reason-bearing commands.
Activation rejects cross-scope, invalid, expired, overlapping, or incomplete
policies and records replacement/audit history. Scheduling routes configure only
the surcharge/allocation foundation; they do not create scheduled bookings.

The inventory below began as the Phase 14–17 target. As of 2026-09-02, its
pricing, payment, fixed-route, scheduled-booking, analytics, rollout, audit,
support/safety, alert, and retention families are implemented in source. The
generated OpenAPI document, not this hand-maintained list, is the exact method and
path authority. Routes absent from OpenAPI remain unimplemented even if named in
older prose.

```text
POST            /operations/auth/login
POST            /operations/auth/mfa/verify
POST            /operations/auth/mfa/step-up
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
GET            /operations/administrative-grant-requests
POST           /operations/administrative-grant-requests/create
POST           /operations/administrative-grant-requests/revoke
POST           /operations/administrative-grant-requests/{request_id}/approve
POST           /operations/administrative-grant-requests/{request_id}/reject
POST           /operations/administrative-grant-requests/{request_id}/cancel
POST           /operations/markets/{market_id}/users/{user_id}/sessions/revoke
POST           /operations/markets/{market_id}/users/{user_id}/suspend
POST           /operations/markets/{market_id}/users/{user_id}/reactivate

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
POST            /operations/driver-applications/{application_id}/vehicles/{vehicle_id}/verify

GET/POST         /operations/cities/{city_id}/pricing-rules
GET/PATCH        /operations/pricing-rules/{version_id}
POST             /operations/pricing-rules/{version_id}/submit
POST             /operations/pricing-rules/{version_id}/activate
GET/POST         /operations/cities/{city_id}/operator-fee-policies
GET/PATCH        /operations/operator-fee-policies/{version_id}
POST             /operations/operator-fee-policies/{version_id}/submit
POST             /operations/operator-fee-policies/{version_id}/activate
GET/POST         /operations/cities/{city_id}/scheduling-policies
GET/PATCH        /operations/scheduling-policies/{version_id}
POST             /operations/scheduling-policies/{version_id}/submit
POST             /operations/scheduling-policies/{version_id}/activate

GET/POST         /operations/cities/{city_id}/payment-recipient-accounts
PATCH            /operations/payment-recipient-accounts/{account_id}
POST             /operations/payment-recipient-accounts/{account_id}/verify
POST             /operations/payment-recipient-accounts/{account_id}/retire
GET/POST         /operations/cities/{city_id}/payment-capability-versions
PATCH            /operations/payment-capability-versions/{capability_id}
POST             /operations/payment-capability-versions/{capability_id}/submit
POST             /operations/payment-capability-versions/{capability_id}/approve
POST             /operations/payment-capability-versions/{capability_id}/activate
GET              /operations/payments/manual-transfers
POST             /operations/payments/{payment_id}/manual-transfer/verify
POST             /operations/payments/{payment_id}/manual-transfer/reject
GET              /operations/payments/refunds
POST             /operations/payments/{payment_id}/refunds

GET/POST         /operations/cities/{city_id}/fixed-routes
GET              /operations/cities/{city_id}/fixed-route-fare-options
GET/PATCH        /operations/fixed-routes/{route_id}
POST             /operations/fixed-routes/{route_id}/retire
POST             /operations/fixed-routes/{route_id}/versions
GET/PATCH        /operations/fixed-route-versions/{version_id}
POST             /operations/fixed-route-versions/{version_id}/submit
POST             /operations/fixed-route-versions/{version_id}/publish
POST             /operations/fixed-route-versions/{version_id}/retire

GET              /operations/scheduled-bookings
GET              /operations/scheduled-bookings/{booking_id}
GET              /operations/analytics/definitions
GET              /operations/analytics/facts
GET              /operations/rollout-overview
GET              /operations/cities/{city_id}/operational-aggregates
GET              /operations/audit-logs
GET              /operations/support/tickets
GET              /operations/support/tickets/{ticket_id}
POST             /operations/support/tickets/{ticket_id}/triage
POST             /operations/support/tickets/{ticket_id}/transition
POST             /operations/support/tickets/{ticket_id}/escalate-safety
GET              /operations/safety/reports
GET              /operations/safety/reports/{report_id}
POST             /operations/safety/reports/{report_id}/transition
GET              /operations/case-alerts
POST             /operations/case-alerts/{alert_id}/acknowledge
GET              /operations/case-retention/holds
POST             /operations/case-retention/holds
POST             /operations/case-retention/holds/{hold_id}/release
GET              /operations/case-retention/actions
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
* Browser CORS accepts only exact reviewed HTTPS origins. MFA, recent step-up,
  secure refresh-cookie rotation, and CSRF binding are application-enforced;
  the deployed web artifact still requires its reviewed restrictive CSP.

The Phase 15 fare-options route exposes only unbound `DRAFT`/`IN_REVIEW`
fixed-route fare metadata in the caller's exact city/operator scope. It does not
grant tariff mutation permission or expose pricing audit actors. A route editor
may bind one option while creating draft geometry. Conversely, a pricing editor
may create a fixed-route fare against an existing unpriced draft direction.
Fare activation requires the reciprocal one-to-one link; route submission
requires a linked fare; route publication requires that fare to be active for
the full route period. These checks are backend-owned and optimistic-versioned.

Operations authentication issues a dedicated administrative audience and never
accepts a normal mobile bearer token as sufficient. `auth.md` and `security.md`
fix the implemented TOTP/recovery, ten-minute step-up, eight-hour refresh-cookie,
CSRF, enrollment/replacement, and revocation protocol. Deployment-specific CSP,
reviewer ownership, access review, and incident exercises remain release
evidence rather than API behavior.

### City-authorization lifecycle decisions

`POST /operations/driver-applications/{application_id}/authorization/decisions`
uses the isolated operations session, `review_driver_applications` permission,
the application's city scope, recent MFA and a required `Idempotency-Key`.
Scope is checked before returning even a stored replay response.

```json
{
  "expected_application_version": 7,
  "action": "SUSPEND",
  "reason_code": "ELIGIBILITY_REVIEW"
}
```

| Action | Allowed current states | Required reason | Result |
| --- | --- | --- | --- |
| `SUSPEND` | `ACTIVE` | `SAFETY_REVIEW` or `ELIGIBILITY_REVIEW` | `SUSPENDED` |
| `REVOKE` | `ACTIVE`, `SUSPENDED`, `EXPIRED` | `OPERATING_PERMISSION_WITHDRAWN` | `REVOKED` |
| `REINSTATE` | `SUSPENDED` | `ELIGIBILITY_REVIEW_PASSED` | `ACTIVE`, after current eligibility checks |

Success returns `OperationsDriverApplicationDetailResponse`, increments the
application version, appends a city-scoped authorization audit event, and writes
one driver-owned `DRIVER_CITY_AUTHORIZATION_CHANGED` notification plus one
`driver.city_authorization.changed` outbox event in the same transaction. The
event carries only `authorization_id`; the delivery worker reloads the
authorization/profile to derive the recipient and sends a non-authoritative
refresh hint. The original application approval remains historical; the
nested authorization status represents current permission. Reinstatement
requires an unexpired original authorization, active global and professional
account, approved driver, verified owned vehicle, valid credentials, complete
city evidence, reviewed services and no other active authorization for that
driver/city. It cannot extend expiry, change city/services/vehicle or reinstate
revoked authority; revocation requires a new application.

`401` means no valid operations session; `403` means missing review permission
or recent MFA; `404` hides absent/out-of-scope applications; `409` means stale
application version, changed command payload under the same key, invalid
transition or failed reinstatement eligibility; `422` rejects malformed or
extra fields. Unexpected faults produce the standard sanitized `500` and roll
back the decision, version, audit, notification, outbox event and idempotency
result together. Replaying a completed idempotency key creates no additional
notification or outbox row.

Application, driver and authorization locks serialize decisions with assignment.
A restriction that commits first prevents subsequent eligible assignment in
that city. Assignment committed first retains its ride and is handled through
the ordinary ride/support workflow. Other city authorizations and global login
remain unchanged. Existing future commitments retain their history and are
revalidated at handoff. No automatic driver online transition or push-delivery
guarantee is introduced by this endpoint.

## 59.5 City resolution and response scope

Ride/booking requests may include a catalog-selected city identifier, but the
backend verifies it against pickup/service geometry and policy. A mismatch is a
safe validation error, not a fallback to another city. Responses include the
resolved city/service/operator identifiers and relevant immutable version IDs so
clients can display facts without selecting rules.

Cross-city object identifiers return `404` or `403` according to the documented
enumeration policy, never data from another grant. Database filtering is applied
before pagination/counting so totals cannot leak another city's records.

## 59.6 Expansion idempotency and concurrency tests

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

# 60. API Design Principles

## Endpoint delivery checklist

Implement one endpoint family at a time. For every endpoint, define authentication, ownership, validation, idempotency, concurrency behavior, error shape, and the focused test. The client must never declare authoritative business state. If an endpoint needs a new field or transition, update the domain and persistence contract in the same slice or split the contract from implementation explicitly.

The Kotlin gateways are handwritten, so route compatibility is enforced from
their actual Ktor call sites. `infra/scripts/validate_mobile_api_contract.py`
extracts each mobile `client.<method>(api.endpoint("..."))` operation, expands
only the reviewed finite driver transition segment, and separately checks the
live-event WebSocket because WebSocket routes are absent from OpenAPI.
`infra/scripts/validate_web_api_contract.py` applies the same fail-closed rule to
the operations console: it recognizes direct calls and only the private,
method-bound route helpers listed in the validator; derives finite action paths
from rejecting Kotlin `when` selectors and the account-security enum; and
requires every gateway to use `OperationsApiEndpoints`. That builder accepts an
HTTP(S) base ending in exactly one `/api/v1` and clean relative paths, preventing
the former control-plane/payment `/api/v1/api/v1` defect.

Both gates compare every expanded method/path pair with FastAPI's generated
OpenAPI contract. An unparsed call, runtime route variable, unsafe fragment, or
non-fail-closed dynamic segment fails CI rather than being silently omitted.
This proves route and method presence, not request/response schema compatibility,
authorization behavior, or runtime provider availability; focused gateway and
backend tests retain those duties.

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
