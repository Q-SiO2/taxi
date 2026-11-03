# TaxiMobile — Selected four-style system

## Board alpha execution authorized — 15 October 2026

The owner now directs the earliest functional board alpha, authorizes application
implementation and TaxiMobile Railway staging changes/deployment, and requires
French, Arabic and English with concise copy. This supersedes the earlier
planning-only stop. The selected four-style contract remains in force; no further
palette approval is needed. Follow [the active board alpha checkpoint](../board-alpha.md)
for execution and evidence. Native, integrated staging, device and release
acceptance must still be demonstrated.

**Owner-selected direction: 15 October 2026.**
The owner explicitly selected **Folded Streets, Street Press, Glazed Machine and
Notepad** as four options for users to choose from. The preceding independent
color-theme proposal is withdrawn. Prism current, Cut collage and Grain and light
are abstract treatments within the expressive styles, not additional style options.
Main vehicle/city illustrations are not part of the selected system.

This records approval of the visual direction and selection model. Browser
specimens and specifications do not establish native implementation or release
acceptance. The current goal establishes the identity and its implementation path;
application rollout follows the delivery packets below and the existing roadmap.

## Four complete options

| Label | Stable application value | Interface grammar | Abstract treatment | Motion |
| --- | --- | --- | --- | --- |
| Folded Streets | `folded_streets` | Crisp planes, asymmetric color edges, cut/hinged framing and clear hierarchy | Flowing spectral field; consistent cobalt/pink/orange/mint/yellow relationships | Short hinged edges and bounded color movement around a stable content surface |
| Street Press | `street_press` | Sharp printed rules, bold editorial headings, firm actions, deliberate ink rhythm | Contrasting cut collage; multicolor planes and restrained print registration | Short collage/registration performances; text never jitters |
| Glazed Machine | `glazed_machine` | Broad tactile framing, rounded material edges, small stepped shadows and generous controls | Matte grain and a bounded light field | Held settling poses and a light pass; no moving controls |
| Notepad | `notepad` | Grayscale ruled utility, square controls, simple sections and familiar icons | Static rules, margin rail and ink hierarchy; no elaborate graphic field | Decorative motion disabled. Immediate focus/pressed, explicit busy/result feedback and real data updates remain |

Preview values `fold`, `print` and `tactile` map to the three stable application
values above; `notepad` maps directly. Do not persist a display label or palette
name. The default recommendation for the first implementation is Folded Streets;
the user can choose any of the four. This default is an implementation choice,
not a claim that the owner ranked one style above the others.

## Notepad is a complete functional style

Preserve icons, meaningful structure, readable labels, focus order, the current
task, authoritative status and actionable recovery. Give the main job priority:

- Passenger: choose pickup/destination, review fare, request/cancel appropriately,
  follow the assigned trip, resolve payment, review history, access account/help/safety.
- Driver: availability and eligibility, incoming offer, current job, arrival/start/
  completion, cash confirmation/recovery and earnings. Current work remains dominant.
- Applicant: requirements, evidence, submission/review, status and requested correction.
- Operations: scope, queue, record, reviewed command, security and audit workflows.

Remove ornamental animation, moving gradients, parallax, collage performances,
decorative texture and unnecessary hero space. Keep a static ruled-paper structure
and a compact icon for a meaningful empty state. Secondary tools remain reachable
through labelled links/More where appropriate; Notepad does not silently disable
permissions, payment recovery, safety, destructive review or required evidence.

All status distinctions use text and a consistent symbol/outline as well as tone.
Pending cash must not resemble confirmed payment simply because both are gray.
In production, use grayscale semantic tokens and an appropriate monochrome map
presentation, preserving pickup/destination/route distinctions through shape,
stroke and label. The browser atlas additionally desaturates hard-coded schematic
map/status details; that filter is a specimen shortcut, not the native architecture.

## Shared invariants and exact base tokens

| Token | Folded Streets | Street Press | Glazed Machine | Notepad |
| --- | --- | --- | --- | --- |
| Page | `#F7EFD9` | `#FFF8E8` | `#F7F0E5` | `#F5F5F5` |
| Opaque task surface | `#FFFDF4` | `#FFF8E8` | `#FFFDF5` | `#FFFFFF` |
| Primary ink | `#191A23` | `#191A23` | `#191A23` | `#181818` |
| Secondary ink | `#52525C` | `#4B4B4B` | `#565463` | `#505050` |
| Primary action | `#263AD4` | `#191A23` | `#31317D` | `#202020` |
| Action label | `#FFFFFF` | `#FFFFFF` | `#FFFFFF` | `#FFFFFF` |
| Selection surface | `#E8E8FF` | `#FFF3B5` | `#EEE6D9` | `#ECECEC` |
| Control stroke | `#656571` | `#5C5C5C` | `#656277` | `#737373` |
| Static accent | `#EE5A32` | `#EF78AE` | `#A5DCD5` | `#B3B3B3` |

These tokens replace the five historical palette sets. Semantic danger/warning/
confirmed-result roles still have explicit labels and symbols; Notepad substitutes
grayscale semantic tokens. Decorative fields never determine text contrast because
essential text rests on an opaque surface. Validate actual adjacent colors after
native composition; a token calculation alone cannot prove the full render.

Keep the existing licensed font resources and icon family. The current browser
reference uses Plex for the crisp/print/notepad interface, Jakarta for the tactile
Latin treatment, and Plex Arabic for the Arabic specimen. Typography pair changes
are review controls, not another user appearance menu. Avoid letter spacing on
Arabic. Use tabular monetary/timing figures where the font supports them.

Shared interaction dimensions remain: 48 dp minimum icon targets; 56 dp ordinary
primary actions and 64 dp critical driver actions; persistent labels; 16/24 body
and field text; larger Arabic line metrics; content grows at enlarged text sizes.
Style controls radius/edge/shadow rather than altering hit targets or action order.
Notepad removes rounded/shadowed decoration, not minimum usable target sizes.

## Selection, persistence and motion policy

Use one labelled **Style** choice list with exactly four options, a visible checked
state and a short preview. Reuse C04 ChoiceRow, not an overcrowded four-item segment.
Entry points are S12 and links from passenger/driver Account; applicant A12 and
the operations account/preferences surface use the same local style preference.
No new backend endpoint, role, operational command or pricing rule is required.

The setting is presentation state, independent of authentication and server facts.
Persist locally through the existing platform storage patterns; the shared
preference and platform adapters are implemented (see the checkpoint below).
Survive restart
and role/page changes. Do not imply account/device synchronization. A style switch
preserves drafts, scroll/context, selected map points, active ride/offer state and
pending command ownership; it must not reissue a request or rebuild the coordinator.

The browser lab stores `taximobile.designReview.style` only for this review tool.
It accepts a `?style=notepad` (or `fold`/`print`/`tactile`) review link. This does not
write the real app preference. Storage failure must be disclosed by the specimen.

For expressive styles, OS reduced motion suppresses decorative performance while
retaining the selected style and its static pose. Notepad disables decorative
motion independently of OS preference. Real busy/progress/status remains explicit;
no flourish fabricates assignment, arrival, payment or eligibility. Stop effects
when hidden, disposed, offscreen or superseded. Keep active driver, financial,
security and consequential review surfaces stable.

The current replayed reference is one 2,400 ms performance with Stop and scrub.
Native timings and cost require acceptance on the actual platforms. A low-power
static treatment should preserve style geometry, rather than switching the user's
selected style or removing controls.

## Every-page and component coverage

The [atlas](page-atlas.html) renders all 213 individual compositions under each of
the four styles. [All 40 components](component-gallery.html) use the same selection.
Every standalone page specification links this contract; S12 and account entry
compositions include the four-style choice explicitly. The [style coverage ledger](style-coverage.md)
records each page's functional/expressive context and the Notepad condition.
This is comprehensive design/specimen coverage, not 852 implemented native screens.

## Implementation packets

| Packet | Work | Required evidence |
| --- | --- | --- |
| ST-0 Reconcile authorities | Record the selected four-style system, withdraw palette controls and old hero art, update all page/component specifications | Current docs and browser choices agree; no new palette-vs-style ambiguity |
| ST-1 Shared preference and tokens | Introduce one style value/state at the theme boundary; inspect `TaxiTheme.kt`, `TaxiColors.kt`, `TaxiShapes.kt` and call sites; use simple platform persistence | All four values round-trip; unknown value has a documented fallback; preference survives restart; no coordinator or domain request reset |
| ST-2 Components and motion proof | Implement the common component grammar and gated abstract layers; Notepad uses grayscale tokens and no decorative controllers | Real Android/web welcome, fare, driver offer and receipt; Arabic/large text, fixed actions, actual lifecycle/OS reduced motion and decoded/frame cost checks |
| ST-3 Complete view rollout | Apply the shared system through UX-2–UX-8 and the 213-view ledger; adapt compact/static treatment by job | Each view/state/entry path checked; all functions and icons retained in Notepad; consistent preference across roles |
| ST-4 Acceptance and alpha | Owner review of actual native screenshots, phone rehearsal and core journeys before presentation | Existing alpha, pilot and public release gates remain separate; no design/specimen check clears them |

### Native motion observation — 21 October

[Exact-v18 API31 passenger evidence](board-alpha-evidence/v18-native-motion-verification-20261021.json)
now observes the actual OS-motion contract. Forty-nine original screenshots cover
seven conditions: three expressive styles at normal and zero animator scale, plus
Notepad at normal scale. Normal expressive frames visibly change and settle;
all four required static conditions have zero changed artwork pixels. Reduced
motion matches each selected style's normal settled pose exactly. Text and action
pixels stay identical throughout all seven conditions.

Android window/transition animations were disabled equally to isolate application
artwork, then all original settings were restored. The existing account was
restored through normal sign-in. No APK/source, role grant, ride or payment change.
This closes the bounded native welcome OS-motion observation, not frame-rate/CPU,
all-role/all-view lifecycle, iOS or physical-device acceptance. ST-2/ST-3 remain
partial at their wider scope. The dated source checkpoint below is historical;
use [current delivery](../board-alpha.md) for later core, language and visual evidence.

### Historical source implementation checkpoint — 15 October

ST-1 is implemented in shared source with Android SharedPreferences, browser
localStorage, JVM preferences and an iOS UserDefaults adapter. Unknown values
fall back to Folded Streets; storage failure remains visible and retryable.
JVM state-retention and platform-independent storage/contrast/motion tests pass;
Android preference persistence was observed after restart. JS/Wasm and Android
compile; iOS runtime/build acceptance remains open on this Windows host.

ST-2/ST-3 are partial: common and existing page components consume the selected
palette/geometry/type, and twelve actual Android welcome renders plus the first
native ride/cash journey are evidenced in [board-alpha.md](../board-alpha.md).
Each view/state still needs its own acceptance, web localization is incomplete,
and map-provider styling, large text, native reduced-motion/lifecycle/frame-cost
and physical-device evidence remain open. Do not convert 213 specifications or
259 source declarations into a claim that every page has been accepted.

The owner has authorized implementation and TaxiMobile staging deployment.
ST-4, alpha gate acceptance and any unrelated service migration remain separate.
