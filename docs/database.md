# TaxiMobile — Database Specification

## 1. Purpose

This document defines the logical data model for TaxiMobile.

The primary database will be:

* PostgreSQL
* PostGIS

The database is the authoritative persistent store for important application data.

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
├── created_at
└── updated_at
```

`driver_id` and `vehicle_id` may be null before a driver accepts the ride.

When an offer is accepted, the backend writes both `driver_id` and the driver's
currently selected, verified `vehicle_id` in the same locked transaction. It
also snapshots the limited passenger-facing driver name and vehicle make,
model, color, and taxi identifier onto the ride. The ID preserves relational
integrity; the snapshot preserves historical passenger identity even if profile
or vehicle records change later.

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
├── cooperative_id
├── name
├── version
├── configuration
├── effective_from
├── effective_until
├── status
└── created_at
```

A ride should reference the applicable pricing-rule version.

Changing pricing rules must not alter historical rides.

---

# 24. Payments

Payments should be separate from rides.

Conceptual structure:

```text
payments
├── id
├── ride_id
├── payer_id
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
AUTHORIZED
COMPLETED
FAILED
REFUNDED
CANCELLED
```

The exact payment lifecycle will be defined in `payments.md`.

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
├── cooperative_fee
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

The exact accounting model remains undecided.

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

The MVP `ride_ratings` table implements the passenger-to-driver subset: one
row per `(ride_id, reviewer_id)`, a database-enforced score range of 1–5, and
foreign keys for the ride, reviewer, and reviewed driver user. It holds no
safety classification; safety reporting remains a separate future table and
access policy.

---

# 27. Safety Reports

Safety reports should be separated from ordinary ratings.

Conceptual structure:

```text
safety_reports
├── id
├── ride_id
├── reporter_id
├── reported_user_id
├── category
├── description
├── status
├── created_at
├── reviewed_at
└── resolved_at
```

Access to these records should be highly restricted.

---

# 28. Support Tickets

Support requests should be represented independently.

Conceptual structure:

```text
support_tickets
├── id
├── user_id
├── ride_id
├── category
├── subject
├── status
├── priority
├── assigned_to
├── created_at
├── updated_at
└── resolved_at
```

A support ticket may optionally reference a ride.

The implemented MVP stores participant-owned support tickets with a controlled
category, subject, description, optional ride reference, and `OPEN` status.
Assignment, priority, and resolution fields remain deferred until cooperative
support operations define the people, permissions, retention, and escalation
rules that would make those fields meaningful.

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

---

# 36. Geographic Indexing

PostGIS indexes should be used for geographic queries where appropriate.

The database should support queries such as:

```text
Find available drivers
within a radius of a pickup point.
```

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

Application validation should complement database constraints rather than replace them.

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
Driver credentials
Location data
Safety reports
Audit logs
Notifications
```

Retention periods will be defined in `security.md`.

The database design must support deletion, anonymization, or archival where required.

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
* Fare persistence.
* Payment relationships.
* Deletion/anonymization behavior.

---

# 44. Performance

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
