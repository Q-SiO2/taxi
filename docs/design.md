# TaxiMobile — Design and UI Guidelines

## Board alpha execution authorized — 15 October 2026

The owner now directs the earliest functional board alpha, authorizes application
implementation and TaxiMobile Railway staging changes/deployment, and requires
French, Arabic and English with concise copy. This supersedes the earlier
planning-only stop. The selected four-style contract remains in force; no further
palette approval is needed. Follow [the active board alpha checkpoint](board-alpha.md)
for execution and evidence. Native, integrated staging, device and release
acceptance must still be demonstrated.

## Selected visual direction — recorded 15 October 2026

The owner approved **Folded Streets, Street Press, Glazed Machine and Notepad**
as four complete user-selectable styles. The independent five-color theme menu
is withdrawn. Gradients/collage/grain are treatments inside the expressive styles,
not additional choices. Notepad is grayscale ruled utility, retaining meaningful
icons and main workflows while disabling decorative motion.

[The selected four-style contract](redesign/style-options.md),
[current preview](redesign/abstract-lab.html), [visual system](redesign/visual-system.md)
and [all-page coverage](redesign/style-coverage.md) supersede earlier identity,
palette, shape and motion prescriptions below. The dated rejection/research and
pending-style-selection notes are historical. No further palette confirmation is
needed. Native implementation/device evidence, complete delivery-plan execution,
hosted rehearsal and release gates remain separate; this records design selection.
Backend authority, privacy, accessibility and state/command rules remain in force.


## Latest owner correction — 14 October 2026

The owner further directs the art-free identity toward elaborate abstract motion,
moving color gradients and contrasted collage. Review the
[abstract lab](redesign/abstract-lab.html) and
[expression plan](redesign/abstract-expression.md).

The owner subsequently said they love the new interface treatments without the
main illustration. The current lab defaults to art-free UI and motion; large
illustrations are an optional unselected archive.

The owner rejected the graphical proposal, especially the incoherent city/taxi
scene, and requested a unique, unusual, illustrative and animated identity.
The existing five color directions are proposed themes, not distinct identities.
Review [redesign/identity-reset.md](redesign/identity-reset.md) and the
[new art-direction lab](redesign/identity-lab.html). Material, drawing, composition,
typography and 2D/2.5D/3D motion exploration are reopened. Prior recommendations
are unaccepted; structural every-page coverage remains useful. The identity goal
is active, and application implementation still awaits the complete selected plan.


## Owner-directed redesign review — latest 14 October 2026

The owner now requests broader graphical decoration and interesting animation.
The [expressive concept plan](redesign/expressive-motion.md) explores that visual
layer across the page inventory. Historical anti-decoration clauses below are
not a restriction on this authorized concept work. No app implementation or
domain-state change is authorized by a browser specimen.

The owner rejected the current experience, stopped rehearsal, authorized
unrestricted visual exploration and explicitly requested confirmation of a
complete plan before execution. Review [redesign/README.md](redesign/README.md).
This supersedes the earlier direction-refinement approval. The proposal may
challenge the fixed palette, typography, navigation and chrome in `ui.md`;
it does not override backend authority, privacy or domain contracts. Until owner
confirmation, preserve current application source and perform planning only.
After confirmation, reconcile normative UI/extended/operations visual rules as
UX-0 before implementing the selected system. Earlier identity-retention clauses
below describe the prior direction and must not force gold/navy into this review.

## Alpha UX recovery contract — 12 October 2026

The documented alpha wave now permits a substantial passenger/driver UX overhaul
within the established identity and authority rules. Evaluate entire journeys,
not just spacing/color patches. Passenger screens are map-first with one dominant
next action; driver screens make availability, GPS/network, offer/trip phase and
cash resolution immediately legible. Hide diagnostic UUIDs, raw UTC/routing and
administrative metadata from primary product copy; retain meaningful human trip
references and full backend audit records. Represent unavailable, uncertain and
pending states honestly; never show successful settlement from a local flag.

Use [ui.md](ui.md) for objective visual criteria and [roadmap.md](roadmap.md)
A-02–A-07/A-10 for delivery. Record visual-direction review and actual rendered
evidence separately from source tests. Representative operations polish is part
of A; redesigning every administration screen is not required before presentation.

## Current standing — 2026-09-03

The map-first Compose identity, shared components, passenger and driver flows,
localized English/French/Arabic content, RTL handling, graphical asset fallbacks,
applicant web, and operations web are present in source. This is not UX
acceptance: representative-device layout, screen-reader, keyboard, contrast,
reduced-motion, weak-network, browser, and real-user usability evidence remains
open. See [`gaps.md`](gaps.md).

## Purpose

Define the boundaries between product functionality and visual design.

The visual design should remain flexible while the application's interaction model remains consistent.

## Design Ownership

Interaction rules, backend-authoritative state presentation, and accessibility constraints live in this document.

The approved visual identity — colors, typography, branding, layout chrome, icons, motion, and screen composition — lives in `ui.md`.

The project owner retains final control over visual changes. Coding agents must follow `ui.md` when implementing UI polish and must not invent a competing palette, type system, or interaction language.

The map-first identity and national operations extensions are now implemented in
source. New work must extend that identity instead of reverting to a minimal
developer shell or inventing a competing visual system.

## Platforms

TaxiMobile is intended to support:

* Android
* iOS
* Desktop development/testing where useful
* Web tooling where required by the project

Shared business logic should remain separate from platform-specific UI.

## Core UX Principles

The application should prioritize:

* Clarity
* Speed
* Accessibility
* Minimal unnecessary interaction
* Clear ride status
* Clear pricing
* Clear driver information
* Reliable navigation

Account creation disables submission until the shared client checks pass and
shows a non-dismissible progress state while the backend request is in flight.
On success, both native apps return to sign-in, prefill the submitted email or
phone identifier, clear the password, and show an explicit confirmation. On
failure, they retain the account form and show the safe actionable network,
validation, conflict, or throttling message supplied by application state.

Signed-out recovery uses one previously saved offline code. The shared form is
localized, validates only input shape, submits through the backend gateway, and
always describes a reachable backend result conditionally so account/code
validity cannot be inferred. On accepted response it clears the recovery code
and new password before returning to sign-in. A network or request-shape failure
keeps the form but must never echo either secret.

Authenticated product actions use the same interaction rule. A synchronous
shared gate runs before coroutine launch, allows only one backend action at a
time, and rejects overlapping taps. The initiating control replaces its label
with the localized loading indicator while all competing backend controls are
disabled. Completion always releases the gate; it never implies success without
the backend response and authoritative reconciliation.
Only a non-error authenticated result emits shared success presentation. Cash
settlement and rating show the documented check animation and static confirmation;
support and vehicle drafts clear only after their creation is backend-confirmed.
Rejected or uncertain results retain the draft and never display success.

## Passenger Flow

The primary passenger flow should remain simple:

```text
Open app
   ↓
Choose point-to-point or browse fixed routes
   ↓
Choose pickup/destination or route direction
   ↓
Choose now or schedule (where enabled)
   ↓
Review fare
   ↓
Request taxi
   ↓
Wait for driver
   ↓
Track ride
   ↓
Complete ride
   ↓
Payment / confirmation
```

Published fixed routes are a persistent service-discovery surface, not a layer
of live taxi markers. Their direction, start, finish, static line, and flat fare
remain browsable when no driver is online. Scheduling adds pickup time, surcharge,
cancellation terms, and honest booking status to the existing review flow; it
does not introduce a different visual identity or imply guaranteed assignment.

## Driver Flow

```text
Open app
   ↓
Go online
   ↓
Receive ride offer
   ↓
Review ride
   ↓
Accept / decline
   ↓
Navigate to passenger
   ↓
Start ride
   ↓
Complete ride
   ↓
Confirm payment
```

Offers visibly identify immediate, fixed-route, or scheduled work. Fixed-route
offers show direction and flat fare; scheduled offers show pickup time,
commitment/cancellation terms, fee and expected net. The driver still chooses
Accept or Decline. Accepted future work appears in an upcoming list and does not
make the driver UI look actively on-trip before dispatch handoff.

## UI State

UI should reflect backend state rather than inventing its own authoritative state.

Coroutine cancellation must propagate through ride, immediate-offer and scheduled-booking reads
and commands, including both attempts of a bounded idempotent request. It must
not become a network-error state or trigger another attempt after cancellation.
An ordinary transport retry retains the exact original command/key. Cancelling
an immediate-offer operation also propagates; its transport keeps one attempt
and must not gain command retries through this rule. Cancelling
the caller does not establish that the backend rejected or cancelled a booking;
resume by reloading authorized backend state rather than inventing that outcome.
The [source correction](launch/journey-cancellation.md) retains this distinction.

For example:

```text
MATCHING
DRIVER_ASSIGNED
DRIVER_ARRIVING
RIDE_ACTIVE
RIDE_COMPLETED
```

The application should not display a driver as assigned until the backend confirms the assignment.

Before that assignment, the passenger experience must not display online taxi
markers, available-driver counts, candidate identities, queues, or supply
heatmaps. Matching is represented only as the passenger's request state. The
existing assigned-driver card and optional post-acceptance static last-known
marker remain the first point at which driver-specific data appears.

The initial shared Compose shell receives explicit render state from a coordinator:
session restoration, signed-out, offline, passenger-ready, and driver-ready. It
maps backend ride and driver status to accessible text and deliberately has no
local command that can advance a ride or make a driver available.

The signed-out state switches between login and account-creation forms and
submits only to the authentication coordinator. Registration explains the
backend's 12-character minimum and requires an email address or Moroccan phone
number before enabling submission. The form checks the same basic email and
accepted Moroccan-number shapes for immediate feedback, but the API repeats all
validation and remains authoritative. Password text is never logged, persisted as
UI state, or treated as evidence of a signed-in session; the screen advances only
after the backend validates the session and account role.
Registration failures distinguish duplicate identifiers, invalid form data, and
rate limiting with fixed actionable text. The client does not display raw
framework validation payloads or submitted values.

Authenticated passenger and driver views include an explicit sign-out control.
It always clears secure local credentials, attempts backend session revocation
when connected, and returns to the signed-out state even if that network call
cannot be completed.

The driver-ready view identifies the signed-in driver only with the display name
returned by the authenticated driver-profile API. It does not infer a driver
identity from a vehicle, a ride offer, or locally entered text.

The passenger-ready view includes a compact profile form limited to the
authenticated passenger's display name. It sends an explicit profile update to
the backend and refreshes server-confirmed state; it does not expose or edit
roles, contact identifiers, authentication credentials, or any other account.

Map events must dispatch to the latest Compose screen callback even when the
native renderer retains its original listener. The same mounted map must allow
new selection after trip completion and reject selection when a trip becomes
active. Recreating the Activity or coordinator is not a callback refresh strategy.
The native boundary keeps a stable callback adapter whose current target follows
recomposition; backend authority and the current active-trip guard remain intact.

MapLibre is the selected map renderer for Android and iOS. The passenger flow
should use an accessible MapLibre map to select pickup and destination, with clear
text summaries and a non-map fallback so the flow remains usable when location,
tiles, or rendering are unavailable. Validated latitude and longitude fields may
remain in development builds until the production style/tile source and mobile
permission flows are configured. The client asks the backend for a fare estimate,
discards that estimate whenever either point changes, and creates the ride only
through the authoritative ride API.

Read-only foreground/push/reconnect catch-up preserves the current quote input
identity while rereading the backend estimate and route. It must not replace a
reviewable quote with an empty projection and collapse Request during ordinary
session recovery. Retain session-owned point/direction inputs, not a client price
authority. Owner replacement or a new primary ride clears that intent; revoked
or invalid estimate inputs yield an explicit failure. Point changes still
invalidate the UI's reviewed quote, and no quote recovery may replay ride creation.
Navigation ownership remains stable during valid token rotation. Login/logout
changes it; realtime subscription generations still rotate independently so
sockets reconnect with current credentials.

The reviewed point pair must also be present in the passenger render projection
so a fresh native composition can initialize its form after activity entry. Seed
only the newly created form; an ordinary refresh must not replace newer local
point edits or make returned terms apply to a different pair. This projection
contains inputs only, retains their original precision/labels and adds no fare
cache or automatic ride command. It is not a general persistent draft store.

Route geometry and maneuver summaries come from the provider-neutral backend
routing contract backed by Valhalla. A map route is guidance, not evidence that a
ride progressed, a fare was finalized, or a payment succeeded.

Scheduled review must match the current requested instant and trip context before
it is displayed or submitted. Point requests bind city and exact coordinates;
fixed requests bind the immutable direction version. Equivalent explicit-offset
timestamps may identify the same instant, and normalized address labels may
differ. A stale response cannot authorize confirmation for another request, even
when its pricing versions remain current. The coordinator also rejects mismatches;
only an explicit new read can supply the matching backend review. See
[scheduled review binding](launch/scheduled-review-binding.md).

City-local input resolves civil date/time through the authenticated
[clock-planning read](launch/scheduled-local-input.md), without a quote or booking
command. Missing rules are unavailable, a gap yields no instant, and an overlap
requires a visible offset choice. Match each user-requested read and current
form/owner context before accepting options; retained data after a failed read
must not impersonate a new successful response. Only the selected explicit instant
enters the ordinary backend price/terms review. The later working source uses
native date/calendar and 24-hour time controls, explicit city selection and
presentation-only identities for clock and price reads. It retains typed Arabic
digit correction and clears read/review authority on refresh or recreation.
Platform and device acceptance remain separate from source implementation.

Once a ride is created, the passenger product reloads its authorized detailed
ride and renders the confirmed pickup, destination, route line, distance and
duration throughout the active lifecycle. Turn-by-turn maneuvers belong in a
driver navigation surface when actually implemented, not in the passenger's
primary booking or active-ride sheet. Server
refreshes replace status and assigned-driver data; route failure leaves those
authoritative facts visible and never invents driver movement.

After session restoration, the passenger product retrieves the passenger's rides
and renders a non-terminal backend-confirmed ride as active. Cancellation is
offered only for states permitted by the documented server-side state machine;
the final cancellation status always comes from the API.

Once the backend assigns a driver, the active passenger view presents the
authorized driver display name and bound vehicle make, model, color, and taxi
identifier where supplied. It never infers these details from an offer or shows
private driver information.

When no ride is active, both products display a compact backend-owned recent
ride history (up to ten status/identifier summaries). Detailed receipts, driver
identity, vehicle presentation, and route visualization remain authorized API
work for their corresponding product slices rather than client-side inference.

A selected history ride is local, session-owned navigation intent. Foreground,
push and reconnect catch-up must preserve that selection while loading its
current authorized ride and receipt/feedback again. Retain the identifier and
ownership context, not a cached payment or rating projection. Logout/account
replacement and a newly started primary ride clear the prior history intent;
a late old-session read must not reinstall it. Denied or removed history yields
an explicit error and forgets the inaccessible selection rather than presenting
a cached receipt or silently substituting success.

Ordinary passenger/driver history uses the same short eight-character reference
as the recent-ride row. Full UUIDs remain internal API/resource identifiers.
Prefer an authorized place label; when only a point is available, show at most
five decimal places. This is display formatting only: callback identifiers,
selected coordinates, routing, pricing and backend requests retain full precision.

For the most recent completed passenger ride, the app fetches and displays the
backend-finalized fare and payment method/status as a minimal receipt. It never
derives a final fare from the quoted estimate or from local distance data, and
does not present pending cash settlement as a successful payment.
For manual bank/M-Wallet transfer, `PENDING` permits a passenger claim and
`PROCESSING` means operator reconciliation is outstanding; neither is paid.
Only `COMPLETED` renders verified success. Recipient and payment-reference data
come only from the ride's backend snapshot, remain selectable/read-only, and are
never replaced with locally configured values. The app accepts no financial
credential or statement image.
When the receipt includes stored fare components, the app renders those values
without reconstructing a breakdown locally. The captured tariff version remains
in the backend record for audit; the passenger's primary fare hierarchy does not
expose its internal identifier.
When confirmed refunds exist, the receipt retains that original fare and renders
only backend-returned refunded total, net paid, currency, closed reason labels,
and refund rows. `REFUNDED` means the complete original payment was returned; it
does not mean the transfer was unverified or needs to be sent again. Evidence
references, administrator identity, and private notes never appear in passenger
presentation.

The driver product retrieves currently valid backend offers after availability
refresh. It displays pickup, approximate backend pickup distance/time, locked
estimated fare, and expiry information. It accepts or declines through the offer
API before reloading server-confirmed driver state. Offer actions are never
treated as successful solely because a button was tapped, and the client does
not reconstruct ranking scores.
Malformed or non-positive server timing fails closed: Accept is disabled, the
card states that timing is unavailable, and the app requests an authoritative
offer refresh instead of trusting the device clock or a raw timestamp.

An exhausted bounded search returns the passenger to the new-ride surface with
the `UNMATCHED` journey retained in history and the explicit status “No available
taxis were found nearby.” The app never claims that a driver is coming merely
because matching started.

The approved driver view exposes a compact vehicle-registration and selection
surface. It shows backend verification state and allows selection only after
the server has verified a vehicle; the application explains that registration
does not grant dispatch eligibility.

Both products render a compact notification inbox from the authenticated
backend history. Marking an item read is an explicit API action; the text and
resource ID are only a prompt to refresh authorized ride or driver data.
Foreground and background FCM callbacks feed the same bounded shared refresh
relay as a wake-up signal. If the app screen is active and authenticated, it
reloads the full product state through the API; otherwise normal startup/session
restore catches up. Push payloads never directly change a ride, offer,
availability, fare, payment, notification read state, or visible identity.

During an assigned active ride, both products show the latest backend-confirmed
coordination signal and three role-specific fixed actions. Passengers see pickup,
more-time, and cannot-find-driver choices; drivers see on-my-way, at-pickup, and
cannot-find-passenger choices. The component has no free-text or contact-number
surface. It is hidden before assignment and after terminal state, and unknown
future codes render through a safe generic fallback rather than exposing raw
backend values.

Cancellation and driver state-transition controls remain before coordination
actions so safety-critical progress is not displaced. While a signal is being
sent, only the initiating action shows loading; alternative choices remain
readable but disabled until authoritative refresh completes. Labels,
notifications, and latest-message presentation must remain semantically usable
in English, French, and Arabic/RTL, at large text sizes, and with TalkBack or
VoiceOver. Physical-device acceptance remains a release gate.

Both passenger and approved-driver views show up to ten of the authenticated
account's support-ticket summaries and provide the same minimal ticket form. The
client displays only its own category, subject, server-owned status, and latest
participant-visible response; it does not expose priority, assignment, internal
notes, another participant's information, or financial adjustments. Ticket
creation and refreshed history remain API-confirmed. An active ride may be sent
as an optional association; the backend still verifies participation.

Safety is a distinct section, not a support category. It binds a controlled
category and description to an active, selected, or recent backend ride, shows
only reporter-safe status/public messages, and warns that TaxiMobile reporting
is not an emergency service. The section remains complete without an optional
illustration or icon. It never displays the reported person, submitted safety
description after creation, internal notes, priority, responder, or deadline.
Both creation forms clear only after backend confirmation.

A backend-confirmed passenger cancellation immediately returns the app to the
new-ride flow and keeps the cancelled journey in history. The terminal ride must
not remain in the active-ride slot or require an app restart before another
request can be started.

For an active assigned ride, the driver UI exposes only the next documented
server transition: en route, arrived, start, then complete with an explicitly
reviewed completion coordinate. Android and iOS offer a one-shot foreground
location request after a user action. Driver completion uses the existing guarded
driver-observation callback, then presents its returned coordinate for explicit
completion. It must not fall back to the passenger's cached-coordinate lookup or
turn acquisition into an automatic completion command. While backend-confirmed online, the same
authorized one-shot adapter is scheduled only in the foreground and the UI tells
the driver to keep the app open; it never requests permission automatically or
starts background tracking. Manual coordinate entry is a visible fallback only
when enabled for that build. The map-only board build must offer an actionable
location retry instead of instructing entry into hidden fields. Cash settlement remains
a separate, explicit confirmation after completion and is never inferred from the
ride-completion action.
The current-location control is disabled and shows loading while its one-shot
platform request is pending. Repeated explicit taps are ignored; they must not
cancel or replace the callback owned by the first explicit request. In Android,
an explicit driver lookup takes priority over automatic sampling: cancel the
automatic lookup, suppress its cancellation warning, and defer new automatic
requests until the explicit callback finishes. Foreground/context/freshness
validation still applies to the returned observation. This does not authorize
cached coordinates or automatic completion.

The passenger can use the same one-shot platform location flow to set pickup,
then choose the destination on MapLibre or through validated coordinate fields.
Permission denial keeps the map/manual flow usable and displays an actionable
message. The driver reviews the returned coordinate and explicitly submits it
before going online or completing a ride. Shared code forwards the native
observation time and accuracy unchanged when posting a driver update; backend freshness and movement validation remain
authoritative.

The latest backend-accepted foreground coordinate remains available only for the
current signed-in app process. This prevents a normal availability, offer, or
ride refresh from erasing the driver's MapLibre/Valhalla guidance. Signing out
clears it, and a refresh never turns it into a client-authoritative availability
or dispatch decision.

“Go online” remains a separate action and fails visibly if that accepted location
has become stale. Loading a phone coordinate into the form does not change driver
availability, and submitting it does not itself make the driver dispatchable.
After online entry, unavailable automatic observations produce an actionable
localized warning and a 60-second retry backoff; the UI never implies that an old
coordinate remains eligible.

## Accessibility

The UI should account for:

* Readable text
* Sufficient contrast
* Touch-friendly controls
* Screen readers where applicable
* Clear status indicators
* Avoiding color as the only source of information

The shared product screen must remain vertically scrollable. Passenger receipts,
support history, and the driver vehicle/ride controls can all coexist in one
backend-confirmed state, so controls must not become unreachable on a small
screen simply because the view has more content than the viewport.

Fixed-route direction must be communicated by ordered start/finish text and not
only by a map arrow. Scheduled date/time, city timezone, surcharge, operator fee,
driver net, and cancellation status require text labels and screen-reader order.

## Operations Web Experience

The national operations console extends the approved identity rather than
redesigning it. It uses the same navy/mustard/white palette, typography,
feedback semantics, icon family, restrained MapLibre style, and backend-confirmed
success behavior. Desktop administration may use a persistent sidebar, city
scope switcher, tables, map editors, charts, and side drawers rather than mobile
bottom sheets.

Every protected page visibly identifies the active market/operator/city scope.
Changing the visual scope triggers a backend-authorized reload; it does not grant
access. Draft versus active configuration, unsaved edits, review state,
effective time, and activation impact must be clear. Destructive or public-impact
actions such as city pause, rate activation, route publication, grant change, or
driver rejection require a review/confirmation step and backend-confirmed result.

The public driver web portal uses the same applicant flow and status language as
the driver app. It must not expose operations navigation or suggest that form
completion equals approval.

## Design Constraint

Do not add unnecessary screens, animations, features, or UI complexity merely because they are common in other ride-hailing applications.

TaxiMobile should remain focused on its actual users and requirements. When polish is scheduled, implement only the motion and interaction set defined in `ui.md`, and keep decorative work out of business-rule slices.

## UI delivery gate

Keep UI work separate from business-rule changes. Reuse existing Compose conventions and documented flows. Visual identity and navigation chrome follow `ui.md`; do not invent a second brand system. Every screen must account for loading, empty, error, offline, and backend-confirmed states, with accessibility considered in the same slice.

The shared `Offline` screen presents an explicit `Retry connection` action. Retry
does not replay the failed ride, payment, availability, or profile command. It
re-runs secure session restoration and reloads backend-authoritative product
state; a retained valid session returns to the appropriate passenger/driver
screen, while an absent or rejected session returns to sign-in.
