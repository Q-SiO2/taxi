# TaxiMobile — Authentication and Authorization Specification

## 1. Purpose

This document defines how TaxiMobile authenticates users and determines what authenticated users are allowed to do.

Authentication answers:

> "Who is this user?"

Authorization answers:

> "What is this user allowed to do?"

These must remain separate concepts.

The backend is always authoritative for authentication and authorization.

---

# 2. Security Objectives

The authentication system must:

* Protect user accounts.
* Prevent unauthorized access.
* Protect driver information.
* Protect passenger information.
* Protect financial information.
* Prevent account takeover.
* Support multiple mobile devices.
* Support Android and iOS.
* Allow sessions to be revoked.
* Provide appropriate audit information.
* Avoid storing passwords in plaintext.

---

# 3. Authentication Architecture

The basic architecture is:

```text
Kotlin Multiplatform App
          │
          │ HTTPS
          ▼
     Authentication API
          │
          ├── User database
          ├── Credential verification
          └── Session management
```

The application receives authentication credentials or tokens from the backend.

The mobile application must never directly access the authentication database.

---

# 4. User Identity

The primary user identity is represented by a `User`.

A user may have:

* Phone number.
* Email address.
* Password credential.
* Roles.
* Passenger profile.
* Driver profile.
* Cooperative membership.

A user may have multiple roles.

For example:

```text id="z7y55v"
User
 │
 ├── PASSENGER
 │
 ├── DRIVER
 │
 └── COOPERATIVE_MEMBER
```

Roles must not be inferred solely from the existence of a profile.

---

# 5. Phone Number Authentication

Phone numbers may be used as a primary login identifier.

The backend should normalize phone numbers into a consistent international representation.

For Morocco, this should generally use the appropriate `+212...` representation.

The initial implementation uses a dependency-free Morocco-only normalizer. It
accepts canonical `+212`, international `00212`, and domestic leading-zero
spellings with ordinary spaces, parentheses, dots, or hyphens, then stores the
canonical `+212` form. Other country numbering plans require an explicit future
internationalization decision rather than permissive guessing.

Phone numbers should not be stored in multiple inconsistent formats.

---

# 6. Email Authentication

Email may optionally be associated with an account.

If email login is supported:

* Email addresses should be normalized appropriately.
* Email uniqueness rules must be defined.
* Verification should be supported where required.
* Password reset should require appropriate verification.

The system should not assume every user has an email address.

---

# 7. Password Storage

Passwords must never be stored directly.

The backend must store a password hash generated using a modern password hashing algorithm.

Suitable choices include:

* Argon2id.
* Another modern password-hashing algorithm approved during implementation.

A fast general-purpose hash such as SHA-256 must not be used directly for password storage.

Successful login checks whether the stored Argon2id encoding still matches the
currently reviewed parameters. An older valid encoding is replaced in the same
login transaction after the password has been verified; plaintext is never
persisted or logged during that upgrade.

The password hashing library should manage salts and appropriate parameters.

---

# 8. Password Requirements

The system should enforce reasonable password requirements.

The goal should be resistance to password attacks without creating unnecessary usability problems.

The implementation should avoid arbitrary rules such as requiring multiple obscure character classes unless justified.

Passwords should be checked against commonly compromised passwords where practical.

---

# 9. Login

The login process is:

```text
User
 │
 │ identifier + password
 ▼
Backend
 │
 ├── Find account
 ├── Verify password
 ├── Check account status
 └── Create session
       │
       ├── Access token
       └── Refresh token
```

A successful login returns credentials required for authenticated API access.

---

# 10. Failed Login

The backend should avoid revealing whether an account exists.

For example, the system should not respond differently with:

```text
"User does not exist"
```

versus:

```text
"Password is incorrect"
```

for an unauthenticated login attempt.

A generic authentication failure should be returned.

The implementation also avoids a cheap timing oracle: missing, suspended, and
active accounts all execute one Argon2 password verification before returning a
decision. A process-local random dummy hash supplies equivalent work when no
stored credential exists, but can never authenticate and is never persisted or
logged. Exact network timing equivalence cannot be promised, but account lookup
does not skip the dominant password-hash cost.

---

# 11. Login Rate Limiting

Login attempts must be rate limited.

The system should consider:

* IP address.
* Account identifier.
* Device/session information where appropriate.

Repeated failures should trigger progressively stronger protections where necessary.

The system must avoid creating an easy denial-of-service mechanism against legitimate users.

---

# 12. Access Tokens

Authenticated API requests use an access token.

Example:

```text id="jv9bna"
Authorization: Bearer <access_token>
```

Access tokens expire after 15 minutes. They are signed JWTs but are accepted only while their corresponding server-side session remains active. Validation requires the fixed TaxiMobile API issuer, mobile-client audience, access-token type, subject, session ID, issued-at time, and expiration; a correctly signed token from another security domain or with a missing required claim is rejected.

---

# 13. Refresh Tokens

Refresh tokens allow the client to obtain new access tokens without requiring the user to enter credentials repeatedly.

Conceptually:

```text id="oyl58j"
Access Token
    │
    └── expires
          │
          ▼
     Refresh Token
          │
          ▼
    New Access Token
```

Refresh tokens expire after 30 days and are stored by the backend only as a SHA-256 hash. They have a significantly longer lifetime than access tokens.

---

# 14. Refresh Token Rotation

Refresh tokens should preferably be rotated when used.

Conceptually:

```text id="4ip8pn"
Refresh Token A
       │
       ▼
Refresh request
       │
       ├── Token A revoked
       │
       └── Token B issued
```

This helps limit the impact of stolen refresh tokens.

The implementation detects reuse of a token that has already been rotated. It
revokes the active session family descended from that token and rejects the
request, while leaving independently authenticated devices unaffected. A normal
logout/revocation is not treated as token reuse.

---

# 15. Token Storage

Mobile tokens are sensitive credentials.

The Kotlin application must not store access or refresh tokens in:

* Plaintext files.
* Shared preferences without appropriate protection.
* General application databases.
* Source code.
* Logs.

Tokens should be stored using the secure credential storage mechanism available on each platform.

The Kotlin Multiplatform architecture should provide a common interface while using platform-specific secure storage underneath.

Conceptually:

```text id="g9kbrf"
commonMain
    │
    ▼
SecureTokenStorage interface
    │
    ├── Android implementation
    │
    └── iOS implementation
```

---

# 16. Token Transmission

Tokens must only be transmitted over HTTPS in production.

The application must never send authentication credentials through:

* HTTP.
* URL query parameters.
* Analytics events.
* Logs.
* Error reports.

---

# 17. Logout

Logout should invalidate the relevant session where supported.

The mobile client should:

1. Remove locally stored credentials.
2. Notify the backend when possible.
3. Return to the unauthenticated application state.

If the device is offline during logout, local credentials should still be removed.

When the native client has successfully registered a background-push token in
the current process, it first makes a best-effort authenticated device-revocation
request. This prevents a signed-out installation from remaining an active
recipient under normal connectivity. Failure to revoke push metadata never
delays session revocation or local credential deletion; a later authenticated
registration atomically transfers the provider registration to its new account owner.

The backend also binds each new push registration to the session that claimed
it. Successful `POST /auth/logout` revokes registrations still owned by that
session transactionally. If a newer session has already reclaimed the same app
installation, the old session's explicit device deletion and later logout cannot
revoke the newer binding.

---

# 18. Session Management

Each authenticated device/session should be represented independently where practical.

Conceptually:

```text id="m5clz8"
User
 │
 ├── Session A — Android phone
 ├── Session B — iPhone
 └── Session C — Desktop
```

A user should eventually be able to view and revoke active sessions.

---

# 19. Session Revocation

The backend must be capable of revoking sessions.

Reasons may include:

* User logout.
* Lost phone.
* Suspected account compromise.
* Password reset.
* Administrative action.
* Security incident.

Revoking one session should not necessarily revoke every other session unless required.

---

# 20. Password Reset

A password reset process should verify control over an approved recovery method.

Possible recovery methods include:

* Verified phone number.
* Verified email address.

The exact mechanism depends on available infrastructure.

Password reset links or codes must:

* Expire.
* Be single-use.
* Not expose the existing password.
* Be rate limited.

---

# 21. Password Reset Security

The system must not reveal whether a submitted recovery identifier belongs to an account.

For example:

```text
Password reset requested.
```

should be returned whether or not the identifier exists.

This reduces account enumeration.

---

# 22. Phone Verification

If phone-based authentication is used, the system may verify phone ownership using a one-time code.

Conceptually:

```text
Enter phone number
       │
       ▼
Send verification code
       │
       ▼
User enters code
       │
       ▼
Backend verifies code
       │
       ▼
Phone verified
```

Codes must:

* Expire quickly.
* Be single-use.
* Be rate limited.
* Never be logged in plaintext.

---

# 23. Multi-Factor Authentication

MFA should be considered for:

* Administrative accounts.
* Cooperative administrators.
* High-privilege accounts.
* Potentially drivers.

MFA should not be mandatory for the first MVP unless the required infrastructure is available.

The architecture should nevertheless avoid making MFA impossible to add later.

---

# 24. Device Trust

The application may associate sessions with devices.

However, a device identifier must not be treated as proof of identity.

A stolen authenticated device must still be revocable.

---

# 25. Roles

Initial roles include:

```text id="s0s6ez"
PASSENGER
DRIVER
COOPERATIVE_MEMBER
ADMIN
```

Additional roles may be introduced later.

Roles should be represented in the backend authorization system rather than trusted from client-provided values.

---

# 26. Permissions

Roles should map to permissions.

For example:

```text id="j9sv42"
PASSENGER
 ├── request_ride
 ├── cancel_own_ride
 ├── view_own_rides
 └── rate_completed_ride

DRIVER
 ├── manage_driver_profile
 ├── manage_vehicles
 ├── update_location
 ├── receive_ride_offers
 ├── accept_ride
 ├── complete_ride
 └── view_own_earnings

COOPERATIVE_MEMBER
 ├── view_membership
 ├── participate_in_governance
 └── vote

ADMIN
 └── administrative_permissions
```

This is conceptual.

The final permission list should be defined as the application grows.

---

# 27. Authorization Rules

Authorization should follow the principle of least privilege.

A user should only have access to the minimum resources required for their role.

For example:

```text id="m7f0e4"
Driver A
   │
   └── Can view Driver A's rides

Driver A
   X
   │
   └── Cannot view Driver B's private earnings
```

---

# 28. Resource Ownership

Authorization should consider ownership.

For example:

```text id="r7lj65"
GET /rides/{ride_id}
```

must verify that the authenticated user is:

* The passenger.
* The assigned driver.

The participant endpoint does not grant access merely because an account has an
administrative role. Any future administrative ride-review capability requires
a separate explicit purpose, authorization policy, audit trail, and response
contract rather than inheriting passenger/driver access.

Being authenticated is not sufficient.

---

# 29. Administrative Access

Administrative accounts have elevated privileges and require additional protection.

Administrative functionality should be isolated from normal user functionality.

Administrators should have:

* Strong authentication.
* Appropriate audit logging.
* Restricted permissions.
* Session management.
* Potential MFA.

---

# 30. Administrative Actions

Sensitive administrative actions should generate audit logs.

Examples:

* Approving a driver.
* Rejecting a driver.
* Suspending a driver.
* Modifying pricing.
* Modifying cooperative settings.
* Viewing sensitive documents.
* Resolving safety reports.
* Modifying financial records.

Audit entries should identify:

```text id="0u8k83"
Who
What
When
Which resource
What changed
```

---

# 31. Driver Verification Authorization

Only authorized personnel should be able to modify driver verification state.

The mobile client must never be able to submit:

```json id="4eoj0c"
{
  "verification_status": "APPROVED"
}
```

and have that value accepted simply because the user is authenticated.

The backend determines verification state.

---

# 32. Role Assignment

Users must not be able to assign themselves roles.

For example, a client must never be allowed to send:

```json id="q6nq6q"
{
  "role": "ADMIN"
}
```

and become an administrator.

Role assignment must be performed by trusted backend logic or authorized administrators.

Registration treats the database uniqueness constraints as the final arbiter for
email and phone identifiers. If concurrent requests both pass the initial
existence check, the losing transaction returns the same safe account-conflict
response; database messages, constraint names, and submitted identifiers are not
exposed.

The first `ADMIN` is created only by the deployment-operator bootstrap command
after migrations have been applied. The password is entered through a hidden
interactive prompt, and concurrent bootstrap attempts are serialized by the
database. The command never promotes an existing passenger or driver account and
cannot be reused to create additional administrators. No public registration or
profile request may carry a role.

---

# 33. Driver Activation

Likewise, drivers cannot activate themselves by modifying a local application state.

The authoritative sequence is:

```text id="iw6o0j"
Driver application
       │
       ▼
Verification
       │
       ▼
Administrative approval
       │
       ▼
Backend marks driver ACTIVE
       │
       ▼
Driver may go ONLINE
```

---

# 34. Authentication State on Mobile

The mobile application should maintain a clear authentication state.

Conceptually:

```text id="y9d6ij"
Unauthenticated
      │
      ▼
Authenticating
      │
      ▼
Authenticated
      │
      ├── Token refresh
      │
      └── Logout
```

The application should not display authenticated screens until the authentication state has been established.

---

# 35. Expired Access Token

When an access token expires:

```text id="c0m4y0"
API request
    │
    ▼
401 Unauthorized
    │
    ▼
Attempt token refresh
    │
   ┌┴─────────┐
   │          │
Success     Failure
   │          │
   ▼          ▼
Retry       Logout
request     user
```

The client should avoid infinite refresh loops.

---

# 36. Network Failure

Authentication logic must distinguish between:

```text id="3gy3zr"
401 Unauthorized
```

and:

```text id="0p0kpn"
Network unavailable
```

A network failure does not automatically mean that the user is logged out.

---

# 37. Offline Behavior

TaxiMobile should not attempt to provide full ride functionality offline.

Critical operations such as:

* Ride creation.
* Ride acceptance.
* Ride completion.
* Payment confirmation.

must be confirmed by the backend.

The application may retain limited local state for UI continuity.

---

# 38. Local Sensitive Data

The mobile application should minimize locally stored sensitive information.

Examples that should not be unnecessarily cached:

* Full government identification documents.
* Passwords.
* Payment credentials.
* Sensitive driver verification information.

Local caches should have defined expiration and deletion behavior.

---

# 39. Logging

Authentication secrets must never be logged.

Logs must not contain:

* Passwords.
* Access tokens.
* Refresh tokens.
* Verification codes.
* Full payment credentials.

Care should also be taken with:

* Phone numbers.
* Email addresses.
* Location data.
* Government identifiers.

---

# 40. Error Messages

Authentication errors should provide useful information without leaking sensitive details.

Bad:

```text
User john@example.com exists but entered an incorrect password.
```

Better:

```text
Invalid credentials.
```

---

# 41. Account Enumeration

The API should avoid allowing unauthenticated users to determine whether a particular:

* Phone number.
* Email address.

belongs to an account.

This applies to:

* Login.
* Registration.
* Password reset.
* Verification flows.

---

# 42. Brute Force Protection

The backend should detect repeated authentication failures.

Potential protections include:

* Rate limiting.
* Temporary delays.
* Progressive throttling.
* CAPTCHA or equivalent mechanisms where justified.

The system should not permanently lock users merely because an attacker repeatedly attempts to log into their account.

---

# 43. Session Security

Sessions should have:

* Expiration.
* Revocation.
* Secure token handling.
* Server-side validation.
* Device association where appropriate.

Long-lived sessions should be carefully controlled.

---

# 44. Transport Security

Production clients must reject insecure API endpoints.

Production configuration should use:

```text id="2uybr9"
https://
```

not:

```text id="9q1b5b"
http://
```

except where explicitly required for a trusted local development environment.

---

# 45. Certificate Validation

The mobile application must use normal platform TLS certificate validation.

Custom certificate pinning should not be introduced casually.

If certificate pinning is eventually considered, it must include a rotation strategy so that certificate changes do not permanently break the application.

---

# 46. API Security Boundary

The backend must assume the mobile application is potentially hostile.

This means the backend must assume that a malicious user can:

* Modify application binaries.
* Modify network requests.
* Create custom API clients.
* Replay requests.
* Send invalid JSON.
* Modify local state.

Therefore:

> Security-critical rules must exist on the backend.

---

# 47. Client-Side Validation

The mobile application should still validate input for usability.

For example:

```text
Invalid phone number
Invalid email
Missing pickup location
```

However, client validation is not a security boundary.

The backend must validate the same data independently.

---

# 48. Authentication Testing

Authentication tests should include:

* Correct credentials.
* Incorrect credentials.
* Expired tokens.
* Revoked tokens.
* Invalid tokens.
* Refresh token reuse.
* Password reset.
* Account suspension.
* Role escalation attempts.
* Resource ownership violations.
* Brute-force attempts.

---

# 49. Authorization Testing

Authorization tests should explicitly attempt to access another user's resources.

Examples:

```text id="k48b7d"
Passenger A → Passenger B's profile
Passenger A → Driver B's rides
Driver A → Driver B's earnings
Driver A → Admin endpoint
Passenger → Driver endpoint
Driver → Cooperative administration endpoint
```

All unauthorized attempts must fail.

---

# 50. Security Incident Response

The architecture should allow compromised sessions to be revoked.

In the event of an account compromise, administrators should be able to:

* Revoke sessions.
* Suspend accounts.
* Review audit logs.
* Investigate suspicious actions.

Security incidents should not require direct database manipulation as the normal response.

The initial administrative incident workflow exposes authenticated `ADMIN`-only
operations to revoke all sessions for one user, suspend that user, and reactivate
a suspended user after review. Session revocation also revokes the user's push
registrations. Suspension and revocation are transactional and audited with the
administrator, target, bounded reason, timestamp, and affected counts. Existing
access and refresh tokens remain invalid after reactivation; a new login is
required. Self-suspension and reactivation of a deactivated account are refused.
Administrators can review the append-oriented records through a bounded,
filterable administrator-only endpoint, allowing incident review without normal
direct database access. The endpoint cannot edit or delete audit history.

---

# 51. Authentication MVP

The initial authentication system should support:

```text id="3y1lmy"
User registration
User login
Password hashing
Access tokens
Refresh tokens
Logout
Current-user endpoint
Role-based authorization
Resource ownership checks
Rate limiting
Secure mobile token storage
```

Phone verification and MFA may be added depending on deployment requirements.

---

# 52. Future Authentication Features

Potential future functionality:

* Phone OTP authentication.
* Email verification.
* Password reset.
* MFA.
* Passkeys.
* Device/session management.
* Suspicious-login detection.
* Account recovery workflows.

These should be introduced without requiring a complete rewrite of the authentication architecture.

---

# 53. Authentication Principles

### Principle 1 — Never trust the client

The client is an untrusted environment.

### Principle 2 — Authentication is not authorization

Knowing who someone is does not determine what they may do.

### Principle 3 — Least privilege

Users should receive only the permissions they require.

### Principle 4 — Secrets stay secret

Passwords, tokens, and verification codes must never appear in logs or ordinary application storage.

### Principle 5 — Revocability

Sessions and access must be capable of being revoked.

### Principle 6 — Backend authority

The backend determines identity, permissions, and security-sensitive state.

### Principle 7 — Secure defaults

Security should not depend on developers remembering to enable it for individual endpoints.

### Principle 8 — Auditability

Sensitive administrative actions must be traceable.

### Principle 9 — Platform independence

Authentication must work consistently across Android and iOS.

### Principle 10 — Recoverability

Users and administrators must have safe ways to recover compromised accounts.
