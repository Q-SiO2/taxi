> Historical proposal. Superseded by [style-options.md](style-options.md); not the selected palette system.

# Proposed visual system and all style variants

**Awaiting owner approval.** This replaces the old visual identity only after the
approval record in [delivery.md](delivery.md). All values below are proposed
design tokens, not additions to application source.

## Five independent identities

All directions use solid readable surfaces, a restrained map and a single
strong action. There is no preference for the old gold/navy scheme. Names are
review shorthand, not new product brands. The app remains TaxiMobile.

| Token / purpose | Forest (initial recommendation) | Orchid | Electric | Terracotta | Graphite/Lime |
| --- | --- | --- | --- | --- | --- |
| Page | `#F5F8F5` | `#FBF8FC` | `#F5F7FC` | `#FBF6F2` | `#F6F7F3` |
| Surface | `#FFFFFF` | `#FFFFFF` | `#FFFFFF` | `#FFFFFF` | `#FFFFFF` |
| Primary ink | `#172520` | `#241B2C` | `#17213A` | `#30221D` | `#202527` |
| Secondary ink | `#55635D` | `#65586D` | `#56627A` | `#716057` | `#5C6264` |
| Action fill | `#123D32` | `#4F2768` | `#2453D4` | `#A33E25` | `#D5F46A` |
| Action label | `#FFFFFF` | `#FFFFFF` | `#FFFFFF` | `#FFFFFF` | `#202527` |
| Action pressed | `#0B2C23` | `#39164E` | `#183BA0` | `#7E2B19` | `#BDD94F` |
| Selection wash | `#CFF6DC` | `#E9DDF5` | `#DDE7FF` | `#FFE2D5` | `#EDF7CA` |
| Selection label | `#123D32` | `#4F2768` | `#183BA0` | `#7E2B19` | `#202527` |
| Strong control stroke | `#81908A` | `#91849A` | `#8290AB` | `#9B887C` | `#838A80` |
| Decorative accent | `#F4B78A` apricot | `#D7A3C8` rose | `#9DCFEA` sky | `#E9B080` sand | `#C8D4C3` sage |
| Route / marker | `#123D32` | `#4F2768` | `#2453D4` | `#A33E25` | `#202527` |
| Focus ring | `#123D32` | `#4F2768` | `#2453D4` | `#A33E25` | `#202527` |
| Personality to evaluate | Grounded, welcoming, professional | Distinctive, expressive, refined | Crisp, energetic, technical | Warm, local, human | Bold, minimal, highly graphic |

Forest is recommended for the first comparison, not declared objectively best.
Orchid is the strongest exploratory alternative if the owner wants a more
unexpected identity. Electric is deliberately included without treating blue
as a default. Terracotta needs particular scrutiny beside warning/error states.
Graphite/Lime needs a dark action outline because lime on white has weak edge
contrast. Style selection is global; do not assemble five palettes page by page.

### Shared semantic colors

| Role | Foreground | Soft background | Meaning |
| --- | --- | --- | --- |
| Success | `#17613D` | `#E2F4E9` | Backend-confirmed result; explicit text/check |
| Warning | `#7A4900` | `#FFF0CC` | Pending cash, stale information, deadline |
| Danger | `#A12632` | `#FCE6E9` | Failed action, restricted account, destructive command |
| Information | `#254C79` | `#E7EFF9` | Neutral instructions and guidance |
| Disabled | `#59645F` | `#E8ECE9` | Unavailable control with reason nearby |
| Neutral status | `#55635D` | `#EEF2EF` | Offline, draft or informational state |

Brand green/terracotta never replaces semantic success/error. Every state has a
label and symbol as well as color. A “Pending” badge cannot look like completed.
Do not use decorative accent text for essential information. Soft dividers
`#DEE5DF` are for grouping only; use the strong stroke for a boundary needed to
identify a control. Focus uses a 2 dp ring and 2 dp contrasting offset.

### Dark and outdoor surfaces

Propose driver dark mode for night use after light-mode approval, not a dark
entire application by default. Page `#141C18`; surface `#1D2922`; raised surface
`#25362C`; primary text `#F4F8F5`; secondary `#B8C7BE`; control stroke `#7D9285`.
Actions in all five dark directions use their pale selection color with dark
primary ink, preserving a clear edge against the surface. Route lines get a
contrasting halo. Success `#A6E4BE`, warning `#FFD48B`, danger `#FFADB6`, info
`#B3D2FF`; each is paired with text, not animated illumination.

High contrast is a controlled variant: opaque surfaces, stronger strokes,
no translucency, no shadows required to find controls, static focus/selection.
Outdoor readability requires a physical bright-light review; calculated ratios
cannot prove glare, screen brightness or vehicle-mount usability.

## Typography: three real pairings

| Pairing | Latin display and UI | Arabic display and UI | Use and tradeoff |
| --- | --- | --- | --- |
| T1 (recommended first comparison) | Inter 400/500/600/700 | Noto Sans Arabic 400/500/600/700 | Compact legible UI, good numeric treatment; familiar Latin voice balanced by original composition |
| T2 | Plus Jakarta Sans 400/500/600/700 | Noto Sans Arabic 400/500/600/700 | Warmer geometric personality; verify narrow French labels and numeral distinction |
| T3 | IBM Plex Sans 400/500/600/700 | IBM Plex Sans Arabic 400/500/600/700 | More editorial/work-tool character; closely related multilingual families |

Use one pairing across all roles. Do not stack multiple Latin display fonts
inside booking. Retain a compact monospace for technical references only in
operations details. Taxi identifiers use the primary family with clear digit
shapes and tabular numerals where supported. No uppercase tracking in Arabic.
Never depend on a system fallback for the approved primary script.

| Style | Size / Latin line height | Weight | Arabic line height | Application |
| --- | --- | --- | --- | --- |
| Welcome display | 32 sp / 40 | 700 | 46 | Maximum two lines; marketing surface only |
| Page title | 24 / 32 | 600 | 36 | Full-page headings |
| Sheet title | 22 / 30 | 600 | 34 | Booking/assigned panel |
| Fare or ETA | 28 / 36 | 700 | 40 | One primary number; units 16 sp |
| Section title | 18 / 26 | 600 | 30 | Cards, form sections |
| Body / input | 16 / 24 | 400 | 28 | Important reading and editable fields |
| Action | 16 / 22 | 600 | 28 | Primary/secondary labels |
| Supporting | 14 / 20 | 400/500 | 24 | Dates, descriptions, helper text |
| Compact metadata | 12 / 18 | 500 | 22 | Noncritical timestamps; never essential fare/offer terms |

No 40–52 sp utility titles, letterspaced all-caps buttons or tiny currency labels.
Use local currency formatting from trusted application data. Never animate
changing fare digits or manufacture a rolling ETA. At 1.3×/1.6×/2× text scale,
expand or scroll the content region; the primary action remains reachable and
does not cover content. Never shrink the font to force a long label into a pill.

Arabic uses `start/end` alignment, mirrored directional arrows/navigation,
unmirrored logos/photos/maps and bidi-isolated mixed-script plates, phone numbers
and references. EN/FR/AR examples must include long names, accented French text,
Arabic diacritics and mixed Latin/numeric taxi plates. Font weights/metrics need
fresh native evidence; the browser board is not an Android shaping test.

## Layout and density

- Spacing tokens: 4, 8, 12, 16, 20, 24, 32, 40 dp. Page margins 20 dp
  (16 at 320 dp); section gap 24; row gap 12; field gap 16.
- Shapes: field/button 12 dp radius; card 16; sheet 24 at its top corners;
  compact badge 8. Reserve circles for icon actions/avatars and fully rounded
  tracks for switches. Avoid making every surface a capsule.
- Touch: 48 dp minimum action region, 56 dp primary height, 64 dp important
  driver control, 8 dp minimum separation. Visible map icon 22–24 inside 48 dp.
- Shadows: optional black 8% at 0/2/8 for floating controls; no thick raised
  buttons or multiple stacked shadows. Borders and solid fills carry hierarchy.
- Mobile bar: 56 dp above native safe area; labelled 3-destination nav ~64 dp
  plus safe area. Hide global nav during pickup/confirmation/active work with
  explicit Back or Return-to-trip controls, never by trapping navigation.
- Sheets: content-sized idle panel; ~45–60% booking review; expanded full page
  when content/keyboard needs it. Peek contains a next action and concise context,
  not a wall of form fields. Scrolling and dismissal never cancel a ride.
- Compact mobile 320–599 dp: one column. 600–839: constrain forms to 560 dp;
  map/detail split only if useful. ≥840: 360–420 dp journey rail beside map.
  Operations ≥1200 px: 232 px sidebar, 64 px scope/header, 24–32 px margins,
  12-column grid. 840–1199: collapsible rail and smaller gutters. Below 840:
  labelled menu, stacked record summary and full-page detail; no squeezed tables.
- Table rows: 48 px default, 40 px optional density on desktop only; no forced
  density selector in alpha. Cards replace tables on narrow screens without
  dropping scope, amount, state or next action.

## Map and markers

Map selection is the alpha entry: “Choose destination on map”, then confirm
pickup. A supplied current-location observation may initialize a pickup draft;
the user still confirms it. Never label a point “Your location” without a
permission/freshness-qualified observation. No empty search box implying a provider.

Map style proposal: pale gray roads, muted green parks, low-detail buildings,
readable street names, two-script labels where the selected licensed style supports
them. Retain actual MapLibre attribution visible outside sheet/keyboard overlays.
Customize style colors only after verifying the current provider's terms and glyph
coverage. Keep a readable approved fallback; never promise a new tile provider.

Route uses 5 dp brand stroke with a 2 dp white/dark halo. Pickup is a circle with
“A”; destination a square with “B”. Shape and labels remain distinguishable without
color. The centered selection pin has a fixed 28–32 dp head and shadow; moving
the map does not animate a bouncing target. Assigned driver marker appears only
when permitted and must say last-known age; no smooth invented motion between
stale samples. Bounds account for the actual sheet height, bars, keyboard and
insets. Recenter is one fixed trailing control; remove overlapping control stacks.
Use accessible text summaries and approved fallback selection when maps fail.
Manual coordinates stay a diagnostic fallback, not a consumer booking form.

## Icons, illustrations and photography

**14 October proposed extension:** [expressive-motion.md](expressive-motion.md)
and the [visual atelier](expressive-board.html) broaden this section with a
complete object/illustration vocabulary and contextual motion studies. The
single-welcome-illustration and minimal-motion preference below is the earlier
comparison baseline, not a restriction on the owner's new exploration. Final
asset/style/placement rules are selected together at approval.

Choose one existing licensed vector family, stroke ~1.75–2 dp, 24 dp visual size,
48 dp interaction region. No Unicode glyph stand-ins, emoji navigation, mixed
filled/outlined semantics or custom icon families for individual screens. Every
icon-only action has a localized name and visible focus. Selected navigation may
use a filled counterpart from that same family.

Welcome illustration proposal: one original flat city/taxi composition using
approved tokens, ≤25% of the mobile screen; no photoreal luxury cars. Existing
illustrations can be retired after approval, not repainted indiscriminately.
Vehicle presentation uses real authorized make/color/identifier and a small
consistent silhouette fallback. Do not show fictional driver portraits, stars or
membership badges as if returned by the server. Safety illustration never takes
precedence over instructions. Any future generated artwork needs a separate
asset/license review and device rendering, not part of this planning change.

## Motion and feedback

| Event | Proposed motion | Reduced motion | Guardrail |
| --- | --- | --- | --- |
| Press | Opacity/tone change, optional 0.98 visual scale for 100 ms | Tone only | Hit region and label stay fixed |
| Tab selection | Selection wash moves in 160–200 ms; critically damped | Immediate selection | Touch and focus work without hover |
| Sheet expansion | 220–280 ms settled vertical transition | Immediate or ≤80 ms fade | Focus follows content; no ride-state change |
| Page navigation | ≤180 ms fade + 8 dp translation | Fade only or immediate | Back restores list/scroll context |
| Skeleton | Low-amplitude 1.6 s sweep, only during actual loading | Static blocks | One loading announcement, never per placeholder |
| Refresh | Contained icon rotation while a request is in flight | Static busy icon/text | No spinner loop after failure |
| Confirmed success | Static check plus ≤160 ms reveal | Static check | Runs only after authoritative reconciliation |
| Matching | Subtle single loading indicator with status text | Static status + busy semantics | No countdown, guaranteed ETA or “almost there” |
| Offer timer | Fixed tabular text plus horizontal elapsed bar | Same static structure | Monotonic server timing; no scramble/pulse |

Do not delay an actionable render for a flourish. No confetti on cash completion,
no infinite gradients, cursor trails, parallax maps or auto-scrolling dashboards.
Propose a gentle single native haptic after a confirmed action only where OS
settings allow it; haptics never become the only confirmation. Sound remains
an explicit driver notification policy, not an invented visual-design feature.

## Content and all global state variants

Normal, hovered (web), keyboard focus, pressed, selected, busy, disabled,
validation error, read-only, restricted, offline and reduced-motion variants
must exist for the relevant component. Hover is never needed to reveal an action.

Loading reserves the actual content shape; never use an entire fake dashboard.
Empty states explain what will appear and offer a genuine action. Error states
preserve drafts, say what failed and provide Retry/Back. Connection loss retains
last confirmed facts with freshness and disables unsafe writes. Session expiry
returns to auth with safe context, without storing password/document/payment data.
Unknown command outcome reconciles before any repeat and never shows success.
No permission means no sensitive record data, even in a cached drawer.

Copy is concise, human and localized: “Waiting for a driver”, “Cash not confirmed”,
“Location needs updating”, “No taxi accepted this request”. Explain what can happen
next. Do not turn database enum names, UUIDs, raw UTC, exception text or tariff
versions into primary labels. Operations may expose exact identifiers in an
explicit diagnostic/audit area with safe copy behavior.

Acceptance metrics and contrast calculations are in [delivery.md](delivery.md).
