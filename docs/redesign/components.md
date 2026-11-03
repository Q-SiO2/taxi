# Component contracts and Unlumen recreation plan

**Selected style system, recorded 15 October 2026:** Folded Streets / Street Press /
Glazed Machine / Notepad. [style-options.md](style-options.md) overrides the baseline
radius, edge, surface and decorative-motion treatment below. All 40 component
contracts retain their controls, icons, semantics, dimensions and recovery in each
style. C04 supplies the four labelled Style choices; do not use a four-way segment.
Notepad has grayscale tokens and no decorative animation controllers.


**Proposed; no application components have been changed for this redesign.**
These are product components in shared Compose/theme resources and web-owned
compositions. Reuse current command/state contracts. Component names below are
design names and may be mapped to existing `TaxiButton`, `TaxiTextField`,
`TaxiSheet`, `FareBlock` and other components after reviewing call sites.

## Common contract

Every interactive component receives explicit value, enabled/busy/error state
and intent callback. It cannot authorize a user, assign a driver, advance a ride,
price a journey, settle cash or persist a capability. Preserve the existing
synchronous command gate and session generation fence. A tap emits one intent;
the coordinator reconciles authoritative results. Local optimism is allowed for
focus, draft text and selection only, not backend status.

The [visual system](visual-system.md) defines all colors and metrics. Normal,
focus, pressed, busy, disabled, error, RTL, enlarged-text and reduced-motion
variants are mandatory. On web add hover and keyboard navigation. Each component
needs meaningful semantics, logical reading order and non-color state labels.

## Product component catalogue

| ID / component | Anatomy and styling | Options and interactions | Failure / access behavior |
| --- | --- | --- | --- |
| C01 ActionButton | 56 dp, 12 radius, 16/600 label; optional 20 dp leading icon | Primary solid; secondary outlined; tertiary text; destructive; full width or content width; 64 dp driver variant | Busy preserves width and announces action; competing writes locked; disabled reason visible; no success before server |
| C02 IconAction | 48 dp fixed target, 24 dp icon, solid surface | Neutral/active/danger; optional bounded unread badge; tooltip on web | Localized label; focus ring; counts read as text; never a truncated user-name capsule |
| C03 FormField | Persistent label, 56 dp minimum container, 16 sp value, helper/error below | Text/email/phone/password/multiline/read-only; leading icon optional; password reveal explicit | Correct keyboard/autofill; no secret in errors/logging; preserve safe draft; errors identified semantically |
| C04 ChoiceRow | Label, optional supporting text, trailing check/radio, 56–72 dp | Single/multiple selection; four Style rows; enabled/disabled/read-only | Selected state uses wash + check; no reliance on hover; long text wraps |
| C05 Segment | 48 dp target per option, 12 radius track; moving selection wash | Two/three labelled choices; equal widths or measured content widths | Too many/long options become a list; RTL/focus movement explicit; no tiny icons-only mode |
| C06 PageBar | Back, 24 sp title or compact title, one contextual action | Standard/full-page/transparent over map with opaque controls | Honors safe area; title wraps where needed; session/scope visible when relevant |
| C07 DestinationNav | Three fixed destinations with icon + 12–14 sp label | Passenger Ride/Trips/Account; driver Work/Earnings/Account; selected wash | No magnifying hit targets; active trip remains reachable; no unsupported destination |
| C08 JourneySheet | 24 dp top corners, handle, title, scroll content, stable footer | Peek/review/full-page; draggable only if meaning is clear | Keyboard resizes content; dismissal navigates, never cancels; focus returns to launcher |
| C09 JourneyRow | A-circle or B-square, label, human location, Edit control | Pickup/destination/stop where supported; compact/expanded | Unnamed point has truthful fallback; no assumed address; bidi-isolated coordinates only in diagnostics |
| C10 PinSelection | Fixed central pin, instruction, point summary, confirm footer | Pickup/destination; recenter; textual fallback | Location/tile/provider denial distinct; unsupported service-area result prevents request |
| C11 FareSummary | 28 sp amount + readable currency, estimate/final/pending label | Collapsed summary; expandable server breakdown; quote expiry | No reconstructed tariff; point edits invalidate quote; unavailable final fare says so |
| C12 DriverIdentity | Authorized display name, taxi ID, color/make/model, small image/fallback | Assigned/arriving/arrived; coordination and safety | No star rating/photo if absent; no full contact info; last-known marker explicitly aged |
| C13 OfferPanel | Pickup then destination, server timing, fare/fee/net, Accept/Decline fixed footer | Immediate/fixed-route/scheduled; urgent badge | Accept disabled for invalid/expired time or uncertainty; refresh; no automatic acceptance |
| C14 TripPhasePanel | Human phase title, confirmed facts, next allowed command | Passenger read/coordination; driver arrival/start/complete | Source state determines action; stale/disconnected blocks unsafe transition |
| C15 AvailabilityControl | 64 dp labelled Go online/Go offline action and current status | Requested/busy/confirmed/restricted | Not a visual switch that immediately declares online; freshness/vehicle/eligibility gate |
| C16 HealthStrip | One compact icon, label and expandable detail | GPS/network/session/map; show only material problem | Does not permanently occupy healthy idle map; status label and actionable fix |
| C17 StatusBadge | 8 radius, text + symbol, 12–14 sp | Neutral/info/warning/success/danger; outline or soft fill | No glowing claim of eligibility; success and pending distinct in grayscale |
| C18 InlineNotice | Icon, concise explanation, optional Retry/Review | Info/error/stale/restricted/empty | Nonmodal unless continuing is impossible; do not bury critical error in toast |
| C19 Skeleton | Same geometry as eventual content, restrained shimmer | Row/card/fare/form/table; static reduced motion | Only unknown fields replaced; one announcement; timeout produces actionable error |
| C20 CashCard | Trip/date/amount/state and explicit confirm/reload | Pending queue/selected item/detail/settled read view | Oldest-first server queue; survive restart; pagination preserved; failed load is not “all settled” |
| C21 Receipt | Final fare, method/state, breakdown, refunds, trip summary | Cash/manual transfer; pending/processing/completed/refunded | No credentials/statement images; copy exact transfer data; claims never equal verification |
| C22 ReviewDialog | Title, consequence, exact target/scope/amount, Cancel/Confirm | Cancellation/cash/application/version/grant/security | No auto-submit after MFA; conflict preserves review; dangerous commands distinct from dismissal |
| C23 FormSection | Title, explanation, grouped fields, error summary | Native single task; desktop 2-column only for related fields | First invalid field focus; drafts safe; no giant generic scroll form |
| C24 Timeline | Static labelled steps, date, current state, optional note | Application/booking/trip/case/version/security audit | Server event order; unknown is not complete; private notes stay role-scoped |
| C25 TripRow | Human location/date/status and fare when authorized | Completed/cancelled/unmatched/upcoming; detail navigation | No UUID-first title; loading/empty/error independent of active-trip state |
| C26 NotificationRow | Read/unread marker, safe title/date, resource action | Mark read; open authorized resource | Refresh hint only; missing/unauthorized resource handled without exposing content |
| C27 SupportComposer | Category, authorized trip context, bounded message, submit | Ordinary support/safety/coordination templates only where implemented | No fake emergency response or masked call; pending result retains message |
| C28 SettingRow | Label + supporting text + value/control | Language/four selected styles/sign out/read-only security facts | No pretend contact verification or delete/export buttons without contracts |
| C29 DocumentSlot | Requirement name/type/status, file metadata, Upload/Replace | PDF/JPEG/PNG capability-gated; scan/loading/rejected/ready | No preview of protected file without authorized retrieval; failure retains draft, not fake attachment |
| C30 ScopeBar | Market/operator/city labels, accessible chooser and freshness | Persistent protected-console scope; constrained picker | Scope change closes protected detail/draft safely; no cross-scope stale result |
| C31 DataTable | Header, labelled sort/filter, 48 px rows, pagination/footer | Queue/default; dense 40 px desktop optional; narrow record cards | Sorting only where supported; no invented total/page; loading separate from empty |
| C32 DetailWorkspace | Queue/master left; explicit detail panel right | Drawer/full page/narrow stack, reviewed footer | Focus trap for modal; Escape closes safe detail; back retains filters/scroll |
| C33 VersionEditor | Labelled compatible records, draft/review/active marker, effective dates | Tariff/fee/scheduling/requirements/service-area/config/route | No arbitrary JSON form; optimistic-version conflicts; independent review preserved |
| C34 MetricChart | Label/unit/time range/freshness, constrained semantic plot | Trend/bar/bounded zone; table equivalent | Suppression/absence explicit; no individual trails; no animation of false real-time data |
| C35 AuditRow | Actor/action/time/scope and expandable exact reference | Read-only timeline and safe reference copy | Private payloads not revealed; immutable history not edited |
| C36 CommandPalette | Optional searchable authorized navigation list | Keyboard shortcut desktop; visible menu alternative | Navigation only in first version; cannot bypass confirmation/MFA/authorization |
| C37 CopyFeedback | Fixed copy/check icon and brief text | Transfer reference/taxi ID/approved audit reference | Exact selected field only; clipboard failure says so; no copied secrets |
| C38 RefreshFeedback | Fixed icon + refreshing text | Page/queue/trip reload; retry | Cancels obsolete reads on scope/session change; stale state labelled until refresh resolves |
| C39 EmptyPanel | Short explanation, compact icon, actual next action | No trips/no offers/no application/no queue/filtered zero | Distinguish truly empty from suppressed, restricted or failed read |
| C40 SafeActionFooter | Stable primary plus secondary/tertiary action | Booking, offer, trip phase, review | Content remains scrollable above; safe area honored; no covered terms |

## All Unlumen primitive decisions

The inspected author documentation lists 26 distinct primitives when the
additional Tilt page is included (its index advertises “27+”). “Use” means
recreate the useful behavior in original Compose code
after approval. It does not mean importing React source. See the
[license/provenance discussion](research.md). Native and browser implementation
must work with touch, keyboard, accessibility and reduced motion.

| Primitive | Decision / proposed use | Compose translation and limits |
| --- | --- | --- |
| [Clipped Circle](https://unlumen-ui-docs.vercel.app/docs/ui/effects/clipped-circle) | The author primitive is a cursor-following spotlight; explore artwork-only light sweep M14 | Original contained highlight with touch/focus/replay/static variants; no hover requirement or reveal of critical text; see expressive-motion.md |
| [Command Menu](https://unlumen-ui-docs.vercel.app/docs/ui/unlumen/command-menu) | Later operations navigation enhancement C36 | Accessible dialog + filtered authorized destinations; visible menu still exists |
| [Cursor](https://unlumen-ui-docs.vercel.app/docs/ui/unlumen/cursor) | Exclude | Custom pointer offers no mobile value and can obscure map/task controls |
| [Floating Tooltip](https://unlumen-ui-docs.vercel.app/docs/ui/unlumen/floating-tooltip) | Operations explanation and desktop icon labels | Anchored popup on hover/focus; touch opens labelled help; no moving tooltip over driver controls |
| [Glowing Badge](https://unlumen-ui-docs.vercel.app/docs/ui/unlumen/glowing-badge) | Reinterpret as static status badge C17 | Small tint/outline; no glow loop for online, cash or safety |
| [Highlight](https://unlumen-ui-docs.vercel.app/docs/ui/unlumen/highlight) | Use selection wash C05/C07/C30 | Animate indicator bounds/tone; controlled value; touch/focus; fixed hit regions |
| [Kbd](https://unlumen-ui-docs.vercel.app/docs/ui/unlumen/kbd) | Optional desktop shortcut hint | Small semantic keycap; visible full command name; platform shortcut names |
| [Math Graph](https://unlumen-ui-docs.vercel.app/docs/ui/effects/math-graph) | No literal effect; possible C34 plotting rhythm | Real server aggregates, accessible table, no fabricated animated function |
| [Orbiting Skills](https://unlumen-ui-docs.vercel.app/docs/ui/unlumen/orbiting-skills) | Exclude from product | Rotating decorative items compete with the current task |
| [Progressive Blur](https://unlumen-ui-docs.vercel.app/docs/ui/unlumen/progressive-blur) | Optional map-to-panel edge treatment | Prefer cheap opaque/scrim gradient; no blurred text; opaque low-performance fallback |
| [Shimmer Skeleton](https://unlumen-ui-docs.vercel.app/docs/ui/unlumen/shimmer-skeleton) | Use C19 | Canvas/brush sweep clipped to placeholder; 1.6 s; static reduced motion; one semantic loading state |
| [Slider](https://unlumen-ui-docs.vercel.app/docs/ui/unlumen/slider) | Only if a real later setting requires range input | Native value semantics + numeric alternative; no price slider/critical swipe-only command |
| [Switch](https://unlumen-ui-docs.vercel.app/docs/ui/unlumen/switch) | Use for genuine binary settings C28 | Controlled Toggleable semantic value; stable thumb; availability stays explicit C15 |
| [Theme Switch](https://unlumen-ui-docs.vercel.app/docs/ui/unlumen/theme-switch) | Later approved driver theme setting | Static light/dark/system choices; no full-screen circular transition |
| [Tilt Card](https://unlumen-ui-docs.vercel.app/docs/ui/unlumen/tilt-card) | Welcome board experiment only | Optional tiny decorative tilt, never essential; absent on touch/reduced motion |
| [Tilt](https://unlumen-ui-docs.vercel.app/docs/ui/unlumen/tilt) | Exclude from work/booking | Stable surface and hit target outweigh parallax |
| [Tooltip Preview](https://unlumen-ui-docs.vercel.app/docs/ui/unlumen/tooltip-preview) | Optional public route summary, later | Explicit tap/focus detail; never hover-reveal identity documents/private evidence |
| [Velocity Highlight](https://unlumen-ui-docs.vercel.app/docs/ui/unlumen/velocity-highlight) | Exclude | Scroll velocity must not change meaning or readability |
| [Copy Button](https://unlumen-ui-docs.vercel.app/docs/ui/buttons/copy) | Use C37 | Icon morph/crossfade after actual clipboard write; error retained |
| [Glow Button](https://unlumen-ui-docs.vercel.app/docs/ui/buttons/glow) | Reinterpret as crisp primary focus/press | Subtle static edge, no ambient glowing critical action |
| [Magnetic Button](https://unlumen-ui-docs.vercel.app/docs/ui/unlumen/magnetic-button) | Exclude from functional controls | Targets remain fixed; no pointer-following Accept/Confirm/Cancel |
| [Refresh Button](https://unlumen-ui-docs.vercel.app/docs/ui/buttons/refresh) | Use C38 | Contained rotation/busy text only while authorized request is active |
| [Count Up](https://unlumen-ui-docs.vercel.app/docs/ui/effects/count-up) | Optional decorative aggregate introduction after alpha | Final real value always available; no fares, balances or offer-time counting theatre |
| [Scramble Text](https://unlumen-ui-docs.vercel.app/docs/ui/unlumen/scramble-text) | Exclude | No scrambled destinations, price, dates, status or identifiers |
| [Shimmering Text](https://unlumen-ui-docs.vercel.app/docs/ui/unlumen/shimmering-text) | Exclude from readable product text | Static status hierarchy provides clarity without moving light |
| [Text Reveal](https://unlumen-ui-docs.vercel.app/docs/ui/unlumen/text-reveal) | Optional ≤160 ms welcome entrance | Whole line remains semantically present; no word-by-word delay; reduced motion instant |
| Extra [Dock](https://ui.unlumen.com/components/dock) | Borrow contained nav grouping, omit magnification | C07 fixed labelled cells; desktop pointer growth not suitable for driver/touch |
| Extra [Sidebar 001](https://ui.unlumen.com/components/sidebar-001) | Operations shell inspiration | Collapsible labelled rail, focus order and narrow menu; preserve scope |
| Extra [Animated List](https://ui.unlumen.com/components/animated-list) | Restrained list insertion | Stable item keys, ≤160 ms entry; do not reorder an operator's selected row |
| Extra [Motion FAQs Accordion](https://ui.unlumen.com/components/motion-faqs-accordion) | Help and application requirement explanation | Explicit expanded semantics, focus/tap, stable label; reduced motion immediate |

The primitives and four extra free catalogue references form the research
inventory. React APIs and physics values are not copied as Compose parameters;
animation feel is reviewed natively. No paid dependency or Pro source is assumed.

## Screen-component composition rules

Welcome/auth uses C01/C03/C06/C18/C23. Booking uses C08–C11/C19/C40.
Assigned passenger uses C12/C14/C16/C27. Driver work uses C13–C16/C20/C40.
Account/history uses C25–C28/C39. Applicant uses C23/C24/C29/C33.
Operations uses C30–C36/C22/C37/C38. The page books specify the actual options.

Prototype gallery wave must show every C01–C40 component and applicable variants,
not just a happy-path button. Compose performance investigation focuses on map
overlay layers, text measurement, large lists and low-end hardware. Avoid
adding libraries for small animations available in existing Compose APIs.
