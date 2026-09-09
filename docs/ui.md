# TaxiMobile — UI Plan

## Purpose

Define the visual identity, interaction model, motion language, and screen-by-screen UI plan for the passenger and driver applications.

This document is the **approved visual authority** for TaxiMobile. It does not override backend authority, ride state machines, pricing, payments, or accessibility constraints in `design.md`, `rides.md`, `api.md`, or `security.md`. UI must always reflect backend-confirmed state.

`design.md` remains the interaction and state-authority document. `ui.md` defines how those states look, move, and feel.
`extended_ui.md` is the detailed screen/component companion and defines the
approved mustard/navy/white expansion plus mandatory asset fallbacks. Where an
older blue-accent value in this document conflicts with `extended_ui.md`, the
mustard token is authoritative.

---

## Current implementation standing — 2026-09-02

The former minimal shared shell has been replaced by the approved map-first
passenger and driver experiences. Shared tokens/components, bottom-sheet flows,
driver offer and active-ride surfaces, history/receipts, fixed routes, scheduling,
driver application surfaces, and the national operations web extensions are
implemented in source. They must retain the mustard/navy/white identity defined
with `extended_ui.md`.

| UI wave | Source standing | Remaining acceptance |
| --- | --- | --- |
| Wave 0 — Functional shell | Superseded by later waves | Preserve only as loading/error fallback, not as the product identity. |
| Wave 1 — Design system | Implemented in source | Complete contrast, typography-scale, screen-reader, and component-state audit. |
| Wave 2 — Map-first passenger shell | Map selection, place search/reverse lookup, routing and fallbacks implemented in source | Accept production tiles/routing/geocoder, multilingual place quality, location behavior, network loss, and representative devices. |
| Wave 3 — Driver operational shell | Implemented in source | Accept real dispatch, navigation, safety, battery, and weak-network behavior. |
| Wave 4 — Delight and density | Substantially implemented | Run reduced-motion and performance review; remove any non-authoritative celebratory state. |
| Wave 5 — Production polish | Partially implemented | Physical Android/iOS/browser matrix, accessibility, RTL clipping, crash and store screenshot acceptance remain open. |
| Wave 6 — National extensions | Implemented in source through payment/case operations | Browser E2E, production hosting, protected-document, scoped-operator, and real city workflow acceptance remain open. |

Source presence is not proof of consumer-grade UX. The release gate is the
evidence in [`gaps.md`](gaps.md), not completion of this visual specification.

Do not rebuild business logic while applying visual layers. Theme and layout wrap existing coordinators and gateways.

---

## Product feel

TaxiMobile should feel like a modern ride-hailing product (Uber / Lyft class), adapted for licensed taxi cooperatives:

* **Map is the stage.** Primary passenger and active-ride screens are map-first, not form-first.
* **Sheets carry decisions.** Pickup, fare, matching, driver info, and payment live in morphing bottom sheets.
* **Status is always visible.** A ride never feels abandoned; the UI narrates the next expected event.
* **One primary action.** Every surface has one dominant CTA.
* **Backend is truth.** Animations celebrate confirmed transitions; they never invent assignment, fare, or payment success.
* **Navy is identity.** Color, chrome, and markers read as TaxiMobile without relying on logo alone.
* **Service before supply.** Passengers browse destinations and published routes,
  never the online fleet; driver-specific presentation begins only after backend
  assignment.

---

## Brand system

### Brand name treatment

* Wordmark: `TaxiMobile` in display type, tracking +0.5%.
* Passenger app chrome title: `TaxiMobile`.
* Driver app chrome title: `TaxiMobile Driver` (smaller secondary “Driver” label in Medium, not a second logo).
* Do not invent a mascot for MVP polish. Use a simple geometric taxi mark (rounded rectangle + light bar) as the app icon and empty-state glyph.

### Brand mark

```text
┌──────────────┐
│ ████  ████   │   24×24 / 48×48 / 108×108
│ ████  ████   │   Fill: Navy 800
│ ░░░░░░░░░░░░ │   Light bar: Accent 400
│ ●          ● │   Wheels: Navy 900
└──────────────┘
```

Keep the mark flat, no gloss, no 3D. On map markers, use a filled navy pin with a white taxi glyph.

---

## Color palette (fixed)

All product UI uses this palette only. Do not introduce purple gradients, cream editorial themes, or ad-hoc hex values in feature code. Tokens live in shared theme code (for example `TaxiTheme.colors`).

### Core navy scale

| Token | Hex | Usage |
| --- | --- | --- |
| `navy.950` | `#071426` | Map night overlay, splash deep fill |
| `navy.900` | `#0B1F3A` | Primary brand, app bars, primary reading color |
| `navy.800` | `#163A63` | Elevated navy surfaces, driver online HUD |
| `navy.700` | `#1B3554` | Pressed navy, secondary icons on light |
| `navy.600` | `#27486D` | Borders on navy surfaces |
| `navy.500` | `#3A5F8A` | Secondary text on navy |
| `navy.400` | `#5E82AD` | Icons on light when muted |
| `navy.300` | `#8AA6C5` | Dividers on navy |
| `navy.200` | `#C2D3E6` | Soft chips, map route halo |
| `navy.100` | `#E4EDF7` | Selected row wash, info banners |
| `navy.50` | `#F3F7FB` | App background (light) |

### Accent and feedback

| Token | Hex | Usage |
| --- | --- | --- |
| `accent.600` | `#9B7900` | Pressed mustard and accessible accent text |
| `accent.500` | `#D6A800` | Primary CTA, taxi selection, pickup and route emphasis |
| `accent.400` | `#F3D76A` | Light selection and compact highlights |
| `accent.100` | `#FFF5C2` | Selected-card and accent soft fill |
| `success.600` | `#14804A` | Online, settled cash, verified transfer, completed |
| `success.100` | `#DDF5E8` | Success banner background |
| `warning.600` | `#B7791F` | Expiring offer, stale location |
| `warning.100` | `#FFF3D6` | Warning banner background |
| `danger.600` | `#C53030` | Cancel, decline, errors |
| `danger.100` | `#FDE8E8` | Error banner background |
| `info.600` | `#2B6CB0` | Neutral informational status |
| `info.100` | `#E6F0FA` | Info banner background |

### Neutrals and surfaces

| Token | Hex | Usage |
| --- | --- | --- |
| `surface.0` | `#FFFFFF` | Sheets, cards, fields |
| `surface.1` | `#F6F8FB` | Page background |
| `surface.2` | `#EAECF0` | Recessed wells, segmented tracks and disabled fill |
| `ink.900` | `#0B1F3A` | Primary text (`navy.900`) |
| `ink.700` | `#334155` | Secondary text |
| `ink.500` | `#64748B` | Tertiary / captions |
| `ink.300` | `#94A3B8` | Placeholders, disabled labels |
| `stroke.subtle` | `#D7E0EC` | Hairline borders |
| `stroke.strong` | `#A8B9CD` | Emphasized outlines |
| `overlay.scrim` | `#0B1F3A` @ 40% | Modal scrim |
| `overlay.map` | `#0B1F3A` @ 8–16% | Bottom gradient over map for sheet readability |

### Semantic mapping (do not invent second meanings)

| Meaning | Color |
| --- | --- |
| Primary CTA | `accent.500` fill, `navy.950` label |
| Secondary CTA | white fill, `navy.900` border + label |
| Destructive CTA | `danger.600` |
| Matching / searching | `accent.500` pulse |
| Driver online | `success.600` |
| Driver offline | `ink.500` |
| Offer expiring (<15s) | `warning.600` |
| Payment pending | `warning.600` (with text, never color alone) |
| Transfer review processing | `info.600` + explicit “not yet verified” text |
| Payment completed | `success.600` |
| Unmatched / failed match | `info.600` + explicit copy from `design.md` |

### Dark surfaces

Prefer a **light product chrome** with navy accents. Do not ship a full dark-mode theme in the first polish waves.

Allowed dark surfaces only:

* Splash / session restore full-screen (`navy.950`)
* Map itself (provider tiles)
* Driver “Online” compact HUD strip (`navy.800`)
* Full-screen matching celebration overlay (optional, `navy.900` @ 92%)

---

## Typography

Avoid platform default stacks as the brand voice (no Inter / Roboto / Arial / system UI as the display identity).

### Font families

Bundle as Compose Multiplatform resources:

| Role | Family | Fallback chain | Notes |
| --- | --- | --- | --- |
| Display | **Sora** | `Sora` → `sans-serif` | Headlines, fare amounts, ETA numerals |
| UI / Body | **Manrope** | `Manrope` → `sans-serif` | Buttons, sheets, forms, lists |
| Mono / IDs | **IBM Plex Mono** | `IBM Plex Mono` → `monospace` | Taxi plate / vehicle ID, receipt IDs (never passwords) |

Weights to ship: Sora 600/700; Manrope 400/500/600/700; IBM Plex Mono 500.

Arabic, French, and English catalogs are implemented. Keep Manrope for Latin and
the platform Arabic fallback until a separately licensed and device-validated
Arabic companion is approved; changing typefaces must not alter the navy token
set. Do not hard-code English-only layout widths that break RTL.

### Type scale

| Token | Family | Size | Line height | Weight | Tracking | Use |
| --- | --- | --- | --- | --- | --- | --- |
| `display.lg` | Sora | 40 sp | 44 | 700 | -1% | Splash wordmark, large fare |
| `display.md` | Sora | 32 sp | 36 | 700 | -0.5% | Sheet titles (“Where to?”) |
| `display.sm` | Sora | 24 sp | 28 | 600 | 0 | Section heroes, ETA |
| `title.lg` | Manrope | 20 sp | 26 | 700 | 0 | Screen titles |
| `title.md` | Manrope | 18 sp | 24 | 600 | 0 | Card titles |
| `title.sm` | Manrope | 16 sp | 22 | 600 | 0 | List headers |
| `body.lg` | Manrope | 16 sp | 24 | 400 | 0 | Primary reading |
| `body.md` | Manrope | 14 sp | 20 | 400 | 0 | Secondary copy |
| `body.sm` | Manrope | 12 sp | 16 | 500 | +1% | Captions, timestamps |
| `label.lg` | Manrope | 14 sp | 18 | 700 | +2% | Buttons |
| `label.md` | Manrope | 12 sp | 16 | 600 | +3% | Chips, badges |
| `mono.md` | IBM Plex Mono | 14 sp | 18 | 500 | 0 | Vehicle / taxi IDs |
| `mono.sm` | IBM Plex Mono | 12 sp | 16 | 500 | 0 | Receipt references |

Money: always use `display.sm` or larger for the primary amount; currency code in `body.sm` (`ink.500`). Never animate digit scrambling for fares—snap to backend values.

---

## Layout foundations

### Spacing scale (8 pt base)

`4, 8, 12, 16, 20, 24, 32, 40, 48, 64`

| Token | Value |
| --- | --- |
| `space.xxs` | 4 |
| `space.xs` | 8 |
| `space.sm` | 12 |
| `space.md` | 16 |
| `space.lg` | 20 |
| `space.xl` | 24 |
| `space.2xl` | 32 |
| `space.3xl` | 40 |
| `space.4xl` | 48 |

### Radii

| Token | Value | Use |
| --- | --- | --- |
| `radius.sm` | 8 | Inputs, small chips |
| `radius.md` | 12 | Buttons, list rows |
| `radius.lg` | 16 | Cards |
| `radius.xl` | 24 | Bottom sheets (top corners) |
| `radius.pill` | 999 | Status pills, ETA bubbles |
| `radius.mapPin` | 50% | Circular map markers |

Avoid “pill everything.” Pills are for status and ETA only. Primary CTAs use `radius.md` (12), not stadium pills.

### Elevation / shadow

Use restrained navy-tinted shadows, not multi-layer glow stacks.

| Level | Spec | Use |
| --- | --- | --- |
| `elev.0` | none | Flat page |
| `elev.1` | `0 1 2` @ `navy.900` 6% | Inputs |
| `elev.2` | `0 4 16` @ `navy.900` 10% | Floating chips, map FABs |
| `elev.3` | `0 -8 28` @ `navy.900` 14% | Bottom sheets |
| `elev.4` | `0 12 40` @ `navy.900` 18% | Offer takeover card |

No neon glow, no purple bloom, no stacked drop shadows on every element.

### Safe areas and chrome

* Respect system status bar / home indicator / cutouts.
* Map draws edge-to-edge.
* Floating controls inset: 16 dp from sides, 12 dp below status bar.
* Bottom sheet content padding: 20 / 20 / 24, plus gesture nav inset.
* Minimum touch target: 48×48 dp.
* Primary CTA height: 52 dp.
* Secondary controls: 44–48 dp.

### Grid

* Phone: single column, content max width unconstrained.
* Large phone / fold inner: content still single column; map remains full-bleed.
* Desktop/web test surfaces may center a 480 dp column over a `navy.50` canvas; not a product target.

---

## Motion language

Motion exists to explain state change, not to decorate. Prefer shared Compose animation APIs (`AnimatedContent`, `animate*AsState`, `updateTransition`, `Animatable`).

### Timing tokens

| Token | Duration | Easing | Use |
| --- | --- | --- | --- |
| `motion.instant` | 100 ms | linear | Press opacity |
| `motion.fast` | 180 ms | emphasized decelerate | Chips, icon swaps |
| `motion.base` | 280 ms | standard | Sheet height morph, tab crossfade |
| `motion.slow` | 420 ms | emphasized | Route draw, matching expand |
| `motion.enter` | 320 ms | decelerate | Sheet appear |
| `motion.exit` | 220 ms | accelerate | Sheet dismiss |
| `motion.pulse` | 1200 ms | ease in-out | Matching halo loop |
| `motion.offerTick` | 1000 ms | linear | Offer countdown progress |

Easing presets:

* **standard**: Material emphasized / cubic(0.2, 0, 0, 1)
* **decelerate**: cubic(0, 0, 0, 1)
* **accelerate**: cubic(0.3, 0, 1, 1)
* **emphasized decelerate**: cubic(0.05, 0.7, 0.1, 1)

### Required motion set (ship at least these)

1. **Sheet morph** — bottom sheet height and content crossfade when ride phase changes (`idle → estimate → matching → assigned → active → complete`).
2. **Route draw-on** — polyline animates from pickup toward destination over `motion.slow` after backend route arrives; if route fails, no fake line.
3. **Matching pulse** — accent ring around pickup pin + subtle sheet progress shimmer while `MATCHING`.
4. **Offer entrance** — driver offer card springs up from bottom with `elev.4` and countdown bar.
5. **Status chip swap** — old chip fades/scales out, new chip fades/scales in on backend status change.
6. **CTA press** — scale to 0.98 + 8% darken within `motion.instant`.
7. **Success check** — cash settled / rating submitted uses a 320 ms check-draw, then settles to static success row.

The check is driven by a monotonic backend-confirmed action event, never by the
tap itself. The same event clears successfully submitted support and vehicle
drafts; rejection or uncertain delivery leaves those drafts available to correct
or retry manually.
8. **Reconnect banner** — slides from top on offline; reverse on restored session.

### Context clues (interactive feedback)

Every important action needs a non-color confirmation:

| User action | Immediate clue | Confirmed clue |
| --- | --- | --- |
| Tap map for pickup | Pin drops with 12 dp overshoot, haptic light | Coordinate summary updates under “Pickup” |
| Request ride | CTA → spinner label “Requesting…” | Sheet morphs to Matching; history unchanged until API returns |
| Matching | Pulse + “Finding a nearby taxi…” | Assigned sheet OR unmatched empty state |
| Offer received (driver) | Card rises + medium haptic + optional sound toggle later | Accept/decline enabled |
| Accept offer | Button progress | Assigned ride controls replace offer |
| Cancel | Confirm modal first | Terminal status in history; return to new-ride sheet |
| Go online | Switch animates; “Updating…” | Green Online pill only after API success |
| Settle cash | Confirm modal | Success banner + earnings refresh |
| Submit transfer reference | Button progress | Processing/review copy only; no payment-success animation |
| Push hint received | No business mutation | Soft top toast “Updating ride…” then refresh |

### Reduced motion

Honor OS reduced-motion settings:

* Replace loops with static accent state.
* Crossfade instead of slide where possible.
* Keep state text fully readable without animation.
* Never hide information behind motion that cannot complete.

### Haptics (native only)

| Event | Android | iOS |
| --- | --- | --- |
| Primary CTA success | `CONTEXT_CLICK` / light | `UIImpactFeedbackGenerator.light` |
| Offer received | medium | medium |
| Destructive confirm | heavy | heavy |
| Error | double-light | notification error |

Haptics are progressive enhancement; UI must work without them.

---

## Iconography & illustration

* Style: 1.75 px stroke, rounded joins, 24 dp grid, navy-forward.
* Common controls use the existing Compose/Material family. Distinct brand, transport, map, payment, safety, and status symbols use the approved 1.75 px custom family; do not introduce another icon set or mix styles ad hoc.
* Status icons always pair with text labels.
* Empty states: one navy taxi mark + one sentence + one CTA. No collage, no floating promo stickers on the map.
* Editable masters, runtime mappings, fallbacks, and the visual catalog are maintained in `assets/README.md` and `assets/manifest.json`.

---

## Component catalog

Implement as shared Compose components under something like `feature/ui/` or `core/ui/` once Wave 1 starts. Feature screens consume components; they do not restyle ad hoc.

### 1. `TaxiButton`

Variants: `Primary`, `Secondary`, `Tertiary`, `Destructive`, `Tonelike` (text).

States: enabled, pressed, loading (spinner replaces label, width locked), disabled.

Rules:

* Only one `Primary` per visible sheet region.
* Loading disables double-submit locally; success still requires backend confirmation.
* Label uses `label.lg`.

Android and iOS supply `TaxiButton.loading` from a shared resource-aware pending
action. Admission happens synchronously before a coroutine is launched, closing
the interval in which two rapid taps could enqueue duplicate commands. Only the
initiating repeated-list control shows a spinner; sibling backend controls are
disabled until `finally` releases the one-at-a-time gate.

### 2. `TaxiTextField`

* Height 52, `radius.sm`, `stroke.subtle`, focus ring `accent.500` 2 dp.
* Floating or top-aligned label in `body.sm`.
* Inline error in `danger.600` with icon + text.
* Password: reveal toggle; never log or screenshot-persist.

### 3. `TaxiSheet`

Uber-like bottom sheet with:

* Grabber (32×4, `ink.300`)
* Snap points: `peek` (~28% screen), `half` (~48%), `expanded` (~78%)
* System text scale promotes the minimum reachable snap: `1.3×` promotes peek
  to half, and `1.6×` or greater promotes peek/half to expanded; explicit user
  expansion is never reduced
* Morph between snap points with `motion.base`
* Scrim only when expanded over critical confirmations
* Content scrollable inside sheet; map remains interactive behind peek/half unless modal

### 4. `StatusPill`

Text + optional leading dot. Colors from semantic tokens. Always include accessible description.

Examples: `Matching`, `Driver on the way`, `Arriving`, `In trip`, `Completed`, `Online`, `Offline`, `Payment pending`.

### 5. `FareBlock`

* Large amount (`display.sm`)
* Tariff version caption (`body.sm`, `ink.500`)
* Optional breakdown rows from **backend components only**
* Estimate vs final: label explicitly (`Estimated fare` vs `Final fare`)

### 6. `DriverCard`

Shows only authorized fields:

* Display name
* Vehicle make / model / color
* Taxi / plate ID in mono
* Status pill

Never show private contact, home address, or earnings to passengers.

### 7. `OfferCard` (driver)

* Pickup neighborhood / distance / ETA from API
* Locked estimated fare
* Countdown bar mapped to offer expiry
* Accept (primary) / Decline (secondary)
* On expiry: card exits; list refreshes from API

### 8. `MapFAB`

Circular 48–56 dp, white, `elev.2`, navy icon. Used for my-location, recenter route, support shortcut.

### 9. `ToastBanner`

Top inset banner for offline, push-refresh, non-blocking info. Auto-dismiss informational toasts after 4s; errors stay until acknowledged or condition clears.

### 10. `ConfirmDialog`

For cancel ride, decline offer, settle cash, go offline while offer pending (if applicable). Title, body, destructive/primary pair. No “tap outside to confirm.”

### 11. `Skeleton`

Navy-tinted shimmer (`navy.100` → `navy.200`) for history rows and earnings while loading. Prefer skeletons over spinners for lists; use CTA spinner for mutating actions.

### 12. `SegmentedControl`

For login/register, cash confirmation steps, history filters (later). Track `surface.2`, selected thumb white + `elev.1`.

---

## Map UI specification

MapLibre is the renderer. Style/tile URL remains environment configuration.

### Visual overlay rules

* Full-bleed map under chrome.
* Soft bottom gradient (`overlay.map`) behind the sheet for contrast.
* Pickup pin: mustard teardrop + navy/white center; selection pulse in `accent.500`.
* Destination pin: navy teardrop with a clearly differentiated white/checkered center.
* Route: `navy.900`, width 5 dp, white halo; pickup uses `accent.500`.
* Debug builds use the restrained OpenFreeMap Positron style. If a configured
  provider style cannot load, Android and iOS switch to a bundled neutral
  background with no sprite, glyph, or network dependency; route/point overlays
  and manual coordinate entry remain usable.
* Do **not** animate a fake moving car or label location as live. For an active
  assigned ride, the API now optionally provides one post-assignment last-known
  driver observation. Render it with a distinct static marker, show its
  `observed_at` value in the sheet, and provide an explicit authoritative refresh.
  The marker disappears with terminal ride state; it is not a location stream.
* Before assignment, do not render real or simulated online taxis, supply counts,
  candidate markers, queues, or driver heatmaps. A published fixed-route line is
  static catalog geometry and must use route/direction labeling rather than a
  vehicle marker.
* Attribution remains visible and unobscured.
* One-shot location permission prompts use platform UI; denial keeps map-tap + manual entry.
* While a platform location request is pending, its FAB/button exposes localized
  loading semantics, is disabled, and ignores repeated taps without terminating
  the first request.

### Passenger map modes

| Mode | Map shows | Sheet shows |
| --- | --- | --- |
| Idle | User/context area, no fake taxis | “Where to?” search/destination entry |
| Fixed-route catalog | Selected static route direction, start/finish, optional stops; no taxis | Direction + flat fare + Book now / Schedule |
| Pickup set | Pickup pin | Confirm pickup / set destination |
| Both set | Pins + estimate route after API | Fare estimate + Request |
| Scheduled review | Route/pins or published fixed route; no taxis | Pickup time, timezone, surcharge, operator fee, cancellation terms |
| Scheduled upcoming | Static route context; no driver marker before commitment/handoff | Booking status, time, driver commitment status, cancel policy |
| Matching | Pickup pulse | Finding taxi… |
| Assigned / en route | Route plus optional static last-known driver marker | Driver card + status + observation time |
| Active trip | Route plus optional static last-known driver marker | In-trip status + observation time + support |
| Completed | Static summary optional | Receipt / rate / done |

### Driver map modes

| Mode | Map shows | HUD / sheet |
| --- | --- | --- |
| Offline | Context map | Go online controls |
| Online idle | Context + self marker (process-local last accepted coord) | Online pill + waiting |
| Offer | Highlight pickup | Offer card |
| To pickup | Route to pickup if routing available | Next transition CTA |
| To destination | Route to destination | Trip controls |
| Complete / cash | Summary | Settle cash CTA |

Recenter FAB always returns to the relevant focus (self, pickup, or full route bounds).

---

## Navigation model

Two separate apps (passenger flavor / driver flavor), one shared design system.

### Passenger information architecture

```text
Root
├─ Session restore (full-screen navy)
├─ Auth (login / register)
├─ Home (map + sheet) ← default signed-in
│  ├─ Place selection
│  ├─ Fixed-route catalog / direction detail
│  ├─ Estimate
│  ├─ Schedule review / upcoming bookings
│  ├─ Matching
│  ├─ Active ride
│  └─ Completion / receipt / rating
├─ Activity (ride history)
├─ Inbox (notifications)
├─ Support
└─ Profile / sign out
```

Primary navigation after polish Wave 2:

* **Home** is map-first (no hamburger-first dashboard).
* A compact **bottom destination bar** or top “Where to?” field opens the sheet.
* Secondary destinations (Activity, Inbox, Support, Profile) use a discreet round account button (top-end) opening a modal menu or a later 4-tab bar **only if** content density requires it. Prefer account menu first to avoid dashboard clutter.

### Driver information architecture

```text
Root
├─ Session restore
├─ Auth
├─ Application / pending verification gates
├─ Home (map + availability HUD)
│  ├─ Offline setup (vehicle, location)
│  ├─ Online idle
│  ├─ Offer
│  ├─ Upcoming scheduled commitments
│  └─ Active ride transitions
├─ Earnings
├─ Inbox
├─ Support
└─ Profile / vehicles / sign out
```

Driver Home prioritizes **Online/Offline** and **next required action**. Do not bury Accept under navigation.

---

## Screen-by-screen plan

Copy below is English product copy for implementation; final legal/support wording may change. Status strings must remain mappable from backend enums.

### A. Splash / session restore

* Full-screen `navy.950`
* Centered wordmark `display.md` in white
* Indeterminate thin progress in `accent.400`
* Accessible text: “Checking your secure session…”
* No skip control

### B. Auth — Login

* Light background `surface.1`
* Brand mark + wordmark top
* Segmented Login / Create account
* Identifier field (email or Moroccan phone)
* Password field
* Primary: **Sign in**
* Inline errors from coordinator (network, validation, throttle)
* After registration success: prefills identifier, clears password, and renders a
  polite success banner per `design.md`; registration failures remain assertive
  error banners on the populated account form

### C. Auth — Register

* Fields: display name, email optional, phone optional, password
* Helper: password minimum 12 characters (client hint; API authoritative)
* Submit disabled until shared validity checks pass
* Non-dismissible progress on submit
* Keep form values on failure; never show raw framework payloads

### C2. Auth — Offline recovery code

* Entry point: tertiary **Use a recovery code** action below password sign-in
* Fields: account email/Moroccan phone, complete saved recovery code, new password
* Submit disabled until identifier/code/password have a complete client-side shape
* Non-dismissible progress while the backend evaluates the request
* Success copy is deliberately conditional: it says that the password changed
  only if the account and code were valid, then returns to sign-in and clears both
  secret fields
* Invalid, expired, replayed, absent-account, suspended-account, staff-account,
  and successful requests must not receive distinguishable UI copy
* Network/format/throttle failure keeps the editable recovery form; no raw API
  detail, recovery code, or password enters logs, screenshots, analytics, or crash
  metadata
* Both authenticated account screens expose active sessions, confirmed
  revocation, code creation, one-time code display, and password change. The
  one-time bundle requires a saved-all-codes check before it can be cleared from
  render state and is never automatically copied; the complete secure-save
  interaction remains a physical-device acceptance item

### D. Offline

* Illustration: broken connection glyph in navy
* Message from state
* Primary: **Retry connection** (session restore only; no command replay)

### E. Passenger Home — Idle

Uber-like composition:

1. Full-bleed map
2. Top-end: account button + optional notification badge
3. Bottom sheet peek:
   - Title `Where to?`
   - Destination field (opens expanded place entry)
   - Persistent **Fixed routes** entry for the selected city; it remains useful
     when no taxi is online
   - Up to three unique recent destinations derived from completed backend
     history summaries when available; selecting one still requires pickup and a
     fresh backend fare estimate
4. FAB: current location (one-shot)
5. Context clue: “Pickup defaults to your selected point”

### F. Passenger — Place selection

* Expanded sheet
* Pickup row with dot (`accent.500`) + editable
* Destination row with dot (`navy.900`) + editable
* A collapsed **Find a place** launcher opens an authenticated city-focused
  address/landmark picker; text is debounced and an explicit retry remains
* Results distinguish address, street, area and landmark; outside-area pickup
  results stay visible with a warning but cannot be selected as pickup
* Selecting a result stores its returned coordinate plus display label; the
  coordinate remains authoritative
* A selected map point offers explicit reverse lookup; the nearest returned
  address may label but never move that point
* Show provider attribution with the returned source URL
* Map tap sets the active row
* Manual lat/lon only in development builds if still required; hide in polished production UI once place selection is solid
* Disabled, empty, rate-limited or failed search keeps map selection and manual
  coordinates available and never invents a result
* Primary disabled until both points valid

### G. Passenger — Estimate

* Sheet half
* Route drawn after `POST /routing/route` success
* FareBlock labeled **Estimated fare**
* Tariff version caption
* Primary: **Request taxi**
* Changing either point discards estimate and route immediately
* A Now / Schedule choice appears only when enabled by the backend city catalog
* Scheduled review adds city-local pickup time, scheduling surcharge, operator
  service fee, passenger total, and cancellation/refund terms from the quote
* Fixed-route review replaces arbitrary destination editing with direction,
  ordered start/finish, static line, and locked flat transport fare

### H. Passenger — Matching

* Sheet peek/half
* Title: **Finding a nearby taxi**
* Indeterminate progress + pulse on pickup pin
* Secondary: **Cancel request** (confirm dialog)
* Do not show fake nearby cars
* Do not show real online cars, available counts, candidate identities, or queues
* On `UNMATCHED`: replace with info state — “No available taxis were found nearby.” CTA: **Try again**

### I. Passenger — Assigned / arriving / in trip

* DriverCard
* StatusPill mapped from backend
* Vehicle mono ID
* Route remains guidance only
* Cancel only when server permits
* Support shortcut with ride association when active

### J. Passenger — Completed

* Final fare from receipt API (never local recompute)
* Payment method + status (`PENDING` cash or transfer and `PROCESSING`
  transfer are not paid)
* For transfer: selectable immutable recipient/reference details, optional
  constrained payer reference, and submit action only while pending
* Confirmed refund total, net paid, and localized closed reason rows when the
  receipt API supplies them; retain the original fare above for audit clarity
* Rating 1–5 stars + optional comment
* Primary: **Done** / **Rate and close**
* History updates from API refresh

### K. Passenger — Activity / Inbox / Support / Profile

Keep calm list layouts:

* Activity: up to 10 recent rides; each row explicitly reloads its authorized
  detail and completed receipt rather than acting as static text
* Inbox: notification rows; mark read explicit; tap triggers authorized refresh
* Support: ticket list + create form (category, subject, body)
* Safety: separate warning, authorized ride selector, controlled category,
  description, reporter-safe history, and latest participant response. Never
  present it as emergency dispatch or expose internal case data.
* Profile: display name edit only; sign out always available

### L. Driver — Application gates

* Clear pending / rejected / needs verification states
* Explain that registration ≠ dispatch eligibility
* Primary actions match backend: apply, submit verification

### M. Driver — Home offline

* Map background
* HUD: Offline pill
* Checklist cards:
  1. Verified vehicle selected
  2. Fresh location submitted
  3. Go online
* Failures are visible and actionable (stale location, unverified vehicle)

### N. Driver — Online idle

* Green Online pill
* Subtle “Waiting for offers…”
* Easy **Go offline**
* Earnings glance chip (today total from API if cheap to show; else entry to Earnings)

### O. Driver — Offer (high intensity)

* Modal-ish sheet / elevated card covering lower 55%
* Countdown bar
* Pickup distance / ETA / fare from API
* Accept primary / Decline secondary
* Medium haptic on appear
* If multiple offers are not in MVP, design for one focused offer
* Service label distinguishes immediate, fixed-route, and scheduled work
* Fixed route shows direction/start/finish and locked flat fare
* Scheduled work shows pickup time/timezone, commitment/cancellation terms,
  scheduling surcharge, operator fee/funding mode, and backend expected net

### P. Driver — Active ride

* Single next CTA only: En route → Arrived → Start → Complete
* Complete requires reviewed coordinate (one-shot location or manual fallback)
* Driver cancel separate, confirm dialog, reason if API requires
* After complete: **Confirm cash received** as separate explicit action

### Q. Driver — Earnings

* Summary header: total, count, settled through
* List of earning rows from API
* No client-side fee invention (platform fee may be zero but still server-owned)

### R. Passenger — Fixed Routes

This extends Passenger Home; it is not a new visual language.

* Entry is visible for every city with at least one active published direction,
  regardless of online supply.
* List rows show localized route name, explicit direction, start → finish, and
  flat fare. Do not show taxi counts or availability dots.
* Detail uses the normal full-bleed neutral MapLibre surface and `TaxiSheet` with
  static direction geometry, ordered stops, fare components, and **Book now** /
  **Schedule** actions when enabled.
* Outbound and inbound are separate selectable directions; color alone must not
  communicate direction.
* A paused city keeps the catalog readable with an unavailable status and no
  enabled booking CTA.

### S. Passenger and Driver — Scheduled Work

Passenger scheduled review reuses `FareBlock`, `StatusPill`, `TaxiSheet`, and
existing confirmation patterns. Upcoming rows distinguish **Request received**,
**Finding a driver**, **Driver committed**, **Dispatch approaching**,
**Cancelled**, and **Unfulfilled**. “Scheduled” alone must never be styled as a
driver guarantee.

The driver receives a normal high-attention offer with scheduled timing and may
accept or decline. Accepted commitments appear in a calm upcoming-work list;
they do not replace the online HUD or active-ride CTA until dispatch handoff.
Conflicts and expiry are backend responses, not client calendar arithmetic.
The driver can enable/disable new scheduled offers with a separate city-scoped
control; it never changes the green immediate Online pill and does not cancel
existing commitments.

### T. National Operations Web Console

The protected console uses the same fixed palette, Sora/Manrope/IBM Plex Mono
roles, radii, status colors, icon family, and restrained map style. Desktop
composition uses:

```text
Persistent navy sidebar
Top bar with authenticated identity and market/operator/city scope
White/neutral work surface
Tables and cards for review
Side drawer or full page for editing
Mustard only for the single primary action
```

The web implementation includes the responsive shell, in-memory access/CSRF
state, password-to-MFA challenge, recovery-code entry, explicit step-up dialog,
permission-aware navigation, active scope selectors, rollout/readiness, city and
operator creation, operator status/service assignments, service-area version
entry/review, coherent configuration assembly/review/activation, guarded city
lifecycle review, staff-grant create/revoke with expiry review, and scoped audit. Configuration forms
select compatible loaded records by label and lifecycle; they never ask an
operator to construct arbitrary JSON or treat a pasted identifier as authority.
Later destinations below are added only as their backend phases exist. The delivered payment destination
manages recipient/capability lifecycle, scoped oldest-first transfer
reconciliation, and the append-only refund ledger with explicit backend pending,
success, conflict, and recent-MFA states. The first slice includes loading,
empty, actionable error, conflict, and narrow-layout behavior. Hosted deployment
still requires the reviewed web CSP; full RTL/localization remains a release gate.

Required destinations are:

* Rollout overview.
* Cities and activation readiness.
* Operators and staff grants.
* Driver/vehicle/credential applications.
* Rates, scheduling surcharge, and operator fee policies.
* Payment recipients/capabilities, transfer reconciliation, and refund ledger.
* Fixed routes, directions, stops, geometry, and publication.
* Scheduled booking exception review.
* Aggregate operations and financial reports.
* Audit/security review.

Every page displays the active scope and whether values are draft, under review,
scheduled for activation, active, replaced, paused, or retired. Configuration
activation, service-area approval, operator status/assignment, rate activation,
route publication, city lifecycle change, driver decision, and
grant mutation use a review summary plus explicit confirmation. Success appears
only after the backend returns the new version/status.

Charts use existing semantic colors and text/table alternatives; they do not
introduce a dashboard rainbow. Maps use public route/service-area geometry and
authorized aggregate zones, never participant trails or passenger-facing online
driver markers. Responsive narrow layouts may collapse the sidebar, but the
console is desktop-first and must remain keyboard navigable.

The public driver application portal shares brand/auth/onboarding components but
has no operations navigation. Applicant status uses the same pending/review/
additional-information/approved/rejected/withdrawn semantics as the driver
mobile app.

---

## State presentation matrix

Every screen/slice must implement:

| State | Visual treatment |
| --- | --- |
| Loading (initial) | Skeleton or navy splash; not blank white |
| Loading (mutation) | CTA spinner; content locked |
| Empty | Mark + one sentence + CTA |
| Error | Banner or inline; actionable retry when safe |
| Offline | Dedicated offline screen or sticky banner per `design.md` |
| Success | Brief check + settled static confirmation |
| Backend conflict / stale | Message from API mapping; refresh path |

Forbidden:

* Optimistic “Driver assigned” before API
* Optimistic “Paid” on cash before settle endpoint
* Keeping cancelled ride in the active slot
* Replaying failed mutating commands on Retry connection

---

## Interaction patterns (Uber/Lyft-like, TaxiMobile-specific)

1. **Thumb-zone primary actions** — CTAs sit in the sheet, not the map top.
2. **Progressive disclosure** — history, support, and profile are secondary; ride is primary.
3. **Countdown honesty** — offer timers mirror server expiry; on local zero or an invalid timing envelope, disable Accept and refresh.
4. **Confirm destructive verbs** — cancel / decline / settle.
5. **Sticky status** — while a ride is active, the shared backend-derived status
   pill remains visible above every Account and Inbox panel for both products;
   secondary content never hides the current ride phase.
6. **Accessible parity** — every map-only affordance has a text/list alternative in the sheet.

---

## Accessibility requirements (non-negotiable)

* Contrast: body text on light ≥ 4.5:1; large display text ≥ 3:1; primary button white on `navy.900` passes.
* Do not use color as the only status signal; include text and optionally icon.
* Focus order: top chrome → sheet title → fields → primary CTA.
* Announce status changes via accessibility live regions when ride phase changes.
* Dynamic type: layouts reflow up to large system font sizes; shared sheet snap
  points use the documented `1.3×`/`1.6×` promotion policy and remain scrollable.
* Reduce motion respected.
* Hit targets ≥ 48 dp.
* Map gestures do not trap screen-reader users; expose pickup/destination controls as standard components.

---

## Localization readiness (Wave 5+)

* Product-owned user-visible strings live in Compose resources with complete
  Arabic, French, and English catalogs; presentation state carries resource
  identities rather than fixed-language error copy.
* Follow the platform locale. Arabic, Persian, Hebrew, and Urdu activate RTL at
  the application root; mixed-direction identifiers remain visually isolated.
* Known backend notification event types map to local catalog copy. Unknown
  future event types may display the bounded server fallback title/body until a
  client catalog entry ships.
* The localization validator requires exact key and format-placeholder parity
  and rejects newly embedded presentation literals in the covered UI surfaces.
* Fare numerals remain Western digits unless product later decides otherwise; keep mono IDs LTR embeds in RTL layouts.
* Do not bake English string lengths into fixed-width buttons; use min width + horizontal padding.

---

## Implementation structure (Compose)

Suggested shared packages once Wave 1 starts:

```text
feature/ui/
  theme/
    TaxiColors.kt
    TaxiTypography.kt
    TaxiShapes.kt
    TaxiMotion.kt
    TaxiTheme.kt
  components/
    TaxiButton.kt
    TaxiTextField.kt
    TaxiSheet.kt
    StatusPill.kt
    FareBlock.kt
    DriverCard.kt
    OfferCard.kt
    MapFab.kt
    ToastBanner.kt
    ConfirmDialog.kt
    Skeleton.kt
  icons/
    TaxiIcons.kt
feature/passenger/
  PassengerHome.kt
  ...
feature/driver/
  DriverHome.kt
  ...
feature/fixedroutes/
  FixedRouteCatalog.kt
  FixedRouteDetail.kt
feature/scheduling/
  ScheduledBookingReview.kt
  UpcomingBookings.kt
feature/operations/             # web source sets / operations root only
  OperationsApp.kt
  OperationsNavigation.kt
  ...
```

Rules:

* `TaxiMobileScreen` (or successors) consumes theme; no raw `Color(0xFF...)` in feature files.
* Coordinators remain source of UI state; components are dumb renderers + intent callbacks.
* Screenshot / UI tests target state rendering, not network.

---

## Asset & build notes

* Bundle Sora / Manrope / IBM Plex Mono under shared compose resources with license files retained.
* Bundle the OFL-licensed Noto Sans Arabic fallback used for Arabic-script text;
  do not rely on browser/system fallback inside the Compose canvas.
* App icons: passenger and driver variants share mark; driver adds a small “wheel” or “D” badge in navy.
* Splash aligns with `navy.950` to avoid white flash.
* Map style should harmonize with navy chrome (cool greys/blues). Final production style remains an ops gate in `roadmap.md`.

---

## Explicit non-goals for UI polish

Do not implement merely because Uber/Lyft have them:

* Surge heatmaps
* Social/share cards
* Promotional sticker overlays on the map
* Fake nearby taxi animation without backend data
* Real online taxi markers/counts or candidate heatmaps before assignment
* Chat UI before a documented messaging contract
* Dark-mode full theme
* Custom tab-bar dashboard stuffing stats into the first viewport
* Gesture-only flows without button alternatives

---

## Delivery checklist (per UI slice)

Before a visual slice is “done”:

1. Matches tokens in this document (colors, type, radii, motion).
2. Still obeys backend-authoritative state rules in `design.md`.
3. Loading / empty / error / offline / success covered.
4. Accessibility contrast + reduce-motion checked.
5. Focused UI tests or screenshot tests for critical states where practical.
6. No secrets, tokens, raw passwords, or precise unnecessary location history rendered.
7. Docs updated only if the approved visual contract itself changes.

Android registration acceptance may be repeated through the guarded workspace
launcher. The harness submits the actual localized Compose fields and requires
both the backend registration confirmation and backend-authorized post-login
role gate. It clears only the selected debug package after explicit confirmation,
keeps accessibility data in memory, and never prints its synthetic credentials.
This functional path complements rather than replaces the physical screenshot,
font clipping, TalkBack, permission-dialog, and MapLibre rendering matrix.

---

## Remaining visual release inputs

Source-owned Wave decisions are closed: secondary passenger navigation is
account-menu-first, offer attention uses platform-managed haptics without a sound,
and Arabic uses the platform fallback font until a separately licensed companion
passes physical-device readability and clipping acceptance. The remaining inputs
cannot be proven from source alone:

1. Final production MapLibre style (must still fit navy chrome and attribution rules).
2. Exact marketing wordmark spacing and approved copy for store screenshots.
3. Arabic fallback/font acceptance on the supported physical-device matrix.
