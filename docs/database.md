# TaxiMobile — Database Specification

## 1. Purpose

This document defines the logical data model for TaxiMobile.

The primary database will be:

* PostgreSQL
* PostGIS

The database is the authoritative persistent store for important application data.

**Current standing (2026-09-07):** the Alembic chain contains 51 ordered
migrations through `20260908_0052`; the current workspace has exercised upgrade,
targeted downgrade/re-upgrade, and isolated PostGIS integration lifecycles. This
does not establish managed-provider backup, point-in-time recovery, production
capacity, or backup-expiry compliance. See [`gaps.md`](gaps.md).

The schema should prioritize:

* Data integrity.
* Referential integrity.
* Privacy.
* Auditability.
* Geographic queries.
* Historical accuracy.
* Maintainability.
* Future extensibility.

The database schema should represent the cooperative taxi platform rather than simply reproducing a conventional ride-hailing platform.

---

# 2. Database Principles

## 2.1 Database as source of truth

Important persistent business state must be stored in PostgreSQL.

Examples include:

* Users.
* Drivers.
* Vehicles.
* Rides.
* Payments.
* Cooperative memberships.
* Verification records.

Temporary caches must not become the authoritative source of important business information.

---

## 2.2 Referential integrity

Relationships between records should use database constraints where appropriate.

For example:

```text
Ride.passenger_id
        │
        ▼
User.id
```

The database should prevent references to nonexistent records.

---

## 2.3 UUID identifiers

Application entities should preferably use UUIDs rather than sequential public IDs.

This reduces accidental exposure of record counts and makes distributed systems easier to support later.

UUIDs should be generated securely.

---

## 2.4 Timestamps

Important records should use timezone-aware timestamps.

At minimum, important entities should track:

* `created_at`
* `updated_at`

Historical events should additionally track their event time.

The backend should use UTC internally.

User interfaces may convert timestamps into local time.

---

# 3. Core Entities

The initial logical data model consists of:

```text
User
 │
 ├── Driver
 │      │
 │      ├── Driver Credentials
 │      ├── Vehicle
 │      └── Cooperative Membership
 │
 └── Passenger

Ride
 │
 ├── Passenger
 ├── Driver
 ├── Vehicle
 ├── Pickup Location
 ├── Destination
 ├── Ride Events
 └── Payment

Cooperative
 │
 └── Memberships
```

Additional entities support:

* Authentication.
* Notifications.
* Ratings.
* Documents.
* Support.
* Audit logs.

## 3.1 National expansion target entities

The national model is additive. Its Phase 12 through 14 foundation is implemented by
migrations `20260824_0033`, `20260824_0034`, `20260824_0035`, and
`20260824_0036` without
rewriting existing ride amounts or financial history. The first two migrations
add market/operator/city, operator assignment, service-area/configuration/
readiness, scoped grant, operations-session, and scoped-audit records and
backfill the known Casablanca control-plane scope deterministically. Migration
`0035` adds versioned driver requirements, typed answers and evidence, protected
document metadata, append-only decisions, city/service authorizations, online
city/service state, and its compatibility requirement/application records.
Migration `0036` adds scoped tariff lifecycle fields, versioned operator-fee and
scheduling-surcharge policies, configuration references, immutable ride financial
snapshots, and exact driver-earning components. Migrations `0037`, `0038`, and
`0039` then deliver fixed routes, scheduled bookings, and privacy-bounded
operational analytics. Migration `20260831_0044` delivers payment recipients and
capability versions, `20260831_0045` completes protected driver-document
retention evidence, `20260902_0046` adds mobile account-recovery code digests,
`20260903_0047` adds closed-code active-ride coordination messages, and
`20260903_0048` enforces one active live ride per driver. The
separate operator settlement/payout ledger below remains target
schema and is not implemented.

```text
markets
├── id
├── code
├── name
├── default_currency
├── status
└── timestamps

operators
├── id
├── market_id
├── cooperative_id      # nullable; references existing cooperative when applicable
├── name
├── operator_type
├── status
└── timestamps

cities
├── id
├── market_id
├── code / slug
├── localized_name
├── timezone
├── presentation_centroid
├── lifecycle_status
├── active_configuration_version_id
└── timestamps

operator_city_assignments
├── id
├── operator_id
├── city_id
├── service_type
├── effective_from / effective_until
├── status
└── audit timestamps
```

At most one active operator assignment may be authoritative for a given
`(city, service_type, effective_time)` in the initial expansion. City lifecycle
and active configuration pointers change only through audited backend commands.
When an operator is the existing cooperative, `cooperative_id` references that
record rather than duplicating membership/governance data. Non-cooperative
operator identity never grants cooperative membership implicitly.

Migration `20260831_0044` delivers immutable recipient accounts and reviewed
payment-capability versions for national rollout:

```text
payment_recipient_accounts
├── id
├── city_id
├── operator_id
├── label
├── recipient_name
├── bank_account                 # nullable
├── wallet_id                    # nullable
├── status                       # DRAFT / VERIFIED / RETIRED
├── optimistic_version
├── created_by / verified_by / retired_by
└── verified_at / retired_at / timestamps

payment_capability_versions
├── id
├── city_id
├── operator_id
├── service_type
├── version
├── status                       # DRAFT / IN_REVIEW / APPROVED / ACTIVE / REPLACED
├── cash_enabled                 # constrained true
├── manual_transfer_enabled
├── recipient_account_id         # required exactly when transfer is enabled
├── effective_from / effective_until
├── optimistic_version
├── created/submitted/approved/activated actors and times
└── audit fields
```

Recipient labels are unique within a city/operator scope. Verification freezes
the recipient identity and destination; retirement is blocked while an active
capability references it. A capability must include cash. Manual transfer points
to a verified recipient account with the same city and operator. Capability
activation verifies assignment, operator state, effective time, scope, and recent
MFA. Passenger visibility additionally requires the exact capability foreign key
in the active city-configuration service. Future provider credentials are secret-
manager references, never columns in these tables. Rides and payments retain the
selected capability/recipient IDs and immutable display instructions.

Service boundaries, driver requirements, and coherent activation bundles are
first-class versions rather than mutable columns or an unvalidated JSON object:

```text
city_service_area_versions
├── id
├── city_id
├── version
├── boundary                 # geography(MultiPolygon, 4326)
├── status
├── effective_from / effective_until
└── audit timestamps

driver_requirement_versions
├── id
├── city_id
├── version
├── status
├── effective_from / effective_until
└── audit fields

driver_requirement_items
├── id
├── requirement_version_id
├── requirement_code
├── evidence_type
├── required
├── validity_rule_code
├── display_order
└── localized_copy_key

city_configuration_versions
├── id
├── city_id
├── version
├── status                   # DRAFT / IN_REVIEW / APPROVED / ACTIVE / REPLACED
├── service_area_version_id
├── driver_requirement_version_id
├── localization_bundle_version_id
├── optimistic_version
├── submitted_by / submitted_at
├── approved_by / approved_at
└── activated_by / activated_at

city_configuration_services
├── configuration_version_id
├── service_type
├── operator_city_assignment_id
├── matching_policy_version_id
├── tariff_version_id
├── operator_fee_policy_version_id
├── scheduling_policy_version_id       # nullable when scheduling is disabled
├── payment_capability_version_id
└── enabled

city_configuration_routes
├── configuration_version_id
├── fixed_route_version_id
├── immediate_booking_enabled
└── scheduled_booking_enabled

city_readiness_checks
├── id
├── configuration_version_id
├── gate_code
├── status
├── non_secret_evidence_reference
├── decided_by / decided_at
└── timestamps
```

The Phase 12 table initially contains the city, service-area reference, status,
optimistic version, and review/activation audit fields. Phase 13 adds the owned
`driver_requirement_version_id` reference and deterministically backfills the
legacy Casablanca bundle. Phase 14 adds owned operator-fee and optional
scheduling-policy references to each configuration service and backfills the
legacy service with an explicit zero-fee policy. References to localization and
matching are added only with their owning-domain migrations; nullable or fake IDs
are not created merely to imitate the final bundle early. Migration
`20260831_0044` adds the payment-capability foreign key. The current
`city_configuration_services` slice owns service type, operator assignment,
tariff, operator-fee policy, optional scheduling policy, optional payment
capability, and enabled state. A non-legacy enabled service cannot be activated
without an exact active/effective capability.

The matching, localization, and payment-capability version tables are delivered
with their owning domain; the foreign keys above cannot point to arbitrary
configuration blobs. Support, safety, retention, legal, map/routing, and
localization readiness are represented by allowlisted gate codes and bounded
evidence references, never copied documents, secrets, or free-form credentials.

Phase 18 uses the existing `city_readiness_checks` rows rather than adding a
parallel rollout checklist. Ten allowlisted configuration/operations gates form
the pre-pilot set. `PILOT_SERVICE_AND_FAIRNESS` extends that set for public
activation, and `POST_LAUNCH_REVIEW` is a recognized post-activation closeout
record. All decisions remain configuration-version scoped: replacing a bundle
does not copy or inherit evidence. Stage constraints are enforced by commands,
while the existing unique configuration/gate row and optimistic configuration
version prevent duplicate or stale decisions. No schema migration is needed for
the additive allowlist and response semantics.

A draft configuration uses optimistic concurrency. Submission freezes its
component references; approval and activation are explicit audited transitions.
Activation validates every referenced version, changes the city's active pointer,
and records the replaced bundle in one transaction. It must not point to draft,
expired, cross-city, overlapping, or otherwise incompatible components.
For an already operating city, activation also verifies the replacement bundle's
pilot-entry or public-activation evidence before changing the active pointer.

Scoped administration uses grants rather than global data access:

```text
administrative_grants
├── id
├── user_id
├── role_template
├── market_id          # nullable according to validated scope type
├── operator_id
├── city_id
├── granted_by
├── granted_at
├── expires_at
└── revoked_at
```

Migration `20260907_0049` adds the durable maker-checker state:

```text
administrative_grant_change_requests
├── id
├── action                    # CREATE | REVOKE
├── status                    # PENDING | APPROVED | REJECTED | CANCELLED
├── requester_user_id
├── decided_by_user_id
├── target_user_id
├── role_template
├── market_id | operator_id | city_id
├── source_grant_id           # required only for REVOKE
├── resulting_grant_id        # required only for approved CREATE
├── reason | decision_reason
├── requested_grant_expires_at
├── requested_at | decided_at
└── optimistic_version
```

Checks enforce exact template/scope and action/source shape, prohibit a
requester from targeting themselves, require complete terminal decision state,
require approve/reject deciders to differ from requester and target, bind
cancellation to the requester, validate requested expiry and positive version,
and preserve grant foreign keys. Partial unique indexes allow only one pending
create for a target/role/exact scope and one pending revoke per source grant.
The resulting grant ID is globally unique. Market-row locking and application
checks add live-authority, target, duplicate, stale-version and two-admin
continuity protection that cannot be expressed as static row constraints.

`operations_sessions` stores a hashed rotating refresh token, refresh-family ID,
optional hashed CSRF token, expiry/revocation timestamps, optional device label,
and the verified MFA time/method. Migration `20260830_0043` adds one encrypted
AES-GCM TOTP credential per operations user, single-use hashed recovery-code
rows, and short-lived password challenge rows with bounded attempts. Accepted
TOTP counters are persisted under row lock to reject replay. Raw seeds, recovery
codes, refresh tokens, and CSRF tokens are never stored.

Deleting/replacing an MFA credential cascades its old recovery rows. The trusted-
terminal replacement transaction creates the confirmed new credential, audits
the event, and revokes every live operations session for that user.

Database shape complements, but never replaces, backend permission checks.
Constraints require a valid scope for each template and prevent duplicate
unrevoked grants. Grant requests and resulting mutations remain append/audit
visible; no terminal request is rewritten into another outcome.

Driver city participation is separate from driver identity:

The application structures in this subsection are delivered by `20260824_0035`.
Migration `20260831_0045` completes the protected document retention evidence.
Document evidence is created only after the encrypted store and malware scanner
accept the bytes; disabled or unavailable dependencies fail closed.

```text
driver_city_applications
├── id
├── driver_id
├── city_id
├── requirement_version_id
├── status
├── submitted_at / reviewed_at
├── latest_decision_id          # nullable projection to append-only decision
└── timestamps

driver_application_evidence
├── id
├── application_id
├── requirement_item_id
├── credential_id             # nullable reusable verified credential
├── document_id               # nullable protected application document
├── status
└── timestamps

driver_application_answers
├── id
├── application_id
├── requirement_item_id
├── answer_type
├── boolean_value / date_value / bounded_text_value
└── timestamps

driver_application_documents
├── id
├── application_id
├── requirement_item_id
├── opaque_storage_key
├── media_type / byte_size / sha256
├── malware_scan_status
├── uploaded_at / deleted_at
└── retention_deadline

driver_document_retention_actions
├── id
├── original_document_id          # unique, no FK after hard deletion
├── application_id / city_id
├── reason                        # applicant deletion / replacement / expiry
├── retention_policy_version
├── retention_due_at / executed_at
└── created_at

driver_application_decisions
├── id
├── application_id
├── reviewer_user_id
├── decision
├── bounded_reason_code
├── applicant_safe_message
└── created_at

driver_city_authorizations
├── id
├── driver_id
├── city_id
├── application_id
├── status
├── scheduled_offers_enabled
├── valid_from / valid_until
└── timestamps
```

Mode checks allow exactly one typed answer value and prevent an answer/evidence
from satisfying an item outside the application's snapshotted requirement
version. Applicant edits and document deletion are limited to editable states.
Submission freezes the applicant snapshot; reviewer decisions are append-only.
`WITHDRAWN` is applicant initiated before approval and does not delete the
retention-governed record or confer authorization.
Document replacement/deletion first removes active evidence and sets
`deleted_at`; the retention worker locks due rows, deletes ciphertext
idempotently, removes residual evidence, writes one immutable content-free action,
and only then hard-deletes document metadata. The action intentionally preserves
no filename, hash, object key, document bytes, or reviewer note.

Fixed routes use immutable published versions:

```text
fixed_routes
├── id
├── city_id
├── operator_id
├── code
└── status

fixed_route_versions
├── id
├── fixed_route_id
├── version
├── localized_name
├── effective_from / effective_until
├── publication_status
└── published_by / published_at

fixed_route_directions
├── id
├── route_version_id
├── direction_code
├── start_location
├── finish_location
├── static_geometry
└── flat_fare_policy_version_id

fixed_route_stops
├── id
├── direction_id
├── sequence
├── localized_name
└── location
```

Outbound and inbound are different direction rows. Sequence uniqueness and
valid geometry are database-tested. Historical bookings reference the direction
version, never the mutable route identity alone.

`flat_fare_policy_version_id` is nullable only while route geometry is in
`DRAFT`, allowing geometry review and financial review to begin in either order.
`pricing_rules.fixed_route_direction_id` is the reciprocal unique foreign key.
Before route review, both fields must reference each other and match the exact
city/operator/FIXED_ROUTE/IMMEDIATE scope. An active fare cannot be unbound, and
a published route direction cannot reference a non-active or time-incomplete
fare. The active pricing exclusion scope includes the direction ID, so different
directions in one city can retain independent active fares without overlap.

Scheduled service uses separate records:

```text
scheduled_bookings
├── id
├── passenger_id
├── city_id / operator_id
├── service_type
├── fixed_route_direction_id   # nullable
├── scheduled_for
├── status
├── quote and policy version references
├── current_commitment_id       # nullable
├── live_ride_id               # nullable until handoff
└── lifecycle timestamps

scheduled_booking_offers
├── id
├── booking_id
├── driver_id
├── offered_at / expires_at / responded_at
├── response
└── conflict-policy snapshot

scheduled_booking_commitments
├── id
├── booking_id                 # unique active commitment per booking
├── offer_id
├── driver_id
├── protected_window           # tstzrange including configured buffers
├── status
├── committed_at
└── released_at / release_reason

scheduled_booking_events
├── id
├── booking_id
├── event_type
├── actor_user_id
├── previous_status / new_status
├── controlled_metadata
└── created_at
```

Constraints prevent a booking from referencing a route in another city, more
than one accepted commitment, or more than one live ride. Driver commitment
conflicts use a transaction-safe exclusion/locking strategy over active
`protected_window` ranges plus migrated-database concurrency tests. The booking's
current pointer and commitment row change atomically; a cancelled/released row is
retained for audit rather than overwritten.

Scheduling mutation lock order starts with `scheduled_bookings`, followed by the
relevant offer/commitment and driver rows. `scheduled_bookings/locking.py` reloads
the booking with `FOR UPDATE` and `populate_existing`; accepting/declining an
offer must resolve its booking ID before locking the offer. Driver command locks
also refresh cached state. Five real two-session tests observe
`pg_blocking_pids` before releasing the first transaction and verify durable
duplicate-handoff, cancellation and offline outcomes. Five additional commitment
tests use observed PostgreSQL waits to cover two-driver acceptance, buffered
overlap, adjacent half-open windows, cancellation releasing a window only after
commit, and a direct concurrent insert without application locks. The existing
`ex_scheduled_commitments_driver_window` exclusion constraint rejects that bypass.
No constraint or migration was changed for this evidence. Application error
mapping recognizes only SQLSTATE `23P01` for this exact constraint; foreign-key,
unique, check and unknown integrity faults remain internal errors and roll back.
This is application
transaction hardening, not a schema migration or proof of every domain's lock
order; multi-instance HTTP/load and administrative-revocation races remain open.

Cross-domain live/scheduled exclusion is application-enforced because a
PostgreSQL exclusion constraint cannot directly span `rides` and
`scheduled_booking_commitments`. Both acceptance paths serialize on the driver
profile. Immediate candidate and acceptance queries require no active commitment
whose half-open `protected_window @> server_time`; scheduled acceptance rejects
an active live ride when its proposed range contains server time. Matching
re-queries commitment state after locking its candidate and uses `SKIP LOCKED`
while scheduling owns that driver. A direct database writer that bypasses these
services is not supported authority. The separate unique live-ride index and
scheduled range exclusion remain database backstops within their own tables.

Global account containment uses another cross-domain application lock contract.
New assignment paths first lock their normal ride/booking and driver rows, then
take `FOR SHARE` on `users`; both scoped operations and compatibility suspension
take `FOR UPDATE` on that user row and refresh cached ORM state. Candidate and
scheduled-offer discovery also require `users.status = ACTIVE`, but the locked
commit-point read is authoritative. This creates a deterministic winner without
copying suspension into `driver_profiles` or deleting an assignment that committed
first. Six migrated PostgreSQL cases cover suspended discovery/acceptance and
both observed-wait orders for live acceptance and scheduled handoff. Credential,
vehicle, authorization/configuration, separate-process and failover races remain
distinct tests rather than inferred from this user-row lock.

Location ingestion locks and refreshes the driver row before appending an
observation. Scheduled handoff acquires that same row before selecting the
latest observation. Two observed-wait PostGIS cases prove the ordering: a new
outside-area location committed first prevents direct handoff; handoff committed
first retains its accepted ride when the subsequent location is appended.
The observation order is `observed_at DESC, id DESC` for handoff readiness;
the location-write guard rejects non-increasing timestamps. This contract
assumes the supported write path acquires the driver lock and does not establish
serialization against service-area configuration changes.

City-authorization lifecycle commands use the existing application version as
their optimistic token and append a scoped `audit_logs` event with authorization
ID, application ID, old/new status, reason and resulting application version.
They lock application -> driver -> authorization and refresh ORM state after
waits. Approval now takes the driver lock before its active-authorization query;
reinstatement checks competing active authority under that same lock. Two
observed-wait races prove that approval and reinstatement cannot both activate
the same driver's city permission through supported commands. No new migration
is required. This is an application lock invariant; direct database writes are
not a supported authorization workflow.

Operator compensation and scheduling use independent versioned policies:

Migration `20260824_0036` delivers `operator_fee_policies` and the Phase 14
surcharge/allocation subset of `scheduling_policies`. Migration
`20260829_0038` expands those rows with lead time, booking horizon, offer and
handoff windows, protected/conflict buffers, cancellation/refund behavior, and
fallback authority, then adds the scheduled booking/offer/commitment/event and
driver city-preference tables. Existing Phase 14 policy IDs remain stable.

```text
operator_fee_policies
├── id
├── city_id / operator_id / service_type
├── calculation_mode       # percentage or flat
├── funding_mode           # driver deduction or passenger surcharge
├── percentage_rate
├── flat_amount / currency
├── eligible_base_code
├── rounding_rule / minimum_driver_net
├── effective dates / status / version
└── audit fields

scheduling_policies
├── id
├── city_id / operator_id / service_type
├── lead time / horizon / offer and handoff windows
├── conflict and cancellation configuration
├── surcharge amount / currency / allocation
├── effective dates / status / version
└── audit fields

operator_allocations
├── id
├── operator_id / city_id
├── ride_id / payment_id / fare_record_id
├── operator_fee_policy_version_id
├── funding_mode
├── amount / currency
├── status
└── created_at / settled_at
```

Mode-specific check constraints prohibit a percentage and flat amount from
being active simultaneously. `ride_financial_snapshots` stores the selected
tariff/fee/scheduling IDs, modes, exact transport/surcharge/fee/passenger-total/
driver-gross/driver-deduction/driver-net/operator-allocation amounts, currency,
and immutable policy snapshot before dispatch. Database checks reconcile those
amounts and enforce immediate-versus-scheduled consistency. Phase 14 snapshots
the same components into fare records and driver earnings; Phase 16 copies them
into each scheduled booking before any offer exists and links at most one live
ride at handoff. A separate operator settlement ledger remains a later phase.

Typed domain events and aggregate fact tables include city, operator, service,
booking, route-direction, policy-version, time-bucket, and controlled outcome
dimensions. They must not copy arbitrary API bodies, credential documents,
support text, contact identifiers, payment credentials, or exact long-term
movement history.

Migration `20260829_0039` implements that boundary without making analytics a
second source of truth:

```text
operational_supply_snapshots_hourly
├── city_id / operator_id / service_type
├── zone_code                     # constrained to CITY_WIDE in v1
├── bucket_start / observed_at
├── available_driver_count
├── eligible_driver_count
└── retention_until

operational_domain_events_v1      # allowlisted SQL projection view
operational_metric_facts_hourly_v1 # refreshable materialized aggregate view
```

The event projection derives typed ride, offer, scheduling, onboarding, settled-
payment, refund, support-category, and safety-category events from normalized
tables. It contains no account/driver/passenger ID, coordinate, note, document,
contact, provider reference, credential, or arbitrary JSON column. The
materialized view adds settled financial component facts, matching-fairness
averages, and driver assignment distribution (count, average, min/max, and Gini)
without retaining driver identity. A transaction-scoped advisory lock serializes
refresh, snapshots eligible/available supply at city-wide/hour granularity,
deletes expired snapshots, and rebuilds the materialized facts from authoritative
source records. That full recomputation is the v1 late-event and reconciliation
policy until 730-day retention; no dashboard row is business authority.

Migrations `20260830_0040` and `20260830_0041` complete the first city-scoped
support/safety operations slice. `0040` adds immutable, non-null `city_id`
foreign keys to support tickets and safety reports, backfilled only through
their authoritative ride/city relationship, plus city-aware queue indexes.
`0041` adds durable overdue-delivery state:

```text
case_overdue_alerts
├── id
├── city_id
├── case_kind / case_id
├── response_due_at
├── severity
├── status
├── attempt_count / next_attempt_at
├── last_attempt_at / delivered_at / acknowledged_at
├── acknowledged_by_user_id
└── created_at / updated_at
```

A unique `(case_kind, case_id, response_due_at)` key prevents duplicate alerts
for the same deadline. The case remains authoritative; pager delivery and alert
acknowledgement cannot change case status, assignment, payment, or eligibility.

---

# 4. User

The `users` table represents an account capable of authenticating with the system.

Conceptual fields:

```text
users
├── id
├── phone_number
├── email
├── password_hash
├── status
├── created_at
├── updated_at
└── last_login_at
```

Potential account statuses:

```text
ACTIVE
SUSPENDED
DEACTIVATED
```

The exact authentication fields may change depending on the authentication architecture.

Passwords must never be stored directly.

---

# 5. User Roles

Roles should not be treated simply as a single hard-coded field if users may have multiple roles.

Possible roles include:

```text
PASSENGER
DRIVER
COOPERATIVE_MEMBER
ADMIN
```

A user may potentially have more than one role.

A separate role relationship may therefore be appropriate.

Conceptually:

```text
user_roles
├── user_id
└── role
```

Authorization remains a backend responsibility.

National staff authority is not added as an unscoped role enum. The target
`administrative_grants` relationship supplies a role template plus validated
market/operator/city scope as described in Section 3.1.

---

# 6. Passenger Profile

Passenger-specific information should be separated from the base user account where practical.

Conceptually:

```text
passenger_profiles
├── id
├── user_id
├── display_name
├── created_at
└── updated_at
```

Additional passenger information should only be stored when required.

---

# 7. Driver Profile

A driver profile represents a user participating as a taxi driver.

Conceptual fields:

```text
driver_profiles
├── id
├── user_id
├── display_name
├── profile_photo
├── verification_status
├── account_status
├── availability_status
├── created_at
└── updated_at
```

Driver verification information should not all be stored directly in this table.

Separate verification records should be used.

The implemented profile also stores `active_vehicle_id` and nullable
`available_since`. The latter records the beginning of the driver's current
uninterrupted waiting period. Going online starts it; a declined or expired
offer preserves it so declining is not a dispatch penalty. Acceptance, going
offline, suspension, and ride completion clear it. Returning to availability
after an assigned-ride cancellation starts a new waiting period.

---

# 8. Driver Verification

Driver verification should be represented separately.

Conceptual structure:

```text
driver_verifications
├── id
├── driver_id
├── status
├── submitted_at
├── reviewed_at
├── reviewed_by
├── rejection_reason
├── created_at
└── updated_at
```

This allows the system to maintain a history of verification attempts.

A driver may therefore have multiple historical verification records.

---

# 9. Driver Credentials

Professional credentials should be represented separately.

Conceptual structure:

```text
driver_credentials
├── id
├── driver_id
├── credential_type
├── credential_number
├── issued_at
├── expires_at
├── verification_status
├── created_at
└── updated_at
```

Examples:

```text
DRIVER_LICENSE
TAXI_AUTHORIZATION
PROFESSIONAL_LICENSE
INSURANCE
```

The exact credential types depend on applicable regulations.

Migration `20260813_0028` implements the privacy-minimized portion needed by the
self-read API: driver ownership, configurable credential type, verification
status, issue/expiry timestamps, and audit timestamps. Raw credential numbers
and document references are deliberately absent until protected ingestion,
encryption, retention, and administrator-access policy are approved. This avoids
creating an insecure document store merely to fill a conceptual column list.
Migration `20260813_0029` adds the optional expiry value for which a warning was
last emitted. Storing the warned expiry—not a simple boolean—makes processing
idempotent across replicas while allowing a renewed date to receive a new
warning.

---

# 10. Credential Documents

Sensitive documents should not be embedded directly inside ordinary driver records.

Conceptually:

```text
credential_documents
├── id
├── credential_id
├── storage_reference
├── document_type
├── uploaded_at
├── verified_at
└── retention_until
```

The database should store a secure reference to the document rather than unnecessarily storing the binary document itself.

---

# 11. Vehicle

A vehicle belongs to a driver but should exist independently from the driver account.

Conceptual structure:

```text
vehicles
├── id
├── driver_id
├── make
├── model
├── year
├── color
├── registration_number
├── taxi_identifier
├── passenger_capacity
├── status
├── verification_status
├── created_at
└── updated_at
```

A driver may have multiple vehicles over time.

---

# 12. Vehicle Documents

Vehicle-related documentation should be stored separately.

Examples include:

* Registration.
* Insurance.
* Inspection.
* Taxi authorization.

Conceptually:

```text
vehicle_documents
├── id
├── vehicle_id
├── document_type
├── storage_reference
├── issued_at
├── expires_at
├── verification_status
└── created_at
```

---

# 13. Cooperative

The system should represent the cooperative separately from individual members.

Conceptual structure:

```text
cooperatives
├── id
├── name
├── legal_identifier
├── status
├── created_at
└── updated_at
```

The first deployment may use a single cooperative.

The schema should nevertheless avoid making that assumption impossible to change later.

---

# 14. Cooperative Membership

Membership is a relationship between a driver/user and a cooperative.

Conceptual structure:

```text
cooperative_memberships
├── id
├── cooperative_id
├── user_id
├── membership_status
├── joined_at
├── ended_at
├── membership_number
├── created_at
└── updated_at
```

Possible statuses:

```text
PENDING
ACTIVE
SUSPENDED
ENDED
```

Membership should not automatically be inferred from driver status.

Migration `20260813_0027` implements `cooperatives` and
`cooperative_memberships` with separate status enums, user/cooperative foreign
keys, unique membership identity within a cooperative, indexed ownership and
status reads, and chronological joined/ended date validation. The schema permits
one user to belong to different cooperatives but only one record for each
user/cooperative pair. Governance and contribution tables remain deferred.

---

# 15. Membership Contributions

If the cooperative eventually uses membership contributions, they should be represented independently.

Conceptually:

```text
membership_contributions
├── id
├── membership_id
├── amount
├── currency
├── status
├── payment_reference
├── created_at
└── completed_at
```

The exact financial model remains undecided.

---

# 16. Ride

The `rides` table is one of the most important tables in the system.

Conceptual structure:

```text
rides
├── id
├── passenger_id
├── driver_id
├── vehicle_id
├── city_id
├── operator_id
├── service_type
├── fixed_route_direction_version_id
├── scheduled_booking_id
├── status
├── pickup_location_id
├── destination_location_id
├── requested_at
├── accepted_at
├── started_at
├── completed_at
├── cancelled_at
├── cancellation_reason
├── fare_amount
├── currency
├── payment_method
├── transfer_recipient_name
├── transfer_bank_account
├── transfer_wallet_id
├── created_at
└── updated_at
```

`driver_id` and `vehicle_id` may be null before a driver accepts the ride.

The national fields are planned migration additions. `fixed_route_direction_version_id`
and `scheduled_booking_id` are nullable only for service types that do not use
them. City/operator values are backend-derived and immutable once requested;
foreign keys and service-specific checks prevent cross-city route or policy
references.

When an offer is accepted, the backend writes both `driver_id` and the driver's
currently selected, verified `vehicle_id` in the same locked transaction. It
also snapshots the limited passenger-facing driver name and vehicle make,
model, color, and taxi identifier onto the ride. The ID preserves relational
integrity; the snapshot preserves historical passenger identity even if profile
or vehicle records change later.

`payment_method` is selected only from the backend-advertised capability list.
For `MANUAL_TRANSFER`, recipient name and the configured bank account and/or
M-Wallet identifier are snapshotted when the ride is created. They are nullable
for cash and legacy rows. A current deployment setting must never be joined onto
a historical receipt as though it had been the original destination.

---

# 17. Ride Locations

Locations should be represented using PostGIS geographic types.

A reusable location table may contain:

```text
locations
├── id
├── point
├── address
├── place_identifier
├── created_at
└── updated_at
```

The `point` field should use an appropriate PostGIS geographic type.

For example:

```text
POINT(latitude/longitude)
```

The exact coordinate reference system must be defined during implementation.

---

# 18. Ride Location Snapshots

For important ride events, the system may need to preserve the location at that moment.

For example:

* Pickup arrival.
* Ride start.
* Ride completion.

These should not depend solely on the driver's current live location.

Conceptually:

```text
ride_location_snapshots
├── id
├── ride_id
├── location_type
├── point
├── recorded_at
└── accuracy
```

Possible types:

```text
PICKUP
ARRIVAL
START
COMPLETION
```

---

# 19. Driver Location

Current driver location is different from permanent ride locations.

Conceptually:

```text
driver_locations
├── driver_id
├── point
├── accuracy
├── heading
├── speed
└── recorded_at
```

This data may be updated frequently.

It should not necessarily be treated as a permanent historical table.

A separate strategy may be used for historical location retention.

---

# 20. Ride Events

Important ride state changes should be recorded separately.

Conceptual structure:

```text
ride_events
├── id
├── ride_id
├── event_type
├── actor_user_id
├── previous_status
├── new_status
├── metadata
└── created_at
```

Examples:

```text
RIDE_CREATED
MATCHING_STARTED
DRIVER_OFFERED
DRIVER_DECLINED
DRIVER_ACCEPTED
DRIVER_ARRIVED
RIDE_STARTED
DESTINATION_CHANGED
RIDE_COMPLETED
PASSENGER_CANCELLED
DRIVER_CANCELLED
SYSTEM_CANCELLED
```

This provides an audit trail of the ride lifecycle.

---

## 20.1 Ride Coordination Messages

Migration `20260903_0047` adds a narrow durable record for assigned-ride
coordination:

```text
ride_coordination_messages
├── id
├── ride_id
├── sender_user_id
├── code
└── created_at
```

`ride_id` references `rides` with cascade deletion; `sender_user_id` references
`users` with restricted deletion so the sender cannot disappear while the
message is retained. `code` is constrained to the six approved passenger/driver
signals. There is intentionally no free-text body, recipient field, phone number,
attachment, arbitrary metadata, edit timestamp, or delivery-provider payload.

An index on `(ride_id, created_at)` supports the latest authorized active-ride
read. An index on `(sender_user_id, ride_id)` supports the absolute per-participant
ride cap. The application enforces role ownership, allowed ride state, rate limit,
idempotency, and the 100-message sender/ride cap under the ride transaction lock.
The other participant's persistent `notifications` row and minimized outbox event
are separate records so notification delivery does not become message authority.

Only the latest signal is exposed by the active detailed ride API; this table is
not a participant transcript surface. A lawful retention period, erasure timing,
legal-hold interaction, and managed-backup expiry must be approved before real-user
deployment; source delivery alone does not settle those policies.

---

# 21. Ride Offers

Ride offers should be stored separately from the ride itself.

Conceptual structure:

```text
ride_offers
├── id
├── ride_id
├── driver_id
├── offered_at
├── expires_at
├── responded_at
├── response
└── created_at
```

Possible responses:

```text
PENDING
ACCEPTED
DECLINED
EXPIRED
CANCELLED
```

This allows the system to understand which drivers were offered a ride without modifying the ride itself.

The implemented offer also snapshots
`estimated_pickup_distance_meters`, `estimated_pickup_time_seconds`,
`idle_seconds_at_offer`, `recent_assignment_count`, the normalized proximity,
idle, fairness, and final ranking scores, and `matching_algorithm_version`.
These are operational dispatch evidence, not fare or payment records. The
columns remain nullable only for offers created before migration
`20260812_0026`; every new ranked offer supplies them.

---

# 22. Fare Records

Fare calculation should have a persistent historical record.

Conceptual structure:

```text
fare_records
├── id
├── ride_id
├── pricing_rule_version
├── base_amount
├── distance_amount
├── time_amount
├── additional_amount
├── discount_amount
├── total_amount
├── currency
├── calculated_at
└── finalized_at
```

The exact fields depend on the final pricing model.

The important requirement is that historical fares remain explainable.

---

# 23. Pricing Rules

Pricing rules should be versioned.

Conceptually:

```text
pricing_rules
├── id
├── city_id
├── operator_id
├── service_type
├── booking_type
├── fixed_route_direction_id   # nullable; unique when present
├── name
├── version
├── model / fixed_amount / currency
├── effective_from
├── effective_until
├── status
├── optimistic_version
├── created/submitted/activated actor and time
└── created_at / updated_at
```

A ride should reference the applicable pricing-rule version.

Changing pricing rules must not alter historical rides.

City, operator, service, booking type, and optional immutable fixed-route
direction are implemented scope columns. `fixed_route_direction_id` is null for
on-demand rules and uniquely identifies one complete-direction fare for
fixed-route rules. Equal-specificity active date ranges must not overlap;
different direction IDs are intentionally different specificity scopes.
Historical compatibility rows are backfilled to the deterministic Casablanca
city/platform-operator on-demand scope rather than rewritten.

---

# 24. Payments

Payments should be separate from rides.

Conceptual structure:

```text
payments
├── id
├── ride_id
├── payer_id
├── city_id
├── operator_id
├── payment_capability_version_id     # nullable only for historical/legacy rows
├── payment_recipient_account_id      # nullable for cash and legacy rows
├── amount
├── currency
├── method
├── status
├── provider
├── provider_reference
├── created_at
├── completed_at
└── refunded_at
```

Possible statuses:

```text
PENDING
PROCESSING
COMPLETED
FAILED
CANCELLED
DISPUTED
REFUNDED
```

Implemented methods are `CASH` and `MANUAL_TRANSFER`; `CARD` and
`MOBILE_PAYMENT` remain reserved values and are not current passenger
capabilities. For a manual transfer, `provider` is
`MANUAL_RECONCILIATION` and `provider_reference` is the unique backend-issued
`TM-...` reference shown on the historical receipt. It is not an external
settlement identifier.

Passenger assertions are deliberately separate from payments:

```text
manual_transfer_claims
├── id
├── payment_id
├── claimant_user_id
├── payer_reference
├── status                    # SUBMITTED / VERIFIED / REJECTED
├── submitted_at
├── reviewed_at
├── reviewed_by_user_id
├── review_reason
└── settlement_reference
```

At most one `SUBMITTED` claim may exist for one payment. A verified external
`settlement_reference` is globally unique so one statement transaction cannot
complete two payments. Passenger submission creates no earning and changes the
payment only to `PROCESSING`. Authorized verification marks the claim verified,
marks the payment completed, and creates the unique driver earning in one
transaction. Rejection records its reviewer evidence and returns the payment to
`PENDING` without deleting claim history.

Migration `20260820_0030` adds this launch-compatible structure and immutable
ride instructions. Migration `20260831_0044` adds the owning
`payment_recipient_accounts` and `payment_capability_versions` tables, links the
exact capability into city-configuration services, and adds nullable historical
capability/recipient provenance to `rides` and `payments`. It also adds non-null
city/operator provenance to payments and refunds, backfilled through the existing
ride/payment relationships. The environment recipient remains only for the
deterministic legacy city; new cities must use the versioned tables.

Confirmed passenger refunds are separate append-only accounting facts:

```text
payment_refunds
├── id
├── payment_id
├── city_id
├── operator_id
├── amount
├── currency
├── reason                       # closed approved taxonomy
├── settlement_method            # CASH / EXTERNAL_TRANSFER
├── settlement_reference         # globally unique evidence reference
├── operator_note                # restricted; never passenger-visible
├── driver_recovery_amount       # launch value is exactly zero
├── operator_funded_amount       # launch value equals amount
├── authorized_by_user_id
└── refunded_at
```

Migration `20260824_0031` creates the reason and settlement-method enums, positive
amount and launch-funding reconciliation constraints, payment/administrator
foreign keys, and indexes. The application locks the payment before calculating
the cumulative total, so concurrent refunds cannot exceed the immutable payment
amount. A partial refund leaves the payment `COMPLETED`; a complete cumulative
refund sets `REFUNDED` and `payments.refunded_at`. The original payment, fare,
manual-transfer claim, and driver earning remain unchanged.

The exact lifecycle and evidence rules are defined in `payments.md`.

---

# 25. Driver Earnings

Driver earnings should be represented separately from passenger payment.

Conceptually:

```text
driver_earnings
├── id
├── driver_id
├── ride_id
├── gross_amount
├── transport_fare_amount
├── scheduling_surcharge_amount
├── operator_fee_amount
├── operator_allocation_amount
├── fee_amount
├── operator_fee_policy_version_id
├── operator_fee_funding_mode
├── scheduling_surcharge
├── adjustments
├── net_amount
├── currency
├── status
└── created_at
```

This allows the system to clearly distinguish:

```text
Passenger pays
      │
      ▼
Ride revenue
      │
      ├── Driver earnings
      │
      └── Cooperative/platform contribution
```

Provider-specific payout and general-ledger integration remain undecided.

The national accounting model preserves transport fare, scheduling surcharge,
operator allocation, driver gross, adjustments, and driver net as exact separate
components. Migration `20260824_0036` delivers those earning columns and database
checks for `net = gross - fee + adjustment` and funding-mode fee consistency. A
corresponding append-oriented operator settlement/allocation ledger remains a
later accounting slice; until then the immutable ride snapshot and earning row
retain the operator allocation fact without inferring fee mode from an amount.

---

# 26. Ratings

Ratings should be associated with completed rides.

Conceptual structure:

```text
ratings
├── id
├── ride_id
├── reviewer_id
├── reviewed_user_id
├── score
├── comment
├── created_at
└── updated_at
```

The database should enforce appropriate uniqueness rules to prevent duplicate ratings where applicable.

The `ride_ratings` table implements the passenger-to-driver subset: one
row per `(ride_id, reviewer_id)`, a database-enforced score range of 1–5, and
foreign keys for the ride, reviewer, and reviewed driver user. It holds no
safety classification; safety reporting uses its separate restricted table and
access policy.

---

# 27. Safety Reports

Safety reports are separated from ordinary ratings and support tickets.

Conceptual structure:

```text
safety_reports
├── id
├── city_id
├── ride_id
├── reporter_user_id
├── reported_user_id
├── source_support_ticket_id
├── category
├── description
├── status
├── priority
├── assigned_to_user_id
├── response_due_at
├── first_acknowledged_at
├── escalated_at
├── resolution_code
├── latest_public_message
├── latest_public_message_at
├── retention_policy_version
├── retention_until
├── created_at
├── updated_at
├── resolved_at
└── closed_at
```

`safety_report_notes` contains append-only `INTERNAL` or `PARTICIPANT` messages
with author and creation time. A unique nullable source-support-ticket foreign
key prevents duplicate support escalation. Reporter and reported-user foreign
keys are server-derived from ride participation. Queue indexes cover status plus
response deadline, priority, assignee, ride, and reporter. Participant queries
never project description, identities, assignment, deadlines, retention, or
notes. Access to these records is highly restricted.

---

# 28. Support Tickets

Support requests should be represented independently.

Conceptual structure:

```text
support_tickets
├── id
├── city_id
├── user_id
├── ride_id
├── category
├── subject
├── status
├── priority
├── assigned_to_user_id
├── response_due_at
├── first_responded_at
├── resolution_code
├── latest_public_message
├── latest_public_message_at
├── retention_policy_version
├── retention_until
├── created_at
├── updated_at
├── resolved_at
└── closed_at
```

A support ticket may optionally reference a ride.

`support_ticket_notes` stores append-only `INTERNAL` or `PARTICIPANT` messages,
their author, and creation time. The ticket projects only the latest participant
message for owner-facing APIs. Queue indexes cover city, status plus response
deadline, priority, and assignee. Migration `20260824_0032` adds the lifecycle
fields, notes, and separate safety tables after the support/safety operating
policy was defined; migration `20260830_0040` adds their immutable city boundary.
Assignment mutations verify an active user with the corresponding city-scoped
operations grant (or authorized market-level platform administration) in the
same command path.

---

# 29. Notifications

Notifications should be stored when persistent notification history is required.

Conceptual structure:

```text
notifications
├── id
├── user_id
├── type
├── title
├── body
├── data
├── read_at
└── created_at
```

Push delivery itself should not be treated as the authoritative state.

The MVP persists notification history with server-created titles, bodies, and
minimal resource-ID data. It also stores registered Android/iOS Firebase
Installation IDs and transitional legacy FCM tokens per user so the provider
adapter can deliver background alerts. A registration identifier is
not a credential and no provider result is treated as authoritative ride state.

---

## Transactional outbox delivery

Ride-offer and assignment transactions also persist a narrow delivery record:

```text
outbox_events
├── id
├── topic
├── payload                 # identifiers only, never copied private content
├── available_at
├── delivered_at
├── dead_lettered_at        # terminal delivery failure; business event remains valid
├── attempts
├── locked_at
├── locked_by
├── last_error              # fixed operational outcome code only
└── created_at
```

Delivery failures use exponential backoff and stop after the configured positive
attempt limit. At that point `dead_lettered_at` is set and `last_error` contains
only the fixed `DELIVERY_DEAD_LETTERED` outcome; exception text, device tokens,
coordinates, and private payload data are never copied into operational error
state. Dead-lettering affects only the best-effort refresh hint and never reverses
or weakens the committed ride, notification, assignment, fare, or payment fact.
An operator may requeue a specifically identified event only after correcting the
delivery dependency and recording the operational action outside this table.

The worker claims records with a lease, retries transient delivery failures with
bounded backoff, and clears the lease only when it records the outcome. It must
reload current ride and offer records before emitting a non-authoritative hint;
these fields never make a WebSocket or future push delivery part of the ride's
business state.

---

## Shared rate-limit buckets

Staging and production coordinate abuse limits through a compact operational
table rather than storing them in application memory:

```text
rate_limit_buckets
├── key_hash               # SHA-256 digest; never a raw email, IP, or user ID
├── window_started_at
├── expires_at
└── attempts
```

An atomic PostgreSQL upsert resets an expired fixed window or increments its
attempt count. Database statement time is authoritative across API hosts. Expired
buckets are bounded-cleaned by the adapter and contain no business authority or
request content; dropping an expired bucket cannot alter account, ride, fare, or
payment state.

---

# 30. Push Registrations

Mobile push registrations should be stored separately.

Conceptual structure:

```text
device_tokens
├── id
├── user_id
├── session_id             # nullable only for historical pre-binding rows
├── platform
├── registration_kind      # FIREBASE_INSTALLATION_ID or transitional LEGACY_FCM_TOKEN
├── token                  # physical legacy column containing the registration identifier
├── last_seen_at
├── created_at
└── revoked_at
```

A user may have multiple devices.

Each provider registration kind and identifier has a database-enforced single owner across all users. A
registration by a different authenticated account updates that existing row
atomically rather than inserting a second active recipient. The ownership
migration labels existing rows as legacy tokens and retains only the most recently
seen historical row for any registration that was previously duplicated. New
mobile builds upload FIDs. Logout and provider rejection set `revoked_at`;
re-registration clears it.

Every new registration is bound to the authenticated session that most recently
claimed it. The nullable historical foreign key uses `ON DELETE SET NULL`, while
ordinary session revocation keeps session records and marks registrations owned
by that session revoked. A newer session claiming the same installation replaces
`session_id` atomically, so an older session cannot revoke the newer claim.

---

# 31. Authentication Sessions

If session tracking is required, sessions should be represented independently.

Conceptual structure:

```text
auth_sessions
├── id
├── user_id
├── device_identifier
├── created_at
├── expires_at
├── revoked_at
└── last_used_at
```

The exact implementation depends on the authentication mechanism.

The MVP persists only a hash of each refresh token. It also records a
`refresh_family_id` and `refresh_rotated_at`: the family groups a device's
rotation lineage, and the rotation marker lets the backend distinguish reuse of
an old rotated token from an ordinary logout. Detected reuse revokes only the
still-active sessions in that family.

Migration `20260902_0046` adds a separate ordinary-account offline recovery
collection:

```text
account_recovery_codes
├── id
├── user_id                 # cascading owner foreign key
├── code_hash               # unique 64-character domain-separated SHA-256 digest
├── expires_at
└── created_at
```

Raw recovery codes are never stored. The user/expiry index supports bounded
account lookup, expiry must be later than creation, replacement deletes the
previous set, and successful consumption deletes every code in the set while
the user row is locked. Operations MFA recovery rows remain a distinct security
domain and cannot be substituted for these mobile codes.

---

# 32. Audit Logs

Administrative and security-sensitive operations should generate audit records.

Conceptual structure:

```text
audit_logs
├── id
├── actor_user_id
├── action
├── entity_type
├── entity_id
├── metadata
├── ip_address
└── created_at
```

Audit logs should be append-oriented and should not be casually modified.

The initial operational read path is an `ADMIN`-only paginated API with exact
actor, action, resource-type, and resource-ID filters. It orders by creation time
and ID newest first and exposes no update or delete operation. Passenger and
driver sessions cannot read the collection.

## 32.1 Security incidents and immutable timeline

Migration `20260907_0050` adds `security_incidents` and
`security_incident_timeline_entries`. An incident belongs to one market and may
optionally narrow to one city. It stores a server-generated non-personal
reference, severity/category, bounded operational summary, reporting lead,
detection/containment milestones, postmortem deadline and optimistic version.
Database checks enforce the ordered lifecycle timestamp shape.

Timeline rows have a unique positive sequence per incident, controlled event
kind, actor and occurrence/recording timestamps, bounded summary, and optional
same-scope audit or external runbook reference. A PostgreSQL trigger rejects
`UPDATE` and `DELETE`; corrections are appended as new events. Audit entries for
incident commands contain only status/category/severity, sequence, reference
presence and deadline facts, never the incident summary. Secrets, credentials,
raw provider payloads and unnecessary participant identifiers must not be stored
in either table.

Migration `20260907_0051` adds one-time postmortem completion fields: completion
time, completing user and a closed outcome (`CONTROL_CHANGED`,
`FOLLOW_UP_REQUIRED`, or `NO_FURTHER_ACTION`). A database constraint requires all
three fields together, only on a closed incident, and never before its closure.
The completion command appends a referenced `POSTMORTEM_ACTION`; corrections
remain new timeline rows rather than parent-record rewrites. Partial indexes
support overdue open-containment and closed/pending-postmortem discovery without
scanning participant content.

Migration `20260908_0052` adds
`security_incident_responsibility_assignments`. Its responsibility is one of
`SECURITY_RESPONSE_LEAD`, `COMMUNICATIONS_LEAD`, `OPERATIONS_LIAISON`, or
`POSTMORTEM_OWNER`. Each tenure stores the incident, assignee, assigning actor,
approved roster/shift reference and assignment time; a completed tenure also
stores all three release fields together. A partial unique index permits only one
active tenure for each incident/responsibility pair. The reporting lead is
backfilled as the initial response lead, and new incidents create that assignment
in the opening transaction.

Responsibility history is append-visible rather than freely mutable. A database
trigger prohibits deletion, prohibits changes to identity/assignment facts, and
allows an active row to make exactly one all-fields release transition. A released
row is immutable. Reassigning the response lead also updates the incident's
current `lead_user_id`; every assignment increments the incident optimistic
version and appends a `RESPONSIBILITY_CHANGED` timeline fact. Candidate existence,
grant eligibility and current incident state remain API-authoritative checks, so
the database constraint is necessary but not sufficient authorization.

---

# 33. Cooperative Proposals

Future cooperative governance may require:

```text
cooperative_proposals
├── id
├── cooperative_id
├── created_by
├── title
├── description
├── status
├── voting_started_at
├── voting_ended_at
└── created_at
```

---

# 34. Cooperative Votes

Voting records should be separate.

Conceptual structure:

```text
cooperative_votes
├── id
├── proposal_id
├── member_id
├── vote
└── created_at
```

The database should prevent an eligible member from voting more than once on a proposal unless the governance rules explicitly allow changing a vote.

---

# 35. Entity Relationships

The core relationships can be represented as:

```text
User
 │
 ├────────────── Passenger Profile
 │
 ├────────────── Driver Profile
 │                       │
 │                       ├── Credentials
 │                       ├── Vehicles
 │                       └── Cooperative Membership
 │
 └────────────── Roles
```

And:

```text
Passenger
    │
    ▼
   Ride
    │
    ├──────── Driver
    │
    ├──────── Vehicle
    │
    ├──────── Pickup
    │
    ├──────── Destination
    │
    ├──────── Ride Events
    │
    ├──────── Ride Offers
    │
    ├──────── Fare
    │
    ├──────── Payment
    │
    └──────── Ratings
```

National expansion adds:

```text
Market
  └── City ── Operator Assignment ── Operator
       ├── Driver City Applications / Authorizations
       ├── Configuration and Financial Policy Versions
       ├── Fixed Route Versions / Directions / Stops
       └── Scheduled Bookings ── Offers ── Live Ride
```

---

# 36. Geographic Indexing

PostGIS indexes should be used for geographic queries where appropriate.

The database should support queries such as:

```text
Find available drivers
within a radius of a pickup point.
```

National dispatch, booking, route-catalog, and operations queries should lead
with `city_id` (and service/route scope where applicable). Fixed-route geometry
uses spatial indexes only when query evidence requires them; ordinary catalog
reads should prefer immutable version keys. Passenger APIs never query or expose
the online-driver index as a catalog.

Geographic indexes should be evaluated during implementation rather than assuming every geographic field requires an index.

---

# 37. Database Constraints

Important business rules should be enforced at the database level where practical.

Examples include:

* Unique phone numbers.
* Unique email addresses where required.
* Unique vehicle registration identifiers where legally appropriate.
* Valid foreign-key relationships.
* Valid monetary values.
* Valid rating ranges.
* Unique active ride assignment where required.
* One authoritative active operator per city/service/effective time initially.
* No equal-specificity overlapping active tariff, fee, or scheduling policies.
* Fixed-route direction and booking city/operator consistency.
* One accepted driver commitment and one live ride per scheduled booking.
* Mode-valid percentage or flat operator fee fields.
* Valid scoped administrative grants.
* One payment per ride and one driver earning per payment/ride.
* At most one active submitted manual-transfer claim per payment.
* Unique non-null manual-transfer settlement references.
* Historical manual-transfer instructions remain ride snapshots rather than
  references to mutable deployment configuration.

Application validation should complement database constraints rather than replace them.

Migration `20260903_0048` adds `uq_rides_one_active_per_driver`, a partial unique
index on non-null `driver_id` while status is `ACCEPTED`, `DRIVER_EN_ROUTE`,
`DRIVER_ARRIVED` or `IN_PROGRESS`. The rule is global across cities and immediate/
scheduled origins. Matching/unassigned and terminal history rows do not consume
the slot. Application driver locks and eligibility checks remain required; the
index is a final defense against another writer bypassing them.

Upgrade refuses existing duplicate active assignments with a fixed, non-personal
diagnostic and never cancels, deletes or reassigns rides automatically. Resolve
such conflicts through an approved operational investigation before retrying.
The transactional index build takes a write-blocking table lock: schedule a
maintenance window and measure duration against the candidate dataset before a
live upgrade. The Alembic environment now acquires a database-scoped PostgreSQL
transaction advisory lock before version reads or DDL. A concurrent executor
fails immediately with a fixed retry diagnostic rather than waiting indefinitely
or racing schema changes. Commit, rollback and connection loss release the lock.
Generated offline SQL acquires the same lock inside its outer transaction when
executed; generating the SQL itself does not contact a database.

The lock is cooperative: keep the separate production migration job, and do not
bypass Alembic with unguarded manual DDL. The complete chain must remain in one
transaction. Explicit commits, autocommit blocks or per-migration transactions
require a reviewed replacement locking design and release tests; existing source
tests reject the known transaction-breaking APIs. This guard is not a migration
duration/DDL timeout or maintenance-window substitute. Separate migration limits
now default to 5 seconds for each database lock wait and 300 seconds per SQL
statement. `TAXIMOBILE_MIGRATION_LOCK_TIMEOUT_SECONDS` accepts 1–120;
`TAXIMOBILE_MIGRATION_STATEMENT_TIMEOUT_SECONDS` accepts 1–7200 and must exceed
the lock limit. Zero, malformed and out-of-range values fail before connection.
Online execution uses transaction-local settings; generated offline SQL emits
equivalent `SET LOCAL` statements before ownership acquisition and schema work.
Rollback restores prior connection settings. SQLSTATE `55P03` and `57014` receive
fixed online Alembic diagnostics without echoing SQL, parameters or pasted config
values; unknown database failures retain their existing error path.

These are per-wait/per-statement limits, not a connection, idle-session or total
migration-chain deadline. The deployment must still own an outer job deadline,
maintenance window, blocker investigation and bounded retry; do not cancel
unrelated sessions automatically. Execute generated scripts as one transaction
with the SQL client's stop-on-error option enabled. Downgrade removes only the index and does not modify ride rows;
it removes this database safety net and is not permission to run unsafe writers.

---

# 38. Monetary Values

Monetary values should not use floating-point types.

Use an appropriate fixed-precision decimal representation.

Amounts should always be associated with a currency.

Example:

```text
amount = 25.50
currency = MAD
```

The exact database representation will be selected during implementation.

---

# 39. Soft Deletion

Not every entity should be physically deleted immediately.

Some records may require historical retention.

Where appropriate, the system may use:

```text
deleted_at
```

or explicit status fields.

However, soft deletion should not be used indiscriminately.

Sensitive personal information may require actual deletion or anonymization according to applicable privacy requirements.

---

# 40. Data Retention

Different data categories require different retention policies.

Potential categories include:

```text
Account data
Ride data
Payment records
Manual-transfer claims and reconciliation evidence
Driver credentials
Location data
Safety reports
Audit logs
Notifications
Administrative grants
Driver city applications and documents
Scheduled bookings
Operational aggregate facts
```

The launch policy versions are explicit: `support-launch-v1` projects deletion
or approved archival 730 days after case closure, and `safety-launch-v1`
projects it 1,825 days after closure. Open records have no `retention_until`.
Migration `20260830_0042` makes legal hold and verified minimization controlled
operations. `case_legal_holds` references exactly one support ticket or safety
report, duplicates immutable city scope, and records controlled placement,
review, status, and release facts. Partial unique indexes permit at most one
active hold for each case. `case_retention_actions` also references exactly one
case and permits exactly one `PERSONAL_DATA_ERASED` evidence row per case.

Closed due cases are minimized in place only when no active legal hold exists.
Participant and ride foreign keys become nullable solely for this process;
assignment, descriptions/subjects, latest public messages, and child notes are
removed. `retention_action` and `retention_processed_at` identify the remaining
non-identifying shell, while the action row preserves city, policy version,
retention due time, execution time, and erased-note count. This shell preserves
support-to-safety links, audit resource IDs, and category aggregates without
retaining case content or participant identity. An expiry timestamp alone is
not proof that minimization ran; the action row is the database evidence. Other
record classes retain the periods defined in `security.md` or remain policy-
gated.

The database design must support deletion, anonymization, or archival where required.

Aggregate reporting must not become a permanent shadow copy of personal data.
Typed facts use city/zone/route/time dimensions and controlled outcomes; small
cells are suppressed at the presentation/export boundary. Any source event with
an account, booking, or ride reference follows the stricter source retention and
is not exposed as analyst detail.

---

# 41. Database Migrations

All schema changes must be managed through version-controlled database migrations.

Developers and AI coding agents must not manually modify production databases as a normal development practice.

Each migration should:

* Have a unique version.
* Be reversible where practical.
* Be tested.
* Clearly describe the schema change.

---

# 42. Database Access

The backend uses SQLAlchemy 2.x with the asyncpg PostgreSQL driver. Alembic owns version-controlled migrations. SQLAlchemy models and migrations are kept in the backend codebase; schema changes are never applied manually to a shared or production database.

The implementation may use explicit parameterized SQL for PostGIS operations, locking, and other queries where that is clearer or safer than an ORM query. Every such query remains covered by integration tests against PostGIS.

---

# 43. Database Testing

Database behavior should be tested separately from pure application logic.

Tests should verify:

* Constraints.
* Relationships.
* Migrations.
* Geographic queries.
* Ride assignment consistency.
* Live-command ride-first lock ordering, post-wait ORM refresh, and expiry-worker
  `SKIP LOCKED` recovery without duplicate audit/outbox effects.
* Fare persistence.
* Payment relationships.
* Deletion/anonymization behavior.
* Cross-city authorization and foreign-key isolation.
* Coherent city configuration activation.
* Fixed-route version immutability and direction ordering.
* Scheduled-booking commitment/handoff concurrency.
* Operator-fee mode checks and complete financial reconciliation.
* Aggregate facts contain only approved dimensions.
* Staff-grant maker/checker identity separation, stale decisions, duplicate
  pending requests, target changes, and platform-admin continuity.

---

# 44. Performance

Live-ride transaction evidence currently includes seven actual two-session lock
waits, an expiry worker that skips a held ride and processes it once after release,
and rejection of dispatch on three operational states. The tests retain stale ORM
references deliberately and inspect final rows through a fresh connection. They
do not establish whole-system deadlock freedom: administrative mutations,
cross-domain transactions, separate processes and representative contention must
also be exercised before release. No additional database migration accompanies
this application lock-order hardening.

The initial database should prioritize correctness.

Performance optimization should be evidence-driven.

Potential future optimization areas include:

* Geographic indexes.
* Query indexes.
* Connection pooling.
* Read replicas.
* Partitioning.
* Archival tables.

These should not be introduced prematurely.

---

# 45. Backup and Recovery

Production databases must have a backup strategy.

Backups should support recovery from:

* Hardware failure.
* Software failure.
* Accidental deletion.
* Database corruption.
* Security incidents.

Backups must be protected with appropriate access controls.

A backup that cannot be restored should not be considered a reliable backup.

Recovery procedures should eventually be tested.

---

# 46. Initial Minimum Schema

The minimum viable database should include:

```text
users
user_roles

driver_profiles
driver_verifications
driver_credentials

passenger_profiles

vehicles

cooperatives
cooperative_memberships

rides
ride_offers
ride_events

locations
driver_locations

fare_records
payments
driver_earnings

ratings
```

Additional security, notification, support, and governance tables can be introduced as their corresponding features are implemented.

The national expansion then adds the Section 3.1 market/operator/city,
administrative-grant, city-application/authorization, fixed-route, scheduled-
booking, fee-policy, configuration-version, and aggregate-fact tables in the
roadmap sequence. They are not part of the already implemented minimum schema
and must not be created as one unreviewable migration.

---

# 47. Core Database Principles

## Migration delivery rule

Database work is delivered as a migration-backed slice. Identify the owning entity, constraints, retention/security implications, and affected API/domain code before editing. Never rewrite historical rides, fares, payments, or audit events to make a new rule fit. A documentation conflict blocks the schema change until it is resolved.

### Principle 1 — Persistent truth

PostgreSQL is authoritative for persistent business data.

### Principle 2 — Referential integrity

Relationships must remain valid.

### Principle 3 — Historical accuracy

Completed rides and financial records must remain explainable.

### Principle 4 — Geographic capability

Location data must support efficient geographic operations.

### Principle 5 — Privacy

Personal information and location data must be minimized and protected.

### Principle 6 — Financial precision

Money must never rely on floating-point arithmetic.

### Principle 7 — Auditable operations

Important state changes should be traceable.

### Principle 8 — Migration-based development

Schema changes must be version controlled.

### Principle 9 — No premature complexity

The database should scale from a small deployment without prematurely becoming a distributed system.

### Principle 10 — Cooperative ownership

The schema should support the cooperative's ability to understand, control, export, and preserve its own operational data.
