# TaxiMobile — Security

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

The initial mobile implementation requests only foreground/when-in-use location
after the user selects a current-location action. It performs a one-shot lookup,
does not request background permission, and does not start continuous tracking.
Permission denial, timeout, or disabled location services must not submit a stale
or invented coordinate. A recently observed Android platform location may be used
only as a short timeout fallback and is never retained by the client as location
history. The backend still validates all submitted coordinates, timestamps,
freshness, movement, authorization, and ride state.
Only one foreground lookup may be active per application. Repeated taps are
ignored rather than cancelling/replacing the pending callback, and they never
create an additional location sample or backend submission.
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

National expansion preserves a stricter pre-assignment boundary: passengers
cannot query online taxi markers, available-driver counts, identities,
candidate rankings, queues, or precise supply heatmaps. Published fixed-route
geometry is immutable service-catalog data and contains no driver observation.
Aggregate supply exists only inside scoped operations reporting with coarse
zones, time buckets, and small-cell suppression.

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

CI audits the fully pinned Python runtime lock with PyPA `pip-audit` and fails on
known published vulnerabilities. Dependabot monitors Python, Gradle, GitHub
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

Support-ticket creation is also authenticated and rate-limited. The API verifies
that a caller actually participated in any ride they reference, and support
descriptions are not included in request logs. Safety reports remain separate
because their access and escalation requirements are more restrictive than
ordinary support.

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

CMI card entry occurs only on CMI-controlled hosted pages. TaxiMobile never stores
or proxies primary account numbers or security codes. Callback processing must
verify the CMI-defined signature/authentication material over the exact documented
fields before any payment transition, enforce idempotency, reject amount/currency
or order mismatches, and retain an auditable provider-event reference without
logging secrets or card data.

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

The live-event socket accepts only a bearer access token in the connection
header and validates both its signature and the server-side session before
accepting. Socket messages are server-to-client refresh hints; inbound socket
messages cannot mutate ride state. A received resource ID must still be loaded
through the normal authorization-checked REST endpoint.

Known critical vulnerabilities should be addressed before production deployment.

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

Compromised-account response is an authenticated, audited administrative API
workflow rather than routine direct database manipulation. A suspension locks
the target user row and atomically marks the account suspended, revokes all
active sessions, and revokes all push registrations. Every protected request
checks both active account status and an unrevoked server-side session, so an
already-issued access token stops working immediately. Reactivation does not
restore revoked credentials. Administrators cannot suspend themselves through
the API, limiting accidental loss of the only operator account.

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
