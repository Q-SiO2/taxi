# TaxiMobile — Security

## Current standing — 2026-09-03

The source includes backend authorization, scoped grants, operations MFA,
session revocation, rate limits, audit records, protected-document fail-closed
adapters, secure-cookie/CSRF handling, minimized live-event hints, case
retention/legal holds, and negative automated tests. It has not received an
independent threat-model review, penetration test, production secret/TLS/host
assessment, complete dependency/container/SBOM review, privacy impact assessment,
incident drill, or disaster-recovery acceptance. Therefore it must not be
described as production-secure. The repository threat baseline and executable
security test IDs are in [`threat_model.md`](threat_model.md); open deployment
evidence remains in [`gaps.md`](gaps.md).

## Purpose

Define the basic security requirements for TaxiMobile.

Security is especially important because the application handles:

* User accounts
* Driver identities
* Vehicle information
* Location data
* Ride history
* Payments
* Communication between users

## Core Principles

* Never trust the client.
* Validate input on the backend.
* Apply least-privilege access.
* Minimize stored personal information.
* Protect sensitive data in transit.
* Keep security-sensitive operations auditable.

## Authentication

Authentication rules are defined in `auth.md`.

The backend must verify authentication for protected operations.

A mobile application must never be treated as inherently trusted.

Login performs one Argon2 verification for missing, suspended, and active
accounts, using a process-local non-authenticating dummy hash when no credential
exists. Valid older Argon2 encodings are upgraded only after successful
verification. This reduces a practical timing-enumeration signal without
treating timing as the sole account-enumeration defense.

Ordinary mobile account recovery uses a separate offline-code security domain.
The backend returns eight independent 100-bit codes only after current-password
re-authentication, stores domain-separated SHA-256 digests, expires them after
180 days, and replaces the complete old set on rotation. A valid code is consumed
under row locks, deletes the complete set, changes the Argon2 password hash, and
revokes all mobile sessions, operations sessions, and push registrations in one
transaction. Staff identities cannot use this route. Public reset responses are
generic for absent, invalid, expired, replayed, suspended, staff, and successful
requests; identifier-bearing limiter keys are hashed before storage. Mobile UI,
logs, telemetry, screenshots, crash reports, and support tools must never retain
submitted or newly issued codes.

This control does not verify an email address or phone number and cannot recover
an account whose user never saved a code. Contact verification and support-
assisted recovery require an approved proofing policy; they must not be simulated
with an administrator password override.

Access JWT validation is constrained to HS256 plus TaxiMobile's fixed issuer,
mobile audience, access type, subject, session ID, issued-at time, and expiration.
Signature validity alone is insufficient, and every protected request still
checks the server-side session and active user status.

## Authorization

Authentication answers:

```text
Who are you?
```

Authorization answers:

```text
Are you allowed to do this?
```

Examples:

```text
Passenger → access own rides
Driver → access assigned rides
Admin → manage authorized platform resources
```

Users must not be able to access another user's resources by changing an ID in a request.

## Input Validation

All API input must be validated server-side.

Never rely exclusively on:

* Mobile validation
* Client-side forms
* Kotlin types
* UI restrictions

## API Security

Protected endpoints should require authentication.

Sensitive endpoints should additionally enforce authorization and appropriate rate limits.

Operations endpoints receive separate stricter rate limits for authentication,
search, export, document access, configuration activation, application review,
and grant changes. Rate-limit keys do not expose raw identities or become an
authorization decision.

### Client compatibility is not client trust

Staging and production require every v1 HTTP request and live-event connection
to carry one closed TaxiMobile surface, a strict numeric release version and a
positive bounded build. Missing, malformed, unknown and below-minimum clients
fail before authentication or business work. CORS exposes only controlled policy
and version headers, and rejection bodies never reflect an attacker-supplied
version value. The unauthenticated compatibility endpoint is read-only and
command-free.

These headers are trivially forgeable. They must never establish an account,
role, permission, city/operator scope, driver eligibility, payment state, app
integrity, signing identity, rate-limit exemption or audit actor. Existing token,
server-session, account-status, MFA and scoped authorization checks remain
mandatory after compatibility succeeds. Logs and metrics may use only the closed
surface and controlled policy status where explicitly reviewed; raw arbitrary
version/build values must not become unbounded labels.

Minimum-version changes require immutable current/obsolete artifact tests and an
approved rollout record. They are not an emergency substitute for revoking a
compromised session, account, grant, credential or signing key. Raising a minimum
must retain an operational rollback/forward-fix path and must not strand users
without the approved support and store/web distribution channel.

## Secrets

Never commit:

* API keys
* Passwords
* Private keys
* Payment secrets
* Database credentials
* Production tokens

Secrets belong in environment variables or an appropriate secret-management system.

## Location Privacy

Location information is sensitive.

Only collect location data necessary for the application's functionality.

Do not expose unnecessary historical or real-time location information to other users.

The mobile implementation requests only foreground/when-in-use location after a
user selects a current-location action. Once an approved driver explicitly goes
online, it schedules already-authorized one-shot observations only while the app
is foregrounded: 15 seconds in available/offered states and 10 seconds during an
active ride. The automatic path never opens permission UI, and it stops when the
app is backgrounded, offline, paused or disconnected. Neither platform requests
background-location permission or starts continuous OS tracking.
Permission denial, timeout, or disabled location services must not submit a stale
or invented coordinate. A recently observed Android platform location may be used
only as a short timeout fallback and is never retained by the client as location
history. The backend still validates all submitted coordinates, timestamps,
freshness, movement, authorization, and ride state.
Only one foreground lookup may be active per application. Repeated taps are
ignored rather than cancelling/replacing the pending callback, and they never
create an additional location sample or backend submission.
An unavailable automatic observation produces an in-app warning and a 60-second
backoff instead of repeatedly probing the platform. Normal ride/offer commands
take priority over sampling. Server-side freshness and movement checks remain
authoritative; client scheduling cannot make a stale or spoofed point eligible.
The mobile coordinator may retain only the latest backend-accepted driver
coordinate in process memory to render current navigation across authoritative
state refreshes. It clears the coordinate at account boundaries, never persists
it as location history, and never treats it as proof that a driver remains
fresh, available, eligible, or assigned.

An assigned passenger's active-ride read may contain one last-known driver
observation only when it was submitted after that ride's acceptance. The API
continues to authorize the ride by passenger ownership, omits pre-assignment
dispatch history, and returns no driver location after completion, cancellation,
or unmatched termination. The payload carries its observation timestamp so the
client cannot honestly present it as a live stream. No public driver-location
lookup or historical-location endpoint exists.

Address search and reverse lookup are also treated as sensitive location intent.
They require an active mobile session and pass through the backend; mobile never
contacts the geocoder directly. Query text and raw provider payloads are not
persisted, included in request logs, metrics, push, analytics or audit records.
Inputs, output count and output fields are bounded, languages are allowlisted,
and per-account search/reverse limits use the shared hashed-key limiter in hosted
environments. Deployment owns the fixed provider URL, so user input cannot select
an upstream host. Staging/production requires HTTPS and rejects the shared public
Nominatim endpoint.

The active PostGIS city polygon, not provider locality text, determines whether
a result is eligible as pickup. Reverse lookup retains the user's exact selected
coordinate because a closest indexed address may be physically different. A
disabled, failed or empty lookup cannot block map/manual selection or become an
invented address. Saved-place names, local query history, third-party analytics
and personal labels are not part of this source slice. Provider/data-license,
retention, egress and field privacy acceptance remain release gates.

National expansion preserves a stricter pre-assignment boundary: passengers
cannot query online taxi markers, available-driver counts, identities,
candidate rankings, queues, or precise supply heatmaps. Published fixed-route
geometry is immutable service-catalog data and contains no driver observation.
Aggregate supply exists only inside scoped operations reporting with coarse
zones, time buckets, and small-cell suppression.

## Active-ride participant coordination

The coordination endpoint authorizes only the ride passenger and assigned driver
and accepts only the closed code set belonging to that caller's role. Validation
runs while the ride row is locked and permits only `ACCEPTED`,
`DRIVER_EN_ROUTE`, `DRIVER_ARRIVED`, and `IN_PROGRESS`. Required idempotency,
hashed shared rate limiting, and an absolute 100-message participant/ride cap
bound replay and abuse. Unrelated users, candidate drivers, staff roles, and
terminal rides receive no communication access.

The stored row contains only ride ID, sender user ID, closed code, and timestamp.
It contains no free text, phone number, contact identifier, attachment, or
provider payload. The recipient's persistent notification uses the same closed
code; FCM, WebSocket, logs, and delivery telemetry carry only a generic refresh
hint or opaque identifiers. Clients must reload and reauthorize the ride rather
than trusting notification content.

The detailed ride response omits the latest signal after terminal state, and the
worker suppresses terminal or more-than-five-minute-old live/push delivery. These
source controls do not approve the data lifecycle by themselves. Retention,
erasure and backup expiry, real provider/device delivery, accessibility, abuse
escalation, support ownership, and participant understanding that this is not an
emergency service remain release gates.

## Data Minimization

Do not collect personal information merely because it might become useful later.

Every stored personal-data field should have a clear purpose.

City rollout analytics use typed operational events and allowlisted dimensions.
They must not copy arbitrary request bodies, credential/document contents,
support text, contact identifiers, payment credentials, or exact long-term
movement histories into an analytics payload. Analysts receive aggregate facts,
not participant-level exports. Adding a metric requires a purpose, source,
retention period, scope, late-event policy, and accountable owner.

## National operations web security

The public driver portal and protected operations console are separate security
surfaces even if they share a web artifact. Neither connects directly to the
database, object store, routing engine, payment provider, or Firebase.

Before production use, the protected console requires:

* A dedicated administrative authentication audience and mandatory MFA.
* Short-lived access credentials kept out of persistent browser storage; any
  refresh/session cookie must be `Secure`, `HttpOnly`, narrowly scoped, and use
  an appropriate `SameSite` policy.
* CSRF protection for every cookie-authorized mutation in addition to exact
  origin checks; CORS is not CSRF protection.
* A restrictive Content Security Policy, frame denial, MIME protection,
  dependency review, and no unapproved third-party analytics/tag scripts.
* Backend permission and market/operator/city scope checks before filtering,
  pagination, counts, object reads, exports, or mutation.
* Reauthentication or step-up protection for grant changes, city activation,
  financial-policy activation, route publication, and sensitive document reads.
* Append-oriented audit records for authentication, grants, configuration,
  review decisions, exports, document access, and incident actions.
* Bounded exports with explicit purpose; exports never include secrets, raw
  documents, unnecessary exact locations, or data outside the caller's scope.

Browser navigation state, a selected city switcher, hidden controls, and client
claims are untrusted. A national role does not automatically authorize routine
access to all personal data. The existing broad `ADMIN` role is transitional and
must be migrated deliberately to scoped grants.

Current security status: the backend rejects mobile-audience tokens on
operations routes, resolves active grants server-side, filters scope before
counts/pagination, rotates hashed operations refresh tokens, audits control-plane
commands, and supports an exact configured CORS origin. The browser stores no
bearer token in local/session storage and exposes only implemented destinations
allowed by the returned permissions. Migration `20260830_0043` adds encrypted
TOTP, single-use recovery codes, bounded password challenges, replay prevention,
ten-minute recent-MFA step-up, audited enrollment/replacement, and session
revocation. Hosted refresh is a narrow `Secure`/`HttpOnly`/`SameSite=Strict`
cookie bound to a rotating in-memory CSRF token; local/test may explicitly use
the JSON/password-only compatibility path, while production startup rejects it.

The staff-access console uses a durable maker-checker queue with a closed role
list, selector-derived exact scope, target/expiry/source/reason review and typed
confirmation. Staging/production reject direct grant mutation. Request, approve,
reject and cancel commands require recent MFA and idempotency; the server requires
different requester, target and approver identities, optimistic request versions,
live market authority, and transactionally revalidated target/scope/grant state.
Per-market locking serializes competing decisions. Platform-admin removal cannot
leave fewer than two active administrators, and an expiring platform-admin grant
must have two longer-lived successors. Fixed-field request and grant audits retain
both accountable identities. Authoritative roster linkage, recertification,
break-glass ownership, hosted CSP/MFA and human drill evidence remain required
before production use.

This closes the application-level MFA, step-up, refresh-cookie, and CSRF items.
A production release still requires a reviewed restrictive CSP at the web-host
boundary, named access/recovery reviewers, periodic grant review/removal,
security-event routing, and exercised incident evidence. API frame denial,
no-sniff, no-referrer, no-store, and production HSTS headers are already applied;
they do not replace the web artifact's deployment-specific CSP.

## Protected driver-document boundary

Driver application files are not database blobs and never use public object
URLs. The API accepts one bounded multipart file only after authenticating the
applicant and resolving application ownership. It allows PDF, JPEG, and PNG,
requires declared and signature-detected media types to agree, scans the complete
bounded bytes through private ClamAV, and persists only a random opaque key,
media type, size, SHA-256 integrity value, scan state, and lifecycle timestamps.
File content is encrypted with AES-256-GCM before an atomic private-volume write;
the opaque storage key is authenticated as associated data so moved or altered
ciphertext fails integrity validation.

Storage root, an independent base64url 32-byte encryption key, and scanner host
form an all-or-none startup configuration. No key, partial configuration, scanner
timeout, invalid response, malware result, media spoof, oversized body, path
traversal, or ciphertext-integrity failure is treated as success. API and worker
receive the same key and private volume. ClamAV receives neither and exposes no
host port. The key must not be reused for JWT, MFA, database, pager, monitoring,
Firebase, or payment configuration and must be backed up/rotated through the
deployment secret boundary; losing it makes retained ciphertext unrecoverable.

Review reads require the explicit document permission, application city scope,
recent operations MFA, clean scan state, and a bounded reviewer quota. Every
successful read is audited and streamed with an opaque filename, `no-store`, and
`nosniff`; no document content, hash, key, original filename, identity number, or
raw route is logged. Applicant replacement/deletion removes active evidence and
soft-deletes metadata in the business transaction. The fixed retention worker
then performs idempotent physical deletion, hard-deletes metadata, and preserves
only one immutable content-free erasure record. Production promotion requires a
controlled clean/malware/reviewer/deletion drill plus encrypted-volume backup,
key recovery, expiry, and restore evidence.

## Logging

Logs must not contain sensitive information unnecessarily.

Avoid logging:

* Passwords
* Authentication tokens
* Payment credentials
* Private user information
* Full location histories

## Rate Limiting

Rate limits should protect against:

* Brute-force authentication
* Fake ride creation
* API abuse
* Excessive location updates
* Automated account creation

## Fraud and Abuse

The system should eventually detect suspicious behavior such as:

* GPS spoofing
* Fake accounts
* Fake rides
* Repeated cancellation abuse
* Payment fraud
* Automated requests

Detection should not automatically equal punishment.

## Database Security

Database access must be restricted to authorized backend services.

The mobile applications must never connect directly to the production database.

## Transport Security

Production API communication must use HTTPS/TLS.

Android release builds enforce this boundary before packaging: the API origin
and MapLibre style must be explicit HTTPS URLs without credentials, fragments,
or reserved `.invalid` hosts. Cleartext traffic and Android backup are disabled
in the release manifest. A distributable build additionally requires complete
external signing configuration and flavor-aware Firebase configuration; partial
or missing values fail the build. Keystores, signing passwords, Firebase files,
and R8 mappings are release secrets/artifacts and must not be committed. The
repository's CI-only unsigned/providerless switches produce verification
artifacts and must never be used to promote a release.

iOS Release builds likewise reject placeholder/non-HTTPS API or map values,
invalid versions, absent target-matching Firebase configuration, disabled signing,
or a missing Apple development team. Passenger and driver Firebase plists remain
ignored, are checked against the target bundle ID, and only the selected file is
installed into the built application. APNs entitlements are development-only in
Debug and production in Release. The two explicit CI bypass settings permit only
unsigned/providerless simulator verification and must not be used for archives.

## Mobile crash reporting

Firebase Crashlytics is the selected native crash/ANR adapter and Firebase
Analytics is intentionally absent. Collection is disabled in Debug and in
providerless CI artifacts. Distributable Android and iOS Release builds fail
closed unless crash collection is explicitly enabled after the deployment owner
has approved provider terms, retention, access, incident response, and the user
privacy notice.

Crashlytics and FCM are retained because both are available without charge on
Firebase's Spark plan. This is not permission to add Firebase Analytics or a
metered Firebase database, function, storage, hosting, or phone-authentication
dependency. Any new Firebase product requires a separate architecture, privacy,
cost-limit, data-location, and vendor-exit review. PostgreSQL and the TaxiMobile
API remain authoritative; providerless/WebSocket verification remains supported.

TaxiMobile never sets a Crashlytics user ID and must not add custom keys, manual
logs, Analytics breadcrumbs, coordinates, contact identifiers, credentials,
tokens, request/response bodies, ride/payment identifiers, or other business
payloads. Crash reports are limited to SDK/platform metadata and the stack/error
material required to diagnose the failure. Application exceptions must not embed
secrets or private payloads in their messages. Firebase access must be
least-privilege and separated by environment and app role.

Android's release Crashlytics plugin must upload and retain the R8 mapping that
matches the exact artifact. The final iOS build phase must upload the matching
dSYM. Promotion requires a controlled staging crash for each passenger/driver
application, correct project isolation, successful symbolication, and evidence
that production collection contains no forbidden custom data. Test crashes are
never triggered in production.

## Security Updates

Dependencies should be kept reasonably current.

CI separately audits the fully pinned Python runtime and development locks with
PyPA `pip-audit`, including the reviewed Linux supplement on the Linux runner,
and fails on known published vulnerabilities. Neither audit may be conditional
or non-blocking; the CI validator tests removal and bypass mutations. Test-runner
and async-plugin upgrades must retain function-scoped isolation and repeat the
complete migrated-database/concurrency/worker/restore evidence. A clean runtime
audit alone does not establish a clean development or browser toolchain.
Dependabot monitors Python, Gradle, GitHub
Actions, and both Docker manifests weekly. Findings require review rather than
automatic production rollout; a scanner supplements but does not replace source,
authorization, provider, and deployment review.

Workflow permissions default to read-only repository contents. Every referenced
GitHub Action is pinned to a full immutable commit SHA with its release tag kept
as an update hint; Dependabot proposes reviewed SHA updates instead of relying on
mutable action tags. The Gradle wrapper distribution is pinned by SHA-256, and a
dedicated CI job validates every committed `gradle-wrapper.jar` against Gradle's
trusted checksum list before release artifacts can be considered verified.
CI also runs a repository-owned high-confidence credential gate over Git-tracked
source and configuration. It rejects committed Firebase configuration, signing
containers, local environment files, private-key material, service-account JSON,
and well-known live token formats without printing matched values. When run from
a source archive without Git metadata, it scans only documented source roots and
does not read ignored local `.env`, `local.properties`, caches, builds, backups,
or generated environments.

Production container inputs are validated before rendering the deployment:
application images require a full immutable digest; database URLs cannot target
loopback; JWT and monitoring secrets must be long and distinct; public hosts,
browser origins, and trusted proxy ranges cannot use broad wildcards. The API
and worker containers run read-only as the unprivileged image user with all
Linux capabilities dropped and privilege escalation disabled. Their environment
capabilities are separated so the worker never receives the JWT signing secret
and the API never receives Firebase delivery configuration.

## Deployment HTTP boundary

The API uses an explicit host allowlist and optional explicit browser-origin
allowlist. Staging and production reject wildcard hosts and wildcard browser
origins at startup. Native mobile applications do not require CORS; browser
tooling must be added deliberately through `TAXIMOBILE_CORS_ORIGINS`. Ride
creation is rate-limited server-side alongside authentication and location
updates. Development and isolated tests use a process-local adapter. Staging and
production use atomic PostgreSQL-backed fixed-window buckets, so all API instances
consume the same quota. Persistent bucket keys are SHA-256 digests; raw email
addresses, IP addresses, and user IDs are not stored in the rate-limit table.
If the shared decision cannot be made, the protected request fails with a safe
`503` instead of bypassing the limit.

Staging and production host entries are exact DNS/IPv4-style names: wildcard,
scheme-bearing, port-bearing, path-bearing, and malformed values are rejected.
The container readiness request connects to loopback but sends the first reviewed
allowed name in its HTTP `Host` header. It therefore proves database readiness
through the same host-filter middleware as public traffic instead of weakening
that boundary for internal probes.

Configured production browser origins are exact HTTPS origins without wildcard,
credentials, path, query, or fragment. Their preflight contract permits only the
API's reviewed methods and headers, including `DELETE` and `Idempotency-Key`; it
does not make arbitrary origins trusted. Every API and worker HTTP response uses `no-store`,
legacy `no-cache`, MIME-sniffing protection, no-referrer policy, and frame denial.
Production HTTPS responses also emit one-year HSTS without asserting ownership
of sibling subdomains or preload eligibility. The pure ASGI header layer does not
buffer request or response bodies.

Support-ticket and safety-report creation are authenticated, rate-limited, and
idempotent. The API verifies that the caller participated in every referenced
ride. Safety reports remain separate because their access and escalation
requirements are more restrictive than ordinary support; the backend derives
the other participant and never accepts a client-selected reported identity.

Participant support reads are owner-only and omit priority, assignment,
deadlines, retention, and internal notes. Participant safety reads are
reporter-only and additionally omit the submitted description and both party
identities. Only restricted operations routes receive full case detail. Their
queue and resource queries apply the caller's authorized city set in SQL;
resource scope is checked before idempotency replay so a narrowed or revoked
grant cannot replay a previously authorized sensitive response. Case notes are
append-only through the API and carry an explicit `INTERNAL` or
`PARTICIPANT` visibility; only the latest participant message is projected into
mobile responses. Audit events record fixed transitions and booleans, not note
or message text. Request/error/analytics logs must never include support or
safety free text.

`support-launch-v1` sets a 730-day post-closure retention projection;
`safety-launch-v1` sets 1,825 days because safety review and legal follow-up can
outlive ordinary service handling. These periods do not override Moroccan law,
an approved legal hold, or a shorter required privacy period. The controlled
retention worker locks only closed due cases, rechecks that no active legal hold
exists, deletes case notes and direct participant/ride/assignment/free-text
fields, and writes immutable non-content evidence. A minimal non-identifying
case shell remains for referential integrity and aggregate category accounting.
Processed cases are excluded from participant and restricted case APIs.

Legal-hold placement/release requires a market-scoped `PLATFORM_ADMIN`, an
operations session, `manage_case_retention`, idempotency, controlled reason
codes, an allowlisted non-secret authority-reference shape, city scope, and
fixed-field audit. A hold has a review deadline and at most one active hold may
exist for a case. The authority reference must point to protected legal records;
it must not contain correspondence, credentials, testimony, case description,
or other free text. Access to expired-but-not-yet-processed records remains
restricted. Production restore, backup expiry, and legal-review evidence remain
release controls rather than claims made by source code.

Restricted operations queues require an active operations session and a scoped
`SUPPORT_AGENT`, `SAFETY_RESPONDER`, or market-level `PLATFORM_ADMIN` grant.
Assignees are revalidated as active users with a matching grant on every
mutation. Compatibility `/admin` routes are available only in local development
and test. `TAXIMOBILE_LEGACY_ADMIN_API_ENABLED` defaults off and cannot be
enabled in staging or production; those deployments omit every `/admin` route
from both runtime routing and OpenAPI. Account containment now has a scoped
successor: only a `PLATFORM_ADMIN` with `manage_account_security` across every
market associated with the target may revoke sessions, suspend, or reactivate.
The command requires recent MFA, idempotency, a controlled reason/case reference,
refuses self-action and unrelated targets, and fails closed when coverage is
incomplete. Vehicle verification is bound to one scoped city application, recent
operations MFA, idempotency, selected evidence, and fixed-field audit data. The
console requires exact case-derived identity, controlled inputs and typed action
confirmation, and never replays a command after MFA step-up. Independent
rehearsal, access review,
and removal procedures remain mandatory before hosted production operations.
Maintained client source is separately scanned for legacy endpoint literals in
CI. The request boundary counts exact `/admin` namespace attempts using only
fixed `served`/`blocked` outcomes, never raw paths; local routed responses are
marked deprecated, and a critical alert fires if a legacy route is served. A
blocked probe stays a generic 404 and does not reveal whether compatibility code
exists. Production traffic review and final code-removal approval remain human
release gates.
Pager requests contain only alert/case identifiers,
city, kind, deadline, severity, and attempt number—never case text, participant
identity, contact data, or credentials—and provider failures are logged without
URL, token, payload, or response body. A mobile safety report is not an
emergency-service integration; UI
and participant messages must direct a person in immediate danger to move to a
safe place and contact local emergency services without claiming TaxiMobile has
dispatched help.

Sensitive state-changing ride and cash-settlement commands require an
idempotency key. The backend binds the key to the authenticated user, operation,
and canonical request payload in the same transaction as the business change;
the key is not trusted as an authorization credential.

Push registrations are minimized to the owning user, platform, registration
kind, identifier, lifecycle
timestamps, and revocation state. Notification data contains only resource IDs;
the client must authorize and load the resource before displaying sensitive
details. A push registration is never accepted as proof of identity or payment/ride
authority.

Before authentication, a native app may retain the latest Firebase Installation ID only in
process memory so it can retry authenticated device registration after login.
It must not persist that pending ID in preferences, print it, attach it to
telemetry, or expose it in UI/error messages. Re-registration after an account
switch transfers delivery ownership through the authenticated backend endpoint.
The database enforces one account owner per registration kind and identifier. Logout makes a
best-effort authenticated revocation before destroying local credentials, and
the revocation predicate includes owner, platform, kind, and exact ID so one user
cannot disable or probe another user's delivery registration. Network failure
must never prevent local session removal.

Push registration also records the current authentication session. Both explicit
device revocation and transactional logout include that session ID in their
authorization predicate. This prevents a stale session belonging to the same
user from revoking an installation that a newer session already reclaimed.

Cross-instance live events travel only through the private PostgreSQL connection
already required by the API. Payloads are bounded, versioned, and restricted to
an allowlisted event type plus user and ride UUIDs. Unknown versions, event types,
extra fields, malformed UUIDs, and oversized payloads are rejected without
logging the payload. The recipient still authorizes and reloads the ride over
REST; database notification possession grants no command or read authority.

FCM server authorization uses application default credentials or workload
identity supplied by the deployment secret boundary. Service-account keys,
Firebase configuration files, and APNs credentials must not be committed. Invalid
or unregistered FCM IDs/tokens are revoked without logging their full value. Push
payloads contain no names, phone numbers, exact coordinates, fares, or payment
details.

Mobile FCM receipt applies an independent allowlist before any network refresh:
four known ride event names plus a canonical UUID are required. The process
buffers only one unconsumed hint, does not persist it, and never uses its resource
ID for an unauthenticated read or a client-side state mutation. Android and iOS
then reload through ordinary authenticated endpoints. Malformed and expanded
provider payloads are discarded without logging their values.

FCM/outbox retries are bounded by a positive deployment setting. Terminal
failures retain a timestamp and fixed dead-letter outcome, not raw exception
messages, credentials, device tokens, or copied private content. Dead-letter
replay must target explicit event IDs after the underlying incident is resolved;
bulk or automatic replay is not an ordinary application behavior.
The guarded replay command additionally confirms the exact database host/name,
requires a safe incident reference and explicit execution switch, limits a batch
to 100 unique IDs, reads no payload column, and rolls back if any selected row is
not an undelivered dead letter.

The launch manual-transfer flow exposes only a backend-issued payment reference,
the immutable amount/currency, and the ride-snapshotted recipient destination to
the owning passenger. TaxiMobile must never request or store a card number, CVV,
bank password, M-Wallet PIN, OTP, statement login, or financial screenshot. A
passenger claim and optional payer reference are untrusted assertions and can
change payment state only to `PROCESSING`.

Only an authorized operator comparing the recipient's independent bank/wallet
statement may verify a transfer. Verification requires an idempotent command and
a globally unique settlement reference, is audited, and atomically creates the
driver earning. Rejection retains its bounded reason and claim history. Statement
credentials and exports are outside the mobile/API payload boundary, use
least-privilege operational access, and must not be copied into support tickets,
analytics, or logs. Recipient configuration is protected deployment data; a
verified recipient is immutable, and verification/retirement require recent
operations MFA. Capability activation also requires recent MFA, same-city/
operator/service authority, current assignment/effective time, and exact active-
bundle linkage. Missing, stale, cross-scope, or incomplete configuration disables
the capability rather than exposing partial instructions. Payment-reconciliation
grants do not confer recipient/capability mutation permission.

A refund record is evidence that money has already been returned, not a passenger
request or an administrator promise. Only an authenticated operations principal
with scoped `RECONCILE_PAYMENTS` authority and recent MFA (or the transitional
legacy administrator endpoint) may create one, using an idempotent command after independent cash-handover or
outbound-transfer verification. The database serializes refunds through the
locked payment, rejects cumulative amounts above the immutable charge, and
enforces a globally unique settlement reference. Ordinary users cannot list
refund records or submit the command.

Passenger receipts expose only refund ID, amount, currency, closed reason code,
and time plus aggregate refunded/net-paid totals. They never expose the evidence
reference, private operator note, administrator identity, bank/wallet statement,
or support-case text. Audit events retain fixed accounting fields but do not copy
the free-text operator note or external reference. Launch refunds are
operator-funded and cannot silently mutate a driver's immutable earning; any
future driver recovery requires a separately authorized, append-only policy.

CMI and other card providers are deferred. A future adapter must use hosted card
entry, never store or proxy primary account numbers or security codes, authenticate
provider callbacks over the exact contracted fields, enforce idempotency, reject
amount/currency/order mismatches, and retain an auditable provider-event reference
without logging secrets or card data. A return URL is never payment proof.

Unhandled API exceptions use a fixed `INTERNAL_ERROR` response and a request ID.
The structured error event records only allowlisted request metadata and the
exception class; it does not record the exception message, traceback, request
body, provider response, credentials, payment data, or location history.

Request-validation responses follow the same minimization rule. They contain
only rejected field paths and stable validation codes; framework-provided raw
inputs and validator context are stripped so passwords and other submitted
values cannot be reflected back in an error envelope.

Structured request and exception logs use only framework-owned route templates;
unknown routes are recorded as `_unmatched`. Raw URL paths, path identifiers,
queries, and attacker-controlled unmatched path text are not logged.
Caller-supplied request correlation is accepted only as a canonical UUID.
Anything else is replaced by a server-generated UUID before logging or response,
so contact identifiers and arbitrary text cannot be injected through
`X-Request-ID`.

Operational metrics require a dedicated bearer secret separate from user JWTs
and provider credentials. Staging and production reject a missing or short
`TAXIMOBILE_MONITORING_TOKEN`; development may disable the endpoint. Scrapes expose
only bounded method, route-template, status-class, duration-bucket, and exception-
class labels. They never expose raw paths, query strings, request bodies, IDs,
coordinates, tokens, exception messages, or business payloads. The reverse proxy
must restrict `/internal/metrics` to the monitoring network in addition to bearer
authentication.

Background-worker telemetry uses only the fixed `matching`, `outbox`, and
`credentials` names,
the fixed `success`/`error` outcomes, aggregate processed counts, and
last-success timestamps. Retry logs include the fixed worker name and exception
class only. Raw exception messages are excluded because database and provider
errors can contain connection data, registrations, or payload fragments.
API-only processes do not emit zero-valued worker series; this preserves a safe
absence signal when the private worker or its authenticated scrape target is
down.

Outbox monitoring is aggregate-only. It exposes counts for pending,
dead-lettered, and locked events and the age of the oldest pending event, but no
event topic, payload, participant, resource identifier, or device registration.
If the database snapshot fails, the endpoint reports only an explicit unavailable
gauge and omits count gauges so an outage cannot be mistaken for an empty queue.

Security-incident monitoring follows the same fail-closed boundary. One bounded
aggregate query loads no summaries, timeline entries, audit references, actors or
scope identifiers. It emits only availability and fixed `SEV1`-`SEV4` buckets for
open incidents, containment deadlines, pending postmortems and postmortem
deadlines. Both process roles publish the same snapshot; alert and dashboard
queries use `min`/`max`, never addition. `incident_severity` is the only incident
label and its values are closed in source. A database, timeout, unknown-severity
or malformed-count failure emits only unavailable and no stale zero counts.

Database capacity monitoring uses one fixed, five-second-bounded aggregate query
against `current_database()`. It selects connection/active counts, ungranted-lock
count, server connection limit and deadlock counter only. It never selects or
labels database names, roles, session identities, client addresses, query text or
business tables. Driver, permission, timeout and malformed-result failures are
collapsed into `taximobile_database_metrics_available 0`; stale capacity values
are omitted. Host telemetry is not collected by granting a generic monitoring
container access to the host root filesystem or process namespace.

The live-event socket accepts only a bearer access token in the connection
header and validates both its signature and the server-side session before
accepting. Socket messages are server-to-client refresh hints; inbound socket
messages cannot mutate ride state. A received resource ID must still be loaded
through the normal authorization-checked REST endpoint.

Known critical or high vulnerabilities must block candidate promotion unless the
security owner records the finding, bounded compensating control, expiry date and
retest owner. CI lock-audits Python, reviews newly introduced dependency findings,
submits the resolved Gradle graph on trusted pushes, produces an SPDX JSON SBOM
from the actual built backend image, binds the SBOM hash to immutable source
evidence, and scans both OS and library packages with a blocking high/critical
threshold. Every external CI action is full-commit pinned and a local validator
guards these exact settings. A workflow definition is not a clean scan report:
the immutable candidate must pass remotely, and mobile/web artifact SBOMs,
complete JavaScript/Gradle current-tree scans, DAST and independent testing remain
release gates.

Performance smoke testing is GET-only and bounded by explicit request and
concurrency counts. Remote execution requires an explicit confirmation that the
target is authorized non-production staging. Optional authentication comes from a
short-lived `TAXIMOBILE_PERF_BEARER_TOKEN` supplied by the staging secret boundary;
the command does not print tokens, response bodies, redirect-followed content, or
transport exception messages.

Initial administrator creation is an operator-only database operation, not an API
route. It requires an explicit confirmation switch, reads the password from a
hidden prompt, serializes concurrent attempts, and refuses both ordinary-account
promotion and creation of a different second administrator. Production execution
must occur from an audited trusted terminal after migrations and must not place the
password in process arguments, environment variables, logs, or shell history.

That account is only bootstrap authority for the implemented single-scope
system. National rollout requires an audited scoped-grant migration and must not
silently convert every legacy administrator into an unrestricted market-wide
reader.

Compromised-account response is an authenticated, audited operations API workflow
rather than routine direct database manipulation. The route's market is an
association and audit anchor, not authority to modify only one slice of a global
account. The target must have history in that market, and the actor must hold the
dedicated permission over every associated market. Incomplete coverage returns a
conflict and unrelated targets are hidden. A suspension locks the target user row
and atomically marks the account suspended, revokes all active mobile and
operations sessions, and revokes all push registrations. Every protected request
checks both active account status and an unrevoked server-side session, so an
already-issued access token stops working at the next authorization check.
Assignment commit points additionally take a PostgreSQL shared lock on global
user status after locking their driver; suspension uses the exclusive user lock.
The winner is therefore ordered: suspension first prevents the assignment,
whereas an assignment already holding shared authority may commit before
containment and remains immutable history. Session-only revocation does not
pretend to cancel an already-authorized transaction. Reactivation does not
restore revoked credentials. Self-action is refused. Controlled reasons, case
references, idempotency, recent MFA and fixed-field audit prevent an unreviewable
free-text or replayed containment action. Independent approval policy and a
production incident drill remain operational release requirements.

The first dedicated incident register is implemented at
`/api/v1/operations/security-incidents`. It is isolated from participant tokens,
requires a market-scoped `manage_security_incidents` grant, and requires recent
MFA plus idempotency for writes. Scope filtering occurs in SQL before counts and
pagination. Incident status is forward-only and optimistic-versioned; a stale
operator cannot overwrite a newer containment decision. Manual timeline entries
must cite a visible immutable audit ID or a bounded external runbook reference,
and a PostgreSQL trigger rejects timeline update/delete.

Incident responsibility is a separate closed, append-visible authority record.
Only four responsibilities are accepted and a partial unique index permits one
active tenure per incident/responsibility. The database permits an active tenure
to be released once and rejects deletion or later mutation. The API additionally
requires the exact candidate to be active and already hold a live exact-market
platform-administrator grant. It returns one generic conflict for nonexistent,
inactive, expired, revoked and wrong-market candidates, preventing the assignment
surface from becoming an account- or roster-enumeration oracle. There is no broad
candidate search route.

Assignments require recent MFA, an idempotency key, current incident version,
bounded approved roster/shift reference and valid occurrence time. The general
audit log records the responsibility and whether a prior tenure changed, but not
the assignee UUID or roster reference. The restricted responsibility collection
retains those identifiers because incident commanders need accountable handoff
history. A real duty roster and approved shift process remain deployment inputs;
database eligibility is not proof that a person is currently on call.

The operations web destination is permission-hidden and keeps all tokens in the
existing in-memory operations session boundary. It loads at most 100 scoped
records, permits only controlled enum choices, requires typed confirmation for
creation/timeline/responsibility/transition/postmortem commands, and clears confirmation before
dispatch.
A 403 MFA response opens step-up but never retains or replays the command; a 409
reloads backend authority and requires a fresh selection and confirmation.

Postmortem completion is accepted only for a closed, unfinished incident under
the current optimistic version. It stores a fixed outcome, completion time and
actor, appends a referenced immutable timeline fact, and cannot be overwritten.
An outcome that leaves work open requires a bounded external work reference.

Incident summaries remain restricted operational content. They must not contain
passwords, tokens, provider credentials, raw callback bodies, unnecessary
participant identifiers, or copied support/safety notes. General audit records
store only controlled incident codes, state changes, sequence and whether a
reference/summary was recorded. This source workflow does not execute provider
credential rotation, user notification or account/grant containment by itself.
Aggregate Prometheus rules can signal urgency and deadlines, but real paging
exists only after an approved receiver and escalation roster are configured and
drilled. Responders use the separately authorized containment paths and append
their resulting audit/runbook reference. A staffed production drill is still a
release gate.

Audit review is available only to a currently authenticated administrator and is
bounded to at most 100 records per page. Exact filters prevent broad exports from
being necessary during routine incident review. No API route modifies or deletes
audit records, and ordinary passenger or driver authorization is insufficient.

## Security Invariants

## Security delivery gate

Every capability touching identity, authorization, location, documents, money, or external callbacks must state its trust boundary and include a negative test. Check for secrets, path traversal, client-controlled authority, excessive personal data, and unsafe logging before it is considered complete.

* Client applications are untrusted.
* Authorization is enforced server-side.
* Secrets are never committed to source control.
* Sensitive data is minimized.
* Payment credentials are not stored unnecessarily.
* Production databases are never directly exposed to clients.
