# TaxiMobile — Extended UI/UX Specification

## 0. Purpose

This document defines the complete visual, interaction, layout, validation, motion, and state-management specification for the TaxiMobile product.

The product is a Kotlin Compose Multiplatform taxi-service application with:
- a Passenger experience,
- a Driver experience,
- city taxi services,
- larger/shared or intercity taxi services,
- map-based pickup and route selection,
- service discovery and backend-authorized post-assignment driver tracking,
- payment handling,
- ride history and account management.

The primary design goal is to replace a simplistic, form-heavy, developer-default interface with a deliberate, consumer-grade product that feels coherent, dynamic, trustworthy, and specifically designed for taxi use.

The design must not rely on generic text areas, static forms, arbitrary spacing, or default platform controls where a purpose-built interaction is more appropriate.

## 0.1 Authority and implementation boundary

This document is the detailed screen and component companion to `ui.md`. Its
mustard, navy, and white visual system supersedes the earlier blue-accent values
in `ui.md`; the two documents must be kept synchronized. It does not override
backend authority, domain state machines, security, privacy, or roadmap gates.

A screen may expose only capabilities supported by the documented API. CMI and
other hosted-card entry, OTP verification, saved places, continuous
tracking, general-purpose image upload, messaging, emergency integration, and
service-category selection remain unavailable until their corresponding product
and backend contracts are approved. The exception is the implemented protected
driver city-application PDF/JPEG/PNG workflow described in D02; it remains hidden
when storage/scanning is unconfigured. Reusable controls may exist without being
connected to fake actions or invented success states.

Provider-neutral address/landmark search and explicit reverse geocoding are now
implemented behind authenticated backend routes. They remain behind a collapsed
“Find a place” launcher until used, debounce text by 450 ms, offer an explicit
retry, distinguish result types, show attribution and pickup-area eligibility,
and preserve exact coordinates. Provider failure always retains map and
manual-coordinate selection. Production provider/license/coverage acceptance
and saved Home/Work persistence remain open gates.

**Current standing (2026-09-03):** the passenger, driver, applicant, and national
operations surfaces described here are broadly implemented in source. Any item
marked “delivered” means source-delivered only. Browser/device accessibility,
usability, protected-document, production-provider, and real-workflow acceptance
remain open and are enumerated in [`gaps.md`](gaps.md).

## 0.2 Required asset fail-safes

- Optional illustration and vehicle assets must have a bundled code-drawn or
  geometric fallback with an accessibility description.
- Missing map sprites, glyphs, or provider style data must never crash a screen.
  The app falls back to a dependency-free neutral style, retains route and point
  overlays, explains the limitation, and exposes manual coordinate entry.
- Missing optional profile or document images render a labeled placeholder; they
  never remove the associated action or status.
- Loading failures retain backend-confirmed text and actions. The interface must
  not imply that an unavailable decorative asset means business data is absent.

---

# 1. Core Product Design Principles

## 1.1 High contrast without visual aggression

The main palette is:
- White
- Navy blue
- Mustard yellow

The interface should feel:
- clean,
- premium,
- legible,
- civic and transport-oriented,
- trustworthy,
- practical rather than playful,
- visually bold without becoming loud.

The navy carries structure and seriousness.
The mustard yellow carries action, taxi identity, route emphasis, and selection.
White gives breathing room and prevents the dark navy from making the product feel heavy.

## 1.2 Every field must understand what it is

Do not use generic text inputs for specialized data.

Examples:
- Phone numbers use a phone-number component.
- Email uses an email component.
- OTP uses a segmented code-entry component.
- Manual bank/M-Wallet transfer uses backend-issued, read-only recipient and
  payment-reference fields plus one optional constrained payer reference. It
  never requests credentials, OTPs, or statement screenshots.
- Any future card payment uses the approved provider-hosted entry surface;
  TaxiMobile forms do not render card-number or CVV inputs.
- Search locations use a location-search component.
- Driver document numbers use constrained field formats.
- Dates use date pickers.
- Times use time pickers where relevant.
- Numeric values use numeric keyboards and formatting.

Every input must define:
- accepted character set,
- keyboard type,
- formatting,
- auto-capitalization rules,
- autofill hints,
- inline validation,
- empty state,
- focus state,
- error state,
- valid state,
- disabled state,
- read-only state where necessary.

## 1.3 The map is a product surface, not a background image

The map must react to:
- pickup selection,
- destination selection,
- route previews,
- service choice,
- bottom-sheet expansion,
- driver discovery,
- active ride,
- GPS quality,
- map rotation,
- driver heading,
- pickup confirmation.

Map controls must not overlap sheets, important markers, or system UI.

## 1.4 Page states are part of the design

Each screen must include:
- loading,
- empty,
- error,
- offline,
- unavailable,
- permission-denied,
- partial-data,
- retry,
- success,
- transition states.

A polished app is defined as much by its uncommon states as by its ideal path.

## 1.5 Motion communicates state

Animation is functional.

Use motion to explain:
- where a sheet came from,
- that a route was calculated,
- that a taxi has been found,
- that a location changed,
- that the map camera is following a moving vehicle,
- that a payment succeeded,
- that a ride changed phase.

Avoid decorative motion that competes with navigation.

---

# 2. Color System

## 2.1 Primary palette

### White
- `#FFFFFF`
- Main surfaces
- Cards
- Sheets
- Input backgrounds
- High-contrast text on navy/yellow only where appropriate

### Navy Blue
Primary navy:
- `#0B1F3A`

Usage:
- Primary text
- Main dark surfaces
- Top bars
- Key icons
- Navigation emphasis
- Driver status surfaces
- Selected labels

Secondary navy:
- `#163A63`

Usage:
- Hover/pressed overlays
- Secondary dark surfaces
- Map-control backgrounds
- Info banners

Deep navy:
- `#071426`

Usage:
- High-emphasis overlays
- Fullscreen emergency/help states
- Night-mode-adjacent elements if added later

### Mustard Yellow
Primary mustard:
- `#D6A800`

Usage:
- Primary CTA backgrounds
- Active taxi selection
- Route accents
- Important chips
- Vehicle category highlights
- Focus indicators

Light mustard:
- `#F3D76A`

Usage:
- Selected-card backgrounds
- Highlight strips
- Secondary emphasis

Dark mustard:
- `#9B7900`

Usage:
- Pressed CTA states
- Yellow text/icons where stronger contrast is needed

## 2.2 Supporting neutrals

Light background:
- `#F6F8FB`

Soft border:
- `#D9E0E8`

Muted text:
- `#667085`

Strong text:
- `#101828`

Disabled fill:
- `#EAECF0`

Disabled text:
- `#98A2B3`

Success:
- `#168A52`

Error:
- `#C9362B`

Warning:
- `#B86A00`

Informational:
- `#2D66C3`

## 2.3 Color-role rules

Never use mustard for long body text.

Mustard is for:
- CTA surfaces,
- small accents,
- markers,
- selected tabs,
- route highlights,
- taxi identifiers.

Navy is the primary reading color.

White is the dominant canvas.

Error and success colors must remain semantically consistent and must not be replaced by mustard/navy just to preserve branding.

---

# 3. Typography

Use one sans-serif family consistently across platforms where licensing and rendering are stable.

Recommended hierarchy:

## Display
- 32 sp
- Bold/Semibold
- Landing page headline only

## H1
- 28 sp
- Bold

## H2
- 24 sp
- Semibold

## H3
- 20 sp
- Semibold

## Title
- 18 sp
- Semibold

## Body Large
- 16 sp
- Regular
- 24 sp line height

## Body
- 14 sp
- Regular
- 20 sp line height

## Label
- 13 sp
- Medium

## Caption
- 12 sp
- Regular/Medium

## Numeric emphasis
- 20–28 sp depending on context
- Semibold
- Used for fares, ETA, totals, and earnings

Typography rules:
- Avoid ALL CAPS except very short status chips.
- Never use more than three font weights on one screen.
- Minimum standard body size: 14 sp.
- Buttons should use 15–16 sp Medium/Semibold.
- Input labels should not disappear after typing; use persistent labels or floating labels.

---

# 4. Spacing and Layout System

Base spacing unit: 4 dp.

Allowed spacing values:
- 4
- 8
- 12
- 16
- 20
- 24
- 32
- 40
- 48
- 64

Default horizontal page padding:
- phones: 20 dp
- compact displays: 16 dp minimum

Cards:
- internal padding: 16–20 dp

Bottom sheets:
- horizontal internal padding: 20 dp
- top content padding after handle: 16 dp

Section gaps:
- tightly related content: 8–12 dp
- normal content blocks: 16–20 dp
- major sections: 24–32 dp

Touch targets:
- minimum 48 x 48 dp

---

# 5. Shape System

Small radius:
- 8 dp
- status chips, compact controls

Medium radius:
- 12 dp
- inputs, secondary buttons

Large radius:
- 16 dp
- main cards

Extra large:
- 24 dp
- bottom sheets, large modal surfaces

Pill:
- 999 dp
- segmented status controls, compact chips

Do not randomly mix radii.

---

# 6. Elevation and Surface Hierarchy

Use subtle elevation.

Level 0:
- flat page surface

Level 1:
- input container
- secondary card
- compact toolbar

Level 2:
- floating map control
- taxi/service selection card
- sticky action area

Level 3:
- modal bottom sheet
- active ride panel

Level 4:
- dialogs
- critical actions

Avoid heavy drop shadows.
Favor:
- subtle shadow,
- border,
- tonal separation.

---

# 7. Buttons

## 7.1 Primary button

Background:
- Mustard `#D6A800`

Text:
- Deep navy `#071426`

Height:
- 54 dp

Radius:
- 14 dp

Horizontal padding:
- 20 dp minimum

States:
- Default
- Pressed: dark mustard
- Disabled: disabled fill + disabled text
- Loading: spinner replaces or accompanies text
- Success: optional short success transition only if needed

Rules:
- Only one primary action per major panel.
- Full width for onboarding/auth flows.
- In ride screens, may be sheet-width.

## 7.2 Secondary button

White background
Navy border
Navy text

## 7.3 Tertiary button

Text-only or icon + text
Navy
No filled background

## 7.4 Destructive button

Use semantic error red.
Do not use mustard for destructive actions.

---

# 8. Input System

## 8.1 General field anatomy

Each input may contain:
- persistent label,
- input text,
- leading icon,
- optional trailing icon,
- helper text,
- error text,
- validation indicator.

Height:
- 56 dp normal
- 64 dp when helper/action is embedded

Default:
- White or very light neutral background
- 1 dp soft border

Focused:
- 2 dp navy or mustard focus border
- label navy

Error:
- error border
- error text below
- optional error icon

Disabled:
- muted fill
- no keyboard opening
- muted label

## 8.2 Phone number field

Must not be a generic text box.

Structure:
- country selector segment
- country flag optional
- dialing code
- formatted national number area

Default Morocco behavior:
- preselect `+212`
- numeric phone keyboard
- strip unsupported characters
- normalize pasted input
- handle user pasting:
  - `0612345678`
  - `+212612345678`
  - `212612345678`
  - spaced numbers
- format visually without corrupting the stored normalized number

Validation:
- validate expected structure before enabling Continue
- do not wait until server failure
- show concise error below field
- allow correction without wiping input

Recommended visual example:
`+212 | 6 12 34 56 78`

## 8.3 Email field

Keyboard:
- email-address keyboard

Behavior:
- no auto-capitalization
- no smart punctuation
- trim leading/trailing spaces
- reject spaces inside address
- normalize safely
- provide autofill metadata
- show inline validity after meaningful input

Do not overvalidate with impossible regex rules.
Allow common valid addresses.

## 8.4 Password field

If password auth is used:
- obscured text
- show/hide icon
- password manager/autofill support
- rule feedback
- Caps Lock handling where available

## 8.5 OTP field

Use 4–6 visually separated slots depending on backend.

Behavior:
- numeric keyboard
- paste entire code
- SMS autofill where platform supports it
- automatically advance focus
- backspace moves backward
- submission occurs automatically on complete valid code, or enables Verify
- resend timer with clear countdown

---

# 9. Navigation Architecture

Passenger bottom navigation should not appear during:
- onboarding,
- authentication,
- active booking flow,
- active ride.

Recommended passenger top-level destinations:
- Home
- Trips
- Saved
- Account

Driver top-level destinations:
- Home/Go Online
- Earnings
- Trips
- Account

Do not overcrowd bottom navigation with five unrelated items.

---

# 10. Passenger Application — Screen Map

## P00 — Splash

Purpose:
- app initialization
- authentication restoration
- lightweight branding

Visual:
- white background
- centered logo mark
- optional tiny navy wordmark
- subtle mustard accent

Duration:
- only as long as initialization requires
- never artificially delay startup

Loading:
- small progress indicator if initialization is not immediate

Transitions:
- signed out -> Landing
- signed in -> Passenger Home
- unresolved session -> recovery/error state

---

## P01 — Landing / Welcome

This screen must exist.

Goal:
- explain the service immediately
- separate sign-in and new-user paths
- create visual identity

Layout:
- top 55–60%: illustration or branded transport composition
- bottom 40–45%: headline, short copy, actions

Headline:
- concise
- transport/value oriented

Actions:
- Primary: Continue / Create account
- Secondary: Sign in

Optional:
- language selector in top corner
- legal links in compact footer

Graphic:
- white base
- navy city/map geometry
- mustard taxi highlight
- avoid generic stock-photo aesthetics

Motion:
- very subtle parallax or route-line reveal at entry
- keep startup smooth on low-end devices

---

## P02 — Authentication Method

Goal:
- allow phone-first login
- optional email alternative

Preferred:
- phone as primary
- email as secondary

Components:
- back button
- title
- explanation
- phone field
- Continue
- alternative email action

Do not show unrelated social-login providers unless actually supported.

---

## P03 — Phone Entry

Use specialized phone component.

Additional rules:
- country selector opens searchable modal
- Morocco default
- Continue disabled until structurally valid
- server/network errors appear separately from formatting errors

Error examples:
- invalid number
- too short
- service unavailable
- too many attempts

---

## P04 — OTP Verification

Header:
- Verify your number
- masked destination number

Code slots:
- centered
- large enough for thumb use

Actions:
- resend code with timer
- change number

States:
- waiting
- autofilled
- invalid code
- expired code
- retry lock
- verification loading
- verified

Motion:
- short success transition after verification

---

## P05 — Email Authentication

Specialized email field.
If login link:
- show sent-link state.
If code:
- use verification code UI.
If password:
- use password field and recovery flow.

The implemented password recovery path is provider-independent and requires a
previously saved offline code. The signed-out passenger and driver shells expose
email/phone identifier, full recovery code, and new password fields in EN/FR/AR.
Submit is shape-gated, secret fields are cleared after the generic accepted
response, and the message never confirms account existence or code validity.
The recovery path must not be presented as email/phone verification. Passenger
and driver account panels now expose password-reauthenticated code creation,
one-time code display, session list/confirmed revocation, and password change.
One-time code display now requires a saved-all-codes checkbox before **Clear
codes from this screen** removes the secret bundle from render state. No
automatic clipboard copy is offered. A reviewed physical-device secure-save,
background/process-death, accessibility, screenshot and secret-lifecycle test
remains required before deployment acceptance.

---

## P06 — Basic Profile Setup

Fields:
- first name
- last name
- optional profile image
- optional preferred language

Names:
- text keyboard
- capitalization appropriate
- reasonable max length

Photo:
- optional
- camera/gallery choices only after user action

Primary CTA:
- Continue

---

## P07 — Location Permission

Do not immediately show the OS permission dialog.

First show an explanatory screen:
- why location is needed
- what improves with permission
- privacy reassurance without overclaiming

Primary:
- Enable location

Secondary:
- Not now

If denied:
- explain limitations
- allow manual pickup selection

If permanently denied:
- provide open-settings action

---

## P08 — Notification Permission

Explain:
- driver arrival
- booking status
- ride updates

Request after explanation.

Do not block app use permanently if notifications are denied.

---

# 11. Passenger Home / Map

## P10 — Idle Home

Primary surface:
- full-screen map

Overlay elements:
- top account/location status
- destination search launcher
- recenter control
- service-status information if needed
- bottom sheet / compact panel

Map behavior:
- center on user after permission and fix
- avoid extreme zoom
- show user location with accuracy ring where meaningful
- keep marker size stable relative to screen, not map zoom

Search launcher:
- large white card
- 56 dp height minimum
- location/search icon
- placeholder such as “Where to?”
- favorite shortcut optionally inside trailing area

Bottom panel:
- recent places
- saved Home/Work
- published fixed routes for the selected city
- promotion only if actually useful

The passenger home never exposes online taxi markers, counts, queues, or live
supply status. Published route cards remain useful when no taxi is online and
show direction/start/finish/flat fare without implying availability.

Do not clutter the map with promotional banners.

---

# 12. Location Search

## P11 — Destination Search

Structure:
- top pickup field
- destination field in focus
- search results list
- saved places
- recent destinations

Behavior:
- debounce input
- show loading state
- distinguish exact address from POI
- highlight matched text sparingly

Result row:
- location icon
- primary place name
- secondary address/area
- optional distance

Keyboard:
- search/action key

Empty:
- “No places found”
- offer map selection

Offline:
- explain search unavailable
- retain recent/saved places if local data exists

---

# 13. Pickup Selection

## P12 — Pickup Pin Map

Visual:
- map
- center-fixed pickup pin
- address confirmation sheet

Critical distinction:
The map moves beneath the pin.
The pin should not jump every frame with the map.

Map camera:
- user drags map
- reverse geocoding updates after movement settles

Bottom sheet:
- selected pickup address
- optional pickup note
- Confirm pickup CTA

Pin:
- vertical anchor at bottom tip
- optional subtle lift/drop animation when map begins/stops moving

---

# 14. Route Preview

## P13 — Pickup + Destination Preview

Map:
- route polyline
- pickup marker
- destination marker
- camera fitted to route with safe padding accounting for sheet height

Bottom sheet:
- origin
- destination
- ETA
- approximate route distance
- Edit locations

Polyline:
- navy base or secondary navy
- mustard highlight can indicate active segment / selected path
- strong enough to read over map tiles

Do not crop route behind bottom sheet.

---

# 15. Taxi / Service Selection

## P14 — Service Picker

This is one of the product's key screens.

Potential categories:
- Standard city taxi
- Large/shared taxi
- Intercity taxi
- future premium/accessibility categories if supported

Each service card:
- vehicle asset/illustration
- service name
- passenger capacity
- route-duration estimate when available; never a pre-assignment pickup ETA or
  live-supply signal
- estimated fare or fare rule
- concise descriptor

Selected card:
- mustard-accented border/background
- clearly elevated
- vehicle artwork may gain subtle motion

Unselected:
- white surface
- soft border

Horizontal carousel is acceptable only if:
- card widths are large enough,
- partial next card indicates scrolling,
- all categories are discoverable.

Otherwise use vertical cards.

Large/shared taxi must be visually distinct from normal taxi:
- different vehicle silhouette
- passenger capacity indicator
- fixed-route/shared label where applicable

### P14A — Fixed Route Directory and Direction

Use the same map, cards, typography, and bottom-sheet system.

Directory rows show:
- localized route name,
- explicit outbound/inbound direction,
- start → finish,
- flat fare and currency,
- active/paused booking status.

Detail shows static route geometry and ordered stops. Route direction must be
readable in text and screen-reader order, not only color or arrow direction.
Never add taxi markers or online-driver counts to this catalog. Book now and
Schedule appear only when the backend city catalog enables them.

---

# 16. Fare Breakdown

## P15 — Fare Details

Show:
- base estimate
- distance/time estimate
- supplements if applicable
- shared/fixed-route logic when relevant
- payment method

Do not hide materially important pricing information behind obscure icons.

If final fare is metered rather than fixed:
- state that clearly.

---

# 17. Payment Selection

## P16 — Payment Method

Methods may include:
- Cash, always when rides are bookable
- Bank/M-Wallet transfer, only when advertised by the fare estimate
- Provider-hosted card or saved card only in a later approved release

Each method:
- icon
- label
- short, honest status or timing
- selected indicator
- full-row tap target and radio semantics

The list comes from the backend's `payment_methods` estimate field. The client
must not render `MANUAL_TRANSFER`, `CARD`, or `MOBILE_PAYMENT` from local feature
assumptions. If a selected capability disappears before confirmation, retain the
form, explain the server rejection, and require a new estimate/selection.

Bank/M-Wallet transfer selection explains that:
- the transfer occurs in the passenger's own external bank/wallet service after
  ride completion,
- TaxiMobile charges no gateway fee but an external institution may charge one,
- submitting a reference starts review and does not mean paid,
- cash is the fallback for a new ride when transfer is unavailable.

The finalized transfer receipt shows:
- exact fare amount and currency,
- read-only recipient name,
- bank account and/or M-Wallet identifier,
- prominent backend-issued `TM-...` reference,
- instruction to include that reference where the external service permits,
- one optional 3–80 character payer reference constrained to ASCII letters,
  digits, `.`, `_`, `/`, and `-`,
- `Submit for review` only while authoritative status is `PENDING`.

Submission changes presentation to `PROCESSING` with clear “awaiting operator
verification” copy. It must not trigger paid artwork, a success receipt, or a
driver earning animation. Only an authoritative `COMPLETED` response renders
verified/paid. A safe latest-claim `REJECTED` status returns to pending with an
actionable generic retry/support message; ordinary passenger UI does not expose
internal reason text, reviewer identity, or raw statement evidence.

After an authorized refund, the same receipt preserves the original fare and
shows the authoritative refunded total, net paid amount, and localized reason for
each confirmed refund. Full `REFUNDED` status is informational, not a failed or
retryable transfer state. Never expose settlement references, private operator
notes, reviewer identity, or support-case text.

Never add card, bank-password, wallet-PIN, OTP, statement-login, or screenshot
fields. If immutable transfer instructions are missing, show a bounded service
error and support path; never substitute the deployment's current account or
invent success.

Any future hosted-card entry:
- opens the configured provider-controlled HTTPS payment experience,
- keeps card number, expiration, CVV, and cardholder entry outside TaxiMobile,
- treats the return as pending until the backend verifies and reconciles it,
- offers a safe return/retry or cash path without displaying invented success.

Never simulate security with fake shield graphics or unsupported claims.

---

# 18. Booking Confirmation

## P17 — Confirm Ride

Map route remains visible.

Bottom sheet:
- chosen service
- pickup
- destination
- fare estimate
- payment method
- optional note
- Now / Schedule choice when enabled
- scheduled pickup time and city timezone when selected
- scheduling surcharge and cancellation/refund terms
- operator service fee as a separate line when passenger-funded

Primary:
- Request taxi

Secondary:
- edit relevant fields

Prevent accidental duplicate booking:
- CTA enters loading state immediately after valid submission

---

# 19. Finding Driver

## P18 — Searching

Map:
- pickup/destination remain visible
- no online, candidate, queued, or simulated taxi markers before assignment

Bottom sheet:
- “Finding a driver”
- animated progress
- service selected
- estimated search duration only if meaningful and reliable
- cancel action

Animation:
- route/pickup pulse
- soft radar-like search visualization is acceptable
- never represent the pulse as real driver movement or supply

States:
- searching
- expanded search radius
- delayed
- no drivers
- connection lost
- user cancelled
- driver matched

No-driver state:
- try again
- change service
- modify pickup
- optional alternative service

---

# 20. Driver Matched

## P19 — Driver Assigned

Map:
- driver marker
- pickup marker
- route from driver to passenger
- camera framing both

Sheet:
- driver name
- rating
- taxi identification
- vehicle type
- license plate where appropriate
- ETA
- Call
- Message
- Safety/help
- Cancel

Vehicle marker:
- heading-aware
- anchor at actual ground center
- rotate only vehicle artwork, not label bubble
- orientation must match map bearing rules

---

# 21. Driver Approaching

## P20 — Approach Tracking

Map:
- show only the backend-authorized static last-known observation after assignment
- label its observation time
- replace it only after an explicit authoritative refresh
- do not interpolate, project, or label it as live movement

ETA:
- update without flickering
- avoid second-by-second instability

Sheet:
- ETA emphasized
- pickup point
- driver details collapsed
- contact actions

Notification when:
- nearby
- arrived

---

# 22. Driver Arrived

## P21 — Pickup Ready

Visual:
- stronger mustard status banner
- “Your taxi has arrived”

Sheet:
- driver/taxi details
- exact pickup landmark if available
- waiting status
- contact actions

Optional:
- PIN or ride verification code if backend uses one

---

# 23. Active Ride

## P22 — In Ride

Map:
- user follows route
- camera can switch between follow and free-pan
- route progress visible

Bottom panel:
- destination
- remaining ETA
- ride status
- safety
- share trip if implemented
- payment method

Do not expose unrelated booking controls.

Recenter:
- visible when user pans away
- disappears when following again

---

# 24. Ride Completion

## P23 — Arrival

State transition:
- route tracking ends
- map zooms to destination appropriately

Sheet:
- trip complete
- fare total
- payment status
- receipt action
- rate driver

If cash:
- clear “Pay driver in cash” status
- confirmation behavior only if backend requires it

If bank/M-Wallet transfer:
- `PENDING`: show immutable instructions and submit-for-review action
- `PROCESSING`: show operator review pending, not paid
- `COMPLETED`: show verified payment
- rejected/failed: show correction, support, or permitted alternative path

If a future provider-hosted electronic method is enabled:
- payment progress
- backend-verified success
- failure + safe retry / permitted alternative method

---

# 25. Rating

## P24 — Rating Driver

Components:
- driver summary
- 5-star control
- optional quick tags
- optional comment

Tags:
- Clean vehicle
- Professional
- Safe driving
- Friendly
- Easy pickup
- Other

Low rating may reveal issue-reporting options.

Do not force a written explanation.

---

# 26. Ride History

## P25 — Trips

List grouped by date.

Trip card:
- origin
- destination
- date/time
- service type
- fare
- status

Statuses:
- Completed
- Cancelled
- Failed
- Refunded where relevant

Tap -> trip details.

Empty state:
- branded illustration
- direct link to book first ride

---

# 27. Trip Details

## P26

Show:
- map thumbnail/route
- pickup
- destination
- timestamps
- driver
- taxi/service
- fare breakdown
- payment method
- receipt
- support/report issue

---

# 28. Saved Places

## P27

Default:
- Home
- Work

Custom saved places:
- label
- address
- icon

Editing:
- location search
- map confirmation

---

# 29. Passenger Account

## P28

Sections:
- profile
- phone/email
- saved places
- payments
- language
- notifications
- privacy
- safety
- help
- legal
- log out

Do not dump every setting into one undifferentiated list.

Use section headers and clear grouping.

---

# 30. Profile Editing

## P29

Editable:
- first name
- last name
- photo
- optional profile data

Phone/email changes require reverification.

---

# 31. Help and Safety

## P30

Emergency/help UI must be:
- easy to find during rides
- distinct from normal support
- explicit about what each action does

Implemented actions:
- create ordinary support for an active or optional authorized ride,
- create a separate safety report for an active, selected, or recent authorized
  ride,
- choose a controlled safety category,
- review reporter-safe status and participant messages.

The surface says TaxiMobile reporting is not an emergency service and directs a
person in immediate danger to move to a safe place and contact local emergency
services. It does not claim to place a call, dispatch help, share a trip, upload
evidence, or open messaging because those integrations are not implemented.
Optional safety artwork may be absent; text, warning tone, fields, and controls
remain complete and accessible.

---

# 32. Driver Application — General Principles

Driver UI has different priorities:
- glanceability,
- large touch targets,
- minimal reading while driving,
- status clarity,
- fewer interactions during vehicle movement,
- clear online/offline state,
- high contrast.

Driver home should not visually copy the passenger home.

---

# 33. Driver Onboarding

## D00 — Driver Welcome

Branding consistent with passenger app.

Primary:
- Become a driver / Continue application

Explain:
- key requirements
- basic workflow
- verification expectation
- that eligibility is reviewed for a selected recruiting city

---

## D01 — Identity Details

Specialized fields for:
- full name
- phone
- email
- date of birth
- identity document data where legally required
- recruiting city selection from the backend catalog

Use correct keyboard and formatting per field.

---

## D02 — Document Upload

Each document type gets its own card:
- ID
- driver license
- taxi license/authorization
- vehicle registration
- insurance
- additional permits where necessary

States:
- not uploaded
- uploaded
- processing
- approved
- rejected
- expired

Rejected:
- show exact reason if backend provides it
- re-upload action

Image capture:
- guidance frame
- blur/glare warning if supported

---

## D03 — Vehicle Setup

Fields:
- taxi category
- make
- model
- year
- plate
- passenger capacity
- color
- service eligibility

Large/shared taxi uses distinct category assets.

---

## D04 — Application Status

Timeline:
- submitted
- under review
- additional information
- approved
- rejected
- withdrawn

No vague infinite spinner.

An editable pre-approval application offers **Withdraw application** behind a
confirmation step. The UI keeps the withdrawn record/status and never presents
withdrawal as document deletion or account removal.

When a driver has more than one city application, each status is scoped and
named. Approval in one city must not visually imply national eligibility.

---

# 34. Driver Home

## D10 — Offline

Map:
- location context

Primary status control:
- large “Go online”

Supporting:
- today's earnings
- completed trips
- driver alerts

Mustard CTA on white/navy framework.

---

## D11 — Online / Available

Status:
- clearly ONLINE
- navy surface with mustard active indicator

Map:
- current position
- demand zones only if based on actual platform data

Primary:
- Go offline

Avoid distracting decorative widgets.

---

# 35. Incoming Ride Request

## D12

Critical high-attention screen.

Show:
- pickup area
- pickup distance
- estimated time to pickup
- destination visibility depending on platform rules
- ride/service type
- fare/earning estimate if available and appropriate
- passenger rating if used
- immediate / fixed-route / scheduled service label
- fixed-route direction/start/finish and flat fare when applicable
- scheduled pickup time/timezone and commitment/cancellation terms when applicable
- separate scheduling surcharge, operator fee/funding mode, and expected driver net

Actions:
- Accept
- Decline

Timer:
- visual countdown ring/bar
- must not create panic
- accessible numerically

Accept button:
- large mustard
- easy thumb reach

---

# 36. Navigation to Pickup

## D13

Map-first.

Top:
- next maneuver / navigation context if in-app navigation is implemented

Bottom:
- passenger name
- pickup
- contact
- arrival action

Large controls.
Minimal text.

---

# 37. Driver Arrived

## D14

Primary:
- “I’ve arrived”

After arrival:
- waiting timer
- contact passenger
- cancel/no-show workflow only under valid business rules

---

# 38. Ride Start

## D15

If verification code/PIN is used:
- specialized numeric input
- large digits
- clear error state

Primary:
- Start ride

Do not permit accidental start with invalid ride state.

---

# 39. Active Ride — Driver

## D16

Navigation dominates.

Bottom compact panel:
- destination
- ETA
- passenger
- safety/help

No earnings clutter while driving.

---

# 40. Complete Ride

## D17

Primary:
- Complete ride

Confirmation should occur only if premature taps are costly.

Then:
- fare/payment status
- cash collection if relevant
- electronic confirmation

---

# 41. Driver Earnings

## D20

Dashboard:
- today
- week
- month

Key figures:
- gross earnings
- platform deductions if any
- net earnings
- trip count
- payout/payment status

Charts:
- simple
- readable
- no unnecessary 3D effects

Transaction list:
- trip
- fare
- deduction
- final earning

---

# 42. Driver Trip History

## D21

Similar structure to passenger history, adapted for earnings.

---

# 43. Driver Account / Vehicle

## D22

Sections:
- profile
- vehicle
- documents
- service categories
- payout/payment
- language
- support
- legal
- logout

Document expiry warnings:
- visible
- time-sensitive
- actionable

---

# 44. Bottom Sheets

Bottom sheets are central to the product.

## Sizes

Collapsed:
- 160–220 dp depending on content

Half:
- approximately 45–55% viewport

Expanded:
- approximately 85–95% viewport

Never cover status/system navigation areas improperly.

## Behavior

- drag handle
- velocity-aware settling
- spring animation
- safe nested scrolling
- map padding recalculates with sheet position
- focused text field may force expanded state where needed

## Map synchronization

When sheet rises:
- route/markers shift into visible map area via camera padding
- floating controls move above sheet
- selected vehicle remains visible

---

# 45. Map Marker Design

## User marker
- navy/white target or dot
- accuracy halo
- should not be mistaken for taxi

## Pickup
- mustard pin
- high contrast
- bottom-tip anchor

## Destination
- navy pin or flag
- clearly differentiated from pickup

## Driver vehicle marker
- vehicle silhouette or top/isometric asset
- rotation reflects heading
- size stable in dp
- optional selection halo

## Shared/intercity vehicle
- distinct silhouette
- never recolor the exact same car asset and call it a different service if vehicle type is materially different

---

# 46. Vehicle Projection and Perspective Rules

This area must be treated carefully.

## 46.1 Do not use incompatible perspectives

If the map is visually top-down or modestly tilted:
- vehicle asset must be top-down or shallow isometric.

Do not place:
- a side-view taxi,
- a dramatic 3/4 front render,
- a low-camera 3D render

as a navigation marker on a top-down map.

## 46.2 Marker-space orientation

Vehicle artwork should be produced around a known forward axis.

Recommended:
- source asset points straight upward at 0 degrees.

Then runtime rotation:
- `rotation = heading - mapBearing` when artwork rotates relative to screen/map bearing,
- exact implementation depends on map SDK coordinate system.

Test:
- northbound taxi points upward on north-up map,
- eastbound points right,
- vehicle appears consistent as map rotates.

## 46.3 Anchor

For top-down markers:
- anchor near geometric center.

For shallow isometric assets:
- anchor at tire/ground-contact center, not center of transparent canvas.

Otherwise markers appear to orbit or slide around their GPS coordinate.

## 46.4 Scale

Map marker size should be screen-relative:
- approximately 32–44 dp for normal taxis
- 36–48 dp for larger taxi markers if silhouette remains readable

Do not scale vehicle asset with geographic zoom except intentionally.

## 46.5 Lighting

All 3D/isometric vehicle assets must share:
- same camera angle
- same focal length
- same light direction
- same shadow softness
- same render scale
- same outline policy

Otherwise service cards look like unrelated stock graphics.

---

# 47. Motion System

## Durations

Micro:
- 100–160 ms

Standard:
- 180–260 ms

Large state transition:
- 280–420 ms

Avoid excessively slow onboarding animations.

## Motion examples

Button press:
- subtle scale or tonal response

Bottom sheet:
- spring

Route line:
- quick reveal/draw

Vehicle selected:
- 1–2% lift/scale + mustard border transition

Driver matched:
- sheet content crossfade + map camera transition

Taxi movement:
- interpolated position and rotation

Success:
- concise checkmark or status change

Respect reduced-motion accessibility settings where platform support exists.

---

# 48. Loading System

Never use one spinner for everything.

Use:
- skeleton cards for lists
- inline spinner for button submission
- map shimmer/placeholder only if map genuinely unavailable
- progress state for driver search
- document-processing status for verification

Prevent repeated taps while operation is in flight.

---

# 49. Empty States

Every major list needs an empty state.

Examples:
- no recent trips
- no saved places
- no payment methods
- no driver earnings yet
- no documents uploaded

Each empty state:
- small branded illustration/icon
- short explanation
- one useful CTA if applicable

---

# 50. Error Handling

Error hierarchy:

Field error:
- directly below field

Panel error:
- inside current card/sheet

Transient network issue:
- snackbar/banner with retry when appropriate

Blocking failure:
- dedicated state/screen

Never use a generic “Something went wrong” if the system knows what happened.

---

# 51. Connectivity and Offline Behavior

Passenger:
- preserve recent places
- show offline banner
- prevent booking if network-required
- retain entered data when connection drops

Driver:
- prominent connection status
- do not misrepresent driver as online if connection is lost
- ride-in-progress recovery must be explicit

---

# 52. Accessibility

- minimum 48 dp touch targets
- sufficient contrast
- screen-reader labels for icons
- no information encoded by color alone
- dynamic type/font scaling should not break essential controls
- focus order must follow visual order
- form error messages must be programmatically associated with fields
- map actions need accessible alternatives where possible

---

# 53. Localization

Design for:
- Arabic
- French
- English if supported

Arabic requirements:
- RTL layout
- mirrored navigation icons where semantically appropriate
- text alignment changes
- number/phone handling tested carefully
- map labels are map-provider dependent
- do not manually reverse strings

Components must tolerate text expansion.

Avoid fixed-width buttons based on English labels.

---

# 54. Responsive Layout

Primary target:
- phone portrait

Also test:
- compact Android screens
- tall modern phones
- landscape where necessary
- tablets if supported later
- iOS safe-area differences

Do not hardcode vertical positions against one screenshot.

Use:
- window insets
- constraint-aware layout
- sheet safe areas
- adaptive spacing where necessary

---

# 55. Component Library to Implement in Compose Multiplatform

Recommended reusable components:

- `TaxiScaffold`
- `TaxiTopBar`
- `TaxiBottomNavigation`
- `TaxiPrimaryButton`
- `TaxiSecondaryButton`
- `TaxiTextButton`
- `TaxiIconButton`
- `TaxiTextField`
- `PhoneNumberField`
- `EmailField`
- `PasswordField`
- `OtpInput`
- `LocationSearchField`
- `SearchResultRow`
- `TaxiCard`
- `ServiceTypeCard`
- `PaymentMethodCard`
- `DriverSummaryCard`
- `TripSummaryCard`
- `SavedPlaceRow`
- `StatusChip`
- `InlineError`
- `InfoBanner`
- `OfflineBanner`
- `TaxiBottomSheet`
- `LoadingButton`
- `EmptyState`
- `RatingStars`
- `FareRow`
- `DriverDocumentCard`
- `EarningsSummaryCard`
- `MapFloatingButton`
- `PickupPinOverlay`
- `VehicleMarker`
- `RouteLegend`

Each component must define:
- default
- pressed
- focused
- disabled
- loading
- error
- selected
where relevant.

---

# 56. UI State Architecture

Each screen should use explicit state models rather than scattered booleans.

Example concept:

```kotlin
sealed interface BookingUiState {
    data object Idle : BookingUiState
    data object SelectingDestination : BookingUiState
    data object SelectingPickup : BookingUiState
    data class ChoosingService(...) : BookingUiState
    data object Confirming : BookingUiState
    data object SearchingDriver : BookingUiState
    data class DriverAssigned(...) : BookingUiState
    data class DriverApproaching(...) : BookingUiState
    data object DriverArrived : BookingUiState
    data class InRide(...) : BookingUiState
    data class Completed(...) : BookingUiState
    data class Error(...) : BookingUiState
}
```

The exact architecture may differ, but UI state must be intentional.

Avoid:
- many independent mutable booleans that can contradict each other,
- duplicated loading flags,
- screen behavior encoded only through navigation routes.

---

# 57. Design Review Checklist for Every Screen

Before implementation approval, verify:

1. What is the one primary user goal?
2. Is the main action obvious?
3. Are inputs specialized?
4. Is the keyboard appropriate?
5. Are validation and errors defined?
6. Are loading states defined?
7. Are offline states defined?
8. Are empty states defined?
9. Is visual hierarchy obvious in grayscale?
10. Does the screen still work in Arabic RTL?
11. Does it survive long French labels?
12. Does it work with larger text?
13. Does it avoid accidental taps?
14. Is every icon understandable?
15. Does every map overlay respect bottom-sheet height?
16. Are map markers correctly anchored?
17. Are vehicle perspectives consistent?
18. Is animation communicating state?
19. Does back navigation behave correctly?
20. Is the screen usable one-handed where appropriate?

---

# 58. Recommended Implementation Order

## Stage A — Design foundation
1. Theme/colors
2. Typography
3. spacing
4. shapes
5. buttons
6. inputs
7. cards
8. sheets
9. banners/errors
10. navigation primitives

## Stage B — Passenger onboarding
1. Splash
2. Landing
3. Auth method
4. Phone
5. OTP
6. Profile
7. permissions

## Stage C — Passenger core booking
1. Home map
2. Search
3. Pickup
4. Route preview
5. Service selection
6. fare/payment
7. confirmation
8. searching
9. driver matched
10. active ride
11. completion/rating
12. fixed-route catalog/direction
13. scheduled review/upcoming booking states

## Stage D — Passenger account
1. Trips
2. Trip details
3. Saved
4. Account
5. help/safety

## Stage E — Driver onboarding
1. welcome
2. identity
3. documents
4. vehicle
5. application status

## Stage F — Driver operations
1. offline home
2. online
3. request
4. navigation to pickup
5. arrived
6. ride start
7. active ride
8. completion
9. earnings
10. history/account
11. scheduled offers/upcoming commitments

## Stage G — National operations web (after backend control plane)
1. operations authentication and scope shell — dedicated password/TOTP challenge,
   recovery-code entry, session strength, and explicit recent-MFA step-up delivered
2. rollout overview — Phase 12 delivered
3. city readiness/lifecycle — Phase 12 city creation, service-area point editor,
   coherent configuration assembly, staged review/activation, evidence, and
   guarded lifecycle transition delivered
4. operators, assignments, and staff grants — Phase 12 operator creation/status
   and exact-scope assignment create/retire workflows delivered; staff grant
   create/revoke requests derive selected scope, show expiry/recertification,
   require typed confirmation, and enter a durable queue. The maker may cancel,
   the target cannot decide, and another administrator may approve/reject with a
   reason and version; backend authority and continuity are revalidated at commit.
   Roster, recertification and hosted staff acceptance remain open
5. driver application review — Phase 13 requirement editor, scoped queue,
   decision confirmation, applicant-safe timeline, and recent-MFA protected
   document retrieval delivered; deployment configuration remains fail-closed
6. pricing/scheduling/operator-fee versions — Phase 14 editor expanded with the
   complete Phase 16 scheduling policy contract
7. payment capability/recipient versions, scoped transfer reconciliation, and
   refund ledger — delivered with backend-authoritative lifecycle and MFA prompts
8. fixed-route map editor and publication review — Phase 15 direction, stop,
   geometry, fare, review, and publication workflow delivered
9. scheduled exceptions — Phase 16 scoped read-only list/detail delivered
10. aggregate reporting — Phase 17 rollout-intelligence destination delivered
    with family/service filters, source/definition metadata, summary cards,
    aggregate fact table, and visible all-measure small-cell suppression; a
    suppressed cell is never rendered as zero
11. audit/security review — scoped append-oriented audit view delivered; security
    incident actions remain pending
12. support and safety operations — city-scoped queues, protected detail,
    triage/transition confirmations, minimal safety handoff, and durable overdue
    alert acknowledgement delivered; market-admin legal-hold placement/release
    and immutable erasure-evidence review are delivered without exposing erased
    content; emergency-service limitations remain visible

Items without a delivery note remain future-stage UI and must not appear as
enabled placeholder navigation. Local/test password-only mode remains visibly
labeled; hosted mode uses the implemented MFA and secure-cookie/CSRF protocol.
The console never automatically retries the sensitive command that triggered a
step-up prompt.

---

# 58A. National Operations Web Extension

This console extends the existing identity; it does not introduce a new palette,
font system, icon family, map style, or motion language.

Desktop shell:
- persistent navy sidebar,
- white/neutral content canvas,
- top scope switcher showing market, operator, and city,
- mustard reserved for the primary action/selected state,
- responsive tables, cards, side drawers, and map workspaces,
- exact status text paired with semantic feedback colors.

Required rules:
- scope selection triggers a backend-authorized reload and never grants access,
- draft/review/active/replaced/paused/retired states are visually distinct,
- route/fare/config previews show the version and effective time,
- city pause, rate activation, route publication, staff grant, and driver
  decision require a review summary and explicit confirmation,
- recipient/payment-capability activation shows operator/city scope, effective
  time, cash fallback, destination, reviewer evidence, and a deliberate
  confirmation; no credential field exists,
- the manual-transfer queue defaults oldest-first and shows only scoped claim ID,
  backend payment reference, optional payer reference, exact amount/currency,
  recipient, submission age, and status,
- verification requires a constrained unique settlement reference plus a review
  summary; rejection requires a bounded reason. Neither action accepts an edited
  amount, fare, passenger-supplied success state, or uploaded statement,
- verify/reject controls stay pending until the backend responds. Verified rows
  become immutable and show the audit reference; rejected rows preserve history
  and explain that the passenger may retry,
- charts have text/table alternatives and use a restrained semantic palette,
- city/route maps show service geometry or authorized aggregates, never
  participant trails or passenger-facing online taxis,
- success animation occurs only after the backend returns the new state,
- keyboard, screen-reader, RTL, loading, empty, conflict, error, and offline
  states are designed with the first implementation slice.

The public driver web portal reuses auth/onboarding components but has no
operations sidebar or privileged data. Submitting an application displays a
pending/review status, never an approval celebration.

---

# 59. Acceptance Standard

A page is not considered finished merely because:
- it compiles,
- it displays data,
- buttons work,
- fields accept text.

A finished page must:
- follow the design system,
- include all important states,
- use specialized inputs,
- have correct spacing and hierarchy,
- animate state changes appropriately,
- handle accessibility and localization,
- behave correctly with map/sheet interaction where relevant,
- use final or approved placeholder assets,
- be visually consistent with the rest of the product.

---

# 60. Visual Direction Summary

The finished application should look like a deliberate taxi platform, not a generic template.

White:
- dominant surface and clarity

Navy:
- structure, type, navigation, trust

Mustard:
- taxi identity, selected state, action, route emphasis

The visual language should combine:
- strong geometry,
- restrained iconography,
- clear map integration,
- high-information bottom sheets,
- subtle motion,
- purpose-built transport assets.

The main UI should remain clean enough that the taxi illustrations, map markers, and mustard emphasis become distinctive rather than competing with visual noise.
