# TaxiMobile — Driver System Specification

## 1. Purpose

The driver system manages taxi drivers participating in the TaxiMobile cooperative.

It is responsible for:

* Driver registration.
* Driver identity verification.
* Professional credential verification.
* Vehicle registration.
* Cooperative membership.
* Driver account status.
* Availability.
* Ride participation.
* Driver earnings.
* Driver history.
* Driver-facing notifications.
* Driver-related administrative actions.

The system must distinguish between:

1. A person who has an account.
2. A verified taxi driver.
3. A participating cooperative member.
4. A driver currently available for rides.

These are not automatically the same thing.

---

# 2. Driver Model

A driver is a user who has been verified as an eligible taxi driver.

Conceptually:

```text
User
 │
 ├── Account
 │
 └── Driver Profile
       │
       ├── Professional Credentials
       ├── Vehicle
       └── Cooperative Membership
```

A driver account should not become eligible to receive rides until the required verification process has been completed.

---

# 3. Driver Registration

A person wishing to become a participating driver begins by creating an account.

Initial registration may require:

* Name.
* Phone number.
* Email address where applicable.
* Password or supported authentication credentials.
* Basic identity information.
* Agreement to applicable terms.

Registration creates a user account but does not automatically create an active driver.

---

# 4. Driver Verification

After registration, the applicant must submit the information required to establish eligibility.

Potential information includes:

* Government identification.
* Taxi driver license.
* Professional authorization.
* Vehicle registration.
* Vehicle insurance.
* Taxi authorization or permit.
* Required photographs or documents.

The exact requirements depend on Moroccan law and the jurisdiction in which TaxiMobile operates.

The software should therefore make the verification requirements configurable rather than permanently hard-coding a single document list.

---

# 5. Verification States

A driver application may have states such as:

```text
NOT_STARTED
SUBMITTED
UNDER_REVIEW
ADDITIONAL_INFORMATION_REQUIRED
APPROVED
REJECTED
SUSPENDED
EXPIRED
```

Conceptually:

```text
NOT_STARTED
     │
     ▼
SUBMITTED
     │
     ▼
UNDER_REVIEW
   │       │
   │       ├──► ADDITIONAL_INFORMATION_REQUIRED
   │       │             │
   │       │             └──► UNDER_REVIEW
   │       │
   │       └──► REJECTED
   │
   ▼
APPROVED
```

An approved driver may later become suspended or expired.

---

# 6. Verification Authority

Driver verification should be performed by authorized cooperative administrators or another formally designated verification process.

The mobile application must never determine that a driver is verified merely because required fields appear complete.

The backend must contain the authoritative verification state.

---

# 7. Document Security

Driver documents may contain highly sensitive information.

Documents should:

* Be transmitted securely.
* Be encrypted where appropriate.
* Not be publicly accessible.
* Not be exposed to passengers.
* Only be accessible to authorized personnel.
* Have defined retention policies.
* Be deleted when no longer legitimately required.

Document URLs should never be guessable public URLs.

---

# 8. Driver Profile

Once approved, a driver has a driver profile.

The profile may contain:

* Display name.
* Profile photograph where appropriate.
* Verification status.
* Cooperative membership status.
* Vehicle information.
* Rating information where applicable.
* Service information.
* Driver statistics.

Only information necessary for passenger safety and service should be shown to passengers.

---

# 9. Passenger-Facing Driver Information

Before or during a ride, passengers may need to see:

* Driver name.
* Driver photograph where appropriate.
* Vehicle make.
* Vehicle model.
* Vehicle color.
* Vehicle registration/identification information where legally appropriate.
* Taxi identification.
* Relevant verification indicators.

The platform should avoid exposing unnecessary personal information.

For example, the passenger should not need access to:

* Driver's personal phone number.
* Home address.
* Government identification number.
* Private financial information.

---

# 10. Vehicle Registration

A driver must have at least one eligible vehicle associated with their driver profile.

A vehicle may contain:

* Make.
* Model.
* Year where relevant.
* Color.
* Registration information.
* Taxi identification.
* Vehicle type.
* Passenger capacity.
* Accessibility characteristics where applicable.
* Insurance information.
* Verification status.

The exact fields should be determined by applicable regulations.

---

# 11. Vehicle Verification

Vehicles must be verified before being used for rides.

Vehicle verification may include:

* Registration verification.
* Taxi permit verification.
* Insurance verification.
* Inspection information.
* Vehicle identification.

A vehicle that fails verification must not be eligible for dispatch.

---

# 12. Multiple Vehicles

The architecture should allow a driver to have multiple vehicles.

However, only eligible vehicles should be available for active dispatch.

Example:

```text
Driver
 ├── Vehicle A — ACTIVE
 └── Vehicle B — INACTIVE
```

A driver should explicitly select which eligible vehicle is currently being used.

### MVP vehicle flow

The driver product can register a vehicle and list its verification state. A
registered vehicle starts as `PENDING`; it cannot be selected for active
dispatch or used to go online. An authorized cooperative administrator verifies
an active vehicle through the separate administrative API, which records an
audit entry. The driver can then explicitly select that verified vehicle and
the backend returns the confirmed active-vehicle state. The client never marks
a vehicle verified or selected locally.

Vehicle edits and removal are available only while the driver is offline. An
edit resets verification to `PENDING`; removal is an `INACTIVE` soft
deactivation, not a physical deletion, so historical rides remain explainable.

---

# 13. Driver Status

Driver account status is separate from availability.

Possible account statuses include:

```text
PENDING
ACTIVE
SUSPENDED
DEACTIVATED
```

Only an `ACTIVE` driver should be able to become available for rides.

---

# 14. Driver Availability

Availability represents whether the driver is currently willing and able to receive ride requests.

Possible availability states:

```text
OFFLINE
AVAILABLE
PAUSED
OFFERED_RIDE
EN_ROUTE
AT_PICKUP
ON_RIDE
```

A driver must explicitly enter `AVAILABLE`.

Being logged into the application does not automatically make a driver available.

---

# 15. Going Online

When the driver selects "Go Online", the backend should verify:

* Driver account is active.
* Driver verification is valid.
* Required credentials have not expired.
* At least one eligible vehicle is available.
* Driver has selected an active vehicle.
* Location permission is available.
* Required application permissions are satisfied.
* A recently accepted operational location exists.

If these conditions are met, the backend changes the driver to `AVAILABLE`.

Until a jurisdiction-specific required-type catalog is approved, an empty
credential set does not invent missing requirements. Once any professional
credential is recorded, a non-`VERIFIED` status or an expiry at or before backend
time blocks going online. The same rule is re-evaluated during candidate
selection and offer acceptance so a previously online driver cannot retain new
dispatch eligibility after a credential changes or expires.

The mobile app requests foreground location explicitly and submits it while the
approved driver is still offline. The backend accepts this staging update only
when a verified active vehicle is already selected. It then independently checks
the latest observation against the configured dispatch-freshness interval when
processing “Go Online”; client permission state alone is never trusted.

---

# 16. Going Offline

A driver may go offline when:

* They finish working.
* They take a break.
* They leave the service area.
* They no longer want ride requests.

Going offline should prevent new ride offers.

A driver should not normally be able to go offline while actively completing a ride without first handling the active ride according to the ride state rules.

---

# 17. Driver Location

While available or actively handling a ride, the application may periodically transmit the driver's location.

Location updates should contain:

* Latitude.
* Longitude.
* Timestamp.
* Accuracy where available.
* Heading where available.
* Speed where available.

The backend should reject obviously invalid location updates.

Examples include:

* Impossible geographic coordinates.
* Unrealistic movement.
* Extremely old timestamps.

---

# 18. Location Privacy

Driver location is sensitive information.

The system should distinguish between:

### Active operational location

Used to:

* Match rides.
* Navigate.
* Show the driver's approach to a passenger.

### Historical location

Used for:

* Dispute resolution.
* Safety investigations.
* Operational analysis.

Historical location data should be retained only as long as necessary.

The platform should not create permanent detailed maps of individual drivers' movements without a legitimate purpose.

---

# 19. Ride Offers

An available driver may receive ride offers.

An offer should contain enough information for the driver to make an informed decision.

Potential information:

* Pickup location.
* Estimated distance to pickup.
* Estimated travel time.
* Destination information where appropriate.
* Estimated fare where applicable.
* Passenger requirements where relevant.

The cooperative should determine whether drivers are allowed to decline individual rides without penalty.

The initial system should support declining.

---

# 20. Driver Acceptance

When a driver accepts an offer:

1. The client sends the acceptance request.
2. The backend verifies the offer is still valid.
3. The backend verifies the driver is still eligible.
4. The backend atomically assigns the driver.
5. The ride becomes `ACCEPTED`.
6. The driver state changes appropriately.
7. The passenger receives a real-time update.

If another driver has already accepted the ride, the request must fail cleanly.

---

# 21. Driver Cancellation

Drivers may cancel accepted rides when necessary.

The system should record:

* Driver.
* Ride.
* Timestamp.
* Ride state.
* Reason where appropriate.

The system should not automatically assume that a cancellation represents misconduct.

Legitimate reasons may include:

* Vehicle problem.
* Passenger safety issue.
* Emergency.
* Mechanical failure.
* Incorrect pickup location.
* Passenger no-show.
* Other operational circumstances.

---

# 22. Driver No-Show

The system should distinguish between:

* Driver cancelling.
* Passenger cancelling.
* Driver unable to reach passenger.
* Passenger unable to reach driver.
* Passenger not present.
* Driver not present.

This distinction is important for dispute resolution and cooperative administration.

---

# 23. Driver Earnings

The driver application should provide an earnings view.

The implemented driver app displays the backend-provided settled earnings
summary (gross, explicit fees, adjustments, net, count, and settled-through
timestamp) plus the bounded earning rows returned by the same owner-scoped API.
It performs no arithmetic or inference from completed rides. Date-range controls
and analytics remain deferred until the reporting requirements are agreed.

Potential information includes:

* Current ride earnings.
* Daily earnings.
* Weekly earnings.
* Monthly earnings.
* Completed rides.
* Platform/cooperative fees.
* Payment status.
* Net amount.

The exact financial model will be defined in `payments.md`.

The application should never hide fees from drivers.

---

# 24. Platform Fees

Any fee charged to a ride should be clearly represented.

For example:

```text
Passenger fare
       │
       ├── Driver share
       │
       └── Cooperative/platform contribution
```

The exact percentages or amounts should not be hard-coded into the mobile application.

They should be managed by backend configuration and recorded against each ride.

Historical rides must preserve the financial rules that were applicable at the time.

---

# 25. Cooperative Membership

Cooperative membership is distinct from being a driver.

A driver may be:

```text
Verified driver
      │
      ├── Cooperative member
      │
      └── Non-member participant
```

The exact relationship between membership and platform participation depends on the cooperative's legal structure.

The software should support this distinction.

---

# 26. Cooperative Member Information

Where appropriate, a cooperative member profile may contain:

* Membership status.
* Membership date.
* Membership identifier.
* Voting eligibility.
* Membership contributions.
* Cooperative participation information.

This information must not automatically be visible to passengers.

---

# 27. Cooperative Governance

The long-term platform may provide digital tools for cooperative governance.

Potential functionality includes:

* Member voting.
* Proposals.
* Policy changes.
* Financial reports.
* Cooperative announcements.
* Meeting information.
* Membership administration.

Governance functionality should be implemented separately from the ride-dispatch system.

A driver voting on a cooperative policy should not require access to ride-management functionality.

---

# 28. Cooperative Voting

Future voting functionality may allow eligible members to vote on defined proposals.

A conceptual structure:

```text
Proposal
    │
    ├── Description
    ├── Created by
    ├── Voting period
    ├── Eligibility rules
    └── Results
```

The system must prevent:

* Duplicate votes.
* Unauthorized votes.
* Voting after the deadline.
* Unauthorized modification of results.

The exact governance rules are outside the initial application specification.

---

# 29. Driver Performance

TaxiMobile should avoid reproducing the most harmful aspects of gig-platform performance systems.

The platform may collect operational metrics such as:

* Completed rides.
* Cancellations.
* Acceptance rate.
* Customer feedback.
* Safety reports.
* Average response time.

However, these metrics should not automatically become punitive measures.

Any system that affects a driver's access to the platform should be explicitly defined, transparent, and subject to cooperative governance.

---

# 30. Ratings

Drivers may receive passenger ratings.

Ratings should be presented as feedback rather than an unquestionable measure of driver worth.

A rating system should account for:

* Bad-faith reports.
* Discrimination.
* Accidental ratings.
* Safety-related reports.
* Disputes.

Drivers should have an appropriate mechanism for challenging serious or demonstrably incorrect reports.

The MVP driver account exposes passenger feedback only from an explicitly
selected completed ride in the driver's backend-owned history. It reauthorizes
the ride and rating independently, displays the returned score and optional
comment without reviewer identifiers, and does not use ratings for eligibility,
matching, or earnings. Formal rating disputes remain part of the later operating
policy rather than being simulated as an unsupported client action.

---

# 31. Driver Support

Drivers should have access to support mechanisms.

Potential support categories include:

* Account problems.
* Verification problems.
* Payment problems.
* Ride disputes.
* Passenger problems.
* Vehicle problems.
* Safety incidents.
* Technical problems.

Support requests should be recorded and associated with the appropriate driver and, when relevant, ride.

---

# 32. Driver Suspension

A driver may be temporarily prevented from receiving rides.

Possible suspension reasons include:

* Expired credentials.
* Invalid vehicle documentation.
* Serious safety incident.
* Confirmed fraud.
* Legal requirement.
* Cooperative disciplinary decision.

Suspension should be recorded with:

* Reason.
* Start date.
* Reviewing authority.
* Expected end date where applicable.
* Appeal/review information where applicable.

Suspension should not be implemented as an opaque automated punishment.

---

# 33. Driver Deactivation

A driver account may be deactivated.

Deactivation is distinct from suspension.

The system should preserve historical records where legally required.

The driver should not necessarily be able to simply create a new account to bypass a legitimate deactivation.

Any account-recreation policy must be compatible with applicable law and cooperative governance.

---

# 34. Credential Expiration

Professional credentials may expire.

The system should track expiration dates where relevant.

Before expiration, the driver should receive notifications.

The backend runs a bounded, replica-safe credential lifecycle processor. Its
warning window and poll interval are deployment configuration (30 days and 60
seconds by local default). It stores the exact expiry value already warned,
creates one durable notification and minimized FCM refresh hint, and can warn
again if a renewed credential receives a different expiry. At expiry it changes
the credential status to `EXPIRED` and creates a separate durable notification.

After expiration:

```text
Credential expires
       │
       ▼
Driver becomes ineligible
       │
       ▼
Cannot receive new rides
```

Existing active rides should be handled safely according to operational rules.
The processor does not interrupt an active ride; online, matching, and offer
acceptance checks prevent only new assignments.

---

# 35. Driver Notifications

Drivers may receive notifications for:

* Ride offers.
* Ride acceptance.
* Passenger cancellation.
* Ride changes.
* Credential expiration.
* Payment information.
* Cooperative announcements.
* Support responses.
* Safety alerts.

Notifications should not be treated as authoritative system state.

---

# 36. Driver Account Security

Driver accounts require strong security because they provide access to:

* Passenger information.
* Ride information.
* Earnings.
* Personal information.
* Vehicle information.

The system should support appropriate security measures such as:

* Secure authentication.
* Session management.
* Token expiration.
* Device/session management.
* Optional multi-factor authentication.
* Secure local credential storage.

---

# 37. Driver Data Ownership

Drivers should have meaningful visibility into data the platform stores about them.

Where practical, drivers should be able to access:

* Profile information.
* Ride history.
* Earnings.
* Fees.
* Ratings.
* Account status.
* Cooperative membership information.
* Privacy-minimized professional credential status and expiry information.

The current driver account view loads the authenticated caller's optional
membership through the dedicated cooperative API and displays only cooperative
name, status, member number, and joined timestamp. A confirmed `404` means no
current membership; driver approval is never presented as membership.

Completed history rows are actionable. The selected ride's details and optional
passenger rating are loaded through participant-authorized ride endpoints and
kept only in ephemeral render state; another driver cannot read them.

The same private account view reads professional credential metadata from the
driver self endpoint. It shows configurable type, backend status, and optional
issue/expiry timestamps, but never receives credential numbers, document
references, or document URLs. Document ingestion and administrative review stay
unavailable until jurisdictional policy and protected storage are selected.

The driver profile name, verification status, and account status shown in this
view are also reloaded from the backend profile response; the client does not
derive active or approved state from the presence of controls.

The platform should avoid collecting data that does not have a legitimate purpose.

---

# 38. Driver Data Export

The system should eventually provide an export mechanism for appropriate driver data.

Possible exports include:

* Ride history.
* Earnings.
* Fees.
* Ratings.
* Account information.

The exact export format can be determined later.

---

# 39. Driver Onboarding Flow

The initial onboarding flow should conceptually be:

```text
Create account
      │
      ▼
Apply as driver
      │
      ▼
Provide required information
      │
      ▼
Submit verification
      │
      ▼
Administrative review
      │
   ┌──┴───┐
   │      │
Approved  Rejected
   │
   ▼
Register/select vehicle
   │
   ▼
Complete cooperative requirements
   │
   ▼
Driver becomes ACTIVE
```

The exact sequence may change according to legal and cooperative requirements.

---

# 40. Minimum Viable Driver System

The first implementation should support:

1. Driver account creation.
2. Driver application.
3. Basic verification workflow.
4. Vehicle registration.
5. Driver approval.
6. Driver availability.
7. Driver location updates.
8. Ride offers.
9. Ride acceptance.
10. Ride completion.
11. Driver earnings/history.

Advanced cooperative governance features should come later.

---

# 41. Future Driver Features

Potential future features include:

* Multiple vehicles.
* Advanced earnings analytics.
* Cooperative voting.
* Driver-to-driver communication.
* Shift planning.
* Taxi fleet management.
* Vehicle maintenance reminders.
* Document expiration reminders.
* Driver training resources.
* Cooperative financial dashboards.
* Driver scheduling.
* Shared dispatch zones.
* Accessibility-specific vehicle matching.

These should not be implemented before the core driver and ride systems are stable.

---

# 42. Core Driver Principles

### Principle 1 — Verification before dispatch

Only eligible drivers and vehicles may receive rides.

### Principle 2 — Availability is explicit

Being logged in does not mean being available.

### Principle 3 — Driver autonomy

Drivers should retain reasonable control over when and how they participate.

### Principle 4 — Transparency

Drivers should understand how rides, fees, and relevant performance systems work.

### Principle 5 — No opaque punishment

Automated systems should not silently determine a driver's livelihood.

### Principle 6 — Cooperative participation

The software should support meaningful driver participation in platform governance.

### Principle 7 — Privacy

Driver personal and location information must be protected.

### Principle 8 — Historical integrity

Important driver and ride events should be auditable.

### Principle 9 — Regulatory compliance

Driver eligibility and vehicle requirements must adapt to applicable regulations.

### Principle 10 — Human review

Serious account restrictions should provide appropriate human/cooperative oversight.

## Implementation boundary

Driver applications remain pending until a server-authorized administrator approves
them. Approval records a verification decision, activates the driver account, and
grants the `DRIVER` role; a driver cannot grant that role or approve their own
application through the mobile API.

The driver mobile product reads availability from the backend after session
restoration and sends online/offline requests only through the driver API. It
does not show a local toggle as successful until the backend returns the updated
availability state; rejected eligibility checks remain visible to the driver.

An authenticated account without the backend `DRIVER` role sees an explicit
driver-application action instead of availability controls. Submitting that action
creates the pending application through the driver API; verification and role
approval remain administrative backend operations.
